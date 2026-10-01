"""Tests for SQLite persistence and review recording."""

from datetime import date

import pytest

from flashdsa import db
from flashdsa.cards import load_deck

TODAY = date(2026, 10, 1)


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.seed_deck(connection, load_deck(), today=TODAY)
    yield connection
    connection.close()


def test_seed_inserts_all_cards(conn):
    assert db.card_count(conn) == 40


def test_seed_is_idempotent(conn):
    added = db.seed_deck(conn, load_deck(), today=TODAY)
    assert added == 0
    assert db.card_count(conn) == 40


def test_all_cards_due_on_first_run(conn):
    assert len(db.due_cards(conn, today=TODAY)) == 40


def test_record_review_updates_schedule(conn):
    result = db.record_review(conn, "arr-01", 5, today=TODAY)
    assert result.state.repetitions == 1
    assert result.state.interval_days == 1
    row = conn.execute("SELECT * FROM cards WHERE id = 'arr-01'").fetchone()
    assert row["next_review"] == "2026-10-02"  # tomorrow, interval = 1 day
    assert row["repetitions"] == 1


def test_reviewed_card_no_longer_due_today(conn):
    db.record_review(conn, "arr-01", 5, today=TODAY)
    due_ids = {r["id"] for r in db.due_cards(conn, today=TODAY)}
    assert "arr-01" not in due_ids
    assert len(due_ids) == 39


def test_review_history_logged(conn):
    db.record_review(conn, "arr-01", 4, today=TODAY)
    db.record_review(conn, "arr-02", 2, today=TODAY)
    assert db.review_count(conn) == 2
    row = conn.execute(
        "SELECT * FROM reviews WHERE card_id = 'arr-01'"
    ).fetchone()
    assert row["quality"] == 4
    assert row["reviewed_at"] == TODAY.isoformat()


def test_unknown_card_raises(conn):
    with pytest.raises(KeyError):
        db.record_review(conn, "nope-99", 5, today=TODAY)


def test_due_cards_respects_limit(conn):
    assert len(db.due_cards(conn, today=TODAY, limit=5)) == 5
