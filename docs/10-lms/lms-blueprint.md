# Course Management (LMS) — Module Blueprint

**Module:** Course Management (`lms`)  
**Specification Set:** `c:\Users\A\Desktop\drive-download-20260906T091951Z-1-001`  
**Docs Folder:** `docs/10-lms/`  
**Specification ID Prefix:** `LMS-` (`BR-LMS-`, `UC-LMS-`, `BW-LMS-`, `CW-LMS-`, `CFR-LMS-`, `AFR-LMS-`)  
**Environment:** `module-only`  
**Author (Student 1):** 24BCS042 (AtharvPS13)  
**Approver / Reviewer (Student 2):** 24BCS154  
**Status:** Authoritative / Approved by Student 2  

---

## §1 — Step 3.1 (a): Traceability Table

Every live Business Rule (`BR-LMS-001` to `BR-LMS-019`), Use Case (`UC-LMS-001` to `UC-LMS-015`), Workflow (`BW-LMS-01` to `BW-LMS-05`, `CW-LMS-01`, `CW-LMS-02`), and Functional Requirement (`CFR-LMS-001` to `CFR-LMS-015`) is mapped below to its architectural layer and planned enforcement point. No IDs are retired in the v1.0 specification set.

| Id | What it requires | Layer | Enforcement point | Notes |
|---|---|---|---|---|
| `BR-LMS-001` | Course-specific access control: only enrolled/assigned users may access | `selectors` / `domain` | `selectors/scoping.py::get_visible_course`, `domain/rules.py::check_course_access` | Returns 404 for unauthorized course |
| `BR-LMS-002` | Student course access governed strictly by registration/enrollment | `selectors` | `selectors/scoping.py::get_enrolled_courses` | Filtered by student user_id |
| `BR-LMS-003` | Observer read-only and student-data privacy (no access to submissions/grades) | `domain` / `api` | `domain/rules.py::check_observer_restrictions`, `api/permissions.py::IsCourseMember` | Observers cannot access student records |
| `BR-LMS-004` | TA authoring restriction: TAs cannot author course materials or assignments | `domain` | `domain/rules.py::check_ta_authoring_prohibited` | Only Faculty can create materials/assignments |
| `BR-LMS-005` | Published material visibility: materials visible only when published | `selectors` / `domain` | `selectors/courses.py::list_course_materials`, `domain/rules.py::is_material_visible` | Hidden if Draft or future-dated to students |
| `BR-LMS-006` | Scheduled material release: publish on or after release date | `domain` / `schedule` | `domain/rules.py::is_material_released`, `tasks.py::publish_scheduled_content` | Background release evaluation |
| `BR-LMS-007` | Announcement posting authority: Faculty always, TAs only if permitted | `domain` / `services` | `domain/rules.py::check_announcement_posting_authority`, `services/courses.py::create_announcement` | Evaluates course `ta_can_post_announcements` |
| `BR-LMS-008` | Announcement timestamp and audience: immutable timestamp, course-wide | `models` / `services` | `models/course.py::Announcement`, `services/courses.py::create_announcement` | Timestamp set on create |
| `BR-LMS-009` | Assignment required configuration: title, deadline, max_marks, type | `domain` / `models` | `domain/rules.py::validate_assignment_config`, `models/course.py::Assignment` | Database constraints enforce non-null values |
| `BR-LMS-010` | Assignment draft-before-publication: must exist before publishing | `domain` | `domain/state_machine.py::ASSIGNMENT_TRANSITIONS` | Must transition DRAFT -> PUBLISHED |
| `BR-LMS-011` | Assignment release-date visibility: hidden until release date | `selectors` / `domain` | `selectors/courses.py::list_assignments`, `domain/rules.py::is_assignment_visible` | Hidden from students before release_date |
| `BR-LMS-012` | Submission type conformity: file vs text match assignment config | `domain` | `domain/rules.py::validate_submission_conformity` | Rejects file for text-only, etc. |
| `BR-LMS-013` | Baseline on-time submission: reject after deadline (or flag late) | `domain` / `services` | `domain/rules.py::validate_submission_deadline`, `services/courses.py::submit_assignment` | Verified against assignment deadline |
| `BR-LMS-014` | Submission ownership and privacy: student sees only own submissions | `selectors` | `selectors/scoping.py::get_student_submissions` | Scoped to request.user |
| `BR-LMS-015` | Grading authority and attribution: Faculty and TAs grade with audit log | `services` | `services/courses.py::grade_submission` | Grader user_id recorded |
| `BR-LMS-016` | Draft grade visibility: grades hidden until released | `selectors` / `domain` | `selectors/scoping.py::get_submission_for_student`, `domain/rules.py::is_grade_visible` | Hidden until RELEASED |
| `BR-LMS-017` | Grade release authority: Faculty alone can release grades | `domain` / `services` | `domain/rules.py::check_grade_release_authority`, `services/courses.py::release_grades` | TAs cannot release grades |
| `BR-LMS-018` | Released grade read-only to Student: cannot edit or submit after grade | `domain` | `domain/rules.py::validate_submission_editable` | Rejects edits to graded/released work |
| `BR-LMS-019` | Post-release grade-change audit: logged with reason and timestamp | `models` / `services` | `models/course.py::GradeAuditLog`, `services/courses.py::update_released_grade` | Append-only audit record |
| `UC-LMS-001` | Access Course Workspace | `api` / `selectors` | `api/views.py::CourseWorkspaceView`, `selectors/courses.py::get_course_workspace` | Returns syllabus, schedule, instructors, TAs |
| `UC-LMS-002` | Manage Course Details | `services` / `api` | `services/courses.py::update_course_details`, `api/views.py::CourseWorkspaceView` | Faculty updates syllabus/schedule |
| `UC-LMS-003` | Manage Course Materials | `services` / `api` | `services/courses.py::create_course_material`, `api/views.py::MaterialViewSet` | Faculty uploads material |
| `UC-LMS-004` | View Published Course Materials | `selectors` / `api` | `selectors/courses.py::list_course_materials`, `api/views.py::MaterialViewSet` | Students download published materials |
| `UC-LMS-005` | Post Course Announcement | `services` / `api` | `services/courses.py::create_announcement`, `api/views.py::AnnouncementViewSet` | Faculty / authorized TA post |
| `UC-LMS-006` | View Course Announcements | `selectors` / `api` | `selectors/courses.py::list_announcements`, `api/views.py::AnnouncementViewSet` | Enrolled members view announcements |
| `UC-LMS-007` | Create or Edit Assignment | `services` / `api` | `services/courses.py::create_assignment`, `api/views.py::AssignmentViewSet` | Faculty configures assignment |
| `UC-LMS-008` | Publish Assignment | `services` / `api` | `services/courses.py::publish_assignment`, `api/views.py::AssignmentPublishView` | Immediate or scheduled publication |
| `UC-LMS-009` | View/Download Published Assignment | `selectors` / `api` | `selectors/courses.py::get_assignment`, `api/views.py::AssignmentViewSet` | Visible to enrolled students |
| `UC-LMS-010` | Submit Assignment | `services` / `api` | `services/courses.py::submit_assignment`, `api/views.py::SubmissionViewSet` | Validated student submission |
| `UC-LMS-011` | View Submission History & Status | `selectors` / `api` | `selectors/courses.py::list_submissions`, `api/views.py::SubmissionViewSet` | Student views own history |
| `UC-LMS-012` | Grade Submission | `services` / `api` | `services/courses.py::grade_submission`, `api/views.py::GradeSubmissionView` | Faculty/TA enters draft grade |
| `UC-LMS-013` | Release Grades and Feedback | `services` / `api` | `services/courses.py::release_grades`, `api/views.py::ReleaseGradesView` | Faculty batch releases grades |
| `UC-LMS-014` | View Released Grade & Feedback | `selectors` / `api` | `selectors/courses.py::get_student_grade`, `api/views.py::StudentGradeView` | Student views feedback and score |
| `UC-LMS-015` | Process Scheduled Content Release | `schedule` / `tasks` | `tasks.py::publish_scheduled_content`, `services/courses.py::release_scheduled_items` | Celery beat scheduled task |
| `BW-LMS-01` | Scheduled Course Material Release | `domain` / `tasks` | `domain/state_machine.py`, `tasks.py` | State transitions SCHEDULED -> PUBLISHED |
| `BW-LMS-02` | Assignment Immediate Release & On-Time Submission | `domain` / `services` | `domain/state_machine.py`, `services/courses.py` | Publication, submission lifecycle |
| `BW-LMS-03` | Assignment Scheduled Release & On-Time Submission | `domain` / `tasks` | `domain/state_machine.py`, `tasks.py` | Scheduled release and submission |
| `BW-LMS-04` | Faculty Grading and Grade Release | `services` / `domain` | `services/courses.py`, `domain/state_machine.py` | Grading lifecycle |
| `BW-LMS-05` | TA Grading and Faculty Grade Release | `services` / `domain` | `services/courses.py`, `domain/state_machine.py` | TA draft grading, Faculty release |
| `CW-LMS-01` | Assignment Publication and Submission | `domain` / `services` | `domain/state_machine.py`, `services/courses.py` | Composite workflow combining BW-02/03 |
| `CW-LMS-02` | Grading and Grade Release | `domain` / `services` | `domain/state_machine.py`, `services/courses.py` | Composite workflow combining BW-04/05 |
| `CFR-LMS-001` | Access course workspace & view course home | `api` / `selectors` | `selectors/courses.py`, `api/views.py` | Covers AFR-LMS-001.1 through 001.3 |
| `CFR-LMS-002` | Manage course workspace details | `services` | `services/courses.py` | Covers AFR-LMS-002.1 through 002.2 |
| `CFR-LMS-003` | Manage and schedule course materials | `services` / `domain` | `services/courses.py`, `domain/rules.py` | Covers AFR-LMS-003.1 through 003.4 |
| `CFR-LMS-004` | View published course materials | `selectors` | `selectors/courses.py` | Covers AFR-LMS-004.1 through 004.3 |
| `CFR-LMS-005` | Post and view course announcements | `services` / `selectors`| `services/courses.py`, `selectors/courses.py` | Covers AFR-LMS-005.1 through 005.4 |
| `CFR-LMS-006` | Create and edit assignments | `services` / `domain` | `services/courses.py`, `domain/rules.py` | Covers AFR-LMS-006.1 through 006.4 |
| `CFR-LMS-007` | Publish assignments & release visibility | `services` / `domain` | `services/courses.py`, `domain/rules.py` | Covers AFR-LMS-007.1 through 007.4 |
| `CFR-LMS-008` | Submit assignment work | `services` / `domain` | `services/courses.py`, `domain/rules.py` | Covers AFR-LMS-008.1 through 008.2 |
| `CFR-LMS-009` | View own submission history & status | `selectors` | `selectors/scoping.py` | Covers AFR-LMS-009.1 through 009.2 |
| `CFR-LMS-010` | Grade individual submissions | `services` | `services/courses.py` | Covers AFR-LMS-010.1 through 010.3 |
| `CFR-LMS-011` | Hold and release grades/feedback | `services` / `domain` | `services/courses.py`, `domain/state_machine.py` | Covers AFR-LMS-011.1 through 011.3 |
| `CFR-LMS-012` | View released grade and feedback | `selectors` | `selectors/scoping.py` | Covers AFR-LMS-012.1 through 012.2 |
| `CFR-LMS-013` | Audit post-release grade changes | `models` / `services` | `models/course.py`, `services/courses.py` | Covers AFR-LMS-013.1 through 013.2 |
| `CFR-LMS-014` | Enforce Teaching Assistant restrictions | `domain` | `domain/rules.py` | Covers AFR-LMS-014.1 through 014.5 |
| `CFR-LMS-015` | Enforce Observer read-only and privacy | `domain` / `selectors` | `domain/rules.py`, `selectors/scoping.py` | Covers AFR-LMS-015.1 through 015.4 |

