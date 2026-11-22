# PHC — Primary Health Care module

The PHC module serves the institute's primary health services from `modules/phc/` (Django app
`modules.phc`) and `client/src/modules/phc/` (sixteen lazy client pages). It owns its business
tables in `fusion_integrated`; identity and access come from the session and the IAM, never
from a local access-control table.

## What it does

- Publishes the weekly doctor schedule with the current day's Available/Departed attendance for patients.
- Lets PHC staff search for a patient, record visits and digitized prescriptions, and lets a patient read only their own history, prescriptions and a real PDF copy of a record.
- Handles the medical bill reimbursement path: employee submission with prescription and 90-day window checks, PHC review, Accounts & Audit verification, Approving Authority sanction (approve or reject), and Accounts & Audit payment. Submitted claims are immutable; a reapplication after rejection is a new claim. Students cannot submit claims. Every status change writes a durable, deduplicated notification to the outbox.
- Tracks inventory stock (over-deduction is rejected, never floored), writes a low-stock outbox notice, and carries procurement requisitions from submission to decision and post-delivery fulfillment. Fulfillment does not change stock; stock changes are a separate staff action.
- Records ambulance usage and publishes health advisories visible to patients.
- Produces anonymized demographic, utilization and inventory reports, and keeps an append-only audit trail enforced by database grants.

Every API request passes two gates: the `phc` module grant from the session and the specific
`phc.*` permission checked by `HasPhcPermission` in `modules/phc/api/permissions.py`.

## Layout

```
modules/phc/
  api/          views (thin gates), serializers, permissions, urls
  domain/       policy.py, state_machine.py, pdf.py   (pure, no Django imports)
  services/     all writes, transactions/locks, audit and notification outbox
  selectors/    scoping.py — all reads, ownership narrowed in the queryset
  contracts.py  get_phc_profiles — the only public surface for other modules
  migrations/   0001_initial, 0002_notificationoutbox
  tests/spec/   canonical 187-test suite (FR, UC, BR, WF + adversarial modules)
```

`domain/`, `services/`, `selectors/`, `contracts.py` and `api/` are enforced by import-linter;
the domain layer may not import Django, DRF or Celery.

## API surface

All routes are mounted at `/api/v1/phc/` by `config/urls.py`; the route table is
`modules/phc/api/urls.py`. Every endpoint carries an `@extend_schema` example; the committed
OpenAPI file is `openapi/fusion-integrated.v1.yaml`.

| Group | Routes | Main methods |
|---|---|---|
| Doctor schedule | `schedule`, `staff/schedule`, `staff/schedule/<pk>`, `staff/schedule/<pk>/publish`, `staff/attendance` | list published schedule with attendance; create, maintain, publish; mark attendance |
| Patient records | `staff/patients/search`, `staff/visits`, `staff/prescriptions`, `records`, `records/prescriptions`, `records/download/<pk>` | staff search and write; patient read-only history, prescriptions and PDF copy |
| Reimbursement | `claims`, `claims/mine`, `staff/claims/<pk>/review`, `audit/claims/<pk>/verify`, `approver/claims/<pk>/sanction`, `audit/claims/<pk>/payment` | submit and track own claims; review → verify → sanction → pay |
| Inventory and requisitions | `staff/inventory/adjust`, `staff/inventory/items`, `staff/requisitions`, `approver/requisitions/<pk>/decide`, `staff/requisitions/<pk>/fulfill` | adjust stock; list/create items; submit, decide, fulfill |
| Ambulance | `staff/ambulance` | create usage log |
| Advisories | `staff/advisories`, `advisories` | publish and list published advisories |
| Reports and audit | `staff/reports`, `audit/log` | anonymized report categories; read the audit trail |

The client mounts these under `/phc` through its `MODULE_REGISTRY` entry; the sixteen sidebar
items and their permission requirements are declared in `modules/phc/registry.py`. Nav icon
names are checked against the Phosphor set by `client/src/test/phc-icon-parity.test.ts`.

## Permissions and role grants

`registry.py` declares 19 permissions: `phc.schedule.view`, `phc.schedule.manage`,
`phc.records.view_self`, `phc.records.manage`, `phc.reimbursement.submit`,
`phc.reimbursement.view_self`, `phc.reimbursement.review`, `phc.reimbursement.verify`,
`phc.reimbursement.sanction`, `phc.reimbursement.payment`, `phc.inventory.adjust`,
`phc.requisition.submit`, `phc.requisition.decide`, `phc.requisition.fulfill`,
`phc.ambulance.log`, `phc.advisory.view`, `phc.advisory.publish`, `phc.reports.generate` and
`phc.audit.view`. There are no system or scoped permissions.

Grants are keyed by designation name as spelled in the ERP:

| Designation | Granted permissions |
|---|---|
| `phc_staff` / `PHC Staff` | schedule manage, records manage, inventory adjust, requisition submit and fulfill, ambulance log, advisory publish, reports generate, reimbursement review |
| `accounts_audit` / `Accounts & Audit` | reimbursement verify, reimbursement payment, audit view |
| `approving_authority` / `Approving Authority` | reimbursement sanction, requisition decide |
| `employee` | schedule view, records view_self, advisory view, reimbursement submit, reimbursement view_self |
| `student` | schedule view, records view_self, advisory view (reimbursement is excluded) |

## Running it

From the repository root:

- `make migrate` applies the module migrations (`0002_notificationoutbox` included).
- `make permissions` refreshes `registry/permissions.json`; the IAM applies it with `manage.py seed_iam_permissions --manifest registry/permissions.json`. Module visibility is granted separately through the IAM.
- `make schema` refreshes the committed OpenAPI file, and `make check` runs the server-side gates (567 tests pass).
- `.venv/bin/python -m pytest modules/phc/tests/spec/` runs the 187 canonical spec tests alone; per-strategy artifacts are in `/home/atharva/Documents/Fusion/spec-results/final/{fr,uc,br,wf}/`.
- In `client/`, `npm run typecheck`, `npm test` (37 tests) and `npm run build` are the client gates; `make check-client` runs all three.
- In `client/`, `npm run test:e2e` runs the Playwright happy path with axe-core WCAG A/AA and keyboard checks. See [`e2e-notes.md`](e2e-notes.md).

The deployment order is migrate → seed modules → grants → IAM permission seeding → first user
action; a fresh-database proof is recorded in
[`phc-quality-report.md`](phc-quality-report.md#fresh-environment-proof). The approved design
is [`phc-blueprint.md`](phc-blueprint.md).
