"""System, meeting management, processing pipeline, and transcript HTTP routes."""

from pathlib import Path
import re
import threading
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import database
from app.config import PROJECT_ROOT
from app.database import get_db
from app.models import Meeting, TranscriptSegment
from app.services.alignment import apply_word_alignment
from app.services.diarization import (
    DiarizationError,
    DiarizationUnavailableError,
    assign_speakers_to_segments,
    diarize_audio,
)
from app.services.media import AudioExtractionError, FFmpegUnavailableError, extract_audio
from app.services.transcription import (
    TranscriptionError,
    TranscriptionUnavailableError,
    transcribe_audio,
)
from app.services.transcript import build_processed_transcript


router = APIRouter()

MAX_UPLOAD_BYTES = 500 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
UPLOAD_DIRECTORY = PROJECT_ROOT / "storage" / "uploads"
AUDIO_DIRECTORY = PROJECT_ROOT / "storage" / "audio"
SUPPORTED_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
_RANGE_HEADER_RE = re.compile(r"^bytes=(\d*)-(\d*)$", re.IGNORECASE)
_VIDEO_CHUNK_BYTES = 64 * 1024
ACTIVE_PROCESSING_STATUSES = {"processing", "transcribing", "diarizing", "aligning"}
_ACTIVE_PROCESSING_IDS: set[int] = set()
_PROCESSING_LOCK = threading.Lock()


def _serialize_segment(segment: TranscriptSegment) -> dict:
    """Format one transcript segment with its optional aligned words."""
    return {
        "id": segment.id,
        "speaker": segment.speaker,
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "text": segment.text,
        "words": [
            {
                "id": word.id,
                "word": word.word,
                "start_time": word.start_time,
                "end_time": word.end_time,
            }
            for word in segment.words
        ],
    }


def _serialize_meeting_summary(meeting: Meeting, processed: dict | None = None) -> dict:
    """Format meeting metadata and processed transcript counts."""
    summary = processed or build_processed_transcript(
        meeting.id,
        meeting.status,
        meeting.transcript_segments,
        title=meeting.title,
    )
    return {
        "id": meeting.id,
        "title": meeting.title,
        "video_path": meeting.video_path,
        "audio_path": meeting.audio_path,
        "duration": meeting.duration,
        "status": meeting.status,
        "created_at": meeting.created_at.isoformat(),
        "segment_count": summary["segment_count"],
        "speaker_count": summary["speaker_count"],
    }


def _sanitize_upload_filename(raw_filename: str | None) -> tuple[str, str]:
    """Sanitize an uploaded video filename and return (display_name, extension)."""
    if not raw_filename or "\x00" in raw_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video filename is invalid.",
        )

    cleaned = "".join(ch for ch in raw_filename.replace("\\", "/") if ord(ch) >= 32)
    basename = Path(cleaned).name.strip()
    if not basename or basename.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video filename is invalid.",
        )

    extension = Path(basename).suffix.lower()
    if extension not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported video type. Upload an MP4, WebM, or MOV file.",
        )

    stem = Path(basename).stem.strip()
    if not stem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video filename is invalid.",
        )

    max_stem_len = 255 - len(extension)
    safe_title = f"{stem[:max_stem_len]}{extension}"
    return safe_title, extension


def _resolve_storage_path(relative_path: str | None, label: str) -> Path:
    """Resolve a stored relative path and verify it stays strictly inside storage/."""
    if not relative_path or not isinstance(relative_path, str) or "\x00" in relative_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Meeting {label} path is invalid.")

    candidate = Path(relative_path)
    if candidate.is_absolute() or candidate.drive:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Meeting {label} path is invalid.")

    storage_root = (PROJECT_ROOT / "storage").resolve()
    resolved = (PROJECT_ROOT / candidate).resolve()
    if resolved == storage_root or not resolved.is_relative_to(storage_root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Meeting {label} path is invalid.")
    return resolved


def _get_meeting_or_404(meeting_id: int, db: Session) -> Meeting:
    """Validate meeting ID and fetch the meeting by primary key."""
    if isinstance(meeting_id, bool) or not isinstance(meeting_id, int) or meeting_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting ID must be a positive integer.",
        )
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    return meeting


