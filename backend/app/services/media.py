"""Small FFmpeg wrapper for extracting transcription-ready WAV audio."""

from pathlib import Path
import shutil
import subprocess


class FFmpegUnavailableError(RuntimeError):
    """Raised when FFmpeg cannot be found on the server PATH."""


class AudioExtractionError(RuntimeError):
    """Raised when FFmpeg cannot create a valid output file."""


def ffmpeg_available() -> bool:
    """Return whether the FFmpeg executable can be found."""
    return shutil.which("ffmpeg") is not None


def extract_audio(video_path: Path, audio_path: Path) -> None:
    """Extract mono 16 kHz PCM WAV audio from one video file."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FFmpegUnavailableError("FFmpeg is not installed or is not available on PATH.")
    if not video_path.is_file():
        raise AudioExtractionError("The uploaded video file could not be found.")

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(audio_path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        audio_path.unlink(missing_ok=True)
        raise AudioExtractionError("FFmpeg could not process the uploaded video.") from error

    if result.returncode != 0 or not audio_path.is_file() or audio_path.stat().st_size == 0:
        audio_path.unlink(missing_ok=True)
        raise AudioExtractionError("FFmpeg could not extract audio from this video.")
