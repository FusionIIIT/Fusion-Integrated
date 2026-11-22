# OAP — module blueprint

Module code `oap`, URL segment `/api/v1/oap/`, docs folder `docs/09-oap/`.
Built from the Other Academic Procedures specification set (Problem Statement v1.4,
Requirement Registry CFR/AFR v1.2, Use Case v1.4, Business Rule v1.4, Workflow v1.4,
Traceability Matrix v1.2). Spec id prefixes: `OA-UC-`, `OA-BR-`, `BW-OAP-`, `CW-OAP-`,
`CFR-OAP-`, `AFR-OAP-`. Environment: `module-only`.

Status: **approved** by the module owner (Nirvan Jain) on 2026-11-23, in chat. Student 2's
written approval, required by the assignment guide, is still _pending_.

## Phase 0 inventory

| Artefact | Count | Notes |
|---|---|---|
| Problem Statement sections | 4 | actors, functional scope, exclusions |
| CFR | 22 | `CFR-OAP-001` … `CFR-OAP-022` |
| AFR | 51 | `AFR-OAP-001` … `AFR-OAP-054` (`003`, `050`, `051` absent: retired) |
| Use cases (live) | 25 | `OA-UC-91`/`92` reclassified event-triggered |
| Business rules (live) | 20 | `OA-BR-01`, `03`, `11`, `21`, `22`, `31`–`34`, `41`–`46`, `51`, `52`, `61`–`63` |
| Workflows | 9 basis + 4 composite | `BW-OAP-01`–`09`, `CW-OAP-01`–`04` |

Retired ids: `FR-OAP-003`, `FR-OAP-050`, `FR-OAP-051` (disciplinary / student-issue
handling, outside OAP scope; no replacement). Not cited anywhere in code.

Internal contradictions found: none between the documents. The traceability matrix's
mapping columns are empty, so coverage below is derived by reading each rule and use case.
Use cases `OA-UC-12`, `OA-UC-13`, `OA-UC-14`, `OA-UC-24`, `OA-UC-25`, `OA-UC-37` and
`OA-UC-54` have no `Related CFRs` entry; they are mapped by their AFR statements.

Actors named across BR/UC/WF documents: Student (UG/PG), PG Student, Faculty Member,
Thesis Supervisor, TA Supervisor, Head of Department (HoD), Academic Administrator,
Department Administrator, Librarian, Hostel Warden, Mess In-charge, Lab Supervisor,
respective-Department verifier, Academic Section verifier, Student Section verifier.

## Step 2.4 — roles

Designations are the join key into `globals_designation`. The spec does not spell them as
ERP designation names; the names below are the spec's own actor names and **must be
confirmed against `globals_designation` before the grant is seeded.**

| Role (spec) | Designation to grant | Source | Status |
|---|---|---|---|
| Student (UG/PG) | `student` (kind) | UC OA-UC-01, 04, 11, 14, 21, 24, 25 | held by definition |
| PG Student | `PG Student` | OA-BR-41, OA-BR-61 | **open** — no PG flag exists in IAM (Gap G1) |
| Faculty Member | `faculty` (kind) | OA-UC-54, OA-BR-63 | held by definition |
| Thesis Supervisor | none — resolved per claim from the thesis assignment | OA-UC-33, OA-BR-52 | role resolution, not a designation |
| TA Supervisor | none — resolved per claim from the TA assignment | OA-UC-33, OA-BR-52 | role resolution, not a designation |
| Head of Department | `Head of Department` | OA-UC-03, OA-UC-35, OA-BR-11, OA-BR-44 | confirm spelling |
| Academic Administrator | `Academic Administrator` | OA-UC-12, OA-UC-23, OA-UC-36, OA-BR-21 | confirm spelling |
| Department Administrator | `Department Administrator` | OA-UC-34, OA-UC-41, OA-UC-42, OA-UC-53, OA-BR-51, OA-BR-62 | confirm spelling |
| Librarian | `Librarian` | OA-UC-22, OA-BR-31 | confirm spelling |
| Hostel Warden | `Hostel Warden` | OA-UC-22, OA-BR-31 | confirm spelling |
| Mess In-charge | `Mess In-charge` | OA-UC-22, OA-BR-31 | confirm spelling |
| Lab Supervisor | `Lab Supervisor` | OA-UC-22, OA-BR-31 | confirm spelling |
| Respective-Department verifier | none | OA-BR-31, AFR-OAP-052 | **blocker** — no designation named (Gap G2) |
| Academic Section verifier | none | OA-BR-31, AFR-OAP-053 | **blocker** — no designation named (Gap G2) |
| Student Section verifier | none | OA-BR-31, AFR-OAP-054 | **blocker** — no designation named (Gap G2) |

