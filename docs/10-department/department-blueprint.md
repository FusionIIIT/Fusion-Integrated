# Department (DEPT): blueprint

Module code `department` · docs folder `docs/10-department/` · environment `module-only` ·
spec `06-DEPT` v1.2 STUDENT BASELINE (`specs/06-DEPT`, not committed).

**Status: approved by Student 2 on 2026-11-22, WhatsApp. See the approval record at the end.**

---

## 0. Phase 0 report (Step 1.5)

### Artefact counts

| Artefact | Live | Retired / reserved |
|---|---|---|
| Business rules | 22 (`BR-DEPT-001`..`013`, `015`..`019`, `021`..`024`) | `BR-DEPT-014` retired; its behaviour **moved** to `AFR-DEPT-041`..`046` (notifications). `BR-DEPT-020` does not exist in any document. |
| Use cases | 20 (`UC-DEPT-001`..`012`, `014`..`020`, `022`) | `UC-DEPT-013` retired; behaviour **moved** into the triggering UCs (002, 004, 005, 006, 007, 008, 014). `UC-DEPT-021` reserved, behaviour **dropped** (critical-timetable approval removed by accepted clarification). |
| Workflows | 8 basis (`BW-DEPT-01`..`08`), 4 composite (`CW-DEPT-01`..`04`) | none |
| CFRs | 16 (`CFR-DEPT-001`..`016`) | none |
| AFRs | 51 (`AFR-DEPT-001`..`031`, `034`..`053`) | `FR-DEPT-032`, `FR-DEPT-033` reserved, behaviour **dropped** (critical-timetable). Each AFR carries its historical `FR-DEPT-NNN` with the same number. |

### Traceability matrix

The matrix's `UC Mapping`, `BR Mapping` and `WF Mapping` columns on the CFR/AFR sheet are **empty**,
and so are the mapped-UC/BR/WF columns of the registry's CFR inventory. The UC/BR/WF sheets are
partly filled. Coverage below is derived by reading each rule's own "Related" fields, never from the
matrix.

### Actor inventory (Step 1.4.6)

| Actor | Named in |
|---|---|
| Student | BR-DEPT-002, 008, 019; UC-DEPT-001, 007, 015, 018; BW-DEPT-03, 04 |
| Faculty | BR-DEPT-001, 005, 008, 012, 019; UC-DEPT-001, 002, 004, 007, 011, 015; BW-DEPT-01..04 |
| HOD | BR-DEPT-004, 006, 009, 013, 017, 018, 019; UC-DEPT-001, 002, 003, 005, 012, 014, 015; BW-DEPT-01, 02, 04..06 |
| Dept_Admin | BR-DEPT-007, 009, 010, 011, 017, 018, 019; UC-DEPT-001, 002, 006, 008, 009, 010, 015, 016, 017, 019; BW-DEPT-01, 03..06 |
| Institute Admin / equivalent central authority | BR-DEPT-021; UC-DEPT-020; BW-DEPT-07, 08 |
| System (event-triggered) | UC-DEPT-022; BW-DEPT-07, 08 |
| Alumni | **not an actor**: only a kind of profile record (AFR-DEPT-024, 027) |

### Contradictions between documents

None that change behaviour. One wording mismatch: BR-DEPT-010 says "saved **or advanced for
approval**", but the PS 3.5 accepted clarification removed timetable approval. Read as "not saved".

### Rules that cannot be implemented as written (each is an open question in §8)

1. **BR-DEPT-021..024, UC-DEPT-020/022, BW-DEPT-07/08, CW-DEPT-04: role assignment and access transition.**
   The spec makes this module the place where HOD and Dept_Admin roles are assigned, and has the
   module grant and revoke "role access". On this platform, who holds a designation is owned by the
   ERP and IAM. `fusion_auth/client.py` has no write method, the IAM's `main` exposes no designation
   endpoint, and the prompt forbids a module-owned `Role`/`UserRole` table. → **Q1**.
2. **AFR-DEPT-026 / BR-DEPT-019: "Students in the Faculty member's courses".** The IAM's `main`
   exposes no course-instructor or roster endpoint (`/v1/directory/users`,
   `/v1/academics/{standings,directory,filters}` only). The prompt says a dependency on a missing IAM
   endpoint is a stop. → **Q2**.
3. **BR-DEPT-021: "Institute Admin or equivalent".** No designation with that name exists in
   `globals_designation`. → **Q3**.

### Drift noticed in `docs/03-platform/module-authoring-guide.md` (not fixed)

It names a `make new-module` target, which the `Makefile` no longer has.

---

## Phase 1 answers (§2)

- **2.1 One bounded context?** Yes. Announcements, stock, feedback, timetable, labs, profiles,
  details and role tenure are all "running one department", share the department scope, and have
  no second owner. Nothing here is "mostly" another module's.
- **2.2 Needs from other modules:** `directory.contracts.get_users` (names, kind, department,
  discipline, programme, batch year) and `directory.contracts.search`. No new contract functions.
- **2.3 Identity:** every person is a plain integer `user_id` (`UserScopedModel`). No FK to a person.
- **2.4 Roles:** derived from the actor inventory above; see §4 (d) for the exact designation names.
  The HOD for SM and the Institute Admin cannot be expressed → Q3, Q4.
- **2.5 Scope:** every row has a `department` FK, and every queryset is narrowed to the actor's
  department in `selectors/scoping.py`. Out-of-scope gives **404**. Per collection, see §5 (e).
- **2.6 Time:** two beat entries: notification delivery, and the role transition taking effect
  (UC-DEPT-022, only if Q1 is approved as proposed). §7 (g).
- **2.7 Balance:** inventory quantity is something people spend. The `StockMovement` table is the
  append-only ledger (BR-DEPT-016). `InventoryItem.current_quantity` is a cached running total,
  written only in the same transaction as a movement row, under `select_for_update`, and guarded
  by `CheckConstraint(current_quantity >= 0)`. Corrections are new movements; no movement is
  ever edited or deleted.
- **2.8 Policy:** nothing is administrator-configured. The department rows themselves are
  seeded by a management command (`seed_departments`). Before that runs, the module reports
  "no departments" instead of failing with a 500.

---

## 1. (a) Traceability table (Step 3.1)

Layers: `domain` = pure rule/state table · `models` = DB constraint · `selectors` = row narrowing ·
`services` = write orchestration · `api` = transport only · `tasks` = scheduled.

