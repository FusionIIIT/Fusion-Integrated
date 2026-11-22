# PHC blueprint

Module `phc` (Primary Health Care), delivery folder `docs/09-phc/`, branch `phc-21`.
This is the approved Phase-2 blueprint in the sense of
[`new-module-prompt.md`](../08-delivery/new-module-prompt.md) §3, kept current against the
shipped code. Student 2 approved the blueprint before implementation; this copy records the
as-built decisions and the retired-id map so a reviewer can trace every live rule to one
enforcement point.

## Live / retired id map

The v1.1 specification set is authoritative. The older `FR-PHC-001…038` numbering survives
only as the verbatim text of `AFR-PHC-001…038`; it is not a second live registry.

| Family | Live ids | Retired ids | Note |
|---|---|---|---|
| CFR | CFR-PHC-001…012 | none | 12 coherent requirements |
| AFR | AFR-PHC-001…038 | none | historical FR text preserved verbatim as AFR |
| UC | PHC-UC-01…16, 19…22 | PHC-UC-17, PHC-UC-18 | 20 live; 17 and 18 are marked `Retired` in the v1.1 use-case table and carry no implementation claim |
| BR | PHC-BR-01…14 | none | 14 live rules |
| Workflow | BW-PHC-01…04, CW-PHC-01…02 | none | four basis workflows; the two composites are unions of the basis step sequences |

No retired id is cited anywhere in the code, tests or quality report.

## Step 3.1 (a) — Traceability table

Rules land in `domain/` (pure policy), `services/` (write orchestration) or `selectors/`
(read scoping). `api/` only parses input, checks the two gates and serialises the result.

| Id | What it requires | Layer | Enforcement point | Notes |
|---|---|---|---|---|
| PHC-BR-01 | Published master schedule plus same-day attendance | `selectors` | `scoping.published_schedules`, `scoping.attendance_on` | One response, not two |
| PHC-BR-02 | Patients read only own records; staff read/write per role | `selectors` | `scoping.visits_for`, `scoping.prescriptions_for`, `scoping.visit_for_patient` | Ownership narrows the queryset, so a foreign id is 404 |
| PHC-BR-03 | Role-based access control | `api` | `permission_classes` on every view; `registry.PERMISSIONS` / `ROLE_GRANTS` | Two gates: module grant + action permission |
| PHC-BR-04 | Reimbursement only for employees | `domain` | `policy.is_reimbursable_kind` | Student is excluded by absence of the permission and by `kind` |
| PHC-BR-05 | Claim needs own prescription | `domain` + `services` | `policy.PRESCRIPTION_MESSAGE`, `claims.submit` | Prescription is scoped by claimant id |
| PHC-BR-06 | 90-day submission window | `domain` | `policy.expense_within_window`, `policy.CLAIM_WINDOW_DAYS` | Future dates rejected in `serializers` too |
| PHC-BR-07 | Low-stock trigger is strictly below threshold | `domain` | `policy.is_low_stock` | Equal to threshold is not low |
| PHC-BR-08 | Forward-only reimbursement routing | `domain` | `state_machine.next_claim_state`, `CLAIM_TRANSITIONS` | No edge back to an earlier state exists |
| PHC-BR-09 | Immutable sensitive-data audit trail | `services` + DB grants | `audit.record`, `ops/db/roles.sql` | App role may INSERT but not UPDATE/DELETE `phc_audit_log` |
| PHC-BR-10 | Requisition approval before fulfilment | `domain` | `state_machine.next_requisition_state` | Fulfilment never posts stock |
| PHC-BR-11 | Requisition decision notification | `services` | `notifications.requisition_notice` | Durable outbox row, deduped by key |
| PHC-BR-12 | Report privacy and anonymisation | `services` | `reports.generate` | Counts and item names only; no patient identifiers |
| PHC-BR-13 | Reimbursement status notification | `services` | `notifications.claim_status_notice` | One row per state transition |
| PHC-BR-14 | Claim immutability; reapply as a new claim | `domain` | `state_machine.CLAIM_TRANSITIONS` | No edit or reopen route exists |
| PHC-UC-01 | View doctor availability | `selectors` | `DoctorScheduleListView` | |
| PHC-UC-02 | View own medical records / prescriptions | `selectors` | `PatientRecordsView`, `PatientPrescriptionsView` | |
| PHC-UC-03 | Download own record copy | `services` | `records.record_copy`, `domain/pdf.render_pdf` | Real `%PDF-1.4` bytes |
| PHC-UC-04 | Submit reimbursement claim | `services` | `claims.submit` | |
| PHC-UC-05 | Track own claims | `selectors` | `MyClaimsView` | |
| PHC-UC-06 | Record visit and prescription | `services` | `records.create_visit`, `records.create_prescription` | |
| PHC-UC-07 | Maintain schedule | `services` | `schedules.maintain` | |
| PHC-UC-08 | Mark doctor attendance | `services` | `schedules.mark_attendance` | |
| PHC-UC-09 | Adjust stock | `services` | `inventory.adjust_stock` | Over-deduction rejected, never floored |
| PHC-UC-10 | Create requisition | `services` | `inventory.submit_requisition` | Unknown item ids rejected |
| PHC-UC-11 | Log ambulance usage | `services` | `ambulance.log_usage` | |
| PHC-UC-12 | Publish advisory | `services` | `advisories.publish` | |
| PHC-UC-13 | Generate admin report | `services` | `reports.generate` | |
| PHC-UC-14 | Fulfil approved requisition | `services` | `inventory.fulfill_requisition` | |
| PHC-UC-15 | Review submitted claim | `services` | `claims.advance(..., "review")` | |
| PHC-UC-16 | Decide requisition | `services` | `inventory.decide_requisition` | |
| PHC-UC-19 | Verify claim | `services` | `claims.advance(..., "verify")` | |
| PHC-UC-20 | Sanction claim | `services` | `claims.advance(..., "sanction_*")` | Reject is terminal |
| PHC-UC-21 | Process payment | `services` | `claims.advance(..., "payment")` | |
| PHC-UC-22 | Create and publish schedule | `services` | `schedules.create`, `schedules.publish` | Two-step publication |

