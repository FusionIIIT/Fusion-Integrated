# Institute Accounts and Audits (IAA)

IAA is integrated into the existing Fusion Django and React application. The six
uploaded specification documents are preserved byte-for-byte in this directory;
`SOURCE_SHA256.json` records their checksums. The existing Placement and Employee
Leave Management modules remain available.

## Implementation

| Component | Location |
| --- | --- |
| Domain rules and terminology | `modules/iaa/domain/rules.py` |
| Database models and PostgreSQL integrity guards | `modules/iaa/models.py`, `modules/iaa/migrations/` |
| Role/department/ownership scoping and reports | `modules/iaa/selectors.py` |
| Transactional application services | `modules/iaa/services.py` |
| Validated REST endpoints | `modules/iaa/api/` |
| React workspace and administration forms | `client/src/modules/iaa/` |
| Fusion dashboard notifications | `client/src/modules/iaa/DashboardWidget.tsx` |
| Timeout processing | `modules/iaa/tasks.py`, `modules/iaa/schedule.py` |
| Backend test suite | `modules/iaa/tests/` |
| Browser integration test | `ops/smoke/test_iaa_browser.py`, `client/e2e/iaa-smoke.cjs` |
| API schema | `openapi/fusion-integrated.v1.yaml` |
| Requirements mapping | `IMPLEMENTATION_TRACEABILITY.csv` |

IAA owns its tables and references Fusion identities by ID without cross-module
foreign keys. Its public contract is read-only and batched. The module is
registered as `institute_accounts_audits`, with `/iaa/workspace` as its frontend
entry and `/api/v1/iaa/` as its API prefix.

## Implemented behavior

- Expense/voucher drafts can be incomplete. Submission identifies missing
  information, requires positive amounts and configured evidence, and locks
  ordinary creator edits.
- TA claims submit atomically with trip dates, purpose, amount, and documentary
  requirements. Finance may clarify, reject noncompliant TA, verify ordinary TA,
  or route high-value TA according to the configured threshold.
- Finance clarification and response cycles preserve the original submitted
  content and all query/evidence history.
- Routes match kind, request type, department, and amount. Priority resolves
  precedence; ambiguous equal-priority matches are refused. Routes and policy
  are snapshotted. HoD, Dean, and Director remain distinct roles. Creator steps
  are skipped and a route with no eligible authority is blocked.
- Departmental budgets are checked under a database lock. In-flight approvals
  reserve budget, rejection releases the reservation, and internal recording
  retains it as a committed amount. Insufficiency creates an automatic anomaly
  and keeps the request under Finance handling rather than rejecting it.
- Manual and automatic anomalies have Open/Resolved/Escalated outcomes and
  designated resolver roles. Unresolved anomalies block validation, decisions,
  and internal completion. Anomaly escalation is independent of approval
  timeout escalation.
- Overdue authority assignments escalate to the next eligible configured
  authority. The check is idempotent per assignment. If no higher authority
  exists, the item remains pending, the issue is logged, and overdue
  notifications are generated without an invented rejection.
- Audit observations follow Open → Responded → Closed, with Responded → Open
  for rework. Corrective evidence and Auditor verification are mandatory.
  Prior response cycles remain in the immutable audit trail.
- Finance records internal completion with a reference. This does not execute
  a payment, initiate a bank transfer, or claim payment success.
- Reports show scoped status, anomaly/observation totals, completion time, and
  authority approval turnaround measured separately. CSV exports escape
  spreadsheet formula prefixes. Basic Users and System Admin cannot export
  operational reports.
- Notifications and pending actions are shown in the IAA workspace. Recent
  role-scoped IAA notifications also appear on the Fusion dashboard; the bell
  opens the IAA notification view for users granted the module.
- System Admin manages role grants, department Finance routing, financial
  years, policy, budgets, and approval routes. The active Admin role cannot
  view financial requests or perform approvals.
- Audit entries capture identity, active role, timestamp, action, resulting
  status, and relevant snapshots. PostgreSQL triggers reject their updates and
  deletion, protect recorded financial records, and retain audit observations.

## Role context and identity integration

Fusion IAM still authenticates users; IAA does not introduce another password
database. IAM must grant the module and the permission
`institute_accounts_audits.workspace.access`. The generated permission manifest
declares the seven IAA roles.

IAA maintains explicit per-user role/department grants locally, as required by
the IAA administration use cases. Blank department means institute-wide scope.
An IAA role grant does not bypass Fusion's module and permission gates.

