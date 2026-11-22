# Gymkhana Module Architecture Blueprint

**Module Name**: Gymkhana  
**Module Code**: `gymkhana`  
**Docs Identifier**: `18-gymkhana`  
**Environment**: `module-only`  
**Spec Prefix**: `GYM-`  
**Status**: APPROVED BY STUDENT 2

---

## 1. Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|:---|:---|:---|:---|:---|
| **CFR-GYM-001** | Student Admin establishment of clubs (validation, open status, confirmation) | Service / Domain | `services/clubs.py::create_club` & `confirm_club` | Traces to AFR-001..006 |
| **CFR-GYM-002** | Club Head leadership succession | Service / Domain | `services/leadership.py::change_leadership` | Traces to AFR-007..009 |
| **CFR-GYM-003** | Session and event booking with venue exclusivity and faculty context | Service / Domain | `services/bookings.py::book_session`, `book_event` | Traces to AFR-010..015 |
| **CFR-GYM-004** | Membership application, open status, Club Head approval | Service / Domain | `services/memberships.py::apply`, `approve` | Traces to AFR-016..022 |
| **CFR-GYM-005** | Targeted club polling, branch/batch filtering, one-vote limit | Service / Domain | `services/polls.py::create_poll`, `cast_vote` | Traces to AFR-023..028 |
| **CFR-GYM-006** | Club budget request submission (non-negative amount, supporting file) | Service / Domain | `services/budgets.py::submit_budget_request` | Traces to AFR-029..031 |
| **CFR-GYM-007** | Event report submission and assigned Club Faculty Councillor review | Service / Domain / Selector | `services/reports.py` & `selectors/reports.py` | Traces to AFR-032..034 |
| **BR-GYM-001** | Coordinator & co-coordinator must be valid students | Service / Contract | `services/clubs.py`, `services/leadership.py` via `directory.contracts` | Validated before save |
| **BR-GYM-002** | Club Faculty Councillor must be valid faculty | Service / Contract | `services/clubs.py`, `services/bookings.py` via `directory.contracts` | Validated before save |
| **BR-GYM-003** | Category limited to Technical, Sports, or Cultural | Model / Domain | `models/club.py` `ClubCategory` choices + CheckConstraint | Strict enum |
| **BR-GYM-004** | Club starts in Open status; Student Admin confirms | Model / Domain | `models/club.py` `ClubStatus` + `domain/state_machine.py` | Open -> Confirmed |
| **BR-GYM-005** | Booking start_time < end_time | Model / Domain | `models/booking.py` CheckConstraint (`start_time < end_time`) | DB-level invariant |
| **BR-GYM-006** | Cross-type venue exclusivity (no session/event overlap on venue + date) | Service / Domain | `services/bookings.py` + DB exclusion/atomic transaction check | Checks both sessions and events |
| **BR-GYM-007** | Membership requires confirmed club | Service / Domain | `services/memberships.py::apply_membership` | Refuses if club not confirmed |
| **BR-GYM-008** | Multiple different-club applications allowed | Model / Domain | Separate rows permitted for distinct `club_id` | Enforced by uniqueness scope |
| **BR-GYM-009** | No duplicate same-club application per student | Model / DB | `UniqueConstraint(fields=['club', 'student_id'])` | Prevent double apply |
| **BR-GYM-010** | Club Head authorization (only current coordinator / co-coordinator) | API / Selector / Domain | `api/permissions.py::IsClubHead` / scoping check | Refuses unauthorized users |
| **BR-GYM-011** | Membership approval transition (open -> confirmed) | Model / Domain | `models/membership.py` + `domain/state_machine.py` | Open -> Confirmed |
| **BR-GYM-012** | Minimum poll choices >= 2 | Model / Service | `services/polls.py::create_poll` | Validates choices len >= 2 |
| **BR-GYM-013** | Poll targeting by batch and branch | Model / Domain | `models/poll.py` `target_batches`, `target_branches` | JSONField / array |
| **BR-GYM-014** | Active poll eligibility (student matches target & unexpired) | Selector / Domain | `selectors/polls.py::is_student_eligible_for_poll` | Matches student info and date |
| **BR-GYM-015** | One vote per student per poll | Model / DB | `UniqueConstraint(fields=['poll', 'student_id'])` | Database-level unique constraint |
| **BR-GYM-016** | Leadership succession (superseded assignments no longer current) | Service / Domain | `services/leadership.py` marks prior `is_current=False` | Atomic transition |
| **BR-GYM-017** | Non-negative budget amount (amount >= 0) | Model / DB | `CheckConstraint(check=Q(amount__gte=0))` | DB-level check |
| **BR-GYM-018** | Budget supporting file required | Model / Service | `models/budget.py` `supporting_file` required | Refuses empty upload |
| **BR-GYM-019** | Event report file required | Model / Service | `models/report.py` `report_file` required | Refuses empty upload |
| **BR-GYM-020** | Configured venue required | Domain / Model | `domain/constants.py::CONFIGURED_VENUES` validation | Restricts venue choices |
| **BR-GYM-021** | Faculty report review authorization (only assigned councillor) | API / Selector | `selectors/reports.py` + `api/permissions.py::IsClubFacultyCouncillor` | Scoping returns 404 if not councillor |
| **UC-GYM-001** | Create New Club | API / Service | `POST /api/gymkhana/clubs/` | Student Admin only |
| **UC-GYM-002** | Book Club Session | API / Service | `POST /api/gymkhana/clubs/{id}/sessions/` | Club Head only |
| **UC-GYM-003** | Book Club Event | API / Service | `POST /api/gymkhana/clubs/{id}/events/` | Club Head only |
| **UC-GYM-004** | Apply for Club Membership | API / Service | `POST /api/gymkhana/clubs/{id}/memberships/` | Authenticated Student |
| **UC-GYM-005** | Approve Club Membership | API / Service | `POST /api/gymkhana/memberships/{id}/approve/` | Club Head only |
| **UC-GYM-006** | Create Voting Poll | API / Service | `POST /api/gymkhana/clubs/{id}/polls/` | Club Head only |
| **UC-GYM-007** | Vote in Poll | API / Service | `POST /api/gymkhana/polls/{id}/vote/` | Eligible Student only |
| **UC-GYM-008** | Change Club Leadership | API / Service | `POST /api/gymkhana/clubs/{id}/leadership/` | Club Head only |
| **UC-GYM-009** | Request Club Budget | API / Service | `POST /api/gymkhana/clubs/{id}/budgets/` | Club Head only |
| **UC-GYM-010** | Submit Club Event Report | API / Service | `POST /api/gymkhana/clubs/{id}/reports/` | Club Head only |
| **UC-GYM-011** | Approve / Confirm Club | API / Service | `POST /api/gymkhana/clubs/{id}/confirm/` | Student Admin only |
| **UC-GYM-012** | Review Club Event Report | API / Selector | `GET /api/gymkhana/clubs/{id}/reports/` | Club Faculty Councillor |
| **BW-GYM-01** | Club Membership Enrollment Lifecycle | Domain / Service | `models/membership.py` & `services/memberships.py` | State progression |
| **BW-GYM-02** | Activity Scheduling & Notification | Domain / Service | `services/bookings.py` & outbox notifications | Outbox events |
| **BW-GYM-03** | Club Establishment and Confirmation | Domain / Service | `services/clubs.py` | State progression |

