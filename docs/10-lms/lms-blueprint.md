# LMS (Course Management) — Blueprint

**Module code:** `lms`
**Spec folder:** `C:\Users\sange\Downloads\3-LMS`
**Environment:** `module-only`
**Docs folder:** `docs/10-lms/`
**Status:** Approved by Student 2 (written). Proceeding to Phase 3.

---

## Step 3.1 (a) — Traceability table

### Business rules (19 live)

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-LMS-001 | Course-specific access control | selectors/scoping.py | `scoping.course_for(user, course_id)` → 404 if not linked | |
| BR-LMS-002 | Student access from existing registration data | selectors/scoping.py | registration data is authority; no redefinition | |
| BR-LMS-003 | Observer read-only, no student data | selectors/scoping.py + api/views.py | Observer queryset excludes submissions/grades | |
| BR-LMS-004 | TA authoring restriction | api/permissions.py + services/ | TA denied create/edit assignments/materials/structure | |
| BR-LMS-005 | Published material visibility | selectors/ + models/Material | `is_published=True` filter | |
| BR-LMS-006 | Scheduled material release | services/ + schedule.py | `release_at <= now` guard; Celery beat triggers | |
| BR-LMS-007 | Announcement posting authority | api/views.py + services/ | Faculty always; TA only if permitted | |
| BR-LMS-008 | Announcement timestamp + audience | models/Announcement + api/ | timestamped, course-wide visibility | |
| BR-LMS-009 | Assignment required config | serializers + domain/ | validate due_date, instructions, submission_type, points | |
| BR-LMS-010 | Draft before publication | models/Assignment + services/ | status starts Draft; publish action required | |
| BR-LMS-011 | Release-date visibility | selectors/ + services/ | withhold until release_at | |
| BR-LMS-012 | Submission-type conformity | serializers + domain/ | validate against assignment.submission_type | |
| BR-LMS-013 | Baseline on-time submission | services/ + domain/ | accept if submitted_at <= due_date; late policy = admin-overridable (resolved) | Resolved: admin-overridable |
| BR-LMS-014 | Submission ownership/privacy | selectors/scoping.py | student sees own only | |
| BR-LMS-015 | Grading authority + attribution | services/ + models/Grade | Faculty/TA course role; record grader identity | |
| BR-LMS-016 | Draft grade visibility | selectors/ + api/ | Student sees only Released grades | |
| BR-LMS-017 | Grade release authority | api/views.py + services/ | Faculty only (TA cannot release) | |
| BR-LMS-018 | Released grade read-only to Student | api/serializers.py | Student view is read-only | |
| BR-LMS-019 | Post-release grade-change audit | models/GradeAudit + services/ | log actor + timestamp on any change to released grade | Resolved: only instructor (Faculty) may change |

### Use cases (15 live)

| Id | What it requires | Layer | Enforcement point (planned) |
|---|---|---|---|
| UC-LMS-001 | Access course workspace | selectors/scoping.py + api/views.py | course-specific access check → 404 |
| UC-LMS-002 | Manage course details | api/views.py + services/ | Faculty authorization |
| UC-LMS-003 | Manage course materials | api/views.py + services/ | Faculty auth; material state transitions |
| UC-LMS-004 | View published materials | selectors/ + api/ | published filter + scoping |
| UC-LMS-005 | Post announcement | api/views.py + services/ | posting authority check |
| UC-LMS-006 | View announcements | selectors/ + api/ | course-wide, timestamped |
| UC-LMS-007 | Create/edit assignment | api/views.py + services/ | Faculty auth; required config validation |
| UC-LMS-008 | Publish assignment | services/ + domain/ | draft→published; release date handling |
| UC-LMS-009 | View/download published assignment | selectors/ + api/ | release-date visibility |
| UC-LMS-010 | Submit assignment | services/ + domain/ | type conformity + on-time check |
| UC-LMS-011 | View submission history/status | selectors/ + api/ | own data only |
| UC-LMS-012 | Grade submission | services/ + domain/ | grading authority + attribution + audit |
| UC-LMS-013 | Release grades/feedback | services/ + api/ | Faculty only |
| UC-LMS-014 | View released grade/feedback | selectors/ + api/ | read-only, own data |
| UC-LMS-015 | Process scheduled content release | schedule.py + tasks.py + services/ | Celery beat triggers release |

