from __future__ import annotations

from dataclasses import dataclass

from .engine import LocalSyncEngine, StudentProfile


@dataclass(slots=True)
class SquadDashboard:
    """Simple aggregate metrics for teacher/guild-master visibility."""

    engine: LocalSyncEngine

    def pulse(self, students: list[StudentProfile]) -> dict[str, dict[str, int | str]]:
        result: dict[str, dict[str, int | str]] = {}

        for student in students:
            events = self.engine.pending_events(student.student_id)
            xp_total = sum(event.value for event in events if event.kind == "xp")
            pomodoros = sum(event.value for event in events if event.kind == "pomodoro")
            snapshot = StudentSnapshot(
                student_id=student.student_id,
                xp_total=xp_total,
                pomodoros=pomodoros,
            )
            result[student.student_id] = {
                "name": student.display_name,
                "xp_total": xp_total,
                "pomodoros": pomodoros,
                "pending_events": len(events),
                "predicted_grade": predicted_grade(snapshot),
            }

        return result
