# PHC module blueprint

Module: PHC Management System, code `phc`, environment `module-only`, docs folder `docs/09-phc/`.
Specification ids: `CFR-PHC-`, `AFR-PHC-`, `PHC-UC-`, `PHC-BR-`, `BW-PHC-`, `CW-PHC-`.

## Phase 0 inventory

- Requirements: 12 CFRs (`CFR-PHC-001`–`012`) and 38 AFRs (`AFR-PHC-001`–`038`).
- Use cases: 20 live (`PHC-UC-01`–`16`, `19`–`22`). `PHC-UC-17` and `PHC-UC-18` are retired; their
  behaviour moved to `AFR-PHC-023/030`, `PHC-BR-11/13` (notifications) and `AFR-PHC-025/026`,
  `PHC-BR-07`, `PHC-UC-09` (low-stock alert). Neither retired id is cited in code.
- Business rules: 14 live (`PHC-BR-01`–`14`); none retired.
- Workflows: basis `BW-PHC-01`–`04`, composite `CW-PHC-01` (reimbursement) and `CW-PHC-02`
  (requisition). Legacy `PHC-WF-01/02` are superseded by those; `PHC-WF-03/004` are retired because
  schedule work is one actor's.
- The traceability workbook's `AFR_Traceability` and `CFR_Rollup` mapping columns are empty, and the
  use cases' "Related CFRs / AFRs" fields are blank. Coverage below was derived by reading each rule.
- Actors: Patient (Employee or Student), Employee, PHC Staff (PHC Administrator is the same actor for
  schedules), Accounts & Audit, Approving Authority.

## Phase 1 answers

1. **One bounded context.** Every rule is PHC-internal.
2. **Other modules.** Only `modules.directory.contracts` (`get_users`, `search`) for patient lookup
   and report demographics. Nothing else is needed and nothing is added to another module.
3. **Identity.** Every person is a plain integer user id (`patient_user_id`, `user_id`,
   `originator_user_id`, …). No foreign key leaves the module.
4. **Roles.** Derived from the actor inventory, with citations:
   | Spec actor | Designation / kind | Cited in |
   |---|---|---|
   | Patient (student) | `student` | PHC-UC-01, 02, 03; PHC-BR-02 |
   | Patient / Employee | `faculty`, `staff` | PHC-UC-04, 05; PHC-BR-04 |
   | PHC Staff | `PHC Staff` | PHC-UC-06–15, 22; PHC-BR-07, 08, 10, 11 |
   | Accounts & Audit | `Accounts & Audit` | PHC-UC-19, 21; PHC-BR-08 |
   | Approving Authority | `Approving Authority` | PHC-UC-16, 20; PHC-BR-08, 10 |

   The three office designations do not exist in `fusion-dev.dump`'s `globals_designation`
   (open question 2).
5. **Scope.** `selectors/scoping.py`: a patient sees only their own records and claims; PHC Staff see
   every record except their own; a claim-processing office sees every claim except its own; the
   Approving Authority sees every requisition except one it raised. Out of scope is 404.
6. **Time.** Nothing expires, escalates or advances on a date. No beat entries.
7. **Money.** Claims carry an amount but no balance is spent, so no ledger. Stock levels have an
   append-only `StockAdjustment` history beside the level.
8. **Policy.** The PHC-BR-06 submission window is an effective-dated, never-edited
   `ReimbursementPolicy`. With none in effect, submission answers 409 `policy_missing` and
   `phc_readiness` names the gap.

## Step 3.1 (a) — Traceability

The generated [phc-reference.md](phc-reference.md) links every id below to its exact line.

