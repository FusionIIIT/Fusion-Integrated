# Gymkhana Module Architectural Blueprint

**Module Name**: Gymkhana (`gymkhana`)  
**Docs Folder**: `docs/09-gymkhana/`  
**Specification Reference**: `specs/gymkhana/` (v1.1 Synchronized)  
**Author (Student 1)**: Utkarsh Bagad (24BCS260)  
**Approver (Student 2)**: Sanjana Rai (24BCS222)  
**Approval Date**: 2026-11-20  
**Status**: APPROVED

---

## Step 3.1 (a) — Traceability Table

| ID | What it requires | Layer | Planned Enforcement Point | Notes |
|:---|:---|:---|:---|:---|
| **BR-GYM-001** | Coordinator & co-coordinator must be valid, distinct students | Domain / Policy | `modules.gymkhana.domain.policy.validate_student_leadership` | Verified on creation & leadership change |
| **BR-GYM-002** | Club Faculty Councillor must reference valid faculty member | Domain / Policy | `modules.gymkhana.domain.policy.validate_faculty_councillor` | Enforced at club creation and event booking |
| **BR-GYM-003** | Category limited strictly to Technical, Sports, or Cultural | Domain / Policy | `modules.gymkhana.domain.policy.validate_club_category` | Enforced at creation & models.CharField choices |
| **BR-GYM-004** | Club confirmation lifecycle: only open clubs can be confirmed | Domain / Policy | `modules.gymkhana.domain.policy.validate_club_confirmation_transition` | Student Admin action |
| **BR-GYM-005** | Booking start time must be strictly earlier than end time | Domain / Policy | `modules.gymkhana.domain.policy.validate_booking_time_range` | Checked for session and event bookings |
| **BR-GYM-006** | Cross-type venue exclusivity; no overlapping bookings | Domain / Services | `modules.gymkhana.domain.policy.check_cross_type_venue_conflict` | Sessions and events cannot overlap |
| **BR-GYM-007** | Membership requires confirmed club | Domain / Policy | `modules.gymkhana.domain.policy.validate_membership_application` | Rejects application if club status is open |
| **BR-GYM-008** | Multi-club applications permitted across different clubs | Domain / Models | `modules.gymkhana.models.ClubMembership.Meta.unique_together` | Scoped per (club, student_id) |
| **BR-GYM-009** | Duplicate same-club application rejected | Domain / Models | `modules.gymkhana.models.ClubMembership.unique_together` | DB constraint + pre-validation |
| **BR-GYM-010** | Club Head authorization: only active coordinator/co-coordinator | Domain / Policy | `modules.gymkhana.domain.policy.validate_club_head_authorization` | Guards management, booking, approvals |
| **BR-GYM-011** | Membership approval transition: open -> confirmed | Domain / Policy | `modules.gymkhana.domain.policy.validate_membership_approval_transition` | Club Head action |
| **BR-GYM-012** | Voting poll requires at least 2 choices | Domain / Policy | `modules.gymkhana.domain.policy.validate_poll_creation` | Rejects single/zero option polls |
| **BR-GYM-013** | Poll targeting specifies student batch and branch | Domain / Policy | `modules.gymkhana.domain.policy.validate_poll_creation` | Target criteria required |
| **BR-GYM-014** | Voting eligibility: active, unexpired, matching audience | Domain / Policy | `modules.gymkhana.domain.policy.validate_vote_eligibility` | Enforced in vote service |
| **BR-GYM-015** | Exactly one vote per student per poll | Domain / Models | `modules.gymkhana.models.PollVote.Meta.unique_together` | DB unique constraint on (poll, student_id) |
| **BR-GYM-016** | Leadership succession: superseded leaders deactivated | Domain / Services | `modules.gymkhana.services.applications.change_club_leadership` | Transactional status deactivation |
| **BR-GYM-017** | Non-negative club budget request (amount >= 0) | Domain / Policy | `modules.gymkhana.domain.policy.validate_budget_amount` | Rejects negative amounts |
| **BR-GYM-018** | Budget request requires supporting document file | Domain / Policy | `modules.gymkhana.domain.policy.validate_budget_amount` | Mandatory attachment check |
| **BR-GYM-019** | Event report requires documentation file | Domain / Policy | `modules.gymkhana.domain.policy.validate_event_report` | Mandatory report file |
| **BR-GYM-020** | Configured venues only for Gymkhana bookings | Domain / Policy | `modules.gymkhana.domain.policy.validate_configured_venue` | Whitelist check against configured venues |
| **BR-GYM-021** | Faculty report review restricted to assigned club councillor | Domain / Policy | `modules.gymkhana.domain.policy.validate_faculty_report_review` | Validates councillor matches club assignment |
| **UC-GYM-001** | Create New Club | Services | `modules.gymkhana.services.applications.create_club` | Open status, initial active leadership |
| **UC-GYM-002** | Book Club Session | Services | `modules.gymkhana.services.applications.book_venue` | Booking type: session |
| **UC-GYM-003** | Book Club Event | Services | `modules.gymkhana.services.applications.book_venue` | Booking type: event |
| **UC-GYM-004** | Apply for Club Membership | Services | `modules.gymkhana.services.applications.apply_club_membership` | Open membership created |
| **UC-GYM-005** | Approve Club Membership | Services | `modules.gymkhana.services.applications.approve_club_membership` | Transition to confirmed |
| **UC-GYM-006** | Create Voting Poll | Services | `modules.gymkhana.services.applications.create_voting_poll` | Poll + options creation |
| **UC-GYM-007** | Cast Poll Vote | Services | `modules.gymkhana.services.applications.cast_poll_vote` | Single vote recorded |
| **UC-GYM-008** | Change Club Leadership | Services | `modules.gymkhana.services.applications.change_club_leadership` | Supersedes prior leadership |
| **UC-GYM-009** | Submit Club Budget Request | Services | `modules.gymkhana.services.applications.submit_budget_request` | Open budget request |
| **UC-GYM-010** | Submit Club Event Report | Services | `modules.gymkhana.services.applications.submit_event_report` | Event documentation |
| **UC-GYM-011** | Confirm Club | Services | `modules.gymkhana.services.applications.confirm_club` | Admin confirmation |
| **UC-GYM-012** | Review Club Event Report | Services | `modules.gymkhana.services.applications.review_event_report` | Faculty councillor access |
| **BW-GYM-01** | Club Membership Enrollment Workflow | Services | Full lifecycle: No App -> Open -> Confirmed | Transactional state progression |
| **BW-GYM-02** | Targeted Polling Workflow | Services | Lifecycle: Draft/Unavail -> Open/Targeted -> Voted | Target matching and single-vote limit |
| **BW-GYM-03** | Club Establishment Workflow | Services | Lifecycle: Proposed -> Open -> Confirmed | Admin approval gate |

