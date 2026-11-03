# Workflow Design for Fusion ERP LMS Course Management

## Executive Summary

### Overview of LMS State Transitions, Actors, and Workflow Execution
The Learning Management System (LMS) workflow is designed to enforce strict role-based access control and scoped permissions across various state transitions. The system manages the lifecycle of course materials, announcements, assignments, submissions, grades, and scheduled releases through a series of well-defined states and events.

### Core Principle: Strict Role Enforcement and Scoped Access Control
The core principle of this design is to ensure that only authorized actors can perform specific actions within defined scopes. This includes faculty members managing course content, students interacting with course materials, and teaching assistants (TAs) assisting in grading processes.

## State-Transition Lifecycles & State Machine Tables

### Material Lifecycle (`draft` -> `scheduled` -> `published`)
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| draft        | schedule    | Faculty | release_date > now | scheduled   | None        |
| scheduled    | publish     | Background Engine | now >= release_date | published  | Students gain read-only access |

### Announcement Lifecycle (`created` -> `visible`)
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| created      | publish     | Faculty | None           | visible    | Announcements become visible to all users |

### Assignment Lifecycle (`draft` -> `scheduled` -> `published`)
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| draft        | schedule    | Faculty | release_date > now | scheduled   | None        |
| scheduled    | publish     | Background Engine | now >= release_date | published  | Students gain access to assignment |

### Submission Lifecycle (`pending` -> `submitted` [on-time], `late`, `missing`)
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| pending      | submit      | Student | now <= due_date | submitted   | Submission recorded as on-time |
| pending      | submit      | Student | now > due_date  | late        | Submission marked as late |
| pending      | submit      | Student | None           | missing     | Submission marked as missing |

### Grade Lifecycle (`draft` [graded by Faculty or TA] -> `released` [Faculty only])
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| draft        | grade       | Faculty or TA | None           | released    | Grade becomes visible to student if explicitly released by faculty |

### Scheduled Release Lifecycle (`pending` -> `processing` -> `completed` / `failed`)
| Source State | Event/Action | Actor | Guard Condition | Target State | Side Effects |
|--------------|-------------|-------|----------------|-------------|-------------|
| pending      | process     | Background Engine | None           | processing  | Release is processed in background |
| processing   | complete    | Background Engine | Success        | completed   | Release completes successfully |
| processing   | fail        | Background Engine | Failure        | failed      | Release fails and requires manual intervention |

## Detailed Mapping of Basis Workflows (BW-LMS-01 through 05)

### BW-LMS-01: Scheduled Course Material Release
- **Trigger**: Faculty schedules material with `release_date > now`.
- **Actor**: Faculty.
- **Preconditions**: Material is in `draft` state, release date has not yet arrived.
- **Step-by-step Execution Sequence**:
  1. Faculty sets a future `release_date` for the material.
  2. Background engine monitors and triggers publication when `now >= release_date`.
  3. Students gain read-only access to the published material.
- **State Changes**: `draft` -> `scheduled` -> `published`.
- **Database Operations**: Update material state, log release event.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Material is accessible to students with read-only access.

### BW-LMS-02: Assignment Immediate Release and On-Time Submission
- **Trigger**: Faculty publishes assignment immediately.
- **Actor**: Faculty.
- **Preconditions**: No specific conditions required.
- **Step-by-step Execution Sequence**:
  1. Faculty sets the `due_date` for the assignment.
  2. Students can submit their work before or after the due date.
  3. Submission is recorded as `submitted`.
- **State Changes**: `draft` -> `published`, then `pending` -> `submitted`.
- **Database Operations**: Update assignment state, log submission event.
- **Error/Retry Behavior**: No specific error handling required for immediate release.
- **Postconditions**: Assignment and submissions are tracked in the database.

### BW-LMS-03: Assignment Scheduled Release and On-Time Submission
- **Trigger**: Faculty sets a future `release_date` for the assignment.
- **Actor**: Faculty.
- **Preconditions**: Material is in `draft` state, release date has not yet arrived.
- **Step-by-step Execution Sequence**:
  1. Faculty schedules the assignment with a future `release_date`.
  2. Background engine monitors and triggers publication when `now >= release_date`.
  3. Students gain access to the published assignment before the due date.
  4. Students can submit their work before or after the due date.
- **State Changes**: `draft` -> `scheduled` -> `published`, then `pending` -> `submitted`.
- **Database Operations**: Update assignment state, log release and submission events.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Assignment and submissions are tracked in the database.

### BW-LMS-04: Faculty Grading and Grade Release
- **Trigger**: Faculty grades a student's submission.
- **Actor**: Faculty or TA.
- **Preconditions**: Submission is in `draft` state, faculty has access to grade it.
- **Step-by-step Execution Sequence**:
  1. Faculty grades the submission with a score and feedback.
  2. Grade is held in `draft` state until explicitly released by faculty.
  3. Faculty releases the grade, making it visible to the student.
- **State Changes**: `draft` -> `released`.
- **Database Operations**: Update grade status, log grading and release events.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Grade becomes visible to the student.

