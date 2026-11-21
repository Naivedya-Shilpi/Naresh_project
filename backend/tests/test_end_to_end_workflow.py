"""End-to-end integration test covering all Part 16 meeting workflows."""

from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import routes
from app.database import Base
from app.services.diarization import SpeakerTurn
from app.services.transcription import TranscribedSegment


class _FakeUploadFile:
    def __init__(self, filename: str, payload: bytes, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
        self._payload = payload
        self._offset = 0
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._payload):
            return b""
        if size < 0:
            chunk = self._payload[self._offset :]
            self._offset = len(self._payload)
            return chunk
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    async def close(self) -> None:
        self.closed = True


def _run_coro_sync(coro):
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value
    raise AssertionError("Coroutine suspended unexpectedly without an event loop.")


def _mock_whisperx_module() -> ModuleType:
    module = ModuleType("whisperx")
    module.load_align_model = lambda **_kwargs: (object(), {"language": "en"})
    module.load_audio = lambda _path: [0.0, 0.0]
    module.align = lambda _segments, _model, _metadata, _audio, _device: {
        "segments": [
            {
                "start": 0.0,
                "end": 1.2,
                "words": [
                    {"word": "Good", "start": 0.0, "end": 0.5},
                    {"word": "morning,", "start": 0.55, "end": 1.2},
                ],
            },
            {
                "start": 1.3,
                "end": 2.4,
                "words": [
                    {"word": "everyone.", "start": 1.3, "end": 2.4},
                ],
            },
            {
                "start": 3.0,
                "end": 4.5,
                "words": [
                    {"word": "Let's", "start": 3.0, "end": 3.6},
                    {"word": "begin!", "start": 3.7, "end": 4.5},
                ],
            },
        ]
    }
    return module


class EndToEndWorkflowTestCase(unittest.TestCase):
    @contextmanager
    def _temp_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "storage" / "uploads").mkdir(parents=True)
            (root / "storage" / "audio").mkdir(parents=True)
            engine = create_engine(f"sqlite:///{root / 'e2e.db'}")
            factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            try:
                Base.metadata.create_all(engine)
                with patch.object(routes, "PROJECT_ROOT", root), patch.object(
                    routes, "UPLOAD_DIRECTORY", root / "storage" / "uploads"
                ), patch.object(routes, "AUDIO_DIRECTORY", root / "storage" / "audio"):
                    yield root, factory
            finally:
                routes._ACTIVE_PROCESSING_IDS.clear()
                engine.dispose()

    def test_complete_upload_process_stream_and_transcript_workflow(self) -> None:
        with self._temp_env() as (root, factory):
            # 1. Upload a meeting video
            upload = _FakeUploadFile("team-standup.mp4", b"0123456789abcdef", "video/mp4")
            with factory() as session:
                created = _run_coro_sync(routes.upload_meeting(file=upload, db=session))

            meeting_id = created["id"]
            self.assertEqual(created["title"], "team-standup.mp4")
            self.assertEqual(created["status"], "uploaded")
            self.assertTrue(created["video_path"].startswith("storage/uploads/"))
            self.assertTrue((root / created["video_path"]).is_file())

            # 2. Start background processing (202 Accepted) and verify duplicate rejection (409)
            bg_tasks = BackgroundTasks()
            with factory() as session:
                queued = routes.process_meeting(meeting_id, bg_tasks, db=session)
            self.assertEqual(queued, {"id": meeting_id, "status": "processing"})
            self.assertEqual(len(bg_tasks.tasks), 1)

            with factory() as session, self.assertRaises(HTTPException) as dup_ctx:
                routes.process_meeting(meeting_id, BackgroundTasks(), db=session)
            self.assertEqual(dup_ctx.exception.status_code, 409)

            # 3-5. Run background pipeline: audio extraction -> transcription -> diarization -> word alignment
            def fake_extract(_video_path: Path, audio_path: Path) -> None:
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"RIFF-fake-wav")

            raw_segments = [
                TranscribedSegment(start_time=0.0, end_time=1.2, text="  Good   morning , "),
                TranscribedSegment(start_time=1.3, end_time=2.4, text="everyone . "),
                TranscribedSegment(start_time=3.0, end_time=4.5, text="Let's   begin !"),
            ]
            speaker_turns = [
                SpeakerTurn(speaker="Speaker 1", start_time=0.0, end_time=2.5),
                SpeakerTurn(speaker="Speaker 2", start_time=2.8, end_time=4.6),
            ]

            with patch("app.api.routes.extract_audio", side_effect=fake_extract), patch(
                "app.api.routes.transcribe_audio", return_value=raw_segments
            ), patch("app.api.routes.diarize_audio", return_value=speaker_turns), patch.dict(
                sys.modules, {"whisperx": _mock_whisperx_module()}
            ), patch(
                "app.services.alignment.settings",
                SimpleNamespace(whisper_language="en", whisper_device="cpu"),
            ):
                routes.run_meeting_processing_pipeline(meeting_id, session_factory=factory)

            # 6. Stream and seek the uploaded video via HTTP Range requests
            with factory() as session:
                full_video = routes.stream_meeting_video(meeting_id, range_header=None, db=session)
                partial_video = routes.stream_meeting_video(meeting_id, range_header="bytes=4-9", db=session)

            self.assertEqual(full_video.status_code, 200)
            self.assertEqual(full_video.headers["content-length"], "16")
            self.assertEqual(partial_video.status_code, 206)
            self.assertEqual(partial_video.headers["content-range"], "bytes 4-9/16")
            video_disk_path = root / created["video_path"]
            self.assertEqual(b"".join(routes._iter_video_bytes(video_disk_path, 4, 9)), b"456789")

            # 7-9. Retrieve meeting listing, detail, and processed speaker-grouped transcript with words
            with factory() as session:
                listing = routes.list_meetings(db=session)
                detail = routes.get_meeting_detail(meeting_id, db=session)
                transcript = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(listing["total"], 1)
            self.assertEqual(listing["meetings"][0]["status"], "completed")
            self.assertEqual(listing["meetings"][0]["segment_count"], 2)
            self.assertEqual(listing["meetings"][0]["speaker_count"], 2)

            self.assertEqual(detail["status"], "completed")
            self.assertTrue(detail["audio_path"].startswith("storage/audio/"))
            self.assertEqual(len(transcript["segments"]), 2)

            first_turn, second_turn = transcript["segments"]
            self.assertEqual(first_turn["speaker"], "Speaker 1")
            self.assertEqual(first_turn["start_time"], 0.0)
            self.assertEqual(first_turn["end_time"], 2.4)
            self.assertEqual(first_turn["formatted_timestamp"], "00:00:00")
            self.assertEqual(first_turn["text"], "Good morning, everyone.")
            self.assertEqual(
                [w["word"] for w in first_turn["words"]],
                ["Good", "morning,", "everyone."],
            )

            self.assertEqual(second_turn["speaker"], "Speaker 2")
            self.assertEqual(second_turn["start_time"], 3.0)
            self.assertEqual(second_turn["end_time"], 4.5)
            self.assertEqual(second_turn["formatted_timestamp"], "00:00:03")
            self.assertEqual(second_turn["text"], "Let's begin!")
            self.assertEqual(
                [w["word"] for w in second_turn["words"]],
                ["Let's", "begin!"],
            )