## Step 3.2 (b) — Domain model

Tables in `fusion_integrated`, prefix `phc_`. IAM ids are plain integers, never foreign keys.

| Entity | Fields | Invariants and DB constraints |
|---|---|---|
| `DoctorSchedule` | doctor_name, day_of_week, start_time, end_time, is_published, published_at, published_by | One schedule per doctor/day (`phc_one_schedule_per_doctor_day`); index on doctor+day |
| `DoctorAttendance` | doctor_name, date, status, updated_by | One attendance row per doctor/day (`phc_one_attendance_per_doctor_day`); status in available/departed |
| `Patient` | user_id (PK), display_name, kind | `kind` in student/employee/staff/faculty; no ERP join |
| `Visit` | patient FK, recorded_by, notes, visit_date | Ownership stored as `user_id`; ordered by visit date |
| `Prescription` | visit FK, patient FK, medicine, dosage, recorded_by | Must belong to a visit of the same patient; enforced in `records.create_prescription` |
| `ReimbursementClaim` | employee FK, prescription FK, expense_date, amount, description, state, stage_actor, action_history | `state` from closed choices; index on employee+state; append-only `action_history` |
| `InventoryItem` | name, unit, quantity, reorder_threshold | Quantity never negative; add/deduct is an append-only `StockAdjustment` |
| `StockAdjustment` | item FK, quantity, direction, adjusted_by, reason | `direction` in add/deduct; deduct checked against current stock under a row lock |
| `Requisition` | originator FK, decided_by, decided_at, state, decision_note | `state` from closed choices; approved precedes fulfilled |
| `RequisitionItem` | requisition FK, item FK, quantity | Item ids validated before insert; item FK is PROTECT |
| `AmbulanceLog` | timestamp, patient_name, destination, logged_by | Index on timestamp |
| `HealthAdvisory` | title, content, is_published, published_at, published_by | Only published rows are readable by patients |
| `AuditLog` | actor, actor_role, action, target_type, target_id, detail, created_at | Append-only; DB role has INSERT+SELECT only |
| `NotificationOutbox` | topic, dedupe_key, subject, body, recipient_user_id, recipient_role, status, attempts, sent_at, last_error, payload | `dedupe_key` unique; written inside the source event's transaction |

