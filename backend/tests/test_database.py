"""Focused tests for the Part 3 SQLite setup."""

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Meeting, TranscriptSegment


class DatabaseTestCase(unittest.TestCase):
    def test_creates_tables_and_persists_meeting_with_segments(self) -> None:
        """Verify SQLite table creation and the meeting/segment relationship."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.db"
            engine = create_engine(f"sqlite:///{database_path}")
            Base.metadata.create_all(engine)

            self.assertTrue({"meetings", "transcript_segments"}.issubset(inspect(engine).get_table_names()))

            with Session(engine) as session:
                meeting = Meeting(
                    title="Project update",
                    video_path="storage/originals/project-update.mp4",
                    duration=42.5,
                    status="pending",
                    transcript_segments=[
                        TranscriptSegment(
                            speaker="Speaker 1",
                            start_time=0.0,
                            end_time=3.2,
                            text="Welcome to the project update.",
                        ),
                        TranscriptSegment(
                            speaker="Speaker 2",
                            start_time=3.3,
                            end_time=5.0,
                            text="Thank you.",
                        ),
                    ],
                )
                session.add(meeting)
                session.commit()
                meeting_id = meeting.id

            with Session(engine) as session:
                saved_meeting = session.get(Meeting, meeting_id)
                self.assertIsNotNone(saved_meeting)
                assert saved_meeting is not None
                self.assertEqual(saved_meeting.title, "Project update")
                self.assertEqual(len(saved_meeting.transcript_segments), 2)
                self.assertEqual(saved_meeting.transcript_segments[0].speaker, "Speaker 1")

            engine.dispose()
