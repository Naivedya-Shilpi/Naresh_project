"""Request-time Faster-Whisper transcription service."""

from dataclasses import dataclass
from pathlib import Path

from app.config import settings


class TranscriptionUnavailableError(RuntimeError):
    """Raised when Faster-Whisper cannot be loaded on this machine."""


class TranscriptionError(RuntimeError):
    """Raised when an audio file cannot be transcribed."""


@dataclass(frozen=True)
class TranscribedSegment:
    start_time: float
    end_time: float
    text: str


def transcribe_audio(audio_path: Path) -> list[TranscribedSegment]:
    """Load the configured model on demand and return timestamped segments."""
    if not audio_path.is_file():
        raise TranscriptionError("The extracted audio file could not be found.")

    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise TranscriptionUnavailableError("Faster-Whisper is not installed on this server.") from error

    try:
        model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        raw_segments, _info = model.transcribe(str(audio_path))
        return [
            TranscribedSegment(
                start_time=float(segment.start),
                end_time=float(segment.end),
                text=segment.text.strip(),
            )
            for segment in raw_segments
            if segment.text.strip()
        ]
    except Exception as error:
        raise TranscriptionError("The audio could not be transcribed.") from error