def _load_completed_meeting(
    meeting_id: int, action_name: str, db: Session
) -> tuple[Meeting, Path, list[TranscriptSegment]]:
    """Validate a transcribed meeting before post-processing audio and segments."""
    meeting = _get_meeting_or_404(meeting_id, db)
    if meeting.status not in {"completed", "diarization_failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meeting transcription must be completed before {action_name} can start.",
        )
    if not meeting.audio_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no extracted audio.")

    audio_path = _resolve_storage_path(meeting.audio_path, "audio")
    transcript_segments = list(meeting.transcript_segments)
    if not transcript_segments:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no transcript segments.")

    return meeting, audio_path, transcript_segments


# ---------------------------------------------------------------------------
# System routes
# ---------------------------------------------------------------------------


@router.get("/", tags=["system"], summary="API root metadata")
def root() -> dict[str, str]:
    """Describe the local API without exposing implementation details."""
    return {"message": "Meeting Transcriber API"}


@router.get("/health", tags=["system"], summary="Backend health check")
def health() -> dict[str, str]:
    """Return a minimal liveness response for local development."""
    return {"status": "ok", "service": "meeting-transcriber-backend"}


# ---------------------------------------------------------------------------
# Meeting collection & upload routes
# ---------------------------------------------------------------------------


