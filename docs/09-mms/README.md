# Mess Management System (MMS) — Module Specification Set

## 1. Overview & System Scope
The Mess Management System (MMS) manages institute dining facilities, student mess registrations, daily/weekly dining menus, rebate applications, student feedback, and supervisory administrative operations across student, caretaker, and warden roles.

---

## 2. Roles and Permissions (MMS-ROLE)
- **Student (`student`)**:
  - `mess_module.registration.submit`: Apply for mess registration/deregistration.
  - `mess_module.menu.view`: View active meal schedules and daily menus.
  - `mess_module.rebate.apply`: Submit leave-based rebate requests.
  - `mess_module.feedback.submit`: Submit rating and comments for mess quality.
- **Mess Caretaker (`caretaker`, `mess_caretaker`)**:
  - `mess_module.registration.review`: Approve/reject student registrations.
  - `mess_module.menu.manage`: Create and update recurring weekly meal plans.
  - `mess_module.rebate.review`: Approve, modify, or reject student rebate requests.
  - `mess_module.feedback.view`: Review student ratings and comments.
- **Mess Warden / Admin (`warden`, `mess_warden`, `admin`, `acadadmin`)**:
  - `mess_module.role.manage`: Assign active Mess Caretaker and Mess Warden.
  - `mess_module.oversight.view`: Audit reports, meal participation metrics, and action logs.

---

## 3. Business Rules (BR-MMS)
- **BR-MMS-001**: System must support multiple messes (e.g., "Central Mess", "Mess 1", "Mess 2").
- **BR-MMS-002**: Operational role assignment requires a valid, positive employee ID.
- **BR-MMS-003**: Each mess facility has exactly one active Mess Caretaker at any given date.
- **BR-MMS-004**: Each mess facility has exactly one active Mess Warden at any given date.
- **BR-MMS-005**: Assigning a new active Caretaker/Warden automatically deactivates the prior active assignment.
- **BR-MMS-008**: Only the active Mess Caretaker can open a registration window; opening a new window deactivates prior active windows.
- **BR-MMS-009**: Student mess registrations can only be submitted during an active and open registration window (`window_start <= request_date <= window_end`).
- **BR-MMS-010**: Caretaker approves or rejects registration; approving sets status to `REGISTERED`.
- **BR-MMS-012**: Only currently `REGISTERED` students can submit a deregistration request.
- **BR-MMS-013**: Caretaker approval of deregistration sets status to `DEREGISTERED`.
- **BR-MMS-014**: Weekly meal menu items are uniquely defined by `(mess_name, day_of_week, meal_time)`.
- **BR-MMS-020**: Feedback ratings must be between 1 and 5 stars inclusive.
- **BR-MMS-021**: Minimum rebate duration is 3 consecutive calendar days (`(end_date - start_date) + 1 >= 3`).
- **BR-MMS-022**: Rebate request must be submitted at least one calendar day prior to the rebate start date (`submission_date < start_date`).
- **BR-MMS-023**: Rebate dates cannot overlap with any existing pending or approved rebate for the same student.
- **BR-MMS-025**: Caretakers can modify approved start/end dates when approving a rebate request.
- **BR-MMS-038**: Meal times supported: `BREAKFAST`, `LUNCH`, `SNACKS`, `DINNER`.
- **BR-MMS-039**: Days of week supported: `MONDAY`, `TUESDAY`, `WEDNESDAY`, `THURSDAY`, `FRIDAY`, `SATURDAY`, `SUNDAY`.

---

## 4. Use Case Specifications (MMS-UC)
- **MMS-UC-001**: Assign Operational Mess Role (Warden/Admin assigns employee as Caretaker/Warden).
- **MMS-UC-002**: Open Mess Registration Window (Caretaker defines semester/monthly cycle).
- **MMS-UC-003**: Student Mess Registration Submission (Student submits application).
- **MMS-UC-004**: Caretaker Registration Review (Caretaker reviews and approves/rejects).
- **MMS-UC-005**: Student Mess Deregistration Request (Student requests cancellation).
- **MMS-UC-006**: Caretaker Deregistration Review (Caretaker processes deregistration).
- **MMS-UC-007**: View Daily/Weekly Menu (Student views meals by day and slot).
- **MMS-UC-008**: Publish / Update Menu Item (Caretaker updates meal items).
- **MMS-UC-009**: Submit Rebate Application (Student applies with dates and reason).
- **MMS-UC-010**: Review Rebate Application (Caretaker approves/rejects with optional adjusted dates).
- **MMS-UC-011**: Submit Mess Feedback (Student rates food/hygiene 1-5 stars with comments).
- **MMS-UC-012**: View Oversight Audit Logs (Warden reviews system actions).

---

## 5. Workflows (MMS-WF)
- **MMS-WF-001 (Registration Lifecycle)**:
  1. Caretaker opens registration window.
  2. Student applies for Central Mess.
  3. Caretaker approves application -> Status `REGISTERED`.
  4. Student later requests deregistration.
  5. Caretaker approves deregistration -> Status `DEREGISTERED`.
- **MMS-WF-002 (Rebate Processing)**:
  1. Student requests rebate (minimum 3 days, 1 day advance).
  2. Rule engine validates non-overlap and constraints.
  3. Caretaker reviews, optionally adjusts approved dates, and approves.
  4. Contract reports rebate days for mess billing deductions.
- **MMS-WF-003 (Menu Management & Feedback)**:
  1. Caretaker publishes breakfast, lunch, snacks, and dinner for Monday–Sunday.
  2. Students view menu and submit ratings.
  3. Warden inspects feedback analytics.
