from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from uuid import uuid4
import csv, io, math
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from .database import Base, engine, get_db
from . import models, schemas
from .security import current_user, require_roles, verify_password, create_token
from .scoring import score_loan
from .analytics import calculate_roll_rate
from .compliance import to_ist, allowed_contact_time, reminder_language_allowed
from .seed import seed
from .config import settings

Base.metadata.create_all(bind=engine)
app = FastAPI(title="CollectIQ API", version="1.0.0", description="NBFC field collections MVP API")
allowed_origins = [settings.frontend_origin] if settings.environment.lower() == "production" else [settings.frontend_origin, "http://localhost:5173"]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

@app.on_event("startup")
def startup():
    if settings.environment.lower() == "production":
        if settings.secret_key == "dev-only-change-me" or "replace-this" in settings.secret_key.lower() or len(settings.secret_key) < 32:
            raise RuntimeError("Production requires a unique SECRET_KEY of at least 32 characters")
        if settings.database_url.startswith("sqlite") or ":collectiq@" in settings.database_url:
            raise RuntimeError("Production requires a managed PostgreSQL URL and non-default database credentials")
    else:
        db = next(get_db())
        try: seed(db)
        finally: db.close()

@app.get("/health")
def health(): return {"status": "ok", "service": "collectiq-api"}

@app.post("/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email) == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user), "user": user}

@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)): return user

@app.get("/officers")
def officers(db: Session = Depends(get_db), user: models.User = Depends(require_roles("manager"))):
    q=db.query(models.User).filter(models.User.role=="officer", models.User.active==True)
    if user.branch_id: q=q.filter(models.User.branch_id==user.branch_id)
    return [{"id":u.id,"name":u.name,"email":u.email,"pincodes":[p for p in u.pincodes.split(",") if p]} for u in q.all()]

