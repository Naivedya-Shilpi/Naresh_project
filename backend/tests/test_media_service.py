"""Unit tests for the standard-library FFmpeg wrapper."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.media import AudioExtractionError, extract_audio, ffmpeg_available


class MediaServiceTestCase(unittest.TestCase):
    def test_ffmpeg_availability_uses_path_lookup(self) -> None:
        with patch("app.services.media.shutil.which", return_value=None):
            self.assertFalse(ffmpeg_available())
        with patch("app.services.media.shutil.which", return_value="/usr/local/bin/ffmpeg"):
            self.assertTrue(ffmpeg_available())

    def test_extract_audio_uses_wav_mono_16khz_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "meeting.mp4"
            audio_path = Path(temp_dir) / "meeting.wav"
            video_path.write_bytes(b"video")

            def fake_run(command, **_kwargs):
                audio_path.write_bytes(b"wav")
                self.assertIn("-ac", command)
                self.assertIn("-ar", command)
                self.assertIn("16000", command)
                self.assertIn("pcm_s16le", command)
                return type("Result", (), {"returncode": 0})()

            with patch("app.services.media.shutil.which", return_value="/usr/local/bin/ffmpeg"), patch(
                "app.services.media.subprocess.run", side_effect=fake_run
            ):
                extract_audio(video_path, audio_path)

            self.assertTrue(audio_path.is_file())

    def test_extract_audio_rejects_invalid_video(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.services.media.shutil.which", return_value="/usr/local/bin/ffmpeg"
        ):
            with self.assertRaises(AudioExtractionError):
                extract_audio(Path(temp_dir) / "missing.mp4", Path(temp_dir) / "audio.wav")