### Business rules

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-DEPT-001 | Only Faculty, Dept_Admin, HOD create announcements | services + IAM grant | `department.announcement.create` held only by those roles; `services/announcements.publish` | Student lacks the code → 403 |
| BR-DEPT-002 | Show an announcement only if the viewer matches role, programme and academic-year targets | selectors | `scoping.announcements_for(actor)` | Blank target = any (Q5) |
| BR-DEPT-003 | Block publication when required content/target information is missing or invalid | domain | `domain/rules.validate_announcement` | 422 `announcement_incomplete` |
| BR-DEPT-004 | Only HOD edits/hides/deletes active announcements | services + grant | `department.announcement.update` / `.delete` only on HOD | |
| BR-DEPT-005 | Only Faculty request stock | services + grant | `department.stock_request.create` only on `faculty` | |
| BR-DEPT-006 | Only HOD approves/rejects pending stock request | domain state table | `STOCK_TRANSITIONS` actor = HOD; `department.stock_request.approve` | |
| BR-DEPT-007 | Dept_Admin issues only HOD-approved requests | domain state table | `approved → issued`, actor = DEPT_ADMIN | Other `from` states are inexpressible |
| BR-DEPT-008 | Only authenticated Students/Faculty submit feedback | services + grant | `department.feedback.create` on `student`, `faculty` | |
| BR-DEPT-009 | Only Dept_Admin/HOD mark Resolved/Closed | domain state table | `FEEDBACK_TRANSITIONS` | |
| BR-DEPT-010 | A timetable update must not be saved (or advanced for approval) when overlapping slots are detected | domain + services | `domain/rules.find_overlaps`; service holds `select_for_update` on department | Overlap definition → Q6 |
| BR-DEPT-011 | Official change stays pending until HOD approves | domain + services | `OfficialChange` state table; `Department` row unchanged until approve | Headship excluded |
| BR-DEPT-012 | Faculty resource views limited to resource information within Faculty scope: lab resource profiles and relevant issued-stock history | selectors | `scoping.lab_resources_for`, `scoping.stock_requests_for` | "Relevant" → Q12 |
| BR-DEPT-013 | Only HOD decides official change | domain state table | `department.official_change.approve` | No self-decision guard (Q14) |
| BR-DEPT-015 | Request enters HOD approval only if stock suffices at submission | domain + services | `domain/rules.check_availability` under item row lock | No reservation (PS §4) |
| BR-DEPT-016 | Every insertion and issuance appends an immutable movement | models + services | `StockMovement`: no update/delete path; model `save()` refuses update; no serializer writes it | |
| BR-DEPT-017 | Feedback visible only to submitter and handling Dept_Admin/HOD | selectors | `scoping.feedback_for` | Never in any list for other roles; 404 |
| BR-DEPT-018 | New feedback reviewed by Dept_Admin first; HOD acts after | domain + selectors | state table: only DEPT_ADMIN leaves `new`; HOD's queryset excludes `new` | |
| BR-DEPT-019 | Profile field visibility by viewer role/relationship | selectors + serializers | `selectors/profiles.profile_view_for(actor, ids)` returns tiered DTOs | Course relation → Q2; sensitive data never stored |
| BR-DEPT-021 | Only central authority assigns HOD/Dept_Admin; active HOD gives Headship | services + grant | `department.role_assignment.assign` on Q3 role | Depends on Q1 |
| BR-DEPT-022 | Exactly one active HOD and one active Dept_Admin per department | models + services | partial-unique checks under `select_for_update` on department | "Exactly one" vs initial gap → Q1 |
| BR-DEPT-023 | Each assignment has a validity interval | models | `valid_from`, `valid_to` NOT NULL; `CheckConstraint(valid_to > valid_from)` | |
| BR-DEPT-024 | At effective time, outgoing role access revoked immediately and incoming access granted immediately | selectors + tasks | "in effect now" computed per request; beat task records the transition | Limited to DEPT rows → Q1 |

### Use cases

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| UC-DEPT-001 | View relevant announcements; empty state | selectors + api | `GET /announcements` | |
| UC-DEPT-002 | Create announcement, validate, publish, notify audience | services | `POST /announcements` → outbox rows per recipient (AFR-046) | |
| UC-DEPT-003 | HOD edit / hide / delete active announcement | services | `PATCH /announcements/{id}`, `POST .../hide`, `DELETE` | Delete = soft (Q7) |
| UC-DEPT-004 | Faculty request stock; availability; notify Dept_Admin + HOD | services | `POST /stock-requests` | 422 `insufficient_stock` |
| UC-DEPT-005 | HOD approve/reject; notify on reject | services | `POST /stock-requests/{id}/decide` | |
| UC-DEPT-006 | Dept_Admin issue; decrement; log; notify | services | `POST /stock-requests/{id}/issue` | Atomic |
| UC-DEPT-007 | Submit confidential feedback; notify Dept_Admin | services | `POST /feedback` | |
| UC-DEPT-008 | Dept_Admin initial review, categorize, optionally resolve/close | services | `POST /feedback/{id}/review`, `POST /feedback/{id}/dispose` | |
| UC-DEPT-009 | Upload/modify timetable, block overlaps | services | `POST /timetable-slots`, `PATCH /timetable-slots/{id}` | |
| UC-DEPT-010 | Update general details; official → pending | services | `PATCH /departments/{code}`, `POST /official-changes` | |
| UC-DEPT-011 | Faculty view lab resource profiles and relevant issued-stock history | selectors | `GET /lab-resources`, `GET /stock-requests?status=issued` | Q12 |
| UC-DEPT-012 | HOD approve/reject official change | services | `POST /official-changes/{id}/decide` | |
| UC-DEPT-014 | HOD oversight and resolution after initial review | services | `POST /feedback/{id}/dispose` (HOD), `POST /feedback/{id}/notes` | |
| UC-DEPT-015 | View profiles at permitted tier | selectors | `GET /profiles` (each row at its tier; `PATCH /profiles/{id}` takes the profile record id) | |
| UC-DEPT-016 | Dept_Admin manage Faculty/Student/Alumni profile records | services | `POST/PATCH /profiles` | Scope of "manage" → Q8 |
| UC-DEPT-017 | Dept_Admin update lab profiles | services | `POST/PATCH /lab-resources` | |
| UC-DEPT-018 | Student view programme info + timetable | selectors | `GET /departments/{code}`, `GET /timetable-slots` | Programme source → Q9 |
| UC-DEPT-019 | Dept_Admin insert stock; log | services | `POST /inventory-items`, `POST /inventory-items/{id}/receipts` | |
| UC-DEPT-020 | Central authority creates or changes a time-bound assignment | services | `POST /role-assignments`, `PATCH /role-assignments/{id}` | Assignee must be an institute employee; Q1, Q3 |
| UC-DEPT-022 | System applies effective transition | tasks + selectors | beat `department.apply_role_transitions` | Q1 |

