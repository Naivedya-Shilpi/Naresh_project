"""Unit and SQLite tests for Part 14 FastAPI BackgroundTasks meeting processing."""

from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import routes
from app.database import Base
from app.models import Meeting, TranscriptWord
from app.services.diarization import DiarizationError, DiarizationUnavailableError, SpeakerTurn
from app.services.media import AudioExtractionError
from app.services.transcription import TranscribedSegment, TranscriptionError


class BackgroundProcessingTestCase(unittest.TestCase):
    @contextmanager
    def _temp_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "storage" / "uploads").mkdir(parents=True)
            (root / "storage" / "audio").mkdir(parents=True)
            engine = create_engine(f"sqlite:///{root / 'test.db'}")
            factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            try:
                Base.metadata.create_all(engine)
                with patch.object(routes, "PROJECT_ROOT", root), patch.object(
                    routes, "UPLOAD_DIRECTORY", root / "storage" / "uploads"
                ), patch.object(routes, "AUDIO_DIRECTORY", root / "storage" / "audio"):
                    yield root, engine, factory
            finally:
                routes._ACTIVE_PROCESSING_IDS.clear()
                engine.dispose()

    def _create_uploaded_meeting(self, root: Path, factory) -> int:
        video_path = root / "storage" / "uploads" / "sample.mp4"
        video_path.write_bytes(b"mp4-content")
        with factory() as session:
            meeting = Meeting(
                title="sample.mp4",
                video_path="storage/uploads/sample.mp4",
                status="uploaded",
            )
            session.add(meeting)
            session.commit()
            return meeting.id

    def test_process_endpoint_returns_202_and_prevents_duplicate_jobs(self) -> None:
        process_routes = [
            route
            for route in routes.router.routes
            if getattr(route, "path", None) == "/api/meetings/{meeting_id}/process"
        ]
        self.assertEqual(len(process_routes), 1)
        self.assertEqual(process_routes[0].status_code, 202)

        with self._temp_env() as (root, _engine, factory):
            meeting_id = self._create_uploaded_meeting(root, factory)
            background_tasks = BackgroundTasks()

            with factory() as session:
                result = routes.process_meeting(meeting_id, background_tasks, db=session)

            self.assertEqual(result, {"id": meeting_id, "status": "processing"})
            self.assertEqual(len(background_tasks.tasks), 1)

            # A second call while status is processing must raise 409 Conflict.
            duplicate_tasks = BackgroundTasks()
            with factory() as session, self.assertRaises(HTTPException) as dup_ctx:
                routes.process_meeting(meeting_id, duplicate_tasks, db=session)
            self.assertEqual(dup_ctx.exception.status_code, 409)
            self.assertEqual(len(duplicate_tasks.tasks), 0)

    def test_background_pipeline_runs_stages_sequentially_and_closes_session(self) -> None:
        with self._temp_env() as (root, _engine, factory):
            meeting_id = self._create_uploaded_meeting(root, factory)
            observed_statuses: list[str] = []
            closed_sessions: list[bool] = []

            def tracked_factory():
                raw_session = factory()
                original_close = raw_session.close

                def tracked_close():
                    closed_sessions.append(True)
                    original_close()

                raw_session.close = tracked_close  # type: ignore[method-assign]
                return raw_session

            def record_current_status() -> None:
                with factory() as observer:
                    current = observer.get(Meeting, meeting_id)
                    assert current is not None
                    observed_statuses.append(current.status)

            def fake_extract(_video_path: Path, audio_path: Path) -> None:
                record_current_status()
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"wav")

            def fake_transcribe(_audio_path: Path):
                record_current_status()
                return [
                    TranscribedSegment(start_time=0.0, end_time=1.2, text="Hello everyone."),
                    TranscribedSegment(start_time=1.3, end_time=2.5, text="Welcome back."),
                ]

            def fake_diarize(_audio_path: Path):
                record_current_status()
                return [
                    SpeakerTurn(speaker="Speaker 1", start_time=0.0, end_time=1.2),
                    SpeakerTurn(speaker="Speaker 2", start_time=1.2, end_time=2.6),
                ]

            def fake_align(_audio_path: Path, segments):
                record_current_status()
                segments[0].words = [
                    TranscriptWord(word="Hello", start_time=0.0, end_time=0.5),
                    TranscriptWord(word="everyone.", start_time=0.6, end_time=1.2),
                ]
                return True, None

            with patch("app.api.routes.extract_audio", side_effect=fake_extract), patch(
                "app.api.routes.transcribe_audio", side_effect=fake_transcribe
            ), patch("app.api.routes.diarize_audio", side_effect=fake_diarize), patch(
                "app.api.routes.apply_word_alignment", side_effect=fake_align
            ):
                routes.run_meeting_processing_pipeline(meeting_id, session_factory=tracked_factory)

            self.assertEqual(
                observed_statuses,
                ["processing", "transcribing", "diarizing", "aligning"],
            )
            self.assertEqual(len(closed_sessions), 1)
            self.assertNotIn(meeting_id, routes._ACTIVE_PROCESSING_IDS)

            with factory() as session:
                saved = session.get(Meeting, meeting_id)
                assert saved is not None
                self.assertEqual(saved.status, "completed")
                self.assertIsNotNone(saved.audio_path)
                self.assertEqual(
                    [seg.speaker for seg in saved.transcript_segments],
                    ["Speaker 1", "Speaker 2"],
                )
                self.assertEqual(
                    [word.word for word in saved.transcript_segments[0].words],
                    ["Hello", "everyone."],
                )

    def test_background_pipeline_continues_when_optional_stages_unavailable(self) -> None:
        with self._temp_env() as (root, _engine, factory):
            meeting_id = self._create_uploaded_meeting(root, factory)

            def fake_extract(_video_path: Path, audio_path: Path) -> None:
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"wav")

            with patch("app.api.routes.extract_audio", side_effect=fake_extract), patch(
                "app.api.routes.transcribe_audio",
                return_value=[TranscribedSegment(start_time=0.0, end_time=1.5, text="Solo speaker.")],
            ), patch(
                "app.api.routes.diarize_audio",
                side_effect=DiarizationUnavailableError("No HF token configured"),
            ), patch(
                "app.api.routes.apply_word_alignment",
                return_value=(False, "WhisperX is not installed on this server."),
            ):
                routes.run_meeting_processing_pipeline(meeting_id, session_factory=factory)

            with factory() as session:
                saved = session.get(Meeting, meeting_id)
                assert saved is not None
                self.assertEqual(saved.status, "completed")
                self.assertEqual(len(saved.transcript_segments), 1)
                self.assertEqual(saved.transcript_segments[0].speaker, "Speaker 1")
                self.assertEqual(saved.transcript_segments[0].text, "Solo speaker.")
                self.assertEqual(saved.transcript_segments[0].words, [])

    def test_background_pipeline_marks_failed_when_required_stages_fail(self) -> None:
        with self._temp_env() as (root, _engine, factory):
            audio_fail_id = self._create_uploaded_meeting(root, factory)
            transcribe_fail_id = self._create_uploaded_meeting(root, factory)
            diarize_fail_id = self._create_uploaded_meeting(root, factory)

            # 1. Audio extraction failure -> failed
            with patch(
                "app.api.routes.extract_audio",
                side_effect=AudioExtractionError("FFmpeg error"),
            ):
                routes.run_meeting_processing_pipeline(audio_fail_id, session_factory=factory)

            def fake_extract(_video_path: Path, audio_path: Path) -> None:
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"wav")

            # 2. Transcription failure -> failed
            with patch("app.api.routes.extract_audio", side_effect=fake_extract), patch(
                "app.api.routes.transcribe_audio",
                side_effect=TranscriptionError("Whisper crashed"),
            ):
                routes.run_meeting_processing_pipeline(transcribe_fail_id, session_factory=factory)

            # 3. Diarization runtime failure -> failed
            with patch("app.api.routes.extract_audio", side_effect=fake_extract), patch(
                "app.api.routes.transcribe_audio",
                return_value=[TranscribedSegment(start_time=0.0, end_time=1.0, text="Test")],
            ), patch(
                "app.api.routes.diarize_audio",
                side_effect=DiarizationError("Corrupt diarization"),
            ):
                routes.run_meeting_processing_pipeline(diarize_fail_id, session_factory=factory)

            with factory() as session:
                for failed_id in (audio_fail_id, transcribe_fail_id, diarize_fail_id):
                    meeting = session.get(Meeting, failed_id)
                    assert meeting is not None
                    self.assertEqual(meeting.status, "failed")
                    self.assertNotIn(failed_id, routes._ACTIVE_PROCESSING_IDS)