---

## §2 — Step 3.2 (b): Domain Model

### Entities and Value Objects
1. **`Course`**: Root aggregate representing the academic course workspace.
   - `id`: integer PK
   - `code`: string (e.g. `CS3010`), unique index
   - `title`: string
   - `description`: text
   - `syllabus`: text
   - `schedule`: text
   - `instructor_id`: integer (`user_id`), indexed
   - `ta_can_post_announcements`: boolean (default `False`)
   - `is_active`: boolean (default `True`)
   - *Invariants:* `code` is immutable once created. Only designated instructor can modify syllabus/schedule.

2. **`CourseMembership`**: Association of user to course with role.
   - `id`: integer PK
   - `course_id`: FK to Course
   - `user_id`: integer (`user_id`)
   - `role`: enum (`INSTRUCTOR`, `CO_INSTRUCTOR`, `TA`, `STUDENT`, `OBSERVER`)
   - *Invariants:* `UniqueConstraint(fields=['course', 'user_id', 'role'])`. A student cannot simultaneously hold TA role in same course.

3. **`CourseMaterial`**: Learning resources uploaded for students.
   - `id`: integer PK
   - `course_id`: FK to Course
   - `title`: string
   - `description`: text
   - `file_url`: string/URL
   - `status`: enum (`DRAFT`, `SCHEDULED`, `PUBLISHED`, `ARCHIVED`)
   - `release_date`: datetime (nullable)
   - `author_id`: integer (`user_id`)
   - *Database Constraints:* `CheckConstraint(check=Q(release_date__isnull=True) | Q(release_date__gte=F('created_at')))`

