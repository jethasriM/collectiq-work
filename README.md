# CollectIQ — NBFC Loan Collection Management System

**Submission:** Full-stack engineering MVP  
**Product type:** Mobile-first field collection operations and branch monitoring  
**Status:** Implemented MVP source code; local environment verification required before submission/demo.

CollectIQ replaces spreadsheet/WhatsApp-driven collection follow-up with a role-based workflow for managers and field officers. It includes loan import and assignment, explainable prioritisation, outcome logging, promise tracking, reminder drafts, activity history, offline event queuing and branch analytics.

> **Important:** This is a synthetic-data engineering demonstration, not a production NBFC deployment or legal/compliance certification. Do not upload real borrower data. Payment processing, calls and message delivery are mocked. The priority engine is an explainable heuristic, not a trained or validated credit/recovery model.

## 1. Stack

| Layer | Implementation |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| UI | Custom responsive CSS, Lucide icons, Recharts dependency |
| API | Python, FastAPI, Pydantic |
| Persistence | SQLAlchemy; PostgreSQL in Docker, SQLite for local quick start |
| Authentication | JWT bearer tokens, bcrypt password hashing, role guards |
| Offline | IndexedDB event queue, cached loan-list snapshot, service-worker shell cache |
| Analytics | Dated DPD snapshots and cohort-based roll-rate calculation |
| Tests | Pytest unit tests |
| Runtime | Docker Compose |

## 2. Quick start (Docker — recommended)

Prerequisites: Docker Desktop / Docker Engine with Compose.

1. Extract the project and open a terminal in the project root.
2. Create the environment file:
   - Windows PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Change `SECRET_KEY` in `.env` to a unique random value. For production, use at least 32 random characters and set `ENVIRONMENT=production`.
4. Start the stack: `docker compose up --build`
5. Open the frontend at `http://localhost:5173`.
6. Open API docs at `http://localhost:8000/docs` and health at `http://localhost:8000/health`.

Stop with `Ctrl+C`; run `docker compose down`. To remove the demo database volume and reset the seed data, run `docker compose down -v` (this permanently deletes the local demo database).

## 3. Local development without Docker

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The default local database is `sqlite:///./collectiq.db`. Override `DATABASE_URL` to use PostgreSQL.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

If the API is not at `http://localhost:8000`, set `VITE_API_URL` in `frontend/.env.local` before starting Vite.

## 4. Demo accounts

All accounts are seeded for local demonstration only. Password: `DemoPass123!`

| Role | Email |
|---|---|
| Branch manager | `manager@collectiq.demo` |
| Field officer | `rahul@collectiq.demo` |
| Field officer | `neha@collectiq.demo` |
| Field officer | `imran@collectiq.demo` |

Change or remove seeded credentials before any shared deployment. Seed records use fictional business names and synthetic data.

## 5. Main user journeys

### Manager

1. Sign in as the branch manager.
2. Open **Import & assign** and upload `backend/sample_data/overdue_loans.csv` (also available from the frontend public sample file).
3. Review the import summary. Valid rows are upserted by unique loan ID; duplicate IDs within one file and invalid rows are rejected with row-level errors.
4. Assignment chooses an active officer whose configured pincode territory matches, then selects the eligible officer with the lowest open-loan workload. If no officer covers a pincode, the loan remains unassigned instead of being silently assigned to the wrong territory.
5. Open **Overview** to view overdue buckets, outstanding balance, promises and roll-rate availability.
6. Open a loan to inspect priority reasons and optionally save an audited priority override.

### Field officer

1. Sign in as Rahul or Neha.
2. Open **My priority list** and select an assigned loan.
3. Review the AI advisory score and its explanation.
4. Select Paid, Promise to pay, Not reachable or Dispute; add required information and optionally capture GPS after granting browser permission.
5. Save the outcome. The API checks the event timestamp against 08:00–19:00 Asia/Kolkata.
6. Review promises, draft a Hindi or English template reminder and approve the mock draft. No external message is sent.
7. Review activity history.

### Offline demonstration

1. Sign in and load the officer queue while online.
2. Refresh once while still online so the production service worker can cache the app shell and static assets.
3. Open browser developer tools and switch the network to Offline.
4. Refresh the page. The demo restores the last signed-in user snapshot and cached loan list for offline work.
5. Save an outcome during the permitted contact window. It is persisted in IndexedDB with a unique event ID and user ID.
6. Restore network access. The app retries only the signed-in user's queued events; the backend uses the event ID as an idempotency key.

The demo stores a minimal user snapshot and JWT in browser localStorage to restore the field UI offline, and caches the loan list in IndexedDB. These values are not encrypted at rest. Use only synthetic data; production should use a secure session design, encrypted/minimised local storage and device controls.

