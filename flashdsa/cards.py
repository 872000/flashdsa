"""Card model and bundled deck loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_DECK_PATH = PACKAGE_DIR.parent / "data" / "deck.json"

VALID_DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Card:
    """One flashcard from the bundled deck."""

    id: str
    topic: str
    difficulty: str
    prompt: str
    answer: str


def load_deck(path: str | Path = DEFAULT_DECK_PATH) -> list[Card]:
    """Load the bundled card deck from JSON, validating every card."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    cards: list[Card] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw):
        for field in ("id", "topic", "difficulty", "prompt", "answer"):
            if not entry.get(field):
                raise ValueError(f"deck entry #{i} is missing {field!r}")
        if entry["difficulty"] not in VALID_DIFFICULTIES:
            raise ValueError(
                f"card {entry['id']!r}: difficulty must be one of {VALID_DIFFICULTIES}"
            )
        if entry["id"] in seen:
            raise ValueError(f"duplicate card id {entry['id']!r}")
        seen.add(entry["id"])
        cards.append(
            Card(
                id=entry["id"],
                topic=entry["topic"],
                difficulty=entry["difficulty"],
                prompt=entry["prompt"],
                answer=entry["answer"],
            )
        )
    return cards


def topics(cards: list[Card]) -> list[str]:
    """Topic tags in first-appearance order."""
    return list(dict.fromkeys(card.topic for card in cards))