### Workflows

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BW-DEPT-01 | No stock request → Pending HOD Approval → Approved for Issuance → Issued | domain | `STOCK_TRANSITIONS` | |
| BW-DEPT-02 | No stock request → Pending HOD Approval → Rejected | domain | `STOCK_TRANSITIONS` | |
| CW-DEPT-01 | Union of 01/02 | domain | same table | Exhaustive matrix test |
| BW-DEPT-03 | new → under_review → resolved/closed by Dept_Admin | domain | `FEEDBACK_TRANSITIONS` | |
| BW-DEPT-04 | new → under_review → resolved/closed by HOD | domain | `FEEDBACK_TRANSITIONS` | |
| CW-DEPT-02 | Union of 03/04 | domain | same table | |
| BW-DEPT-05 | Current data effective → Pending HOD Approval → Updated official data effective | domain | `OFFICIAL_CHANGE_TRANSITIONS` | |
| BW-DEPT-06 | Current data effective → Pending HOD Approval → Rejected; current data retained | domain | `OFFICIAL_CHANGE_TRANSITIONS` | |
| CW-DEPT-03 | Union of 05/06 | domain | same table | |
| BW-DEPT-07 | HOD reassignment recorded → effective, Headship synced | services + tasks | `role_assignments` service + beat | Q1 |
| BW-DEPT-08 | Dept_Admin reassignment recorded → effective | services + tasks | same | Q1 |
| CW-DEPT-04 | Union of 07/08 | services + tasks | same | Q1 |

### Requirements (CFR → AFR)

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| CFR-DEPT-001 | Publish targeted announcements + notify | services | UC-DEPT-002 | |
| AFR-DEPT-001 | Faculty/Dept_Admin/HOD create & publish | services + grant | `POST /announcements` | |
| AFR-DEPT-046 | Notify relevant Students/Faculty on publish | services | outbox, recipients from targeting (Q10) | |
| CFR-DEPT-002 | Visibility by role/programme/year | selectors | `announcements_for` | |
| AFR-DEPT-002 | Filter by role, programme, academic year | selectors | `announcements_for` | |
| AFR-DEPT-003 | Authenticated users view relevant ones | api + selectors | `GET /announcements` | |
| CFR-DEPT-003 | HOD maintains active announcements | services | UC-DEPT-003 | |
| AFR-DEPT-004 | HOD edit | services | `PATCH /announcements/{id}` | |
| AFR-DEPT-005 | HOD hide | services | `POST /announcements/{id}/hide` | |
| AFR-DEPT-006 | HOD delete | services | `DELETE /announcements/{id}` | Q7 |
| CFR-DEPT-004 | Inventory records + insertion audit | services + models | UC-DEPT-019 | |
| AFR-DEPT-007 | Dept_Admin inserts stock | services | `POST /inventory-items[/{id}/receipts]` | |
| AFR-DEPT-008 | Maintain current quantity | models + services | `current_quantity` from ledger | |
| AFR-DEPT-014 | Immutable insertion log | models | `StockMovement(kind=receipt)` | |
| CFR-DEPT-005 | Stock request to final outcome | domain + services | CW-DEPT-01 | |
| AFR-DEPT-009 | Faculty submit request | services | `POST /stock-requests` | |
| AFR-DEPT-010 | Validate quantity vs current inventory | domain | `check_availability` | |
| AFR-DEPT-011 | HOD approve/reject | services | `/decide` | |
| AFR-DEPT-012 | Dept_Admin issues only approved | domain | state table | |
| AFR-DEPT-013 | Auto-decrement on issue | services | `issue_stock` | Non-negative backstop → Q13 |
| AFR-DEPT-015 | Immutable issuance log | models | `StockMovement(kind=issue)` | |
| AFR-DEPT-041 | Notify Dept_Admin on new request | services | outbox `stock_request.created` | Recipient = active Dept_Admin (Q1) |
| AFR-DEPT-042 | Notify HOD when authorization needed | services | outbox `stock_request.pending_hod` | Recipient = active HOD (Q1) |
| AFR-DEPT-043 | Notify Faculty on Issued/Rejected only | services | outbox on those two transitions | Not on approve |
| CFR-DEPT-006 | Faculty view their relevant issued-stock history | selectors | `stock_requests_for` filtered to `issued` | "Relevant" → Q12 |
| AFR-DEPT-016 | Faculty view their relevant issued-stock history | selectors | same | Q12 |
| CFR-DEPT-007 | Submit confidential feedback + notify | services | UC-DEPT-007 | |
| AFR-DEPT-017 | Students/Faculty submit | services + grant | `POST /feedback` | |
| AFR-DEPT-018 | Confidential | selectors | `feedback_for` | |
| AFR-DEPT-044 | Notify Dept_Admin | services | outbox `feedback.created` | |
| CFR-DEPT-008 | Review and resolve feedback | domain + services | CW-DEPT-02 | |
| AFR-DEPT-019 | Dept_Admin initial review | domain | `new → under_review` DEPT_ADMIN only | |
| AFR-DEPT-020 | Allow Dept_Admin to categorize during initial review | services | optional `category` on `/review` (Q11) | Not mandatory ("as applicable", UC-DEPT-008) |
| AFR-DEPT-021 | Close simple issue during initial review | services | `/review` with `close=true`: two legal transitions, one transaction | BR-DEPT-018 still holds |
| AFR-DEPT-022 | Dept_Admin or HOD Resolved/Closed | domain | state table | |
| AFR-DEPT-023 | Allow the HOD to access feedback after initial review for oversight and resolution actions | selectors + services | `feedback_for(HOD)` excludes `new`; HOD notes (`/notes`) and disposition (`/dispose`) | |
| AFR-DEPT-045 | Notify submitter on terminal | services | outbox `feedback.disposed` | |
| CFR-DEPT-009 | Dept_Admin manage profiles | services | UC-DEPT-016 | Q8 |
| AFR-DEPT-024 | Same | services | `ProfileRecord` writes | Q8 |
| CFR-DEPT-010 | Profile visibility | selectors | `profile_view_for` | |
| AFR-DEPT-025 | Students: basic for peers/Faculty | selectors | tier BASIC | |
| AFR-DEPT-026 | Faculty: detailed for own course Students | selectors | tier DETAILED if relation known | Q2 |
| AFR-DEPT-027 | Faculty: limited for Faculty/Alumni | selectors | tier LIMITED | |
| AFR-DEPT-028 | HOD/Dept_Admin: full minus sensitive | selectors | tier FULL; sensitive never stored | |
| CFR-DEPT-011 | Conflict-free timetables | domain + services | UC-DEPT-009 | |
| AFR-DEPT-029 | Upload | services | `POST /timetable-slots` (batch) | |
| AFR-DEPT-030 | Modify | services | `PATCH /timetable-slots/{id}` | |
| AFR-DEPT-031 | Detect and block overlaps | domain | `find_overlaps` | Q6 |
| CFR-DEPT-012 | Lab resource profiles | services + selectors | UC-DEPT-017, 011 | |
| AFR-DEPT-034 | Dept_Admin update lab details | services | `POST/PATCH /lab-resources` | |
| AFR-DEPT-035 | Faculty view lab profiles | selectors | `GET /lab-resources` | |
| CFR-DEPT-013 | Student academic info | selectors | UC-DEPT-018 | |
| AFR-DEPT-036 | Students view programme info | selectors | `GET /departments/{code}` programmes block | Q9 |
| AFR-DEPT-037 | Students view applicable timetable | selectors | `timetable_for(student)` by programme + batch | |
| CFR-DEPT-014 | General details | services | UC-DEPT-010 general branch | |
| AFR-DEPT-038 | Dept_Admin update general info | services | `PATCH /departments/{code}` (general fields only) | |
| CFR-DEPT-015 | Official changes pending until HOD | domain + services | CW-DEPT-03 | |
| AFR-DEPT-039 | Pending, not published before approval | services | `Department` untouched until approve | |
| AFR-DEPT-040 | HOD approve/reject | services | `/official-changes/{id}/decide` | |
| CFR-DEPT-016 | Role assignments and effective access | services + tasks | UC-DEPT-020/022 | Q1 |
| AFR-DEPT-047 | Central authority assigns HOD/Dept_Admin to institute employees | services + grant | `POST /role-assignments`; assignee `kind` must be faculty or staff (`directory.get_users`), else 422 `not_employee` | Q1, Q3 |
| AFR-DEPT-048 | Time-bounded validity | models | `valid_from`/`valid_to` | |
| AFR-DEPT-049 | Revoke outgoing immediately | selectors | in-effect check on every request | Q1 |
| AFR-DEPT-050 | Grant incoming immediately | selectors | same | Q1 |
| AFR-DEPT-051 | Exactly one active HOD | services + models | locked overlap check | Q1 |
| AFR-DEPT-052 | Exactly one active Dept_Admin | services + models | same | Q1 |
| AFR-DEPT-053 | Headship derived from active HOD | selectors | `headship_for(departments)`; no stored field | |

