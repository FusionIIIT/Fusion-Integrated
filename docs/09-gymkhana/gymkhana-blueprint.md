# Gymkhana Module Blueprint

**Module Code:** `gymkhana`  
**Specification Set:** `gymkhana-specs/` (SYNCHRONIZED v1.1)  
**Specification ID Prefixes:** `CFR-GYM-`, `AFR-GYM-`, `UC-GYM-`, `BR-GYM-`, `BW-GYM-`  
**Target Environment:** `module-only`  
**Reference Module:** `modules/placement`  
**Author:** Student 1  
**Approver:** Student 2 (revision 2, at the end of this document, is awaiting written approval)  

---

## Step 3.1 (a) — Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| **CFR-GYM-001** | Student Admin-controlled establishment of clubs, validating student leaders and faculty councillor, open -> confirmed lifecycle | Service + Domain | `services.clubs.create_club`, `services.clubs.approve_club`, `domain.club_state` | Constituent AFRs: 001 to 006 |
| **CFR-GYM-002** | Club Head replaces coordinator / co-coordinator with valid students; maintain only current leadership | Service + Model | `services.clubs.change_leadership`, `models.ClubLeadershipHistory` | Constituent AFRs: 007 to 009 |
| **CFR-GYM-003** | Book sessions & events in configured venues, enforce start < end, cross-type venue exclusivity, faculty context for events, student notifications | Service + Model | `services.bookings.book_session`, `services.bookings.book_event`, `models.VenueBooking` | Constituent AFRs: 010 to 015 |
| **CFR-GYM-004** | Confirmed-club membership enrollment: non-duplicate open applications, Club Head approval with optional remarks to confirmed | Service + Model + Domain | `services.memberships.apply_membership`, `services.memberships.approve_membership`, `models.ClubMembership` | Constituent AFRs: 016 to 022 |
| **CFR-GYM-005** | Targeted club polling: >=2 choices, batch/branch target groups, notifications, one vote per eligible student, tally recording | Service + Model | `services.polls.create_poll`, `services.polls.cast_vote`, `models.Poll`, `models.PollVote` | Constituent AFRs: 023 to 028 |
| **CFR-GYM-006** | Club Head submits non-negative budget request with purpose, description, supporting file; store open for tracking without online approval | Service + Model | `services.budgets.submit_budget_request`, `models.ClubBudgetRequest` | Constituent AFRs: 029 to 031 |
| **CFR-GYM-007** | Club Head submits documented event report; assigned Club Faculty Councillor accesses/reviews without approval state | Service + Selector | `services.reports.submit_event_report`, `selectors.reports.get_reports_for_councillor` | Constituent AFRs: 032 to 034 |
| **AFR-GYM-001** | Record club name, category, coordinator, co-coordinator, faculty councillor, description | Service + Model | `services.clubs.create_club`, `models.Club` | Mapped to UC-GYM-001 |
| **AFR-GYM-002** | Validate coordinator and co-coordinator are valid students | Domain + Service | `domain.validation.validate_student_leaders`, `services.clubs` | Mapped to BR-GYM-001 |
| **AFR-GYM-003** | Validate Club Faculty Councillor is a valid faculty member | Domain + Service | `domain.validation.validate_faculty_councillor`, `services.clubs`, `services.bookings` | Mapped to BR-GYM-002 |
| **AFR-GYM-004** | Restrict club category to Technical, Sports, or Cultural | Domain + Model | `models.Club.Category`, `CheckConstraint` | Mapped to BR-GYM-003 |
| **AFR-GYM-005** | Record newly created club in open state | Model + Service | `models.Club.status`, `services.clubs.create_club` | Mapped to BW-GYM-03 |
| **AFR-GYM-006** | Student Admin approves open club to confirmed status | Domain + Service | `domain.club_state.transition_club`, `services.clubs.approve_club` | Mapped to BR-GYM-004, BW-GYM-03 |
| **AFR-GYM-007** | Club Head replaces club coordinator and co-coordinator | Service + Selector | `services.clubs.change_leadership`, `selectors.scoping.check_club_head` | Mapped to UC-GYM-008 |
| **AFR-GYM-008** | Validate replacement leaders are valid students | Domain + Service | `domain.validation.validate_student_leaders` | Mapped to BR-GYM-001 |
| **AFR-GYM-009** | Maintain only current leadership assignments for club | Model + Service | `models.Club` current fields, `models.ClubLeadershipHistory` | Mapped to BR-GYM-016 |
| **AFR-GYM-010** | Book club session with venue, date, start_time, end_time, description, optional poster | Service + Model | `services.bookings.book_session`, `models.VenueBooking` | Mapped to UC-GYM-002 |
| **AFR-GYM-011** | Reject session/event booking unless start_time < end_time | Domain + Model | `domain.validation.validate_booking_times`, `CheckConstraint` | Mapped to BR-GYM-005 |
| **AFR-GYM-012** | Prevent session/event booking overlapping existing booking in same venue on same date | Service + Selector | `services.bookings._check_venue_conflict`, `selectors.bookings` | Mapped to BR-GYM-006 |
| **AFR-GYM-013** | Notify intended students after session booking | Service + Task | `services.bookings.book_session`, `tasks.notify_booking` | Outbox / Celery task |
| **AFR-GYM-014** | Book club event with venue, date, times, faculty councillor, poster, description | Service + Model | `services.bookings.book_event`, `models.VenueBooking` | Mapped to UC-GYM-003 |
| **AFR-GYM-015** | Notify intended students after event booking | Service + Task | `services.bookings.book_event`, `tasks.notify_booking` | Outbox / Celery task |
| **AFR-GYM-016** | Student applies for membership in confirmed club with description/achievements | Service + Model | `services.memberships.apply_membership`, `models.ClubMembership` | Mapped to UC-GYM-004, BW-GYM-01 |
| **AFR-GYM-017** | Allow student to maintain applications to multiple different clubs | Model | No cross-club restriction on `student_id` | Mapped to BR-GYM-008 |
| **AFR-GYM-018** | Prevent duplicate membership application by same student to same club | Model + Service | `UniqueConstraint(fields=['club', 'student'])` | Mapped to BR-GYM-009 |
| **AFR-GYM-019** | Newly submitted membership application recorded with open status | Model + Service | `models.ClubMembership.status = 'open'` | Mapped to BW-GYM-01 |
| **AFR-GYM-020** | Club Head accesses pending membership applications for applicable club | Selector + Scoping | `selectors.memberships.list_pending_for_club`, `selectors.scoping` | Mapped to UC-GYM-005 |
| **AFR-GYM-021** | Club Head approves open membership with optional remarks | Domain + Service | `domain.membership_state.transition_membership`, `services.memberships.approve_membership` | Mapped to BR-GYM-010, BR-GYM-011 |
| **AFR-GYM-022** | Approved membership changes from open to confirmed | Domain + Model | `domain.membership_state`, `models.ClubMembership` | Mapped to BW-GYM-01 |
| **AFR-GYM-023** | Club Head creates voting poll: title, description, expiration date, choices, batch/branch target groups | Service + Model | `services.polls.create_poll`, `models.Poll`, `models.PollTargetGroup` | Mapped to UC-GYM-006, BW-GYM-02 |
| **AFR-GYM-024** | Require at least two choices for a voting poll | Domain + Service | `domain.validation.validate_poll_choices` | Mapped to BR-GYM-012 |
| **AFR-GYM-025** | Notify target group students upon poll creation | Service + Task | `services.polls.create_poll`, `tasks.notify_poll` | Outbox / Celery task |
| **AFR-GYM-026** | Eligible targeted student accesses active poll and available choices | Selector + Scoping | `selectors.polls.get_active_poll_for_student` | Mapped to UC-GYM-007, BR-GYM-014 |
| **AFR-GYM-027** | Eligible targeted student casts one choice in active poll | Service + Model | `services.polls.cast_vote`, `models.PollVote` | Mapped to UC-GYM-007, BW-GYM-02 |
| **AFR-GYM-028** | Prevent duplicate vote by same student in same poll; update poll tally | Model + Service | `UniqueConstraint(fields=['poll', 'student'])`, atomic F-expression increment | Mapped to BR-GYM-015 |
| **AFR-GYM-029** | Club Head submits budget request: amount, purpose, description, supporting file | Service + Model | `services.budgets.submit_budget_request`, `models.ClubBudgetRequest` | Mapped to UC-GYM-009 |
| **AFR-GYM-030** | Reject budget request if amount is negative or supporting file missing | Domain + Model | `domain.validation.validate_budget_request`, `CheckConstraint(amount >= 0)` | Mapped to BR-GYM-017, BR-GYM-018 |
| **AFR-GYM-031** | Store submitted budget request as open for tracking; no online approval/rejection | Model + Service | `models.ClubBudgetRequest.status = 'open'` | Tracking only |
| **AFR-GYM-032** | Club Head submits event report: club, student incharge, event name, datetime, description, report file | Service + Model | `services.reports.submit_event_report`, `models.ClubEventReport` | Mapped to UC-GYM-010 |
| **AFR-GYM-033** | Require report/details file on event report submission | Domain + Model | `domain.validation.validate_report_file` | Mapped to BR-GYM-019 |
| **AFR-GYM-034** | Assigned Club Faculty Councillor accesses/reviews submitted reports for that club | Selector + Scoping | `selectors.reports.get_reports_for_councillor` | Mapped to UC-GYM-012, BR-GYM-021 |
| **BR-GYM-001** | Coordinator, co-coordinator, and replacement leaders must be valid students | Domain + Service | `domain.validation.validate_student_leaders` | Verified via Directory contracts |
| **BR-GYM-002** | Selected Club Faculty Councillor must be a valid faculty member | Domain + Service | `domain.validation.validate_faculty_councillor` | Verified via Directory contracts |
| **BR-GYM-003** | Allowed categories: Technical, Sports, Cultural | Domain + Model | `models.Club.Category`, `CheckConstraint` | Validation in domain and DB |
| **BR-GYM-004** | Club creation sets status open; only Student Admin can confirm; confirmed clubs activate club operations | Domain + Service | `domain.club_state.transition_club` | BW-GYM-03 |
| **BR-GYM-005** | Booking start time must strictly precede end time | Domain + Model | `domain.validation.validate_booking_times`, `CheckConstraint` | Enforced at DB + domain |
| **BR-GYM-006** | Cross-type venue exclusivity: no session or event booking may overlap existing session or event in same venue on same date | Service + Model | Unified `models.VenueBooking` query + select_for_update in `services.bookings` | Cross-type exclusivity |
| **BR-GYM-007** | Membership applications allowed only for confirmed clubs | Domain + Service | `domain.validation.validate_club_confirmed` | Rejects open/unconfirmed clubs |
| **BR-GYM-008** | Multiple different-club applications allowed for a student | Model | No multi-club block | Natural system capability |
| **BR-GYM-009** | No duplicate application to same club by same student | Model + Service | `UniqueConstraint(fields=['club', 'student'])` | Database partial or unique constraint |
| **BR-GYM-010** | Club Head authorization: caller must be current coordinator or co-coordinator of the specified club | Selector + Choke-point | `selectors.scoping.check_club_head` | Core choke-point for club actions |
| **BR-GYM-011** | Membership approval changes status from open to confirmed; optional remarks | Domain + Service | `domain.membership_state.transition_membership` | BW-GYM-01 |
| **BR-GYM-012** | Minimum two distinct choices for a voting poll | Domain + Service | `domain.validation.validate_poll_choices` | Enforced in domain validation |
| **BR-GYM-013** | Poll targeting: target groups defined by batch and branch; notifications sent to matching students | Domain + Service | `domain.validation.validate_target_groups`, `services.polls` | Evaluated against student directory |
| **BR-GYM-014** | Active poll eligibility: poll must be active (now <= expires_at) and student must belong to targeted batch/branch | Selector + Service | `selectors.polls.is_student_eligible` | Scoping filter |
| **BR-GYM-015** | One vote per student per poll; increments tally atomically | Model + Service | `UniqueConstraint(fields=['poll', 'student'])`, `F('vote_count') + 1` | Database concurrency protected |
| **BR-GYM-016** | Leadership change immediately replaces active coordinator/co-coordinator and logs previous leadership | Service + Model | `services.clubs.change_leadership`, `models.ClubLeadershipHistory` | Clean leadership succession |
| **BR-GYM-017** | Club budget request amount must be non-negative (amount >= 0) | Domain + Model | `CheckConstraint(check=Q(amount__gte=0))` | Model DB check constraint |
| **BR-GYM-018** | Budget supporting documentation file is mandatory | Domain + Model | `domain.validation.validate_supporting_file` | Mandatory file attachment |
| **BR-GYM-019** | Event report file is mandatory | Domain + Model | `domain.validation.validate_report_file` | Mandatory file attachment |
| **BR-GYM-020** | Configured venue required: booking venue must exist in configured allowed venue list | Domain + Service | `domain.validation.validate_venue` | Enforced against configured venues |
| **BR-GYM-021** | Faculty report review: only assigned Club Faculty Councillor for that club can review its event reports | Selector + Scoping | `selectors.scoping.check_faculty_councillor` | Scoping 404 on unassigned |
| **UC-GYM-001** | Create New Club (Student Admin) | Service + API | `api.views.ClubViewSet.create`, `services.clubs.create_club` | Actor: Student Admin |
| **UC-GYM-002** | Book Club Session (Club Head) | Service + API | `api.views.BookingViewSet.book_session`, `services.bookings.book_session` | Actor: Club Head |
| **UC-GYM-003** | Book Club Event (Club Head) | Service + API | `api.views.BookingViewSet.book_event`, `services.bookings.book_event` | Actor: Club Head |
| **UC-GYM-004** | Apply for Club Membership (Student) | Service + API | `api.views.MembershipViewSet.apply`, `services.memberships.apply_membership` | Actor: Student |
| **UC-GYM-005** | Approve Club Membership (Club Head) | Service + API | `api.views.MembershipViewSet.approve`, `services.memberships.approve_membership` | Actor: Club Head |
| **UC-GYM-006** | Create Voting Poll (Club Head) | Service + API | `api.views.PollViewSet.create`, `services.polls.create_poll` | Actor: Club Head |
| **UC-GYM-007** | Vote in Poll (Student) | Service + API | `api.views.PollViewSet.vote`, `services.polls.cast_vote` | Actor: Eligible Student |
| **UC-GYM-008** | Change Club Leadership (Club Head) | Service + API | `api.views.ClubViewSet.change_leadership`, `services.clubs.change_leadership` | Actor: Club Head |
| **UC-GYM-009** | Request Club Budget (Club Head) | Service + API | `api.views.BudgetViewSet.create`, `services.budgets.submit_budget_request` | Actor: Club Head |
| **UC-GYM-010** | Submit Club Event Report (Club Head) | Service + API | `api.views.ReportViewSet.create`, `services.reports.submit_event_report` | Actor: Club Head |
| **UC-GYM-011** | Approve / Confirm Club (Student Admin) | Service + API | `api.views.ClubViewSet.confirm`, `services.clubs.approve_club` | Actor: Student Admin |
| **UC-GYM-012** | Review Club Event Report (Club Faculty Councillor) | Selector + API | `api.views.ReportViewSet.list`, `selectors.reports` | Actor: Club Faculty Councillor |
| **BW-GYM-01** | Club Membership Enrollment | Workflow | `domain.membership_state`, `services.memberships` | (none) -> open -> confirmed |
| **BW-GYM-02** | Targeted Poll Participation | Workflow | `domain.poll_state`, `services.polls` | (none) -> active -> expired / voted |
| **BW-GYM-03** | Club Establishment and Confirmation | Workflow | `domain.club_state`, `services.clubs` | (none) -> open -> confirmed |