Concurrency-sensitive facts live in the database where possible: row locks
(`select_for_update`) guard claim transitions, requisition decisions and stock deductions;
dedupe is a unique index rather than a Python check.

## Step 3.3 (c) — State machine

Declarative tables in `modules/phc/domain/state_machine.py`. An action with no edge from the
current state is inexpressible.

Claims:

| From | Event | Actor | To |
|---|---|---|---|
| submitted | review | PHC Staff | pending_audit |
| pending_audit | verify | Accounts & Audit | pending_sanction |
| pending_sanction | sanction approve | Approving Authority | approved_for_payment |
| pending_sanction | sanction reject | Approving Authority | rejected (terminal) |
| approved_for_payment | payment | Accounts & Audit | reimbursed (terminal) |

Requisitions:

| From | Event | Actor | To |
|---|---|---|---|
| pending_approval | approve | Approving Authority | approved |
| pending_approval | reject | Approving Authority | rejected (terminal) |
| approved | fulfill | PHC Staff | fulfilled (terminal) |

A stale `expected_updated_at` yields 409. An action whose record is at the wrong stage
yields 404 with a "still at an earlier stage" message, preserving the v1.1 exception cases.

## Step 3.4 (d) — Permission list

Exact registry content is `modules/phc/registry.py`: 19 `PERMISSIONS`, empty
`SYSTEM_PERMISSIONS`, and `ROLE_GRANTS` keyed by `phc_staff`, `PHC Staff`, `accounts_audit`,
`Accounts & Audit`, `approving_authority`, `Approving Authority`, `employee` and `student`.
No `Role`, `Permission`, `UserRole` or `ModuleAccess` model exists in this module. The
manifest is published with `make permissions` then applied by IAM seeding; `make check`
verifies it is current.

## Step 3.5 (e) — Endpoint list

All paths are under `/api/v1/phc/`. Every route has `MODULE = HasModuleGrant("phc")` plus one
`HasPhcPermission(code)`; both gates are required.

