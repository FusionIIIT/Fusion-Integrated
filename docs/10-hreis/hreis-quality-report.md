# HR-EIS backend quality report

**Handoff state:** draft PR prepared for Student 2’s independent specification tests. The assignment’s independent 10/10 review and Student 2 test/review phase have not been performed yet.

## Scope delivered

The branch adds the HR-EIS backend package, API registration, database models and migrations, request services, state transitions, selectors, permission registry entries, OpenAPI and permission-manifest output, a source-ID traceability register, and a generated source reference. The assigned scope is backend only; no client pages or browser tests are included.

## Verification recorded

The latest HR-EIS-focused coverage run reported **57 tests passed**, **96.67% total branch coverage**, and **97.40% domain coverage**, meeting the prompt’s 90% module and 95% domain floors. The test suite covers the core state-machine safeguards, HTTP request privacy and submission, policy and employee administration, claim processing, leave ledger rules, and idempotent retries.

The final check round passed: `ruff check .`; all five `lint-imports` contracts; `no_cross_module_fk.py`; `contracts_are_plural.py`; `nav_matches_routes.py`; the 193-link reference generator; permission-manifest check; migration check; Django system check; warning-free OpenAPI generation with a matching committed schema; and the complete repository test suite. The production deploy check also reported no issues, with two platform checks silenced by the repository configuration.

## Not yet proven or complete

- Student 2’s independent spec-derived tests and review have not started; this draft handoff is intended to let that phase begin.
- Traceability contains 193 live source rows, but each row is marked partial or gap; not every live ID yet has an ID-named behavioral test.
- Policy values and the authority route matrix must be supplied/configured before requests can be used in a real deployment.
- Full HR form schemas, appraisal archival/reviewer lifecycle, LTC Returned transition, policy cadence reminders, email/dashboard delivery, and payroll/finance synchronization remain incomplete or undefined by available contracts.
- The backend stores document references in request JSON; it does not yet implement secure document uploads through `core/files`.
- Fresh deployment with the institute database, IAM grants, and first-user production workflow has not been demonstrated. The full test suite does apply the module migrations to isolated test databases.
- Mutation testing, a separate adversarial review, and a post-Student-2 10/10 review remain outstanding.

## Known operational boundaries

The module does not seed invented leave or appraisal policy. HR administrators must create effective-dated policy versions first. Notification rows are local in-app records only. No HREIS scheduled task is registered because reminder timing and delivery behavior are not specified well enough to schedule safely.
