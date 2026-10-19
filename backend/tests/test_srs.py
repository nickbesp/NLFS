import pytest

from app.srs import sm2


def test_first_successful_review_gives_one_day():
    assert sm2(repetitions=0, interval=1, ease_factor=2.5, quality=4) == (1, 1, 2.5)


def test_second_successful_review_gives_six_days():
    reps, interval, _ = sm2(repetitions=1, interval=1, ease_factor=2.5, quality=4)
    assert (reps, interval) == (2, 6)


def test_later_reviews_multiply_interval_by_ease():
    reps, interval, _ = sm2(repetitions=2, interval=6, ease_factor=2.5, quality=4)
    assert (reps, interval) == (3, 15)


def test_failed_review_resets_repetitions_and_interval():
    reps, interval, _ = sm2(repetitions=5, interval=40, ease_factor=2.5, quality=2)
    assert (reps, interval) == (0, 1)


def test_ease_factor_adjusts_with_quality():
    assert sm2(0, 1, 2.5, 5)[2] == pytest.approx(2.6)
    assert sm2(0, 1, 2.5, 3)[2] == pytest.approx(2.36)


def test_ease_factor_never_drops_below_1_3():
    assert sm2(0, 1, 1.3, 0)[2] == pytest.approx(1.3)


@pytest.mark.parametrize("quality", [-1, 6])
def test_quality_out_of_range_rejected(quality):
    with pytest.raises(ValueError):
        sm2(0, 1, 2.5, quality)