@app.post("/loans/import")
async def import_loans(file: UploadFile = File(...), db: Session = Depends(get_db), user: models.User = Depends(require_roles("manager"))):
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, "Upload a CSV file")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024: raise HTTPException(413, "CSV exceeds the 5 MB upload limit")
    try: raw = content.decode("utf-8-sig")
    except UnicodeDecodeError: raise HTTPException(400, "CSV must be UTF-8 encoded")
    reader = csv.DictReader(io.StringIO(raw))
    required = {"loan_id","borrower_name","pincode","outstanding","dpd"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(400, f"CSV must include: {', '.join(sorted(required))}")
    officer_query = db.query(models.User).filter(models.User.role=="officer", models.User.active==True)
    if user.branch_id: officer_query=officer_query.filter(models.User.branch_id==user.branch_id)
    officers = officer_query.all()
    created=updated=unassigned=0; errors=[]; seen_ids=set()
    for line, row in enumerate(reader, start=2):
        try:
            lid=(row.get("loan_id") or "").strip(); pin=(row.get("pincode") or "").strip()
            if not lid or len(lid)>40 or not pin.isdigit() or len(pin) not in (5,6): raise ValueError("loan_id and a valid 5–6 digit numeric pincode are required")
            if lid in seen_ids: raise ValueError("Duplicate loan_id in this CSV file")
            seen_ids.add(lid)
            amount=float(row.get("outstanding") or 0); dpd=int(row.get("dpd") or 0)
            if not math.isfinite(amount) or amount < 0 or dpd < 0: raise ValueError("outstanding must be finite and non-negative; DPD cannot be negative")
            loan=db.query(models.Loan).filter_by(loan_id=lid).first()
            is_new = loan is None
            if is_new: loan=models.Loan(loan_id=lid); db.add(loan)
            loan.borrower_name=(row.get("borrower_name") or "Unknown borrower").strip(); loan.pincode=pin
            loan.branch_name=(row.get("branch_name") or (user.branch.name if user.branch else "Indore")).strip()
            if user.branch and loan.branch_name != user.branch.name: raise ValueError("CSV branch_name is outside your assigned branch")
            loan.outstanding=amount; loan.dpd=dpd
            loan.payment_history=(row.get("payment_history") or "unknown").strip().lower()
            pd=(row.get("promise_date") or "").strip(); loan.promise_date=date.fromisoformat(pd) if pd and pd not in {"-","NA"} else None
            requested=(row.get("officer_email") or "").strip().lower()
            eligible=[o for o in officers if pin in [p.strip() for p in o.pincodes.split(",") if p.strip()]]
            if requested:
                chosen=next((o for o in officers if o.email.lower()==requested), None)
                if not chosen: raise ValueError("officer_email does not match an active officer")
                if pin not in [p.strip() for p in chosen.pincodes.split(",") if p.strip()]: raise ValueError("Selected officer is not mapped to this pincode")
            else:
                pool=eligible
                chosen=min(pool, key=lambda o: db.query(models.Loan).filter(models.Loan.assigned_to==o.id, models.Loan.status=="open", models.Loan.id!=loan.id).count()) if pool else None
            if chosen: loan.assigned_to=chosen.id
            else: loan.assigned_to=None
            db.flush()
            if loan.promise_date and chosen:
                existing_promise=db.query(models.Promise).filter_by(loan_id=loan.id, promise_date=loan.promise_date).first()
                if not existing_promise:
                    promise_status="broken" if loan.promise_date < datetime.now(ZoneInfo("Asia/Kolkata")).date() else "upcoming"
                    db.add(models.Promise(loan_id=loan.id, officer_id=chosen.id, promise_date=loan.promise_date, amount=loan.outstanding, status=promise_status, reminder_status="draft"))
            snapshot=db.query(models.LoanDpdSnapshot).filter_by(loan_id=loan.id, snapshot_date=datetime.now(ZoneInfo("Asia/Kolkata")).date()).first()
            if snapshot: snapshot.dpd=loan.dpd
            else: db.add(models.LoanDpdSnapshot(loan_id=loan.id, snapshot_date=datetime.now(ZoneInfo("Asia/Kolkata")).date(), dpd=loan.dpd))
            db.commit()
            if is_new: created+=1
            else: updated+=1
            if not chosen: unassigned+=1
        except Exception as exc:
            db.rollback()
            errors.append({"line":line,"error":str(exc)})
    db.commit()
    return {"created":created,"updated":updated,"unassigned":unassigned,"errors":errors,"message":"Import processed; invalid rows were skipped. Loans without a matching territory officer remain unassigned."}

@app.get("/loans")
def list_loans(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    q=db.query(models.Loan).filter(models.Loan.status=="open")
    if user.role=="officer": q=q.filter(models.Loan.assigned_to==user.id)
    elif user.branch: q=q.filter(models.Loan.branch_name==user.branch.name)
    rows=q.all(); result=[]
    for loan in rows:
        broken=db.query(models.Promise).filter(models.Promise.loan_id==loan.id, models.Promise.status=="broken").count()
        result.append(loan_dict(loan, db, broken))
    return sorted(result,key=lambda x:x["priority"]["score"],reverse=True)

def loan_dict(loan, db, broken=0):
    officer=db.get(models.User,loan.assigned_to) if loan.assigned_to else None
    priority=score_loan(loan,broken)
    if loan.priority_override is not None:
        priority={"score":loan.priority_override,"reasons":["Manager-adjusted priority",loan.priority_override_reason or "Manual review requested",*priority["reasons"][:1]][:3]}
    return {"id":loan.id,"loan_id":loan.loan_id,"borrower_name":loan.borrower_name,"pincode":loan.pincode,"branch_name":loan.branch_name,"outstanding":loan.outstanding,"dpd":loan.dpd,"promise_date":loan.promise_date.isoformat() if loan.promise_date else None,"payment_history":loan.payment_history,"assigned_to":loan.assigned_to,"officer_name":officer.name if officer else "Unassigned","status":loan.status,"priority":priority}

@app.get("/loans/{loan_pk}")
def loan_detail(loan_pk:int, db:Session=Depends(get_db), user:models.User=Depends(current_user)):
    loan=db.get(models.Loan,loan_pk)
    if not loan: raise HTTPException(404,"Loan not found")
    if user.role=="officer" and loan.assigned_to!=user.id: raise HTTPException(403,"Loan is not assigned to you")
    if user.role=="manager" and user.branch and loan.branch_name!=user.branch.name: raise HTTPException(404,"Loan not found")
    data=loan_dict(loan,db)
    data["outcomes"]=[{"outcome":o.outcome,"notes":o.notes,"occurred_at":o.occurred_at.isoformat()} for o in db.query(models.Outcome).filter_by(loan_id=loan.id).order_by(models.Outcome.occurred_at.desc()).limit(10)]
    data["promises"]=[{"id":p.id,"promise_date":p.promise_date.isoformat(),"amount":p.amount,"status":p.status,"reminder_status":p.reminder_status} for p in db.query(models.Promise).filter_by(loan_id=loan.id).order_by(models.Promise.promise_date.desc()).all()]
    return data

@app.post("/loans/{loan_pk}/outcomes")
def log_outcome(loan_pk:int, body:schemas.OutcomeIn, db:Session=Depends(get_db), user:models.User=Depends(require_roles("officer"))):
    loan=db.get(models.Loan,loan_pk)
    if not loan or loan.assigned_to!=user.id: raise HTTPException(404,"Assigned loan not found")
    if body.outcome not in {"paid","promise","not_reachable","dispute"}: raise HTTPException(422,"Unsupported outcome")
    existing=db.query(models.Outcome).filter_by(event_uuid=body.event_uuid).first()
    if existing:
        if existing.officer_id != user.id or existing.loan_id != loan.id:
            raise HTTPException(409, "Idempotency key has already been used for another event")
        return {"status":"already_synced","outcome_id":existing.id}
    local=to_ist(body.occurred_at)
    now_ist=datetime.now(ZoneInfo("Asia/Kolkata"))
    if local > now_ist + timedelta(minutes=5): raise HTTPException(422, "Contact timestamp cannot be in the future")
    if not allowed_contact_time(local):
        raise HTTPException(403,"Borrower contact is permitted only between 08:00 and 19:00 IST")
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(422, "Latitude and longitude must be provided together")
    if body.outcome == "promise":
        if not body.promise_date: raise HTTPException(422,"Promise date is required for promise outcome")
        if body.promise_date < local.date(): raise HTTPException(422,"Promise date cannot be in the past")
        if body.promise_amount is not None and body.promise_amount > float(loan.outstanding):
            raise HTTPException(422,"Promise amount cannot exceed the outstanding balance")
    outcome=models.Outcome(event_uuid=body.event_uuid,loan_id=loan.id,officer_id=user.id,outcome=body.outcome,notes=body.notes,latitude=body.latitude,longitude=body.longitude,occurred_at=local.replace(tzinfo=None))
    db.add(outcome)
    if body.outcome=="promise":
        p=models.Promise(loan_id=loan.id,officer_id=user.id,promise_date=body.promise_date,amount=body.promise_amount,status="upcoming",reminder_status="draft")
        db.add(p); loan.promise_date=body.promise_date
    elif body.outcome=="paid":
        loan.status="resolved"
        db.query(models.Promise).filter(models.Promise.loan_id==loan.id, models.Promise.status=="upcoming").update({"status":"fulfilled"}, synchronize_session=False)
    db.add(models.Activity(officer_id=user.id,loan_id=loan.id,action="outcome_logged",detail=body.outcome,latitude=body.latitude,longitude=body.longitude,occurred_at=local.replace(tzinfo=None)))
    db.commit()
    return {"status":"synced","outcome_id":outcome.id}

@app.post("/loans/{loan_pk}/priority-override")
def priority_override(loan_pk:int, body:dict, db:Session=Depends(get_db), user:models.User=Depends(require_roles("manager"))):
    loan=db.get(models.Loan,loan_pk)
    if not loan: raise HTTPException(404,"Loan not found")
    if user.branch and loan.branch_name!=user.branch.name: raise HTTPException(404,"Loan not found")
    score=body.get("score"); reason=str(body.get("reason", "")).strip()
    if not isinstance(score,int) or not 0 <= score <= 100: raise HTTPException(422,"Score must be an integer from 0 to 100")
    if not reason or len(reason)>300: raise HTTPException(422,"A short override reason is required")
    loan.priority_override=score; loan.priority_override_reason=reason
    db.add(models.Activity(officer_id=user.id,loan_id=loan.id,action="priority_override",detail=f"Score set to {score}: {reason}"))
    db.commit(); return {"status":"updated","loan":loan_dict(loan,db)}

@app.get("/promises")
def promises(db:Session=Depends(get_db), user:models.User=Depends(current_user)):
    q=db.query(models.Promise).join(models.Loan)
    if user.role=="officer": q=q.filter(models.Promise.officer_id==user.id)
    elif user.branch: q=q.filter(models.Loan.branch_name==user.branch.name)
    rows=q.order_by(models.Promise.promise_date).all(); today=datetime.now(ZoneInfo("Asia/Kolkata")).date(); out=[]
    for p in rows:
        if p.status=="upcoming" and p.promise_date<today: p.status="broken"
        out.append({"id":p.id,"loan_id":p.loan_id,"loan_ref":p.loan.loan_id,"borrower":p.loan.borrower_name,"promise_date":p.promise_date.isoformat(),"amount":p.amount,"status":p.status,"reminder_status":p.reminder_status})
    db.commit(); return out

@app.post("/promises/{promise_id}/reminder-draft")
def reminder_draft(promise_id:int, body:schemas.ReminderIn, db:Session=Depends(get_db), user:models.User=Depends(current_user)):
    p=db.get(models.Promise,promise_id)
    if not p: raise HTTPException(404,"Promise not found")
    if user.role=="officer" and p.officer_id!=user.id: raise HTTPException(403,"Not your promise")
    if user.role=="manager" and user.branch and p.loan.branch_name!=user.branch.name: raise HTTPException(404,"Promise not found")
    loan=p.loan
    if body.language not in {"hi","en"}: raise HTTPException(422,"Language must be hi or en")
    templates={
      "en": f"Dear {loan.borrower_name}, this is a courteous reminder regarding your loan account {loan.loan_id}. Our records show a payment commitment for {p.promise_date.isoformat()}. Please contact your assigned officer if you need assistance. Thank you.",
      "hi": f"नमस्ते {loan.borrower_name}, आपके ऋण खाते {loan.loan_id} के संबंध में यह एक विनम्र अनुस्मारक है। हमारे रिकॉर्ड के अनुसार भुगतान की निर्धारित तारीख {p.promise_date.isoformat()} है। सहायता के लिए कृपया अपने अधिकारी से संपर्क करें। धन्यवाद।"
    }
    draft=templates[body.language]
    if not reminder_language_allowed(draft):
        raise HTTPException(422,"Reminder blocked by the respectful-language filter")
    p.reminder_status="drafted"; db.commit()
    return {"language":body.language,"draft":draft,"requires_officer_approval":True,"delivery":"mock_only","policy":"No message is sent automatically. Only the assigned officer may approve during the permitted contact window."}

@app.post("/promises/{promise_id}/mark-reminder-approved")
def approve_reminder(promise_id:int, db:Session=Depends(get_db), user:models.User=Depends(require_roles("officer"))):
    p=db.get(models.Promise,promise_id)
    if not p: raise HTTPException(404,"Promise not found")
    if p.officer_id!=user.id: raise HTTPException(403,"Only the assigned officer can approve this reminder")
    if not allowed_contact_time(datetime.now(ZoneInfo("Asia/Kolkata"))):
        raise HTTPException(403,"Reminder approval is permitted only between 08:00 and 19:00 IST")
    p.reminder_status="approved_mock"; db.add(models.Activity(officer_id=user.id,loan_id=p.loan_id,action="reminder_approved_mock",detail=f"Promise {p.id}")); db.commit()
    return {"status":"approved_mock","sent":False}

@app.get("/dashboard")
def dashboard(db:Session=Depends(get_db), user:models.User=Depends(require_roles("manager"))):
    all_loans=db.query(models.Loan).all()
    if user.branch:
        all_loans=[l for l in all_loans if l.branch_name == user.branch.name]
    loans=[l for l in all_loans if l.status=="open"]
    total=len(loans)
    buckets={"1-30":sum(1 for l in loans if 1<=l.dpd<=30),"31-60":sum(1 for l in loans if 31<=l.dpd<=60),"61+":sum(1 for l in loans if l.dpd>60)}
    def transitions_for(branch_name=None):
        branch_loans=[l for l in all_loans if branch_name is None or l.branch_name==branch_name]
        transitions=[]
        for loan in branch_loans:
            snapshots=db.query(models.LoanDpdSnapshot).filter_by(loan_id=loan.id).order_by(models.LoanDpdSnapshot.snapshot_date.desc()).limit(2).all()
            if len(snapshots)==2:
                transitions.append((snapshots[1].dpd,snapshots[0].dpd))
        return transitions
    overall_rate=calculate_roll_rate(transitions_for())
    def branch_roll_rate(branch_name):
        return calculate_roll_rate(transitions_for(branch_name))
    promise_query=db.query(models.Promise).join(models.Loan)
    if user.branch: promise_query=promise_query.filter(models.Loan.branch_name==user.branch.name)
    broken=promise_query.filter(models.Promise.status=="broken").count()
    officer_rows=[]
    officer_query=db.query(models.User).filter_by(role="officer")
    if user.branch_id: officer_query=officer_query.filter(models.User.branch_id==user.branch_id)
    today_ist=datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    for o in officer_query.all():
        officer_rows.append({"name":o.name,"assigned":db.query(models.Loan).filter_by(assigned_to=o.id).count(),"visits_today":db.query(models.Activity).filter(models.Activity.officer_id==o.id,models.Activity.action=="outcome_logged",func.date(models.Activity.occurred_at)==today_ist).count()})
    branches=[]
    for branch in ([user.branch] if user.branch else db.query(models.Branch).all()):
        branch_loans=[l for l in loans if l.branch_name==branch.name]
        b1=sum(1 for l in branch_loans if 1<=l.dpd<=30); b2=sum(1 for l in branch_loans if 31<=l.dpd<=60)
        branches.append({"branch":branch.name,"dpd_1_30":b1,"dpd_31_60":b2,"roll_rate":branch_roll_rate(branch.name)})
    return {"total_loans":total,"outstanding_total":round(sum(float(l.outstanding) for l in loans),2),"buckets":buckets,"roll_rate":overall_rate,"roll_rate_basis":"latest two dated DPD snapshots; unavailable until a prior 1–30 DPD cohort snapshot exists","broken_promises":broken,"officers":officer_rows,"branches":branches}

@app.get("/activity")
def activity(db:Session=Depends(get_db), user:models.User=Depends(current_user)):
    q=db.query(models.Activity).outerjoin(models.Loan)
    if user.role=="officer": q=q.filter(models.Activity.officer_id==user.id)
    elif user.branch: q=q.filter(models.Loan.branch_name==user.branch.name)
    rows=q.order_by(models.Activity.occurred_at.desc()).limit(100).all()
    return [{"id":a.id,"officer":db.get(models.User,a.officer_id).name,"loan_id":db.get(models.Loan,a.loan_id).loan_id if a.loan_id else None,"action":a.action,"detail":a.detail,"latitude":a.latitude,"longitude":a.longitude,"occurred_at":a.occurred_at.isoformat()} for a in rows]
