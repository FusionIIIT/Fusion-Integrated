# Gymkhana module — blueprint

Status: **approved 2026-11-22** (see the approvals record at the end).

Source specification: the Gymkhana SYNCHRONIZED v1.1 package — Problem Statement (PS), Business Rules
(BR-GYM-001…021), Use Cases (UC-GYM-001…012), Workflows (BW-GYM-01…03), CFR/AFR registry
(CFR-GYM-001…007, AFR-GYM-001…034) and the RTM workbook.

Module code, folder, URL segment and permission prefix: `gymkhana`. Docs folder: `docs/18-gymkhana/`.
Environment: `module-only`.

## 0. Inventory and rulings this blueprint is built on

| Kind | Live | Retired / not live |
|---|---|---|
| Business rules | 21 — BR-GYM-001…021 | none. Pre-sync BR001…BR020 are history; old BR012, BR018, BR019 map to no live id (dropped as implementation detail per the BR preamble). |
| Use cases | 12 — UC-GYM-001…012 | none |
| Workflows | 3 basis — BW-GYM-01, 02, 03 | no composite exists |
| Requirements | CFR-GYM-001…007, AFR-GYM-001…034 | FR-GYM-001…034 (v1.0), renamed one-to-one to AFR-GYM-001…034 |

The RTM's UC/BR/WF columns at CFR and AFR level are empty; coverage below is derived by reading each
requirement, not from the matrix.

Rulings given in Phase 1 (2026-11-22), referred to below as **R1…R10**:

| # | Ruling |
|---|---|
| R1 | Files are Google Drive links validated by `core/files/drive.py`. A missing link is "required file missing" (BR-GYM-018/019, AFR-GYM-030/033). No `core/` change, no new dependency. |
| R2 | Leadership is module-owned, with start/end dates. A change ends the old assignments and starts new ones. No dependency on ERP `co-ordinator` designations. |
| R3 | Club Head permissions are granted to `student`; BR-GYM-010 is enforced per club in scoping. Hide Club Head links from non-leaders where the platform allows, otherwise a clear empty state. |
| R4 | Student Admin is a new designation, `Student Admin`, created locally for testing; which real post holds it is an open question for the academic office. |
| R5 | Report review is granted to `faculty`, scoped to clubs where that faculty member is the assigned councillor; any other club's report is 404. |
| R6 | Session/event notifications go to the club's confirmed members (agreed reading of "intended student recipients"). |
| R7 | Venues come from an operator command / seeded config only; no venue screen. |
| R8 | Least exposure: bookings → club leaders + confirmed members; budget requests → club leaders; event reports → submitting club's leaders + its assigned councillor (not Student Admin); poll results → counts only, to the creating club's leaders; a student sees only their own vote. |
| R9 | Add `students_in_cohorts(batch_years, disciplines)` to `modules/directory/contracts.py`, backed by `academic_directory`. Approved by Student 2. |
| R10 | Half-open booking intervals; club names unique case-insensitively; coordinator ≠ co-coordinator; a student may lead several clubs; student in charge must be a valid student; a report need not link to a booking; poll expiry valid to end of day IST, not in the past at creation, batch/branch checked at vote time; every Club Head operation requires a confirmed club; an event's faculty is the club's assigned councillor, validated as faculty. |

On R3 "where the platform allows": it does not. The IAM builds each role's sidebar from that role's
grants alone (`iam/services.py::navigation_by_designation`); there is no per-person predicate. So the
"My clubs" item appears for every student, and the page shows the empty state *"You do not lead a
club. Club Heads are the coordinator and co-coordinator Student Admin assigned when the club was
created."*

---

## 3.1 (a) Traceability

Layer legend: **D** domain (pure), **M** model/DB constraint, **Se** selector/scoping, **Sv** service,
**A** api (transport only).

