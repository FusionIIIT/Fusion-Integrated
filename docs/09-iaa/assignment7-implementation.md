# Assignment 7 — Internal Audit and Accounts (IAA)

## Specification basis
Scope is based on the uploaded IAA problem statement, CFR/AFR registry, use cases, business rules, workflows and traceability matrix. The registry contains 18 consolidated CFRs and 75 AFRs; the workflow specification defines 19 basis and four composite workflows. The supplied RTM's AFR-level UC/BR/WF/transition/coverage columns are blank despite a full-coverage summary count. This discrepancy is recorded as a specification-source gap; full AFR-level traceability is not claimed.

## CFR coverage map
| CFR | Implemented responsibility |
|---|---|
| 01 | Expense/voucher drafts, submit-time validation, creator-scoped edit and history |
| 02 | Finance queue, clarification questions and requester responses |
| 03 | Internal Process/Record with explicit `monetary_transfer_executed=false`; no payment processing |
| 04 | Configurable approval routes, HoD/Dean/Director authority steps, remarks and self-approval prevention |
| 05 | Per-step deadlines, Celery Beat escalation task and management command |
| 06 | Department budget checks with locked reads and shortfall anomaly hand-off |
| 07 | Manual and rule-triggered anomalies with Open/Resolved/Escalated lifecycle |
| 08 | TA-specific trip dates/purpose, attachments and submission validation |
| 09 | Financial-year TA policy verification and clarification workflow |
| 10 | Configurable high-value TA threshold and approval routing |
| 11 | Verified standard TA and approved TA can be internally recorded; no transfer |
| 12 | Auditor role can inspect financial records and raise audit observations |
| 13 | Observation response, evidence references, verification, re-open and close |
| 14 | Role-scoped status/turnaround summary and CSV export |
| 15 | Own-request tracking and recipient-scoped notification/read state |
| 16 | Financial-year, budget, approval-rule and local IAA role-assignment configuration |
| 17 | Fusion active-role switching and action-time role attribution |
| 18 | Append-only audit log for module actions and configuration changes |

## Runtime configuration
System Admin must configure financial-year dates, budgets, TA policy, document requirements, high-value TA threshold, approval hierarchy and timeout values. Institutional monetary limits and approval periods are not hard-coded.

## Integration limits needing deployment verification
- Fusion IAM remains the authority for effective role and module grants. The existing repository IAM client provides active-role switching, not role-grant mutation; local IAA assignments are audit/configuration records and do not provision IAM grants.
- Supporting documents store storage references and metadata. Production must provide an authorized upload/storage service and verify references.
- Celery Beat and workers must run to process overdue approvals.
- The RTM atomic mappings need completion by the specification owner before claiming full AFR coverage.
- PostgreSQL, live IAM, storage and notification delivery require integration verification.

IAA Process/Record is internal governance only; it does not initiate bank transfers or payments.