---

## 2. (b) Domain model (Step 3.2)

All tables live in `fusion_integrated`. People are plain `user_id` integers. There are no
foreign keys to another module.

| Entity | Fields | Invariants (DB-enforced unless noted) |
|---|---|---|
| `Department` | `code` (CSE, ECE, ME, Design, NS, SM, LA), `name`, `core_policies`, general: `description`, `contact_email`, `contact_phone`, `office_location`, `website` | `UniqueConstraint(code)`; `name` non-blank `CheckConstraint` |
| `OfficialChange` | `department`, `field` (`name`/`core_policies`), `proposed_value`, `previous_value`, `status` (pending/approved/rejected), `proposed_by`, `decided_by`, `decided_at`, `reason` | `CheckConstraint(field in (name, core_policies))` (Headship inexpressible); partial unique: one `pending` per (department, field); self-decision guard only if Q14 says so |
| `Announcement` | `department`, `title`, `body`, `audience_role` (student/faculty/dept_admin/hod/all), `programme` (blank = any), `batch_year` (null = any), `status` (active/hidden/deleted), `author_id`, `published_at`, `edited_at` | `title`, `body` non-blank checks |
| `InventoryItem` | `department`, `name`, `unit`, `current_quantity` | `CheckConstraint(current_quantity >= 0)`; unique (department, lower(name)) |
| `StockMovement` | `item`, `kind` (receipt/issue), `quantity`, `actor_id`, `stock_request` (null for receipt), `note`, `created_at` | `CheckConstraint(quantity > 0)`; `CheckConstraint(kind=issue ⇔ stock_request not null)`; unique (stock_request) for issues; append-only: `save()` refuses update, `delete()` raises, no API write |
| `StockRequest` | `department`, `item`, `requester_id`, `quantity`, `status` (pending_hod/approved/rejected/issued), `decided_by`, `decided_at`, `reason`, `issued_by`, `issued_at` | `CheckConstraint(quantity > 0)`; status choices; self-decision guard only if Q14 says so |
| `Feedback` | `department`, `submitter_id`, `submitter_kind`, `subject`, `body`, `category` (optional; set during initial review, may stay blank), `status` (new/under_review/resolved/closed), `reviewed_by`, `reviewed_at`, `disposed_by`, `disposed_at`, `resolution_note` | `CheckConstraint(status=new ⇔ reviewed_by is null)` |
| `FeedbackNote` | `feedback`, `author_id`, `body` | HOD oversight note (UC-DEPT-014 alt. flow); append-only |
| `TimetableSlot` | `department`, `kind` (class/lab), `programme`, `batch_year`, `course_code`, `day_of_week` 0..6, `starts_at`, `ends_at`, `room`, `updated_by` | `CheckConstraint(ends_at > starts_at)`; overlap checked in service under department lock (Q6) |
| `LabResource` | `department`, `name`, `location`, `equipment` (text), `capacity`, `status` (available/maintenance/retired), `updated_by` | unique (department, name) |
| `ProfileRecord` | `department`, `user_id` (null for an alumnus without a login), `kind` (faculty/student/alumni), `display_name`, `office`, `research_interests`, `bio`, `graduation_year`, `current_position`, `updated_by` | unique (department, user_id) where user_id not null; no sensitive field exists (Q8) |
| `RoleTenure` (only if Q1 approved) | `department`, `role` (hod/dept_admin), `user_id`, `valid_from`, `valid_to`, `assigned_by`, `transition_applied_at` | `CheckConstraint(valid_to > valid_from)`; overlap check under `select_for_update` on department; not an RBAC table: grants nothing, only narrows rows |
| `DepartmentNotification` | outbox, same shape as Placement's `NotificationOutbox` | `dedupe_key` unique |

The ledger rule (2.7) means `current_quantity` changes only inside `services/inventory.py`, in the
same transaction as its `StockMovement`, holding `select_for_update` on the item row.

---

## 3. (c) State machines (Step 3.3)

All live in `domain/state_machine.py` as declarative `(from, to) → Transition(permission, actors)`
tables, in the same shape as Placement's. A pair that isn't in the table can't be expressed.

**Stock request** (BW-DEPT-01/02, CW-DEPT-01)