## Step 3.1 (a) — traceability (live rules and use cases)

| Id | What it requires | Layer | Enforcement point | Notes |
|---|---|---|---|---|
| OA-BR-01 | role-based access and data scope | selectors + services | `selectors/scoping.py`; `services/*` permission + role check | 404 for out-of-scope rows |
| OA-BR-03 | alerts + email for required notifications | services + outbox | `services/notifications.py` | delivery in `tasks.py` |
| OA-BR-11 | only HoD decides leave | services | `services/leave.py::decide` | |
| OA-BR-21 | Academic Administrator verifies and decides bonafide | services | `services/bonafide.py::verify`, `::decide` | |
| OA-BR-22 | bonafide download only after approval | selectors | `selectors/bonafide.py::certificate_for` | |
| OA-BR-31 | each no-dues authority records only its own domain | services | `services/no_dues.py::record_result` | domain from active role |
| OA-BR-32 | seven results kept separately | models | `NoDuesResult` unique `(case, domain)` | |
| OA-BR-33 | finalize only when seven clear | domain + services | `domain/no_dues.py::status`, `services/no_dues.py::finalize` | |
| OA-BR-34 | certificate only after finalization | selectors | `selectors/no_dues.py::certificate_for` | |
| OA-BR-41 | only PG students submit claims | services | `services/assistantship.py::submit` (permission `PG Student`) | Gap G1 |
| OA-BR-42 | both supervisor verifications before review | domain + DB | `domain/assistantship.py`, `UniqueConstraint(claim, role)` | |
| OA-BR-43 | review only after both verifications | domain | `state_machines.CLAIM` | |
| OA-BR-44 | HoD decides claim | services | `services/assistantship.py::decide` | |
| OA-BR-45 | stipend only for HoD-approved | domain | `state_machines.CLAIM` | |
| OA-BR-46 | fixed progression | domain | `state_machines.CLAIM` | |
| OA-BR-51 | DA records supervisor and TA assignments | services | `services/assignments.py` | |
| OA-BR-52 | supervisor roles distinct, may be same person | models | `UniqueConstraint(claim, role)`; both roles may share a `user_id` | |
| OA-BR-61 | seminar request within PG scope | services | permission `PG Student` | Gap G1 |
| OA-BR-62 | DA schedules and logs seminars | services | `services/seminar.py::schedule` | |
| OA-BR-63 | PG students and faculty view schedules | selectors | `selectors/seminar.py::schedules_for` | |
| OA-UC-01 | submit leave, optional document | services | `services/leave.py::submit` | Drive link |
| OA-UC-03 | HoD decides leave | services | `services/leave.py::decide` | |
| OA-UC-04 | student tracks leave status/history | selectors | `selectors/leave.py` | |
| OA-UC-11 | submit bonafide request | services | `services/bonafide.py::request` | |
| OA-UC-12 | AA verifies and decides bonafide | services | `services/bonafide.py` | |
| OA-UC-13 | download bonafide | selectors | `selectors/bonafide.py::certificate_for` | Gap G5 format |
| OA-UC-14 | track bonafide status | selectors | `selectors/bonafide.py` | |
| OA-UC-21 | initiate no-dues, route to seven | services | `services/no_dues.py::initiate` | |
| OA-UC-22 | authority records own domain | services | `services/no_dues.py::record_result` | |
| OA-UC-23 | AA finalizes no-dues | services | `services/no_dues.py::finalize` | |
| OA-UC-24 | track no-dues progress | selectors | `selectors/no_dues.py` | |
| OA-UC-25 | download no-dues certificate | selectors | `selectors/no_dues.py::certificate_for` | |
| OA-UC-31 | submit assistantship claim | services | `services/assistantship.py::submit` | refuses if a supervisor is unresolved (E1) |
| OA-UC-33 | supervisor verifies claim | services | `services/assistantship.py::verify` | |
| OA-UC-34 | DA reviews and forwards | services | `services/assistantship.py::forward` | no send-back path (spec) |
| OA-UC-35 | HoD decides claim | services | `services/assistantship.py::decide` | |
| OA-UC-36 | AA processes stipend | services | `services/assistantship.py::process_stipend` | |
| OA-UC-37 | track claim | selectors | `selectors/assistantship.py` | |
| OA-UC-41 | record thesis supervisor | services | `services/assignments.py::record_thesis_supervisor` | supersedes, never edits |
| OA-UC-42 | record TA assignment | services | `services/assignments.py::record_ta` | |
| OA-UC-51 | request seminar scheduling | services | `services/seminar.py::request` | |
| OA-UC-53 | schedule and log seminar | services | `services/seminar.py::schedule` | |
| OA-UC-54 | view seminar schedule | selectors | `selectors/seminar.py` | |
| OA-UC-91 | event notification | services + tasks | `services/notifications.py`, `tasks.py` | event-triggered |
| OA-UC-92 | pending-action reminder | tasks | `tasks.py::send_pending_reminders` | Gap G6 |

