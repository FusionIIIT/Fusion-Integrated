# Assignment 7 LMS Course Management

This branch implements LMS inside `FusionIIIT/Fusion-Integrated`, under `modules/lms`, with React screens under `client/src/modules/lms`. It starts from the existing Fusion-Integrated main branch and does not include the previous ELM branch or the separate Fusion monolith submission. Generation and integration used Codex.

## Implemented work

- Course workspace models and initial migration, scoped by external academic course ID, year and semester type.
- Read-only academic course-association contract in `modules/academics/contracts.py`. No registration, add/drop, waitlist or official examination records are modified.
- IAM module/permission checks, active-role matching and course-specific association checks. IAM identities are integer references; LMS does not create a second user/login system.
- Course home, syllabus, schedule, instructor and TA information.
- File, text and link materials, sections, publication and scheduled release.
- Timestamped announcements from Faculty and externally authorized TAs.
- Draft assignments, editing, publication, release dates, due dates, submission type and points possible.
- On-time student submissions and private file storage/downloads with ownership/course checks.
- Student submission history and own released grades; draft grades and feedback are removed from student API responses.
- Faculty/TA grading, grader attribution, Faculty-only release, audit rows and revision checks.
- Observer read-only course content without assignments, submissions, grades or student-specific source metadata.
- React course list/detail routes, forms, file uploads and guarded downloads using the existing shell, authentication, HTTP client and Mantine components.
- Celery release schedule and `python manage.py release_lms_content` fallback.
- Generated IAM manifest, permission catalog, OpenAPI schema and module-boundary registration.

## Registration provider is required

Fusion-Integrated's supplied base has no academic course-registration implementation. The old Fusion monolith's models are not imported into this service. Configure `LMS_COURSE_PROVIDER` to the dotted Python path of a read-only adapter for the authoritative registration/teaching-assignment source.

The callable accepts a list of IAM user IDs and returns a dictionary keyed by those integer IDs. Each value is a list of confirmed associations. Every association supplies:

| Field | Meaning |
| --- | --- |
| `course_id` | Positive integer ID from the authoritative academic system |
| `year` | Offering year |
| `semester_type` | `Odd Semester`, `Even Semester` or `Summer Semester` |
| `role` | `student`, `faculty`, `ta` or `observer`, confirmed for that course |
| `code`, `title` | Public course display information |
| `may_announce` | Optional explicit TA announcement authorization; true only when authorized |
| `instructors`, `tas` | Optional public staff lists containing `user_id` and `display_name` |

Unknown source fields are discarded, so Observer responses do not inherit arbitrary student data from an upstream payload. The adapter must handle the source system's identity mapping and Observer linkage policy. The LMS service never grants its own membership or falls back to mock enrolments. Without a configured/working provider, course access returns `registration_unavailable` with HTTP 503. Tests substitute an in-memory provider only in fixtures.

## Specification and unresolved policy

Source bundle: Problem Statement v1.0 unchanged, synchronized Requirement Registry, Use Cases, Business Rules, Workflows and Traceability Matrix v1.0 supplied for this assignment. Source hashes are recorded in `source-inventory.json`.

ISS-LMS-001 through ISS-LMS-006 remain unresolved in the supplied documents. Late submission, resubmission and post-release grade edits return explicit unresolved-policy errors. Notification delivery is not implemented. TA announcement authorization and Observer associations must come from an authorized external source; no institutional policy is inferred. Audit rows record grading/release, while a complete post-release correction lifecycle remains pending clarification.

## Setup and routes

Install the existing Fusion-Integrated requirements. Configure its existing PostgreSQL and IAM settings, plus the registration-provider callable. Run migrations and regenerate/publish IAM permissions using the repository's role-assignment guide:

```text
python manage.py migrate
python manage.py permission_manifest
python manage.py seed_modules
```

API namespace: `/api/v1/lms/`. Client namespace: `/lms/`, with `/lms/courses` and `/lms/courses/:id`. Declared designations include basic student/faculty roles, Course Faculty, Teaching Assistant, TA and Observer. The actor must also hold the matching course association in the authoritative source.

`LMS_UPLOAD_ROOT` defaults to `var/lms-private` beneath the backend root. Do not serve that directory as public media. Downloads go through authenticated API checks. The forms impose a 10 MB implementation upload limit.

## Executed checks

- Full backend suite: **395 passed**, including **15 LMS cases**, using `config.settings.test_sqlite`.
- Existing client suite: **35 passed**; no dedicated new LMS React tests are claimed.
- Production client build and TypeScript compilation: passed; the existing shared bundle produced a 500 kB advisory warning.
- Whole-repository Ruff, Django checks, migration drift: passed.
- Five import contracts, cross-module FK check, plural contract getters and navigation/route parity: passed.
- Generated permission manifest and strict OpenAPI generation: passed.

Reproduce the local backend test run with `python -m pytest --ds=config.settings.test_sqlite`. These settings keep LMS migrations enabled and synchronize the unrelated placement app from its current models because its historical index migration requires PostgreSQL. Production/CI PostgreSQL settings are unchanged.

The registration provider, live IAM, PostgreSQL concurrency, Celery worker execution and browser end-to-end flow were not verified against live services. API authorization tests use stubbed IAM and a test-only provider. This is implementation and local verification evidence, not a claim of deployment readiness or complete atomic-requirement coverage.