---

## Step 3.2 (b) — Domain Model

### 1. `Club` (`modules.gymkhana.models.club`)
Represents a student club or organisation.
- `id`: AutoField (PK)
- `name`: CharField(max_length=120, unique=True)
- `category`: CharField(max_length=30, choices=Category.choices) — `technical`, `sports`, `cultural`
- `description`: TextField()
- `coordinator_id`: IntegerField() — User ID of current student coordinator
- `co_coordinator_id`: IntegerField() — User ID of current student co-coordinator
- `faculty_councillor_id`: IntegerField() — User ID of current faculty councillor
- `status`: CharField(max_length=20, choices=ClubStatus.choices, default='open') — `open`, `confirmed`
- `created_at`: DateTimeField(auto_now_add=True)
- `updated_at`: DateTimeField(auto_now=True)
- **Constraints:**
  - `CheckConstraint(check=Q(category__in=['technical', 'sports', 'cultural']), name='check_gymkhana_club_category')`
  - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='check_gymkhana_club_status')`
  - `CheckConstraint(check=~Q(coordinator_id=F('co_coordinator_id')), name='check_distinct_coordinator_co_coordinator')`

### 2. `ClubLeadershipHistory` (`modules.gymkhana.models.club`)
Audit log of club coordinator and co-coordinator transitions (`BR-GYM-016`).
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='leadership_history')
- `coordinator_id`: IntegerField()
- `co_coordinator_id`: IntegerField()
- `changed_by_id`: IntegerField()
- `changed_at`: DateTimeField(auto_now_add=True)

### 3. `VenueBooking` (`modules.gymkhana.models.booking`)
Unified booking aggregate for both sessions and events. Combining sessions and events into one table ensures cross-type venue conflict prevention (`BR-GYM-006`) at the database level using transactions and locking.
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='bookings')
- `booking_type`: CharField(max_length=20, choices=BookingType.choices) — `session`, `event`
- `venue`: CharField(max_length=100) — must be from configured venues list (`BR-GYM-020`)
- `booking_date`: DateField()
- `start_time`: TimeField()
- `end_time`: TimeField()
- `name`: CharField(max_length=150, blank=True) — event name or session title
- `description`: TextField()
- `poster_file`: FileField(upload_to='gymkhana/posters/', blank=True, null=True)
- `faculty_councillor_id`: IntegerField(null=True, blank=True) — required when `booking_type == 'event'`
- `booked_by_id`: IntegerField()
- `created_at`: DateTimeField(auto_now_add=True)
- **Constraints:**
  - `CheckConstraint(check=Q(booking_type__in=['session', 'event']), name='check_gymkhana_booking_type')`
  - `CheckConstraint(check=Q(start_time__lt=F('end_time')), name='check_booking_start_before_end')`

### 4. `ClubMembership` (`modules.gymkhana.models.membership`)
Tracks student membership application and confirmed enrollment.
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='memberships')
- `student_id`: IntegerField()
- `description`: TextField(blank=True) — application description / achievements
- `status`: CharField(max_length=20, choices=MembershipStatus.choices, default='open') — `open`, `confirmed`
- `remarks`: TextField(blank=True) — optional Club Head approval remarks
- `applied_at`: DateTimeField(auto_now_add=True)
- `approved_at`: DateTimeField(null=True, blank=True)
- `approved_by_id`: IntegerField(null=True, blank=True)
- **Constraints:**
  - `UniqueConstraint(fields=['club', 'student_id'], name='unique_club_membership_per_student')` (`BR-GYM-009`)
  - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='check_gymkhana_membership_status')`