## Step 3.2 (b) — domain model

All person references are plain integers `user_id` (`UserScopedModel`). No foreign key
crosses a module boundary. No auth tables.

- `LeaveApplication` (TimeStamped, UserScoped): `status` (`submitted`, `approved`,
  `rejected`), `reason`, `from_date`, `to_date` (`CheckConstraint` to_date >= from_date),
  `supporting_document_link` (Drive link, optional), `decided_by_user_id`, `decided_at`.
- `BonafideRequest`: `status` (`submitted`, `approved`, `rejected`), `purpose` (text),
  `verified_by_user_id`, `verified_at`, `decided_by_user_id`, `decided_at`.
- `NoDuesCase`: `status` (`in_progress`, `finalized`) stored; the derived state
  (`in_progress`, `dues_outstanding`, `all_clear`, `finalized`) is computed by
  `domain/no_dues.py`. Unique partial constraint: one open (`finalized` = false) case per
  student (`UniqueConstraint(user_id, condition=finalized=False)`).
- `NoDuesResult`: `case` FK (same module), `domain` (`library`, `hostel`, `mess`,
  `department`, `lab`, `academic_section`, `student_section`), `result`
  (`pending`, `clear`, `outstanding`), `recorded_by_user_id`, `recorded_at`.
  `UniqueConstraint(case, domain)` (OA-BR-32). Pre-created at initiation, all seven rows.
- `AssistantshipClaim`: `status` (see state machine), `thesis_supervisor_user_id`,
  `ta_supervisor_user_id` (snapshots taken at submission, OA-UC-31 E1),
  `dept_forwarded_at`, `hod_decided_by_user_id`, `hod_decided_at`, `stipend_processed_at`.
- `SupervisorVerification`: `claim` FK, `role` (`thesis`, `ta`), `verified_by_user_id`,
  `verified_at`. `UniqueConstraint(claim, role)`. Two rows per claim when both are done.
- `ThesisSupervisorAssignment`: `student_user_id`, `supervisor_user_id`, `assigned_by_user_id`,
  `assigned_at`, `superseded_at` (null while current). `UniqueConstraint(student_user_id,
  condition=superseded_at IS NULL)`. Recording a new one supersedes the old row.
- `TAAssignment`: `student_user_id`, `course_code` (blank allowed), `supervisor_user_id`
  (nullable), `assigned_by_user_id`, `assigned_at`. `CheckConstraint`: at least one of
  `course_code` and `supervisor_user_id` present.
- `SeminarRequest`: `status` (`awaiting_scheduling`, `scheduled`), `requested_by_user_id`.
- `SeminarSchedule`: `request` OneToOne, `scheduled_for` (datetime), `venue` (text),
  `scheduled_by_user_id`, `scheduled_at`. Written once; history kept in `OapEvent`.
- `OapEvent`: append-only history for every transition: `aggregate` (`leave`, `bonafide`,
  `no_dues`, `claim`, `seminar`), `aggregate_id`, `from_state`, `to_state`,
  `actor_user_id`, `occurred_at`. Serves AFR-015 and AFR-048. Never edited.
- `Notification`: `recipient_user_id`, `channel` (`alert`, `email`), `subject`, `body`,
  `status` (`pending`, `sent`, `failed`, `read`), `attempts`, `last_error`, `created_at`.
  Written in the same transaction as the event (outbox).