---

## 2. Domain Model & Invariants

All user/student/faculty references are stored as integer `user_id`s, adhering strictly to ADR-0013 (zero cross-module foreign keys).

### Entities

1. **`Club`**
   - `id`: AutoField (Primary Key)
   - `name`: CharField(max_length=150, unique=True)
   - `category`: CharField(max_length=50, choices=['Technical', 'Sports', 'Cultural'])
   - `description`: TextField(blank=True)
   - `faculty_councillor_id`: IntegerField()
   - `status`: CharField(max_length=20, choices=['open', 'confirmed'], default='open')
   - `created_at`: DateTimeField(auto_now_add=True)
   - `updated_at`: DateTimeField(auto_now=True)
   - *Invariants / Constraints*:
     - `CheckConstraint(check=Q(category__in=['Technical', 'Sports', 'Cultural']), name='gymkhana_club_valid_category')`
     - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='gymkhana_club_valid_status')`

2. **`ClubLeadership`**
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='leaderships')
   - `student_id`: IntegerField()
   - `role`: CharField(max_length=30, choices=['coordinator', 'co_coordinator'])
   - `is_current`: BooleanField(default=True)
   - `assigned_at`: DateTimeField(auto_now_add=True)
   - *Invariants / Constraints*:
     - `UniqueConstraint(fields=['club', 'role'], condition=Q(is_current=True), name='gymkhana_unique_current_club_role')`

3. **`ClubBooking`** (covers both Sessions and Events)
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='bookings')
   - `booking_type`: CharField(max_length=20, choices=['session', 'event'])
   - `title`: CharField(max_length=200)
   - `venue`: CharField(max_length=100)
   - `date`: DateField()
   - `start_time`: TimeField()
   - `end_time`: TimeField()
   - `description`: TextField(blank=True)
   - `created_by_id`: IntegerField()
   - `created_at`: DateTimeField(auto_now_add=True)
   - *Invariants / Constraints*:
     - `CheckConstraint(check=Q(start_time__lt=F('end_time')), name='gymkhana_booking_valid_time_range')`
     - `CheckConstraint(check=Q(booking_type__in=['session', 'event']), name='gymkhana_booking_valid_type')`

4. **`ClubMembership`**
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='memberships')
   - `student_id`: IntegerField()
   - `status`: CharField(max_length=20, choices=['open', 'confirmed'], default='open')
   - `remarks`: TextField(blank=True)
   - `applied_at`: DateTimeField(auto_now_add=True)
   - `confirmed_at`: DateTimeField(null=True, blank=True)
   - *Invariants / Constraints*:
     - `UniqueConstraint(fields=['club', 'student_id'], name='gymkhana_unique_student_club_membership')`
     - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='gymkhana_membership_valid_status')`

