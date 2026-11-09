# Security Notes

This repository is a synthetic-data engineering MVP. Do not use it with real borrower data.

## Implemented controls
- Password hashing with bcrypt.
- JWT authentication and backend role guards.
- Branch-level manager scope and assigned-loan officer scope on key routes.
- CSV extension, size, encoding, pincode, amount, DPD and duplicate-ID validation.
- SQLAlchemy ORM query construction.
- Unique event UUID for offline outcome idempotency; UUID reuse across another officer/loan is rejected.
- Server-side Asia/Kolkata contact-window check against the recorded event timestamp.
- Production startup rejects the default/short JWT secret.

## Not implemented / required before production
- HTTPS termination, HSTS, secure cookie session model or token revocation.
- Rate limiting, account lockout, MFA and device/session management.
- Encryption at rest, field-level encryption, offline IndexedDB/localStorage encryption and remote wipe.
- DPDP notice/consent, retention, erasure and data-principal request workflows.
- Tamper-resistant trusted timestamps / device attestation.
- Full security test, penetration test, dependency scanning and operational alerting.
- Managed secret store, database backups and tested recovery.

Report vulnerabilities privately to the project owner. Never test against real borrower data or a production NBFC environment without written authorisation.