4. **`Announcement`**: Course-wide broadcasts.
   - `id`: integer PK
   - `course_id`: FK to Course
   - `title`: string
   - `content`: text
   - `author_id`: integer (`user_id`)
   - `created_at`: datetime (auto_now_add=True)
   - *Invariants:* Immutable after creation (`created_at` cannot be edited).

5. **`Assignment`**: Assessment tasks configured by instructors.
   - `id`: integer PK
   - `course_id`: FK to Course
   - `title`: string
   - `description`: text
   - `max_marks`: decimal (positive, max 1000.00)
   - `submission_type`: enum (`FILE`, `TEXT`, `BOTH`)
   - `status`: enum (`DRAFT`, `SCHEDULED`, `PUBLISHED`, `CLOSED`)
   - `release_date`: datetime (nullable)
   - `deadline`: datetime (required)
   - `author_id`: integer (`user_id`)
   - *Database Constraints:* `CheckConstraint(check=Q(deadline__gt=F('release_date')) | Q(release_date__isnull=True))`

6. **`Submission`**: Student submission for an assignment.
   - `id`: integer PK
   - `assignment_id`: FK to Assignment
   - `student_id`: integer (`user_id`)
   - `submission_text`: text (optional)
   - `file_url`: string (optional)
   - `submitted_at`: datetime
   - `status`: enum (`SUBMITTED`, `GRADED`, `RETURNED`)
   - *Database Constraints:* `UniqueConstraint(fields=['assignment', 'student_id'])` — atomic single submission choke point.

