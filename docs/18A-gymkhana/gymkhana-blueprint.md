# Gymkhana Module Blueprint (docs/18A-gymkhana)

This document is the authoritative Phase 2 design blueprint for the **Gymkhana** module (`18A`, URL segment `gymkhana`) in `Fusion-Integrated`. It strictly follows the specification set in `/mnt/c/Users/Kshethra/Documents/A9/Gymkhana` and matches the architectural standard and conventions of `modules/placement`.

---

## 3.1 (a) — Traceability Table

Every live Business Rule (`BR-GYM-`), Use Case (`UC-GYM-`), Basis Workflow (`BW-GYM-`), Coherent Functional Requirement (`CFR-GYM-`), and Atomic Functional Requirement (`AFR-GYM-`) from the synchronized baseline is mapped below to its architectural layer and planned enforcement point.

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **BR-GYM-001** | Coordinator, co-coordinator, and replacement leaders must reference valid students | `domain` & `services` | `modules/gymkhana/services/clubs.py` via `directory.contracts.get_users` | Verified on creation (`UC-001`) and leadership change (`UC-008`). |
| **BR-GYM-002** | Club Faculty Councillor must reference a valid faculty member | `domain` & `services` | `modules/gymkhana/services/clubs.py` via `directory.contracts.get_users` | Verified on creation (`UC-001`) and event booking context (`UC-003`). |
| **BR-GYM-003** | Club category is limited to Technical, Sports, or Cultural | `domain` & `models` | `modules/gymkhana/models/club.py` (`CheckConstraint`) | `CheckConstraint(category__in=['Technical', 'Sports', 'Cultural'])`. |
| **BR-GYM-004** | Club creation results in `open`; Student Admin approval transitions to `confirmed` | `domain` & `services` | `modules/gymkhana/domain/state_machine.py` (`ClubEstablishmentStateMachine`) | Declarative state machine; no rejection transition exists in baseline. |
| **BR-GYM-005** | Booking start time must be strictly earlier than end time | `domain` & `models` | `modules/gymkhana/models/booking.py` (`CheckConstraint`) | `CheckConstraint(start_time__lt=F('end_time'))`. |
| **BR-GYM-006** | No session or event may overlap any existing session or event in same venue/date | `domain` & `services` | `modules/gymkhana/services/bookings.py` (`VenueDayLock` critical section) | Cross-type exclusivity: session-session, event-event, and session-event via stable venue/date row lock. |
| **BR-GYM-007** | Student may apply for membership only in a confirmed club | `domain` & `services` | `modules/gymkhana/services/memberships.py` (`apply_membership`) | Refuses application if `club.status != 'confirmed'`. |
| **BR-GYM-008** | Student may apply to multiple different clubs | `domain` & `models` | `modules/gymkhana/models/membership.py` (`UniqueConstraint` on club+student) | Different club FKs are permitted concurrently for the same student. |
| **BR-GYM-009** | Student may not submit duplicate membership application to same club | `models` & `services` | `modules/gymkhana/models/membership.py` (`UniqueConstraint(fields=['club', 'student_id'])`) | Database-enforced uniqueness under concurrency; refuses duplicate. |
| **BR-GYM-010** | Only applicable coordinator or co-coordinator may perform Club Head operations for that club | `selectors` & `services` | `modules/gymkhana/selectors/scoping.py` (`get_managed_club`) | Object-level scope check; returns 404 for foreign clubs. |
| **BR-GYM-011** | Approving open membership changes status to confirmed and retains remarks | `domain` & `services` | `modules/gymkhana/domain/state_machine.py` (`ClubMembershipStateMachine`) | Choke-point update: status `open` -> `confirmed`, persists `remarks`. |
| **BR-GYM-012** | Voting poll must have at least two choices | `domain` & `services` | `modules/gymkhana/domain/polls.py` & `services/polls.py` | Refuses creation if `len(choices) < 2`. |
| **BR-GYM-013** | Poll is addressed only to student groups selected by batch and branch | `domain` & `services` | `modules/gymkhana/domain/polls.py` & `services/polls.py` | Stores target batch/discipline records; filters voter eligibility. |
| **BR-GYM-014** | Student may participate only in active, unexpired poll where student matches target | `domain` & `services` | `modules/gymkhana/services/polls.py` (`cast_vote`) | Refuses vote if poll is expired or student's batch/discipline does not match. |
| **BR-GYM-015** | Student may cast at most one vote in same poll | `models` & `services` | `modules/gymkhana/models/poll.py` (`UniqueConstraint(fields=['poll', 'student_id'])`) | Concurrent duplicate votes prevented by database unique constraint. |
| **BR-GYM-016** | Replacing coordinator/co-coordinator retires superseded active leadership | `domain` & `services` | `modules/gymkhana/services/clubs.py` (`change_leadership`) | Single transaction closes previous `effective_to` and inserts new tenure. |
| **BR-GYM-017** | Submitted club budget amount must be zero or greater | `domain` & `models` | `modules/gymkhana/models/budget.py` (`CheckConstraint(amount__gte=0)`) | Database constraint prevents negative amounts. |
| **BR-GYM-018** | Club budget request must include required supporting file | `domain` & `services` | `modules/gymkhana/services/budgets.py` via `core.files.drive.parse` | Rejects empty value; validates Drive URL syntax. |
| **BR-GYM-019** | Club event report must include required report/details file | `domain` & `services` | `modules/gymkhana/services/reports.py` via `core.files.drive.parse` | Rejects empty value; validates Drive URL syntax. |
| **BR-GYM-020** | Session/event booking must use a venue configured for Gymkhana booking | `domain` & `services` | `modules/gymkhana/domain/scheduling.py` (`validate_venue`) | Refuses venue if not in `CONFIGURED_VENUES`. |
| **BR-GYM-021** | Club Faculty Councillor may review/access submitted reports only for assigned club | `selectors` | `modules/gymkhana/selectors/scoping.py` (`visible_event_reports`) | Queryset filtered by `club__faculty_councillor_id == principal.user_id` (404 otherwise). |
| **UC-GYM-001** | Create New Club | `api` & `services` | `modules/gymkhana/api/views.py` (`ClubCreateView`) & `services/clubs.py` | Actor: Student Admin. Creates club in `open` state and initial leadership tenure. |
| **UC-GYM-002** | Book Club Session | `api` & `services` | `modules/gymkhana/api/views.py` (`SessionBookingView`) & `services/bookings.py` | Actor: Club Head. Validates slot exclusivity and notifies students. |
| **UC-GYM-003** | Book Club Event | `api` & `services` | `modules/gymkhana/api/views.py` (`EventBookingView`) & `services/bookings.py` | Actor: Club Head. Validates faculty context, venue exclusivity. |
| **UC-GYM-004** | Apply for Club Membership | `api` & `services` | `modules/gymkhana/api/views.py` (`MembershipApplyView`) & `services/memberships.py` | Actor: Student. Records application in `open` state. |
| **UC-GYM-005** | Approve Club Membership | `api` & `services` | `modules/gymkhana/api/views.py` (`MembershipApproveView`) & `services/memberships.py` | Actor: Club Head. Transitions status to `confirmed`. |
| **UC-GYM-006** | Create Voting Poll | `api` & `services` | `modules/gymkhana/api/views.py` (`PollCreateView`) & `services/polls.py` | Actor: Club Head. Creates choices and target groups; notifies students. |
| **UC-GYM-007** | Vote in Poll | `api` & `services` | `modules/gymkhana/api/views.py` (`PollVoteView`) & `services/polls.py` | Actor: Student. Verifies eligibility; records vote and choice reference. |
| **UC-GYM-008** | Change Club Leadership | `api` & `services` | `modules/gymkhana/api/views.py` (`ClubLeadershipView`) & `services/clubs.py` | Actor: Club Head. Validates new student leaders; updates assignments and history. |
| **UC-GYM-009** | Request Club Budget | `api` & `services` | `modules/gymkhana/api/views.py` (`BudgetRequestView`) & `services/budgets.py` | Actor: Club Head. Submits non-negative budget with supporting file. |
| **UC-GYM-010** | Submit Club Event Report | `api` & `services` | `modules/gymkhana/api/views.py` (`EventReportView`) & `services/reports.py` | Actor: Club Head. Submits report with event date AND time, student incharge, documentation file. |
| **UC-GYM-011** | Approve Club | `api` & `services` | `modules/gymkhana/api/views.py` (`ClubApproveView`) & `services/clubs.py` | Actor: Student Admin. Transitions club from `open` to `confirmed`. |
| **UC-GYM-012** | Review Club Event Report | `api` & `selectors` | `modules/gymkhana/api/views.py` (`EventReportDetailView`) & `selectors/scoping.py` | Actor: Club Faculty Councillor. Accesses report and file redirect (302). |
| **BW-GYM-01** | Club Membership Enrollment | `domain` & `services` | `modules/gymkhana/services/memberships.py` | Basis workflow: UC-004 (`open`) -> UC-005 (`confirmed`). |
| **BW-GYM-02** | Targeted Poll Participation | `domain` & `services` | `modules/gymkhana/services/polls.py` | Basis workflow: UC-006 (`active`) -> UC-007 (vote recorded). |
| **BW-GYM-03** | Club Establishment and Confirmation | `domain` & `services` | `modules/gymkhana/services/clubs.py` | Basis workflow: UC-001 (`open`) -> UC-011 (`confirmed`). |
| **CFR-GYM-001** | Student Admin-controlled establishment of clubs | `services` | `modules/gymkhana/services/clubs.py` | Parent requirement for AFR-001 through AFR-006. |
| **CFR-GYM-002** | Club Head leadership change and validation | `services` | `modules/gymkhana/services/clubs.py` | Parent requirement for AFR-007 through AFR-009. |
| **CFR-GYM-003** | Booking sessions and events with venue exclusivity and notifications | `services` | `modules/gymkhana/services/bookings.py` | Parent requirement for AFR-010 through AFR-015. |
| **CFR-GYM-004** | Confirmed-club membership enrollment and approval | `services` | `modules/gymkhana/services/memberships.py` | Parent requirement for AFR-016 through AFR-022. |
| **CFR-GYM-005** | Targeted club polling and single-vote enforcement | `services` | `modules/gymkhana/services/polls.py` | Parent requirement for AFR-023 through AFR-028. |
| **CFR-GYM-006** | Club budget request submission and tracking | `services` | `modules/gymkhana/services/budgets.py` | Parent requirement for AFR-029 through AFR-031. |
| **CFR-GYM-007** | Documented club event report submission and faculty review | `services` & `selectors` | `modules/gymkhana/services/reports.py` & `selectors/scoping.py` | Parent requirement for AFR-032 through AFR-034. |
| **AFR-GYM-001** | Capture required club data on creation | `services` | `modules/gymkhana/services/clubs.py` (`create_club`) | Name, category, coordinator, co-coordinator, faculty councillor, description. |
| **AFR-GYM-002** | Validate coordinator and co-coordinator are valid students | `services` | `modules/gymkhana/services/clubs.py` (`create_club`) | Directory contract check: `kind == "student"`. |
| **AFR-GYM-003** | Validate Club Faculty Councillor is a valid faculty member | `services` | `modules/gymkhana/services/clubs.py` (`create_club`) | Directory contract check: `kind == "faculty"`. |
| **AFR-GYM-004** | Restrict club category to Technical, Sports, or Cultural | `models` | `modules/gymkhana/models/club.py` (`CheckConstraint`) | Enforced in database. |
| **AFR-GYM-005** | Record newly created club in `open` state | `models` & `services` | `modules/gymkhana/models/club.py` (default `'open'`) | Default initial state. |
| **AFR-GYM-006** | Student Admin approve open club and record as `confirmed` | `services` | `modules/gymkhana/services/clubs.py` (`approve_club`) | Updates status to `confirmed`. |
| **AFR-GYM-007** | Club Head replace coordinator and co-coordinator assignments | `services` | `modules/gymkhana/services/clubs.py` (`change_leadership`) | Choke-point update. |
| **AFR-GYM-008** | Validate replacement leaders are valid students | `services` | `modules/gymkhana/services/clubs.py` (`change_leadership`) | Directory contract check: `kind == "student"`. |
| **AFR-GYM-009** | Maintain only current coordinator and co-coordinator for the club | `models` & `services` | `modules/gymkhana/models/club.py` | Club row fields updated; prior leaders superseded. |
| **AFR-GYM-010** | Club Head book session with venue, date, times, description, poster | `services` | `modules/gymkhana/services/bookings.py` (`book_session`) | Creates session booking. |
| **AFR-GYM-011** | Reject booking if start time does not precede end time | `models` & `domain` | `modules/gymkhana/models/booking.py` (`CheckConstraint`) | `start_time < end_time`. |
| **AFR-GYM-012** | Prevent session/event overlap in same venue on same date | `services` | `modules/gymkhana/services/bookings.py` | Enforced under venue/date row lock. |
| **AFR-GYM-013** | Notify intended students after session booked | `services` | `modules/gymkhana/services/bookings.py` & `tasks.py` | Emits notification event to outbox/task. |
| **AFR-GYM-014** | Club Head book event with faculty context, venue, date, times, poster, description | `services` | `modules/gymkhana/services/bookings.py` (`book_event`) | Creates event booking. |
| **AFR-GYM-015** | Notify intended students after event booked | `services` | `modules/gymkhana/services/bookings.py` & `tasks.py` | Emits notification event to outbox/task. |
| **AFR-GYM-016** | Student apply for membership in confirmed club | `services` | `modules/gymkhana/services/memberships.py` (`apply_membership`) | Validates club is confirmed. |
| **AFR-GYM-017** | Student may maintain applications to multiple different clubs | `models` | `modules/gymkhana/models/membership.py` | Unique on (club, student_id). |
| **AFR-GYM-018** | Prevent duplicate membership application to same club | `models` | `modules/gymkhana/models/membership.py` | Database unique constraint rejects duplicate. |
| **AFR-GYM-019** | Record newly submitted application with `open` status | `models` | `modules/gymkhana/models/membership.py` | Default status is `'open'`. |
| **AFR-GYM-020** | Club Head access pending applications for their club | `selectors` | `modules/gymkhana/selectors/scoping.py` (`pending_memberships`) | Scoped to actor's club. |
| **AFR-GYM-021** | Club Head approve open application and record optional remarks | `services` | `modules/gymkhana/services/memberships.py` (`approve_membership`) | Saves remarks. |
| **AFR-GYM-022** | Change approved membership application to `confirmed` | `domain` & `services` | `modules/gymkhana/domain/state_machine.py` | Status set to `'confirmed'`. |
| **AFR-GYM-023** | Club Head create poll with title, description, expiry, choices, targets | `services` | `modules/gymkhana/services/polls.py` (`create_poll`) | Stores poll, choices, targets. |
| **AFR-GYM-024** | Require at least two choices for a poll | `domain` & `services` | `modules/gymkhana/domain/polls.py` | Rejects `len(choices) < 2`. |
| **AFR-GYM-025** | Notify target student groups on poll creation | `services` | `modules/gymkhana/services/polls.py` & `tasks.py` | Enqueues notification task. |
| **AFR-GYM-026** | Eligible targeted student access active poll and choices | `selectors` | `modules/gymkhana/selectors/scoping.py` (`visible_polls`) | Filters by batch/discipline match. |
| **AFR-GYM-027** | Eligible targeted student cast one choice in active poll | `services` | `modules/gymkhana/services/polls.py` (`cast_vote`) | Validates active, unexpired, targeted, choice in poll. |
| **AFR-GYM-028** | Prevent more than one vote by same student in same poll and record tally | `models` & `services` | `modules/gymkhana/models/poll.py` (`PollVote` unique constraint) | Rejects 2nd vote; tally derived from votes. |
| **AFR-GYM-029** | Club Head submit budget request with amount, purpose, description, supporting file | `services` | `modules/gymkhana/services/budgets.py` (`submit_budget_request`) | Persists request. |
| **AFR-GYM-030** | Reject budget request with negative amount or missing file | `domain` & `models` | `modules/gymkhana/models/budget.py` (`CheckConstraint`) & `services` | Rejects negative or missing file. |
| **AFR-GYM-031** | Store submitted budget request as `open` for tracking; approval out of scope | `models` & `services` | `modules/gymkhana/models/budget.py` | Status is `'open'`; no approval lifecycle. |
| **AFR-GYM-032** | Club Head submit event report with incharge, event name, date/time, description, file | `services` | `modules/gymkhana/services/reports.py` (`submit_event_report`) | Persists report with date AND time. |
| **AFR-GYM-033** | Require report/details file when event report is submitted | `services` | `modules/gymkhana/services/reports.py` via `core.files.drive` | Rejects if file link missing/invalid. |
| **AFR-GYM-034** | Assigned Club Faculty Councillor access and review submitted event reports | `selectors` | `modules/gymkhana/selectors/scoping.py` (`visible_event_reports`) | Filtered to councillor's club. |

