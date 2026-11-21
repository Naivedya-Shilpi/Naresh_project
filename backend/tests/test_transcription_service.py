"""Unit tests for lazy Faster-Whisper transcription integration."""

import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from app.services.transcription import TranscriptionError, transcribe_audio


class TranscriptionServiceTestCase(unittest.TestCase):
    def test_transcribes_short_sample_with_timestamps(self) -> None:
        class FakeSegment:
            start = 0.0
            end = 0.5
            text = " Hello meeting. "

        class FakeModel:
            def __init__(self, model_name, *, device, compute_type):
                self.arguments = (model_name, device, compute_type)

            def transcribe(self, _audio_path):
                return iter([FakeSegment()]), object()

        fake_module = ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeModel

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "short.wav"
            with wave.open(str(audio_path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(b"\x00\x00" * 1600)

            with patch.dict(sys.modules, {"faster_whisper": fake_module}):
                segments = transcribe_audio(audio_path)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].start_time, 0.0)
        self.assertEqual(segments[0].end_time, 0.5)
        self.assertEqual(segments[0].text, "Hello meeting.")

    def test_rejects_missing_audio_before_loading_model(self) -> None:
        with self.assertRaises(TranscriptionError):
            transcribe_audio(Path("/missing/audio.wav"))