@router.post(
    "/api/meetings/upload",
    status_code=status.HTTP_201_CREATED,
    tags=["meetings"],
    summary="Upload a meeting video",
    responses={
        400: {"description": "Uploaded video file is empty."},
        413: {"description": "Video exceeds the 500 MB upload limit."},
        415: {"description": "Unsupported video file type or MIME type."},
        500: {"description": "Could not save file or create meeting record."},
    },
)
async def upload_meeting(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Store one supported video (MP4, WebM, MOV) and create its initial meeting record."""
    safe_title, extension = _sanitize_upload_filename(file.filename)
    if file.content_type not in {None, "", "application/octet-stream", SUPPORTED_TYPES[extension]}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file content type does not match a supported video format.",
        )

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIRECTORY / f"{uuid4().hex}{extension}"
    bytes_written = 0

    try:
        with saved_path.open("xb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Video exceeds the 500 MB upload limit.",
                    )
                destination.write(chunk)

        if bytes_written == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded video file is empty.")

        meeting = Meeting(
            title=safe_title,
            video_path=saved_path.relative_to(PROJECT_ROOT).as_posix(),
            status="uploaded",
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    except HTTPException:
        saved_path.unlink(missing_ok=True)
        raise
    except OSError as error:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save the video file.") from error
    except Exception as error:
        db.rollback()
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create the meeting.") from error
    finally:
        await file.close()

    return {
        "id": meeting.id,
        "title": meeting.title,
        "video_path": meeting.video_path,
        "status": meeting.status,
        "created_at": meeting.created_at.isoformat(),
    }


@router.get(
    "/api/meetings",
    tags=["meetings"],
    summary="List all meetings",
)
def list_meetings(db: Session = Depends(get_db)) -> dict:
    """Return all recorded meetings ordered from newest to oldest."""
    statement = (
        select(Meeting)
        .options(selectinload(Meeting.transcript_segments).selectinload(TranscriptSegment.words))
        .order_by(Meeting.created_at.desc(), Meeting.id.desc())
    )
    meetings = db.scalars(statement).all()
    return {
        "meetings": [_serialize_meeting_summary(meeting) for meeting in meetings],
        "total": len(meetings),
    }


@router.get(
    "/api/meetings/{meeting_id}",
    tags=["meetings"],
    summary="Retrieve meeting details",
    responses={404: {"description": "Meeting not found."}},
)
def get_meeting_detail(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Return metadata and processed transcript segments for a single meeting."""
    meeting = _get_meeting_or_404(meeting_id, db)
    processed = build_processed_transcript(
        meeting.id,
        meeting.status,
        meeting.transcript_segments,
        title=meeting.title,
    )
    return {
        **_serialize_meeting_summary(meeting, processed=processed),
        "segments": processed["segments"],
    }


def _unsatisfiable_range(file_size: int) -> HTTPException:
    """Build a 416 Range Not Satisfiable error with the RFC Content-Range header."""
    return HTTPException(
        status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        detail="Requested byte range is not satisfiable.",
        headers={"Content-Range": f"bytes */{file_size}"},
    )


def _parse_byte_range(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse an HTTP Range header into an inclusive (start, end) byte span."""
    if file_size <= 0:
        raise _unsatisfiable_range(file_size)

    match = _RANGE_HEADER_RE.match(range_header.strip())
    if not match:
        raise _unsatisfiable_range(file_size)

    start_raw, end_raw = match.groups()
    if not start_raw and not end_raw:
        raise _unsatisfiable_range(file_size)

    if not start_raw:
        suffix_length = int(end_raw)
        if suffix_length <= 0:
            raise _unsatisfiable_range(file_size)
        return max(0, file_size - suffix_length), file_size - 1

    start = int(start_raw)
    if start < 0 or start >= file_size:
        raise _unsatisfiable_range(file_size)

    end = file_size - 1 if not end_raw else min(int(end_raw), file_size - 1)
    if end < start:
        raise _unsatisfiable_range(file_size)

    return start, end


def _iter_video_bytes(video_path: Path, start: int, end: int, chunk_size: int = _VIDEO_CHUNK_BYTES):
    """Stream inclusive byte range [start, end] from a video file."""
    remaining = end - start + 1
    with video_path.open("rb") as video_file:
        video_file.seek(start)
        while remaining > 0:
            chunk = video_file.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get(
    "/api/meetings/{meeting_id}/video",
    tags=["meetings"],
    summary="Stream meeting video with HTTP Range support",
    responses={
        200: {"description": "Full video stream."},
        206: {"description": "Partial byte-range video stream."},
        400: {"description": "Meeting video path is invalid."},
        404: {"description": "Meeting or video file not found."},
        416: {"description": "Requested byte range is not satisfiable."},
    },
)
@router.get(
    "/api/meetings/{meeting_id}/video/stream",
    tags=["meetings"],
    summary="Stream meeting video with HTTP Range support (alias)",
    responses={
        200: {"description": "Full video stream."},
        206: {"description": "Partial byte-range video stream."},
        400: {"description": "Meeting video path is invalid."},
        404: {"description": "Meeting or video file not found."},
        416: {"description": "Requested byte range is not satisfiable."},
    },
)
def stream_meeting_video(
    meeting_id: int,
    range_header: str | None = Header(default=None, alias="Range"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Serve an uploaded meeting video with byte-range seeking support."""
    meeting = _get_meeting_or_404(meeting_id, db)
    video_path = _resolve_storage_path(meeting.video_path, "video")
    if not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting video file could not be found.",
        )

    file_size = video_path.stat().st_size
    if file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting video file is empty.",
        )

    media_type = SUPPORTED_TYPES.get(video_path.suffix.lower(), "application/octet-stream")
    if range_header is None:
        return StreamingResponse(
            _iter_video_bytes(video_path, 0, file_size - 1),
            status_code=status.HTTP_200_OK,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    start, end = _parse_byte_range(range_header, file_size)
    return StreamingResponse(
        _iter_video_bytes(video_path, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(end - start + 1),
        },
    )


# ---------------------------------------------------------------------------
# Processing pipeline routes
# ---------------------------------------------------------------------------


def run_meeting_processing_pipeline(
    meeting_id: int,
    session_factory=None,
) -> None:
    """Run audio extraction, transcription, diarization, and word alignment in the background."""
    with _PROCESSING_LOCK:
        if meeting_id in _ACTIVE_PROCESSING_IDS:
            return
        _ACTIVE_PROCESSING_IDS.add(meeting_id)

    factory = session_factory or database.SessionLocal
    session = factory()
    try:
        meeting = session.get(Meeting, meeting_id)
        if meeting is None:
            return

        try:
            video_path = _resolve_storage_path(meeting.video_path, "video")
        except HTTPException:
            meeting.status = "failed"
            session.commit()
            return

        if not video_path.is_file():
            meeting.status = "failed"
            session.commit()
            return

        # Stage 1: Audio extraction
        meeting.status = "processing"
        session.commit()
        audio_path = AUDIO_DIRECTORY / f"{uuid4().hex}.wav"
        try:
            extract_audio(video_path, audio_path)
        except (FFmpegUnavailableError, AudioExtractionError, Exception):
            meeting.status = "failed"
            session.commit()
            return

        meeting.audio_path = audio_path.relative_to(PROJECT_ROOT).as_posix()
        meeting.status = "audio_ready"
        session.commit()

        # Stage 2: Speech-to-text transcription
        meeting.status = "transcribing"
        session.commit()
        try:
            transcribed_segments = transcribe_audio(audio_path)
        except (TranscriptionUnavailableError, TranscriptionError, Exception):
            meeting.status = "failed"
            session.commit()
            return

        meeting.transcript_segments.clear()
        session.flush()
        transcript_segments = [
            TranscriptSegment(
                meeting_id=meeting.id,
                speaker="Speaker 1",
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.text,
            )
            for segment in transcribed_segments
        ]
        session.add_all(transcript_segments)
        session.commit()

        # Stage 3: Speaker diarization
        if transcript_segments:
            meeting.status = "diarizing"
            session.commit()
            try:
                speaker_turns = diarize_audio(audio_path)
                assign_speakers_to_segments(transcript_segments, speaker_turns)
                session.commit()
            except DiarizationUnavailableError:
                # Preserve default Speaker 1 labels if optional gated model/token is unavailable.
                session.commit()
            except (DiarizationError, Exception):
                meeting.status = "failed"
                session.commit()
                return

            # Stage 4: Optional word alignment (preserves existing transcript on fallback)
            meeting.status = "aligning"
            session.commit()
            try:
                apply_word_alignment(audio_path, transcript_segments)
            except Exception:
                pass

        meeting.status = "completed"
        session.commit()
    except Exception:
        session.rollback()
        try:
            failed_meeting = session.get(Meeting, meeting_id)
            if failed_meeting is not None:
                failed_meeting.status = "failed"
                session.commit()
        except Exception:
            session.rollback()
    finally:
        session.close()
        with _PROCESSING_LOCK:
            _ACTIVE_PROCESSING_IDS.discard(meeting_id)


@router.post(
    "/api/meetings/{meeting_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["meetings"],
    summary="Start full background processing for a meeting",
    responses={
        202: {"description": "Background processing started."},
        400: {"description": "Meeting video path is invalid."},
        404: {"description": "Meeting not found."},
        409: {"description": "Meeting is already being processed."},
        422: {"description": "Uploaded video file could not be found."},
    },
)
def process_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """Queue sequential audio extraction, transcription, diarization, and word alignment."""
    meeting = _get_meeting_or_404(meeting_id, db)
    with _PROCESSING_LOCK:
        is_running = meeting_id in _ACTIVE_PROCESSING_IDS
    if meeting.status in ACTIVE_PROCESSING_STATUSES or is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting is already being processed.",
        )

    video_path = _resolve_storage_path(meeting.video_path, "video")
    if not video_path.is_file():
        meeting.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded video file could not be found.",
        )

    meeting.status = "processing"
    db.commit()
    background_tasks.add_task(run_meeting_processing_pipeline, meeting.id)

    return {
        "id": meeting.id,
        "status": meeting.status,
    }