---

## 3.2 (b) — Domain Model

### Architectural Foreign Key Boundary
Per **ADR-0013** (*"No cross-module foreign keys"*), no `ForeignKey` may cross a module boundary (e.g. from `gymkhana` to `auth_user`, `directory`, or `placement`). Institute identities owned by IAM/Directory are referenced strictly by scalar `BigIntegerField` user IDs (`user_id`).
However, **relationships between entities internal to Gymkhana use Django `ForeignKey` with explicit `on_delete` policies**.

```
  ┌────────────────────────────────────────────────────────┐
  │                         Club                           │
  ├────────────────────────────────────────────────────────┤
  │ id: int [PK]                                           │
  │ name: str [unique]                                     │
  │ category: str ['Technical', 'Sports', 'Cultural']      │
  │ description: str                                       │
  │ coordinator_id: int [scalar user_id]                   │
  │ co_coordinator_id: int [scalar user_id]                │
  │ faculty_councillor_id: int [scalar user_id]            │
  │ status: str ['open', 'confirmed']                      │
  │ created_at / updated_at: datetime                      │
  └───────────────────────────┬────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │ 1                 │ 1                 │ 1
          ▼ * [CASCADE]       ▼ * [CASCADE]       ▼ * [CASCADE]
  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
  │ ClubMembership  │ │     Booking     │ │      Poll       │
  ├─────────────────┤ ├─────────────────┤ ├─────────────────┤
  │ id: int         │ │ id: int         │ │ id: int         │
  │ club: FK(Club)  │ │ club: FK(Club)  │ │ club: FK(Club)  │
  │ student_id: int │ │ type: str       │ │ title: str      │
  │ status: str     │ │ venue: str      │ │ expires_at: dt  │
  │ remarks: str    │ │ date: date      │ │ status: str     │
  │ description: str│ │ start_time: time│ └────────┬────────┘
  └─────────────────┘ │ end_time: time  │          │ 1
                      │ poster_url: str │          ▼ * [CASCADE]
                      └─────────────────┘   ┌───────────────┐
                                            │  PollChoice   │
                                            ├───────────────┤
                                            │ id: int       │
                                            │ poll: FK(Poll)│
                                            │ text: str     │
                                            └───────┬───────┘
                                                    │ 1
                                                    ▼ * [PROTECT]
                                            ┌───────────────┐
                                            │   PollVote    │
                                            ├───────────────┤
                                            │ id: int       │
                                            │ poll: FK(Poll)│
                                            │ choice: FK    │
                                            │ student_id:int│
                                            └───────────────┘
```

