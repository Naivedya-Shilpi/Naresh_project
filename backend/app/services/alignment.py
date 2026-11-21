"""Request-time WhisperX word-level alignment with segment-timestamp fallback."""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Protocol, Sequence

from app.config import settings
from app.models import TranscriptSegment, TranscriptWord


class AlignmentUnavailableError(RuntimeError):
    """Raised when WhisperX or its alignment model cannot be loaded."""


class AlignmentError(RuntimeError):
    """Raised when audio segments cannot be aligned."""


@dataclass(frozen=True)
class AlignedWord:
    word: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class AlignedSegment:
    start_time: float
    end_time: float
    words: list[AlignedWord]


class AlignableSegment(Protocol):
    start_time: float
    end_time: float
    text: str


def _valid_span(start_value: object, end_value: object) -> tuple[float, float] | None:
    """Convert raw start/end timestamps to finite ordered floats when valid."""
    if start_value is None or end_value is None:
        return None
    try:
        start_time = float(start_value)
        end_time = float(end_value)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(start_time) and math.isfinite(end_time)) or end_time < start_time:
        return None
    return start_time, end_time


def align_audio_segments(audio_path: Path, segments: Sequence[AlignableSegment]) -> list[AlignedSegment]:
    """Load WhisperX alignment on demand and return word-aligned segments."""
    if not audio_path.is_file():
        raise AlignmentError("The extracted audio file could not be found.")
    if not segments:
        return []

    try:
        import whisperx
    except ImportError as error:
        raise AlignmentUnavailableError("WhisperX is not installed on this server.") from error

    payload = [
        {"start": float(segment.start_time), "end": float(segment.end_time), "text": segment.text}
        for segment in segments
    ]

    try:
        align_model, metadata = whisperx.load_align_model(
            language_code=settings.whisper_language,
            device=settings.whisper_device,
        )
        if align_model is None:
            raise AlignmentUnavailableError("Could not load the WhisperX alignment model.")
        audio = whisperx.load_audio(str(audio_path))
        result = whisperx.align(payload, align_model, metadata, audio, settings.whisper_device)
    except AlignmentUnavailableError:
        raise
    except Exception as error:
        raise AlignmentError("The transcript could not be word-aligned.") from error

    raw_segments = result.get("segments") if isinstance(result, dict) else None
    if not isinstance(raw_segments, list) or len(raw_segments) != len(segments):
        raise AlignmentError("WhisperX returned unexpected alignment segments.")

    aligned_segments: list[AlignedSegment] = []
    for original, raw_segment in zip(segments, raw_segments):
        if not isinstance(raw_segment, dict):
            raise AlignmentError("WhisperX returned malformed segment data.")

        segment_span = _valid_span(raw_segment.get("start"), raw_segment.get("end"))
        start_time, end_time = (
            segment_span if segment_span is not None else (float(original.start_time), float(original.end_time))
        )

        words: list[AlignedWord] = []
        for raw_word in raw_segment.get("words") or []:
            if not isinstance(raw_word, dict):
                continue
            word_text = str(raw_word.get("word", "")).strip()
            word_span = _valid_span(raw_word.get("start"), raw_word.get("end"))
            if not word_text or word_span is None:
                continue
            words.append(AlignedWord(word=word_text, start_time=word_span[0], end_time=word_span[1]))

        aligned_segments.append(AlignedSegment(start_time=start_time, end_time=end_time, words=words))

    return aligned_segments


def apply_word_alignment(audio_path: Path, segments: Sequence[TranscriptSegment]) -> tuple[bool, str | None]:
    """Apply word alignment to ORM segments, retaining segment timestamps on fallback."""
    try:
        aligned_segments = align_audio_segments(audio_path, segments)
    except (AlignmentUnavailableError, AlignmentError) as error:
        return False, str(error)

    for segment, aligned in zip(segments, aligned_segments):
        segment.start_time = aligned.start_time
        segment.end_time = aligned.end_time
        segment.words = [
            TranscriptWord(word=word.word, start_time=word.start_time, end_time=word.end_time)
            for word in aligned.words
        ]

    return True, None