### 5. `Poll` (`modules.gymkhana.models.poll`)
Student voting poll created by Club Head.
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='polls')
- `created_by_id`: IntegerField()
- `title`: CharField(max_length=200)
- `description`: TextField()
- `expires_at`: DateTimeField()
- `status`: CharField(max_length=20, default='active') — `active`, `expired`
- `created_at`: DateTimeField(auto_now_add=True)

### 6. `PollTargetGroup` (`modules.gymkhana.models.poll`)
Target batches and branches for poll eligibility (`BR-GYM-013`).
- `id`: AutoField (PK)
- `poll`: ForeignKey(Poll, on_delete=CASCADE, related_name='target_groups')
- `batch`: CharField(max_length=20) — e.g. "2023", "2024", or "all"
- `branch`: CharField(max_length=50) — e.g. "CSE", "ECE", "ME", or "all"
- **Constraints:**
  - `UniqueConstraint(fields=['poll', 'batch', 'branch'], name='unique_poll_target_group')`

### 7. `PollChoice` (`modules.gymkhana.models.poll`)
Choices for a voting poll (`BR-GYM-012` requires >= 2 choices).
- `id`: AutoField (PK)
- `poll`: ForeignKey(Poll, on_delete=CASCADE, related_name='choices')
- `choice_text`: CharField(max_length=200)
- `vote_count`: PositiveIntegerField(default=0)
- **Constraints:**
  - `UniqueConstraint(fields=['poll', 'choice_text'], name='unique_choice_per_poll')`

