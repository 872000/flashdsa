"""Tests for scripted quiz sessions and the demo command."""

from datetime import date

from flashdsa import db, demo
from flashdsa import quiz as quiz_module
from flashdsa.cards import load_deck

TODAY = date(2026, 10, 1)


def make_conn(tmp_path):
    conn = db.connect(tmp_path / "test.db")
    db.seed_deck(conn, load_deck(), today=TODAY)
    return conn


def test_scripted_session_reviews_due_cards(tmp_path, capsys):
    conn = make_conn(tmp_path)
    summary = quiz_module.run_session(conn, grades=[5, 4, 3], limit=3, today=TODAY)
    assert summary.reviewed == 3
    assert summary.grades == [5, 4, 3]
    assert db.review_count(conn) == 3
    conn.close()


def test_session_summary_accuracy(tmp_path, capsys):
    conn = make_conn(tmp_path)
    summary = quiz_module.run_session(conn, grades=[5, 5, 2, 1], limit=4, today=TODAY)
    assert summary.recall_rate == 50.0
    assert summary.average_quality == 3.25
    out = capsys.readouterr().out
    assert "Session complete" in out
    conn.close()


def test_empty_session_reports_caught_up(tmp_path, capsys):
    conn = make_conn(tmp_path)
    quiz_module.run_session(conn, grades=[5] * 40, today=TODAY)  # review everything
    summary = quiz_module.run_session(conn, today=TODAY)  # nothing left due
    assert summary.reviewed == 0
    assert "caught up" in capsys.readouterr().out
    conn.close()


def test_demo_runs_end_to_end_and_renders_chart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "docs" / "session.png"
    assert demo.run(out) == 0
    assert out.exists() and out.stat().st_size > 10_000