5. **`VotingPoll`**
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='polls')
   - `title`: CharField(max_length=250)
   - `description`: TextField(blank=True)
   - `target_batches`: JSONField(default=list)  # e.g. ["2022", "2023"]
   - `target_branches`: JSONField(default=list) # e.g. ["CSE", "ECE", "ME"]
   - `expires_at`: DateTimeField()
   - `created_by_id`: IntegerField()
   - `created_at`: DateTimeField(auto_now_add=True)

6. **`PollChoice`**
   - `id`: AutoField
   - `poll`: ForeignKey(VotingPoll, on_delete=CASCADE, related_name='choices')
   - `text`: CharField(max_length=200)
   - `votes_count`: PositiveIntegerField(default=0)

7. **`PollVote`**
   - `id`: AutoField
   - `poll`: ForeignKey(VotingPoll, on_delete=CASCADE, related_name='votes')
   - `choice`: ForeignKey(PollChoice, on_delete=CASCADE, related_name='votes')
   - `student_id`: IntegerField()
   - `voted_at`: DateTimeField(auto_now_add=True)
   - *Invariants / Constraints*:
     - `UniqueConstraint(fields=['poll', 'student_id'], name='gymkhana_unique_student_poll_vote')`

8. **`ClubBudgetRequest`**
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='budget_requests')
   - `amount`: DecimalField(max_digits=12, decimal_places=2)
   - `purpose`: CharField(max_length=250)
   - `description`: TextField()
   - `supporting_file`: FileField(upload_to='gymkhana/budgets/')
   - `status`: CharField(max_length=20, default='open')
   - `submitted_by_id`: IntegerField()
   - `submitted_at`: DateTimeField(auto_now_add=True)
   - *Invariants / Constraints*:
     - `CheckConstraint(check=Q(amount__gte=0), name='gymkhana_budget_non_negative')`

9. **`ClubEventReport`**
   - `id`: AutoField
   - `club`: ForeignKey(Club, on_delete=CASCADE, related_name='event_reports')
   - `title`: CharField(max_length=200)
   - `description`: TextField()
   - `report_file`: FileField(upload_to='gymkhana/reports/')
   - `submitted_by_id`: IntegerField()
   - `submitted_at`: DateTimeField(auto_now_add=True)