### 8. `PollVote` (`modules.gymkhana.models.poll`)
Audit record ensuring one vote per student per poll (`BR-GYM-015`).
- `id`: AutoField (PK)
- `poll`: ForeignKey(Poll, on_delete=CASCADE, related_name='votes')
- `student_id`: IntegerField()
- `choice`: ForeignKey(PollChoice, on_delete=CASCADE, related_name='cast_votes')
- `voted_at`: DateTimeField(auto_now_add=True)
- **Constraints:**
  - `UniqueConstraint(fields=['poll', 'student_id'], name='unique_student_vote_per_poll')`

### 9. `ClubBudgetRequest` (`modules.gymkhana.models.budget`)
Budget request submitted by Club Head and stored as open for tracking (`CFR-GYM-006`).
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='budget_requests')
- `submitted_by_id`: IntegerField()
- `amount`: DecimalField(max_digits=12, decimal_places=2)
- `purpose`: CharField(max_length=255)
- `description`: TextField()
- `supporting_file`: FileField(upload_to='gymkhana/budgets/')
- `status`: CharField(max_length=20, default='open') — tracking open status (`AFR-GYM-031`)
- `submitted_at`: DateTimeField(auto_now_add=True)
- **Constraints:**
  - `CheckConstraint(check=Q(amount__gte=0), name='check_positive_budget_amount')` (`BR-GYM-017`)

