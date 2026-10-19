"""SuperMemo SM-2 spaced repetition algorithm."""

MIN_EASE_FACTOR = 1.3


def sm2(repetitions: int, interval: int, ease_factor: float, quality: int) -> tuple[int, int, float]:
    """Return the new (repetitions, interval_days, ease_factor) after a review.

    quality: 0-5 self-rating. Below 3 counts as a failed recall.
    """
    if not 0 <= quality <= 5:
        raise ValueError("quality must be between 0 and 5")

    if quality < 3:
        repetitions, interval = 0, 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease_factor)
        repetitions += 1

    ease_factor += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    ease_factor = max(MIN_EASE_FACTOR, round(ease_factor, 4))
    return repetitions, interval, ease_factor
