---
note: >
  Domain model for the LMS (Course Management) module. All entities, fields,
  constraints and indexes for `modules/lms`.
---

# LMS Domain Model

Companion: [state machine](lms-state-machine.md) (transition tables).

---

## Shape

```
Course (ERP, read-only projection)
  │
  ├──* CourseMaterial ─── user_id (no FK — crosses to IAM)
  ├──* Announcement ─── user_id
  └──* Assignment ─── user_id
           │
           └──* Submission (1 per student per attempt) ─── user_id
                    │
                    └── 1 Grade ─── user_id (graded_by, released_by)
                          │
                          └──* GradeAudit (append-only)
```

Every `user_id` is a **plain integer**, never a foreign key — it references IAM's
`erp_user_id` across a boundary (ADR-0013). Reads go through
`fusion_auth` / IAM client. No cross-module FKs.

---

## Entities

### CourseMaterial

A course material (file, link, or note) uploaded by Faculty.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `course_id` | int (indexed) | ERP course, no FK |
| `user_id` | int (indexed) | uploader (UserScopedModel) |
| `title` | varchar(255) | |
| `material_type` | enum(file, link, note) | |
| `content` | text | link URL or note text |
| `file` | FileField (optional) | stored under `lms/materials/` |
| `section` | varchar(100) | module/week grouping |
| `status` | enum(draft, published, scheduled) | default draft |
| `release_at` | datetime (nullable) | future release time |
| `created_at`, `updated_at` | datetime | TimeStampedModel |

**Indexes:** `(course_id, status, release_at)`

### Announcement

A course-wide announcement posted by Faculty or permitted TA.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `course_id` | int (indexed) | |
| `user_id` | int (indexed) | author (UserScopedModel) |
| `content` | text | |
| `is_pinned` | bool | default False |
| `created_at`, `updated_at` | datetime | TimeStampedModel |

**Indexes:** `(course_id, -created_at)`

### Assignment

A course assignment with due date, submission type, and points.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `course_id` | int (indexed) | |
| `user_id` | int (indexed) | creator (UserScopedModel) |
| `title` | varchar(255) | |
| `instructions` | text | |
| `due_at` | datetime | |
| `submission_type` | enum(file, text, link) | |
| `points_possible` | positive int | ≥ 0 |
| `status` | enum(draft, published, scheduled, available) | default draft |
| `release_at` | datetime (nullable) | future release time |
| `max_attempts` | positive int | default 1 |
| `created_at`, `updated_at` | datetime | TimeStampedModel |

**Constraints:** `CheckConstraint(points_possible >= 0)`
**Indexes:** `(course_id, status)`

### Submission

A student's submission for an assignment.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `assignment` | FK → Assignment | same module, CASCADE |
| `user_id` | int (indexed) | student (UserScopedModel) |
| `submission_type` | enum(file, text, link) | |
| `content` | text | |
| `file` | FileField (optional) | stored under `lms/submissions/` |
| `submitted_at` | datetime | auto_now_add |
| `status` | enum(submitted, late, missing) | default submitted |
| `is_late` | bool | default False |
| `attempt_number` | positive int | default 1 |

**Constraints:** `UniqueConstraint(assignment, user_id, attempt_number)`
**Indexes:** `(assignment, user_id)`

### Grade

A grade for a submission (1:1).

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `submission` | OneToOne → Submission | |
| `user_id` | int (indexed) | student (UserScopedModel) |
| `points` | positive int (nullable) | |
| `feedback` | text | |
| `status` | enum(draft, released) | default draft |
| `graded_by` | int | grader's user_id |
| `graded_at` | datetime | auto_now_add |
| `released_by` | int (nullable) | releaser's user_id |
| `released_at` | datetime (nullable) | |
| `created_at`, `updated_at` | datetime | TimeStampedModel |

**Constraints:** `CheckConstraint(points is null or points >= 0)`

### GradeAudit

Append-only audit log for post-release grade changes.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `grade` | FK → Grade | CASCADE |
| `changed_by` | int (indexed) | |
| `changed_at` | datetime | auto_now_add |
| `old_points`, `new_points` | positive int (nullable) | |
| `old_feedback`, `new_feedback` | text | |
| `reason` | text | |

**Ordering:** `-changed_at`

---

## Invariants

- A submission's type must match the assignment's configured `submission_type` (BR-LMS-012).
- A grade cannot exceed `assignment.points_possible` (BR-LMS-015).
- Released grades are read-only to students (BR-LMS-018).
- Post-release grade changes create an audit record (BR-LMS-019).
- No cross-module foreign keys (ADR-0013): `course_id` and `user_id` are plain ints.