### 10. `ClubEventReport` (`modules.gymkhana.models.report`)
Documentation submitted by Club Head for an event and reviewed by Club Faculty Councillor (`CFR-GYM-007`).
- `id`: AutoField (PK)
- `club`: ForeignKey(Club, on_delete=CASCADE, related_name='event_reports')
- `submitted_by_id`: IntegerField()
- `student_incharge_id`: IntegerField()
- `event_name`: CharField(max_length=150)
- `event_date`: DateTimeField()
- `description`: TextField()
- `report_file`: FileField(upload_to='gymkhana/reports/')
- `submitted_at`: DateTimeField(auto_now_add=True)

---

## Step 3.3 (c) — State Machines

Declarative transition tables in `modules/gymkhana/domain/state_machines.py`:

### 1. Club Establishment Lifecycle (`BW-GYM-03`)
```python
CLUB_TRANSITIONS = {
    # (current_state, event, actor_role) -> next_state
    ("open", "CONFIRM", "student_admin"): "confirmed",
}
```
*Note: A newly created club begins in `open`. Only `student_admin` can confirm it.*

### 2. Club Membership Lifecycle (`BW-GYM-01`)
```python
MEMBERSHIP_TRANSITIONS = {
    # (current_state, event, actor_role) -> next_state
    ("open", "APPROVE", "club_head"): "confirmed",
}
```
*Note: A newly submitted application begins in `open`. Only `club_head` can approve it with optional remarks.*

### 3. Voting Poll Lifecycle (`BW-GYM-02`)
```python
POLL_TRANSITIONS = {
    # (current_state, event, actor_role) -> next_state
    ("active", "EXPIRE", "system"): "expired",
}
```
*Note: Poll is active while `now <= expires_at`. Evaluated dynamically and transitioned by Celery beat worker.*

---

## Step 3.4 (d) — Permission List

The exact `registry.py` specification:

