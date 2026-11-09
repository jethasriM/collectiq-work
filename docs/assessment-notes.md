# Engineering Assessment Notes

## Problem addressed

The original workflow separates overdue-loan data, field assignment, visit outcomes and management reporting across Excel, WhatsApp and notebooks. CollectIQ brings those activities into one auditable workflow.

## Core slice delivered

- CSV import and row-level validation.
- Pincode/territory-based workload assignment.
- Role-based officer priority queue.
- Explainable priority score and manager override.
- Four outcome types and optional GPS capture.
- Promise-to-pay tracking and bilingual reminder drafts.
- Activity history.
- Manager DPD distribution and cohort roll-rate reporting.
- IndexedDB offline event queue with retry and idempotency.

## Important assumptions

- The brief provides three sample loan records but no phone numbers, precise borrower addresses, branch master, historical daily DPD snapshots or labelled payment outcomes.
- All additional records are synthetic.
- A pincode can be used for coarse territory matching, not precise navigation to a borrower.
- Roll rate requires at least two dated snapshots and a defined prior-DPD cohort.
- Payment and message delivery are mocked.

## Defensible AI explanation

The priority engine is intentionally a deterministic heuristic. Its output is a relative work-queue ranking, not a calibrated risk probability. It uses the available features and returns human-readable reasons. A manager can override the rank with a recorded reason. A trained model is deferred until the client supplies an appropriately governed historical dataset and outcome labels.

## Limitations that should be stated in a review

- The current interface is English; Hindi reminder drafts are supported, but complete Hindi localisation is not yet complete.
- Offline records are stored in browser IndexedDB without application-level encryption. Use synthetic demo data only.
- Browser event timestamps are not a tamper-proof source of truth. Production compliance needs trusted device-time controls and monitoring.
- The MVP has no Alembic migration history, production security audit, DPDP workflow, real telephony/SMS connector, or production ML validation.

## Suggested live demo sequence

1. Log in as manager.
2. Import the sample CSV.
3. Show rejected-row validation by trying a duplicate or malformed row.
4. Show pincode assignment and unassigned case if no officer has that territory.
5. Log in as officer Rahul.
6. Open a loan and explain the top-three priority reasons.
7. Log a Promise to Pay outcome with GPS permission.
8. Open the promise tracker and generate a Hindi reminder draft.
9. Approve the mock draft and explicitly show that it is not sent.
10. Show activity history and manager dashboard.
11. Demonstrate offline queue only after the app has loaded and cached the shell/list.

## Do not claim

- That the score predicts NPA or repayment probability.
- That the roll rate has improved due to the product.
- That the application is RBI-certified or legally compliant by virtue of this prototype.
- That a phone call, SMS, WhatsApp message or payment was actually made.
- That offline borrower data is encrypted.
