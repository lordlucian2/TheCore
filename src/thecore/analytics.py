from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StudentSnapshot:
    student_id: str
    xp_total: int
    pomodoros: int


def predicted_grade(snapshot: StudentSnapshot) -> str:
    """Heuristic grade estimate used for monthly motivation loops."""

    score = snapshot.xp_total + (snapshot.pomodoros * 25)
    if score >= 1600:
        return "A1"
    if score >= 1200:
        return "B2"
    if score >= 800:
        return "B3"
    if score >= 500:
        return "C4"
    return "C6"


def monthly_pulse_ranking(snapshots: list[StudentSnapshot]) -> list[StudentSnapshot]:
    return sorted(
        snapshots,
        key=lambda snapshot: (snapshot.xp_total, snapshot.pomodoros),
        reverse=True,
    )
