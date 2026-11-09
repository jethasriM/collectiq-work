# Verification Report

**Verification date:** 9 November 2026  
**Scope:** Static checks and backend unit tests performed in the provided build environment.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Python source compilation | PASS | `python -m py_compile backend/app/*.py` completed without syntax errors. |
| Backend unit tests | PASS | `14 passed` with `python -m pytest -q` from `backend/`. |
| Frontend TypeScript/JSX syntax transpilation | PASS | TypeScript `transpileModule` parsed `App.tsx`, `main.tsx`, `api.ts` and `offline.ts` without syntax diagnostics. |
| Docker Compose YAML parsing | PASS | `docker-compose.yml` parsed successfully with PyYAML. |
| Service worker JavaScript syntax | PASS | `node --check frontend/public/sw.js`. |

## Checks not completed in this environment

| Check | Status | Reason |
|---|---|---|
| Full frontend dependency install and Vite production build | NOT RUN | `npm install` could not reach `registry.npmjs.org` (DNS/network unavailable); offline npm cache did not contain required React typings. |
| Backend API integration tests / live server smoke test | NOT RUN | FastAPI, SQLAlchemy and JWT dependencies were not installed in the execution environment; `pip install` could not reach the package index. |
| Docker image build and Compose end-to-end run | NOT RUN | Docker CLI/daemon is not available in the execution environment. |
| Browser-based mobile/offline acceptance test | NOT RUN | No browser runtime or live API stack was available. |

## Required local acceptance checks before submission

Run these on a machine with internet access and Docker Desktop/Engine:

```bash
# From project root
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
# Change SECRET_KEY in .env before starting

docker compose up --build
```

Then verify:

1. `http://localhost:8000/health` returns `{"status":"ok","service":"collectiq-api"}`.
2. `http://localhost:8000/docs` opens Swagger.
3. Manager and all three officer demo accounts can sign in.
4. Manager imports the sample CSV and sees accepted/rejected row counts.
5. Rahul, Neha and Imran see only their own assigned open loans.
6. A field officer logs a promise and the manager sees it in the tracker.
7. A Paid outcome resolves the loan and fulfills its upcoming promises.
8. An outcome outside 08:00–19:00 IST is rejected by the API.
9. Replaying an event UUID for the same officer/loan is idempotent; reusing it for another loan/officer is rejected.
10. Two dated DPD snapshots produce a cohort roll-rate; a missing historical cohort displays `—`, not 0%.
11. Offline logging survives refresh, then syncs once after reconnect.
12. Run `npm install && npm run build` in `frontend/` and `python -m pytest -q` in `backend/`.

## Interpretation

The source tree passes the checks that were executable in this environment. The absence of a full dependency install and live runtime means this report does **not** claim an end-to-end deployment was verified here. Complete the local acceptance checklist before presenting it as a running application.
