from datetime import datetime, timedelta, timezone
import unittest

from src.thecore.engine import LocalSyncEngine, StudyEvent, StudentProfile
from src.thecore.quests import generate_tutorial_quests
from src.thecore.squad import SquadDashboard


class TheCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = LocalSyncEngine()
        self.now = datetime.now(tz=timezone.utc)
        self.student = StudentProfile(
            student_id="st_001", display_name="Lucian", school="Southbridge"
        )

    def test_record_and_ghost_snapshot(self) -> None:
        event = StudyEvent(
            student_id=self.student.student_id,
            kind="pomodoro",
            value=2,
            started_at=self.now - timedelta(minutes=50),
            ended_at=self.now - timedelta(minutes=1),
            nonce="abc",
        )

        signature = self.engine.record(event)
        self.assertEqual(len(signature), 64)

        ghost = self.engine.ghost_for(self.student)
        self.assertIsNotNone(ghost)
        self.assertIn("was active", ghost.summary)

    def test_burst_sync_clears_events(self) -> None:
        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="xp",
                value=120,
                started_at=self.now - timedelta(minutes=20),
                ended_at=self.now - timedelta(minutes=10),
                nonce="1",
            )
        )
        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="pomodoro",
                value=3,
                started_at=self.now - timedelta(minutes=10),
                ended_at=self.now - timedelta(minutes=2),
                nonce="2",
            )
        )

        aggregate = self.engine.burst_sync(self.student.student_id)
        self.assertEqual(aggregate["xp_total"], 120)
        self.assertEqual(aggregate["pomodoros"], 3)
        self.assertEqual(aggregate["count"], 2)
        self.assertEqual(self.engine.pending_events(self.student.student_id), [])

    def test_duration_validation(self) -> None:
        bad_event = StudyEvent(
            student_id=self.student.student_id,
            kind="xp",
            value=10,
            started_at=self.now - timedelta(hours=4),
            ended_at=self.now,
            nonce="too-long",
        )
        with self.assertRaises(ValueError):
            self.engine.record(bad_event)

    def test_quests_and_dashboard(self) -> None:
        quests = generate_tutorial_quests()
        self.assertEqual(len(quests), 3)

        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="xp",
                value=200,
                started_at=self.now - timedelta(minutes=30),
                ended_at=self.now - timedelta(minutes=20),
                nonce="pulse",
            )
        )
        dashboard = SquadDashboard(self.engine)
        pulse = dashboard.pulse([self.student])

        self.assertEqual(pulse[self.student.student_id]["xp_total"], 200)
        self.assertEqual(pulse[self.student.student_id]["pending_events"], 1)


if __name__ == "__main__":
    unittest.main()
