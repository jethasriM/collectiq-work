from types import SimpleNamespace
from app.scoring import score_loan

def loan(dpd=12, outstanding=100000, payment_history='regular'):
    return SimpleNamespace(dpd=dpd, outstanding=outstanding, payment_history=payment_history)

def test_score_never_exceeds_100():
    assert score_loan(loan(90, 50_00_000, 'missed'), 9)['score'] == 100

def test_broken_promises_increase_priority():
    base = score_loan(loan(18, 250000, 'late'), 0)['score']
    broken = score_loan(loan(18, 250000, 'late'), 1)['score']
    assert broken > base

def test_reasons_are_limited_to_three():
    result = score_loan(loan(30, 800000, 'missed'), 3)
    assert len(result['reasons']) == 3