```python
MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Campus Life",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student Nav Items ---
    {"code": "gymkhana.clubs", "label": "Clubs",
     "icon": "UsersThree", "to": "/gymkhana/clubs",
     "required_permission": "gymkhana.club.view", "sort_order": 10},
    {"code": "gymkhana.my_memberships", "label": "My Memberships",
     "icon": "UserCheck", "to": "/gymkhana/memberships",
     "required_permission": "gymkhana.membership.view", "sort_order": 20},
    {"code": "gymkhana.polls", "label": "Voting Polls",
     "icon": "CheckSquare", "to": "/gymkhana/polls",
     "required_permission": "gymkhana.poll.view", "sort_order": 30},
    {"code": "gymkhana.calendar", "label": "Events & Sessions",
     "icon": "CalendarBlank", "to": "/gymkhana/calendar",
     "required_permission": "gymkhana.booking.view", "sort_order": 40},

    # -- Club Head / Leadership Nav Items ---
    {"code": "gymkhana.club_management", "label": "Club Management",
     "icon": "GearSix", "to": "/gymkhana/manage",
     "required_permission": "gymkhana.club.manage", "sort_order": 50},

    # -- Student Admin Nav Items ---
    {"code": "gymkhana.admin_clubs", "label": "Club Approvals",
     "icon": "ShieldCheck", "to": "/gymkhana/admin",
     "required_permission": "gymkhana.club.approve", "sort_order": 60},

    # -- Faculty Councillor Nav Items ---
    {"code": "gymkhana.faculty_reports", "label": "Club Reports",
     "icon": "FileText", "to": "/gymkhana/reports",
     "required_permission": "gymkhana.report.view", "sort_order": 70},
]

PERMISSIONS = [
    ("gymkhana.club.view", "View active and confirmed clubs"),
    ("gymkhana.club.create", "Create a new club proposal"),
    ("gymkhana.club.approve", "Confirm and approve open clubs"),
    ("gymkhana.club.manage", "Manage club operations, members, and bookings"),
    ("gymkhana.booking.view", "View venue bookings and schedules"),
    ("gymkhana.booking.create", "Book club sessions and events"),
    ("gymkhana.membership.view", "View club membership applications"),
    ("gymkhana.membership.create", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve club membership applications"),
    ("gymkhana.poll.view", "View active targeted polls"),
    ("gymkhana.poll.create", "Create targeted voting polls"),
    ("gymkhana.poll.vote", "Cast vote in targeted polls"),
    ("gymkhana.budget.view", "View club budget tracking requests"),
    ("gymkhana.budget.create", "Submit club budget tracking requests"),
    ("gymkhana.report.view", "View submitted club event reports"),
    ("gymkhana.report.create", "Submit club event reports"),
]

SYSTEM_PERMISSIONS = [
    "gymkhana.poll.expire",
]

SCOPE_PERMISSIONS = {
    "gymkhana.club.manage": "club_id",
    "gymkhana.membership.approve": "club_id",
    "gymkhana.report.view": "club_id",
}

ROLE_GRANTS = {
    # Basic student role (held by definition)
    "student": [
        "gymkhana.club.view",
        "gymkhana.booking.view",
        "gymkhana.membership.view",
        "gymkhana.membership.create",
        "gymkhana.poll.view",
        "gymkhana.poll.vote",
        "gymkhana.club.manage",     # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.booking.create",  # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.membership.approve", # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.poll.create",     # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.budget.view",     # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.budget.create",   # Scoped via selectors: only active coordinator/co-coordinator
        "gymkhana.report.create",   # Scoped via selectors: only active coordinator/co-coordinator
    ],
    # Basic faculty role (held by definition)
    "faculty": [
        "gymkhana.club.view",
        "gymkhana.booking.view",
        "gymkhana.report.view",     # Scoped via selectors: only assigned Club Faculty Councillor
    ],
    # Student Admin designation (ERP globals_designation)
    "student_admin": [
        "gymkhana.club.view",
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.booking.view",
        "gymkhana.budget.view",
    ],
}
```

---

## Step 3.5 (e) — Endpoint List

All endpoints live under `/api/v1/gymkhana/`:

