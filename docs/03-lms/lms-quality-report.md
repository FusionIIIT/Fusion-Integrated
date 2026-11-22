# LMS (Course Management) — Quality Report

**Module:** LMS Course Management (`lms`)
**Documentation Path:** `docs/03-lms/`
**Environment:** `module-only`
**Status:** Verification Passed — Ready for Student 1 & Student 2 Review

---

## 1. CI Verification Suite Execution

### 1.1 Backend Verification (`make check`)

```bash
$ make check
.venv/bin/python manage.py check
System check identified no issues (0 silenced).
.venv/bin/python manage.py makemigrations --check --dry-run
No changes detected
.venv/bin/ruff check .
All checks passed!
.venv/bin/lint-imports

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲
      ╚╝────────────────────┘

---------
Contracts
---------

Analyzed 257 files, 848 dependencies.
-------------------------------------

Modules may reach each other ONLY through contracts.py KEPT
domain/ must not import Django, DRF or Celery KEPT
core/ must not import any module KEPT
Layering inside placement KEPT
Layering inside lms KEPT

Contracts: 5 kept, 0 broken.
.venv/bin/python ops/checks/no_cross_module_fk.py
no cross-module foreign keys
.venv/bin/python ops/checks/contracts_are_plural.py
all contract getters are plural
.venv/bin/python ops/checks/nav_matches_routes.py
nav items and client routes agree
.venv/bin/python manage.py permission_manifest --check
permission manifest matches the registries
make schema-check
make[1]: Entering directory '/home/abhi/Documents/Fusion/Fusion-Integrated-A9'
openapi schema matches the code
make[1]: Leaving directory '/home/abhi/Documents/Fusion/Fusion-Integrated-A9'
.venv/bin/python -m pytest -q
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 76%]
..................................................... [ 88%]
.......................................................          [100%]
468 passed in 37.15s
```

### 1.2 Frontend Verification (`make check-client`)

```bash
$ make check-client
cd client && npm run typecheck && npm test && npm run build

> typecheck
> tsc --noEmit && tsc --noEmit -p e2e

> test
> vitest run

 RUN  v2.1.9 /home/abhi/Documents/Fusion/Fusion-Integrated-A9/client

 Test Files  6 passed (6)
      Tests  38 passed (38)
   Start at  08:31:27
   Duration  5.33s (transform 1.34s, setup 3.95s, collect 8.73s, tests 1.21s, environment 9.79s, prepare 1.47s)

> build
> tsc -b && vite build

vite v5.4.21 building for production...
✓ 1373 modules transformed.
dist/index.html                                     0.47 kB │ gzip:   0.30 kB
dist/assets/index-C8Jg2u9o.css                     39.52 kB │ gzip:   7.48 kB
dist/assets/CoursesPage-nxmhzQly.js                  4.74 kB │ gzip:   1.91 kB
dist/assets/GradingPage-DsBU2EAy.js                  6.02 kB │ gzip:   2.34 kB
dist/assets/MaterialsPage-BpNqPcNA.js                6.41 kB │ gzip:   2.57 kB
dist/assets/AssignmentsPage-BXVX0A2v.js              6.55 kB │ gzip:   2.50 kB
dist/assets/MyGradesPage-1dj5cy-x.js                 2.63 kB │ gzip:   1.24 kB
dist/assets/AnnouncementsPage-CIy-MhvB.js            3.59 kB │ gzip:   1.70 kB
dist/assets/index-CkLa11az.js                      510.84 kB │ gzip: 165.88 kB
✓ built in 7.79s
```

---

## 2. Test Coverage & Breakdown

### 2.1 Coverage Run (`pytest --cov=modules.lms`)

```bash
$ pytest --cov=modules.lms modules/lms/tests/
...........................................                              [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.3-final-0 ________________

Name                                     Stmts   Miss  Cover
------------------------------------------------------------
modules/lms/__init__.py                      0      0   100%
modules/lms/api/__init__.py                  0      0   100%
modules/lms/api/permissions.py              13      2    85%
modules/lms/api/serializers.py              45      0   100%
modules/lms/api/urls.py                      3      0   100%
modules/lms/api/views.py                   299     54    82%
modules/lms/apps.py                          5      0   100%
modules/lms/contracts.py                    55      0   100%
modules/lms/domain/__init__.py               3      0   100%
modules/lms/domain/calculations.py           8      0   100%
modules/lms/domain/constants.py             41      0   100%
modules/lms/domain/rules.py                  8      0   100%
modules/lms/domain/state_machine.py         43      0   100%
modules/lms/domain/validators.py            39      2    95%
modules/lms/models/__init__.py               7      0   100%
modules/lms/models/announcements.py         16      0   100%
modules/lms/models/assignments.py           26      0   100%
modules/lms/models/grading.py               39      0   100%
modules/lms/models/materials.py             26      0   100%
modules/lms/models/submissions.py           22      0   100%
modules/lms/models/workspace.py             34      0   100%
modules/lms/registry.py                     10      0   100%
modules/lms/schedule.py                      4      4     0%
modules/lms/selectors/__init__.py            8      0   100%
modules/lms/selectors/announcements.py       8      1    88%
modules/lms/selectors/assignments.py        27      3    89%
modules/lms/selectors/grading.py            37      7    81%
modules/lms/selectors/materials.py          27      2    93%
modules/lms/selectors/scoping.py            33      5    85%
modules/lms/selectors/submissions.py        40     14    65%
modules/lms/selectors/workspace.py          24      3    88%
modules/lms/services/__init__.py             7      0   100%
modules/lms/services/announcements.py       26      4    85%
modules/lms/services/assignments.py         48     21    56%
modules/lms/services/grading.py             66      8    88%
modules/lms/services/materials.py           24      2    92%
modules/lms/services/submissions.py         37      5    86%
modules/lms/services/workspace.py           19      3    84%
modules/lms/tasks.py                        13      0   100%
------------------------------------------------------------
TOTAL                                     1190    140    88%
43 passed in 8.80s
```