@router.post(
    "/api/meetings/{meeting_id}/extract-audio",
    tags=["meetings"],
    summary="Extract mono 16 kHz WAV audio from a meeting video",
    responses={
        400: {"description": "Meeting video path is invalid."},
        404: {"description": "Meeting not found."},
        422: {"description": "Source video missing or audio extraction failed."},
        503: {"description": "FFmpeg is unavailable on the server."},
    },
)
def extract_meeting_audio(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Extract a meeting's audio synchronously and record the WAV artifact."""
    meeting = _get_meeting_or_404(meeting_id, db)
    video_path = _resolve_storage_path(meeting.video_path, "video")
    if not video_path.is_file():
        meeting.status = "audio_failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded video file could not be found.",
        )

    audio_path = AUDIO_DIRECTORY / f"{uuid4().hex}.wav"
    meeting.status = "processing"
    db.commit()

    try:
        extract_audio(video_path, audio_path)
    except FFmpegUnavailableError as error:
        meeting.status = "audio_failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except AudioExtractionError as error:
        meeting.status = "audio_failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    meeting.audio_path = audio_path.relative_to(PROJECT_ROOT).as_posix()
    meeting.status = "audio_ready"
    db.commit()
    db.refresh(meeting)

    return {
        "id": meeting.id,
        "audio_path": meeting.audio_path,
        "status": meeting.status,
    }


