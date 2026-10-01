"""Tests for the bundled card deck."""

from flashdsa.cards import VALID_DIFFICULTIES, load_deck, topics

EXPECTED_TOPICS = {
    "arrays",
    "two-pointers",
    "sliding-window",
    "hash-maps",
    "trees",
    "graphs",
    "dynamic-programming",
}


def test_deck_has_forty_cards():
    assert len(load_deck()) == 40


def test_deck_covers_all_topics():
    assert set(topics(load_deck())) == EXPECTED_TOPICS


def test_every_card_has_prompt_answer_topic_difficulty():
    for card in load_deck():
        assert card.id.strip()
        assert card.prompt.strip()
        assert card.answer.strip()
        assert card.topic in EXPECTED_TOPICS
        assert card.difficulty in VALID_DIFFICULTIES


def test_card_ids_unique():
    ids = [c.id for c in load_deck()]
    assert len(ids) == len(set(ids))


def test_answers_are_substantive():
    for card in load_deck():
        assert len(card.answer.split()) >= 8, f"answer too thin for {card.id}"