### BW-LMS-05: TA Grading and Faculty Grade Release
- **Trigger**: TA grades a student's submission.
- **Actor**: TA or Faculty.
- **Preconditions**: Submission is in `draft` state, TA has access to grade it.
- **Step-by-step Execution Sequence**:
  1. TA grades the submission with a score and feedback.
  2. Grade is held in `draft` state until explicitly released by faculty.
  3. Faculty reviews and releases the grade, making it visible to the student.
- **State Changes**: `draft` -> `released`.
- **Database Operations**: Update grade status, log grading and release events.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Grade becomes visible to the student.

## Composite Workflows (CW-LMS-01 and CW-LMS-02)

### CW-LMS-01: Assignment Publication and Submission
- **Trigger**: Faculty authorizes an assignment with a future release date or immediate due date.
- **Actor**: Faculty, Student.
- **Preconditions**: No specific conditions required.
- **Step-by-step Execution Sequence**:
  1. Faculty schedules the assignment with a future `release_date` or publishes it immediately.
  2. Students gain access to the published assignment before the due date.
  3. Students submit their work before or after the due date.
- **State Changes**: `draft` -> `scheduled` -> `published`, then `pending` -> `submitted`.
- **Database Operations**: Update assignment state, log release and submission events.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Assignment and submissions are tracked in the database.

### CW-LMS-02: Grading and Grade Release
- **Trigger**: Faculty or TA grades a student's submission.
- **Actor**: Faculty, TA.
- **Preconditions**: Submission is in `draft` state, faculty has access to grade it.
- **Step-by-step Execution Sequence**:
  1. Faculty or TA grades the submission with a score and feedback.
  2. Grade is held in `draft` state until explicitly released by faculty.
  3. Faculty reviews and releases the grade, making it visible to the student.
- **State Changes**: `draft` -> `released`.
- **Database Operations**: Update grade status, log grading and release events.
- **Error/Retry Behavior**: If background processing fails, retry mechanism is in place.
- **Postconditions**: Grade becomes visible to the student.

## Unresolved Policy Dependencies (Strictly [NEEDS CLARIFICATION])

### ISS‑LMS‑001: Late‑Submission Policy
- **Status:** `NEEDS CLARIFICATION`
- **Known:** `Submission.status` can represent `late`.
- **Unknown:** Whether late submissions are rejected, flagged, or overridable.

### ISS‑LMS‑002: TA Permissions (Announcements & Grading)
- **Status:** `NEEDS CLARIFICATION`
- **Known:** TA role exists.
- **Unknown:** Configurability of TA posting announcements and grading per course.

### ISS‑LMS‑003: Notification Delivery Channels
- **Status:** `NEEDS CLARIFICATION`
- **Known:** In‑app notification event log exists.
- **Unknown:** Whether email delivery is required.

### ISS‑LMS‑004: Observer Linkage Granularity
- **Status:** `NEEDS CLARIFICATION`
- **Known:** Observer entity defined.
- **Unknown:** Scope of linkage (student‑specific vs. course‑level).

### ISS‑LMS‑005: Resubmission Policy
- **Status:** `NEEDS CLARIFICATION`
- **Known:** `Submission.version` field present.
- **Unknown:** Allowed number of attempts and late‑resubmission handling.

### ISS‑LMS‑006: Post‑Release Grade Change Authority & Effects
- **Status:** `NEEDS CLARIFICATION`
- **Known:** `GradeAuditLog` required.
- **Unknown:** Who may edit grades after release and downstream effects.


### ISS-LMS-001: Late-Submission Policy
- **Baseline Constraint**: Strict `t <= t_due` enforcement; rejected with error after due date until override policy clarified.
  - [Confirmed by existing repository]

### ISS-LMS-002: TA Permissions for Announcements & Grading
- **Baseline Constraint**: Configurable course flags with `allow_ta_grading=True`, `allow_ta_announcements=False`; TA attribution always recorded.
  - [Required by official specification]

### ISS-LMS-003: Notification Delivery Channels
- **Baseline Constraint**: Transactional in-app outbox records; no hardcoded SMTP.
  - [Recommended design]

### ISS-LMS-004: Observer Linkage Granularity
- **Baseline Constraint**: Course-level linkage with strict prohibition of student data access.
  - [Confirmed by existing repository]

### ISS-LMS-005: Resubmission Policy
- **Baseline Constraint**: Single active submission attempt prior to due date.
  - [Recommended design]

### ISS-LMS-006: Post-Release Grade Change Authority & Audit Effects
- **Baseline Constraint**: Faculty-only edits with mandatory `GradeAuditLog` recording assessor, timestamp, previous score, new score, and reason.
  - [Confirmed by existing repository]

## Decision Labels

- [Confirmed by existing repository]: The decision is consistent with the current implementation in the codebase.
- [Required by official specification]: The decision is mandated by the official LMS specifications.
- [Recommended design]: The decision is a recommended approach based on best practices and industry standards.
- [Needs instructor clarification]: Further details or clarifications are needed from the instructors to finalize this decision.

This document provides a comprehensive overview of the workflow design for Fusion ERP LMS Course Management, ensuring strict role enforcement and scoped access control across various state transitions and workflows.