@router.post(
    "/api/meetings/{meeting_id}/transcribe",
    tags=["meetings"],
    summary="Transcribe meeting audio with Faster-Whisper",
    responses={
        400: {"description": "Meeting audio path is invalid."},
        404: {"description": "Meeting not found."},
        409: {"description": "Meeting audio is not ready for transcription."},
        422: {"description": "Missing audio or transcription error."},
        503: {"description": "Faster-Whisper is unavailable on the server."},
    },
)
def transcribe_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Transcribe an audio-ready meeting with default Speaker 1 labels."""
    meeting = _get_meeting_or_404(meeting_id, db)
    if meeting.status != "audio_ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting audio must be ready before transcription can start.",
        )
    if not meeting.audio_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no extracted audio.")

    audio_path = _resolve_storage_path(meeting.audio_path, "audio")

    meeting.status = "transcribing"
    db.commit()

    try:
        transcribed_segments = transcribe_audio(audio_path)
    except TranscriptionUnavailableError as error:
        meeting.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except TranscriptionError as error:
        meeting.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    meeting.transcript_segments.clear()
    db.flush()
    transcript_segments = [
        TranscriptSegment(
            meeting_id=meeting.id,
            speaker="Speaker 1",
            start_time=segment.start_time,
            end_time=segment.end_time,
            text=segment.text,
        )
        for segment in transcribed_segments
    ]
    db.add_all(transcript_segments)
    meeting.status = "completed"
    db.commit()

    return {
        "id": meeting.id,
        "status": meeting.status,
        "segments": [_serialize_segment(segment) for segment in transcript_segments],
    }


@router.post(
    "/api/meetings/{meeting_id}/diarize",
    tags=["meetings"],
    summary="Assign speaker labels using pyannote.audio",
    responses={
        400: {"description": "Meeting audio path is invalid."},
        404: {"description": "Meeting not found."},
        409: {"description": "Meeting transcription must complete before diarization."},
        422: {"description": "Missing audio/segments or diarization failure."},
        503: {"description": "Pyannote model or token is unavailable."},
    },
)
def diarize_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Assign pyannote speaker labels to an already transcribed meeting."""
    meeting, audio_path, transcript_segments = _load_completed_meeting(meeting_id, "diarization", db)

    meeting.status = "diarizing"
    db.commit()
    try:
        speaker_turns = diarize_audio(audio_path)
        assign_speakers_to_segments(transcript_segments, speaker_turns)
        meeting.status = "completed"
        db.commit()
    except DiarizationUnavailableError as error:
        meeting.status = "diarization_failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except DiarizationError as error:
        meeting.status = "diarization_failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    return {
        "id": meeting.id,
        "status": meeting.status,
        "speaker_turns": [turn.__dict__ for turn in speaker_turns],
        "segments": [_serialize_segment(segment) for segment in transcript_segments],
    }


@router.post(
    "/api/meetings/{meeting_id}/align",
    tags=["meetings"],
    summary="Align transcript words with WhisperX",
    responses={
        400: {"description": "Meeting audio path is invalid."},
        404: {"description": "Meeting not found."},
        409: {"description": "Meeting transcription must complete before alignment."},
        422: {"description": "Meeting has no audio or transcript segments."},
    },
)
def align_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Align transcript words using WhisperX, falling back to segment timestamps."""
    meeting, audio_path, transcript_segments = _load_completed_meeting(meeting_id, "alignment", db)

    meeting.status = "aligning"
    db.commit()
    aligned, error_message = apply_word_alignment(audio_path, transcript_segments)
    meeting.status = "completed"
    db.commit()

    return {
        "id": meeting.id,
        "status": meeting.status,
        "aligned": aligned,
        "alignment_error": error_message,
        "segments": [_serialize_segment(segment) for segment in transcript_segments],
    }


# ---------------------------------------------------------------------------
# Transcript retrieval routes
# ---------------------------------------------------------------------------


@router.get(
    "/api/meetings/{meeting_id}/transcript",
    tags=["meetings"],
    summary="Retrieve processed meeting transcript",
    responses={404: {"description": "Meeting not found."}},
)
@router.get(
    "/api/meetings/{meeting_id}/transcript/processed",
    tags=["meetings"],
    summary="Retrieve processed meeting transcript (alias)",
    responses={404: {"description": "Meeting not found."}},
)
def get_meeting_transcript(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Return a meeting's processed transcript segments and optional word timestamps."""
    meeting = _get_meeting_or_404(meeting_id, db)

    return build_processed_transcript(
        meeting.id,
        meeting.status,
        meeting.transcript_segments,
        title=meeting.title,
    )
