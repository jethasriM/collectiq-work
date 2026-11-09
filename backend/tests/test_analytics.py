from app.analytics import calculate_roll_rate

def test_roll_rate_uses_only_prior_1_to_30_dpd_cohort():
    assert calculate_roll_rate([(10, 35), (20, 25), (45, 55)]) == 50.0

def test_roll_rate_is_none_without_historical_cohort():
    assert calculate_roll_rate([(0, 10), (35, 40)]) is None

def test_roll_rate_zero_is_distinct_from_missing_history():
    assert calculate_roll_rate([(5, 10), (12, 30)]) == 0.0