### Entities, Fields, and Database Constraints

1. **`Club`**:
   - `id`: BigAutoField (PK).
   - `name`: `CharField(max_length=100, unique=True)`.
   - `category`: `CharField(max_length=20)`. Restricted to `'Technical'`, `'Sports'`, `'Cultural'` (`BR-GYM-003`).
   - `description`: `TextField()`.
   - `coordinator_id`: `BigIntegerField()`. Scalar user ID of student leader (`BR-GYM-001`).
   - `co_coordinator_id`: `BigIntegerField()`. Scalar user ID of student leader (`BR-GYM-001`).
   - `faculty_councillor_id`: `BigIntegerField()`. Scalar user ID of faculty member (`BR-GYM-002`).
   - `status`: `CharField(max_length=20, default='open')`. Restricted to `'open'`, `'confirmed'` (`BR-GYM-004`).
   - `created_at`, `updated_at`: `DateTimeField`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['name'], name='gymkhana_club_name_uniq')`
     - `CheckConstraint(check=~Q(coordinator_id=F('co_coordinator_id')), name='gymkhana_club_distinct_coordinators')`
     - `CheckConstraint(check=Q(category__in=['Technical', 'Sports', 'Cultural']), name='gymkhana_club_category_valid')`
     - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='gymkhana_club_status_valid')`
   - **Indexes**:
     - `models.Index(fields=['status'], name='gymkhana_club_status_idx')`

