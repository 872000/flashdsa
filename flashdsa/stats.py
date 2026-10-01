"""Review statistics: topic mastery, 7-day forecast, review heatmap."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from . import sm2

# A card counts as "learned" once it has survived at least two successful
# reviews and its easiness factor is comfortably above the SM-2 floor.
LEARNED_MIN_REPETITIONS = 2
LEARNED_MIN_EASINESS = 2.0


@dataclass(frozen=True)
class TopicMastery:
    topic: str
    total: int
    learned: int

    @property
    def percent(self) -> float:
        return 100.0 * self.learned / self.total if self.total else 0.0


def mastery_by_topic(conn: sqlite3.Connection) -> list[TopicMastery]:
    """Per-topic mastery, topics ordered by first card appearance."""
    topic_order: list[str] = []
    buckets: dict[str, list[sqlite3.Row]] = {}
    for row in conn.execute("SELECT * FROM cards ORDER BY rowid"):
        buckets.setdefault(row["topic"], []).append(row)
        if row["topic"] not in topic_order:
            topic_order.append(row["topic"])

    stats: list[TopicMastery] = []
    for topic in topic_order:
        rows = buckets[topic]
        learned = sum(
            1
            for r in rows
            if r["repetitions"] >= LEARNED_MIN_REPETITIONS
            and r["easiness"] >= LEARNED_MIN_EASINESS
        )
        stats.append(TopicMastery(topic=topic, total=len(rows), learned=learned))
    return stats


def forecast(conn: sqlite3.Connection, days: int = 7, today: date | None = None) -> list[tuple[date, int]]:
    """For each of the next `days` days: how many cards are due that day.

    Uses each card's *own* next_review date, so cards already scheduled
    further out land on the right day instead of piling onto day 0.
    Overdue cards (next_review in the past) are counted on day 0.
    """
    today = today or date.today()
    next_reviews = [row["next_review"] for row in conn.execute("SELECT next_review FROM cards")]

    result: list[tuple[date, int]] = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        iso = day.isoformat()
        if offset == 0:
            count = sum(1 for nr in next_reviews if nr <= iso)
        else:
            count = sum(1 for nr in next_reviews if nr == iso)
        result.append((day, count))
    return result


def heatmap(conn: sqlite3.Connection, days: int = 90, today: date | None = None) -> dict[date, int]:
    """Reviews per calendar day for the last `days` days (heatmap source)."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    counts: dict[date, int] = {start + timedelta(days=i): 0 for i in range(days)}
    for row in conn.execute(
        "SELECT reviewed_at, COUNT(*) AS n FROM reviews WHERE reviewed_at >= ? GROUP BY reviewed_at",
        (start.isoformat(),),
    ):
        counts[date.fromisoformat(row["reviewed_at"])] = row["n"]
    return counts


def average_easiness(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT AVG(easiness) AS avg_ef FROM cards").fetchone()
    return row["avg_ef"] if row["avg_ef"] is not None else sm2.INITIAL_EASINESS
