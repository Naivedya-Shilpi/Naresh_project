"""System and upload HTTP routes."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.database import get_db
from app.models import Meeting, TranscriptSegment
from app.services.media import AudioExtractionError, FFmpegUnavailableError, extract_audio
from app.services.diarization import (
    DiarizationError,
    DiarizationUnavailableError,
    assign_speakers_to_segments,
    diarize_audio,
)
from app.services.transcription import (
    TranscriptionError,
    TranscriptionUnavailableError,
    transcribe_audio,
)


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


@router.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Describe the local API without exposing implementation details."""
    return {"message": "Meeting Transcriber API"}


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return a minimal liveness response for local development."""
    return {"status": "ok", "service": "meeting-transcriber-backend"}


@router.post("/api/meetings/upload", status_code=status.HTTP_201_CREATED, tags=["meetings"])
async def upload_meeting(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Store one supported video and create its initial meeting record."""
    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    if extension not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported video type. Upload an MP4, WebM, or MOV file.",
        )
    if file.content_type not in {None, "application/octet-stream", SUPPORTED_TYPES[extension]}:
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
            title=original_filename,
            video_path=str(saved_path.relative_to(PROJECT_ROOT)),
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


@router.post("/api/meetings/{meeting_id}/extract-audio", tags=["meetings"])
def extract_meeting_audio(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Extract a meeting's audio synchronously and record the WAV artifact."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")

    storage_root = (PROJECT_ROOT / "storage").resolve()
    video_path = (PROJECT_ROOT / meeting.video_path).resolve()
    if not video_path.is_relative_to(storage_root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting video path is invalid.")

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

    meeting.audio_path = str(audio_path.relative_to(PROJECT_ROOT))
    meeting.status = "audio_ready"
    db.commit()
    db.refresh(meeting)

    return {
        "id": meeting.id,
        "audio_path": meeting.audio_path,
        "status": meeting.status,
    }


@router.post("/api/meetings/{meeting_id}/transcribe", tags=["meetings"])
def transcribe_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Transcribe an audio-ready meeting with default Speaker 1 labels."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if meeting.status != "audio_ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting audio must be ready before transcription can start.",
        )
    if not meeting.audio_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no extracted audio.")

    storage_root = (PROJECT_ROOT / "storage").resolve()
    audio_path = (PROJECT_ROOT / meeting.audio_path).resolve()
    if not audio_path.is_relative_to(storage_root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting audio path is invalid.")

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
        "segments": [
            {
                "id": segment.id,
                "speaker": segment.speaker,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
            }
            for segment in transcript_segments
        ],
    }


@router.post("/api/meetings/{meeting_id}/diarize", tags=["meetings"])
def diarize_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    """Assign pyannote speaker labels to an already transcribed meeting."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
    if meeting.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting transcription must be completed before diarization can start.",
        )
    if not meeting.audio_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no extracted audio.")

    storage_root = (PROJECT_ROOT / "storage").resolve()
    audio_path = (PROJECT_ROOT / meeting.audio_path).resolve()
    if not audio_path.is_relative_to(storage_root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting audio path is invalid.")

    transcript_segments = list(meeting.transcript_segments)
    if not transcript_segments:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting has no transcript segments.")

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
        "segments": [
            {
                "id": segment.id,
                "speaker": segment.speaker,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
            }
            for segment in transcript_segments
        ],
    }
