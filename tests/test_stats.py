"""Tests for stats: mastery, forecast, heatmap."""

from datetime import date, timedelta

import pytest

from flashdsa import db, stats
from flashdsa.cards import load_deck

TODAY = date(2026, 10, 1)


def make_conn(tmp_path, reviews: list[tuple[str, int, date]] | None = None):
    conn = db.connect(tmp_path / "test.db")
    db.seed_deck(conn, load_deck(), today=TODAY)
    for card_id, quality, day in reviews or []:
        db.record_review(conn, card_id, quality, today=day)
    return conn


def test_mastery_zero_before_any_reviews(tmp_path):
    conn = make_conn(tmp_path)
    for m in stats.mastery_by_topic(conn):
        assert m.percent == 0.0
        assert m.learned == 0
    conn.close()


def test_mastery_counts_learned_cards(tmp_path):
    # Two successful reviews with high grades => learned.
    conn = make_conn(
        tmp_path,
        [
            ("arr-01", 5, TODAY),
            ("arr-01", 5, TODAY + timedelta(days=1)),
            ("arr-02", 2, TODAY),
        ],
    )
    by_topic = {m.topic: m for m in stats.mastery_by_topic(conn)}
    assert by_topic["arrays"].learned == 1
    assert by_topic["arrays"].total == 6
    assert by_topic["arrays"].percent == pytest.approx(100 / 6)
    conn.close()


def test_failed_card_not_counted_as_learned(tmp_path):
    conn = make_conn(tmp_path, [("arr-01", 1, TODAY), ("arr-01", 0, TODAY)])
    by_topic = {m.topic: m for m in stats.mastery_by_topic(conn)}
    assert by_topic["arrays"].learned == 0
    conn.close()


def test_forecast_covers_seven_days(tmp_path):
    conn = make_conn(tmp_path)
    fc = stats.forecast(conn, days=7, today=TODAY)
    assert len(fc) == 7
    assert fc[0] == (TODAY, 40)  # everything due on day one
    assert sum(c for _, c in fc[1:]) == 0
    conn.close()


def test_forecast_places_reviewed_cards_on_their_day(tmp_path):
    conn = make_conn(tmp_path, [("arr-01", 5, TODAY)])
    fc = dict(stats.forecast(conn, days=7, today=TODAY))
    assert fc[TODAY] == 39
    assert fc[TODAY + timedelta(days=1)] == 1
    conn.close()


def test_forecast_counts_overdue_cards_on_day_zero(tmp_path):
    conn = make_conn(tmp_path)  # everything due on TODAY
    later = TODAY + timedelta(days=3)
    fc = dict(stats.forecast(conn, days=7, today=later))
    assert fc[later] == 40  # all overdue, shown as due "today"
    conn.close()


def test_heatmap_counts_reviews_per_day(tmp_path):
    conn = make_conn(
        tmp_path,
        [
            ("arr-01", 5, TODAY),
            ("arr-02", 4, TODAY),
            ("arr-03", 3, TODAY - timedelta(days=1)),
        ],
    )
    heat = stats.heatmap(conn, days=7, today=TODAY)
    assert heat[TODAY] == 2
    assert heat[TODAY - timedelta(days=1)] == 1
    assert heat[TODAY - timedelta(days=6)] == 0
    conn.close()