2. **`ClubLeadershipHistory`**:
   - `id`: BigAutoField (PK).
   - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="leadership_history")`.
   - `coordinator_id`: `BigIntegerField()`.
   - `co_coordinator_id`: `BigIntegerField()`.
   - `effective_from`: `DateTimeField(default=timezone.now)`.
   - `effective_to`: `DateTimeField(null=True, blank=True)`. `null=True` denotes currently active leadership tenure.
   - `changed_by_user_id`: `BigIntegerField()`.
   - **Lifecycle & Invariants**:
     - On club creation (`UC-GYM-001`), the initial tenure is recorded with `effective_from=now(), effective_to=None`.
     - On leadership change (`UC-GYM-008`, `BR-GYM-016`), in one transaction:
       1. Close current active row: `filter(club=club, effective_to__isnull=True).update(effective_to=timezone.now())`.
       2. Insert new row: `create(club=club, coordinator_id=..., co_coordinator_id=..., effective_from=now(), effective_to=None)`.
       3. Update `Club.coordinator_id` and `Club.co_coordinator_id`.
   - **Indexes**:
     - `models.Index(fields=['club', 'effective_to'], name='gymkhana_lead_hist_idx')`

3. **`ClubMembership`**:
   - `id`: BigAutoField (PK).
   - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")`.
   - `student_id`: `BigIntegerField(db_index=True)`. Scalar user ID.
   - `description`: `TextField(blank=True, default='')` (achievements or statement, `AFR-GYM-016`).
   - `status`: `CharField(max_length=20, default='open')`. Restricted to `'open'`, `'confirmed'` (`BR-GYM-011`).
   - `remarks`: `TextField(blank=True, default='')` (`UC-GYM-005`).
   - `created_at`, `updated_at`: `DateTimeField`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['club', 'student_id'], name='gymkhana_membership_club_student_uniq')` (`BR-GYM-009`, `AFR-GYM-018`).
     - `CheckConstraint(check=Q(status__in=['open', 'confirmed']), name='gymkhana_membership_status_valid')`.
   - **Indexes**:
     - `models.Index(fields=['club', 'status'], name='gymkhana_member_club_stat_idx')`
     - `models.Index(fields=['student_id', 'status'], name='gymkhana_member_stu_stat_idx')`

4. **`VenueDayLock` (Concurrency Lock Resource)**:
   - `id`: BigAutoField (PK).
   - `venue`: `CharField(max_length=60)`.
   - `date`: `DateField()`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['venue', 'date'], name='gymkhana_venueday_uniq')`.
   - **Indexes**:
     - `models.Index(fields=['venue', 'date'], name='gymkhana_venueday_idx')`.
   - **Purpose & Lifecycle**:
     - Provides a stable, row-level serialization anchor for all simultaneous booking attempts for that venue on that date.
     - **Creation Strategy**: Created just-in-time on the first booking attempt for a given `(venue, date)` using atomic conflict-safe insertion (`bulk_create(..., ignore_conflicts=True)` / `INSERT ... ON CONFLICT DO NOTHING`).
     - **Persistence**: Once created, `VenueDayLock` rows are persistent markers; they are never deleted when bookings are canceled or modified, ensuring subsequent bookings on the same venue/date immediately acquire existing row locks without re-triggering creation logic.

5. **`Booking`** (Unified Aggregate for Cross-Type Exclusivity):
   - `id`: BigAutoField (PK).
   - `booking_type`: `CharField(max_length=10)`. Restricted to `'session'`, `'event'` (`UC-GYM-002`, `UC-GYM-003`).
   - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="bookings")`.
   - `venue`: `CharField(max_length=60)` (`BR-GYM-020`).
   - `date`: `DateField(db_index=True)`.
   - `start_time`: `TimeField()`.
   - `end_time`: `TimeField()`.
   - `name`: `CharField(max_length=150, blank=True, default='')`.
   - `description`: `TextField()`.
   - `poster_url`: `CharField(max_length=500, blank=True, default='')`.
   - `poster_file_id`: `CharField(max_length=200, blank=True, default='')`.
   - `faculty_councillor_id`: `BigIntegerField(null=True, blank=True)` (event context, `UC-GYM-003`).
   - `created_at`: `DateTimeField(auto_now_add=True)`.
   - **Database Constraints**:
     - `CheckConstraint(check=Q(start_time__lt=F('end_time')), name='gymkhana_booking_time_valid')` (`BR-GYM-005`).
     - `CheckConstraint(check=Q(booking_type__in=['session', 'event']), name='gymkhana_booking_type_valid')`.
   - **Indexes**:
     - `models.Index(fields=['venue', 'date', 'start_time'], name='gymkhana_booking_venue_slot_idx')`
     - `models.Index(fields=['club', 'date'], name='gymkhana_booking_club_date_idx')`

6. **`Poll`**:
   - `id`: BigAutoField (PK).
   - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="polls")`.
   - `title`: `CharField(max_length=200)`.
   - `description`: `TextField()`.
   - `expires_at`: `DateTimeField(db_index=True)`.
   - `status`: `CharField(max_length=20, default='active')`. Restricted to `'active'`, `'expired'`.
   - `created_by_user_id`: `BigIntegerField()`.
   - `created_at`: `DateTimeField(auto_now_add=True)`.
   - **Database Constraints**:
     - `CheckConstraint(check=Q(status__in=['active', 'expired']), name='gymkhana_poll_status_valid')`.
   - **Indexes**:
     - `models.Index(fields=['club', 'status'], name='gymkhana_poll_club_stat_idx')`
     - `models.Index(fields=['status', 'expires_at'], name='gymkhana_poll_stat_exp_idx')`

7. **`PollChoice`**:
   - `id`: BigAutoField (PK).
   - `poll`: `ForeignKey(Poll, on_delete=models.CASCADE, related_name="choices")`.
   - `text`: `CharField(max_length=200)`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['poll', 'text'], name='gymkhana_poll_choice_text_uniq')`.
   - **Tally Consistency**: Tallies are **derived dynamically via `Count('votes')` from `PollVote`** (`poll.choices.annotate(tally=Count('votes'))`). This eliminates lost updates under concurrency without needing mutable counter columns.

8. **`PollTarget`**:
   - `id`: BigAutoField (PK).
   - `poll`: `ForeignKey(Poll, on_delete=models.CASCADE, related_name="targets")`.
   - `batch_year`: `IntegerField()`.
   - `discipline`: `CharField(max_length=50, blank=True, default='all')`.
   - **Definition of `discipline='all'`**:
     A record with `discipline='all'` matches students of *any* discipline/branch within that `batch_year`. A specific discipline (e.g. `'CSE'`) matches only students whose Directory discipline equals `'CSE'`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['poll', 'batch_year', 'discipline'], name='gymkhana_polltarget_uniq')`.
   - **Indexes**:
     - `models.Index(fields=['poll', 'batch_year'], name='gymkhana_polltarget_idx')`

9. **`PollVote`**:
   - `id`: BigAutoField (PK).
   - `poll`: `ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")`.
   - `choice`: `ForeignKey(PollChoice, on_delete=models.PROTECT, related_name="votes")`.
   - `student_id`: `BigIntegerField(db_index=True)`. Scalar user ID.
   - `created_at`: `DateTimeField(auto_now_add=True)`.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['poll', 'student_id'], name='gymkhana_pollvote_uniq')` (`BR-GYM-015`, `AFR-GYM-028`).
   - **Service Invariant**: The service verifies `choice.poll_id == poll.id`. Concurrent duplicate votes are serialized and rejected by the database unique constraint, safely handled as `ConflictError`.

10. **`ClubBudgetRequest`**:
    - `id`: BigAutoField (PK).
    - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="budget_requests")`.
    - `amount`: `DecimalField(max_digits=12, decimal_places=2)`.
    - `purpose`: `CharField(max_length=200)`.
    - `description`: `TextField()`.
    - `supporting_file_url`: `CharField(max_length=500)`.
    - `supporting_file_id`: `CharField(max_length=200)`.
    - `status`: `CharField(max_length=20, default='open')` (`AFR-GYM-031`).
    - `submitted_by_user_id`: `BigIntegerField()`.
    - `created_at`: `DateTimeField(auto_now_add=True)`.
    - **Database Constraints**:
      - `CheckConstraint(check=Q(amount__gte=0), name='gymkhana_budget_amount_gte_zero')` (`BR-GYM-017`).
      - `CheckConstraint(check=Q(status='open'), name='gymkhana_budget_status_open')`.

