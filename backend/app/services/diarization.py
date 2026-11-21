"""Request-time pyannote speaker diarization and segment attribution."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from app.config import settings


class DiarizationUnavailableError(RuntimeError):
    """Raised when pyannote or its gated model cannot be loaded."""


class DiarizationError(RuntimeError):
    """Raised when diarization cannot process an audio file."""


@dataclass(frozen=True)
class SpeakerTurn:
    speaker: str
    start_time: float
    end_time: float


class TimestampedSegment(Protocol):
    start_time: float
    end_time: float
    speaker: str


def diarize_audio(audio_path: Path) -> list[SpeakerTurn]:
    """Load pyannote on demand and return chronologically labelled speaker turns."""
    if not audio_path.is_file():
        raise DiarizationError("The extracted audio file could not be found.")
    if not settings.pyannote_auth_token:
        raise DiarizationUnavailableError(
            "Pyannote requires a Hugging Face access token with accepted model conditions."
        )

    try:
        from pyannote.audio import Pipeline
    except ImportError as error:
        raise DiarizationUnavailableError("pyannote.audio is not installed on this server.") from error

    try:
        try:
            pipeline = Pipeline.from_pretrained(settings.pyannote_model, token=settings.pyannote_auth_token)
        except TypeError:
            pipeline = Pipeline.from_pretrained(settings.pyannote_model, use_auth_token=settings.pyannote_auth_token)
        annotation = pipeline(str(audio_path))
        raw_turns = sorted(
            (
                (float(turn.start), float(turn.end), str(raw_speaker))
                for turn, _track, raw_speaker in annotation.itertracks(yield_label=True)
                if float(turn.end) > float(turn.start)
            ),
            key=lambda item: (item[0], item[1], item[2]),
        )
    except Exception as error:
        raise DiarizationError("The audio could not be diarized.") from error

    labels: dict[str, str] = {}
    turns: list[SpeakerTurn] = []
    for start_time, end_time, raw_speaker in raw_turns:
        label = labels.setdefault(raw_speaker, f"Speaker {len(labels) + 1}")
        turns.append(SpeakerTurn(speaker=label, start_time=start_time, end_time=end_time))
    return turns


def assign_speakers_to_segments(segments: Iterable[TimestampedSegment], turns: Iterable[SpeakerTurn]) -> None:
    """Set each transcript segment to the speaker with greatest time overlap."""
    ordered_turns = list(turns)
    for segment in segments:
        best_turn: SpeakerTurn | None = None
        best_overlap = 0.0
        for turn in ordered_turns:
            overlap = max(0.0, min(segment.end_time, turn.end_time) - max(segment.start_time, turn.start_time))
            if best_turn is None or overlap > best_overlap:
                best_turn = turn
                best_overlap = overlap
        if best_turn is not None and best_overlap > 0:
            segment.speaker = best_turn.speaker
