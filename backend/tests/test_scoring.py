from types import SimpleNamespace
from app.scoring import score_loan

def test_score_is_bounded_and_explained():
    loan=SimpleNamespace(dpd=29,outstanding=720000,payment_history="missed")
    result=score_loan(loan,2)
    assert 0 <= result["score"] <= 100
    assert len(result["reasons"]) == 3
    assert any("29 DPD" in reason for reason in result["reasons"])

def test_lower_risk_scores_lower():
    low=score_loan(SimpleNamespace(dpd=3,outstanding=50000,payment_history="regular"),0)
    high=score_loan(SimpleNamespace(dpd=28,outstanding=700000,payment_history="missed"),1)
    assert high["score"] > low["score"]


def test_reasons_cover_three_explanation_dimensions():
    result = score_loan(SimpleNamespace(dpd=5, outstanding=50000, payment_history="regular"), 0)
    assert len(result["reasons"]) == 3
    assert any("DPD" in reason for reason in result["reasons"])
    assert any("Outstanding balance" in reason for reason in result["reasons"])


def test_broken_promise_is_explained_when_it_affects_score():
    result = score_loan(SimpleNamespace(dpd=18, outstanding=250000, payment_history="late"), 1)
    assert any("broken promise" in reason for reason in result["reasons"])