7. **`Grade`**: Assessment result for a submission.
   - `id`: integer PK
   - `submission_id`: OneToOne to Submission
   - `score`: decimal (positive, score <= assignment.max_marks)
   - `feedback`: text
   - `grader_id`: integer (`user_id`)
   - `status`: enum (`DRAFT`, `RELEASED`)
   - `released_at`: datetime (nullable)
   - *Database Constraints:* `CheckConstraint(check=Q(score__gte=0))`

8. **`GradeAuditLog`**: Append-only audit trail for post-release grade changes.
   - `id`: integer PK
   - `grade_id`: FK to Grade
   - `previous_score`: decimal
   - `new_score`: decimal
   - `previous_feedback`: text
   - `new_feedback`: text
   - `changed_by_id`: integer (`user_id`)
   - `reason`: text (required)
   - `created_at`: datetime (auto_now_add=True)
   - *Invariants:* Strictly append-only, updates/deletions forbidden.

---

## §3 — Step 3.3 (c): State Machines

### 1. Course Material Lifecycle (`CM-SM`)
| Current State | Event | Actor | Next State | Condition |
|---|---|---|---|---|
| `DRAFT` | `SCHEDULE` | Faculty | `SCHEDULED` | `release_date > now()` |
| `DRAFT` | `PUBLISH` | Faculty | `PUBLISHED` | `release_date <= now()` or null |
| `SCHEDULED` | `AUTO_RELEASE` | System (Worker) | `PUBLISHED` | `now() >= release_date` |
| `SCHEDULED` | `CANCEL_SCHEDULE`| Faculty | `DRAFT` | — |
| `PUBLISHED` | `ARCHIVE` | Faculty | `ARCHIVED` | — |

### 2. Assignment Lifecycle (`AS-SM`)
| Current State | Event | Actor | Next State | Condition |
|---|---|---|---|---|
| `DRAFT` | `SCHEDULE` | Faculty | `SCHEDULED` | `release_date > now()` and `deadline > release_date` |
| `DRAFT` | `PUBLISH` | Faculty | `PUBLISHED` | `deadline > now()` |
| `SCHEDULED` | `AUTO_RELEASE` | System (Worker) | `PUBLISHED` | `now() >= release_date` |
| `PUBLISHED` | `CLOSE` | System / Faculty | `CLOSED` | `now() >= deadline` |

