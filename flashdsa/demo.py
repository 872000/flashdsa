"""Scripted end-to-end demo: seeds a fresh DB, reviews cards, renders a chart.

Simulates two days of reviewing on bundled demo data (a throwaway database
in a temp dir), so it never touches your real review history.
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from . import db as db_module
from . import quiz as quiz_module
from . import stats as stats_module
from .cards import load_deck

# Scripted self-grades: a believable mix of perfect / good / shaky recalls.
DAY1_GRADES = [5, 4, 5, 3, 4, 5, 2, 4, 5, 5, 3, 4]
DAY2_GRADES = [5, 5, 4, 5, 4, 5, 2, 4, 5, 5, 4, 3]


def render_session_chart(
    conn,
    summary: quiz_module.SessionSummary,
    out: Path,
    today: date,
    days_simulated: int,
) -> Path:
    """Render mastery bars + 7-day forecast to PNG (README screenshot)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mastery = stats_module.mastery_by_topic(conn)
    forecast = stats_module.forecast(conn, days=7, today=today)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#0f172a")

    # --- left: mastery by topic ---
    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        ax.tick_params(colors="#cbd5e1", labelsize=10)
        for spine in ax.spines.values():
            spine.set_color("#334155")

    topic_names = [m.topic.replace("-", " ") for m in mastery]
    percents = [m.percent for m in mastery]
    colors = ["#22c55e" if p >= 60 else "#f59e0b" if p >= 30 else "#64748b" for p in percents]
    ax1.barh(topic_names, percents, color=colors, edgecolor="none", height=0.6)
    ax1.set_xlim(0, 100)
    ax1.set_xlabel("mastery %", color="#cbd5e1")
    ax1.set_title("Mastery by topic", color="#f8fafc", fontsize=13, pad=12)
    for i, (p, m) in enumerate(zip(percents, mastery)):
        ax1.text(p + 1.5, i, f"{m.learned}/{m.total}", va="center", color="#cbd5e1", fontsize=9)

    # --- right: 7-day forecast ---
    labels = ["today" if d == today else d.strftime("%a") for d, _ in forecast]
    counts = [c for _, c in forecast]
    bars = ax2.bar(labels, counts, color="#38bdf8", edgecolor="none", width=0.6)
    ax2.set_ylabel("cards due", color="#cbd5e1")
    ax2.set_title("Due-card forecast — next 7 days", color="#f8fafc", fontsize=13, pad=12)
    for bar, c in zip(bars, counts):
        if c:
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                str(c),
                ha="center",
                color="#cbd5e1",
                fontsize=10,
            )

    fig.suptitle(
        f"FlashDSA demo — {days_simulated} days, {summary.reviewed} reviews · "
        f"avg quality {summary.average_quality:.1f}/5 · recall {summary.recall_rate:.0f}%",
        color="#f8fafc",
        fontsize=14,
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def run(out: Path) -> int:
    out = Path(out)
    with tempfile.TemporaryDirectory(prefix="flashdsa-demo-") as tmp:
        db_path = Path(tmp) / "demo.db"
        conn = db_module.connect(db_path)
        db_module.seed_deck(conn, load_deck())

        day1 = date.today()
        day2 = day1 + timedelta(days=1)

        print("=" * 60)
        print(" FlashDSA demo — scripted sessions on bundled demo data")
        print("=" * 60)
        print(f"\n—— Day 1 ({day1}) ——")
        session1 = quiz_module.run_session(conn, grades=DAY1_GRADES, limit=12, today=day1)

        # Day 2: re-review exactly the cards seen on day 1.
        day1_ids = [
            row["card_id"]
            for row in conn.execute(
                "SELECT card_id FROM reviews WHERE reviewed_at = ? ORDER BY id",
                (day1.isoformat(),),
            )
        ]
        print(f"\n—— Day 2 ({day2}) ——\n{len(day1_ids)} card(s) due again.\n")
        session2 = quiz_module.SessionSummary()
        for i, (card_id, grade) in enumerate(zip(day1_ids, DAY2_GRADES), start=1):
            card = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            print(f"[{i}/{len(day1_ids)}] [{card['topic']}] ({card['difficulty']})")
            print(f"  Q: {card['prompt']}")
            print(f"  A: {card['answer']}")
            print(f"  Grade: {grade}")
            result = db_module.record_review(conn, card_id, grade, today=day2)
            session2.reviewed += 1
            session2.grades.append(grade)
            print(f"  → next review in {result.state.interval_days} day(s) (EF {result.state.easiness:.2f})\n")

        combined = quiz_module.SessionSummary(
            reviewed=session1.reviewed + session2.reviewed,
            grades=session1.grades + session2.grades,
        )
        print("—" * 60)
        print(f"Demo complete: {combined.reviewed} reviews over 2 days · "
              f"avg quality {combined.average_quality:.1f}/5 · "
              f"recall {combined.recall_rate:.0f}%")

        chart = None
        try:
            chart = render_session_chart(conn, combined, out, today=day2, days_simulated=2)
        except ImportError:
            print("\nmatplotlib is not installed — skipping the session chart.")
            print("Install it with: pip install 'flashdsa[charts]'")
        if chart:
            print(f"\nSession chart saved to {chart}")
        conn.close()
    return 0