---

## 3. Declarative State Machines

### 3.1 Club Confirmation Lifecycle (BW-GYM-03)
```python
CLUB_TRANSITIONS = {
    # (current_state, event, allowed_actor) -> new_state
    ("open", "confirm", "student_admin"): "confirmed",
}
```

### 3.2 Club Membership Enrollment Lifecycle (BW-GYM-01)
```python
MEMBERSHIP_TRANSITIONS = {
    # (current_state, event, allowed_actor) -> new_state
    ("open", "approve", "club_head"): "confirmed",
}
```

---

## 4. Permission Registry Specification (`modules/gymkhana/registry.py`)

```python
MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "app": "gymkhana",
}

PERMISSIONS = [
    {"code": "gymkhana.club.create", "label": "Create new Gymkhana club"},
    {"code": "gymkhana.club.approve", "label": "Approve/confirm Gymkhana club"},
    {"code": "gymkhana.club.view", "label": "View Gymkhana clubs and details"},
    {"code": "gymkhana.leadership.update", "label": "Change club coordinator and co-coordinator"},
    {"code": "gymkhana.session.book", "label": "Book club session"},
    {"code": "gymkhana.event.book", "label": "Book club event"},
    {"code": "gymkhana.membership.apply", "label": "Apply for club membership"},
    {"code": "gymkhana.membership.approve", "label": "Approve club membership application"},
    {"code": "gymkhana.poll.create", "label": "Create voting poll"},
    {"code": "gymkhana.poll.vote", "label": "Vote in club poll"},
    {"code": "gymkhana.budget.request", "label": "Submit club budget request"},
    {"code": "gymkhana.report.submit", "label": "Submit club event report"},
    {"code": "gymkhana.report.review", "label": "Review assigned club event reports"},
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

ROLE_GRANTS = {
    "Dean_s": [
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.club.view",
    ],
    "studentacadadmin": [
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.club.view",
    ],
    "co-ordinator": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "co": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "Convenor": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "Convener": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "ug_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "pg_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "phd_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "Counsellor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Associate Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Assistant Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
}
```

---

## 5. Integration Entries

### 5.1 `Fusion-client` `INTEGRATED_MODULES` Entry
```js
{
  id: "gymkhana",
  label: "Gymkhana",
  icon: "Award",
  to: "/gymkhana",
  section: "Campus Life",
}
```

### 5.2 Client Registry (`client/src/app/registry.ts`)
```ts
import { gymkhanaRoutes } from "../modules/gymkhana/routes";

// Under registered module routes:
...gymkhanaRoutes,
```

---

## 6. Client Pages & Route Hierarchy

All routes live under `/gymkhana/` and are guarded with permissions:

1. `/gymkhana` — **Clubs Directory & Overview** (`gymkhana.club.view`)
2. `/gymkhana/clubs/new` — **Create Club** (`gymkhana.club.create` - Student Admin)
3. `/gymkhana/clubs/:id` — **Club Details, Sessions & Events** (`gymkhana.club.view`)
4. `/gymkhana/clubs/:id/manage` — **Club Leadership & Settings** (`gymkhana.leadership.update`)
5. `/gymkhana/clubs/:id/memberships` — **Membership Applications Review** (`gymkhana.membership.approve`)
6. `/gymkhana/clubs/:id/book` — **Book Session / Event** (`gymkhana.session.book` / `gymkhana.event.book`)
7. `/gymkhana/clubs/:id/budgets` — **Club Budget Requests** (`gymkhana.budget.request`)
8. `/gymkhana/clubs/:id/reports` — **Event Reports & Review** (`gymkhana.report.submit` / `gymkhana.report.review`)
9. `/gymkhana/polls` — **Active & Targeted Polls** (`gymkhana.poll.vote`)
10. `/gymkhana/clubs/:id/polls/new` — **Create Poll** (`gymkhana.poll.create`)

---

## 7. REST API Endpoints