## 6. CSV schema

Required columns: `loan_id,borrower_name,pincode,outstanding,dpd`.

Optional columns: `branch_name,promise_date,payment_history,officer_email`.

- Pincode must contain 5 or 6 digits.
- Outstanding must be a finite, non-negative number.
- DPD must be a non-negative integer.
- Upload limit: 5 MB.
- Branch managers may import only their own branch.
- An explicit officer email must refer to an active officer in the manager's branch whose territory includes the pincode.
- CSV rows without an eligible officer remain unassigned for manager review.

## 7. AI priority logic

`backend/app/scoring.py` contains a deterministic, explainable baseline score using DPD, outstanding amount, payment-history category and broken-promise count. The API returns a score from 0–100 and up to three reason strings. Managers can override a score with a required reason; the override is recorded in the activity log.

This is a **heuristic ranking aid**, not a probability of default, credit decision, or evidence that the target roll-rate improvement will be achieved. A production model would require historical labelled outcomes, temporal validation, calibration, bias testing, monitoring and approval by the NBFC.

## 8. Roll-rate definition

The dashboard does not infer a roll rate from a single static DPD distribution. It uses dated `LoanDpdSnapshot` records. A loan enters the cohort denominator only when its previous snapshot is 1–30 DPD; it counts as rolled when its latest snapshot is 31–60 DPD.

The displayed value is unavailable (`—`) until there are at least two dated snapshots for a loan in the eligible prior-DPD cohort. The synthetic demo seed includes a small illustrative historical cohort; daily CSV imports create/update the snapshot for that date. This avoids presenting an ungrounded bucket-mix ratio as a true roll rate.

## 9. API route groups

- `POST /auth/login`, `GET /auth/me`
- `GET /officers`
- `POST /loans/import`, `GET /loans`, `GET /loans/{loan_pk}`
- `POST /loans/{loan_pk}/outcomes`
- `POST /loans/{loan_pk}/priority-override`
- `GET /promises`
- `POST /promises/{promise_id}/reminder-draft`
- `POST /promises/{promise_id}/mark-reminder-approved` (mock approval; does not send)
- `GET /dashboard`, `GET /activity`
- `GET /health`

Swagger/OpenAPI is available at `/docs`.

## 10. Testing

Backend unit tests:

```bash
cd backend
python -m pytest -q
```

Frontend production build:

```bash
cd frontend
npm install
npm run test
npm run build
```

The submission test report records exactly which checks were executed in the build environment and which could not be run because package installation/network access was unavailable. Run both commands on the target machine before presenting the application.

## 11. Data model

Core tables: `branches`, `users`, `loans`, `outcomes`, `promises`, `activities`, and `loan_dpd_snapshots`.

- `Loan.loan_id` is unique.
- Outcome `event_uuid` is unique for offline idempotency.
- Monetary outstanding values use SQL `NUMERIC(14,2)`.
- Snapshot rows are unique per loan and snapshot date.
- Branch managers and officers are restricted to their branch / assigned loans at the API layer.

## 12. Known MVP boundaries

- No payment gateway, cash receipt, real dialler, SMS, WhatsApp or email delivery; those integrations are deliberately mocked.
- The `tel:` action is a placeholder because the supplied sample has no borrower phone numbers; no call is placed by the demo.
- Hindi is supported for reminder drafts; the overall application chrome is currently English, so a complete Hindi UI localisation remains follow-on work.
- Offline outcome events and loan-list snapshots persist in IndexedDB. Offline local data is not encrypted, and this demo does not implement device management or secure remote wipe.
- Contact-window enforcement validates the recorded client event timestamp server-side. A production system must add trusted device time / tamper controls and compliance monitoring; client timestamps alone are not a tamper-proof attestation.
- Database schema is created at startup for the MVP. Add Alembic migrations and a tested upgrade path before production.
- No formal DPDP consent/notice, retention/deletion workflow, encryption-at-rest policy, backup/restore, rate limiting, SIEM or penetration test is included.
- A trained ML model, weekly back-test scheduler and model monitoring are not implemented; the score is a baseline heuristic.

## 13. Production-readiness checklist

Before handling real borrower data: replace seed accounts; configure strong managed secrets; enforce HTTPS; use managed PostgreSQL with encryption, backups and tested restore; add Alembic migrations; implement privacy notice/consent and retention controls; encrypt/minimise offline data; implement device/session controls; validate reliable trusted contact timestamps; add structured audit/security monitoring and rate limits; perform security testing and legal/compliance review; validate the priority model on historical data; and load-test import, dashboard and sync paths.
