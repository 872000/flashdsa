"""Interactive (or scripted) review session over due cards."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

from . import db as db_module

GRADE_HELP = (
    "5 perfect · 4 hesitant but correct · 3 correct with difficulty · "
    "2 wrong, answer looked familiar · 1 wrong, barely recalled · 0 blackout"
)


@dataclass
class SessionSummary:
    reviewed: int = 0
    grades: list[int] = field(default_factory=list)

    @property
    def average_quality(self) -> float:
        return sum(self.grades) / len(self.grades) if self.grades else 0.0

    @property
    def recall_rate(self) -> float:
        """Share of reviews graded 3+ (successful recall)."""
        if not self.grades:
            return 0.0
        return 100.0 * sum(1 for g in self.grades if g >= 3) / len(self.grades)


def _prompt_grade(card_no: int, total: int) -> int:
    while True:
        raw = input(f"  Grade your recall [{card_no}/{total}] (0-5): ").strip()
        if raw in {"0", "1", "2", "3", "4", "5"}:
            return int(raw)
        print("  Please enter a number 0-5.")


def run_session(
    conn: sqlite3.Connection,
    grades: list[int] | None = None,
    limit: int | None = None,
    today: date | None = None,
) -> SessionSummary:
    """Run one review session over due cards.

    Args:
        conn: open database connection.
        grades: scripted grades for non-interactive runs (e.g. demos/tests).
            When None, the session is interactive.
        limit: max cards to review this session.
        today: review date; defaults to today.

    Returns:
        SessionSummary with counts and grades.
    """
    today = today or date.today()
    due = db_module.due_cards(conn, today=today, limit=limit)
    scripted = list(grades) if grades is not None else None
    summary = SessionSummary()
    total = len(due)

    if total == 0:
        print("No cards due — you're all caught up! 🎉")
        return summary

    print(f"\n{total} card{'s' if total != 1 else ''} due for review.\n")
    for i, row in enumerate(due, start=1):
        print(f"[{i}/{total}] [{row['topic']}] ({row['difficulty']})")
        print(f"  Q: {row['prompt']}")
        if scripted is None:
            input("  Press Enter to reveal the answer… ")
        print(f"  A: {row['answer']}")

        if scripted is None:
            print(f"  {GRADE_HELP}")
            grade = _prompt_grade(i, total)
        else:
            grade = scripted.pop(0) if scripted else 3
            print(f"  Grade: {grade}")

        result = db_module.record_review(conn, row["id"], grade, today=today)
        summary.reviewed += 1
        summary.grades.append(grade)
        print(f"  → next review in {result.state.interval_days} day(s) (EF {result.state.easiness:.2f})\n")

    print("—" * 48)
    print(f"Session complete: {summary.reviewed} reviewed · "
          f"avg quality {summary.average_quality:.1f}/5 · "
          f"recall {summary.recall_rate:.0f}%")
    return summary
