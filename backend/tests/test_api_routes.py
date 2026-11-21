"""Comprehensive route, error-handling, session, and OpenAPI tests for Part 10."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import routes
from app.database import Base, get_db
from app.main import app
from app.models import Meeting, TranscriptSegment, TranscriptWord
from app.services.transcription import TranscribedSegment, TranscriptionError


class _FakeUploadFile:
    def __init__(self, filename: str, payload: bytes, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
        self._payload = payload
        self._offset = 0
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._payload):
            return b""
        if size < 0:
            chunk = self._payload[self._offset :]
            self._offset = len(self._payload)
            return chunk
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    async def close(self) -> None:
        self.closed = True


def _run_coro_sync(coro):
    try:
        coro.send(None)
    except StopIteration as stop:
        return stop.value
    raise AssertionError("Coroutine suspended unexpectedly without an event loop.")


class ApiRoutesTestCase(unittest.TestCase):
    @contextmanager
    def _temp_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "storage" / "uploads").mkdir(parents=True)
            (root / "storage" / "audio").mkdir(parents=True)
            engine = create_engine(f"sqlite:///{root / 'test.db'}")
            try:
                Base.metadata.create_all(engine)
                with patch.object(routes, "PROJECT_ROOT", root), patch.object(
                    routes, "UPLOAD_DIRECTORY", root / "storage" / "uploads"
                ), patch.object(routes, "AUDIO_DIRECTORY", root / "storage" / "audio"):
                    yield root, engine
            finally:
                engine.dispose()

    def test_system_routes_and_db_session_lifecycle(self) -> None:
        self.assertEqual(routes.root(), {"message": "Meeting Transcriber API"})
        self.assertEqual(routes.health(), {"status": "ok", "service": "meeting-transcriber-backend"})

        generator = get_db()
        db_session = next(generator)
        self.assertIsInstance(db_session, Session)
        generator.close()

    def test_upload_list_and_get_meeting_detail(self) -> None:
        with self._temp_env() as (root, engine):
            with Session(engine) as session:
                empty_list = routes.list_meetings(db=session)
            self.assertEqual(empty_list, {"meetings": [], "total": 0})

            upload_file = _FakeUploadFile("weekly-sync.mp4", b"video bytes", "video/mp4")
            with Session(engine) as session:
                uploaded = _run_coro_sync(routes.upload_meeting(file=upload_file, db=session))

            self.assertTrue(upload_file.closed)
            self.assertEqual(uploaded["title"], "weekly-sync.mp4")
            self.assertEqual(uploaded["status"], "uploaded")
            self.assertTrue((root / uploaded["video_path"]).is_file())

            # Insert an older completed meeting with grouped segments and words.
            with Session(engine) as session:
                older_meeting = Meeting(
                    title="older-review.mov",
                    video_path="storage/uploads/older.mov",
                    audio_path="storage/audio/older.wav",
                    duration=42.0,
                    status="completed",
                    created_at=datetime.fromisoformat(uploaded["created_at"]) - timedelta(hours=1),
                    transcript_segments=[
                        TranscriptSegment(
                            speaker="Speaker 1",
                            start_time=0.0,
                            end_time=1.0,
                            text="Hello  team .",
                            words=[TranscriptWord(word="Hello", start_time=0.0, end_time=0.5)],
                        ),
                        TranscriptSegment(
                            speaker="Speaker 2",
                            start_time=1.2,
                            end_time=2.5,
                            text="Ready !",
                        ),
                    ],
                )
                session.add(older_meeting)
                session.commit()
                older_id = older_meeting.id

            with Session(engine) as session:
                listing = routes.list_meetings(db=session)
                detail = routes.get_meeting_detail(older_id, db=session)

            self.assertEqual(listing["total"], 2)
            self.assertEqual([item["id"] for item in listing["meetings"]], [uploaded["id"], older_id])
            self.assertEqual(listing["meetings"][1]["segment_count"], 2)
            self.assertEqual(listing["meetings"][1]["speaker_count"], 2)

            self.assertEqual(detail["id"], older_id)
            self.assertEqual(detail["title"], "older-review.mov")
            self.assertEqual(detail["duration"], 42.0)
            self.assertEqual(detail["segment_count"], 2)
            self.assertEqual(detail["speaker_count"], 2)
            self.assertEqual(detail["segments"][0]["text"], "Hello team.")
            self.assertEqual(detail["segments"][0]["words"][0]["word"], "Hello")
            self.assertEqual(detail["segments"][1]["text"], "Ready!")

    def test_upload_rejects_unsupported_empty_and_oversized_files(self) -> None:
        with self._temp_env() as (_root, engine):
            bad_type = _FakeUploadFile("notes.txt", b"text", "text/plain")
            with Session(engine) as session, self.assertRaises(HTTPException) as bad_ctx:
                _run_coro_sync(routes.upload_meeting(file=bad_type, db=session))
            self.assertEqual(bad_ctx.exception.status_code, 415)

            empty_video = _FakeUploadFile("empty.mp4", b"", "video/mp4")
            with Session(engine) as session, self.assertRaises(HTTPException) as empty_ctx:
                _run_coro_sync(routes.upload_meeting(file=empty_video, db=session))
            self.assertEqual(empty_ctx.exception.status_code, 400)
            self.assertTrue(empty_video.closed)

            oversized_video = _FakeUploadFile("large.mov", b"12345", "video/quicktime")
            with Session(engine) as session, patch.object(routes, "MAX_UPLOAD_BYTES", 4), self.assertRaises(
                HTTPException
            ) as size_ctx:
                _run_coro_sync(routes.upload_meeting(file=oversized_video, db=session))
            self.assertEqual(size_ctx.exception.status_code, 413)
            self.assertTrue(oversized_video.closed)

    def test_security_filename_sanitization_storage_paths_and_meeting_ids(self) -> None:
        with self._temp_env() as (root, engine):
            # Path traversal in upload filename is stripped to a safe basename.
            traversal_upload = _FakeUploadFile("../../evil.mp4", b"video", "video/mp4")
            with Session(engine) as session:
                created = _run_coro_sync(routes.upload_meeting(file=traversal_upload, db=session))
            self.assertEqual(created["title"], "evil.mp4")
            saved_path = (root / created["video_path"]).resolve()
            self.assertTrue(saved_path.is_relative_to((root / "storage" / "uploads").resolve()))

            # Invalid filenames (null bytes, missing stem, empty name) are rejected with 400.
            for bad_name in ("", "   ", ".mp4", "evil\x00.mp4", "../"):
                bad_file = _FakeUploadFile(bad_name, b"video", "video/mp4")
                with Session(engine) as session, self.assertRaises(HTTPException) as name_ctx:
                    _run_coro_sync(routes.upload_meeting(file=bad_file, db=session))
                self.assertEqual(name_ctx.exception.status_code, 400)

            # Non-positive meeting IDs are rejected with 400 Bad Request.
            with Session(engine) as session:
                for invalid_id in (0, -1, -99):
                    with self.assertRaises(HTTPException) as id_ctx:
                        routes.get_meeting_detail(invalid_id, db=session)
                    self.assertEqual(id_ctx.exception.status_code, 400)

            # Storage path resolver blocks traversal, absolute paths, root storage dir, and null bytes.
            for unsafe_path in (
                "",
                "../outside.mp4",
                "storage/../../outside.mp4",
                "/etc/passwd",
                "C:/Windows/win.ini",
                "storage",
                "storage/uploads/bad\x00.mp4",
            ):
                with self.assertRaises(HTTPException) as path_ctx:
                    routes._resolve_storage_path(unsafe_path, "video")
                self.assertEqual(path_ctx.exception.status_code, 400)

    def test_extract_audio_success_and_error_cases(self) -> None:
        with self._temp_env() as (root, engine):
            with Session(engine) as session:
                missing_video_meeting = Meeting(
                    title="missing.mp4",
                    video_path="storage/uploads/does-not-exist.mp4",
                    status="uploaded",
                )
                traversal_meeting = Meeting(
                    title="bad.mp4",
                    video_path="../outside.mp4",
                    status="uploaded",
                )
                valid_video = root / "storage" / "uploads" / "valid.mp4"
                valid_video.write_bytes(b"mp4")
                valid_meeting = Meeting(
                    title="valid.mp4",
                    video_path="storage/uploads/valid.mp4",
                    status="uploaded",
                )
                session.add_all([missing_video_meeting, traversal_meeting, valid_meeting])
                session.commit()
                missing_id = missing_video_meeting.id
                traversal_id = traversal_meeting.id
                valid_id = valid_meeting.id

            with Session(engine) as session, self.assertRaises(HTTPException) as not_found_ctx:
                routes.extract_meeting_audio(99999, db=session)
            self.assertEqual(not_found_ctx.exception.status_code, 404)

            with Session(engine) as session, self.assertRaises(HTTPException) as traversal_ctx:
                routes.extract_meeting_audio(traversal_id, db=session)
            self.assertEqual(traversal_ctx.exception.status_code, 400)

            with Session(engine) as session, self.assertRaises(HTTPException) as missing_file_ctx:
                routes.extract_meeting_audio(missing_id, db=session)
            self.assertEqual(missing_file_ctx.exception.status_code, 422)
            with Session(engine) as session:
                self.assertEqual(session.get(Meeting, missing_id).status, "audio_failed")

            def fake_extract(_video_path, audio_path):
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"wav")

            with Session(engine) as session, patch("app.api.routes.extract_audio", side_effect=fake_extract):
                result = routes.extract_meeting_audio(valid_id, db=session)

            self.assertEqual(result["status"], "audio_ready")
            self.assertTrue((root / result["audio_path"]).is_file())

    def test_processing_and_retrieval_error_cases(self) -> None:
        with self._temp_env() as (root, engine):
            (root / "storage" / "audio" / "ready.wav").write_bytes(b"wav")
            with Session(engine) as session:
                uploaded_meeting = Meeting(
                    title="uploaded.mp4",
                    video_path="storage/uploads/u.mp4",
                    status="uploaded",
                )
                ready_meeting = Meeting(
                    title="ready.mp4",
                    video_path="storage/uploads/r.mp4",
                    audio_path="storage/audio/ready.wav",
                    status="audio_ready",
                )
                empty_completed = Meeting(
                    title="empty-completed.mp4",
                    video_path="storage/uploads/e.mp4",
                    audio_path="storage/audio/ready.wav",
                    status="completed",
                )
                session.add_all([uploaded_meeting, ready_meeting, empty_completed])
                session.commit()
                uploaded_id = uploaded_meeting.id
                ready_id = ready_meeting.id
                empty_completed_id = empty_completed.id

            # Invalid meeting IDs return 404 across endpoints.
            with Session(engine) as session:
                for fn in (
                    routes.get_meeting_detail,
                    routes.transcribe_meeting,
                    routes.diarize_meeting,
                    routes.align_meeting,
                    routes.get_meeting_transcript,
                ):
                    with self.assertRaises(HTTPException) as ctx:
                        fn(99999, db=session)
                    self.assertEqual(ctx.exception.status_code, 404)

            # Invalid workflow states return 409 Conflict.
            with Session(engine) as session:
                for fn in (routes.transcribe_meeting, routes.diarize_meeting, routes.align_meeting):
                    with self.assertRaises(HTTPException) as ctx:
                        fn(uploaded_id, db=session)
                    self.assertEqual(ctx.exception.status_code, 409)

            # Missing transcript segments for diarize/align return 422.
            with Session(engine) as session:
                for fn in (routes.diarize_meeting, routes.align_meeting):
                    with self.assertRaises(HTTPException) as ctx:
                        fn(empty_completed_id, db=session)
                    self.assertEqual(ctx.exception.status_code, 422)

            # Transcription failure marks meeting as failed and raises 422.
            with Session(engine) as session, patch(
                "app.api.routes.transcribe_audio",
                side_effect=TranscriptionError("corrupt audio"),
            ), self.assertRaises(HTTPException) as fail_ctx:
                routes.transcribe_meeting(ready_id, db=session)
            self.assertEqual(fail_ctx.exception.status_code, 422)
            with Session(engine) as session:
                failed_meeting = session.get(Meeting, ready_id)
                self.assertEqual(failed_meeting.status, "failed")
                failed_meeting.status = "audio_ready"
                session.commit()

            # Transcription success stores segments and transitions to completed.
            with Session(engine) as session, patch(
                "app.api.routes.transcribe_audio",
                return_value=[TranscribedSegment(start_time=0.0, end_time=1.0, text="Hello.")],
            ):
                transcribed = routes.transcribe_meeting(ready_id, db=session)
            self.assertEqual(transcribed["status"], "completed")
            self.assertEqual(transcribed["segments"][0]["speaker"], "Speaker 1")

    def test_stream_meeting_video_supports_range_requests_and_errors(self) -> None:
        with self._temp_env() as (root, engine):
            video_file = root / "storage" / "uploads" / "demo.mp4"
            video_file.write_bytes(b"0123456789")

            with Session(engine) as session:
                meeting = Meeting(
                    title="demo.mp4",
                    video_path="storage/uploads/demo.mp4",
                    status="uploaded",
                )
                missing_file_meeting = Meeting(
                    title="missing.mp4",
                    video_path="storage/uploads/missing.mp4",
                    status="uploaded",
                )
                traversal_meeting = Meeting(
                    title="bad.mp4",
                    video_path="../bad.mp4",
                    status="uploaded",
                )
                session.add_all([meeting, missing_file_meeting, traversal_meeting])
                session.commit()
                meeting_id = meeting.id
                missing_id = missing_file_meeting.id
                traversal_id = traversal_meeting.id

            # Full video response without Range header -> 200 OK.
            with Session(engine) as session:
                full_response = routes.stream_meeting_video(meeting_id, range_header=None, db=session)
            self.assertEqual(full_response.status_code, 200)
            self.assertEqual(full_response.media_type, "video/mp4")
            self.assertEqual(full_response.headers["accept-ranges"], "bytes")
            self.assertEqual(full_response.headers["content-length"], "10")
            self.assertEqual(b"".join(routes._iter_video_bytes(video_file, 0, 9)), b"0123456789")

            # Partial Range requests -> 206 Partial Content.
            with Session(engine) as session:
                head_range = routes.stream_meeting_video(meeting_id, range_header="bytes=0-3", db=session)
                tail_range = routes.stream_meeting_video(meeting_id, range_header="bytes=4-", db=session)
                suffix_range = routes.stream_meeting_video(meeting_id, range_header="bytes=-3", db=session)

            self.assertEqual(head_range.status_code, 206)
            self.assertEqual(head_range.headers["content-range"], "bytes 0-3/10")
            self.assertEqual(head_range.headers["content-length"], "4")
            self.assertEqual(b"".join(routes._iter_video_bytes(video_file, 0, 3)), b"0123")

            self.assertEqual(tail_range.status_code, 206)
            self.assertEqual(tail_range.headers["content-range"], "bytes 4-9/10")
            self.assertEqual(tail_range.headers["content-length"], "6")
            self.assertEqual(b"".join(routes._iter_video_bytes(video_file, 4, 9)), b"456789")

            self.assertEqual(suffix_range.status_code, 206)
            self.assertEqual(suffix_range.headers["content-range"], "bytes 7-9/10")
            self.assertEqual(suffix_range.headers["content-length"], "3")
            self.assertEqual(b"".join(routes._iter_video_bytes(video_file, 7, 9)), b"789")

            # Invalid Range headers -> 416 Range Not Satisfiable.
            with Session(engine) as session:
                for bad_range in ("bytes=100-200", "bytes=5-2", "items=0-3", "bytes=-"):
                    with self.assertRaises(HTTPException) as range_ctx:
                        routes.stream_meeting_video(meeting_id, range_header=bad_range, db=session)
                    self.assertEqual(range_ctx.exception.status_code, 416)
                    self.assertEqual(range_ctx.exception.headers["Content-Range"], "bytes */10")

            # Invalid ID, missing file on disk, and path traversal errors.
            with Session(engine) as session:
                with self.assertRaises(HTTPException) as not_found_ctx:
                    routes.stream_meeting_video(99999, range_header=None, db=session)
                self.assertEqual(not_found_ctx.exception.status_code, 404)

                with self.assertRaises(HTTPException) as missing_ctx:
                    routes.stream_meeting_video(missing_id, range_header=None, db=session)
                self.assertEqual(missing_ctx.exception.status_code, 404)

                with self.assertRaises(HTTPException) as traversal_ctx:
                    routes.stream_meeting_video(traversal_id, range_header=None, db=session)
                self.assertEqual(traversal_ctx.exception.status_code, 400)

    def test_swagger_openapi_schema_includes_all_required_endpoints(self) -> None:
        schema = app.openapi()
        self.assertEqual(schema["info"]["title"], "Meeting Transcriber API")
        self.assertEqual(schema["info"]["version"], "0.10.0")
        paths = schema["paths"]

        expected_endpoints = {
            "/",
            "/health",
            "/api/meetings/upload",
            "/api/meetings",
            "/api/meetings/{meeting_id}",
            "/api/meetings/{meeting_id}/video",
            "/api/meetings/{meeting_id}/video/stream",
            "/api/meetings/{meeting_id}/process",
            "/api/meetings/{meeting_id}/extract-audio",
            "/api/meetings/{meeting_id}/transcribe",
            "/api/meetings/{meeting_id}/diarize",
            "/api/meetings/{meeting_id}/align",
            "/api/meetings/{meeting_id}/transcript",
            "/api/meetings/{meeting_id}/transcript/processed",
        }
        self.assertTrue(expected_endpoints.issubset(set(paths.keys())))
        self.assertIn("get", paths["/api/meetings"])
        self.assertIn("get", paths["/api/meetings/{meeting_id}"])
        self.assertIn("post", paths["/api/meetings/upload"])