| Id | What it requires | Layer | Enforcement point |
|---|---|---|---|
| PHC-BR-01 | Patients see the published weekly schedule with today's attendance | selectors | `scoping.schedules_for` |
| PHC-BR-02 | Patients read only their own records, read-only | selectors + api | `scoping.visits_for`; record views are GET-only |
| PHC-BR-03 | Role-based access to every function | api | `_Gates.get_permissions`: module grant, then permission |
| PHC-BR-04 | Only employees claim | domain | `rules.require_employee`, and only `faculty`/`staff` hold `phc.claim.create` |
| PHC-BR-05 | Claim links the claimant's own recorded prescription | services | `submit_claim` via `scoping.own_prescriptions` |
| PHC-BR-06 | Claim within the configured window from the expense date | domain + models | `rules.check_submission_window`, `ReimbursementPolicy` |
| PHC-BR-07 | Low-stock alert when level < threshold | domain + services | `rules.is_low_stock`; `adjust_stock` writes `LowStockAlert` |
| PHC-BR-08 | Claim order PHC Staff → A&A → Authority → A&A | domain | `CLAIM_TRANSITIONS` |
| PHC-BR-09 | Immutable audit of patient-record, stock and claim-status changes | services + DB | `trail.audit`; migration 0002 triggers |
| PHC-BR-10 | Requisition must be approved before fulfilment | domain | `REQUISITION_TRANSITIONS` |
| PHC-BR-11 | Notify the originator of a requisition decision | services | `requisitions.transition` |
| PHC-BR-12 | Reports anonymised | domain + selectors | `reports.suppress`; `selectors/reports.py` returns counts only |
| PHC-BR-13 | Notify the claimant on every status change | services | `transition_claim` |
| PHC-BR-14 | Submitted claim never edited or reopened | models + DB + domain | `ReimbursementClaim.save`, trigger, terminal states |
| PHC-UC-01–03 | View schedule, view own records, download own PDF | api + selectors | `ScheduleListView`, `VisitListView`, `RecordsPdfView` |
| PHC-UC-04, 05 | Submit and track a claim | services + api | `submit_claim`, `ClaimListView`/`ClaimDetailView` |
| PHC-UC-06 | Record visit and prescription | services | `records.record_visit` |
| PHC-UC-07, 08, 22 | Maintain, attend, create and publish schedules | services | `services/schedules.py` |
| PHC-UC-09 | Adjust stock | services | `inventory.adjust_stock` |
| PHC-UC-10, 14, 16 | Raise, fulfil, decide requisitions | services | `services/requisitions.py` |
| PHC-UC-11, 12 | Ambulance log, advisories | services | `services/operations.py` |
| PHC-UC-13 | Reports | selectors | `selectors/reports.py` |
| PHC-UC-15, 19, 20, 21 | Review, verify, sanction, pay | domain + services | `CLAIM_TRANSITIONS`, `transition_claim` |
| BW-PHC-01/02, CW-PHC-01 | Claim approved-and-paid / rejected | domain | `CLAIM_TRANSITIONS` |
| BW-PHC-03/04, CW-PHC-02 | Requisition approved-and-fulfilled / rejected | domain | `REQUISITION_TRANSITIONS` |
| CFR-PHC-001–012, AFR-PHC-001–038 | As above, one link each | — | see `phc-reference.md` |

## Step 3.2 (b) — Domain model

| Entity | Key fields | Invariants (database unless noted) |
|---|---|---|
| `DoctorSchedule` + `ScheduleSlot` | doctor, specialization, published flag/time; day, start, end | slot ends after it starts; one slot per (schedule, day, start); published ⇒ published_at |
| `DoctorAttendance` | schedule, date, status | one row per schedule per day |
| `PatientVisit` + `Prescription` | patient id, date, complaint, diagnosis, recorder; medicine, dosage, days | recorder ≠ patient |
| `ReimbursementPolicy` | effective_from, window_days, includes_last_day | append-only (trigger); window > 0; one per effective date |
| `ReimbursementClaim` | claimant, prescription, expense date, amount, status | amount > 0; frozen fields (trigger + `save`); no delete |
| `ClaimAction` | claim, actor, event, from, to | append-only (trigger) |
| `InventoryItem` | name, unit, stock level, reorder threshold | unique name; level ≥ 0; threshold ≥ 0 |
| `StockAdjustment` | item, delta, level after | append-only; delta ≠ 0 |
| `LowStockAlert` | item, adjustment, level, threshold | append-only; level < threshold |
| `Requisition` + `RequisitionLine` | originator, purpose, status, decision, fulfilment; item, quantity | decided ⇒ decided_at; fulfilled ⇒ fulfilled_at; quantity > 0; one line per item |
| `AmbulanceLog` | used_at, patient name, destination, recorder | — |
| `HealthAdvisory` | title, body, published_at, publisher | — |
| `AuditRecord`, `Notification` | actor/recipient, resource, action/message | append-only (trigger) |

## Step 3.3 (c) — State machines

Claims (`CLAIM_TRANSITIONS`, keyed by permission rather than role name):

| State | Event | Permission | Next |
|---|---|---|---|
| pending_phc_review | forward | phc.claim.review | pending_accounts_verification |
| pending_accounts_verification | verify | phc.claim.update | pending_sanction |
| pending_sanction | approve | phc.claim.approve | approved_for_payment |
| pending_sanction | reject | phc.claim.approve | rejected (terminal) |
| approved_for_payment | pay | phc.claim.update | reimbursed (terminal) |

Requisitions (`REQUISITION_TRANSITIONS`); submission creates the row straight into
`pending_approval` (PHC-UC-10 M4):

| State | Event | Permission | Next |
|---|---|---|---|
| pending_approval | approve | phc.requisition.approve | approved |
| pending_approval | reject | phc.requisition.approve | rejected (terminal) |
| approved | fulfill | phc.requisition.update | fulfilled (terminal) |

## Step 3.4 (d) — Permissions

Exactly as `modules/phc/registry.py`: 26 permissions, `SYSTEM_PERMISSIONS = []`,
`SCOPE_PERMISSIONS = []`, and `ROLE_GRANTS` for `student`, `faculty`, `staff`, `PHC Staff`,
`Accounts & Audit`, `Approving Authority`. Each claim stage is held by exactly one office.