11. **`ClubEventReport`**:
    - `id`: BigAutoField (PK).
    - `club`: `ForeignKey(Club, on_delete=models.CASCADE, related_name="event_reports")`.
    - `student_incharge_id`: `BigIntegerField()`. Validated via Directory contract (`kind == "student"`).
    - `event_name`: `CharField(max_length=150)`.
    - `event_date`: `DateField()`.
    - `event_time`: `TimeField()`. Explicitly captures event time per `UC-GYM-010`.
    - `description`: `TextField()`.
    - `report_file_url`: `CharField(max_length=500)`.
    - `report_file_id`: `CharField(max_length=200)`.
    - `submitted_by_user_id`: `BigIntegerField()`.
    - `created_at`: `DateTimeField(auto_now_add=True)`.
    - **Indexes**:
      - `models.Index(fields=['club', 'event_date'], name='gymkhana_report_club_date_idx')`

---

### Booking Concurrency Strategy Evaluation & Justification

#### The Problem with `select_for_update()` over Empty Results
When two concurrent requests attempt to book the *same venue, date, and overlapping slot* when no booking row exists yet, executing `Booking.objects.select_for_update().filter(...)` returns an empty queryset. In PostgreSQL, `SELECT FOR UPDATE` on a query that matches 0 rows locks zero rows and does not prevent phantom inserts. Both transactions proceed to insert, causing an illegal overlap (`BR-GYM-006`).

#### Evaluation of Options

1. **Option A: Stable Resource Locking via `VenueDayLock` (Selected Strategy)**:
   - Introduce `VenueDayLock(venue, date)` with a unique constraint on `(venue, date)`.

   - **The First-Time Booking Concurrency Race**:
     When a `(venue, date)` has never been booked before, no `VenueDayLock` row exists in the database. If two transactions $T_1$ and $T_2$ arrive concurrently to book that venue/date:
     - Naive `get_or_create()` or direct `create()` without conflict handling can raise `IntegrityError` in PostgreSQL, which marks the current transaction block as aborted unless wrapped in a database savepoint.
     - Simply catching `IntegrityError` without acquiring `select_for_update()` would allow the losing transaction to proceed without locking, completely bypassing serialization.
     - Therefore, lock acquisition must atomically handle both row creation and exclusive row-lock acquisition.

   - **Atomic Lock Acquisition & Creation Strategy (`acquire_venue_day_lock`)**:
     To guarantee safe first-time creation without duplicate key errors, transaction abortion, or serialization bypass, lock acquisition uses an atomic pattern:
     ```python
     def acquire_venue_day_lock(venue: str, date: datetime.date) -> VenueDayLock:
         """
         Atomically acquire an exclusive row-level lock on the VenueDayLock anchor for (venue, date).
         Guarantees safe serialization even if the lock row does not exist yet.
         """
         # 1. Fast path: Row already exists from a previous booking
         try:
             return VenueDayLock.objects.select_for_update().get(venue=venue, date=date)
         except VenueDayLock.DoesNotExist:
             pass

         # 2. Slow path: First-time booking attempt for this venue and date.
         # Insert the anchor using bulk_create with ignore_conflicts=True,
         # which translates to PostgreSQL: `INSERT ... ON CONFLICT (venue, date) DO NOTHING`.
         # (Alternatively: savepoint-isolated try / with transaction.atomic(): create() / except IntegrityError).
         # bulk_create(ignore_conflicts=True) is preferred as it is atomic and avoids savepoint overhead.
         VenueDayLock.objects.bulk_create(
             [VenueDayLock(venue=venue, date=date)],
             ignore_conflicts=True,
         )

         # 3. Serialized row-level lock acquisition:
         # The row is now guaranteed to exist in the database.
         # select_for_update() acquires an exclusive row lock.
         # If another concurrent transaction inserted the row first, this query blocks
         # until that transaction finishes (commits or rolls back).
         return VenueDayLock.objects.select_for_update().get(venue=venue, date=date)
     ```

   - **Booking Algorithm**:
     ```python
     @transaction.atomic
     def book_slot(*, booking_type, club, venue, date, start_time, end_time, ...):
         # 1. Acquire exclusive row lock on the stable (venue, date) anchor
         lock_obj = acquire_venue_day_lock(venue=venue, date=date)

         # 2. Critical section: serial execution for (venue, date)
         overlap = Booking.objects.filter(
             venue=venue, date=date,
             start_time__lt=end_time, end_time__gt=start_time,
         ).exists()
         if overlap:
             raise ConflictError(
                 "The venue is already booked for an overlapping time slot on this date.",
                 code="venue_overlap",
             )

         # 3. Insert booking (session or event)
         return Booking.objects.create(
             booking_type=booking_type,
             club=club,
             venue=venue,
             date=date,
             start_time=start_time,
             end_time=end_time,
             ...
         )
     ```

   - **Step-by-Step Concurrent Execution Analysis**:
     Suppose transactions $T_1$ and $T_2$ attempt to book the same venue and date simultaneously for the very first time:
     1. Both transactions miss the fast path (`VenueDayLock.DoesNotExist`).
     2. Both execute `bulk_create(..., ignore_conflicts=True)`.
     3. PostgreSQL executes `INSERT ... ON CONFLICT (venue, date) DO NOTHING`:
        - $T_1$'s INSERT succeeds, creating the row.
        - $T_2$'s INSERT hits the unique index conflict and does nothing (`DO NOTHING`). Neither transaction raises an unhandled error, and neither transaction aborts.
     4. Both proceed to `select_for_update().get(venue=venue, date=date)`:
        - $T_1$ immediately secures the exclusive row-level lock (`X` lock on `VenueDayLock`).
        - $T_2$'s `SELECT FOR UPDATE` attempts to lock the same row, detects the active lock held by $T_1$, and **blocks at the database level** until $T_1$ completes.
     5. **Resolution**:
        - **If $T_1$ commits** (successfully books its slot): $T_2$ unblocks, receives the latest committed snapshot, executes its overlap query in Step 2, detects the overlap with $T_1$'s booking, and raises `ConflictError("venue_overlap")`.
        - **If $T_1$ rolls back** (e.g. input validation failure or transient error): $T_2$ unblocks, evaluates the overlap query against unrolled state, finds no conflicting booking, and successfully creates its booking.
     - **Invariants Guaranteed**:
       - *Zero Duplicate Locks*: `UniqueConstraint(fields=['venue', 'date'])` ensures exactly one `VenueDayLock` row can exist.
       - *Zero Serialization Bypass*: Neither $T_1$ nor $T_2$ can enter the critical section without holding the exclusive `select_for_update()` lock.
       - *Zero False Conflicts*: Bookings for different venues or different dates acquire distinct lock rows and proceed concurrently without contention.

   - **Justification**:
     - Completely prevents race conditions across simultaneous session/session, event/event, and session/event requests.
     - 100% portable Django ORM and PostgreSQL semantics; requires no database extensions or superuser permissions.
     - Scoped strictly to `(venue, date)` so bookings for different venues or different dates run in parallel without contention.
     - Fully handles cold-start first-time booking concurrency without relying on pre-population scripts or risking transaction aborts.

2. **Option B: PostgreSQL `ExclusionConstraint` (Defense in Depth)**:
   - Uses `ExclusionConstraint` from `django.contrib.postgres.constraints` using a GiST index on `[('venue', '='), ('date', '='), (tsrange, '&&')]`.
   - *Limitation*: Requires PostgreSQL extension `btree_gist`. In local dev or fresh installs without superuser privileges, `CREATE EXTENSION btree_gist` may fail.
   - *Verdict*: `VenueDayLock` is the primary application concurrency barrier.

---

## 3.3 (c) — State Machines & Authorization

State transitions are authorized strictly via the authenticated `principal.permissions` and object-level scoping. Caller-supplied role-name strings are never trusted.

