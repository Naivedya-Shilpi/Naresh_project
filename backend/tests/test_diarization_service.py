"""Unit tests for mocked speaker turns and timestamp-overlap attribution."""

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from app.services.diarization import SpeakerTurn, assign_speakers_to_segments, diarize_audio


@dataclass
class FakeSegment:
    start_time: float
    end_time: float
    speaker: str = "Speaker 1"


class DiarizationServiceTestCase(unittest.TestCase):
    def test_labels_mocked_raw_speakers_by_first_appearance(self) -> None:
        class Turn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class Annotation:
            def itertracks(self, yield_label):
                self.assertTrue(yield_label)
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

        pyannote_package = ModuleType("pyannote")
        pyannote_package.__path__ = []
        audio_module = ModuleType("pyannote.audio")
        audio_module.Pipeline = Pipeline

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "meeting.wav"
            audio_path.write_bytes(b"wav")
            with patch.dict(sys.modules, {"pyannote": pyannote_package, "pyannote.audio": audio_module}), patch(
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