| Method | Path | Request Body | Status Codes | Permissions |
|:---|:---|:---|:---|:---|
| `GET` | `/api/gymkhana/clubs/` | None (filters: status, category) | 200 | `gymkhana.club.view` |
| `POST` | `/api/gymkhana/clubs/` | `{name, category, description, coordinator_id, co_coordinator_id, faculty_councillor_id}` | 201, 400 | `gymkhana.club.create` |
| `GET` | `/api/gymkhana/clubs/{id}/` | None | 200, 404 | `gymkhana.club.view` |
| `POST` | `/api/gymkhana/clubs/{id}/confirm/` | None | 200, 400, 404 | `gymkhana.club.approve` |
| `POST` | `/api/gymkhana/clubs/{id}/leadership/` | `{coordinator_id, co_coordinator_id}` | 200, 400, 403, 404 | `gymkhana.leadership.update` |
| `POST` | `/api/gymkhana/clubs/{id}/sessions/` | `{title, venue, date, start_time, end_time, description}` | 201, 400, 403, 404 | `gymkhana.session.book` |
| `POST` | `/api/gymkhana/clubs/{id}/events/` | `{title, venue, date, start_time, end_time, description}` | 201, 400, 403, 404 | `gymkhana.event.book` |
| `GET` | `/api/gymkhana/clubs/{id}/bookings/` | None (filters: date, venue) | 200, 404 | `gymkhana.club.view` |
| `POST` | `/api/gymkhana/clubs/{id}/memberships/` | None / `{remarks}` | 201, 400, 404 | `gymkhana.membership.apply` |
| `GET` | `/api/gymkhana/clubs/{id}/memberships/` | None (filter: status) | 200, 403, 404 | `gymkhana.membership.approve` |
| `POST` | `/api/gymkhana/memberships/{id}/approve/` | `{remarks}` | 200, 400, 403, 404 | `gymkhana.membership.approve` |
| `POST` | `/api/gymkhana/clubs/{id}/polls/` | `{title, description, target_batches, target_branches, expires_at, choices}` | 201, 400, 403, 404 | `gymkhana.poll.create` |
| `GET` | `/api/gymkhana/polls/` | None (scoped to eligible active polls) | 200 | `gymkhana.poll.vote` |
| `POST` | `/api/gymkhana/polls/{id}/vote/` | `{choice_id}` | 200, 400, 403, 404 | `gymkhana.poll.vote` |
| `POST` | `/api/gymkhana/clubs/{id}/budgets/` | multipart: `{amount, purpose, description, supporting_file}` | 201, 400, 403, 404 | `gymkhana.budget.request` |
| `GET` | `/api/gymkhana/clubs/{id}/budgets/` | None | 200, 403, 404 | `gymkhana.budget.request` |
| `POST` | `/api/gymkhana/clubs/{id}/reports/` | multipart: `{title, description, report_file}` | 201, 400, 403, 404 | `gymkhana.report.submit` |
| `GET` | `/api/gymkhana/clubs/{id}/reports/` | None | 200, 403, 404 | `gymkhana.report.review` |

---

## 8. Known Gaps and Open Decisions

1. **No Online Budget Approval Lifecycle**: As explicitly confirmed by CFR-GYM-006, budget requests are captured and retained in open status for audit and administrative tracking. No approve/reject endpoint is implemented for budget requests.
2. **Membership Lifecycle**: The specification specifies submission (`open`) and approval (`confirmed`). No rejection/cancellation transition exists in the v1.1 synchronized baseline.
3. **Venues**: Venues configured for Gymkhana bookings are stored in `domain/constants.py::CONFIGURED_VENUES` (`L-101`, `L-102`, `CC1`, `CC2`, `Hall-1`, `Sports Ground`, `Auditorium`).
4. **Scoping**: When a non-councillor or non-member accesses private records (e.g. event reports or club membership queues), queries return `404 Not Found` per platform security rules.

---

## 9. Student 2 Approval Record

> **Dated written approval — 2026-11-23:** “Student 2 approves the Gymkhana Architecture Blueprint
> (docs/18-gymkhana/gymkhana-blueprint.md) exactly as written, with no changes.”
>
> **Student 2 ruling — empty poll targets:** reject poll creation.
>
> **Student 2 ruling — event faculty context:** use the assigned club councillor.
