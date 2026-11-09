"""Explainable MVP priority score. Not a production-trained model."""
def score_loan(loan, broken_promises: int = 0):
    reasons = []
    dpd = max(0, int(loan.dpd or 0))
    dpd_points = min(40, dpd * 1.45)
    if dpd >= 25: reasons.append(f"{dpd} DPD — close to the 30-day bucket boundary")
    elif dpd >= 15: reasons.append(f"{dpd} DPD — overdue days are increasing")
    else: reasons.append(f"{dpd} DPD — early intervention window")
    amount_points = min(20, (float(loan.outstanding or 0) / 100000) * 3.2)
    if loan.outstanding >= 500000: reasons.append("High outstanding balance")
    elif loan.outstanding >= 250000: reasons.append("Material outstanding balance")
    else: reasons.append("Outstanding balance is below the high-balance threshold")
    history = (loan.payment_history or "unknown").lower()
    history_points = 18 if history in {"missed", "irregular", "late"} else 7 if history == "unknown" else 2
    if history_points >= 18: reasons.append("Recent payment history is irregular")
    elif history == "unknown": reasons.append("Payment history needs verification")
    else: reasons.append("Payment history is recorded as regular")
    broken_points = min(22, broken_promises * 11)
    if broken_promises:
        reasons = reasons[:2] + [f"{broken_promises} broken promise(s) recorded"]
    score = round(min(100, dpd_points + amount_points + history_points + broken_points))
    return {"score": score, "reasons": reasons[:3]}