| Method | Path | Required Permission | Throttle Scope | Return Type | Rule IDs Enforced |
|---|---|---|---|---|---|
| `GET` | `/clubs/` | `gymkhana.club.view` | `read` | `List[ClubSummarySerializer]` | BR-GYM-004 |
| `POST` | `/clubs/` | `gymkhana.club.create` | `write` | `ClubDetailSerializer` | BR-GYM-001, BR-GYM-002, BR-GYM-003, UC-GYM-001 |
| `GET` | `/clubs/{id}/` | `gymkhana.club.view` | `read` | `ClubDetailSerializer` | AFR-GYM-001 |
| `POST` | `/clubs/{id}/confirm/` | `gymkhana.club.approve` | `write` | `ClubDetailSerializer` | BR-GYM-004, UC-GYM-011, BW-GYM-03 |
| `POST` | `/clubs/{id}/leadership/` | `gymkhana.club.manage` | `write` | `ClubDetailSerializer` | BR-GYM-001, BR-GYM-010, BR-GYM-016, UC-GYM-008 |
| `GET` | `/bookings/` | `gymkhana.booking.view` | `read` | `List[VenueBookingSerializer]` | AFR-GYM-010, AFR-GYM-014 |
| `POST` | `/bookings/session/` | `gymkhana.booking.create` | `write` | `VenueBookingSerializer` | BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020, UC-GYM-002 |
| `POST` | `/bookings/event/` | `gymkhana.booking.create` | `write` | `VenueBookingSerializer` | BR-GYM-002, BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020, UC-GYM-003 |
| `GET` | `/memberships/` | `gymkhana.membership.view` | `read` | `List[MembershipSerializer]` | AFR-GYM-016, AFR-GYM-020 |
| `POST` | `/memberships/apply/` | `gymkhana.membership.create` | `write` | `MembershipSerializer` | BR-GYM-007, BR-GYM-008, BR-GYM-009, UC-GYM-004, BW-GYM-01 |
| `POST` | `/memberships/{id}/approve/` | `gymkhana.membership.approve` | `write` | `MembershipSerializer` | BR-GYM-010, BR-GYM-011, UC-GYM-005, BW-GYM-01 |
| `GET` | `/polls/` | `gymkhana.poll.view` | `read` | `List[PollSummarySerializer]` | BR-GYM-014, UC-GYM-007 |
| `POST` | `/polls/` | `gymkhana.poll.create` | `write` | `PollDetailSerializer` | BR-GYM-010, BR-GYM-012, BR-GYM-013, UC-GYM-006, BW-GYM-02 |
| `GET` | `/polls/{id}/` | `gymkhana.poll.view` | `read` | `PollDetailSerializer` | BR-GYM-014, AFR-GYM-026 |
| `POST` | `/polls/{id}/vote/` | `gymkhana.poll.vote` | `write` | `VoteResultSerializer` | BR-GYM-014, BR-GYM-015, UC-GYM-007, BW-GYM-02 |
| `GET` | `/budgets/` | `gymkhana.budget.view` | `read` | `List[BudgetRequestSerializer]` | AFR-GYM-031 |
| `POST` | `/budgets/` | `gymkhana.budget.create` | `write` | `BudgetRequestSerializer` | BR-GYM-010, BR-GYM-017, BR-GYM-018, UC-GYM-009 |
| `GET` | `/reports/` | `gymkhana.report.view` | `read` | `List[EventReportSerializer]` | BR-GYM-021, UC-GYM-012 |
| `POST` | `/reports/` | `gymkhana.report.create` | `write` | `EventReportSerializer` | BR-GYM-010, BR-GYM-019, UC-GYM-010 |

### Client Routes & Guarding (1-to-1 match with NAV_ITEMS)
- `/gymkhana/clubs` -> `<RequirePermission permission="gymkhana.club.view"><ClubsPage/></RequirePermission>`
- `/gymkhana/memberships` -> `<RequirePermission permission="gymkhana.membership.view"><MembershipsPage/></RequirePermission>`
- `/gymkhana/polls` -> `<RequirePermission permission="gymkhana.poll.view"><PollsPage/></RequirePermission>`
- `/gymkhana/calendar` -> `<RequirePermission permission="gymkhana.booking.view"><CalendarPage/></RequirePermission>`
- `/gymkhana/manage` -> `<RequirePermission permission="gymkhana.club.manage"><ClubManagementPage/></RequirePermission>`
- `/gymkhana/admin` -> `<RequirePermission permission="gymkhana.club.approve"><ClubAdminPage/></RequirePermission>`
- `/gymkhana/reports` -> `<RequirePermission permission="gymkhana.report.view"><FacultyReportsPage/></RequirePermission>`

### Sidebar Entry for `INTEGRATED_MODULES` (`Fusion-client` handover instruction)
```javascript
{
  id: "gymkhana",
  label: "Gymkhana",
  icon: "Trophy",
  to: "/gymkhana/clubs",
  section: "Campus Life",
}
```

---

## Step 3.6 (f) — Contracts

### 1. Exposed by `modules.gymkhana.contracts` (Plural getters only)
```python
def get_clubs(club_ids: Sequence[int]) -> Sequence[Dict[str, Any]]:
    """Return public details for requested club IDs."""
    ...

def get_confirmed_club_members(club_ids: Sequence[int]) -> Sequence[Dict[str, Any]]:
    """Return confirmed membership records for requested club IDs."""
    ...
```

### 2. External Module / IAM Dependencies
- `IamClient.get_users(user_ids: Sequence[int])`: validates user existence, student vs. faculty kind (`BR-GYM-001`, `BR-GYM-002`).
- `Directory / Academic Directory`: resolves student batch and discipline/branch for poll targeting checks (`BR-GYM-013`, `BR-GYM-014`).

---

## Step 3.7 (g) — Scheduled Work (`modules.gymkhana.schedule`)