### Workflows (7 live)

| Id | Type | What it requires | Layer | Enforcement point |
|---|---|---|---|---|
| BW-LMS-01 | Basis | Scheduled material release | services/ + schedule.py | Material Draft/Scheduled → Published |
| BW-LMS-02 | Basis | Assignment immediate release + on-time submission | services/ + domain/ | Draft → Available → Submitted |
| BW-LMS-03 | Basis | Assignment scheduled release + on-time submission | services/ + schedule.py | Draft → Scheduled → Available → Submitted |
| BW-LMS-04 | Basis | Faculty grading + grade release | services/ + domain/ | Submitted → Graded(Draft) → Released |
| BW-LMS-05 | Basis | TA grading + Faculty grade release | services/ + domain/ | Submitted → Graded(Draft, TA) → Released (Faculty) |
| CW-LMS-01 | Composite | Assignment publication + submission | services/ | integrates BW-02 + BW-03 |
| CW-LMS-02 | Composite | Grading + grade release | services/ | integrates BW-04 + BW-05 |

### Requirements (15 CFRs, 47 AFRs)

CFR-LMS-001..015 (coherent requirements), AFR-LMS-00x.y (atomic requirements). Coverage derived by reading each rule (matrix CFR columns are empty). Key CFRs:
- CFR-LMS-001: Access course workspace and view course details
- CFR-LMS-002: Manage course workspace details
- CFR-LMS-003: Manage and schedule course materials
- CFR-LMS-004: View published materials
- CFR-LMS-005: Post/view announcements
- CFR-LMS-006: Create/edit/publish assignments
- CFR-LMS-007: View/download published assignments
- CFR-LMS-008: Submit assignments
- CFR-LMS-009: View submission history/status
- CFR-LMS-010: Grade submissions
- CFR-LMS-011: Release grades/feedback
- CFR-LMS-012: View released grades/feedback
- CFR-LMS-013: Process scheduled content release
- CFR-LMS-014: Course access control
- CFR-LMS-015: Observer read-only access

---

## Step 3.2 (b) — Domain model

### Entities

**CourseWorkspace** (read-only projection; not owned by this module)
- `course_id` (int, from ERP/registration), `title`, `syllabus`, `schedule`, `instructors[]`, `tas[]`
- Source: existing course-registration data. This module does not own the course; it owns the LMS workspace layered on top.

**CourseMaterial**
- `id`, `course_id` (int, no FK), `title`, `type` (file/link/note), `content_url` or `file`, `section` (module/week), `status` (Draft/Published/Scheduled), `release_at` (nullable datetime), `created_by` (user_id), `created_at`, `updated_at`
- Constraints: index on `(course_id, status, release_at)`.

**Announcement**
- `id`, `course_id`, `author_id` (user_id), `content`, `posted_at`
- Constraints: index on `(course_id, posted_at desc)`.

**Assignment**
- `id`, `course_id`, `title`, `instructions`, `due_at`, `submission_type` (file/text/link), `points_possible`, `status` (Draft/Published/Scheduled/Available), `release_at` (nullable), `created_by` (user_id), `created_at`, `updated_at`
- Constraints: `CheckConstraint(points_possible >= 0)`, index on `(course_id, status)`.

**Submission**
- `id`, `assignment_id`, `student_id` (user_id), `submission_type`, `content` (file/text/link), `submitted_at`, `status` (submitted/late/missing), `is_late` (bool)
- Constraints: `UniqueConstraint(assignment_id, student_id)` for baseline (one submission per student; resubmission allows N attempts), index on `(assignment_id, student_id)`.