| Method | Path | Permission | Returns | Rule ids |
|---|---|---|---|---|
| GET | `schedule` | `phc.schedule.view` | published schedules + today's attendance | BR-01, UC-01 |
| POST | `staff/schedule` | `phc.schedule.manage` | new unpublished schedule | UC-22 |
| PATCH | `staff/schedule/<pk>` | `phc.schedule.manage` | updated schedule | UC-07 |
| POST | `staff/schedule/<pk>/publish` | `phc.schedule.manage` | published schedule | UC-22 |
| POST | `staff/attendance` | `phc.schedule.manage` | attendance row | UC-08 |
| GET | `staff/patients/search` | `phc.records.manage` | patient matches | UC-06 |
| POST | `staff/visits` | `phc.records.manage` | visit | UC-06 |
| POST | `staff/prescriptions` | `phc.records.manage` | prescription | UC-06 |
| GET | `records` | `phc.records.view_self` | own visits | BR-02, UC-02 |
| GET | `records/prescriptions` | `phc.records.view_self` | own prescriptions | BR-02, UC-02 |
| GET | `records/download/<pk>` | `phc.records.view_self` | PDF bytes | BR-02, UC-03 |
| POST | `claims` | `phc.reimbursement.submit` | submitted claim | BR-04..06, UC-04 |
| GET | `claims/mine` | `phc.reimbursement.view_self` | own claims | UC-05 |
| POST | `staff/claims/<pk>/review` | `phc.reimbursement.review` | claim at pending_audit | UC-15, BR-13 |
| POST | `audit/claims/<pk>/verify` | `phc.reimbursement.verify` | claim at pending_sanction | UC-19 |
| POST | `approver/claims/<pk>/sanction` | `phc.reimbursement.sanction` | approved or rejected claim | UC-20, BR-08 |
| POST | `audit/claims/<pk>/payment` | `phc.reimbursement.payment` | reimbursed claim | UC-21 |
| POST | `staff/inventory/adjust` | `phc.inventory.adjust` | stock adjustment | BR-07, UC-09 |
| GET/POST | `staff/inventory/items` | `phc.inventory.adjust` | item list / new item | UC-09 |
| POST | `staff/requisitions` | `phc.requisition.submit` | pending requisition | BR-10, UC-10 |
| POST | `approver/requisitions/<pk>/decide` | `phc.requisition.decide` | decided requisition | BR-11, UC-16 |
| POST | `staff/requisitions/<pk>/fulfill` | `phc.requisition.fulfill` | fulfilled requisition | UC-14 |
| POST | `staff/ambulance` | `phc.ambulance.log` | ambulance log | UC-11 |
| POST | `staff/advisories` | `phc.advisory.publish` | published advisory | UC-12 |
| GET | `advisories` | `phc.advisory.view` | published advisories | UC-12 |
| GET | `staff/reports` | `phc.reports.generate` | aggregate counts | BR-12, UC-13 |
| GET | `audit/log` | `phc.audit.view` | audit rows | BR-09 |

Sidebar entry already registered in `client/src/app/registry.ts`:
`id: "phc"`, `label: "PHC"`, `icon: "Stethoscope"`, `to: "/phc"`, `section: "PHC"`, with the
16 nav items from `modules/phc/registry.py::NAV_ITEMS`. Phosphor names are used by the
parity test in `client/src/test/phc-icon-parity.test.ts`.

## Step 3.6 (f) — Contracts

`modules/phc/contracts.py` exposes one plural getter,
`get_phc_profiles(user_ids: Sequence[int]) -> dict[int, PHCProfileDTO]`, returning
`has_patient_record`, `may_claim_reimbursement` and a user-facing message per id. The data
class is immutable. No other module may import `modules.phc.models`, `.services`,
`.selectors` or `.api`; `.importlinter` enforces this in both directions.

Dependencies on other modules are resolved through their contracts only: identity and
permissions from the request session (IAM), person name/kind from `get_users`, and no
`fusionlab` connection. Nothing from another module is needed to serve a PHC request.

## Step 3.7 (g) — Scheduled work

None. `SYSTEM_PERMISSIONS` is empty. Notifications are written synchronously to a durable
outbox inside the source transaction; no Celery beat entry is required for correctness, so
none is claimed. See `docs/09-phc/e2e-notes.md` for the load-test N/A justification.

## Step 3.8 (h) — Open questions and known-gap resolution

- PHC-UC-17 and PHC-UC-18 are retired in the v1.1 use-case table. They are intentionally not
  implemented and are not claimed anywhere.
- The earlier JSON record-download gap is closed: `RecordDownloadView` now returns real PDF
  bytes with `Content-Type: application/pdf`, and tests assert `%PDF-1.4`, record content and
  `%%EOF`.
- The earlier notification gap is closed: claim status changes, requisition decisions and
  low-stock events write deduplicated `NotificationOutbox` rows with recipient, topic,
  subject, body and payload, asserted in `modules/phc/tests/spec/br/test_adversarial.py`.
- Over-deduction is no longer floored at zero: it is a 422 and the attempted change is not
  persisted.
- The specification does not settle who consumes the notification outbox (in-app list,
  email or SMS). The module writes the durable row; the delivery channel is an open question
  for the platform owner and is not guessed here.
- The specification gives no predictable peak event for PHC, so no load test is claimed.
- No new designation is requested. All grants use designation names already present in the
  frozen IAM fixture.
