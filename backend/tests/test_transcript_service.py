"""Unit and SQLite integration tests for the Part 9 transcript processing service."""

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import routes
from app.database import Base
from app.models import Meeting, TranscriptSegment, TranscriptWord
from app.services.transcript import (
    clean_transcript_text,
    format_timestamp,
    normalize_speaker_label,
    process_transcript_segments,
)


class TranscriptServiceTestCase(unittest.TestCase):
    @contextmanager
    def _sqlite_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir) / 'test.db'}")
            try:
                Base.metadata.create_all(engine)
                yield engine
            finally:
                engine.dispose()

    def test_cleans_whitespace_and_punctuation_without_changing_words(self) -> None:
        raw = "  Good   morning\teveryone  ! \n Let's   begin ,  please . "
        self.assertEqual(
            clean_transcript_text(raw),
            "Good morning everyone! Let's begin, please.",
        )
        self.assertEqual(clean_transcript_text("   \n\t  "), "")
        self.assertEqual(normalize_speaker_label("  "), "Speaker 1")
        self.assertEqual(normalize_speaker_label(" Speaker   2 "), "Speaker 2")
        self.assertEqual(format_timestamp(65.9), "00:01:05")

    def test_orders_chronologically_and_groups_consecutive_same_speaker(self) -> None:
        segments = [
            SimpleNamespace(
                id=3,
                speaker="Speaker 1",
                start_time=8.0,
                end_time=10.0,
                text="Thanks   again .",
                words=[],
            ),
            SimpleNamespace(
                id=2,
                speaker="Speaker 2",
                start_time=4.5,
                end_time=7.5,
                text="Morning !",
                words=[],
            ),
            SimpleNamespace(
                id=1,
                speaker="Speaker 1",
                start_time=0.5,
                end_time=2.0,
                text="Good   morning ,",
                words=[
                    SimpleNamespace(id=12, word="morning,", start_time=1.1, end_time=1.9),
                    SimpleNamespace(id=11, word=" Good ", start_time=0.5, end_time=1.0),
                ],
            ),
            SimpleNamespace(
                id=4,
                speaker="Speaker 1",
                start_time=2.1,
                end_time=4.0,
                text="everyone .",
                words=[
                    SimpleNamespace(id=13, word="everyone.", start_time=2.2, end_time=3.9),
                ],
            ),
        ]

        processed = process_transcript_segments(segments)

        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0].speaker, "Speaker 1")
        self.assertEqual(processed[0].segment_ids, [1, 4])
        self.assertEqual(processed[0].start_time, 0.5)
        self.assertEqual(processed[0].end_time, 4.0)
        self.assertEqual(processed[0].formatted_timestamp, "00:00:00")
        self.assertEqual(processed[0].text, "Good morning, everyone.")
        self.assertEqual(
            [(w.word, w.start_time, w.end_time) for w in processed[0].words],
            [
                ("Good", 0.5, 1.0),
                ("morning,", 1.1, 1.9),
                ("everyone.", 2.2, 3.9),
            ],
        )

        self.assertEqual(processed[1].speaker, "Speaker 2")
        self.assertEqual(processed[1].text, "Morning!")
        self.assertEqual(processed[1].words, [])

        self.assertEqual(processed[2].speaker, "Speaker 1")
        self.assertEqual(processed[2].segment_ids, [3])
        self.assertEqual(processed[2].text, "Thanks again.")

    def test_handles_missing_speaker_and_skips_empty_segments(self) -> None:
        segments = [
            SimpleNamespace(id=1, speaker="", start_time=0.0, end_time=1.0, text="   ", words=[]),
            SimpleNamespace(id=2, speaker=None, start_time=1.0, end_time=2.5, text="Hello   world", words=[]),
            SimpleNamespace(id=3, speaker="  ", start_time=2.6, end_time=4.0, text="Second line", words=[]),
        ]

        processed = process_transcript_segments(segments)

        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0].speaker, "Speaker 1")
        self.assertEqual(processed[0].text, "Hello world Second line")
        self.assertEqual(processed[0].segment_ids, [2, 3])

    def test_route_returns_processed_transcript_without_mutating_sqlite_rows(self) -> None:
        with self._sqlite_session() as engine:
            with Session(engine) as session:
                meeting = Meeting(
                    title="standup.mp4",
                    video_path="storage/uploads/standup.mp4",
                    status="completed",
                    transcript_segments=[
                        TranscriptSegment(
                            speaker="Speaker 1",
                            start_time=0.0,
                            end_time=1.2,
                            text="  Hello   team , ",
                            words=[
                                TranscriptWord(word="Hello", start_time=0.0, end_time=0.5),
                                TranscriptWord(word="team,", start_time=0.6, end_time=1.2),
                            ],
                        ),
                        TranscriptSegment(
                            speaker="Speaker 1",
                            start_time=1.3,
                            end_time=2.5,
                            text="let's   start .",
                            words=[
                                TranscriptWord(word="let's", start_time=1.3, end_time=1.8),
                                TranscriptWord(word="start.", start_time=1.9, end_time=2.5),
                            ],
                        ),
                        TranscriptSegment(
                            speaker="Speaker 2",
                            start_time=3.0,
                            end_time=4.2,
                            text="Sounds   good !",
                            words=[],
                        ),
                    ],
                )
                session.add(meeting)
                session.commit()
                meeting_id = meeting.id

            with Session(engine) as session:
                payload = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(payload["id"], meeting_id)
            self.assertEqual(payload["title"], "standup.mp4")
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["segment_count"], 2)
            self.assertEqual(payload["speaker_count"], 2)
            self.assertEqual(payload["segments"][0]["speaker"], "Speaker 1")
            self.assertEqual(payload["segments"][0]["start_time"], 0.0)
            self.assertEqual(payload["segments"][0]["end_time"], 2.5)
            self.assertEqual(payload["segments"][0]["formatted_timestamp"], "00:00:00")
            self.assertEqual(payload["segments"][0]["text"], "Hello team, let's start.")
            self.assertEqual(
                [word["word"] for word in payload["segments"][0]["words"]],
                ["Hello", "team,", "let's", "start."],
            )
            self.assertEqual(payload["segments"][1]["text"], "Sounds good!")

            # Verify raw database rows were not overwritten.
            with Session(engine) as session:
                saved_meeting = session.get(Meeting, meeting_id)
                self.assertIsNotNone(saved_meeting)
                assert saved_meeting is not None
                self.assertEqual(len(saved_meeting.transcript_segments), 3)
                self.assertEqual(saved_meeting.transcript_segments[0].text, "  Hello   team , ")

    def test_route_handles_meeting_with_empty_transcript(self) -> None:
        with self._sqlite_session() as engine:
            with Session(engine) as session:
                meeting = Meeting(
                    title="empty.mp4",
                    video_path="storage/uploads/empty.mp4",
                    status="uploaded",
                )
                session.add(meeting)
                session.commit()
                meeting_id = meeting.id

            with Session(engine) as session:
                payload = routes.get_meeting_transcript(meeting_id, db=session)

            self.assertEqual(payload["id"], meeting_id)
            self.assertEqual(payload["segment_count"], 0)
            self.assertEqual(payload["speaker_count"], 0)
            self.assertEqual(payload["segments"], [])

    def test_registers_transcript_and_processed_routes(self) -> None:
        paths = {getattr(route, "path", None) for route in routes.router.routes}
        self.assertIn("/api/meetings/{meeting_id}/transcript", paths)
        self.assertIn("/api/meetings/{meeting_id}/transcript/processed", paths)