- `ReminderPolicy`: effective-dated, never edited. `effective_from`, `after_hours`
  (int). No row means no reminders are sent and the readiness command says so (Gap G6).

Constraints that must hold under concurrency sit in the database: the unique constraints
above and `select_for_update` on every transition.

## Step 3.3 (c) — state machines

Declarative tables in `domain/state_machines.py` as `(state, event, role) -> state`.
`next_state()` raises `IllegalTransition`; services translate it to `ConflictError`.

LEAVE: `submitted --approve[hod]--> approved`; `submitted --reject[hod]--> rejected`.
BONAFIDE: `submitted --approve[academic_admin]--> approved`;
`submitted --reject[academic_admin]--> rejected`. Verification is a stamp, not a state (OA-UC-12 M3).
CLAIM:
- `awaiting_dual_verification --verify[supervisor]--> awaiting_other_verification`
- `awaiting_other_verification --verify[supervisor]--> awaiting_department_review`
- `awaiting_department_review --forward[dept_admin]--> awaiting_hod_decision`
- `awaiting_hod_decision --approve[hod]--> approved_awaiting_stipend`
- `awaiting_hod_decision --reject[hod]--> rejected`
- `approved_awaiting_stipend --process_stipend[academic_admin]--> stipend_processed`

NO-DUES (derived): `in_progress` while any result is `pending`; `dues_outstanding` when all
seven are recorded and one is `outstanding`; `all_clear` when all seven are `clear`;
`finalized` by `finalize[academic_admin]` from `all_clear` only. An outstanding domain that
later becomes clear moves the case back out of `dues_outstanding` (OA-UC-22 A1).

SEMINAR: `awaiting_scheduling --schedule[dept_admin]--> scheduled`.

## Step 3.4 (d) — permissions and roles

Codes are `oap.<singular_noun>.<verb>`, verbs from the closed list. Registry in
`modules/oap/registry.py`. Permission decides the verb; scoping decides the rows; the
acting role (`principal.active_role`) decides the specific authority where the spec names
one (HoD, Academic Administrator, Department Administrator, authority designations).

Permissions: `oap.leave_application.{create, view_self, view, approve}`,
`oap.bonafide_request.{create, view_self, view, review, approve}`,
`oap.bonafide_certificate.view_self`, `oap.no_dues_case.{create, view_self, view, approve}`, `oap.no_dues_result.update`, `oap.no_dues_certificate.view_self`,
`oap.assistantship_claim.{create, view_self, view, review, approve, update}`,
`oap.assistantship_verification.review`, `oap.thesis_supervisor_assignment.{assign, view}`,
`oap.ta_assignment.{assign, view}`, `oap.seminar_request.{create, view_self, view}`,
`oap.seminar_schedule.{update, view}`, `oap.notification.view_self`.

System permissions (no human): none. Scheduled work is run by the service itself.

Grants (`ROLE_GRANTS`, keyed by designation name):
- `student`: leave create/view_self; bonafide create/view_self; bonafide_certificate
  view_self; no_dues create/view_self; no_dues_certificate view_self; notification view_self.
- `PG Student`: assistantship create/view_self; seminar_request create/view_self; seminar_schedule view.
- `faculty`: assistantship_verification review; seminar_schedule view.
- `Head of Department`: leave_application view/approve; assistantship_claim view/approve.
- `Academic Administrator`: bonafide_request view/review/approve; no_dues_case view/approve;
  assistantship_claim view/update.
- `Department Administrator`: thesis_supervisor_assignment assign/view; ta_assignment assign/view;
  assistantship_claim view/review; seminar_request view; seminar_schedule update/view.
- `Librarian`, `Hostel Warden`, `Mess In-charge`, `Lab Supervisor`: no_dues_result update;
  no_dues_case view.

The three verifiers in Gap G2 are not granted anything.

Scope rules (`selectors/scoping.py`, 404 never 403):
- Leave, bonafide, no-dues, claim, seminar request: own rows for the student; the
  responsible role sees all rows (HoD sees all leave; AA sees all bonafide and no-dues cases;
  DA sees all claims and seminar requests).
- Claims for supervisors: only claims whose snapshot names the faculty member.
- No-dues authorities: see every case, but the response carries only their own domain's result.
- Unknown or missing active role fails closed to no rows.

