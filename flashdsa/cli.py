"""Command-line interface: quiz / stats / init / demo."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from . import db as db_module
from . import quiz as quiz_module
from . import stats as stats_module
from .cards import load_deck

VERSION = "0.1.0"


def default_db_path() -> Path:
    """XDG-style default location, overridable with FLASHDSA_DB."""
    env = os.environ.get("FLASHDSA_DB")
    if env:
        return Path(env).expanduser()
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "flashdsa" / "flashdsa.db"


def cmd_init(args: argparse.Namespace) -> int:
    conn = db_module.connect(args.db)
    added = db_module.seed_deck(conn, load_deck())
    total = db_module.card_count(conn)
    print(f"Deck ready: {added} new card(s) added, {total} tracked at {args.db}")
    conn.close()
    return 0


def cmd_quiz(args: argparse.Namespace) -> int:
    conn = db_module.connect(args.db)
    db_module.seed_deck(conn, load_deck())
    grades = None
    if args.grades:
        grades = [int(g) for g in args.grades.split(",")]
    quiz_module.run_session(conn, grades=grades, limit=args.limit)
    conn.close()
    return 0


def _bar(percent: float, width: int = 20) -> str:
    filled = int(round(percent / 100 * width))
    return "█" * filled + "░" * (width - filled)


def cmd_stats(args: argparse.Namespace) -> int:
    conn = db_module.connect(args.db)
    db_module.seed_deck(conn, load_deck())
    today = date.today()

    print(f"\n📊 FlashDSA stats — {db_module.card_count(conn)} cards · "
          f"{db_module.review_count(conn)} reviews logged\n")

    print("Mastery by topic")
    for m in stats_module.mastery_by_topic(conn):
        print(f"  {m.topic:<15} {_bar(m.percent)} {m.percent:5.1f}%  ({m.learned}/{m.total} learned)")

    print("\nDue-card forecast (next 7 days)")
    for day, count in stats_module.forecast(conn, days=7, today=today):
        label = "today" if day == today else day.strftime("%a %b %d")
        print(f"  {label:<12} {count:>3} card(s) due")

    heat = stats_module.heatmap(conn, days=7, today=today)
    week_total = sum(heat.values())
    print(f"\nReviews in the last 7 days: {week_total}")
    conn.close()
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from . import demo as demo_module

    return demo_module.run(args.out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flashdsa",
        description="Spaced-repetition DSA flashcards for interview prep (SM-2).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "--db",
        type=Path,
        default=default_db_path(),
        help="path to the SQLite database (default: %(default)s)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="seed the database with the bundled deck")
    p_init.set_defaults(func=cmd_init)

    p_quiz = sub.add_parser("quiz", help="review due cards")
    p_quiz.add_argument("--limit", type=int, default=None, help="max cards this session")
    p_quiz.add_argument(
        "--grades",
        default=None,
        help='scripted grades, e.g. --grades "5,4,3" (non-interactive)',
    )
    p_quiz.set_defaults(func=cmd_quiz)

    p_stats = sub.add_parser("stats", help="mastery by topic + 7-day forecast")
    p_stats.set_defaults(func=cmd_stats)

    p_demo = sub.add_parser("demo", help="run a scripted end-to-end demo on demo data")
    p_demo.add_argument(
        "--out",
        type=Path,
        default=Path("docs") / "session.png",
        help="where to save the rendered session chart",
    )
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