| From | To | Actor | Permission |
|---|---|---|---|
| (none) | pending_hod | FACULTY | `department.stock_request.create` (guard: `stock_available`) |
| pending_hod | approved | HOD | `department.stock_request.approve` (guard `not_self` only if Q14 says so) |
| pending_hod | rejected | HOD | `department.stock_request.approve` (guard `not_self` only if Q14 says so) |
| approved | issued | DEPT_ADMIN | `department.stock_issue.create` |

**Feedback** (BW-DEPT-03/04, CW-DEPT-02)

| From | To | Actor | Permission |
|---|---|---|---|
| (none) | new | STUDENT, FACULTY | `department.feedback.create` |
| new | under_review | DEPT_ADMIN | `department.feedback.review` |
| under_review | resolved | DEPT_ADMIN, HOD | `department.feedback_resolution.create` |
| under_review | closed | DEPT_ADMIN, HOD | `department.feedback_resolution.create` |

**Official change** (BW-DEPT-05/06, CW-DEPT-03)

| From | To | Actor | Permission |
|---|---|---|---|
| (none) | pending | DEPT_ADMIN | `department.official_change.create` |
| pending | approved | HOD | `department.official_change.approve` (guard `not_proposer` only if Q14 says so) |
| pending | rejected | HOD | `department.official_change.approve` (guard `not_proposer` only if Q14 says so) |

**Role tenure** (BW-DEPT-07/08, only if Q1 approved): recorded → in effect → ended. These follow
the clock, not an event, so in-effect means `valid_from <= now < valid_to`. That is computed on
every read, so access never waits for a worker. The beat task only stamps
`transition_applied_at` and queues the audit notification.

---

## 4. (d) Permission list: exact `registry.py` content (Step 3.4)

```python
MODULE = {
    "code": "department", "label": "Department", "icon": "Buildings",
    "base_path": "/department", "nav_section": "Academics", "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("department.department.view", "See department details and headship"),
    ("department.department.update", "Update general department details"),
    ("department.official_change.view", "See proposed official changes"),
    ("department.official_change.create", "Propose an official change"),
    ("department.official_change.approve", "Approve or reject an official change"),
    ("department.announcement.view", "See relevant announcements"),
    ("department.announcement.create", "Publish an announcement"),
    ("department.announcement.update", "Edit or hide an active announcement"),
    ("department.announcement.delete", "Delete an active announcement"),
    ("department.inventory_item.view", "See inventory items and quantities"),
    ("department.inventory_item.create", "Add items and record stock receipts"),
    ("department.stock_movement.view", "See the stock movement log"),
    ("department.stock_request.view", "See stock requests in scope"),
    ("department.stock_request.create", "Request stock"),
    ("department.stock_request.approve", "Approve or reject a stock request"),
    ("department.stock_issue.create", "Issue approved stock"),
    ("department.feedback.view", "See feedback in scope"),
    ("department.feedback.create", "Submit feedback"),
    ("department.feedback.review", "Initial review and categorisation"),
    ("department.feedback_resolution.create", "Mark feedback resolved or closed"),
    ("department.timetable.view", "See timetables"),
    ("department.timetable.create", "Upload timetable slots"),
    ("department.timetable.update", "Modify or remove timetable slots"),
    ("department.lab_resource.view", "See lab resource profiles"),
    ("department.lab_resource.update", "Add and update lab resource profiles"),
    ("department.profile.view", "See department profiles at your tier"),
    ("department.profile.update", "Manage department profile records"),
    ("department.role_assignment.view", "See HOD and Dept_Admin tenures"),
    ("department.role_assignment.assign", "Record an HOD or Dept_Admin tenure"),
    ("department.role_assignment.update", "System: apply a tenure taking effect"),
]

SYSTEM_PERMISSIONS = ["department.role_assignment.update"]

SCOPE_PERMISSIONS = {}   # scope is the department, decided in selectors/scoping.py

_STUDENT = ["department.department.view", "department.announcement.view",
            "department.feedback.view", "department.feedback.create",
            "department.timetable.view", "department.profile.view"]

_FACULTY = [*_STUDENT, "department.announcement.create",
            "department.inventory_item.view", "department.stock_request.view",
            "department.stock_request.create", "department.lab_resource.view"]

_DEPT_ADMIN = ["department.department.view", "department.department.update",
               "department.official_change.view", "department.official_change.create",
               "department.announcement.view", "department.announcement.create",
               "department.inventory_item.view", "department.inventory_item.create",
               "department.stock_movement.view", "department.stock_request.view",
               "department.stock_issue.create", "department.feedback.view",
               "department.feedback.review", "department.feedback_resolution.create",
               "department.timetable.view", "department.timetable.create",
               "department.timetable.update", "department.lab_resource.view",
               "department.lab_resource.update", "department.profile.view",
               "department.profile.update", "department.role_assignment.view"]

_HOD = ["department.department.view", "department.official_change.view",
        "department.official_change.approve", "department.announcement.view",
        "department.announcement.create", "department.announcement.update",
        "department.announcement.delete", "department.inventory_item.view",
        "department.stock_movement.view", "department.stock_request.view",
        "department.stock_request.approve", "department.feedback.view",
        "department.feedback_resolution.create", "department.timetable.view",
        "department.lab_resource.view", "department.profile.view",
        "department.role_assignment.view"]

_CENTRAL = ["department.department.view", "department.role_assignment.view",
            "department.role_assignment.assign"]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    # Spelled exactly as globals_designation (copied from fusionlab, 2026-11-22).
    "HOD (CSE)": _HOD, "HOD (Design)": _HOD, "HOD (ECE)": _HOD,
    "HOD (Liberal Arts)": _HOD, "HOD (ME)": _HOD, "HOD (NS)": _HOD,
    "deptadmin_cse": _DEPT_ADMIN, "deptadmin_design": _DEPT_ADMIN,
    "deptadmin_ece": _DEPT_ADMIN, "deptadmin_liberalarts": _DEPT_ADMIN,
    "deptadmin_me": _DEPT_ADMIN, "deptadmin_ns": _DEPT_ADMIN,
    "deptadmin_sm": _DEPT_ADMIN,
    "acadadmin": _CENTRAL,        # Q3: proposed "equivalent central authority"
}
```

Role sources (Step 2.4, derived, cited): Student (BR-DEPT-008, UC-DEPT-007/018), Faculty (BR-DEPT-001,
005, UC-DEPT-004), HOD (BR-DEPT-004, 006, 013, UC-DEPT-005/012/014), Dept_Admin (BR-DEPT-007, 010,
018, UC-DEPT-006/008/009), central authority (BR-DEPT-021, UC-DEPT-020).