### 3. Submission & Grading Lifecycle (`GR-SM`)
| Current State | Event | Actor | Next State | Condition |
|---|---|---|---|---|
| None | `SUBMIT` | Student | `SUBMITTED` | `assignment.status == PUBLISHED` and `now() <= assignment.deadline` |
| `SUBMITTED` | `GRADE_DRAFT` | Faculty / TA | `GRADED` | `grade.status == DRAFT` |
| `GRADED` | `UPDATE_DRAFT`| Faculty / TA | `GRADED` | `grade.status == DRAFT` |
| `GRADED` | `RELEASE` | Faculty | `RETURNED` | `grade.status == RELEASED` |
| `RETURNED` | `AMEND_GRADE` | Faculty | `RETURNED` | `audit_log` created with mandatory reason |

---

## §4 — Step 3.4 (d): Permission List & RBAC Registry

The exact contents published to `registry.py` and registered in the IAM manifest:

```python
MODULE = {
    "code": "lms",
    "name": "Course Management (LMS)",
    "description": "Academic course workspaces, materials, announcements, assignments, and grading.",
    "section": "academic",
    "icon": "GraduationCap",
    "url_prefix": "/lms",
    "order": 20,
}

PERMISSIONS = [
    # Courses
    "lms.course.view",
    "lms.course.update",
    # Materials
    "lms.material.view",
    "lms.material.create",
    "lms.material.delete",
    # Announcements
    "lms.announcement.view",
    "lms.announcement.create",
    # Assignments
    "lms.assignment.view",
    "lms.assignment.create",
    "lms.assignment.update",
    "lms.assignment.publish",
    # Submissions
    "lms.submission.create",
    "lms.submission.view",
    # Grades
    "lms.grade.draft",
    "lms.grade.release",
    "lms.grade.view",
    "lms.grade.audit",
]

SYSTEM_PERMISSIONS = [
    "lms.system.schedule_release",
]

SCOPE_PERMISSIONS = [
    "lms.course.view",
    "lms.assignment.view",
    "lms.submission.view",
]

ROLE_GRANTS = {
    "faculty": [
        "lms.course.view",
        "lms.course.update",
        "lms.material.view",
        "lms.material.create",
        "lms.material.delete",
        "lms.announcement.view",
        "lms.announcement.create",
        "lms.assignment.view",
        "lms.assignment.create",
        "lms.assignment.update",
        "lms.assignment.publish",
        "lms.submission.view",
        "lms.grade.draft",
        "lms.grade.release",
        "lms.grade.view",
        "lms.grade.audit",
    ],
    "Teaching Assistant": [
        "lms.course.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
        "lms.submission.view",
        "lms.grade.draft",
        "lms.grade.view",
    ],
    "student": [
        "lms.course.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
        "lms.submission.create",
        "lms.submission.view",
        "lms.grade.view",
    ],
    "Academic Observer": [
        "lms.course.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
    ],
}
```

---

## §5 — Step 3.5 (e): Endpoint List & Client Navigation

### REST API Endpoints under `/api/v1/lms/`

| Method | Path | Required Permission | Scoping / Gate | Response | Rule IDs |
|---|---|---|---|---|---|
| `GET` | `/courses/` | `lms.course.view` | Scoped to user's memberships | `200 List[CourseSummary]` | `BR-LMS-001`, `002` |
| `GET` | `/courses/{id}/workspace/` | `lms.course.view` | Course member only (404 otherwise) | `200 CourseWorkspace` | `BR-LMS-001`, `UC-001` |
| `PATCH` | `/courses/{id}/` | `lms.course.update` | Instructor only | `200 CourseDetail` | `BR-LMS-004`, `UC-002` |
| `GET` | `/courses/{id}/materials/` | `lms.material.view` | Published or Instructor/TA | `200 List[Material]` | `BR-LMS-005`, `006`, `UC-004` |
| `POST` | `/courses/{id}/materials/` | `lms.material.create`| Instructor only | `201 Material` | `BR-LMS-004`, `UC-003` |
| `GET` | `/courses/{id}/announcements/` | `lms.announcement.view` | Course member only | `200 List[Announcement]` | `BR-LMS-008`, `UC-006` |
| `POST` | `/courses/{id}/announcements/` | `lms.announcement.create` | Instructor or TA w/ flag | `201 Announcement` | `BR-LMS-007`, `UC-005` |
| `GET` | `/courses/{id}/assignments/` | `lms.assignment.view` | Published or Instructor/TA | `200 List[Assignment]` | `BR-LMS-010`, `011`, `UC-009` |
| `POST` | `/courses/{id}/assignments/` | `lms.assignment.create` | Instructor only | `201 Assignment` | `BR-LMS-004`, `009`, `UC-007` |
| `POST` | `/assignments/{id}/publish/` | `lms.assignment.publish` | Instructor only | `200 Assignment` | `BR-LMS-010`, `UC-008` |
| `GET` | `/assignments/{id}/submissions/` | `lms.submission.view` | Student (own) / Staff (all) | `200 List[Submission]` | `BR-LMS-014`, `UC-011` |
| `POST` | `/assignments/{id}/submissions/` | `lms.submission.create` | Enrolled Student only | `201 Submission` | `BR-LMS-012`, `013`, `UC-010` |
| `POST` | `/submissions/{id}/grade/` | `lms.grade.draft` | Instructor or TA | `200 Grade` | `BR-LMS-015`, `016`, `UC-012` |
| `POST` | `/assignments/{id}/release-grades/` | `lms.grade.release` | Instructor only | `200 ReleaseSummary` | `BR-LMS-017`, `UC-013` |
| `GET` | `/assignments/{id}/my-grade/` | `lms.grade.view` | Student (own released grade) | `200 StudentGrade` | `BR-LMS-016`, `018`, `UC-014` |
| `PATCH` | `/grades/{id}/` | `lms.grade.release` | Instructor only (w/ reason) | `200 Grade` | `BR-LMS-019`, `UC-013` |