### 1. Club Establishment Lifecycle (`BW-GYM-03`)
```
[Uncreated] ──(create)──> [open] ──(approve)──> [confirmed] (terminal)
```

```python
# Transition Table: (current_state, event) -> (target_state, required_permission, guard_fn)
CLUB_TRANSITIONS = {
    (None, "create"): (
        "open",
        "gymkhana.club.create",
        lambda principal, club: True,  # Authenticated caller with permission
    ),
    ("open", "approve"): (
        "confirmed",
        "gymkhana.club.approve",
        lambda principal, club: True,  # Student Admin gate
    ),
}
```

### 2. Club Membership Lifecycle (`BW-GYM-01`)
```
[No Application] ──(apply)──> [open] ──(approve)──> [confirmed] (terminal)
```

```python
MEMBERSHIP_TRANSITIONS = {
    (None, "apply"): (
        "open",
        "gymkhana.membership.create",
        lambda principal, club: club.status == "confirmed",
    ),
    ("open", "approve"): (
        "confirmed",
        "gymkhana.membership.approve",
        lambda principal, membership: principal.user_id
        in (membership.club.coordinator_id, membership.club.co_coordinator_id),
    ),
}
```

### 3. Poll Lifecycle (`BW-GYM-02`)
```
[Uncreated] ──(create)──> [active] ──(vote)──> [active]
                              │
                    (expire [Internal Task])
                              ▼
                          [expired] (terminal)
```

```python
POLL_TRANSITIONS = {
    (None, "create"): (
        "active",
        "gymkhana.poll.create",
        lambda principal, poll: principal.user_id
        in (poll.club.coordinator_id, poll.club.co_coordinator_id),
    ),
    ("active", "vote"): (
        "active",
        "gymkhana.poll.update",
        lambda principal, poll: poll.status == "active"
        and poll.expires_at > timezone.now(),
    ),
}
```
*Note*: The `expire` event is an internal system background task executed by Celery beat (`gymkhana.close_expired_polls`) or management command. It is not exposed to HTTP callers and requires no human IAM permission.

---

## 3.4 (d) — Permission List (`registry.py`)

All permission codes strictly adhere to `<module>.<singular_noun>.<verb>` using the closed verb vocabulary from `docs/02-iam/rbac-model.md`: `view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`.

```python
MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Gymkhana",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student views
    {
        "code": "gymkhana.student.clubs",
        "label": "Clubs",
        "icon": "UsersThree",
        "to": "/gymkhana/clubs",
        "required_permission": "gymkhana.club.view",
        "sort_order": 10,
    },
    {
        "code": "gymkhana.student.memberships",
        "label": "My Memberships",
        "icon": "IdentificationBadge",
        "to": "/gymkhana/my-memberships",
        "required_permission": "gymkhana.membership.view",  # Corrected to view
        "sort_order": 20,
    },
    {
        "code": "gymkhana.student.schedule",
        "label": "Schedule",
        "icon": "CalendarBlank",
        "to": "/gymkhana/schedule",
        "required_permission": "gymkhana.session.view",
        "sort_order": 30,
    },
    {
        "code": "gymkhana.student.polls",
        "label": "Voting Polls",
        "icon": "CheckSquareOffset",
        "to": "/gymkhana/polls",
        "required_permission": "gymkhana.poll.view",  # Corrected to view
        "sort_order": 40,
    },
    # -- Club Head views
    {
        "code": "gymkhana.head.manage",
        "label": "Club Management",
        "icon": "GearSix",
        "to": "/gymkhana/manage-club",
        "required_permission": "gymkhana.membership.view",  # Hub view permission
        "sort_order": 50,
    },
    {
        "code": "gymkhana.head.bookings",
        "label": "Book Venue",
        "icon": "CalendarPlus",
        "to": "/gymkhana/book-venue",
        "required_permission": "gymkhana.session.create",
        "sort_order": 60,
    },
    {
        "code": "gymkhana.head.budget",
        "label": "Budget Tracking",
        "icon": "Coins",
        "to": "/gymkhana/budget-requests",
        "required_permission": "gymkhana.budget.create",
        "sort_order": 70,
    },
    {
        "code": "gymkhana.head.reports",
        "label": "Event Reports",
        "icon": "FileText",
        "to": "/gymkhana/event-reports",
        "required_permission": "gymkhana.report.create",
        "sort_order": 80,
    },
    # -- Faculty Councillor view
    {
        "code": "gymkhana.faculty.review",
        "label": "Report Review",
        "icon": "FileSearch",
        "to": "/gymkhana/councillor-review",
        "required_permission": "gymkhana.report.review",
        "sort_order": 85,
    },
    # -- Student Admin view
    {
        "code": "gymkhana.admin.approvals",
        "label": "Club Approvals",
        "icon": "Checks",
        "to": "/gymkhana/club-approvals",
        "required_permission": "gymkhana.club.approve",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    ("gymkhana.club.view", "Browse confirmed clubs"),
    ("gymkhana.club.create", "Create new club record"),
    ("gymkhana.club.approve", "Approve open club to confirmed"),
    ("gymkhana.leadership.update", "Replace club coordinator and co-coordinator"),
    ("gymkhana.session.view", "View public club sessions"),
    ("gymkhana.session.create", "Book club session"),
    ("gymkhana.event.view", "View public club events"),
    ("gymkhana.event.create", "Book club event"),
    ("gymkhana.membership.view", "View club membership applications"),
    ("gymkhana.membership.create", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve pending club membership"),
    ("gymkhana.poll.view", "View active eligible voting polls"),
    ("gymkhana.poll.create", "Create voting poll"),
    ("gymkhana.poll.update", "Cast vote in active poll"),
    ("gymkhana.budget.view", "View club budget requests"),
    ("gymkhana.budget.create", "Submit club budget request"),
    ("gymkhana.report.view", "View submitted club event reports"),
    ("gymkhana.report.create", "Submit club event report"),
    ("gymkhana.report.review", "Review event report as faculty councillor"),
]

# Scheduled work runs internally without human permissions; closed vocabulary respected.
SYSTEM_PERMISSIONS = []

SCOPE_PERMISSIONS = [
    "gymkhana.membership.approve",
    "gymkhana.session.create",
    "gymkhana.event.create",
    "gymkhana.poll.create",
    "gymkhana.leadership.update",
    "gymkhana.budget.create",
    "gymkhana.report.create",
    "gymkhana.report.review",
]

_STUDENT = [
    "gymkhana.club.view",
    "gymkhana.membership.view",
    "gymkhana.membership.create",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.poll.view",
    "gymkhana.poll.update",
]

_CLUB_HEAD = [
    "gymkhana.club.view",
    "gymkhana.session.view",
    "gymkhana.session.create",
    "gymkhana.event.view",
    "gymkhana.event.create",
    "gymkhana.membership.view",
    "gymkhana.membership.approve",
    "gymkhana.poll.view",
    "gymkhana.poll.create",
    "gymkhana.leadership.update",
    "gymkhana.budget.view",
    "gymkhana.budget.create",
    "gymkhana.report.view",
    "gymkhana.report.create",
]

_FACULTY_COUNCILLOR = [
    "gymkhana.club.view",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.report.view",
    "gymkhana.report.review",
]

_STUDENT_ADMIN = [
    "gymkhana.club.view",
    "gymkhana.club.create",
    "gymkhana.club.approve",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.report.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "co-ordinator": _CLUB_HEAD,  # [APPROVED BY STUD2 2]
    "co co-ordinator": _CLUB_HEAD,  # [APPROVED BY STUD2 2]
    "faculty": _FACULTY_COUNCILLOR,  # [APPROVED BY STUD2 4]
    "Dean_s": _STUDENT_ADMIN,  # [APPROVED BY STUD2 1]
    "studentacadadmin": _STUDENT_ADMIN,  # [APPROVED BY STUD2 1]
}
```