---

## Step 3.2 (b) — Domain Model

All user references use positive integer IDs (`IntegerField(db_index=True)`) per ADR-0013 cross-module decoupling. No foreign keys to external user or IAM tables.

### Entities & Constraints
1. **Club**
   * Fields: `id`, `name` (unique CharField 100), `category` (CharField 20), `description` (TextField), `status` (open, confirmed), `created_at`, `updated_at`.
   * Invariant: Name is unique across all categories.
2. **ClubLeadership**
   * Fields: `id`, `club` (FK to Club), `coordinator_id` (int), `co_coordinator_id` (int), `faculty_councillor_id` (int), `is_active` (bool), `assigned_at`.
   * Invariant: `coordinator_id != co_coordinator_id`. At most one active record per club.
3. **ClubMembership**
   * Fields: `id`, `club` (FK to Club), `student_id` (int), `status` (open, confirmed), `applied_at`, `confirmed_at`.
   * Constraint: `unique_together = ("club", "student_id")`.
4. **VenueBooking**
   * Fields: `id`, `club` (FK to Club), `booking_type` (session, event), `venue_name` (CharField 100), `booking_date` (DateField), `start_time` (TimeField), `end_time` (TimeField), `description` (TextField), `poster_url` (CharField), `created_by_id` (int), `created_at`.
   * Invariant: `start_time < end_time`. No overlapping bookings on same venue & date.
5. **VotingPoll & PollOption & PollVote**
   * `VotingPoll`: `id`, `club`, `title`, `description`, `target_batch`, `target_branch`, `is_active`, `expires_at`, `created_by_id`, `created_at`.
   * `PollOption`: `id`, `poll` (FK), `option_text` (CharField 200).
   * `PollVote`: `id`, `poll` (FK), `option` (FK), `student_id` (int), `voted_at`.
   * Constraint: `PollVote.unique_together = ("poll", "student_id")`.
6. **ClubBudgetRequest**
   * Fields: `id`, `club`, `requested_amount` (DecimalField 12,2), `description`, `supporting_file`, `status` (open), `submitted_by_id`, `submitted_at`.
   * Invariant: `requested_amount >= 0.00`. Supporting file required.
7. **ClubEventReport**
   * Fields: `id`, `club`, `event_name`, `event_date`, `report_file`, `submitted_by_id`, `submitted_at`.
   * Invariant: `report_file` required.