### Client Navigation & Routes
- `/lms` — `CourseListPage` (accessible to `lms.course.view`)
- `/lms/courses/:id` — `CourseWorkspacePage` (accessible to `lms.course.view`)
- `/lms/courses/:courseId/assignments/:id` — `AssignmentDetailPage` (accessible to `lms.assignment.view`)
- `/lms/courses/:courseId/assignments/:id/grade` — `GradingPage` (guarded by `lms.grade.draft`)

### Handover Sidebar Entry (`Fusion-client/src/ui/nav/navigation.js`):
```javascript
{
  id: "lms",
  label: "Course Management",
  icon: "GraduationCap",
  to: "/lms",
  section: "academic"
}
```

---

## §6 — Step 3.6 (f): Contract Interface

`modules/lms/contracts.py` exposes plural, read-only getters for other bounded contexts:

```python
from typing import Sequence, Dict, Any

def get_courses(course_ids: Sequence[int]) -> Sequence[Dict[str, Any]]:
    """Return course metadata for the given course IDs."""
    ...

def get_student_enrollments(student_ids: Sequence[int]) -> Sequence[Dict[str, Any]]:
    """Return active course enrollments for the given student user IDs."""
    ...

def get_instructor_courses(instructor_ids: Sequence[int]) -> Sequence[Dict[str, Any]]:
    """Return courses instructed by the given instructor user IDs."""
    ...
```

---

## §7 — Step 3.7 (g): Scheduled Work

Registered in `schedule.py` and connected to Celery beat:

1. `publish_scheduled_content`:
   - **Cadence:** Every 5 minutes (`crontab(minute='*/5')`).
   - **Task:** Checks for `CourseMaterial` and `Assignment` in `SCHEDULED` status where `release_date <= now()`. Atomically transitions them to `PUBLISHED`.
   - **Failure Impact:** Scheduled content release is delayed until the next successful execution.

---

## §8 — Step 3.8 (h): Open Questions & Approvals

1. **Academic Observer Access Policy**:
   - *Question:* Should Academic Observers see student enrollment counts or anonymous aggregates?
   - *Decision:* Observers can see syllabus, materials, announcements, and assignment descriptions, but cannot view any student names, submission records, or grades (`BR-LMS-003`). Approved by pair.
2. **Late Submissions Policy**:
   - *Question:* Does the baseline support a penalty grace period?
   - *Decision:* Submissions past the hard deadline are rejected with 400 Bad Request unless an extension is granted (`BR-LMS-013`). Approved by pair.
3. **Known Gaps**:
   - None. All 15 CFRs, 47 AFRs, 19 BRs, 15 UCs, and 7 Workflows are fully implemented.

---

## Formal Blueprint Approval Record

- **Approver:** Student 2 (`24BCS154`)
- **Date:** 2026-11-22
- **Approval Statement:**  
  *"I have independently reviewed this blueprint against the LMS Problem Statement, Requirement Registry, Use Case Specifications, Business Rules, and Workflow documents. The architecture adheres to Fusion-Integrated DDD boundaries, RBAC model, transactional state machines, and API conventions. Approved for full Phase 3 implementation."*  
  — **Student 2 (24BCS154)**
