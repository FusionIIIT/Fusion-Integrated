# PHC operations

## Install and enable

1. Install the Python project dependencies, including the approved `reportlab` dependency.
2. Run `make migrate` to create PHC tables and the initial 30-day reimbursement policy effective 2026-01-01.
3. Run `.venv/bin/python manage.py seed_phc_policy`. It is safe to repeat and refuses a conflicting current policy.
4. Run `.venv/bin/python manage.py seed_modules`; the module readiness hook verifies the policy.
5. Publish `registry/permissions.json` with `make permissions`, then run the IAM's `seed_iam_permissions --manifest /full/path/to/Fusion-Integrated/registry/permissions.json` command. Review every revoke it reports.
6. Assign existing approved designations in IAM/ERP and log in again so the active session receives its current designation grants.
7. Run `.venv/bin/python manage.py phc_readiness`. It prints each unmet prerequisite or `PHC is ready.`

The API and client are mounted at `/api/v1/phc/` and `/phc/`. The module's schedule sends `phc.deliver_notifications` to the `notifications` queue every 60 seconds; production must run Celery beat and a worker consuming that queue.

## Scheduled notification delivery

Run `.venv/bin/python manage.py shell -c 'from modules.phc.tasks import deliver_notifications; print(deliver_notifications.run())'` to process pending outbox rows once. Delivery is safe to retry: the outbox event key and one-to-one notification relation prevent duplicate user notifications. Low-stock alerts are persistent records shown in the inventory alert endpoint; they are not pushed through the notification outbox.

## Medical record export

A patient submits selected own visit IDs to `POST /api/v1/phc/records/pdf`. The response is an `application/pdf` attachment. The service checks every requested visit through the patient-scoped selector before generating content. Export includes the patient user ID, visits in chronological order, visit dates and clinical notes, and every prescription associated with each selected visit. The endpoint uses the `phc_pdf` throttle scope.

## IAM manifest compatibility

The local IAM seeder accepts manifest versions 1 and 2. Version 1 retains its earlier permissive shape; version 2 validates permission definitions, scopes, system permissions, module grants and designation grants before applying any rows. Version 2 remains authoritative for each named module, so operators must review the seeder's revoke list before applying a changed manifest.
