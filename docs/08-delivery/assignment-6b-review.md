# Assignment 6B — implementation and verification

## Baseline preserved

The supplied `Fusion-Integrated_1.zip` is retained unchanged in the uploaded
attachments. SHA-256:
`93c17c577c90290a6a318336dfcd92f21e40cbd06d893bcc766e6254e6272977`.
Its application files were integrated into the existing Fusion-Integrated
checkout without copying its Git metadata or replacing local configuration.
The ZIP is the supplied baseline; its Phase-1 provenance was not independently
verified. Keep it alongside the final source when submitting the assignment.

The user reports Qwen 2.5:8b as the original selected model. That offline model
is unavailable for this session. Changes here were implemented using the
current assistant and ordinary engineering tools; no Qwen execution is claimed.

## Existing implementation

The supplied module contains Django models, migrations, domain rules, services,
selectors, REST endpoints, and React pages. It registers with Fusion's module
registry, permission manifest, navigation, URL routing, and Celery schedule.
Identity remains delegated to the existing IAM integration.

Implemented workflows include applying for leave; substitute consent and
renomination; unit-head review; establishment routing; final sanction;
withdrawal; cancellation; extension; resumption; annual credits and year-end
processing; holiday calendars; offline records; corrections; and SLA reminders.
The ledger records balance changes separately from request state transitions.

## Improvements beyond the supplied ZIP

1. **Hierarchy integrity:** `save_unit` previously rejected only a direct
   self-parent. It accepted moving Academics under its child CSE, creating a
   cycle. It now validates the entire parent chain and rejects existing cycles
   too. Hierarchy rows are locked in a stable order during updates.
2. **Reserved balances:** an administrator could subtract seven of eight CL
   days while a pending request reserved two. The request could later be
   approved and produce a negative balance. Corrections now preserve pending
   reservations, while still permitting use of exactly the unreserved balance.

Four regression tests were added in
`modules/leave/tests/test_administration_regressions.py`. Before the fixes,
three failed and one passed. After the fixes all four passed. The concurrent
reparenting behavior was not separately stress-tested.

## Validation performed

- `DJANGO_SETTINGS_MODULE=config.settings.test make check`: passed after the
  fixes, running all 546 backend tests, Django checks, migration consistency,
  Ruff, five import-boundary contracts, foreign-key and plural-contract checks,
  navigation consistency, permission manifest, and OpenAPI schema comparison.
- `make check-client`: passed TypeScript checks, 37 tests across five files,
  and the production build. The build reports an advisory bundle-size warning.
- Applied `leave.0001_initial` successfully to local PostgreSQL.
- Ran `seed_modules` and `seed_leave_policy` successfully.
- Restarted Django; `/readyz` returned database/cache/broker all `ok`.
- Requested the Leave API through Vite; anonymous access returned HTTP 401.
- `git diff --check`: passed.

Backend API tests exercise the workflows with a fake IAM, including permission
denials, ownership scoping, assigned reviewers, and concurrent application
protection. These tests do not establish live IAM interoperability or a complete
browser-driven employee journey.

## Running locally

From the repository root:

```sh
docker compose up -d --wait
make migrate
.venv/bin/python manage.py seed_modules
.venv/bin/python manage.py seed_leave_policy
make dev
```

In another terminal, run `npm run dev` from `client/`. Dependencies are already
installed in `.venv` and `client/node_modules`. The ignored `.env` holds local
database configuration; do not include it in a submission or source archive.

## Remaining external configuration and assessment limits

`manage.py leave_readiness` currently reports six configuration gaps: no
published holiday calendar for 2026, no unit with a configured Unit Head, and
no sanctioning authority for SCL, EL, COL, or VL. Configure real institute data
through the Leave administration APIs/pages; it was not fabricated for setup.
IAM must also supply employee identity, module grants, and role permissions for
live login. Production background processing needs a Celery worker and beat,
including consumption of the notifications queue.

The Assignment 6B brief describes the engineering process, but the separate
complete ELM specification package was not supplied. Business-rule references
in the code were reviewed as implementation claims, not independently verified
requirements. Full specification compliance and deployment readiness therefore
remain unverified. The offline-model iteration requirement also cannot be
claimed for this session.

An unrelated base-project defect remains: `make seed` invokes `seed_demo`, whose
published placement posting has no description and violates
`posting_published_has_required_content`. Use the targeted module seed commands
above; that placement defect was not changed in this Leave implementation task.
