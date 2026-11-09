from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from .models import Branch, User, Loan, Promise, LoanDpdSnapshot
from .security import hash_password

def seed(db: Session):
    if db.query(User).first(): return
    branch = Branch(name="Indore Central")
    db.add(branch); db.flush()
    manager = User(name="Aditi Sharma", email="manager@collectiq.demo", password_hash=hash_password("DemoPass123!"), role="manager", branch_id=branch.id, pincodes="452001,452002,452003")
    rahul = User(name="Rahul Chouhan", email="rahul@collectiq.demo", password_hash=hash_password("DemoPass123!"), role="officer", branch_id=branch.id, pincodes="452001,452002")
    neha = User(name="Neha Solanki", email="neha@collectiq.demo", password_hash=hash_password("DemoPass123!"), role="officer", branch_id=branch.id, pincodes="452002,452003")
    imran = User(name="Imran Qureshi", email="imran@collectiq.demo", password_hash=hash_password("DemoPass123!"), role="officer", branch_id=branch.id, pincodes="452002")
    db.add_all([manager, rahul, neha, imran]); db.flush()
    rows = [
        ("LN-10293", "Company B (packaging unit)", "452001", 640000, 12, date(2026,11,5), "regular", rahul.id),
        ("LN-10871", "Company C (fertiliser shop)", "452003", 310000, 27, None, "irregular", neha.id),
        ("LN-11930", "Company D (printing press)", "452002", 220000, 19, date(2026,10,31), "missed", imran.id),
        ("LN-12004", "Shree Tools & Dies", "452001", 480000, 8, None, "regular", rahul.id),
        ("LN-12019", "Mahalaxmi Traders", "452003", 175000, 23, None, "late", neha.id),
        ("LN-12025", "Om Packaging Works", "452002", 720000, 29, None, "missed", neha.id),
        ("LN-12031", "Vijay Machine Tools (synthetic)", "452001", 390000, 34, None, "irregular", rahul.id),
        ("LN-12032", "Narmada Components (synthetic)", "452003", 255000, 22, None, "regular", neha.id),
        ("LN-12033", "Kaveri Hardware (synthetic)", "452002", 180000, 42, None, "missed", imran.id),
    ]
    loan_objects = {}
    for lid, name, pin, amount, dpd, pdate, history, officer in rows:
        loan = Loan(loan_id=lid, borrower_name=name, pincode=pin, branch_name=branch.name, outstanding=amount, dpd=dpd, promise_date=pdate, payment_history=history, assigned_to=officer)
        db.add(loan); loan_objects[lid] = (loan, officer)
    db.flush()
    # Seed the two promises supplied in the client brief for a realistic tracker.
    for lid, pdate, amount, officer in [("LN-10293", date(2026,11,5), 640000, rahul.id), ("LN-11930", date(2026,10,31), 220000, imran.id)]:
        loan, _ = loan_objects[lid]
        db.add(Promise(loan_id=loan.id, officer_id=officer, promise_date=pdate, amount=amount, status="upcoming", reminder_status="draft"))
    # Synthetic historical DPD snapshots make the demo roll-rate calculation meaningful.
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    for lid, previous_dpd in [("LN-12031", 20), ("LN-12032", 15), ("LN-12033", 28)]:
        loan, _ = loan_objects[lid]
        db.add_all([
            LoanDpdSnapshot(loan_id=loan.id, snapshot_date=today - timedelta(days=7), dpd=previous_dpd),
            LoanDpdSnapshot(loan_id=loan.id, snapshot_date=today, dpd=loan.dpd),
        ])
    db.commit()