**Grade**
- `id`, `submission_id` (1:1), `points` (nullable), `feedback` (text), `status` (Draft/Released), `graded_by` (user_id), `graded_at`, `released_by` (user_id, nullable), `released_at` (nullable)
- Constraints: `CheckConstraint(points is null or points >= 0)`.

**GradeAudit**
- `id`, `grade_id`, `changed_by` (user_id), `changed_at`, `old_points`, `new_points`, `old_feedback`, `new_feedback`, `reason`

All models: `TimeStampedModel`, `UserScopedModel` where applicable. No cross-module FKs.

---

## Step 3.3 (c) — State machines

**Material:** `Draft` → `Published` (immediate) | `Scheduled` → (beat) → `Published`.

**Assignment:** `Draft` → `Published` (immediate → `Available`) | `Scheduled` (future → `Available` via beat). `Available` → (student submits) → `Submitted`.

**Submission:** `Submitted` → `Graded (Draft)` → `Released`. Post-release grade change → `GradeAudit` row.

**Grade:** `Draft` → `Released` (Faculty only). Post-release change → audit log (instructor only).

Illegal transitions inexpressible (declarative transition table in `domain/state_machine.py`).

---

## Step 3.4 (d) — Permission list

**MODULE:** `code = "lms"`, `name = "LMS (Course Management)"`

**PERMISSIONS** (verb from closed list in rbac-model.md):
- `lms.course.view` — view course workspace
- `lms.course.manage` — manage course details
- `lms.material.view` — view published materials
- `lms.material.manage` — create/edit/schedule materials
- `lms.announcement.view` — view announcements
- `lms.announcement.create` — post announcements
- `lms.assignment.view` — view published assignments
- `lms.assignment.manage` — create/edit/publish assignments
- `lms.submission.create` — submit assignment
- `lms.submission.view_own` — view own submission history
- `lms.submission.view` — view submissions (Faculty/TA)
- `lms.grade.create` — grade submissions
- `lms.grade.release` — release grades
- `lms.grade.view` — view released grades

**SYSTEM_PERMISSIONS:** `lms.scheduled_release.run` (Celery beat, no human holds it)

**SCOPE_PERMISSIONS:** none (scoping is in selectors)

**ROLE_GRANTS:**
- `student`: `lms.course.view`, `lms.material.view`, `lms.announcement.view`, `lms.assignment.view`, `lms.submission.create`, `lms.submission.view_own`, `lms.grade.view`
- `Professor`, `Associate Professor`, `Assistant Professor` (faculty): all permissions
- `Teaching Assistant` (new designation, provisioned in dev): `lms.course.view`, `lms.material.view`, `lms.announcement.view`, `lms.announcement.create`, `lms.assignment.view`, `lms.submission.view`, `lms.grade.create`
- `Observer` (new designation): `lms.course.view`, `lms.material.view`, `lms.announcement.view`

"Teaching Assistant" and "Observer" are new designations not in `globals_designation`. Provisioned in dev via `assign_role`; requested from academic office for production.

---

## Step 3.5 (e) — Endpoint list

All under `/api/v1/lms/`. Two gates: module grant, then permission.

