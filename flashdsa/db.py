"""SQLite persistence: card scheduling state + full review history."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from . import sm2
from .cards import Card

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id            TEXT PRIMARY KEY,
    topic         TEXT NOT NULL,
    difficulty    TEXT NOT NULL,
    prompt        TEXT NOT NULL,
    answer        TEXT NOT NULL,
    easiness      REAL NOT NULL,
    repetitions   INTEGER NOT NULL,
    interval_days INTEGER NOT NULL,
    next_review   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id         TEXT NOT NULL REFERENCES cards(id),
    reviewed_at     TEXT NOT NULL,
    quality         INTEGER NOT NULL,
    easiness_before REAL NOT NULL,
    easiness_after  REAL NOT NULL,
    interval_before INTEGER NOT NULL,
    interval_after  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_next_review ON cards(next_review);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_at ON reviews(reviewed_at);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open the database, creating parent dirs and the schema if needed."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def seed_deck(conn: sqlite3.Connection, cards: list[Card], today: date | None = None) -> int:
    """Insert bundled cards that are not already tracked. Returns # added."""
    today = today or date.today()
    added = 0
    for card in cards:
        cur = conn.execute(
            """INSERT OR IGNORE INTO cards
               (id, topic, difficulty, prompt, answer, easiness, repetitions, interval_days, next_review)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card.id,
                card.topic,
                card.difficulty,
                card.prompt,
                card.answer,
                sm2.INITIAL_EASINESS,
                0,
                0,
                today.isoformat(),
            ),
        )
        added += cur.rowcount
    conn.commit()
    return added


def due_cards(conn: sqlite3.Connection, today: date | None = None, limit: int | None = None) -> list[sqlite3.Row]:
    """Cards whose next_review is today or earlier, oldest first."""
    today = today or date.today()
    sql = "SELECT * FROM cards WHERE next_review <= ? ORDER BY next_review, id"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, (today.isoformat(),)).fetchall()


def record_review(
    conn: sqlite3.Connection,
    card_id: str,
    quality: int,
    today: date | None = None,
) -> sm2.ReviewResult:
    """Grade a card, run SM-2, persist the new schedule + a history row."""
    today = today or date.today()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown card id {card_id!r}")

    state = sm2.ReviewState(
        easiness=row["easiness"],
        repetitions=row["repetitions"],
        interval_days=row["interval_days"],
    )
    result = sm2.update(state, quality, today)

    conn.execute(
        """UPDATE cards SET easiness = ?, repetitions = ?, interval_days = ?, next_review = ?
           WHERE id = ?""",
        (
            result.state.easiness,
            result.state.repetitions,
            result.state.interval_days,
            result.next_review.isoformat(),
            card_id,
        ),
    )
    conn.execute(
        """INSERT INTO reviews
           (card_id, reviewed_at, quality, easiness_before, easiness_after, interval_before, interval_after)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            card_id,
            today.isoformat(),
            quality,
            state.easiness,
            result.state.easiness,
            state.interval_days,
            result.state.interval_days,
        ),
    )
    conn.commit()
    return result


def card_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM cards").fetchone()["n"]


def review_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM reviews").fetchone()["n"]