### Business rules

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-GYM-001 | Coordinator, co-coordinator and replacements are valid students | Sv | `services/people.py::require_students` (directory `kind == "student"`, `is_active`) called by `clubs.create_club` and `leadership.change_leadership` | Absent from the directory = invalid; message names the field |
| BR-GYM-002 | Faculty councillor is a valid faculty member (creation; event context) | Sv | `people.require_faculty` in `clubs.create_club`; `bookings.book_event` re-validates the club's assigned councillor (R10) | |
| BR-GYM-003 | Category ∈ {Technical, Sports, Cultural} | D + M | `domain/rules.py::CATEGORIES`; `CheckConstraint gym_club_category_valid` | |
| BR-GYM-004 | New club is open; Student Admin approval → confirmed | D + Sv + M | `domain/state_machine.py::CLUB_TRANSITIONS`; `services/clubs.py::approve_club`; `CheckConstraint gym_club_status_valid` | No reject edge exists in the table |
| BR-GYM-005 | Booking start < end | D + M | `domain/rules.py::check_time_range`; `CheckConstraint gym_booking_start_before_end` | |
| BR-GYM-006 | No overlap of any session/event in the same venue on the same date | D + Sv + M | `domain/rules.py::overlaps` (half-open, R10); `services/bookings.py::_book` under a `select_for_update` on the `VenueDay` lock row | Both kinds live in one table, so cross-type overlap is one query. See 3.2 for why no exclusion constraint. |
| BR-GYM-007 | Apply only to a confirmed club | Sv | `services/memberships.py::apply` (club fetched from `confirmed` clubs) | |
| BR-GYM-008 | Applications to different clubs are allowed | M | Uniqueness is `(club, user_id)` only — nothing keyed on `user_id` alone | Tested positively |
| BR-GYM-009 | No duplicate same-club application | M + Sv | `UniqueConstraint gym_membership_one_per_club`; service pre-check gives the message, `IntegrityError` under a race maps to the same 409 | |
| BR-GYM-010 | Only the club's current coordinator/co-coordinator performs Club Head operations | Se + Sv | `selectors/scoping.py::led_clubs(actor)` (current `LeadershipAssignment`, club `confirmed` per R10); every Club Head service resolves its club through it | Foreign club → 404 |
| BR-GYM-011 | Approving an open application → confirmed, keeps optional remarks | D + Sv | `domain/state_machine.py::MEMBERSHIP_TRANSITIONS`; `services/memberships.py::approve` | |
| BR-GYM-012 | Poll has ≥ 2 choices | D + Sv | `domain/rules.py::check_choices`; `services/polls.py::create_poll` | |
| BR-GYM-013 | Poll is addressed to selected batch/branch groups; used for notification and access | D + Sv | `domain/rules.py::in_audience`; notification expansion via `directory.students_in_cohorts`; vote/visibility check in `services/polls.py` and `scoping.polls_open_to` | Empty branch = all branches |
| BR-GYM-014 | Participate only in an active, unexpired poll you are targeted by | D + Sv | `domain/rules.py::poll_is_active` (end of expiry day IST, R10) + `in_audience`; `services/polls.py::cast_vote` | "Active" ≡ not expired: no deactivation exists in the spec |
| BR-GYM-015 | At most one vote per student per poll | M + Sv | `UniqueConstraint gym_vote_one_per_student`; `IntegrityError` → 409 | |
| BR-GYM-016 | Superseded leadership no longer current | M + Sv | `services/leadership.py::change_leadership` sets `valid_to` on current rows and inserts new ones in one transaction; partial unique `gym_leader_one_current_per_role` | History retained (R2) |
| BR-GYM-017 | Budget amount ≥ 0 | D + M | `domain/rules.py::check_amount`; `CheckConstraint gym_budget_amount_non_negative` | |
| BR-GYM-018 | Budget request carries its supporting file | Sv + M | `services/budget.py::submit` → `core.files.drive.parse`; `CheckConstraint gym_budget_document_present` | Drive link (R1) |
| BR-GYM-019 | Event report carries its report file | Sv + M | `services/reports.py::submit` → `drive.parse`; `CheckConstraint gym_report_file_present` | Drive link (R1) |
| BR-GYM-020 | Booking uses a configured venue | Sv | `services/bookings.py::_book` against `selectors/venues.py::current_venues()` | Effective-dated venue list (3.2) |
| BR-GYM-021 | Councillor reads reports only of the club they are assigned to | Se | `scoping.reports_for(actor)` narrows to `club.faculty_councillor_user_id == actor.user_id` | Others → 404 |

### Use cases

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| UC-GYM-001 | Student Admin creates a club, status open | Sv | `services/clubs.py::create_club` | Alt flow: each invalid assignment named in `details` |
| UC-GYM-002 | Club Head books a session | Sv | `services/bookings.py::book_session` | Poster optional |
| UC-GYM-003 | Club Head books an event | Sv | `services/bookings.py::book_event` | Poster required (AFR-GYM-014) |
| UC-GYM-004 | Student applies for membership | Sv | `services/memberships.py::apply` | |
| UC-GYM-005 | Club Head approves one or more open applications | Sv | `services/memberships.py::approve_many` → `approve` per id, each independent | Per-id result list |
| UC-GYM-006 | Club Head creates a poll and notifies its audience | Sv | `services/polls.py::create_poll` | |
| UC-GYM-007 | Student votes once in an eligible poll | Sv | `services/polls.py::cast_vote` | |
| UC-GYM-008 | Club Head replaces coordinator and co-coordinator | Sv | `services/leadership.py::change_leadership` | |
| UC-GYM-009 | Club Head submits a budget request (open) | Sv | `services/budget.py::submit` | |
| UC-GYM-010 | Club Head submits an event report | Sv | `services/reports.py::submit` | |
| UC-GYM-011 | Student Admin approves an open club | Sv | `services/clubs.py::approve_club` | |
| UC-GYM-012 | Councillor lists and opens their club's reports | Se + A | `scoping.reports_for`; `GET event-reports`, `GET event-reports/{id}` | Read only, no state |

### Workflows

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BW-GYM-01 | No application → open (student) → confirmed (Club Head) | D + Sv | `MEMBERSHIP_TRANSITIONS`; `memberships.apply` / `approve` | |
| BW-GYM-02 | Poll not available → open (Club Head) → vote recorded (student) | D + Sv | `polls.create_poll` / `cast_vote`; per-student state is the `Vote` row | No poll status column: open/expired is derived from the date |
| BW-GYM-03 | No club → open → confirmed, both by Student Admin | D + Sv | `CLUB_TRANSITIONS`; `clubs.create_club` / `approve_club` | |

