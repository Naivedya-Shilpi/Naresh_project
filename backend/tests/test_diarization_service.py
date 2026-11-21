"""Unit tests for mocked speaker turns, error handling, and SQLite segment attribution."""

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import routes
from app.database import Base
from app.models import Meeting, TranscriptSegment
from app.services.diarization import (
    DiarizationError,
    DiarizationUnavailableError,
    SpeakerTurn,
    assign_speakers_to_segments,
    diarize_audio,
)


@dataclass
class FakeSegment:
    start_time: float
    end_time: float
    speaker: str = "Speaker 1"


def _fake_pyannote_modules(pipeline_cls: type) -> dict[str, ModuleType]:
    pyannote_package = ModuleType("pyannote")
    pyannote_package.__path__ = []
    audio_module = ModuleType("pyannote.audio")
    audio_module.Pipeline = pipeline_cls
    return {"pyannote": pyannote_package, "pyannote.audio": audio_module}


class DiarizationServiceTestCase(unittest.TestCase):
    def test_labels_mocked_raw_speakers_by_first_appearance(self) -> None:
        test_case = self

        class Turn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class Annotation:
            def itertracks(self, yield_label):
                test_case.assertTrue(yield_label)
                return iter(
                    [
                        (Turn(0.0, 1.0), "track-a", "SPEAKER_01"),
                        (Turn(1.0, 2.0), "track-b", "SPEAKER_00"),
                        (Turn(2.0, 3.0), "track-c", "SPEAKER_01"),
                    ]
                )

        class Pipeline:
            @classmethod
            def from_pretrained(cls, _model, **_kwargs):
                return cls()

            def __call__(self, _path):
                return Annotation()

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "meeting.wav"
            audio_path.write_bytes(b"wav")
            with patch.dict(sys.modules, _fake_pyannote_modules(Pipeline)), patch(
                "app.services.diarization.settings",
                SimpleNamespace(pyannote_auth_token="test-token", pyannote_model="test-model"),
            ):
                turns = diarize_audio(audio_path)

        self.assertEqual([turn.speaker for turn in turns], ["Speaker 1", "Speaker 2", "Speaker 1"])

    def test_assigns_speakers_using_largest_timestamp_overlap(self) -> None:
        segments = [
            FakeSegment(start_time=0.0, end_time=1.0),
            FakeSegment(start_time=1.0, end_time=2.2),
            FakeSegment(start_time=2.2, end_time=3.0),
        ]
        mocked_turns = [
            SpeakerTurn(speaker="Speaker 1", start_time=0.0, end_time=1.4),
            SpeakerTurn(speaker="Speaker 2", start_time=1.4, end_time=3.0),
        ]

        assign_speakers_to_segments(segments, mocked_turns)

        self.assertEqual([segment.speaker for segment in segments], ["Speaker 1", "Speaker 2", "Speaker 2"])

    def test_keeps_default_speaker_when_no_turn_overlaps(self) -> None:
        segment = FakeSegment(start_time=5.0, end_time=6.0)
        assign_speakers_to_segments([segment], [SpeakerTurn("Speaker 2", 0.0, 1.0)])
        self.assertEqual(segment.speaker, "Speaker 1")

    def test_rejects_missing_audio_before_loading_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(DiarizationError):
                diarize_audio(Path(temp_dir) / "missing.wav")

    def test_requires_auth_token_for_model_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "meeting.wav"
            audio_path.write_bytes(b"wav")
            with patch(
                "app.services.diarization.settings",
                SimpleNamespace(pyannote_auth_token=None, pyannote_model="test-model"),
            ):
                with self.assertRaises(DiarizationUnavailableError):
                    diarize_audio(audio_path)

    def test_raises_unavailable_when_pipeline_returns_none(self) -> None:
        class DeniedPipeline:
            @classmethod
            def from_pretrained(cls, _model, **_kwargs):
                return None

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "meeting.wav"
            audio_path.write_bytes(b"wav")
            with patch.dict(sys.modules, _fake_pyannote_modules(DeniedPipeline)), patch(
                "app.services.diarization.settings",
                SimpleNamespace(pyannote_auth_token="test-token", pyannote_model="test-model"),
            ):
                with self.assertRaises(DiarizationUnavailableError):
                    diarize_audio(audio_path)

    def test_diarize_meeting_updates_sqlite_segments(self) -> None:
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
                            TranscriptSegment(speaker="Speaker 1", start_time=0.0, end_time=1.0, text="First."),
                            TranscriptSegment(speaker="Speaker 1", start_time=1.0, end_time=2.0, text="Second."),
                        ],
                    )
                    session.add(meeting)
                    session.commit()
                    meeting_id = meeting.id

                mocked_turns = [
                    SpeakerTurn(speaker="Speaker 1", start_time=0.0, end_time=0.8),
                    SpeakerTurn(speaker="Speaker 2", start_time=0.8, end_time=2.0),
                ]
                with Session(engine) as session, patch.object(routes, "PROJECT_ROOT", root), patch(
                    "app.api.routes.diarize_audio", return_value=mocked_turns
                ):
                    result = routes.diarize_meeting(meeting_id, db=session)

                self.assertEqual(result["status"], "completed")
                self.assertEqual([item["speaker"] for item in result["segments"]], ["Speaker 1", "Speaker 2"])

                with Session(engine) as session:
                    saved_meeting = session.get(Meeting, meeting_id)
                    self.assertIsNotNone(saved_meeting)
                    assert saved_meeting is not None
                    self.assertEqual(saved_meeting.status, "completed")
                    self.assertEqual(
                        [segment.speaker for segment in saved_meeting.transcript_segments],
                        ["Speaker 1", "Speaker 2"],
                    )
            finally:
                engine.dispose()