---

## 3.5 (e) — Endpoint List & Navigation

All endpoints mount under `/api/v1/gymkhana/` behind module and permission gates.

| HTTP Method | URL Path | Module Gate | Permission Gate | Serializer / Response | Rules Enforced |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/gymkhana/clubs/` | `gymkhana` | `gymkhana.club.view` | `ClubSummarySerializer(many=True)` | `BR-GYM-004`, `BR-GYM-007` |
| `POST` | `/api/v1/gymkhana/clubs/` | `gymkhana` | `gymkhana.club.create` | `ClubDetailSerializer` (201) | `BR-GYM-001`–`004`, `UC-001`, `AFR-001`–`005` |
| `GET` | `/api/v1/gymkhana/clubs/{id}/` | `gymkhana` | `gymkhana.club.view` | `ClubDetailSerializer` | `BR-GYM-004`, `UC-001` |
| `POST` | `/api/v1/gymkhana/clubs/{id}/approve/` | `gymkhana` | `gymkhana.club.approve` | `ClubDetailSerializer` | `BR-GYM-004`, `UC-011`, `AFR-006` |
| `POST` | `/api/v1/gymkhana/clubs/{id}/leadership/` | `gymkhana` | `gymkhana.leadership.update` | `ClubDetailSerializer` | `BR-GYM-001`, `010`, `016`, `UC-008`, `AFR-007`–`009` |
| `GET` | `/api/v1/gymkhana/memberships/` | `gymkhana` | `gymkhana.membership.view` | `MembershipSerializer(many=True)` | `BR-GYM-008`, `UC-004` (Student's own applications) |
| `POST` | `/api/v1/gymkhana/memberships/` | `gymkhana` | `gymkhana.membership.create` | `MembershipSerializer` (201) | `BR-GYM-007`–`009`, `UC-004`, `AFR-016`–`019` |
| `GET` | `/api/v1/gymkhana/clubs/{id}/memberships/` | `gymkhana` | `gymkhana.membership.view` | `MembershipSerializer(many=True)` | `BR-GYM-010`, `UC-005`, `AFR-020` (Pending applications for club) |
| `POST` | `/api/v1/gymkhana/memberships/{id}/approve/` | `gymkhana` | `gymkhana.membership.approve` | `MembershipSerializer` | `BR-GYM-010`, `011`, `UC-005`, `AFR-021`–`022` |
| `GET` | `/api/v1/gymkhana/bookings/` | `gymkhana` | `gymkhana.session.view` | `BookingSerializer(many=True)` | `BR-GYM-006`, `UC-002`, `UC-003` (Public calendar schedule) |
| `POST` | `/api/v1/gymkhana/sessions/` | `gymkhana` | `gymkhana.session.create` | `BookingSerializer` (201) | `BR-GYM-005`, `006`, `010`, `020`, `UC-002`, `AFR-010`–`013` |
| `POST` | `/api/v1/gymkhana/events/` | `gymkhana` | `gymkhana.event.create` | `BookingSerializer` (201) | `BR-GYM-002`, `005`, `006`, `010`, `020`, `UC-003`, `AFR-014`–`015` |
| `GET` | `/api/v1/gymkhana/polls/` | `gymkhana` | `gymkhana.poll.view` | `PollSummarySerializer(many=True)` | `BR-GYM-013`, `014`, `UC-007`, `AFR-026` |
| `POST` | `/api/v1/gymkhana/polls/` | `gymkhana` | `gymkhana.poll.create` | `PollDetailSerializer` (201) | `BR-GYM-010`, `012`, `013`, `UC-006`, `AFR-023`–`025` |
| `GET` | `/api/v1/gymkhana/polls/{id}/` | `gymkhana` | `gymkhana.poll.view` | `PollDetailSerializer` | `BR-GYM-014`, `UC-007`, `AFR-026` |
| `POST` | `/api/v1/gymkhana/polls/{id}/vote/` | `gymkhana` | `gymkhana.poll.update` | `PollVoteResultSerializer` | `BR-GYM-014`, `015`, `UC-007`, `AFR-027`–`028` |
| `GET` | `/api/v1/gymkhana/clubs/{id}/budgets/` | `gymkhana` | `gymkhana.budget.view` | `BudgetRequestSerializer(many=True)`| `BR-GYM-010`, `UC-009`, `AFR-031` |
| `POST` | `/api/v1/gymkhana/clubs/{id}/budgets/` | `gymkhana` | `gymkhana.budget.create` | `BudgetRequestSerializer` (201) | `BR-GYM-010`, `017`, `018`, `UC-009`, `AFR-029`–`031` |
| `GET` | `/api/v1/gymkhana/clubs/{id}/reports/` | `gymkhana` | `gymkhana.report.view` | `EventReportSerializer(many=True)` | `BR-GYM-010`, `UC-010`, `AFR-032` |
| `POST` | `/api/v1/gymkhana/clubs/{id}/reports/` | `gymkhana` | `gymkhana.report.create` | `EventReportSerializer` (201) | `BR-GYM-010`, `019`, `UC-010`, `AFR-032`–`033` |
| `GET` | `/api/v1/gymkhana/reports/{id}/` | `gymkhana` | `gymkhana.report.view` | `EventReportDetailSerializer` | `BR-GYM-021`, `UC-012`, `AFR-034` |
| `GET` | `/api/v1/gymkhana/reports/{id}/download/` | `gymkhana`| `gymkhana.report.review` | HTTP 302 Redirect to Drive URL | `BR-GYM-021`, `UC-012`, `AFR-034` |

### Client Route Guards & Page Architecture (Step 6.4)
- **Club Management Hub (`/gymkhana/manage-club`)**:
  - Route is guarded with `RequirePermission permission="gymkhana.membership.view"`.
  - The page serves as a unified operational console for the Club Head. Inside the page, each section and control is independently checked via `can()` from `useAuth`:
    - Leadership change button: `can("gymkhana.leadership.update")`
    - Membership approvals table & action buttons: `can("gymkhana.membership.approve")`
    - Create poll button: `can("gymkhana.poll.create")`
    - Submit budget request modal: `can("gymkhana.budget.create")`
    - Submit event report modal: `can("gymkhana.report.create")`
  - This prevents conflating multiple coarse permissions into one or granting permissions solely to render a nav link.

---

## 3.6 (f) — Cross-Module Contracts

Gymkhana exports plural getters in `modules/gymkhana/contracts.py`:

```python
"""Gymkhana public contract. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ClubLeadersDTO:
    club_id: int
    club_name: str
    coordinator_id: int
    co_coordinator_id: int
    faculty_councillor_id: int
    status: str


@dataclass(frozen=True)
class StudentClubMembershipDTO:
    club_id: int
    club_name: str
    status: str  # 'open', 'confirmed'


def get_active_club_leaders(
    club_ids: Sequence[int],
) -> dict[int, ClubLeadersDTO]:
    """Return leadership assignments for requested club IDs."""
    ids = {int(i) for i in club_ids if i is not None}
    if not ids:
        return {}
    from modules.gymkhana.models import Club

    rows = Club.objects.filter(pk__in=ids)
    return {
        c.pk: ClubLeadersDTO(
            c.pk,
            c.name,
            c.coordinator_id,
            c.co_coordinator_id,
            c.faculty_councillor_id,
            c.status,
        )
        for c in rows
    }


def get_student_memberships(
    user_ids: Sequence[int],
) -> dict[int, list[StudentClubMembershipDTO]]:
    """Return club memberships for a batch of student IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.gymkhana.models import ClubMembership

    rows = (
        ClubMembership.objects.filter(student_id__in=ids)
        .select_related("club")
        .values_list("student_id", "club_id", "club__name", "status")
    )
    result: dict[int, list[StudentClubMembershipDTO]] = {
        uid: [] for uid in ids
    }
    for uid, cid, cname, status in rows:
        result[uid].append(StudentClubMembershipDTO(cid, cname, status))
    return result