### Requirements

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| CFR-GYM-001 | Club establishment and confirmation | Sv | AFR-GYM-001…006 | |
| CFR-GYM-002 | Leadership change | Sv | AFR-GYM-007…009 | |
| CFR-GYM-003 | Session/event booking with notifications | Sv | AFR-GYM-010…015 | |
| CFR-GYM-004 | Membership enrolment | Sv | AFR-GYM-016…022 | |
| CFR-GYM-005 | Targeted polling | Sv | AFR-GYM-023…028 | |
| CFR-GYM-006 | Budget request submission/tracking | Sv | AFR-GYM-029…031 | |
| CFR-GYM-007 | Event report submission and councillor review | Sv + Se | AFR-GYM-032…034 | |
| AFR-GYM-001 | Create club with name, category, leaders, councillor, description | Sv | `clubs.create_club` | |
| AFR-GYM-002 | Leaders valid students at creation | Sv | `people.require_students` | = BR-GYM-001 |
| AFR-GYM-003 | Councillor valid faculty | Sv | `people.require_faculty` | = BR-GYM-002 |
| AFR-GYM-004 | Category restricted | D + M | `CATEGORIES`, `gym_club_category_valid` | = BR-GYM-003 |
| AFR-GYM-005 | New club recorded open | D + Sv | `CLUB_TRANSITIONS` initial edge | |
| AFR-GYM-006 | Student Admin approves open → confirmed | Sv | `clubs.approve_club` | |
| AFR-GYM-007 | Club Head replaces both leaders | Sv | `leadership.change_leadership` | |
| AFR-GYM-008 | New leaders valid students | Sv | `people.require_students` | |
| AFR-GYM-009 | Only current leaders remain current | M + Sv | partial uniques + `valid_to` | |
| AFR-GYM-010 | Book session: venue, date, start, end, description, optional poster | Sv | `bookings.book_session` | |
| AFR-GYM-011 | Start precedes end | D + M | `check_time_range`, `gym_booking_start_before_end` | |
| AFR-GYM-012 | No overlap in venue/date | Sv | `bookings._book` | |
| AFR-GYM-013 | Notify on session booked | Sv | `bookings.book_session` → `notifications.enqueue_many` to confirmed members (R6) | |
| AFR-GYM-014 | Book event with event details, councillor, venue, date, times, poster, description | Sv | `bookings.book_event` | |
| AFR-GYM-015 | Notify on event booked | Sv | `bookings.book_event` → `notifications.enqueue_many` | |
| AFR-GYM-016 | Apply to a confirmed club with description | Sv | `memberships.apply` | |
| AFR-GYM-017 | Applications to several clubs | M | `(club, user_id)` uniqueness only | |
| AFR-GYM-018 | No duplicate same-club application | M + Sv | `gym_membership_one_per_club` | |
| AFR-GYM-019 | New application recorded open | D + Sv | `MEMBERSHIP_TRANSITIONS` initial edge | |
| AFR-GYM-020 | Club Head sees pending applications for their club | Se | `scoping.memberships_for` | |
| AFR-GYM-021 | Club Head approves with optional remarks | Sv | `memberships.approve` | |
| AFR-GYM-022 | Approved → confirmed | D + Sv | `MEMBERSHIP_TRANSITIONS` | |
| AFR-GYM-023 | Create poll: title, description, expiry, choices, batch/branch targets | Sv | `polls.create_poll` | |
| AFR-GYM-024 | ≥ 2 choices | D | `check_choices` | |
| AFR-GYM-025 | Notify target students on creation | Sv | `polls.create_poll` → one broadcast row expanded by the drain through `students_in_cohorts` | |
| AFR-GYM-026 | Eligible student sees active poll and its choices | Se | `scoping.polls_open_to` | |
| AFR-GYM-027 | Eligible student casts one choice | Sv | `polls.cast_vote` | |
| AFR-GYM-028 | No second vote; accepted vote counted in tally | M + Se | `gym_vote_one_per_student`; tally = `COUNT` per choice in `selectors/polls.py::tallies` | Counted, not a counter column, so no lost update |
| AFR-GYM-029 | Budget request: amount, purpose, description, file | Sv | `budget.submit` | |
| AFR-GYM-030 | Reject negative amount or missing file | D + Sv + M | `check_amount`, `drive.parse`, constraints | |
| AFR-GYM-031 | Stored open for tracking; no approval lifecycle | M | `CheckConstraint gym_budget_status_open` | `status` exists so tracking reads it; only `open` is storable |
| AFR-GYM-032 | Report: club, student in charge, event name, date/time, description, file | Sv | `reports.submit` | |
| AFR-GYM-033 | Report file required | Sv + M | `drive.parse`, `gym_report_file_present` | |
| AFR-GYM-034 | Assigned councillor reads their club's reports | Se | `scoping.reports_for` | |

No live id is left as a gap.

---