## Step 3.5 (e) — endpoints

All under `/api/v1/oap/`. Every endpoint: `HasModuleGrant("oap")` first, then
`HasPermission(...)`. Errors use the platform envelope.

| Method | Path | Permission | Returns | Rules |
|---|---|---|---|---|
| POST | `leave-applications` | `leave_application.create` | 201 application | OA-UC-01, BR-01, BR-03 |
| GET | `leave-applications` | `leave_application.view_self` or `view` | list (scoped) | OA-UC-04, BR-01 |
| GET | `leave-applications/{id}` | `view_self` or `view` | application + history | BR-01 |
| POST | `leave-applications/{id}/decision` | `leave_application.approve` (HoD) | 200 | OA-UC-03, BR-11 |
| POST | `bonafide-requests` | `bonafide_request.create` | 201 | OA-UC-11 |
| GET | `bonafide-requests` | `view_self` or `view` | list | OA-UC-14 |
| GET | `bonafide-requests/{id}` | `view_self` or `view` | request | BR-01 |
| POST | `bonafide-requests/{id}/verify` | `bonafide_request.review` (AA) | 200 | OA-UC-12, BR-21 |
| POST | `bonafide-requests/{id}/decision` | `bonafide_request.approve` (AA) | 200; 409 until verified | OA-UC-12, BR-21 |
| GET | `bonafide-requests/{id}/certificate` | `bonafide_certificate.view_self` | 200 metadata or 409 | OA-UC-13, BR-22 |
| POST | `no-dues-cases` | `no_dues_case.create` | 201, seven results pending | OA-UC-21, BR-31 |
| GET | `no-dues-cases` | `view_self` or `view` | list (scoped) | OA-UC-24 |
| GET | `no-dues-cases/{id}` | `view_self` or `view` | case (own-domain result for authorities) | OA-UC-24, BR-31 |
| POST | `no-dues-cases/{id}/results` | `no_dues_result.update` + authority role | 200 | OA-UC-22, BR-31, BR-32 |
| POST | `no-dues-cases/{id}/finalize` | `no_dues_case.approve` (AA) | 200 | OA-UC-23, BR-33 |
| GET | `no-dues-cases/{id}/certificate` | `no_dues_certificate.view_self` | 200 metadata or 409 | OA-UC-25, BR-34 |
| POST | `assistantship-claims` | `assistantship_claim.create` (PG Student) | 201 | OA-UC-31, BR-41, BR-42 |
| GET | `assistantship-claims` | `view_self` or `view` or supervisor scope | list | OA-UC-37 |
| GET | `assistantship-claims/{id}` | same | claim + verifications | BR-01 |
| POST | `assistantship-claims/{id}/verifications` | `assistantship_verification.review` | 200 | OA-UC-33, BR-42, BR-52 |
| POST | `assistantship-claims/{id}/forward` | `assistantship_claim.review` (DA) | 200 | OA-UC-34, BR-43 |
| POST | `assistantship-claims/{id}/decision` | `assistantship_claim.approve` (HoD) | 200 | OA-UC-35, BR-44 |
| POST | `assistantship-claims/{id}/stipend` | `assistantship_claim.update` (AA) | 200 | OA-UC-36, BR-45 |
| POST | `thesis-supervisor-assignments` | `thesis_supervisor_assignment.assign` | 201 | OA-UC-41, BR-51 |
| GET | `thesis-supervisor-assignments` | `thesis_supervisor_assignment.view` | list | BR-51 |
| POST | `ta-assignments` | `ta_assignment.assign` | 201 | OA-UC-42, BR-51 |
| GET | `ta-assignments` | `ta_assignment.view` | list | BR-51 |
| POST | `seminar-requests` | `seminar_request.create` (PG Student) | 201 | OA-UC-51, BR-61 |
| GET | `seminar-requests` | `view_self` or `view` | list | BR-62 |
| POST | `seminar-requests/{id}/schedule` | `seminar_schedule.update` (DA) | 200 | OA-UC-53, BR-62 |
| GET | `seminar-schedules` | `seminar_schedule.view` | scheduled seminars | OA-UC-54, BR-63 |
| GET | `notifications` | `notification.view_self` | own alerts | OA-BR-03 |

