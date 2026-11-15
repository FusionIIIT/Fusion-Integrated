# Employee Leave Management pilot

This pilot lets an employee submit a pending leave request, list their own requests,
and view their own leave balances. It uses the existing Fusion login, role switcher,
HTTP client and application shell.

The client pages are `/leave/requests` and `/leave/balances`. The API endpoints are
`/api/v1/leave/requests/` and `/api/v1/leave/balances/`. Both require the
`leave_cell` module grant and the matching permission from `modules/leave/registry.py`.
Ownership is taken from the authenticated IAM Principal. Clients cannot set the
employee identifier or request status, and request update/delete methods are disabled.

## Local setup

Follow `docs/08-delivery/role-assignment-guide.md` to configure the shared development
environment and synthetic accounts. Apply migrations, run `manage.py seed_modules`,
regenerate permissions, and publish the manifest to IAM. Assign a test account the
`employee` designation and select it after login. Balance rows must be provisioned
before they appear on the balances page.

## Current scope

This is a create/list/balance pilot. Approval workflows, balance deduction and credit
accounting, detailed leave-category rules, substitute routing, scheduled processing,
and complete requirement traceability are not implemented. It is not a complete ELM
module. No approved implementation blueprint is included.

## Verification

Django startup and migration-consistency checks, permission-manifest checks,
navigation/route parity, cross-module foreign-key checks, frontend typechecking and
a production client build passed. A brief synthetic-account smoke verified login,
request creation, own-request listing and balances. An API smoke checked that another
employee's request and balance are excluded. The full backend/client suites and visual
browser verification were not run.