## 3.2 (b) Domain model

All tables in `fusion_integrated`. Every person is a plain integer `user_id` (IAM id). No cross-module
foreign key. All indexes and constraints are named.

| Model (file) | Fields | Database-enforced invariants |
|---|---|---|
| `Club` (`models/clubs.py`) | `name`, `category`, `description`, `status` (`open`/`confirmed`), `faculty_councillor_user_id`, `created_by_user_id`, `approved_by_user_id` null, `approved_at` null, timestamps | `gym_club_name_unique_ci` — `UniqueConstraint(Lower("name"))`; `gym_club_category_valid`; `gym_club_status_valid`; `gym_club_confirmed_has_approver` (confirmed ⇔ approver and time set). Indexes: `gym_club_status_name_idx (status, name)`, `gym_club_councillor_idx (faculty_councillor_user_id)` |
| `LeadershipAssignment` (`models/clubs.py`) | `club` FK, `user_id`, `role` (`coordinator`/`co_coordinator`), `valid_from`, `valid_to` null, `assigned_by_user_id` | `gym_leader_one_current_per_role` — unique `(club, role)` where `valid_to IS NULL`; `gym_leader_distinct_people` — unique `(club, user_id)` where `valid_to IS NULL` (R10: coordinator ≠ co-coordinator); `gym_leader_role_valid`; `gym_leader_valid_range` (`valid_to IS NULL OR valid_to >= valid_from`). Index: `gym_leader_current_user_idx (user_id)` where `valid_to IS NULL` — serves "clubs I lead" on every Club Head request |
| `Membership` (`models/memberships.py`) | `club` FK, `user_id`, `description`, `status` (`open`/`confirmed`), `remarks`, `approved_by_user_id` null, `approved_at` null, timestamps | `gym_membership_one_per_club` — unique `(club, user_id)`; `gym_membership_status_valid`. Indexes: `gym_membership_club_status_idx (club, status, created_at)`, `gym_membership_user_idx (user_id, created_at)` |
| `VenueList` + `Venue` (`models/venues.py`) | `VenueList`: `effective_from`, `created_by_label`, `created_at`. `Venue`: `venue_list` FK, `name` | `gym_venue_unique_in_list` — unique `(venue_list, Lower(name))`; `gym_venuelist_effective_unique` — unique `effective_from`. Never edited: a change is a new list with a later `effective_from` (§2.8) |
| `VenueDay` (`models/bookings.py`) | `venue_name`, `date` | `gym_venueday_unique` — unique `(venue_name, date)`. Exists only to be locked: every booking takes `select_for_update` on its venue-day row, so two overlapping requests serialize and the second sees the first |
| `Booking` (`models/bookings.py`) | `club` FK, `kind` (`session`/`event`), `venue_name`, `date`, `start_time`, `end_time`, `description`, `poster_link`, `poster_file_id`, `event_name`, `faculty_user_id` null, `created_by_user_id`, timestamps | `gym_booking_start_before_end`; `gym_booking_kind_valid`; `gym_booking_event_complete` (event ⇒ `event_name`, `poster_link`, `faculty_user_id` present). Indexes: `gym_booking_venue_date_idx (venue_name, date, start_time)` — the overlap query; `gym_booking_club_date_idx (club, date)` — the schedule list |
| `Poll`, `PollChoice`, `PollTarget`, `Vote` (`models/polls.py`) | `Poll`: `club` FK, `title`, `description`, `expires_on` (date), `created_by_user_id`. `PollChoice`: `poll` FK, `label`, `position`. `PollTarget`: `poll` FK, `batch_year`, `discipline` (`""` = all branches). `Vote`: `poll` FK, `choice` FK, `user_id`, `cast_at` | `gym_choice_position_unique (poll, position)`; `gym_target_unique (poll, batch_year, discipline)`; `gym_vote_one_per_student (poll, user_id)`. Indexes: `gym_poll_club_expiry_idx (club, expires_on)`, `gym_poll_expiry_idx (expires_on)`, `gym_target_cohort_idx (batch_year, discipline)` — "polls targeting me", `gym_vote_choice_idx (choice)` — tally |
| `BudgetRequest` (`models/budget.py`) | `club` FK, `purpose`, `description`, `amount` Decimal(12,2), `document_link`, `document_file_id`, `status` (`open`), `submitted_by_user_id`, timestamps | `gym_budget_amount_non_negative`; `gym_budget_document_present` (`document_file_id <> ''`); `gym_budget_status_open`. Index: `gym_budget_club_created_idx (club, created_at)` |
| `EventReport` (`models/reports.py`) | `club` FK, `student_incharge_user_id`, `event_name`, `event_at`, `description`, `report_link`, `report_file_id`, `submitted_by_user_id`, timestamps | `gym_report_file_present`. Index: `gym_report_club_created_idx (club, created_at)` |
| `AuditEvent` (`models/audit.py`) | `action`, `object_type`, `object_id`, `actor_user_id`, `club_id`, `details` (JSON of ids and codes only), `at` | Index: `gym_audit_object_idx (object_type, object_id, at)` |
| `NotificationOutbox` (`models/notifications.py`) | Same shape as Placement's (`topic`, `dedupe_key` unique, recipient, subject, body, payload, status, attempts, `claimed_at`…), table `gymkhana_notification_outbox` | `dedupe_key` unique. Indexes: `gym_outbox_pending_idx (status, created_at)`, `gym_outbox_recipient_idx (recipient_user_id, created_at)` |