```python
BEAT_SCHEDULE = {
    "gymkhana-expire-polls-hourly": {
        "task": "modules.gymkhana.tasks.expire_polls",
        "schedule": 3600.0, # hourly
    },
}
```
- **Task:** `modules.gymkhana.tasks.expire_polls`
- **Cadence:** Hourly (3600 seconds)
- **Impact if omitted:** Expired polls remain active indefinitely unless dynamically filtered by query time checks. The query layer also enforces `now <= expires_at` as defense-in-depth, so failure of Celery beat does not cause incorrect voting permissions.

---

## Step 3.8 (h) — Open Questions & Known Gaps

1. **Configured Venues Baseline (`BR-GYM-020`):**
   - The spec specifies that sessions and events must use a "configured venue".
   - *Proposal:* Provide a fixed institute venue list (`["Hall 1", "Hall 2", "L-101", "L-102", "Open Air Theatre", "SAC Gym", "Football Ground"]`) configurable via django settings (`GYMKHANA_CONFIGURED_VENUES`).
2. **Online Budget Approval Out of Scope (`CFR-GYM-006`, `AFR-GYM-031`):**
   - Budget requests are strictly stored and tracked in `open` status. No approval/rejection endpoint or lifecycle is provided, matching the synchronised specification.
3. **Membership Rejection/Cancellation Out of Scope (`CFR-GYM-004`, `AFR-GYM-021`):**
   - Applications only transition from `open` to `confirmed`. No rejection/cancel transition exists in the v1.1 baseline.
4. **Target Group Audience Resolution (`BR-GYM-013`):**
   - When batch or branch is `"all"`, all students in the institute are targeted. If specific batch and branch are provided, student must match both batch and branch to vote.
5. **No New External Python/JS Dependencies:**
   - No external libraries outside standard Django, DRF, and existing packages in `Fusion-Integrated` are introduced.

---

## Revision 2 — awaiting Student 2's written approval

Made after commit `38eca25`, when re-checking the module found that it did not meet this blueprint.

### Changes to the design above

| Change | Why |
|---|---|
| `student_admin` no longer holds `gymkhana.report.view` | CFR-GYM-007 allows "only the assigned Club Faculty Councillor" to read reports |
| Permissions are narrowed to the acting role (`selectors/access.py`) | The session lists the permissions of every role held |
| New `VenueDay(venue, booking_date)`, locked before each booking | Locking overlapping rows locks nothing when there are none, so BR-GYM-006 could be raced |
| New `GymkhanaNotification` outbox, and a task every 60 seconds to send it | AFR-GYM-013, AFR-GYM-015 and AFR-GYM-025 had no implementation |
| Uploads go to `PLACEMENT_UPLOAD_ROOT/gymkhana`, private, under a generated name | They were written into the repository |
| A student's batch and branch come from the directory | The session carries neither, so targeted voting always refused |
| A poll needs at least one target group | BW-GYM-02, transition 1: "valid target groups" |
| A report cannot be dated in the future | UC-GYM-010 precondition |
| Nobody approves their own membership application | BR-GYM-010; a security rule |

### Endpoints added

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/access/` | `gymkhana.club.view` | What the acting role may do, and the clubs led |
| `GET` | `/venues/` | `gymkhana.booking.view` | Venues for the booking form |
| `GET` | `/people/` | `gymkhana.club.create` or `gymkhana.club.manage` | Username search, for Student Admin and club heads only |
| `GET` | `/poll-options/` | `gymkhana.poll.create` | Batches and branches that exist, for club heads only |
| `GET` | `/bookings/{id}/poster/` | `gymkhana.booking.view` | Poster download |
| `GET` | `/budgets/{id}/file/` | `gymkhana.budget.view` | Supporting file download |
| `GET` | `/reports/{id}/file/` | `gymkhana.report.view` | Report download |

Every write endpoint carries the `gymkhana_write` throttle.

### Open questions for Student 2

Each is built on the reading in the second column, and changes if you decide otherwise.

| Question | Reading used |
|---|---|
| Who are the "intended student recipients" of a session or event? | The club's confirmed members |
| How are notifications sent? | Email, through the module's own outbox, as Placement does |
| Is a poster required for an event? AFR-GYM-014 lists it and AFR-GYM-010 calls only the session's optional | Optional, because FR-015 expects an event without one to be accepted |
| Must an event name the club's own councillor, or any faculty member? | Any faculty member |
| Polls, reports and leadership changes list no confirmed-club precondition | Polls and reports need a confirmed club; a leadership change does not |
| Who sees a poll's tally? | Whoever may open the poll |
| May coordinator and co-coordinator be the same person, or two clubs share a name? | No to both |
| May a booking be made for a past date? | Yes; no rule forbids it |
| Should a file's bytes have to match its extension? | No: the spec tests upload plain text as `.pdf`. Type, size and active content are checked, and files are only ever downloaded |

### Known gaps

- "Valid student" and "valid faculty" check the person's kind. The directory contract does not say
  whether an account is active.
- The poll audience is read from the IAM's `academics/directory`, which also returns CPI. Only ids
  are kept.
- `PLACEMENT_UPLOAD_ROOT` is another module's setting name. A setting of our own is a shared-file
  change and needs approval.
