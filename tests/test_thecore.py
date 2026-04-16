from datetime import datetime, timedelta, timezone
import unittest

from src.thecore.analytics import StudentSnapshot, monthly_pulse_ranking, predicted_grade
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

    def test_duplicate_nonce_is_rejected(self) -> None:
        base_event = StudyEvent(
            student_id=self.student.student_id,
            kind="xp",
            value=100,
            started_at=self.now - timedelta(minutes=20),
            ended_at=self.now - timedelta(minutes=10),
            nonce="nonce-1",
        )
        self.engine.record(base_event)

        replay = StudyEvent(
            student_id=self.student.student_id,
            kind="xp",
            value=100,
            started_at=self.now - timedelta(minutes=20),
            ended_at=self.now - timedelta(minutes=10),
            nonce="nonce-1",
        )
        with self.assertRaises(ValueError):
            self.engine.record(replay)

    def test_sync_batch_acknowledge(self) -> None:
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

        batch = self.engine.create_sync_batch(self.student.student_id)
        aggregate = self.engine.acknowledge_batch(batch)
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

    def test_quests_dashboard_and_predictions(self) -> None:
        quests = generate_tutorial_quests()
        self.assertEqual(len(quests), 3)

        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="xp",
                value=1000,
                started_at=self.now - timedelta(minutes=30),
                ended_at=self.now - timedelta(minutes=20),
                nonce="pulse-1",
            )
        )
        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="pomodoro",
                value=10,
                started_at=self.now - timedelta(minutes=19),
                ended_at=self.now - timedelta(minutes=1),
                nonce="pulse-2",
            )
        )

        dashboard = SquadDashboard(self.engine)
        pulse = dashboard.pulse([self.student])

        self.assertEqual(pulse[self.student.student_id]["xp_total"], 1000)
        self.assertEqual(pulse[self.student.student_id]["pending_events"], 2)
        self.assertEqual(pulse[self.student.student_id]["predicted_grade"], "B2")

    def test_monthly_ranking(self) -> None:
        snapshots = [
            StudentSnapshot(student_id="a", xp_total=500, pomodoros=5),
            StudentSnapshot(student_id="b", xp_total=900, pomodoros=1),
            StudentSnapshot(student_id="c", xp_total=900, pomodoros=4),
        ]
        ranked = monthly_pulse_ranking(snapshots)
        self.assertEqual([entry.student_id for entry in ranked], ["c", "b", "a"])
        self.assertEqual(predicted_grade(ranked[0]), "B3")


if __name__ == "__main__":
    unittest.main()
