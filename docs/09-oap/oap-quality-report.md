# OAP — quality report

Module `oap`. Spec: Other Academic Procedures, Problem Statement v1.4, Requirement
Registry CFR/AFR v1.2, Use Cases v1.4, Business Rules v1.4, Workflows v1.4, Traceability
Matrix v1.2. Blueprint: [oap-blueprint.md](oap-blueprint.md).

## Status

Builder's report. **No independent review has been run.** The review prompt
(`module-review-prompt.md`) is not present in this checkout, so no 10/10 scorecard exists.
The module is not ready for the pull request until a reviewer scores it 10/10 in all nine
dimensions and Student 2's spec tests pass.

## Approvals

| Item | Approved by | Where | Date |
|---|---|---|---|
| Blueprint (`oap-blueprint.md`) | module owner (Nirvan Jain) | chat | 2026-11-23 |
| `config/celery.py` change (OAP timers merged) | module owner | chat | 2026-11-23 |
| Blueprint, Student 2 written approval | _pending_ | — | — |
| Any new dependency | none | — | — |
| Changes outside `modules/oap/`, `client/src/modules/oap/`, `docs/09-oap/` | `config/celery.py` (above), `client/src/app/registry.ts` (one registry entry for the client route), generated `openapi/fusion-integrated.v1.yaml` and `registry/permissions.json` | chat (celery) | 2026-11-23 |

## Gates (run on the working tree, after the last change)

| Gate | Result |
|---|---|
| `manage.py check` | no issues |
| `makemigrations --check --dry-run` | no changes |
| `lint-imports` | 5 contracts kept, 0 broken |
| `ruff check .` | passes |
| `ops/checks/no_cross_module_fk.py` | passes |
| `ops/checks/contracts_are_plural.py` | passes |
| `ops/checks/nav_matches_routes.py` | passes (14 nav items, 14 routes) |
| `permission_manifest --check` | matches |
| `schema-check` (OpenAPI) | matches |
| `pytest -q` (full suite, includes `modules/oap/tests`) | passes |
| `make check-client` (typecheck, test, build) | passes; 39 client tests, 5 files |
| `make e2e` | target does not exist in this Makefile; not run |

## Module tests (builder's, from the prompt's §5)

31 backend tests in `modules/oap/tests/`, plus the client hook tests in
`client/src/modules/oap/api/hooks.test.tsx`.

- Domain: every illegal transition in each machine is refused (enumerated from the table);
  claim path order; no-dues derivation; both supervisor roles required.
- Registry: every granted and nav permission is declared; no retired spec id is cited.
- API: both gates separately (module grant without permission, permission without module
  grant); student cannot decide leave even holding the HoD designation; cross-student access
  is 404; two-designation principal sees only the acting role's rows; bonafide decision
  requires verification; certificate refused before approval; no-dues finalize refused while
  pending; the Librarian records only the library domain; claim refused without both
  supervisors; supervisor cannot verify a claim not assigned to them; department cannot
  forward before both verifications; thesis reassignment supersedes; TA assignment needs a
  course or faculty; seminar schedule and faculty visibility; seminar schedules refused
  without the permission; reminders silent without a policy.

Not written by the builder: concurrency tests (§5.7, real threads), query budget tests (§5.8),
schedule presence test (§5.9), the full adversarial pass (§5.11). These are open.

## Known gaps (from the blueprint, unchanged)

- G1 PG status: `PG Student` designation unconfirmed.
- G2 Department, Academic Section and Student Section verifiers have no designation; their
  no-dues results cannot be recorded.
- G3 The Department verifier is not checked against the student's department.
- G4 Role-holder recipients are not resolved; only claim supervisors receive notifications and reminders.
- G5 Certificates return availability metadata, not a file.
- G6 No reminder policy is seeded; reminders stay off until `oap_set_reminder_policy` runs.
- G7 No supervisor or department send-back path (per spec).
- G8 Leave documents are Drive links with no size or type rule.
- G9 Seminar schedule has only `scheduled_for` and `venue`.
- G10 No withdrawal, cancellation or reschedule (per spec).
- G11 No finance integration (per spec).
- G12 The frontend is built, but its pages are not browser-tested. The browser walkthrough
  in guide Step 10 has not been run.

## Things the builder did by hand

- Replaced an empty `Q()` used with OR in scoping with an explicit match-all clause, because
  an empty Q narrows an OR instead of widening it.
- Replaced f-string permission codes with literal strings so the permission manifest check
  can see that each code is enforced.
- Removed `oap.no_dues_case.review` after the manifest check showed nothing enforced it;
  consolidation is served by the detail view.
- Added a bonafide rule: the decision needs a prior verification (OA-UC-12 M3 before M4).

## Unverified inputs

- Designation spellings (`Head of Department`, `Academic Administrator`, and so on) are the
  spec's actor names, not confirmed against `globals_designation` (G1, G2 open).
- Frontend icon names are Phosphor names chosen by the builder; they have not been seen
  rendering in the portal (guide Step 6.6 is `full-platform` only).
