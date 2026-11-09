"""Collection analytics derived from dated portfolio snapshots."""

def calculate_roll_rate(transitions: list[tuple[int, int]]) -> float | None:
    """Return 1-30 -> 31-60 DPD roll rate as a percentage.

    Each tuple is (previous_dpd, current_dpd). Loans without a prior 1-30 DPD
    snapshot are excluded from the cohort denominator. None means there is no
    eligible historical cohort; it must not be displayed as 0%.
    """
    cohort = [(previous, current) for previous, current in transitions if 1 <= previous <= 30]
    if not cohort:
        return None
    rolled = sum(1 for _, current in cohort if 31 <= current <= 60)
    return round(rolled / len(cohort) * 100, 1)