### 2.2 Test Inventory & Specification Traceability

| Test File | Count | Traceable Specifications / Rules Tested |
|---|---|---|
| `test_domain.py` | 12 | `BR-LMS-004`, `BR-LMS-005`, `BR-LMS-011`, `BR-LMS-012`, `BR-LMS-013`, `BR-LMS-015`, `BR-LMS-016` (Validators, Rules, Calculations, FSMs) |
| `test_models.py` | 7 | `BR-LMS-010`, `BR-LMS-015`, `lms_assignment_points_positive`, `lms_assignment_due_after_release`, `lms_unique_course_user_role`, `lms_grade_points_non_negative` |
| `test_selectors.py` | 7 | `CFR-LMS-001`, `AFR-LMS-001.2`, `BR-LMS-005`, `BR-LMS-011`, `BR-LMS-016`, `BR-LMS-017` (Row scoping, observer privacy, staff roster only) |
| `test_services.py` | 5 | `CFR-LMS-002`, `UC-LMS-002`, `UC-LMS-003`, `UC-LMS-004`, `BR-LMS-007`, `BR-LMS-012`, `BR-LMS-013`, `BR-LMS-017`, `BR-LMS-019` (Full lifecycle) |
| `test_api.py` | 5 | `UC-LMS-001` through `UC-LMS-005` (REST DRF endpoints, authentication, serializers, error handling) |
| `test_privilege_escalation.py` | 5 | Security baseline: student write rejection, TA faculty-action rejection, TA restricted flag checks, observer read-only enforcement, cross-course isolation |
| `test_schedule.py` | 1 | `BR-LMS-005`, `BR-LMS-011` (`lms.tasks.process_scheduled_content_release` Celery Beat task) |
| `test_contracts.py` | 1 | Platform ADR-0013 & plural getters rule (`get_course_summaries`, `get_user_course_enrollments`, `get_student_course_grades`) |
| **Total LMS Tests** | **43** | **100% Pass Rate** |

---

## 3. Adversarial Pass & Security Defenses

1. **Closed Action Vocabulary:**
   - Redesigned LMS permission codes strictly to the IAM standard actions (`view`, `create`, `update`, `delete`, `review`, `publish`).
   - `permission_manifest --check` confirmed 0 undeclared, 0 duplicate, and 0 unenforced permissions.

2. **Teaching Assistant Scoping & Delegation:**
   - TAs are granted `lms.announcement.create` and `lms.submission.review` globally in IAM, but the services layer enforces course-level delegation via `CourseMembership.can_post_announcement` and `CourseMembership.can_grade`.
   - Verified that a TA attempting to post an announcement without `can_post_announcement=True` receives `403 Forbidden`.
   - Verified that a TA attempting to grade without `can_grade=True` receives `403 Forbidden`.
   - Verified that a TA can never publish grades (`BR-LMS-017`: faculty-only action).

3. **Course Observer Isolation & Privacy:**
   - Observers receive read-only course details and the teaching staff roster (`instructors`, `teaching_assistants`).
   - The student roster is strictly excluded from course detail endpoints to eliminate peer disclosure.
   - Submissions and grades endpoints return empty lists (or `403 Forbidden`), completely preventing observers from accessing student identities or submitted work.

4. **Fail-Safe Content Release:**
   - In addition to Celery Beat background transitions, selectors enforce fail-safe filtering: `(release_date is null or release_date <= now())`.
   - Even if background release jobs are delayed, students cannot retrieve unreleased materials or assignments.

5. **Post-Release Grade Change Audit (`GradeChangeAudit`):**
   - While in `DRAFT` status, grades can be adjusted without audit logging.
   - Once published to students, any subsequent update to `points_awarded` or `feedback_text` automatically creates a `GradeChangeAudit` row recording `old_points`, `new_points`, `old_feedback`, `new_feedback`, `changed_by`, `changed_at`, and the mandatory `reason`.

6. **Cross-Course Isolation:**
   - An instructor of Course A attempting to modify Course B, post announcements in Course B, or grade Course B submissions is blocked with `403 Forbidden`.

---

## 4. Scheduled Tasks

- **Task Name:** `lms.tasks.process_scheduled_content_release`
- **Schedule:** Every 60 seconds (`*/1 * * * *`)
- **Queue / Routing:** Routed to `lms` Celery queue via `config/celery.py`
- **Verification:** Unit tested in `test_schedule.py`. Atomically updates past-due `CourseMaterial` and `Assignment` records from `SCHEDULED` to `PUBLISHED` while leaving future records in `SCHEDULED`.

---

## 5. Architectural Compliance Record

- **No Cross-Module Foreign Keys:** Passes `ops/checks/no_cross_module_fk.py`. Cross-module references use synthetic integer `course_id` and `user_id` without database-level foreign keys.
- **Plural Contract Getters:** Passes `ops/checks/contracts_are_plural.py`. All getters in `modules/lms/contracts.py` accept sequence parameters (`Sequence[int]`).
- **Client/Server Navigation Agreement:** Passes `ops/checks/nav_matches_routes.py`. All 6 `NAV_ITEMS` (`courses`, `materials`, `announcements`, `assignments`, `grades`, `grading`) match routes in `client/src/modules/lms/routes.tsx`.
- **OpenAPI Schema Conformance:** Passes `make schema-check`. OpenApi schema is committed and validated with zero warnings.
- **Clean Git Tree:** No unneeded files or external modules modified.
