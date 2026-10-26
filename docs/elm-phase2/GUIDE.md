# ELM Phase 2 code and verification guide

This package improves the existing ELM module from the local checkout on `feature/elm-module`. The related upstream submission is FusionIIIT/Fusion-Integrated PR 158, whose recorded head was `8a4a3559331a063d6568aa382b54ba54a94423c5`. The preserved snapshot contains the supplied local source; it is not asserted to be a byte-for-byte checkout of that remote commit.

The original Phase-1 folder has not been modified. `ELM_Phase1_Preserved.zip` contains its source snapshot, excluding Git metadata, local secrets, virtual environments and dependency installations. The initial ELM migration is unchanged. New migrations are additive.

## Authorship and assignment evidence

The original PR identifies Qwen2.5-Coder-7B-Instruct with Aider. These Phase-2 changes were generated and tested by Codex at the user's request. No local Qwen session was run for these changes. The assignment asks for iterative use of the selected local model; this deliverable does not establish that requirement. Do not describe this work as local-Qwen output or fabricate model interaction logs, screenshots, live testing or production deployment evidence.

## What changed

- Fusion Principal numeric user IDs replace usernames as ELM account identities. Each API checks module access and action permission. Approval queues and decisions are restricted to the assigned user and active authority role.
- Annual defaults now follow the supplied baseline: CL 8, RH 2, SCL 15, staff EL 30, eligible COL 20, faculty VL 60. Faculty EL starts at zero and receives converted VL/carry-forward. Staff receive no VL.
- The backend calculates days, validates dates and calendar eligibility, rejects forged durations and overlapping active applications, and supports distinct FN/AN CL halves on the same date.
- Station departure, return and address are validated together within the leave application.
- Substitute nominees must be another configured employee without overlapping leave. Decline leaves the request pending for replacement or withdrawal; consent gates approval routing. Accepted coverage also prevents conflicting new leave by that substitute.
- CL/RH end at the configured Unit Head. Higher categories continue through configured processing/authority steps. Not Recommended is recorded and forwarded. Director self-sanction requires the Director's active IAM role.
- Withdrawal is terminal and releases reservations once. Cancellation uses a separate request and restores balance only upon final pre-start approval. Extension posts incremental days. Resumption retains original approved dates, records reviewed actual dates and adjusts accounts.
- Audit entries, account entries, in-app notifications and attendance integration outbox records are transactional. Pending-only reminders and notification escalation are idempotent per task assignment.
- Administrative policy, employee hierarchy and calendar APIs validate input and record configuration audits. Published calendar replacements are created as new records; drafts do not replace the current published calendar. Offline-sanctioned leave uses a separate evidence-bearing synchronization endpoint.
- Employee screens now expose half-day selection, substitute recovery, lifecycle actions, notifications, history and printable HTML downloads. API paths use the shared `/api/v1` base exactly once; error messages follow Fusion's error envelope.
- Updated the permission manifest and generated permission catalogue, added ELM to architecture enforcement, documented OpenAPI endpoints and regenerated the schema.
- Fixed an observed base-directory zero-TTL cache issue: zero now disables reuse even if two timestamps are equal on Windows.

## Verification and its boundaries

See `evidence/` for command logs, JUnit results and the check summary. Portable tests use `config.settings.elm_test`, SQLite and the repository's fake IAM. ELM migrations are exercised. Placement migrations contain an index operation that fails under SQLite, so only Placement uses its current model schema in this test setting; its production migrations are not changed.

The following require a real development environment before deployment:

1. Run all migrations and tests against PostgreSQL, including concurrent application/approval/withdrawal and substitute races. SQLite does not verify PostgreSQL row-lock behavior.
2. Run Fusion IAM, synchronize identities and permission grants, and verify employee login, role switching, CSRF and navigation end to end.
3. Configure real employee hierarchies, holiday calendars and academic vacation data; exercise representative workflows manually.
4. Connect an attendance consumer to the ELM outbox and acknowledge successfully synchronized events. The generated code records durable events; it does not claim to have updated a live external attendance module.
5. Arrange a scheduler to invoke SLA/year-end commands. No background scheduler was installed on this computer.