Collections share one path for read and write; permissions are chosen per method
(`api/views.py::_MethodGated`). Client sidebar entries: none in this pass. `NAV_ITEMS` stays empty until the client
module exists, because `nav_matches_routes.py` fails CI for a nav entry without a route.

## Step 3.6 (f) — contracts

`contracts.py` exposes one plural getter for other modules:
`get_no_dues_status(user_ids) -> dict[int, NoDuesStatusDTO]` (`cleared`, `finalized`).
No module needs it today; it exists so the academic office can read the seven-authority
outcome without reading `NoDuesResult`. It needs no addition to any other module.

Needs from others: none. Identity from the request principal. The thesis and TA
supervisor relationships are recorded by this module's own Department Administrator,
not read from the ERP, so no `fusionlab` read is needed.

## Step 3.7 (g) — scheduled work

- `oap.deliver-notifications`, every 60 s: drains `Notification` rows with channel `email`
  and status `pending`. Without it, no email is sent and every email row stays pending.
- `oap.send-pending-reminders`, hourly: reads the current `ReminderPolicy`. With no policy it
  sends nothing and says so. With one, it reminds claim supervisors of pending verifications
  older than `after_hours` (Gap G6 covers the other actors).

## Step 3.8 (h) — open questions and gaps

- **G1 — PG status.** Assistantship and seminar requests are PG-only (OA-BR-41, OA-BR-61).
  IAM has no PG flag. The design grants these to a `PG Student` designation. Confirm the
  designation exists in `globals_designation`, or name the flag the academic office keeps.
- **G2 — three verifier roles have no designation.** Respective-Department verifier, Academic
  Section verifier and Student Section verifier are named by the spec but not as designations.
  The `oap` result endpoint accepts them through the permission only once a designation is
  granted. Request from the academic office: the designation names, and which Department a
  Department verifier covers. Until then, Department, Academic Section and Student Section
  results cannot be recorded in production.
- **G3 — respective department.** OA-BR-31 says "respective Department". The student's
  department is an ERP field this module does not read (no ERP read rule). The Department
  verifier is trusted to record the department result. Not enforced.
- **G4 — who is "the appropriate HoD" and "the responsible actor".** The spec does not say
  how HoD or Academic Administrator is chosen when several hold the role. Routing is by role
  only. Notifications to role-holders need an IAM lookup by designation, which does not exist
  yet, so only claim supervisors (known user ids) are reminded or notified directly.
- **G5 — bonafide and no-dues certificate format.** The PS fixes no template, no validity
  period and no signature rule. The download endpoint returns availability metadata, not a
  file.
- **G6 — reminder thresholds.** None are specified. `ReminderPolicy` is empty until the
  institute sets one. Reminders are sent for supervisors only (Gap G4).
- **G7 — supervisor return path.** The spec has no send-back or rejection by a supervisor or
  by the Department Administrator (OA-UC-33 E1, OA-UC-34 E1). None is built.
- **G8 — supporting documents.** Leave supporting documents are Drive links, validated by
  `core.files.drive.parse`, because the platform moved to Drive links. No size or type rule.
- **G9 — seminar schedule fields.** The spec gives no fields for a schedule. `scheduled_for` and
  `venue` are the minimum. No conflict rule (spec exclusion).
- **G10 — no withdrawal, cancellation or reschedule.** Excluded by the PS (§4). Not built.
- **G11 — no finance integration.** Stipend processing records completion only (OA-UC-36).
- **G12 — frontend.** No client module in this pass. The sidebar entry and the pages are a
  separate step.

## Phase gates

- Blueprint approval: module owner, in chat, 2026-11-23: approved. Student 2, in writing: _pending_.
- Shared-file change this pass: `config/celery.py` merges `modules/oap/schedule.py` into the
  beat schedule and task routes. Without it the notification and reminder timers never run.
  Approved 2026-11-23. `config/settings/base.py`, `config/urls.py` and `.importlinter` already
  name `oap` and are unchanged by this pass.
- Generated files regenerated by this pass: `openapi/fusion-integrated.v1.yaml`,
  `registry/permissions.json`. `docs/02-iam/permission-catalog.generated.md` is regenerated
  on `make permissions` as well.
- New dependency: none.
- Management commands: `oap_readiness` (names every unmet prerequisite) and
  `oap_set_reminder_policy --after-hours N --by USER_ID`.