```

### Dependencies on Other Modules
- **`modules.directory.contracts.get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]`**:
  - Validates student status for coordinator and co-coordinator (`kind == "student"`, `BR-GYM-001`).
  - Validates student status for student incharge of event report (`kind == "student"`, `UC-GYM-010`, `AFR-GYM-032`).
  - Validates faculty councillor status (`kind == "faculty"`, `BR-GYM-002`).
  - Retrieves student `batch_year` and `discipline` for poll targeting verification (`BR-GYM-013`, `BR-GYM-014`).

---

## 3.7 (g) — Scheduled Work (`schedule.py`)

```python
"""Gymkhana scheduled timers. Merged in config/celery.py."""

TASK_ROUTES = {
    "gymkhana.close_expired_polls": {"queue": "default"},
    "gymkhana.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "gymkhana.close-expired-polls": {
        "task": "gymkhana.close_expired_polls",
        "schedule": 300.0,  # 5 minutes
        "options": {"expires": 290},
    },
    "gymkhana.deliver-notifications": {
        "task": "gymkhana.deliver_notifications",
        "schedule": 60.0,  # 1 minute
        "options": {"expires": 55},
    },
}
```

- Scheduled tasks run as trusted internal background tasks. They do not hold human IAM tokens and require no pseudo-permissions.
- Operators can trigger manual runs via `manage.py gymkhana_tasks --task close_expired_polls`.

---

## 3.8 (h) — Open Questions & Decisions Pending Approval

The following four items were explicitly approved by the Student2. Implementation may proceed using the approved rulings recorded below.

---

### [APPROVED BY STUD2 1] Student Admin Role Mapping in IAM

- **Context**: Spec names `Student Admin` (`UC-GYM-001`, `UC-GYM-011`, `BW-GYM-03`). The string `"Student Admin"` does not exist in `globals_designation`.
- **Recommended Option**:
  - Map `ROLE_GRANTS` for Student Admin permissions to `Dean_s` (Dean of Students, designation id 48) and `studentacadadmin` (id 119).
  - *Rationale*: Both are existing, catalogued designations in ERP and IAM. `Dean_s` is already assigned to `fac00083` in the dev dump.
- **Alternative Option**:
  - Provision a brand-new designation `"Student Admin"` into `globals_designation` in `fusionlab` and sync it into IAM.
- **Technical & Security Implications**:
  - If a new designation is created in dev, production deployment will require the institute's academic office to add the designation to the real ERP before deployment.
  - Using `Dean_s` requires zero ERP schema changes and matches existing administrative authority.
- **Approver Confirmation Required**: **APPROVED by Student2**.
- **Implementation Work Blocked**: Seeding `ROLE_GRANTS` in `registry.py` and creating synthetic Student Admin test fixtures in `accounts.ts`.

---

### [APPROVED BY STUD2 2] Club Head Role Mapping (`co-ordinator` vs `co co-ordinator`)

- **Context**: `globals_designation` contains both `'co-ordinator'` (id 56) and `'co co-ordinator'` (id 57). In the synthetic dump, both have 0 holders.
- **Recommended Option**:
  - Key `ROLE_GRANTS` with **both** `"co-ordinator"` and `"co co-ordinator"`.
  - *Rationale*: Reflects both coordinator posts in institute practice.
- **Alternative Option**:
  - Key `ROLE_GRANTS` with `"co-ordinator"` only.
- **Technical & Security Implications**:
  - `co co-ordinator` is uncatalogued in `iam/rbac.py`'s `CATALOGUE`, but uncatalogued roles are accepted and synced without errors.
  - Club Head actions are gated by object-level scoping (`selectors/scoping.py`), so granting the verb to both designations poses zero privilege escalation risk.
- **Approver Confirmation Required**: **APPROVED by Student2**.
- **Implementation Work Blocked**: Finalizing `ROLE_GRANTS` in `registry.py`.

---

### [APPROVED BY STUD2 3] Google Drive Links vs. Direct File Uploads

- **Context**: `BR-GYM-018`, `BR-GYM-019`, and `UC-009`/`010` mention supporting files and event reports. `PS §7.72` states implementation storage mechanisms are not prescribed.
- **Recommended Option**:
  - Accept and store validated Google Drive links (`drive_url`, `drive_file_id`, `original_filename`) validated via `core.files.drive.parse()`.
  - *Validation Limitation*: Explicitly note that `core.files.drive.parse()` verifies URL syntax, scheme, authority, and domain structure only. It does **not** verify remote file existence, sharing permissions, or reviewer accessibility.
  - *Rationale*: Matches `core/files/drive.py` and Placement (`modules/placement/services/documents.py`). `core/files/storage.py` is explicitly deprecated for writes.
- **Alternative Option**:
  - Implement multipart binary byte upload to local disk/storage.
- **Technical & Security Implications**:
  - Binary file uploads introduce server disk exhaustion risks, SSRF, and require ClamAV anti-virus scanning in production. Drive links eliminate byte-handling vulnerabilities.
  - Review access is achieved via HTTP 302 redirect with `Referrer-Policy: no-referrer`.
- **Approver Confirmation Required**: **APPROVED by Student2**.
- **Implementation Work Blocked**: Model schema for `ClubBudgetRequest` and `ClubEventReport` (URL fields vs FileField) and serializer field types.

---

### [APPROVED BY STUD2 4] Faculty-Wide Report Permission with Club Scoping

- **Context**: `BR-GYM-021` and `UC-GYM-012` state that the Club Faculty Councillor reviews event reports. Faculty members hold basic role `faculty`. There is no `Club Faculty Councillor` designation in `globals_designation`.
- **Recommended Option**:
  - Grant `gymkhana.report.review` to `faculty` in `ROLE_GRANTS`. Enforce object-level access in `selectors/scoping.py` by filtering `report.club.faculty_councillor_id == principal.user_id` (returning 404 for unassigned clubs).
  - *Rationale*: Complies with Security Baseline 2.4 and 2.5 (*"filtering in selector, out-of-scope returns 404"*).
- **Alternative Option**:
  - Require the institute to create a new designation `"Club Faculty Councillor"` in ERP, assign it only to specific faculty, and grant the permission to that designation.
  - *Rationale*: Only faculty with this designation see Gymkhana in their sidebar.
- **Technical & Security Implications**:
  - Under the recommended option, every faculty member gets the Gymkhana module link in their sidebar. Unassigned faculty will see an empty report list `[]`.
- **Approver Confirmation Required**: **APPROVED by Student2**.
- **Implementation Work Blocked**: Route guard and nav item definition for `gymkhana.faculty.review`.

---

## Conclusion & Stop

This revised Phase 2 blueprint is approved for Phase 3 implementation. **The four pending decisions have been approved by Student2, and implementation shall proceed using the rulings recorded above.**