## Remaining scope and assumptions

- This is improved code for review and integration, not a certified production deployment or a claim of complete assignment compliance.
- Administrative functions and offline entry have APIs, with OpenAPI documentation; dedicated administration screens are not implemented. Record maintenance is deliberately restricted to audited annotations rather than arbitrary approval or balance changes.
- Existing Phase-1 data needs explicit reconciliation: usernames must be mapped to numeric IAM IDs, old fixed-12-day credits and usage reviewed, opening audit entries established and pending routes assigned. No automatic identity guess or balance rewrite is performed. Use a backed-up database or a clean development database; do not point this version at an unreconciled production database.
- Cross-year applications must be split; cross-year extensions and post-close historical adjustments are rejected. Year-end currently uses the calendar-year boundary (January 1), with explicit command invocation for the year being closed.
- Weekend counting for CL/SCL defaults to Saturday/Sunday plus published closed dates. Institute policy must confirm the calendar convention. EL/COL/VL count continuously; RH uses published RH dates. Vacation data is an imported projection, not a live Academic Calendar API connector.
- Routing is configured per employee/category using unit/designation-aware administrative input and captured on submission. Pending requests retain that route; changing configuration does not automatically reroute existing tasks. Cancellation follows the original route. Configuring a new employee category/role requires a matching IAM grant.
- Policy annual-credit changes affect newly initialized accounts; posted accounts need explicit audited reconciliation rather than automatic retroactive rewriting.
- Medical/offline evidence is recorded as a reference, not an uploaded attachment with verified contents. Authorities remain responsible for validating the referenced evidence.
- Notifications are stored in the ELM inbox. Email/SMS delivery and automatic reassignment on escalation are not implemented; escalation sends an in-app notification to the configured recipient, with a responsible-user fallback.
- API list endpoints are currently unpaginated except the notification inbox limit. High-volume pagination and a more polished user interface remain future work.

## Run the portable tests on Windows

Open PowerShell in the extracted `ELM_Phase2` directory. Python 3.12+ and Node.js are required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.elm_test -o addopts= -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.elm_test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.elm_test
cd client
npm ci
npm test
npm run build
```

Do not use the SQLite test settings to run a public or production service. The dependencies used for verification are recorded in `evidence/python-dependencies.txt`; frontend versions come from `client/package-lock.json`.

## Run with PostgreSQL and real Fusion IAM

1. Create the virtual environment and install dependencies as above.
2. Copy `.env.example` to `.env`; fill the database password, IAM URL/API prefix, IAM service token and development settings. Keep secrets out of source control.
3. Start PostgreSQL/Redis with `docker compose up -d` when Docker is available, or configure equivalent local services. This computer's setup was not changed.
4. Start a compatible Fusion_System_Administrator development instance separately. Use your own fork or the compatible base version; confirm the contract in `fusion_auth/client.py`.
5. On a clean/backed-up development database:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.dev
.\.venv\Scripts\python.exe manage.py seed_modules --settings=config.settings.dev
.\.venv\Scripts\python.exe manage.py sync_directory --settings=config.settings.dev
```

6. Import the generated `registry/permissions.json` using the IAM's supported permission-manifest workflow, and grant the ELM module plus appropriate employee, authority or administrator permissions. Integrated `seed_modules` alone does not grant IAM access.
7. Using an authorized administrator session, configure employee records and routes, then publish the holiday/RH calendar through the endpoints below. All identities must exist in the Fusion directory. For example, configure authorities before submitting applications that route to them.
8. Import the published academic vacation periods when VL is needed. Use JSON with `source_reference`, `start_date`, `end_date` fields:

```powershell
.\.venv\Scripts\python.exe manage.py elm_import_vacations published-vacations.json --settings=config.settings.dev
.\.venv\Scripts\python.exe manage.py elm_audit_data --settings=config.settings.dev
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8002 --settings=config.settings.dev
```

9. In another terminal run `cd client`, `npm ci`, then `npm run dev`. Sign in through the Fusion shell; ELM appears when the real IAM grants it.
10. Test Faculty, Staff, Substitute, Unit Head, higher authority, Director and Leave Administrator behavior with distinct development accounts. Confirm that an ordinary employee cannot access another person's applications or approval queue.

## API examples

All routes below are relative to `/api/v1/elm/`. Use your normal authenticated Fusion development session and CSRF token. Scripts can use an existing authorized `Authorization: Token ...` credential; do not paste credentials into the report.

Employee configuration example, POST `admin/employees/`:

```json
{
  "user_id": "1001", "kind": "staff", "unit": "Administration",
  "designation": "Assistant", "coverage_required": true,
  "routes": {
    "CL": [{"user_id":"1002","role":"unit_head"}],
    "RH": [{"user_id":"1002","role":"unit_head"}],
    "SCL": [{"user_id":"1002","role":"unit_head"},{"user_id":"1003","role":"director"}],
    "EL": [{"user_id":"1002","role":"unit_head"},{"user_id":"1003","role":"director"}],
    "COL": [{"user_id":"1002","role":"unit_head"},{"user_id":"1003","role":"director"}]
  },
  "escalation_user_id": "1003"
}
```

Replace sample IDs with actual employees and configure their profiles too. Supported processing roles include `unit_head`, `establishment`, `deputy_registrar`, `dean`, `registrar`, `director`. An authority must have the matching active IAM role and `elm.leave.approve` permission. Only genuine Directors should receive `is_director=true` and the Director IAM role.

Publish a calendar, POST `admin/calendars/`:

```json
{"year":2026,"closed_dates":["2026-12-25"],"restricted_dates":["2026-11-10"],"publish":true}
```

Configure policy/SLA, POST `admin/policy/`:

```json
{"reminder_hours":24,"escalation_hours":48,"medical_evidence_required":true}
```

Employee operations: GET/POST `leaves/`; GET `balances/?year=2026`; POST `leaves/{id}/withdraw/` with `reason`; POST `leaves/{id}/replace-substitute/` with `substitute_id`; POST `leaves/{id}/cancel/` with `reason`; POST `leaves/{id}/extend/` with `end_date`, `reason` and optional `substitute_id`/`evidence_reference`; POST `leaves/{id}/resume/` with actual resumption in `end_date` and `reason`; GET `leaves/{id}/export/`, `notifications/`, `ledger/`.

Decision operations: GET `substitute-queue/` and POST `substitute-queue/{id}/decision/` with `accept` and `remarks`; GET `approvals/` and POST `approvals/{id}/decision/` with `approve` and `remarks`. `approve=false` at an intermediate higher-leave stage records Not Recommended and continues; it is final rejection only at the final authority.

Administrator operations: POST `offline/` accepts the application fields plus `employee_id`, `sanction_reference` and `unavailable_reason`; POST `leaves/{id}/maintenance/` accepts only `remarks`.

The generated schema at `openapi/fusion-integrated.v1.yaml` describes the request/response types. API errors use Fusion's standard error envelope.

## Scheduled operations

```powershell
# Invoke periodically; events are emitted only for still-pending tasks.
.\.venv\Scripts\python.exe manage.py elm_process sla --settings=config.settings.dev
# Invoke after the configured calendar year has ended, then reconcile any exceptions.
.\.venv\Scripts\python.exe manage.py elm_process year-end --year 2026 --settings=config.settings.dev
```

Year-end processing is idempotent per employee/year and reports pending/ambiguous accounts as exceptions rather than guessing. No scheduler is bundled or installed.
