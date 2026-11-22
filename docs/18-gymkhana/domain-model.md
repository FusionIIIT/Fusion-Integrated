# Gymkhana Module — Domain Model

This document specifies the domain entities, relationships, constraints, and invariants for the Gymkhana module (`modules.gymkhana`) within the Fusion-Integrated platform.

## 1. Domain Entities & Responsibilities

The Gymkhana module models student extracurricular activities, club management, activity room/ground bookings, membership applications, democratic polling, budget requests, and event reports.

### 1.1 Core Entities

1. **Club (`gymkhana_club`)**
   - **Fields**: `id`, `name` (unique), `category` (Technical, Sports, Cultural), `coordinator_user_id` (int), `co_coordinator_user_id` (int), `faculty_councillor_user_id` (int), `description` (text), `status` (open, confirmed), `created_at`, `updated_at`.
   - **Invariants**:
     - Coordinator and Co-coordinator must be distinct active students (`GYM-FR-01`).
     - Faculty councillor must be an active faculty member (`GYM-FR-02`).
     - Newly created clubs start in `open` status; transition to `confirmed` requires `gymkhana.club.manage` permission (held by Student Admin) (`GYM-FR-03`, `GYM-FR-04`).

2. **ClubSession (`gymkhana_session`)**
   - **Fields**: `id`, `club_id` (FK -> Club), `venue`, `date`, `start_time`, `end_time`, `description`, `poster`, `created_by_user_id`, `created_at`, `updated_at`.
   - **Invariants**:
     - `start_time < end_time` enforced by DB CheckConstraint `gym_session_time_valid`.
     - `venue` must be among `settings.GYMKHANA_VENUES`.
     - Overlapping sessions or events at the same venue on the same date are prohibited, synchronized via `BookingLock`.

3. **ClubEvent (`gymkhana_event`)**
   - **Fields**: `id`, `club_id` (FK -> Club), `name`, `venue`, `date`, `start_time`, `end_time`, `description`, `poster`, `faculty_user_id`, `created_by_user_id`, `created_at`, `updated_at`.
   - **Invariants**:
     - `faculty_user_id` must be an active faculty member.
     - `start_time < end_time` enforced by DB CheckConstraint `gym_event_time_valid`.
     - Venue non-overlap invariant checked synchronously with sessions.

4. **BookingLock (`gymkhana_booking_lock`)**
   - **Fields**: `id`, `venue`, `date`.
   - **Invariants**:
     - Unique per `(venue, date)`.
     - Acquired with `select_for_update()` inside a transaction during session or event booking to guarantee race-free serialization across concurrent workers.

5. **MembershipApplication (`gymkhana_membership`)**
   - **Fields**: `id`, `club_id` (FK -> Club), `student_user_id`, `description`, `status` (open, confirmed), `remarks`, `approved_by_user_id`, `created_at`, `updated_at`.
   - **Invariants**:
     - A student may apply at most once per club (`UniqueConstraint(club, student_user_id)`).
     - Membership applications can only be submitted to `confirmed` clubs.
     - Approval can only be performed by the club's coordinator or co-coordinator.

6. **VotingPoll (`gymkhana_poll`), PollTargetGroup (`gymkhana_poll_group`), PollChoice (`gymkhana_poll_choice`), PollVote (`gymkhana_poll_vote`)**
   - **Invariants**:
     - Target groups designate eligible student populations (`batch_year`, `discipline`).
     - A student must belong to a target group to cast a vote.
     - Exactly one vote per student per poll (`UniqueConstraint(poll, student_user_id)`).
     - Voting is rejected once `is_active=False` or `expires_at <= timezone.now()`.

7. **BudgetRequest (`gymkhana_budget_request`)**
   - **Fields**: `id`, `club_id` (FK -> Club), `amount`, `purpose`, `description`, `supporting_file`, `created_by_user_id`, `status`.
   - **Invariants**:
     - `amount >= 0` enforced by DB CheckConstraint `gym_budget_nonnegative`.

8. **ClubEventReport (`gymkhana_event_report`)**
   - **Fields**: `id`, `club_id` (FK -> Club), `student_incharge_user_id`, `event_name`, `event_at`, `description`, `report_file`, `created_by_user_id`.
   - **Invariants**:
     - Faculty Councillors review only reports belonging to clubs they supervise (`selectors/scoping`).

9. **NotificationOutbox (`gymkhana_notification_outbox`)**
   - **Fields**: `id`, `topic`, `dedupe_key` (unique), `recipient_user_id`, `subject`, `body`, `status` (pending, sending, sent, failed), `attempts`, `last_error`, `claimed_at`, `sent_at`.
   - **Invariants**:
     - Idempotent queuing via `ignore_conflicts=True` on `dedupe_key`.
     - Transactional outbox drained via Celery task or management command.

---

## 2. Cross-Module Boundaries & Zero Cross-Module FK

In compliance with platform architecture:
- ForeignKeys to `User` or other domain modules are strictly prohibited.
- User identity is referenced exclusively by plain integer `user_id` fields.
- User metadata (name, email, kind, batch_year, discipline) is resolved through `modules.directory.contracts.get_users()` or `student_ids_in_groups()`.
