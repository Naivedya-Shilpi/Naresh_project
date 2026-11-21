"""Unit and SQLite persistence tests for mocked WhisperX word alignment and fallback."""

import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import routes
from app.database import Base
from app.models import Meeting, TranscriptSegment
from app.services.alignment import AlignmentError, align_audio_segments


@dataclass
class FakeSegment:
    start_time: float
    end_time: float
    text: str


def _fake_whisperx_module(align_result: dict | None = None, align_error: Exception | None = None) -> ModuleType:
    module = ModuleType("whisperx")
    module.load_align_model = lambda **_kwargs: (object(), {"language": "en"})
    module.load_audio = lambda _path: [0.0, 0.0]

    def fake_align(_segments, _model, _metadata, _audio, _device):
        if align_error is not None:
            raise align_error
        return align_result

    module.align = fake_align
    return module


class AlignmentServiceTestCase(unittest.TestCase):
    @contextmanager
    def _seeded_meeting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "storage" / "audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "input.wav").write_bytes(b"wav")

            engine = create_engine(f"sqlite:///{root / 'test.db'}")
            try:
                Base.metadata.create_all(engine)
                with Session(engine) as session:
                    meeting = Meeting(
                        title="meeting.mp4",
                        video_path="storage/uploads/meeting.mp4",
                        audio_path="storage/audio/input.wav",
                        status="completed",
                        transcript_segments=[
                            TranscriptSegment(
                                speaker="Speaker 1",
                                start_time=0.0,
                                end_time=1.5,
                                text="Hello team.",
                            ),
                            TranscriptSegment(
                                speaker="Speaker 2",
                                start_time=1.5,
                                end_time=3.0,
                                text="Good morning.",
                            ),
                        ],
                    )
                    session.add(meeting)
                    session.commit()
                    meeting_id = meeting.id
                yield root, engine, meeting_id
            finally:
                engine.dispose()

    def test_aligns_words_with_mocked_whisperx_and_skips_unaligned_tokens(self) -> None:
        mocked_result = {
            "segments": [
                {
                    "start": 0.12,
                    "end": 1.4,
                    "words": [
                        {"word": "Hello", "start": 0.12, "end": 0.55},
                        {"word": "team", "start": 0.6, "end": 1.4},
                        {"word": "123"},
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "meeting.wav"
            audio_path.write_bytes(b"wav")
            with patch.dict(sys.modules, {"whisperx": _fake_whisperx_module(mocked_result)}), patch(
                "app.services.alignment.settings",
                SimpleNamespace(whisper_language="en", whisper_device="cpu"),
            ):
                aligned = align_audio_segments(
                    audio_path,
                    [FakeSegment(start_time=0.0, end_time=1.5, text="Hello team 123")],
                )

        self.assertEqual(len(aligned), 1)
        self.assertEqual(aligned[0].start_time, 0.12)
        self.assertEqual(aligned[0].end_time, 1.4)
        self.assertEqual([(w.word, w.start_time, w.end_time) for w in aligned[0].words], [
            ("Hello", 0.12, 0.55),
            ("team", 0.6, 1.4),
        ])

    def test_rejects_missing_audio_before_loading_whisperx(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(AlignmentError):
                align_audio_segments(
                    Path(temp_dir) / "missing.wav",
                    [FakeSegment(start_time=0.0, end_time=1.0, text="Hello")],
                )

    def test_align_meeting_persists_words_and_preserves_speakers(self) -> None:
        mocked_result = {
            "segments": [
                {
                    "start": 0.08,
                    "end": 1.42,
                    "words": [
                        {"word": "Hello", "start": 0.08, "end": 0.52},
                        {"word": "team.", "start": 0.58, "end": 1.42},
                    ],
                },
                {
                    "start": 1.55,
                    "end": 2.9,
                    "words": [
                        {"word": "Good", "start": 1.55, "end": 2.0},
                        {"word": "morning.", "start": 2.05, "end": 2.9},
                    ],
                },
            ]
        }

        with self._seeded_meeting() as (root, engine, meeting_id):
            with Session(engine) as session, patch.object(routes, "PROJECT_ROOT", root), patch.dict(
                sys.modules, {"whisperx": _fake_whisperx_module(mocked_result)}
            ), patch(
                "app.services.alignment.settings",
                SimpleNamespace(whisper_language="en", whisper_device="cpu"),
            ):
                aligned_response = routes.align_meeting(meeting_id, db=session)

            self.assertTrue(aligned_response["aligned"])
            self.assertIsNone(aligned_response["alignment_error"])
            self.assertEqual(aligned_response["status"], "completed")
            self.assertEqual([s["speaker"] for s in aligned_response["segments"]], ["Speaker 1", "Speaker 2"])

            with Session(engine) as session:
                transcript = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(transcript["status"], "completed")
            self.assertEqual([s["speaker"] for s in transcript["segments"]], ["Speaker 1", "Speaker 2"])
            self.assertEqual(transcript["segments"][0]["start_time"], 0.08)
            self.assertEqual(
                [(w["word"], w["start_time"], w["end_time"]) for w in transcript["segments"][0]["words"]],
                [("Hello", 0.08, 0.52), ("team.", 0.58, 1.42)],
            )
            self.assertEqual(
                [(w["word"], w["start_time"], w["end_time"]) for w in transcript["segments"][1]["words"]],
                [("Good", 1.55, 2.0), ("morning.", 2.05, 2.9)],
            )

    def test_falls_back_to_segment_timestamps_when_whisperx_unavailable(self) -> None:
        with self._seeded_meeting() as (root, engine, meeting_id):
            with Session(engine) as session, patch.object(routes, "PROJECT_ROOT", root), patch.dict(
                sys.modules, {"whisperx": None}
            ):
                response = routes.align_meeting(meeting_id, db=session)

            self.assertFalse(response["aligned"])
            self.assertIn("WhisperX", response["alignment_error"])
            self.assertEqual(response["status"], "completed")

            with Session(engine) as session:
                transcript = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(
                [(s["speaker"], s["start_time"], s["end_time"], s["words"]) for s in transcript["segments"]],
                [
                    ("Speaker 1", 0.0, 1.5, []),
                    ("Speaker 2", 1.5, 3.0, []),
                ],
            )

    def test_falls_back_to_segment_timestamps_when_alignment_fails(self) -> None:
        failing_module = _fake_whisperx_module(align_error=RuntimeError("alignment crashed"))
        with self._seeded_meeting() as (root, engine, meeting_id):
            with Session(engine) as session, patch.object(routes, "PROJECT_ROOT", root), patch.dict(
                sys.modules, {"whisperx": failing_module}
            ), patch(
                "app.services.alignment.settings",
                SimpleNamespace(whisper_language="en", whisper_device="cpu"),
            ):
                response = routes.align_meeting(meeting_id, db=session)

            self.assertFalse(response["aligned"])
            self.assertIsNotNone(response["alignment_error"])
            self.assertEqual(response["status"], "completed")

            with Session(engine) as session:
                transcript = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(
                [(s["speaker"], s["start_time"], s["end_time"], s["words"]) for s in transcript["segments"]],
                [
                    ("Speaker 1", 0.0, 1.5, []),
                    ("Speaker 2", 1.5, 3.0, []),
                ],
            )