Design notes:

- **Why not a Postgres exclusion constraint for BR-GYM-006.** It would need `btree_gist` for equality
  on `venue_name`, which needs `CREATE EXTENSION` — a superuser act the least-privilege roles of
  ADR-0012 do not have. The venue-day lock row gives the same guarantee for this module's only write
  path, and a threaded concurrency test proves it (Step 5.7).
- **The outbox is a copy, not shared.** Placement owns its own. Two consumers fail the `core/`
  admission test (three needed), so this module keeps its own until a third appears.
- **Poll tally is counted**, so a concurrent vote cannot lose an increment.
- **Drive links**: `*_link` keeps the canonical URL `drive.parse` rebuilds, and `*_file_id` keeps its
  id. The submitted string is never stored.
- **Times**: `Booking.date/start_time/end_time` are local IST wall-clock values, which is what a
  venue's day means. `EventReport.event_at` is an aware datetime.

---

## 3.3 (c) State machines

`domain/state_machine.py` — pure Python, a tuple of `Transition(frm, to, event, actors)`, resolved
through one `resolve(frm, event, actor)` that raises `InvalidTransition` or `ActorNotAllowed`.
`NONE` is the "no record yet" source.

| Machine | From | Event | Actor | To | Rules |
|---|---|---|---|---|---|
| Club (BW-GYM-03) | `NONE` | `create` | `student_admin` | `open` | BR-GYM-001…004 |
| Club | `open` | `approve` | `student_admin` | `confirmed` | BR-GYM-004 |
| Membership (BW-GYM-01) | `NONE` | `apply` | `student` | `open` | BR-GYM-007…009 |
| Membership | `open` | `approve` | `club_head` | `confirmed` | BR-GYM-010, 011 |

No other edge exists. That makes a reject, a cancel or a second approval impossible to express:
`confirmed` has no outgoing edge, so approving it again raises `InvalidTransition` → 409 `already_confirmed`.

Polls (BW-GYM-02) have no stored state. "Open" is `poll_is_active(expires_on, now)`, and "student
has voted" is the existence of the `Vote` row, guarded by `gym_vote_one_per_student`.

---

## 3.4 (d) Permissions — exact `registry.py` content

```python
MODULE = {
    "code": "gymkhana", "label": "Gymkhana", "icon": "UsersThree",
    "base_path": "/gymkhana", "nav_section": "Gymkhana", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "gymkhana.clubs", "label": "Clubs", "icon": "UsersThree",
     "to": "/gymkhana/clubs",
     "required_permission": "gymkhana.membership.create", "sort_order": 10},
    {"code": "gymkhana.polls", "label": "Polls", "icon": "ListChecks",
     "to": "/gymkhana/polls",
     "required_permission": "gymkhana.vote.create", "sort_order": 20},
    {"code": "gymkhana.schedule", "label": "Club Schedule", "icon": "CalendarBlank",
     "to": "/gymkhana/schedule",
     "required_permission": "gymkhana.booking.view", "sort_order": 30},
    {"code": "gymkhana.my_clubs", "label": "My Clubs", "icon": "Flag",
     "to": "/gymkhana/my-clubs",
     "required_permission": "gymkhana.leadership.assign", "sort_order": 40},
    {"code": "gymkhana.administration", "label": "Club Administration",
     "icon": "ShieldCheck", "to": "/gymkhana/administration",
     "required_permission": "gymkhana.club.approve", "sort_order": 60},
    {"code": "gymkhana.reports", "label": "Club Reports", "icon": "FileText",
     "to": "/gymkhana/reports",
     "required_permission": "gymkhana.event_report.review", "sort_order": 70},
]

PERMISSIONS = [
    ("gymkhana.club.view", "See clubs"),
    ("gymkhana.club.create", "Create a club"),
    ("gymkhana.club.approve", "Confirm an open club"),
    ("gymkhana.leadership.assign", "Change a club's coordinator and co-coordinator"),
    ("gymkhana.membership.view", "See membership applications"),
    ("gymkhana.membership.create", "Apply to join a club"),
    ("gymkhana.membership.approve", "Approve membership applications"),
    ("gymkhana.booking.view", "See club sessions and events"),
    ("gymkhana.booking.create", "Book a club session or event"),
    ("gymkhana.poll.view", "See polls"),
    ("gymkhana.poll.create", "Create a voting poll"),
    ("gymkhana.vote.create", "Vote in a poll"),
    ("gymkhana.budget_request.view", "See club budget requests"),
    ("gymkhana.budget_request.create", "Submit a club budget request"),
    ("gymkhana.event_report.view", "See the club's own event reports"),
    ("gymkhana.event_report.create", "Submit a club event report"),
    ("gymkhana.event_report.review", "Review event reports of an assigned club"),
]

SYSTEM_PERMISSIONS = []          # the notification drain authorises nothing
SCOPE_PERMISSIONS = []           # every scope here comes from club data, not a code

_STUDENT = [
    "gymkhana.club.view",
    "gymkhana.membership.view", "gymkhana.membership.create",
    "gymkhana.poll.view", "gymkhana.vote.create",
    "gymkhana.booking.view",
    # Club Head (R3): held by every student, effective only for clubs they lead (BR-GYM-010).
    "gymkhana.leadership.assign", "gymkhana.membership.approve",
    "gymkhana.booking.create", "gymkhana.poll.create",
    "gymkhana.budget_request.view", "gymkhana.budget_request.create",
    "gymkhana.event_report.view", "gymkhana.event_report.create",
]

_STUDENT_ADMIN = ["gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve"]

_FACULTY = ["gymkhana.event_report.review"]

ROLE_GRANTS = {
    "student": _STUDENT,                 # basic role (UC-GYM-002…010)
    "Student Admin": _STUDENT_ADMIN,     # R4; UC-GYM-001, UC-GYM-011
    "faculty": _FACULTY,                 # basic role, R5; UC-GYM-012
}

def readiness() -> list[str]: ...        # 3.7 / Step 7.5
```