Facts used:
- **Department from designation.** The acting designation's name gives the department:
  `HOD (CSE)` → CSE, `deptadmin_cse` → CSE, `HOD (NS)` → NS, `HOD (Liberal Arts)` → LA. This
  mapping is a constant in `domain/roles.py`. Per "only the active role counts", a HOD acts in
  their own department only.
- **`dept_admin` (no department) is not granted.** A grant without a department would reach
  every department or none.
- **No `HOD (SM)` exists.** → Q4.
- **No account in `fusion-dev.dump` holds a `deptadmin_*` designation.** Test accounts are
  provisioned with `assign_role` (Part 5 of `role-assignment-guide.md`).
- **The module is not granted to `staff` or to any other designation.**
- **No `is_dangerous` permission.** Nothing here moves money or grants IAM permissions.
  `role_assignment.assign` narrows rows inside DEPT only (Q1).

---

## 5. (e) Endpoints (Step 3.5)

Every endpoint sits behind `HasModuleGrant("department")` + `HasPermission(<code>)`. Lists use
cursor pagination. Out-of-scope rows give 404, an illegal transition gives 409, and a business
rule refusal gives 422 (`api-conventions.md`).

| Method | Path under `/api/v1/department/` | Permission | Returns | Rules |
|---|---|---|---|---|
| GET | `context` | `department.view` | the acting role and department, so the client shows only that role's controls | Step 3.4 "only the acting role counts" |
| GET | `departments` | `department.view` | departments in scope, with headship | AFR-053 |
| GET | `departments/{code}` | `department.view` | details, headship, programmes | UC-010/018 |
| PATCH | `departments/{code}` | `department.update` | updated (general fields only; official field → 422 `official_field`) | AFR-038 |
| GET | `official-changes` | `official_change.view` | list | BR-011 |
| POST | `official-changes` | `official_change.create` | 201 pending | BR-011 |
| POST | `official-changes/{id}/decide` | `official_change.approve` | decided | BR-013 |
| GET | `announcements` | `announcement.view` | relevant list | BR-002 |
| POST | `announcements` | `announcement.create` | 201 | BR-001/003, AFR-046 |
| PATCH | `announcements/{id}` | `announcement.update` | edited | BR-004/003 |
| POST | `announcements/{id}/hide` | `announcement.update` | hidden | AFR-005 |
| DELETE | `announcements/{id}` | `announcement.delete` | 204 | AFR-006 |
| GET | `inventory-items` | `inventory_item.view` | items + quantity | AFR-008 |
| POST | `inventory-items` | `inventory_item.create` | 201 + receipt movement | AFR-007/014 |
| POST | `inventory-items/{id}/receipts` | `inventory_item.create` | 201 movement | AFR-014 |
| GET | `stock-movements` | `stock_movement.view` | ledger | BR-016 |
| GET | `stock-requests` | `stock_request.view` | in scope | BR-012, AFR-016 |
| POST | `stock-requests` | `stock_request.create` | 201 pending_hod | BR-005/015 |
| POST | `stock-requests/{id}/decide` | `stock_request.approve` | decided | BR-006 |
| POST | `stock-requests/{id}/issue` | `stock_issue.create` | issued | BR-007/016 |
| GET | `feedback` | `feedback.view` | in scope | BR-017 |
| POST | `feedback` | `feedback.create` | 201 new | BR-008 |
| GET | `feedback/{id}` | `feedback.view` | one feedback, with its notes, in the viewer's scope (404 otherwise) | BR-017, BR-018 |
| POST | `feedback/{id}/review` | `feedback.review` | under_review (or closed) | BR-018, AFR-021 |
| POST | `feedback/{id}/dispose` | `feedback_resolution.create` | resolved/closed | BR-009 |
| POST | `feedback/{id}/notes` | `feedback_resolution.create` | 201 note | UC-014 |
| GET | `timetable-slots` | `timetable.view` | the applicable week's slots, whole and unpaginated (the one exception to cursor pagination: a week is one screen, sorted by day and time) | AFR-037 |
| POST | `timetable-slots` | `timetable.create` | 201 batch; 422 `timetable_conflict` with clashes | BR-010 |
| PATCH | `timetable-slots/{id}` | `timetable.update` | updated / 422 | BR-010 |
| DELETE | `timetable-slots/{id}` | `timetable.update` | 204 | AFR-030 |
| GET | `lab-resources` | `lab_resource.view` | in scope | BR-012 |
| POST / PATCH | `lab-resources[/{id}]` | `lab_resource.update` | 201 / updated | AFR-034 |
| GET | `profiles`, `profiles/{id}` | `profile.view` | tiered | BR-019 |
| POST / PATCH | `profiles[/{id}]` | `profile.update` | 201 / updated | AFR-024 |
| GET | `role-assignments` | `role_assignment.view` | tenures | BR-021..023 |
| GET | `role-assignments/vacancies` | `role_assignment.view` | each vacant or ending role in the viewer's departments (Q1 mitigation) | BR-022 |
| POST | `role-assignments` | `role_assignment.assign` | 201 / 409 `tenure_overlap` / 422 `not_employee` | BR-021..023, AFR-047 |
| PATCH | `role-assignments/{id}` | `role_assignment.assign` | changed validity interval / 409 `tenure_overlap` | UC-020 ("create or change"), BR-023 |

All write endpoints carry `throttle_scope = "department_write"` and the platform CSRF check.

### Client routes (`client/src/modules/department/routes.tsx`), each with a nav item

| Route | Nav label | Guard (`RequirePermission`) |
|---|---|---|
| `/department/overview` (the bare `/department` redirects here) | Overview | `department.department.view` (details; official-change panel shown by permission) |
| `/department/announcements` | Announcements | `department.announcement.view` |
| `/department/inventory` | Inventory & Stock | `department.inventory_item.view` |
| `/department/feedback` | Feedback | `department.feedback.view` |
| `/department/timetable` | Timetable | `department.timetable.view` |
| `/department/labs` | Lab Resources | `department.lab_resource.view` |
| `/department/profiles` | People | `department.profile.view` |
| `/department/roles` | HOD & Dept_Admin | `department.role_assignment.view` |

Record details open in a drawer on the list page. No detail route exists.

### `Fusion-client` sidebar entry (cannot be added in `module-only`)

```js
{ id: "department", label: "Department", icon: "Buildings", to: "/department/overview", section: "Academics" }
```

---

## 6. (f) Contracts (Step 3.6)

**Exposed by `modules/department/contracts.py`** (plural):

- `get_headships(department_codes: Sequence[str]) -> dict[str, HeadshipDTO]`, which gives the
  current HOD `user_id` per department (AFR-DEPT-053). It is only meaningful if Q1 is approved.