## Step 3.5 (e) — Endpoints

All under `/api/v1/phc/`, behind `HasModuleGrant("phc")` then `HasPermission(...)`; writes carry
`throttle_scope = "phc_write"` (300/hour).

| Method | Path | Permission | Rules |
|---|---|---|---|
| GET / POST | `schedules` | schedule.view / schedule.create | PHC-UC-01, 22; BR-01 |
| PUT | `schedules/<id>` | schedule.update | PHC-UC-07 |
| POST | `schedules/<id>/publish` | schedule.publish | PHC-UC-22 |
| POST | `schedules/<id>/attendance` | attendance.update | PHC-UC-08 |
| GET | `patients?q=` | patient.view | AFR-PHC-006 |
| GET / POST | `records` | record.view / record.create | PHC-UC-02, 06; BR-02, 09 |
| GET | `records/<id>` | record.view | PHC-UC-02 |
| GET | `records/pdf?ids=` | record.view | PHC-UC-03 |
| GET / POST | `claims` | claim.view / claim.create | PHC-UC-04, 05; BR-04–06 |
| GET | `claims/prescriptions` | claim.create | BR-05 |
| GET | `claims/<id>` | claim.view | PHC-UC-05 |
| POST | `claims/<id>/transition` | claim.review / update / approve | PHC-UC-15, 19–21; BR-08, 09, 13, 14 |
| GET / POST | `inventory` | inventory.view / inventory.create | BR-09 |
| GET | `inventory/alerts` | inventory.view | BR-07 |
| POST | `inventory/<id>/adjust` | inventory.update | PHC-UC-09; BR-07, 09 |
| GET / POST | `requisitions` | requisition.view / requisition.create | PHC-UC-10 |
| POST | `requisitions/<id>/transition` | requisition.approve / update | PHC-UC-14, 16; BR-10, 11 |
| GET / POST | `ambulance` | ambulance.view / ambulance.create | PHC-UC-11 |
| GET / POST | `advisories` | advisory.view / advisory.publish | PHC-UC-12 |
| GET | `reports` | report.view | PHC-UC-13; BR-12 |
| GET | `notifications` | notification.view | BR-11, 13 |

Client routes: each of the nine pages (`schedule`, `advisories`, `records`, `claims`, `inventory`,
`requisitions`, `ambulance`, `reports`, `notifications`) is wrapped in `RequirePermission` with its
nav item's `required_permission`; shared pages also gate each control with `can()`.

`Fusion-client` sidebar entry for `INTEGRATED_MODULES`:
`{ id: "phc", label: "Primary Health Centre", icon: "FirstAidKit", to: "/phc", section: "Health Services" }`.

## Step 3.6 (f) — Contracts

`modules/phc/contracts.py` exposes nothing: no other module consumes PHC data. PHC uses
`modules.directory.contracts.get_users` and `search`, which already exist. No IAM change is needed.

## Step 3.7 (g) — Scheduled work

None. `schedule.py` exports empty `BEAT_SCHEDULE` and `TASK_ROUTES`, merged in `config/celery.py`.

## Step 3.8 (h) — Open questions

1. **PHC-BR-06 window.** The spec gives no length, boundary or owner. The module stores both the
   length and whether the last day counts as a policy version set with
   `manage.py phc_configure_window`; until one exists, claims are refused with a clear message.
   The value itself must come from the institute.
2. **Office designations.** `PHC Staff`, `Accounts & Audit` and `Approving Authority` are not in
   `globals_designation` in `fusion-dev.dump`. They are used as spelled in the spec, provisioned for
   testing with `Fusion_System_Administrator`'s `assign_role`; production creation is the academic
   office's decision.
3. **Negative stock.** The spec says an invalid adjustment is rejected (PHC-UC-09 E1) but does not
   define invalid. The module refuses a zero change and any change that would take the level below
   zero.
4. **Duplicate claims.** The spec allows a new claim after rejection (PHC-BR-14) and does not limit
   claims per prescription, so none is imposed.
5. **Anonymisation threshold.** PHC-BR-12 requires anonymised output without a method. Reports return
   counts only and show any count from 1 to 4 as `<5`.
6. **Docs folder number.** `09` follows the assignment number; no other number was assigned.

## Approval record

- 2026-11-23: Student 2 (Kousik) approved this blueprint in writing, typed into Student 1's builder
  chat: "I have read docs/09-phc/phc-blueprint.md (PHC module, Assignment 9) against the PHC
  specification, and I approve it, including its open questions in Step 3.8." An earlier relayed
  "fine you can start the code generation" predates this version and is superseded.
- Shared-file changes (all pre-approved by Step 4.0 of the prompt): `config/settings/base.py`,
  `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, the
  regenerated schema, manifest and permission catalog, and `ops/docs/phc_reference.py`.
- New dependencies: none.