Role list and citations:

- `student` — Student (UC-GYM-004, UC-GYM-007, BR-GYM-007…009, BR-GYM-013…015). It also carries
  Club Head (BR-GYM-010; UC-GYM-002, 003, 005, 006, 008, 009, 010) per R3.
- `Student Admin` — UC-GYM-001, UC-GYM-011, BR-GYM-004, BW-GYM-03. This is a new designation; its
  spelling is ours because the ERP has no such row yet (R4).
- `faculty` — Club Faculty Councillor (UC-GYM-012, BR-GYM-021), R5.

The verbs are all from the closed list, and there is no `manage`. Every code is checked by a service
or a view, which is what `permission_manifest --check` requires. Holding a permission decides the
verb; which club it applies to is decided in `selectors/scoping.py`.

**Visibility consequences, stated so they are decided, not discovered:**
- Every student sees "Clubs", "Polls", "Club Schedule" and "My Clubs".
- Every faculty member sees Gymkhana with one item, "Club Reports". It shows an empty state unless
  they are a councillor.
- Student Admin sees "Club Administration" only.

**Testing provisioning:** I'll create the `Student Admin` designation with `assign_role --user
<staff dump account> --designation "Student Admin"`. No other designation is needed: Club Heads and
councillors are ordinary students and faculty assigned through the module's own data.

**Platform behaviour this design relies on, to verify in Phase 5:**
- IAM `/me` sends the **union** of permissions across a person's roles (`iam/services.py::build_session`).
  Only navigation is split per role.
- A student's acting role is typically `ug_student`, while the grant is on `student`.

The role-switch test (Step 5.1) pins what this module controls: it reads `principal.permissions`
only and derives club authority from module data, never from role names. If a dump student does not
see Gymkhana while acting as `ug_student`, that is the same behaviour Placement has today, not
something this module should work around. I'll report it if I see it.

---

## 3.5 (e) Endpoints

Every view: `permission_classes = [HasModuleGrant("gymkhana"), HasPermission(<code>)]`, cookie/token
auth from `REST_FRAMEWORK` defaults (unchanged), `@extend_schema` with request and response examples.
Writes carry `throttle_scope = "gymkhana_write"` (60/hour), except votes (`"gymkhana_vote"`, 30/hour)
and the people picker (`"directory_search"`, already 120/hour). Lists use `core.api.pagination.CursorPagination`.
Unparseable query parameters are 400s.

Status codes: 401 no session; 403 permission missing; 404 out of scope; 409 state conflict; 400/422
invalid input; 429 throttled.

| Method | Path | Permission | Returns | Rules |
|---|---|---|---|---|
| GET | `clubs?status=&category=` | `club.view` | Clubs in scope: Student Admin all; others confirmed only | BR-GYM-004, 007 |
| POST | `clubs/create` | `club.create` | 201 club (open) | UC-GYM-001, BR-GYM-001…004, AFR-GYM-001…005 |
| POST | `clubs/{id}/approve` | `club.approve` | 200 club (confirmed) | UC-GYM-011, BR-GYM-004, AFR-GYM-006 |
| GET | `me/clubs` | `club.view` | `{leading: [...], member_of: [...]}` — drives "My Clubs" and the empty state | BR-GYM-010 |
| POST | `clubs/{id}/leadership` | `leadership.assign` | 200 the new current leaders | UC-GYM-008, BR-GYM-001, 010, 016, AFR-GYM-007…009 |
| GET | `memberships?club=&status=` | `membership.view` | Own applications ∪ applications to clubs I lead | AFR-GYM-020 |
| POST | `memberships/apply` | `membership.create` | 201 application (open) | UC-GYM-004, BR-GYM-007…009, AFR-GYM-016…019 |
| POST | `memberships/approve` | `membership.approve` | 200 `[{id, outcome, code, message}]`, each independent | UC-GYM-005, BR-GYM-010, 011, AFR-GYM-021, 022 |
| GET | `venues` | `booking.create` | Current venue names | BR-GYM-020 |
| GET | `bookings?club=&from=&to=` | `booking.view` | Bookings of clubs I lead or am a confirmed member of (R8) | — |
| POST | `sessions` | `booking.create` | 201 booking | UC-GYM-002, BR-GYM-005, 006, 010, 020, AFR-GYM-010…013 |
| POST | `events` | `booking.create` | 201 booking | UC-GYM-003, BR-GYM-002, 005, 006, 010, 020, AFR-GYM-014, 015 |
| GET | `polls` | `poll.view` | Active polls I am targeted by, with my own vote's choice id | UC-GYM-007, BR-GYM-013, 014, AFR-GYM-026 |
| GET | `polls/managed?club=` | `poll.create` | Polls of clubs I lead, with per-choice counts (R8) | AFR-GYM-028 |
| POST | `polls/create` | `poll.create` | 201 poll | UC-GYM-006, BR-GYM-010, 012, 013, AFR-GYM-023…025 |
| POST | `polls/{id}/votes` | `vote.create` | 201 `{choice_id}` | UC-GYM-007, BR-GYM-013…015, AFR-GYM-027, 028 |
| GET | `budget-requests?club=` | `budget_request.view` | Requests of clubs I lead | AFR-GYM-031 |
| POST | `budget-requests/create` | `budget_request.create` | 201 request (open) | UC-GYM-009, BR-GYM-010, 017, 018, AFR-GYM-029…031 |
| GET | `event-reports?club=` | `event_report.view` or `event_report.review` | Reports of clubs I lead ∪ clubs I am councillor of | UC-GYM-012, BR-GYM-021, AFR-GYM-034 |
| GET | `event-reports/{id}` | `event_report.view` or `event_report.review` | One report with its Drive link | UC-GYM-012, BR-GYM-021 |
| POST | `event-reports/create` | `event_report.create` | 201 report | UC-GYM-010, BR-GYM-010, 019, AFR-GYM-032, 033 |
| GET | `people?q=&kind=student\|faculty` | `club.create` or `leadership.assign` or `event_report.create` | Up to 25 `{user_id, username, display_name, kind}` | Picker; the service further requires Student Admin or a current leader of a confirmed club, so a plain student gets 403 |

The bookings list is narrower than the "Club Schedule" page's permission. A student who is neither
leader nor member gets an empty list, and the page explains why.

### Client routes and their guards (Step 6.4)

Every route is single-role, so every route is closed with `RequirePermission` using exactly its nav
item's permission. Detail views are drawers or modals on the list page, never routes.

| Route | Guard | Controls on it |
|---|---|---|
| `clubs` | `gymkhana.membership.create` | Apply modal (UC-GYM-004); "my applications" status |
| `polls` | `gymkhana.vote.create` | Vote control per poll (UC-GYM-007); own choice shown after voting |
| `schedule` | `gymkhana.booking.view` | Book-session and book-event modals, shown only for clubs in `me/clubs.leading` |
| `my-clubs` | `gymkhana.leadership.assign` | Per led club: pending-applications drawer (UC-GYM-005), change-leadership modal (UC-GYM-008), poll modal and results drawer (UC-GYM-006), budget modal and list (UC-GYM-009), report modal and list (UC-GYM-010). Empty state when leading none |
| `administration` | `gymkhana.club.approve` | Create-club modal (UC-GYM-001, gated `can("gymkhana.club.create")`), approve button on open clubs (UC-GYM-011) |
| `reports` | `gymkhana.event_report.review` | Report list and detail drawer (UC-GYM-012) |

`client/src/app/registry.ts` gets the entry `gymkhana: { code: "gymkhana", basePath: "/gymkhana",
load: () => import("../modules/gymkhana/routes") }`.

### `Fusion-client` sidebar entry (to hand over; cannot be added in `module-only`)

```js
{ id: "gymkhana", label: "Gymkhana", icon: "UsersThree", to: "/gymkhana", section: "Gymkhana" }
```

`id` equals `MODULE["code"]`; `icon` is Phosphor; `to` equals `base_path`; `section` equals
`nav_section`. If `INTEGRATED_MODULES` groups modules under an existing section name, the maintainer
should use that name. I cannot read that file here (open question H8).

---

## 3.6 (f) Contracts

**Exposed by `modules/gymkhana/contracts.py`** (read only, plural):

```python
@dataclass(frozen=True)
class ClubAffiliationDTO:
    user_id: int
    leads: tuple[str, ...]        # club names, current leadership
    member_of: tuple[str, ...]    # club names, confirmed memberships