**Used from others:** `directory.contracts.get_users`, `directory.contracts.search`. Nothing new is
needed from any module.

**Missing IAM projection (stop, per Step 3.6): Q2.** No endpoint on the IAM's `main` gives course
rosters (which students are in a given faculty member's courses). I will not add an `IamClient`
method or a `FakeIam` twin for it.

---

## 7. (g) Scheduled work (Step 3.7)

| Beat entry | Cadence | Breaks in the real world if it does not run |
|---|---|---|
| `department.deliver_notifications` | 60 s, queue `notifications` | Every AFR-041..046 notice sits in the outbox. Nobody learns of a stock request, feedback or announcement. |
| `department.apply_role_transitions` (only if Q1 approved) | 60 s, default queue | Access is still correct, because "in effect" is computed per request. What goes missing is the transition record, the audit row and the change-of-head notice. |

Both tasks are idempotent and also run as `manage.py run_department_tasks`.

---

## 8. (h) Open questions (Step 3.8): each needs Student 2's written answer before code

**Q1. Role assignment (BR-DEPT-021..024, UC-DEPT-020/022, BW-DEPT-07/08, CW-DEPT-04, AFR-047..053).**
This is a conflict between the spec and the architecture, so it is escalated, not decided here.
Who holds a designation belongs to the ERP and IAM. This module can't write it, and it may not own
a role table.

*Proposal:* a `RoleTenure` table that is a **business record, not RBAC**. It never grants a
permission and only narrows rows. A person acts as HOD or Dept_Admin of department D only if
**both** of these hold:
1. their acting IAM designation holds the permission (the verb);
2. a tenure for D naming them is in effect now (the rows).

Results:
- Revocation inside DEPT is immediate (AFR-049/050).
- Headship is derived from the tenure (AFR-053).
- Notification recipients (AFR-041/042/044) are known.

*Spec impact (disclosed): this proposal does not fully meet BR-DEPT-024 / AFR-DEPT-049 / AFR-DEPT-050.*
- Inside DEPT, the switch-over is immediate: the outgoing holder's DEPT rows are empty and their
  DEPT actions are refused from `valid_to`; the incoming holder's work from `valid_from`.
- Outside DEPT, it is not: the IAM designation (and so the sidebar link and the module grant) is
  changed separately by the central authority with `assign_role`. The module cannot do it, because
  the IAM has no write endpoint and a module may not write the ERP.

*Cardinality: this proposal does not fully meet BR-DEPT-022 / AFR-DEPT-051 / AFR-DEPT-052.*
"Exactly one at any given time" and "time-bounded" (BR-DEPT-023) can only both hold if a successor
is always recorded before the current tenure ends, and only the central authority can do that.
What the module enforces:
- **never more than one** in effect (locked overlap check, 409 `tenure_overlap`);
- a reassignment closes the outgoing tenure exactly at the incoming `valid_from`, in one locked
  transaction, so a reassignment never leaves a gap;
- a tenure's `valid_to` cannot be moved earlier unless a successor already starts at that moment;
- `check_department_readiness` and the Roles page flag any department with no holder now, or
  whose holder ends within 30 days with no successor recorded.

What it cannot prevent: a department before its first assignment, or a tenure reaching its
`valid_to` with nobody recorded after it. During such a gap the role's actions for that department
are unavailable (fail closed), never granted to someone else.

**Ruling needed:** approve this as written, or choose (a) stop and escalate to the course staff,
or (b) another reading of BR-DEPT-022.

**Q2. Faculty-to-course relation (AFR-DEPT-026).** There's no roster endpoint on the IAM's `main`.
*Proposal:* treat it as a known gap. Until the IAM publishes rosters, Faculty see students only at
the **BASIC** tier (what a student sees of a peer), never DETAILED. BR-DEPT-019 grants Faculty
nothing about students outside their courses, so BASIC is the least that keeps the People page
usable without disclosing more than any department member already sees. The IAM addition is
listed as a dependency. *Spec impact (disclosed):* AFR-DEPT-026 is not met until the IAM adds
rosters. Approve the gap, or tell me to stop the module until the IAM has the endpoint.

**Q3. "Institute Admin or equivalent" (BR-DEPT-021).** No such designation exists. *Proposal:*
`acadadmin`, which already exists and is held by 5 fixture accounts. The alternatives are
`Registrar` or `Director`.

**Q4. HOD for SM.** `deptadmin_sm` exists but `HOD (SM)` does not. *Proposal:* SM has no HOD
grant. Stock approvals, official changes and HOD feedback oversight are unavailable for SM until
the academic office creates `HOD (SM)`. I won't invent the designation, because creating a
designation is the ERP's job, not this module's (Step 3.4). *Spec impact (disclosed):* for SM only,
BR-DEPT-022 / AFR-DEPT-051 and the HOD-gated requirements (CFR-DEPT-003, AFR-DEPT-011, AFR-DEPT-023,
AFR-DEPT-040) cannot be met until `HOD (SM)` exists; when it does, the only change is one line in
`ROLE_GRANTS`. Alternatives: (a) leave SM out of the seeded departments entirely, or (b) map SM to
an existing designation you name.

**Q5. Announcement wildcard (BR-DEPT-002 says wildcard behaviour is unspecified).** *Proposal:* a
blank programme or a null batch year means "any". Audience role is required, one of
student / faculty / dept_admin / hod / all, so every UC-DEPT-001 viewer role can be targeted
(BR-DEPT-002 filters by role). Notification on publish (AFR-046) still goes only to matching
Students and Faculty, as the AFR says.

**Q6. Timetable overlap (BR-DEPT-010 says the definition is domain-specific).** *Proposal:* two
slots on the same day whose time ranges intersect (`start < other_end and other_start < end`)
conflict if they share the **room**, or share the **programme and batch year**. Touching
end-to-start does not conflict.

**Q7. Delete announcement (retention unspecified, AFR-006).** *Proposal:* a soft delete
(`status=deleted`). The row disappears from every view and API, and is kept for audit.

**Q8. "Manage profiles" (AFR-024 says no CRUD policy is stated).** Identity fields (name, email,
programme, batch) belong to the ERP and are read through `directory`. *Proposal:* Dept_Admin
creates and updates a department-local `ProfileRecord` supplement (office, research interests,
bio; for alumni, graduation year and current position). Alumni have no login kind, so an alumnus
is a record with no `user_id`. There is no delete; a record can be deactivated. The module stores
no sensitive data at all: no date of birth, phone, address, category, gender or medical data.
Field tiers:

| Tier | Who sees it | Fields |
|---|---|---|
| BASIC | Student viewing a peer or faculty; Faculty viewing a student (see Q2) | name, kind, programme, department |
| LIMITED | Faculty viewing faculty/alumni | BASIC + email, office, research interests, current position |
| DETAILED | Faculty viewing their course students (blocked by Q2) | LIMITED + username, discipline, batch year |
| FULL | HOD or Dept_Admin, anyone in the department | every stored field |

**Q9. "Academic program information" (AFR-036).** *Proposal:* the programme list for the
student's department comes from the IAM's existing `academics/filters` endpoint, plus the
department's general `description`. Nothing new is stored.

**Q10. Announcement recipients (AFR-046).** *Proposal:* notify the department's students and/or
faculty that match the target, from `directory` (`user_ids_in_discipline` for students; faculty by
`department`), with one outbox row each and email as the channel. "Real-time and/or email" is
satisfied by email. The portal owns the notification bell.

**Q11. Feedback categories (AFR-020 says the vocabulary is unspecified).** *Proposal:* a closed
list: `academic`, `infrastructure`, `administrative`, `facilities`, `other`.

**Q12. "Relevant" issued-stock history (BR-DEPT-012, UC-DEPT-011, AFR-DEPT-016).** The spec says
Faculty view "their relevant issued-stock history" and does not define "relevant". *Proposal:*
the Faculty member's own requests that reached Issued, since "their" is the AFR's own word.
Alternative: every issued request in the Faculty member's department.

**Q13. Stock at issuance (AFR-DEPT-013, PS §4).** PS §4 says the module does not define a second
availability check at issuance. *Proposal:* no business re-check at issuance, exactly as the PS
says. The ledger still keeps `CheckConstraint(current_quantity >= 0)` as a database integrity
backstop (Step 2.7): if two approved requests together exceed stock, the second issuance is
refused with 409 `stock_exhausted` and nothing changes, instead of recording a negative quantity.
Alternative: drop the constraint and allow negative stock.

**Q14. Self-decision (BR-DEPT-006, BR-DEPT-013).** The spec does not forbid an HOD from deciding a
request they made while acting as Faculty, and a department has one HOD, so a guard would leave
that request with nobody able to decide it. *Proposal:* **no** self-decision guard on stock
requests or official changes; the decider is recorded on every decision for audit. Alternative:
keep the guard and accept that such a request can never be decided.

**Gaps outside the module's folders that need approval (Step 7.7):**
- registration lines in `config/settings/base.py`, `config/urls.py`, `config/celery.py`,
  `.importlinter` and `client/src/app/registry.ts`;
- the regenerated `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json` and
  `docs/02-iam/permission-catalog.generated.md`;
- `client/e2e/accounts.ts` entries for HOD and Dept_Admin test accounts.

No new dependency is planned.

---

## Approval record

| Item | Approved by | Date | Where (link or quote) |
|---|---|---|---|
| Blueprint (§1–§7) | Student 2 | 2026-11-22, 19:41 IST | WhatsApp message to Student 1 (shown as edited): "I approve the Department blueprint and Q1-Q14 as proposed, including the changes outside the module's folders." [name and roll number omitted] |
| Q1..Q14 rulings: every proposal as written | Student 2 | 2026-11-22, 19:41 IST | same message |
| Changes outside module folders (§8 list) | Student 2 | 2026-11-22, 19:41 IST | same message |
| Six questions raised in review rounds 1–3 (below): every proposal as written | Student 2 | 2026-11-23, 03:26 IST | WhatsApp message to Student 1: "I agree with all six proposed answers: (1) HOD sees all department announcements, (2) Faculty relevance by role only, (3) notes visible to the submitter, (4) notes allowed after closure, (5) no notice to the outgoing holder, (6) ready with vacancy warnings." [roll number omitted] |
| Round 6 fix-or-waive decision: R6-01 to R6-05 fixed, none waived; Q14 kept; 50-line limit is for functions; no address in stored mail errors | Student 2 | 2026-11-23, 18:05 IST | WhatsApp message to Student 1: "I accept the round 6 fixes for R6-01 to R6-05, with nothing waived. On the reviewer's questions: (1) keep Q14, no self-decision guard on stock requests; (2) the 50-line limit applies to functions, not to describe blocks in tests; (3) a failed email's stored error must not keep an address, as built." |

## Questions raised in review (rounds 1–3), answered

Each answer keeps what the code already does, so none changes behaviour.

| # | Question | Answer (approved 2026-11-23) |
|---|---|---|
| R-Q1 | Which announcements does the HOD see? | Every announcement of the department, whatever its audience. |
| R-Q2 | How is an announcement relevant to Faculty? | By audience role only (`faculty` or `all`); no course or batch filter. |
| R-Q3 | Who sees internal feedback notes? | The submitter sees the notes on their own feedback. |
| R-Q4 | May a note be added after feedback is closed? | Yes; notes stay allowed after resolution or closure. |
| R-Q5 | Is the outgoing HOD or Dept_Admin notified at a switch-over? | No; only the incoming holder is notified. |
| R-Q6 | Is the module ready while a role is vacant? | Yes; readiness passes and names each vacancy as a warning. |

## Changes after approval (review round 1)

These implement what was approved; none changes a ruling.

- The Q1 mitigation is now built: `check_department_readiness` and `GET role-assignments/vacancies`
  (shown on the HOD & Dept_Admin page) name every role with nobody in effect, or ending within
  30 days with no successor.
- BR-DEPT-022 and BR-DEPT-010 are also enforced by the database: triggers in `0001_initial` refuse an
  overlapping tenure or a clashing slot, under a per-department advisory lock. No extension or
  dependency is added.
- The Overview route is `/department/overview`.

## Changes after approval (review round 2)

These enforce what was approved; none changes a ruling.

- **Only the acting role counts, on every write.** The IAM sends the union of every held role's
  permissions, so each write also checks the acting role. Announcements (create, edit, hide,
  delete) are now a declarative table in `domain/state_machine.py`, like the other three
  lifecycles. Every other office write calls `require_acting`. An HOD or Dept_Admin acting in a
  plain role, or whose tenure has ended (BR-DEPT-024), is refused every office write.
- `GET context` reports the acting role, and the client shows an office control only to the
  role that owns it.
- A department name proposal is limited to the 120 characters its column holds. `website` and
  `contact_email` are limited to their columns.
- The timetable list is returned whole (see the endpoint table).

## Changes after approval (review round 5)

These enforce what was approved; none changes a ruling.

- **A successor never cuts the incumbent short.** A tenure that starts inside the current one and
  ends before it is refused (`would_cut_short`), so BR-DEPT-022 holds for the rest of the term.
- A timetable upload takes at most 500 slots.
