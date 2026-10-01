"""Tests for the SM-2 algorithm (from-scratch implementation)."""

from datetime import date

import pytest

from flashdsa import sm2
from flashdsa.sm2 import ReviewState, update, validate_quality


def test_first_successful_review_interval_is_one_day():
    result = update(ReviewState(), 5, today=date(2026, 10, 1))
    assert result.state.repetitions == 1
    assert result.state.interval_days == 1
    assert result.next_review == date(2026, 10, 2)


def test_second_successful_review_interval_is_six_days():
    first = update(ReviewState(), 5, today=date(2026, 10, 1))
    second = update(first.state, 4, today=date(2026, 10, 2))
    assert second.state.repetitions == 2
    assert second.state.interval_days == 6


def test_third_review_interval_is_previous_times_easiness():
    state = ReviewState(easiness=2.5, repetitions=2, interval_days=6)
    result = update(state, 5, today=date(2026, 10, 1))
    expected_ef = 2.5 + (0.1 - 0 * (0.08 + 0 * 0.02))
    assert result.state.easiness == pytest.approx(expected_ef)
    assert result.state.interval_days == round(6 * expected_ef)


def test_easiness_formula_matches_sm2_spec():
    # q=3 on a fresh card: EF = 2.5 + (0.1 - 2*(0.08 + 2*0.02)) = 2.5 - 0.14
    result = update(ReviewState(), 3, today=date(2026, 10, 1))
    assert result.state.easiness == pytest.approx(2.5 + (0.1 - 2 * (0.08 + 2 * 0.02)))


@pytest.mark.parametrize("quality", [0, 1, 2])
def test_failed_recall_resets_repetitions(quality):
    state = ReviewState(easiness=2.6, repetitions=4, interval_days=30)
    result = update(state, quality, today=date(2026, 10, 1))
    assert result.state.repetitions == 0
    assert result.state.interval_days == 1
    assert result.next_review == date(2026, 10, 2)


def test_easiness_never_drops_below_floor():
    state = ReviewState(easiness=1.3, repetitions=0, interval_days=0)
    result = update(state, 0, today=date(2026, 10, 1))
    assert result.state.easiness >= sm2.MIN_EASINESS


@pytest.mark.parametrize("bad", [-1, 6, 10, "5", 4.0, None, True])
def test_invalid_quality_rejected(bad):
    with pytest.raises(ValueError):
        validate_quality(bad)


@pytest.mark.parametrize("good", [0, 1, 2, 3, 4, 5])
def test_valid_quality_accepted(good):
    assert validate_quality(good) == good


def test_perfect_streak_grows_interval_monotonically():
    state = ReviewState()
    intervals = []
    for _ in range(5):
        result = update(state, 5, today=date(2026, 10, 1))
        intervals.append(result.state.interval_days)
        state = result.state
    assert intervals == sorted(intervals)
    assert intervals[0] == 1 and intervals[1] == 6