A single assigned role can be used automatically. Multi-role users must select
their active IAA role. The UI logs selection with `POST /iaa/session` and sends
`X-IAA-Role` on subsequent API requests; every request validates that selection
against current assignments. The selected role is stored per user in the
browser tab, not in a shared global server session. Switching roles cannot
rewrite historical identities or roles. The header is a selection, not an
authorization credential.

## Setup in the existing environment

Dependencies are the existing project's dependencies; no manifest or lockfile
changes are needed. From `/workspace/Fusion-Integrated`:

```sh
docker compose up -d --wait
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_modules
```

Before live use, bootstrap one **existing** Fusion identity:

```sh
.venv/bin/python manage.py bootstrap_iaa --user-id YOUR_EXISTING_FUSION_USER_ID
```

The command checks that identity through the existing directory/IAM contract
and refuses to bypass an existing administrator. Grant this user the IAA module
and permission in IAM. Sign in through the normal Fusion shell and open IAA.

In the System Admin workspace configure, in order:

1. Existing user role assignments and their department scopes.
2. Non-overlapping active financial years covering submission dates.
3. Departments and eligible Finance assignees.
4. One active policy: TA threshold, optional daily cap, documentary/budget
   requirements, and eligible anomaly resolver/escalation roles.
5. Department/year budget allocations.
6. Ordered authority routes for expense and TA: amount range (minimum inclusive,
   maximum exclusive), optional department/type criteria, priority, and timeout
   hours. A wildcard route requires institute-wide authority assignments.

No institutional thresholds, budget amounts, Finance identities, or approvals
are fabricated by migration. A submission with missing Finance routing is
retained and flagged; after correcting department configuration, an Admin can
recover its routing by record ID without viewing the financial content.

Start development with `make dev`, and in `client/` run `npm run dev`. Restart
Django after adding the module if using `--noreload`.

For autonomous overdue processing run a Celery worker that consumes both the
default `celery` and `notifications` queues plus Celery beat:

```sh
.venv/bin/celery -A config worker -Q celery,notifications --loglevel=INFO
.venv/bin/celery -A config beat --loglevel=INFO
```

The IAA beat task checks every five minutes; timeout durations come from the
configured route steps. Run `.venv/bin/python manage.py run_iaa_escalations` for
an immediate manual check. Do not run multiple beat instances for one deployment.

## Validation and traceability

Run the standard checks:

```sh
DJANGO_SETTINGS_MODULE=config.settings.test make check
make check-client
```

The explicit browser test additionally needs Vite running on port 5173, Node's
`playwright` package, and Chromium. These are available in this environment:

```sh
.venv/bin/pytest ops/smoke/test_iaa_browser.py -o addopts='' -q
```

It uses an isolated PostgreSQL test database, real React screens and real Django
API transitions, and a fake IAM. It does not create a development login bypass.
See `VALIDATION.md` for the measured results.

The supplied workbook contains 18 CFRs and 75 AFRs. The generated CSV preserves
its original crosswalk columns and adds implementation/test references for all
75 AFR rows. The original `Coverage` column describes the specification's own
mapping, not an independent implementation certification. Representative tests
are not proof of every possible policy combination.

## Concrete implementation choices and limits

- Supporting documents and corrective evidence are HTTPS references to
  access-controlled document storage. The server never fetches these URLs;
  binary upload hosting, malware scanning, and remote-document availability
  checks are not provided. Access policies on that storage must be configured
  separately.
- Finance records documentary/policy review as an explicit attestation.
  Completeness, trip dates, the optional daily cap, approval threshold, and
  departmental budgets are checked automatically. Institution-specific policy
  interpretation still requires Finance review.
- Observation targets are financial records representing expense/TA processes;
  a separate free-standing institutional-process register is not introduced.
- Operational lists show the newest 200 authorized records, with type, status,
  and department filters available for financial requests. Reports and CSV
  exports aggregate the full authorized scope. Large-scale pagination and
  performance/load certification are follow-up work.
- Current-instance validation uses synthetic IAM identities. Live institute
  IAM access and institutional configuration are required to exercise real
  employee login; they were not independently verified here.
- The original IAA documents are the requirements for this implementation. No
  local/offline Qwen execution is claimed for this work.
- Production deployment, mentor approval, PR submission, and GitHub publication
  are separate actions. This work does not claim they have occurred.
