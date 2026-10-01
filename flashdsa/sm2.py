"""SM-2 spaced-repetition algorithm, implemented from scratch.

Reference: Piotr Wozniak's SM-2 (1987), the algorithm behind SuperMemo.

Each card carries an *easiness factor* (EF), a *repetition* count and the
*interval* (in days) until the next review. After the learner self-grades
their recall with a quality score q in 0..5:

- EF is nudged up for perfect recalls and down for poor ones (floor 1.3).
- q >= 3 counts as a successful recall: the interval grows
  (1 day, then 6 days, then interval * EF).
- q < 3 resets the repetition count and the interval back to 1 day.

Higher EF + longer streaks => the card is shown less and less often.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

MIN_EASINESS = 1.3
INITIAL_EASINESS = 2.5


@dataclass(frozen=True)
class ReviewState:
    """Scheduling state of one card before a review."""

    easiness: float = INITIAL_EASINESS
    repetitions: int = 0
    interval_days: int = 0


@dataclass(frozen=True)
class ReviewResult:
    """Scheduling state of one card after a review."""

    state: ReviewState
    next_review: date


def validate_quality(quality: int) -> int:
    """Ensure a self-grade is an int in the SM-2 range 0..5."""
    if isinstance(quality, bool) or not isinstance(quality, int):
        raise ValueError(f"quality must be an int in 0..5, got {quality!r}")
    if not 0 <= quality <= 5:
        raise ValueError(f"quality must be an int in 0..5, got {quality!r}")
    return quality


def update(state: ReviewState, quality: int, today: date | None = None) -> ReviewResult:
    """Apply one SM-2 review and return the new state + next review date.

    Args:
        state: the card's current scheduling state.
        quality: self-graded recall quality, 0 (blackout) .. 5 (perfect).
        today: review date; defaults to today.

    Returns:
        ReviewResult with the updated state and next_review date.
    """
    q = validate_quality(quality)
    today = today or date.today()

    easiness = state.easiness + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    easiness = max(MIN_EASINESS, easiness)

    if q < 3:
        # Failed recall: restart the repetition chain.
        repetitions, interval = 0, 1
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = max(1, round(state.interval_days * easiness))

    new_state = ReviewState(
        easiness=round(easiness, 4),
        repetitions=repetitions,
        interval_days=interval,
    )
    return ReviewResult(new_state, today + timedelta(days=interval))