| Method | Path | Permission | Returns | Rules |
|---|---|---|---|---|
| GET | `/courses/{id}/` | `lms.course.view` | course workspace | BR-001,002,003 |
| PATCH | `/courses/{id}/` | `lms.course.manage` | updated details | BR-001,004 |
| GET | `/courses/{id}/materials/` | `lms.material.view` | published materials | BR-005,006 |
| POST | `/courses/{id}/materials/` | `lms.material.manage` | created material | BR-004,005,006 |
| PATCH | `/courses/{id}/materials/{mid}/` | `lms.material.manage` | updated material | BR-004,005,006 |
| GET | `/courses/{id}/announcements/` | `lms.announcement.view` | announcements | BR-008 |
| POST | `/courses/{id}/announcements/` | `lms.announcement.create` | created announcement | BR-007,008 |
| GET | `/courses/{id}/assignments/` | `lms.assignment.view` | published assignments | BR-011 |
| POST | `/courses/{id}/assignments/` | `lms.assignment.manage` | created assignment (Draft) | BR-009,010 |
| PATCH | `/courses/{id}/assignments/{aid}/` | `lms.assignment.manage` | updated assignment | BR-009,010 |
| POST | `/courses/{id}/assignments/{aid}/publish/` | `lms.assignment.manage` | published/scheduled | BR-010,011 |
| GET | `/courses/{id}/assignments/{aid}/` | `lms.assignment.view` | details + download | BR-011 |
| POST | `/courses/{id}/assignments/{aid}/submit/` | `lms.submission.create` | submission record | BR-012,013,014 |
| GET | `/courses/{id}/assignments/{aid}/submissions/` | `lms.submission.view` | submissions (Faculty/TA) | BR-014,015 |
| GET | `/courses/{id}/assignments/{aid}/my-submission/` | `lms.submission.view_own` | own history/status | BR-014 |
| POST | `/courses/{id}/assignments/{aid}/submissions/{sid}/grade/` | `lms.grade.create` | grade (Draft) | BR-015,016 |
| POST | `/courses/{id}/assignments/{aid}/submissions/{sid}/release-grade/` | `lms.grade.release` | released grade | BR-017,018,019 |
| GET | `/courses/{id}/assignments/{aid}/my-grade/` | `lms.grade.view` | own released grade + feedback | BR-016,018 |

**Client routes** (nav_matches_routes.py enforced): `/lms/courses/:id`, `/lms/courses/:id/materials`, `/lms/courses/:id/announcements`, `/lms/courses/:id/assignments`, `/lms/courses/:id/assignments/:aid`, `/lms/courses/:id/gradebook`.

**Nav items:** one per route, each with `required_permission`.

---

## Step 3.6 (f) — Contracts

`modules/lms/contracts.py` exposes (plural getters):
- `get_course_workspaces(course_ids: Sequence[int]) -> list[CourseWorkspaceDTO]`
- `get_materials(course_ids: Sequence[int]) -> list[MaterialDTO]`

Needed from IAM (existing, no new endpoints):
- `get_users(ids)` — person name, kind, discipline
- `search_users(query)` — for TA assignment
- `get_academic_standings(ids)` — if CPI needed (likely not for LMS baseline)

No new IAM endpoints needed. No `fusionlab` connection.

---

## Step 3.7 (g) — Scheduled work

| Beat entry | Cadence | What breaks if it doesn't run |
|---|---|---|
| `lms.release_scheduled_materials` | every 1 min | Scheduled materials never publish |
| `lms.release_scheduled_assignments` | every 1 min | Scheduled assignments never become available |

Both registered in `schedule.py` + `config/celery.py`. Tasks must be idempotent.

---

## Step 3.8 (h) — Open questions (resolved readings)

| # | Question | Resolution (per Student 1 + Student 2) |
|---|---|---|
| a | Late-submission policy | Admin-overridable (late flag recorded, admin can override) |
| b | TA permissions | Configurable per course |
| c | Notification channel | Both email + in-app |
| d | Observer linkage | Entire course section |
| e | Resubmission policy | Number of attempts allowed (default 1, configurable) |
| f | Post-release grade change | Only instructor (Faculty) may change; audit logged |

**Known gaps accepted:** None beyond the above. All six are resolved readings.

**TA/Observer designations:** New designations "Teaching Assistant" and "Observer" — provisioned in dev via `assign_role`, requested from academic office for production.

---

## Approval

- Blueprint approved by Student 2: ✅ (written approval received)
- Gaps approved: N/A (all resolved)
- Shared-file changes approved: Step 4.0 registration lines (pre-approved per prompt)
- New dependencies: none

---

**Stop here. Wait for approval before Step 4.1.**

Approval received. Proceeding to Phase 3 (backend, layer by layer) is authorized.