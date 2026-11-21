"""Integration tests for the Part 4 upload endpoint."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import database
from app.api import routes
from app.database import Base, SessionLocal
from app.main import app
from app.models import Meeting, TranscriptSegment
from app.services.transcription import TranscribedSegment
from app.services.diarization import SpeakerTurn


class UploadEndpointTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "uploads.db"
        self.upload_directory = Path(self.temp_dir.name) / "uploads"
        self.original_engine = database.engine
        self.original_project_root = routes.PROJECT_ROOT
        self.original_audio_directory = routes.AUDIO_DIRECTORY
        self.original_upload_directory = routes.UPLOAD_DIRECTORY
        self.engine = create_engine(f"sqlite:///{self.database_path}", connect_args={"check_same_thread": False})
        database.engine = self.engine
        SessionLocal.configure(bind=self.engine)
        Base.metadata.create_all(self.engine)
        routes.PROJECT_ROOT = Path(self.temp_dir.name)
        routes.UPLOAD_DIRECTORY = self.upload_directory
        routes.AUDIO_DIRECTORY = Path(self.temp_dir.name) / "audio"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        database.engine = self.original_engine
        SessionLocal.configure(bind=self.original_engine)
        routes.PROJECT_ROOT = self.original_project_root
        routes.AUDIO_DIRECTORY = self.original_audio_directory
        routes.UPLOAD_DIRECTORY = self.original_upload_directory
        self.temp_dir.cleanup()

    def test_successful_upload_creates_meeting_and_file(self) -> None:
        response = self.client.post(
            "/api/meetings/upload", files={"file": ("meeting.mp4", b"video bytes", "video/mp4")}
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["title"], "meeting.mp4")
        self.assertEqual(body["status"], "uploaded")
        self.assertTrue((Path(self.temp_dir.name) / body["video_path"]).is_file())

    def test_rejects_unsupported_type(self) -> None:
        response = self.client.post(
            "/api/meetings/upload", files={"file": ("notes.txt", b"not a video", "text/plain")}
        )

        self.assertEqual(response.status_code, 415)
        self.assertIn("MP4, WebM, or MOV", response.json()["detail"])

    def test_rejects_empty_file(self) -> None:
        response = self.client.post(
            "/api/meetings/upload", files={"file": ("empty.mp4", b"", "video/mp4")}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Uploaded video file is empty.")

    def test_rejects_file_over_size_limit(self) -> None:
        original_limit = routes.MAX_UPLOAD_BYTES
        routes.MAX_UPLOAD_BYTES = 4
        try:
            response = self.client.post(
                "/api/meetings/upload", files={"file": ("large.mov", b"12345", "video/quicktime")}
            )
        finally:
            routes.MAX_UPLOAD_BYTES = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertIn("500 MB", response.json()["detail"])

    def test_audio_extraction_updates_meeting(self) -> None:
        source_video = self.upload_directory / "source.mp4"
        self.upload_directory.mkdir(parents=True)
        source_video.write_bytes(b"video")
        with SessionLocal() as session:
            meeting = Meeting(title="source.mp4", video_path="uploads/source.mp4", status="uploaded")
            session.add(meeting)
            session.commit()
            meeting_id = meeting.id

        def fake_extract(_video_path, audio_path):
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(b"wav")

        with patch("app.api.routes.extract_audio", side_effect=fake_extract):
            response = self.client.post(f"/api/meetings/{meeting_id}/extract-audio")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "audio_ready")
        self.assertTrue((Path(self.temp_dir.name) / response.json()["audio_path"]).is_file())

    def test_transcription_persists_timestamped_segments(self) -> None:
        audio_directory = Path(self.temp_dir.name) / "audio"
        audio_directory.mkdir()
        (audio_directory / "input.wav").write_bytes(b"wav")
        with SessionLocal() as session:
            meeting = Meeting(
                title="meeting.mp4",
                video_path="uploads/meeting.mp4",
                audio_path="audio/input.wav",
                status="audio_ready",
            )
            session.add(meeting)
            session.commit()
            meeting_id = meeting.id

        fake_segments = [TranscribedSegment(start_time=0.0, end_time=1.25, text="Hello everyone.")]
        with patch("app.api.routes.transcribe_audio", return_value=fake_segments):
            response = self.client.post(f"/api/meetings/{meeting_id}/transcribe")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["segments"][0]["speaker"], "Speaker 1")
        self.assertEqual(body["segments"][0]["start_time"], 0.0)
        self.assertEqual(body["segments"][0]["end_time"], 1.25)

        with SessionLocal() as session:
            saved_meeting = session.get(Meeting, meeting_id)
            self.assertEqual(saved_meeting.status, "completed")
            self.assertEqual(len(saved_meeting.transcript_segments), 1)

    def test_diarization_updates_transcript_speakers(self) -> None:
        audio_directory = Path(self.temp_dir.name) / "audio"
        audio_directory.mkdir()
        (audio_directory / "input.wav").write_bytes(b"wav")
        with SessionLocal() as session:
            meeting = Meeting(
                title="meeting.mp4",
                video_path="uploads/meeting.mp4",
                audio_path="audio/input.wav",
                status="completed",
                transcript_segments=[
                    TranscriptSegment(speaker="Speaker 1", start_time=0.0, end_time=1.0, text="First."),
                    TranscriptSegment(speaker="Speaker 1", start_time=1.0, end_time=2.0, text="Second."),
                ],
            )
            session.add(meeting)
            session.commit()
            meeting_id = meeting.id

        turns = [
            SpeakerTurn(speaker="Speaker 1", start_time=0.0, end_time=0.8),
            SpeakerTurn(speaker="Speaker 2", start_time=0.8, end_time=2.0),
        ]
        with patch("app.api.routes.diarize_audio", return_value=turns):
            response = self.client.post(f"/api/meetings/{meeting_id}/diarize")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["speaker"] for item in response.json()["segments"]], ["Speaker 1", "Speaker 2"])
