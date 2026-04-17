from datetime import datetime, timedelta, timezone
import unittest

from src.thecore.analytics import StudentSnapshot, monthly_pulse_ranking, predicted_grade
from src.thecore.engine import LocalSyncEngine, StudyEvent, StudentProfile
from src.thecore.ai import AIQuery, AIResponse, AIResponseMode, ClutchAI
from src.thecore.quests import generate_tutorial_quests
from src.thecore.room import PresenceState, RoomTimer, StudyRoom
from src.thecore.service import TheCoreService
from src.thecore.session import RoomType, StudySession
from src.thecore.squad import SquadDashboard
from src.thecore.storage import SQLiteAIStore, SQLiteEventStore, SQLiteRoomStore, SQLiteStudentStore, SQLiteVaultStore
from src.thecore.vault import VaultResource


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
        self.assertEqual(pulse[self.student.student_id]["rank_tier"], "Gold")
        self.assertEqual(pulse[self.student.student_id]["streak"], 1)

    def test_streak_for_consecutive_days(self) -> None:
        yesterday = self.now - timedelta(days=1)
        day_before = self.now - timedelta(days=2)

        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="xp",
                value=50,
                started_at=day_before - timedelta(minutes=30),
                ended_at=day_before - timedelta(minutes=5),
                nonce="streak-1",
            )
        )
        self.engine.record(
            StudyEvent(
                student_id=self.student.student_id,
                kind="pomodoro",
                value=1,
                started_at=yesterday - timedelta(minutes=30),
                ended_at=yesterday - timedelta(minutes=5),
                nonce="streak-2",
            )
        )

        self.assertEqual(self.engine.streak_for(self.student.student_id, as_of=self.now), 2)

    def test_vault_store_persistence(self) -> None:
        store = SQLiteVaultStore()
        resource = VaultResource(
            resource_id="res_1",
            author_id=self.student.student_id,
            title="Study Notes on Algebra",
            subject="Mathematics",
            description="A quick guide to equations.",
            tags=["algebra", "revision"],
            content_url="https://example.com/notes",
        )

        store.add(resource)
        loaded = store.load(resource_id="res_1")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].title, "Study Notes on Algebra")

        score = store.vote("res_1", upvote=True)
        self.assertEqual(score, 1)
        store.close()

    def test_student_store_persistence(self) -> None:
        store = SQLiteStudentStore()
        store.add(self.student)

        loaded = store.load(self.student.student_id)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].display_name, "Lucian")

        updated_profile = StudentProfile(
            student_id=self.student.student_id,
            display_name="Lucian Vale",
            school="Southbridge High",
        )
        store.update(updated_profile)
        reloaded = store.load(self.student.student_id)
        self.assertEqual(reloaded[0].display_name, "Lucian Vale")
        store.close()

    def test_ai_store_logging(self) -> None:
        store = SQLiteAIStore()
        query = AIQuery(
            query_id="q1",
            student_id=self.student.student_id,
            subject="Biology",
            prompt="Explain cell division.",
            mode=AIResponseMode.HINT,
        )
        response = AIResponse(
            query_id="q1",
            mode=AIResponseMode.HINT,
            text="Try breaking the problem into smaller parts.",
        )

        store.append_query(query)
        store.append_response(response)

        queries = store.load_queries(self.student.student_id)
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0].query_id, "q1")

        responses = store.load_responses("q1")
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].text, "Try breaking the problem into smaller parts.")
        store.close()

    def test_vault_and_ai_service_integration(self) -> None:
        event_store = SQLiteEventStore()
        vault_store = SQLiteVaultStore()
        ai_store = SQLiteAIStore()
        service = TheCoreService.from_store(event_store, vault_store=vault_store, ai_store=ai_store)

        resource = VaultResource(
            resource_id="res_2",
            author_id=self.student.student_id,
            title="History Revision Sheet",
            subject="History",
            description="Key events for exam prep.",
            tags=["history", "revision"],
        )
        service.record_resource(resource)
        loaded = service.load_resources(resource_id="res_2")
        self.assertEqual(len(loaded), 1)

        query = AIQuery(
            query_id="q2",
            student_id=self.student.student_id,
            subject="Biology",
            prompt="Explain cell division.",
            mode=AIResponseMode.HINT,
        )
        response = AIResponse(
            query_id="q2",
            mode=AIResponseMode.HINT,
            text="Try breaking the problem into smaller parts.",
        )
        service.log_ai_query(query)
        service.log_ai_response(response)

        self.assertEqual(len(service.load_ai_queries(self.student.student_id)), 1)
        self.assertEqual(len(service.load_ai_responses("q2")), 1)

        vault_store.close()
        ai_store.close()
        resource = VaultResource(
            resource_id="res_1",
            author_id=self.student.student_id,
            title="Study Notes on Algebra",
            subject="Mathematics",
            description="A quick guide to equations.",
            tags=["algebra", "revision"],
            content_url="https://example.com/notes",
        )

        resource.vote(True)
        resource.vote(True)
        resource.vote(False)
        resource.add_tags(["exam", "revision"])

        self.assertEqual(resource.upvotes, 2)
        self.assertEqual(resource.downvotes, 1)
        self.assertEqual(resource.score(), 1)
        self.assertIn("exam", resource.tags)
        self.assertEqual(resource.tags.count("revision"), 1)

    def test_clutch_ai_response_modes(self) -> None:
        ai = ClutchAI()
        query = AIQuery(
            query_id="q1",
            student_id=self.student.student_id,
            subject="Biology",
            prompt="Explain cell division.",
            mode=AIResponseMode.HINT,
        )
        response = ai.generate_response(query)

        self.assertEqual(response.mode, AIResponseMode.HINT)
        self.assertIn("Try breaking the problem", response.text)
        self.assertEqual(response.metadata["mode"], "hint")

        step_query = AIQuery(
            query_id="q2",
            student_id=self.student.student_id,
            subject="Biology",
            prompt="Explain cell division.",
            mode=AIResponseMode.STEP_BY_STEP,
        )
        step_response = ai.generate_response(step_query)
        self.assertEqual(step_response.mode, AIResponseMode.STEP_BY_STEP)
        self.assertIn("step", step_response.text)

    def test_room_presence_ghosts_and_timer(self) -> None:
        other = StudentProfile(
            student_id="st_002",
            display_name="Nia",
            school="Southbridge",
        )

        event = StudyEvent(
            student_id=other.student_id,
            kind="pomodoro",
            value=2,
            started_at=self.now - timedelta(minutes=50),
            ended_at=self.now - timedelta(minutes=10),
            nonce="ghost-1",
        )
        self.engine.record(event)

        room = StudyRoom(room_id="room-1", room_type=RoomType.GROUP)
        room.update_presence(self.student.student_id, PresenceState.FOCUSING, self.now - timedelta(minutes=5))
        room.update_presence(other.student_id, PresenceState.OFFLINE, self.now - timedelta(minutes=20))

        ghosts = room.offline_ghosts([self.student, other], self.engine)
        self.assertEqual(len(ghosts), 1)
        self.assertEqual(ghosts[0].student_id, other.student_id)
        self.assertIn("was active", ghosts[0].summary)

        timer = RoomTimer(cycle_type="focus", duration_seconds=1500, started_at=self.now - timedelta(minutes=5))
        self.assertTrue(timer.is_active(self.now))
        self.assertEqual(timer.remaining_seconds(self.now), 1200)

    def test_room_store_persistence(self) -> None:
        room = StudyRoom(
            room_id="room_1",
            room_type=RoomType.GROUP,
            participant_ids={self.student.student_id},
            presence={self.student.student_id: PresenceState.FOCUSING},
            last_seen_at={self.student.student_id: self.now},
            ambient_mode="lofi",
            timer=RoomTimer(cycle_type="focus", duration_seconds=1500, started_at=self.now - timedelta(minutes=5)),
        )
        store = SQLiteRoomStore()
        store.add(room)
        loaded = store.load("room_1")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.room_id, "room_1")
        self.assertEqual(loaded.room_type, RoomType.GROUP)
        self.assertEqual(loaded.presence[self.student.student_id], PresenceState.FOCUSING)
        store.close()

    def test_room_service_integration(self) -> None:
        event_store = SQLiteEventStore()
        student_store = SQLiteStudentStore()
        room_store = SQLiteRoomStore()
        service = TheCoreService.from_store(
            event_store,
            room_store=room_store,
            student_store=student_store,
        )

        room = StudyRoom(
            room_id="room_2",
            room_type=RoomType.GROUP,
            participant_ids={self.student.student_id},
            presence={self.student.student_id: PresenceState.FOCUSING},
            last_seen_at={self.student.student_id: self.now},
            ambient_mode="lofi",
        )
        service.create_room(room)
        service.record_student(self.student)
        loaded = service.load_room("room_2")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.room_id, "room_2")

        room.update_presence(self.student.student_id, PresenceState.BREAK, self.now)
        service.update_room(room)
        updated = service.load_room("room_2")
        self.assertEqual(updated.presence[self.student.student_id], PresenceState.BREAK)

        student_profiles = service.load_student(self.student.student_id)
        self.assertEqual(len(student_profiles), 1)
        self.assertEqual(student_profiles[0].display_name, "Lucian")

        room_store.close()
        event_store.close()
        student_store.close()

    def test_study_session_xp_formula(self) -> None:
        session = StudySession(
            session_id="s1",
            student_id=self.student.student_id,
            room_type=RoomType.SOLO,
            started_at=self.now - timedelta(minutes=30),
            ended_at=self.now,
            completed_pomodoros=1,
            is_first_session_of_day=True,
        )

        solo_xp = self.engine.session_xp(session)
        self.assertGreater(solo_xp, 30)
        self.assertEqual(solo_xp, 30 + 50 + 25)

        group_session = StudySession(
            session_id="s2",
            student_id=self.student.student_id,
            room_type=RoomType.GROUP,
            started_at=self.now - timedelta(minutes=30),
            ended_at=self.now,
            completed_pomodoros=1,
            is_first_session_of_day=True,
        )
        group_xp = self.engine.session_xp(group_session)
        self.assertEqual(group_xp, 112)
        self.assertGreater(group_xp, solo_xp)

    def test_monthly_ranking(self) -> None:
        snapshots = [
            StudentSnapshot(student_id="a", xp_total=500, pomodoros=5),
            StudentSnapshot(student_id="b", xp_total=900, pomodoros=1),
            StudentSnapshot(student_id="c", xp_total=900, pomodoros=4),
        ]
        ranked = monthly_pulse_ranking(snapshots)
        self.assertEqual([entry.student_id for entry in ranked], ["c", "b", "a"])
        self.assertEqual(predicted_grade(ranked[0]), "B3")

    def test_service_persists_and_acknowledges(self) -> None:
        store = SQLiteEventStore()
        service = TheCoreService.from_store(store)

        event = StudyEvent(
            student_id=self.student.student_id,
            kind="xp",
            value=250,
            started_at=self.now - timedelta(minutes=15),
            ended_at=self.now - timedelta(minutes=5),
            nonce="service-1",
        )
        service.record_event(event)
        self.assertEqual(len(store.load(self.student.student_id)), 1)

        recovered = TheCoreService.from_store(store)
        batch = recovered.create_batch(self.student.student_id)
        aggregate = recovered.acknowledge_batch(batch)

        self.assertEqual(aggregate["xp_total"], 250)
        self.assertEqual(len(store.load(self.student.student_id)), 0)
        store.close()


if __name__ == "__main__":
    unittest.main()
