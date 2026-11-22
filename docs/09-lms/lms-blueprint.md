# Learning Management System (LMS - Course Management) Module Blueprint

**Module Code**: `lms`  
**Base Path**: `/lms`  
**Specification Set**: `01_LMS_CourseManagement_Problem_Statement_v1.0_UNCHANGED.docx` through `06_LMS_CourseManagement_Traceability_Matrix_v1.0_SYNCHRONIZED.xlsx`  
**Standard**: Conforming to `docs/03-platform/platform-structure.md`, `definition-of-done.md`, and `modules/placement` reference architecture.  
**Approver**: Student 2 (K Lasya Reddy, 24BCS105), written blueprint approval recorded on 10 November 2026.

---

## 1. Domain Summary & Functional Scope

The LMS (Course Management) module provides a unified academic workspace for course offerings:
1. **Course Workspace**: Dedicated hub displaying course overview, syllabus, schedule, instructors, and teaching assistants. Enforces course-level role authorization (`BR-LMS-001`).
2. **Course Materials**: Hierarchical curriculum organization (modules, weekly sections), multi-format materials (files, links, lecture notes), draft and scheduled releases (`BR-LMS-005`, `BR-LMS-006`).
3. **Course Announcements**: Timestamped course notice board with role-scoped write enforcement and reverse-chronological feeds (`BR-LMS-007`, `BR-LMS-008`).
4. **Assignments & Deadlines**: Multi-format assignments (file upload, text entry, URL submission), points possible, due dates, closing cutoffs, and individualized deadline extensions (`BR-LMS-009` through `BR-LMS-012`).
5. **Student Submissions**: Submissions with attempts, format validation, on-time / late classification, and immutability once graded (`BR-LMS-013`, `BR-LMS-014`).
6. **Grading & Evaluation**: Scoring against rubric points, initial draft state, faculty grade release, student view restriction, and post-release audit trails (`BR-LMS-015` through `BR-LMS-019`).

---

## 2. Data Boundaries & Platform Architecture (ADR-0013)

- **No Foreign Keys to IAM or ERP**: All user references are stored as integer user IDs (`created_by_user_id`, `student_user_id`, `graded_by_user_id`, `user_id`).
- **Directory Contract Integration**: User identity, names, and emails are resolved via `modules.directory.contracts.get_users` in batched plural requests (`contracts_are_plural`).
- **Layering & Isolation**: `modules.lms.domain` contains pure Python models, enums, and validators. It does not import Django, DRF, or Celery.

---

## 3. RBAC, Registry & Permissions

### Permissions Declared:
- `lms.course.view`: View enrolled/assigned course workspace
- `lms.course.manage`: Configure course workspace details and publish state
- `lms.material.view`: Browse published materials
- `lms.material.manage`: Create, edit, and publish materials
- `lms.announcement.view`: View course announcements
- `lms.announcement.manage`: Post course announcements
- `lms.assignment.view`: View course assignments
- `lms.assignment.manage`: Create, edit, and publish assignments
- `lms.deadline.view`: View assignment deadlines and extension status
- `lms.deadline.manage`: Grant individual deadline extensions
- `lms.submission.view`: View assignment submissions
- `lms.submission.submit`: Submit student assignment solutions
- `lms.grade.view`: View released grades
- `lms.grade.grade`: Evaluate student submissions and release grades

### Role Grants Mapping (`ROLE_GRANTS`):
- `faculty`: Holds all `lms.*` permissions.
- `ta`: Holds `lms.course.view`, `lms.material.view`, `lms.announcement.view`, `lms.announcement.manage`, `lms.assignment.view`, `lms.deadline.view`, `lms.submission.view`, `lms.grade.view`, `lms.grade.grade`.
- `student`: Holds `lms.course.view`, `lms.material.view`, `lms.announcement.view`, `lms.assignment.view`, `lms.deadline.view`, `lms.submission.submit`, `lms.submission.view`, `lms.grade.view`.

---

## 4. API Endpoints

- `GET /api/v1/lms/courses/`: List accessible courses for principal
- `GET /api/v1/lms/courses/{code}/`: Course workspace detail
- `PATCH /api/v1/lms/courses/{code}/`: Update course workspace (Faculty only)
- `GET /api/v1/lms/courses/{code}/materials/`: List course materials
- `POST /api/v1/lms/courses/{code}/materials/`: Create material (Faculty only)
- `GET /api/v1/lms/courses/{code}/announcements/`: List course announcements
- `POST /api/v1/lms/courses/{code}/announcements/`: Post announcement (Faculty / authorized TA)
- `GET /api/v1/lms/courses/{code}/assignments/`: List course assignments
- `POST /api/v1/lms/courses/{code}/assignments/`: Create assignment (Faculty only)
- `POST /api/v1/lms/courses/{code}/assignments/{id}/submissions/`: Submit solution (Student)
- `POST /api/v1/lms/courses/{code}/assignments/{id}/grades/`: Evaluate submission (Faculty / TA)
- `POST /api/v1/lms/courses/{code}/assignments/{id}/release-grades/`: Release grades to students (Faculty only)

---

## 5. Scheduled Tasks & Celery

- `modules.lms.tasks.release_scheduled_materials_task`: Automated hourly release of scheduled materials whose release time has passed.
- Registered in `config/celery.py` under `app.conf.beat_schedule`.

---

## 6. Fusion-client Navigation Entry

```javascript
{
  id: "lms",
  label: "Course Management",
  icon: "BookOpen",
  to: "/lms",
  section: "Academics"
}
```

---

## 7. Approval Record

- **Blueprint Version**: 1.0
- **Approver**: K Lasya Reddy (24BCS105), Student 2
- **Approval Date**: 10 November 2026
- **Status**: Formally Approved in Writing
