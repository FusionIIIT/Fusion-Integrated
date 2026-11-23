# LMS Course Management

This module provides course workspaces, organized materials, announcements,
assignment publication, Student submissions, grading and released feedback.
It implements the approved A9-LMS-BP-0.2 decisions against the live IAM academic
contract, revision `494160849bd101a5cb77a1b1c9f0881307079888`.

## Access and data ownership

IAM owns identity, permissions, course offerings and course associations. The
module stores only opaque 68-character offering keys and integer actor IDs.
Every request requires a module grant, an action permission and a live association
for its acting role. Course associations never grant an absent action permission.
Out-of-course identifiers are 404; an unsupported action is 403.

Students read common content and only their own submissions and released grades.
Faculty configure their assigned workspaces and publish content and grades. TAs
read assigned courses and submissions and save draft grades; their announcement
posting additionally requires an effective Faculty policy. Observers read only
common course content. Local TA/Observer designations are `lms_ta` and
`lms_observer`; no role or enrollment authority is added to the LMS database.

The approved development setup reads real synthetic course-registration records;
nonstudent teaching/observer associations are explicitly tagged
`synthetic_fixture`. These fixtures are not a production teaching-assignment feed.
The working identifiers `lms` and `docs/10-lms/` are pair-endorsed values.

## Deployment order

1. Deploy the pinned IAM academic contract; synchronize its offering catalogue.
2. Configure the platform database, service token, Redis and private storage root.
3. Run `manage.py migrate` then `manage.py sync_lms_workspaces`.
4. Run `manage.py seed_modules` and regenerate the permission manifest with
   `make permissions`. Seed that manifest in IAM using `seed_iam_permissions`.
5. Provision the appropriate real IAM designations and course associations.
6. Run `manage.py check_lms_ready`.
7. Start the web service, `celery -A config worker` and `celery -A config beat`.

`sync_lms_workspaces` is idempotent. It preserves Faculty-edited details and seeds
safe, false TA announcement policies. Readiness names unmet migration, source or
policy prerequisites. A fresh installation is not active until setup is complete.

The supplied development settings force eager tasks. Real ETA scheduling requires
an environment-specific settings overlay setting `CELERY_TASK_ALWAYS_EAGER=False`
and a running broker/worker/beat. Production base settings already default false.
No supplied development or test gate was weakened for the local overlay.

`PRIVATE_UPLOAD_ROOT` must be outside the repository and static/web roots.
Uploads are private attachments, never public media URLs. Approved profiles cap
materials at 25,000,000 bytes and submissions at 10,000,000 bytes. PDF, ZIP,
TAR.GZ, TXT, DOCX and IPYNB content is validated using bounded standard-library
inspection. Files are never extracted or executed. Authorized parent views stream
downloads; responses never contain storage paths. Newly staged bytes are removed
if their database write fails.

## Client and API

The existing portal shell hosts `/lms/courses`, `/lms/teaching` and `/lms/grading`.
Each route has its navigation permission guard. Controls additionally follow
action permissions and course capabilities. HTTP and downloads use the shared
client; cache keys include user and acting role. All lists support cursor paging.
Course materials display their section and order. Submission status is derived
from the Student's own history: missing before success, submitted afterward.

The REST surface mounts only at `/api/v1/lms/`. The generated OpenAPI document
describes course details/policies, sections, materials, announcements, assignments,
submissions, grade writes/releases and scoped attachment downloads.

## Rules and transactions

- The server records one successful submission per Student/assignment, enforced by
  a database uniqueness constraint and an assignment row lock. Failed requests
  consume no attempt. The deadline is inclusive; requests after it receive
  `422 SUBMISSION_DUE_DATE_EXCEEDED`; repeat successes receive
  `409 SUBMISSION_ALREADY_EXISTS`.
- Submission type becomes immutable after a submission. Due dates then may only
  remain unchanged or extend. Points possible become immutable after grading.
- Faculty and assigned TAs save Draft grades. Only Faculty release them. Students
  never receive Draft grades. Faculty corrections retain Released state and
  atomically append actor/time and before/after score/feedback audit data.
- Versioned course policies and grade audit records are append-only through the
  module interfaces. There is no update/delete API for either history.
- The release tables admit only explicit lifecycle edges. An on-commit ETA job
  is primary; a 60-second, 50-item catch-up sweep recovers missed dispatches.
  Tasks lock and re-read eligibility, so duplicate jobs, stale ETAs and withdrawn
  scheduled content cannot cause an early or repeated publication.

The original blueprint is preserved byte for byte. Implementation helpers are
grouped in `domain/rules.py`, `models/__init__.py` and scoped selector modules;
the generated [implementation reference](lms-reference.md) resolves every live ID
to its concrete enforcement and builder assertion.

See [the quality report](lms-quality-report.md) for actual checks and approval
records. Independent reviewer scoring and the separate specification-test stage
are subsequent milestones; this record does not assign itself a score.