def get_club_affiliations(user_ids: Sequence[int]) -> dict[int, ClubAffiliationDTO]: ...
```

It has no consumer yet. It is offered for a student-profile or awards module; if you'd rather ship no
public surface until a consumer asks, I'll leave `contracts.py` with no functions (open question H6).

**Needed from other modules:**

| Need | Call | Status |
|---|---|---|
| Valid student / faculty, active (BR-GYM-001, 002); voter's batch and branch (BR-GYM-013) | `directory.get_users(ids)` | exists |
| People picker | `directory.search(q, kind, limit)` | exists |
| Poll audience for notification (AFR-GYM-025) | `directory.students_in_cohorts(batch_years: Sequence[int], disciplines: Sequence[str]) -> list[int]` | **new, approved (R9)**. Pages `IamClient.academic_directory` (an existing IAM `main` endpoint, already in `FakeIam`) for each batch × discipline pair; empty `disciplines` = all branches. Raises `IamUnavailable` rather than returning a silently partial audience |

No new `IamClient` method and no new IAM endpoint are needed. The module never touches `fusionlab`.

In `module-only`, `batch_year` or `discipline` can be empty for fixture students. Such a student
matches no target group, so they are not notified and cannot vote. That is the correct closed
reading, and it is tested deliberately.

---

## 3.7 (g) Scheduled work

| Beat entry | Task | Cadence | Queue | If it does not run |
|---|---|---|---|---|
| `gymkhana.deliver-notifications` | `gymkhana.deliver_notifications` | 60 s, `expires: 55` | `notifications` | No session, event or poll notification is ever sent (AFR-GYM-013, 015, 025). The rows pile up in `gymkhana_notification_outbox` as `pending`. |

Nothing else needs a clock: poll expiry is evaluated when the poll is read or voted on.

The task is safe to run twice: rows are claimed by a conditional `UPDATE`, as in Placement, and
broadcast expansion is idempotent through per-recipient dedupe keys.

Management commands:
- `seed_gymkhana_venues --venue NAME [--venue NAME …] [--effective-from DATE]` writes a new venue
  list version.
- `gymkhana_readiness` prints `registry.readiness()` and exits non-zero when anything is unmet.
- `gymkhana_deliver_notifications [--limit N]` is a manual run of the task.

`readiness()` reports exactly one prerequisite: *"No Gymkhana venue list is in effect. Run `manage.py
seed_gymkhana_venues --venue "<name>" …` with the institute's venues; until then no session or event
can be booked."* An empty venue list never 500s: booking answers 409 `no_venues_configured` with the
same sentence.

Deployment order: `migrate` → `seed_gymkhana_venues` → `seed_modules` → `make permissions` +
`seed_iam_permissions` → `gymkhana_readiness`.

---

## 3.8 (h) Open questions

None blocks the build. Every default below was accepted as proposed on 2026-11-22.

| # | Question | Proposed default |
|---|---|---|
| H1 | Which real institute post holds `Student Admin` (R4)? For the academic office. | Built and tested against a locally created `Student Admin` designation |
| H2 | May a Club Head approve **their own** membership application to a club they lead? (Step 5.11 asks this of every approver.) | Refuse with 409 `self_approval`; the other leader can approve it |
| H3 | Must a poll's choices be distinct? Two identical labels are arguably not "two choices" (BR-GYM-012). | Distinct after trimming and ignoring case, max 10 choices, max 20 target groups |
| H4 | May a session or event be booked for a date already past? Not addressed by the spec. | Refuse dates before today (IST) with 409 `booking_in_past`, and bookings more than 365 days ahead |
| H5 | May an event report's `event_at` lie in the future? UC-GYM-010's precondition is "the relevant event has occurred". | Refuse a future `event_at` with 409 `event_not_yet_held` |
| H6 | Ship `get_club_affiliations` in `contracts.py` with no consumer, or ship an empty contract? | Ship it (small, tested) |
| H7 | Bookings cannot be cancelled in the baseline, so a mistaken booking holds its venue for good. Accept as a known limitation? | Yes. Record it as a known gap for the next spec revision; build no cancel |
| H8 | The `Fusion-client` `section` name for the sidebar entry (3.5). | `"Gymkhana"`, the maintainer may regroup |
| H9 | Text lengths. | name 120, title 200, purpose 200, event name 200, description 4000, remarks 1000, choice 200 |

## Approvals record

Written approval from Student 2, the pair's approver, on 2026-11-22:

> "I approve the Gymkhana blueprint (docs/18-gymkhana/gymkhana-blueprint.md) including R1–R10, R9 (directory contracts change) and H1–H9 defaults. — Saroj Aman, 22 Nov 2026" (written, WhatsApp, 2026-11-22)

| Item | Approver | Record |
|---|---|---|
| Phase 1 rulings R1–R10 | Student 2 | the quote above, 2026-11-22 |
| R9: change to `modules/directory/contracts.py` and its tests | Student 2 | the quote above, 2026-11-22 |
| H1–H9 defaults, all accepted as proposed | Student 2 | the quote above, 2026-11-22 |
| This blueprint | Student 2 | the quote above, 2026-11-22 |
| Pre-approved shared lines (Step 4.0): `config/settings/base.py` (`DOMAIN_MODULES`, throttle rates `gymkhana_write`, `gymkhana_vote`), `config/urls.py`, `config/celery.py`, `client/src/app/registry.ts`, `.importlinter`, `client/e2e/accounts.ts` entries, `ops/docs/gymkhana_reference.py`, regenerated schema/manifest/catalogue | prompt | pre-approved |
