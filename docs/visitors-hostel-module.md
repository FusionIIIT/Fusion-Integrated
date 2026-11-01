# Visitors Hostel module

This module is implemented for the current Fusion-Integrated repository: Django REST Framework on the server and React, TypeScript, Mantine, and the shared `http` client in the web client. It does not use the earlier Express/Mongoose snippets because those do not match this repository's architecture.

## What is included

- Booking requests, review and approval, room allocation, check-in/out, cancellation and modification requests.
- Room availability checks shared by online and offline requests.
- Configurable room tariffs, meal rates, bills and offline cash settlement records.
- Inventory adjustments, replenishment requests and threshold notifications.
- Stay exception alerts, email outbox delivery, and role-scoped reports.
- API endpoints, server-driven navigation, client pages, tests, and an initial database migration.

## Architecture and authorization

Fusion owns identity and permissions. The module stores external user identifiers as integers and does not create cross-module foreign keys. `registry.py` declares intended permission grants; `registry/permissions.json` is generated from module registries. The module remains `planned` until its IAM module grant and designation identifiers are configured by the platform. Configure operational caretaker and VH In-Charge assignments before relying on role-directed notifications.

The role grant table gives tariff management to VH In-Charge. Caretaker can record offline requests but cannot create online requests. Only VH In-Charge can approve or reject forwarded requests. Report types are restricted by role on the server.

## Integration

Copy `modules/visitors_hostel/` and `client/src/modules/visitors_hostel/` into a matching Fusion-Integrated checkout. Apply the included `integration.patch` for settings, API URL inclusion, Celery registration, client route registration, and import-boundary configuration. Regenerate the permission manifest after modifying module grants:

```powershell
python manage.py permission_manifest
```

Create or verify the migration using the target repository environment, then migrate its configured database:

```powershell
python manage.py makemigrations visitors_hostel
python manage.py migrate
```

The module intentionally does not invent platform-level role assignment, email templates/recipients beyond the configured role and visitor email fields, or rate values. Configure tariffs and meal rates before creating billable allocations or meal requests. Configure email delivery in the host application.

## Checks

Run focused tests and repository checks from the Fusion-Integrated root:

```powershell
python -m pytest modules/visitors_hostel/tests -q
python manage.py check
python ops/checks/no_cross_module_fk.py
python ops/checks/contracts_are_plural.py
python ops/checks/nav_matches_routes.py
python manage.py permission_manifest --check
lint-imports
```

The implementation was checked with the focused domain tests, Django system check, module-boundary checks, navigation check, permission manifest check, Python compilation, and Import Linter. Client typecheck/build/browser tests still need to be run in an environment with the repository's Node dependencies installed.