---

## Step 3.3 (c) — State Machines

### 1. Club Establishment Lifecycle (BW-GYM-03)
```text
(State: None)      + Event: Submit Club Details (Actor: Admin)  -> State: OPEN
(State: OPEN)      + Event: Confirm Club (Actor: Admin)         -> State: CONFIRMED
(State: CONFIRMED) + Event: Confirm Club                        -> ILLEGAL (Rejected by validate_club_confirmation_transition)
```

### 2. Club Membership Lifecycle (BW-GYM-01)
```text
(State: None)      + Event: Apply (Actor: Student, Club: Confirmed) -> State: OPEN
(State: OPEN)      + Event: Approve (Actor: Coordinator)            -> State: CONFIRMED
(State: CONFIRMED) + Event: Approve                                 -> ILLEGAL (Rejected by validate_membership_approval_transition)
```

---

## Step 3.4 (d) — Permission List (`registry.py`)

```python
MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Campus",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "gymkhana.browse_clubs", "label": "Browse Clubs", "icon": "Users", "to": "/gymkhana", "required_permission": "gymkhana.club.view", "sort_order": 10},
    {"code": "gymkhana.my_memberships", "label": "My Memberships", "icon": "UserCheck", "to": "/gymkhana/memberships", "required_permission": "gymkhana.membership.apply", "sort_order": 20},
    {"code": "gymkhana.voting_polls", "label": "Voting Polls", "icon": "Checks", "to": "/gymkhana/polls", "required_permission": "gymkhana.poll.vote", "sort_order": 30},
    {"code": "gymkhana.manage_club", "label": "Manage Club", "icon": "Gear", "to": "/gymkhana/manage", "required_permission": "gymkhana.club.manage", "sort_order": 40},
    {"code": "gymkhana.venue_bookings", "label": "Venue Bookings", "icon": "CalendarBlank", "to": "/gymkhana/bookings", "required_permission": "gymkhana.booking.manage", "sort_order": 50},
    {"code": "gymkhana.budget_requests", "label": "Budget Requests", "icon": "CurrencyDollar", "to": "/gymkhana/budget", "required_permission": "gymkhana.budget.submit", "sort_order": 60},
    {"code": "gymkhana.event_reports", "label": "Event Reports", "icon": "ClipboardText", "to": "/gymkhana/reports", "required_permission": "gymkhana.report.submit", "sort_order": 70},
    {"code": "gymkhana.club_approvals", "label": "Club Approvals", "icon": "ShieldCheck", "to": "/gymkhana/admin/clubs", "required_permission": "gymkhana.club.admin", "sort_order": 80},
    {"code": "gymkhana.review_reports", "label": "Review Reports", "icon": "FileSearch", "to": "/gymkhana/faculty/reports", "required_permission": "gymkhana.report.review", "sort_order": 90},
]

PERMISSIONS = [
    ("gymkhana.club.view", "See available clubs"),
    ("gymkhana.membership.apply", "Apply for club memberships"),
    ("gymkhana.poll.vote", "Vote in active polls"),
    ("gymkhana.club.manage", "Manage club details and activities"),
    ("gymkhana.booking.manage", "Book venues for events"),
    ("gymkhana.budget.submit", "Submit budget requests"),
    ("gymkhana.report.submit", "Submit event reports"),
    ("gymkhana.club.admin", "Approve club memberships and budgets"),
    ("gymkhana.report.review", "Review submitted event reports"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "student": ["gymkhana.club.view", "gymkhana.membership.apply", "gymkhana.poll.vote"],
    "club_coordinator": [
        "gymkhana.club.view", "gymkhana.membership.apply", "gymkhana.poll.vote",
        "gymkhana.club.manage", "gymkhana.booking.manage", "gymkhana.budget.submit", "gymkhana.report.submit",
    ],
    "student_admin": [
        "gymkhana.club.view", "gymkhana.membership.apply", "gymkhana.poll.vote",
        "gymkhana.club.manage", "gymkhana.booking.manage", "gymkhana.budget.submit", "gymkhana.report.submit",
        "gymkhana.club.admin",
    ],
    "faculty": ["gymkhana.club.view", "gymkhana.report.review"],
}
```

---

## Step 3.5 (e) — Endpoint List

All endpoints sit under `/api/v1/gymkhana/` behind `HasModuleGrant("gymkhana")` and action-specific `HasPermission(...)`:

| Method | Endpoint | Permissions Required | Status Code | Enforced Rules |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/gymkhana/clubs/` | `gymkhana.club.view` | 200 OK | Filter/List clubs |
| `POST` | `/api/v1/gymkhana/clubs/` | `gymkhana.club.admin` | 201 Created / 400 Bad Request | BR-001, BR-002, BR-003, UC-001 |
| `GET` | `/api/v1/gymkhana/clubs/<pk>/` | `gymkhana.club.view` | 200 OK / 404 Not Found | Club details lookup |
| `POST` | `/api/v1/gymkhana/clubs/<pk>/confirm/` | `gymkhana.club.admin` | 200 OK / 400 Bad Request | BR-004, UC-011 |
| `POST` | `/api/v1/gymkhana/clubs/<pk>/leadership/` | `gymkhana.club.manage` | 200 OK / 400 / 403 Forbidden | BR-001, BR-010, BR-016, UC-008 |
| `POST` | `/api/v1/gymkhana/clubs/<club_id>/apply/` | `gymkhana.membership.apply` | 201 Created / 400 Bad Request | BR-007, BR-009, UC-004 |
| `POST` | `/api/v1/gymkhana/memberships/<pk>/approve/` | `gymkhana.club.manage` | 200 OK / 400 / 403 Forbidden | BR-010, BR-011, UC-005 |
| `GET` | `/api/v1/gymkhana/bookings/` | `gymkhana.club.view` | 200 OK | List bookings |
| `POST` | `/api/v1/gymkhana/bookings/` | `gymkhana.booking.manage` | 201 Created / 400 / 403 Forbidden | BR-005, BR-006, BR-020, UC-002, UC-003 |
| `GET` | `/api/v1/gymkhana/polls/` | `gymkhana.poll.vote` | 200 OK | List active polls |
| `POST` | `/api/v1/gymkhana/polls/` | `gymkhana.club.manage` | 201 Created / 400 Bad Request | BR-012, BR-013, UC-006 |
| `POST` | `/api/v1/gymkhana/polls/<poll_id>/vote/` | `gymkhana.poll.vote` | 201 Created / 400 Bad Request | BR-014, BR-015, UC-007 |
| `GET` | `/api/v1/gymkhana/budgets/` | `gymkhana.budget.submit` | 200 OK | List budget requests |
| `POST` | `/api/v1/gymkhana/budgets/` | `gymkhana.budget.submit` | 201 Created / 400 / 403 Forbidden | BR-017, BR-018, UC-009 |
| `GET` | `/api/v1/gymkhana/reports/` | `gymkhana.report.submit` | 200 OK | List event reports |
| `POST` | `/api/v1/gymkhana/reports/` | `gymkhana.report.submit` | 201 Created / 400 / 403 Forbidden | BR-019, UC-010 |
| `GET` | `/api/v1/gymkhana/reports/<pk>/review/` | `gymkhana.report.review` | 200 OK / 403 / 404 | BR-021, UC-012 |

### Frontend Routes & Route Guards (`client/src/modules/gymkhana/routes.tsx`)
* `/gymkhana` — `ClubsDashboard` (open to all authenticated users with `gymkhana.club.view`)
* `/gymkhana/manage` — `ClubManagement` guarded by `<RequirePermission permission="gymkhana.club.manage">`
* `/gymkhana/polls` — `VotingPolls` guarded by `<RequirePermission permission="gymkhana.poll.vote">`

---

## Step 3.6 (f) — Contracts (`modules/gymkhana/contracts.py`)

All getters are strictly plural per platform architecture rule:
* `get_clubs(club_ids: Sequence[int]) -> list[dict[str, Any]]`
* `get_active_leaderships(club_ids: Sequence[int]) -> list[dict[str, Any]]`
* `get_memberships(student_ids: Sequence[int]) -> list[dict[str, Any]]`
* `get_venue_bookings(venue_names: Sequence[str], booking_dates: Sequence[date]) -> list[dict[str, Any]]`

---

## Step 3.7 (g) — Scheduled Work
No periodic celery beat tasks required for Gymkhana core. Poll expirations and venue schedule queries are calculated dynamically against `timezone.now()`.

---

## Step 3.8 (h) — Open Questions & Approvals

1. **Student 2 Approval of Architectural Blueprint**:
   * *Status*: **APPROVED**
   * *Approver*: Sanjana Rai (Student 2 / 24BCS222)
   * *Date*: 2026-11-20
   * *Written Record*: *"Reviewed the Gymkhana architectural blueprint against specs/gymkhana (BR-001 to 021, UC-001 to 012, and BW-01 to 03). ADR-0013 integer user IDs, permission mappings in registry.py, plural contracts, and route guards verified. Blueprint approved for implementation."*
