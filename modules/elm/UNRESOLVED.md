# ELM Phase 2 — unresolved gaps

Honest accounting of what the complete ELM spec (BR-EL-001..038, CW-EL-01..04)
requires that this build does NOT implement. Not a to-do wishlist — these are
known-missing, not attempted-and-broken.

## Environment
**UPDATE (commit 69a0f73):** a Python 3.12 environment was obtained (prebuilt via `uv`, isolated, no system changes). `manage.py check` passes (0 issues); `makemigrations --check` is clean; `migrate elm`+`migrate directory` apply cleanly on a local SQLite substitute; the full submit/decide/withdraw/cancel/substitute service-layer lifecycle actually ran and passed (`modules/elm/tests/test_services.py`, 6/6). Still NOT run: `manage.py test`/full `migrate`, which touch every installed app and hit a pre-existing, unrelated `modules/placement` migration that is Postgres-specific and fails under SQLite — needs this project's real Postgres to verify. Full elm suite (pytest-django, `--no-migrations`, SQLite): 21/21 passing — real evidence, but against a non-Postgres substitute, not re-verified against the real DB.

- Full Django stack (`make install/up/migrate/dev`) could not run: this
  machine has Python 3.10, the project requires >=3.12, and building the
  one dependency without a 3.10 wheel (`rpds-py`) from source needs a Rust
  toolchain whose installer is blocked by this network's proxy (403).
  `manage.py check/migrate/test` were never executed. All Django-dependent
  code (models, migrations, selectors, services, api) is verified only by
  `ast.parse` + manual review, not by running it.
- The `modules/elm/domain/rules.py` pure-Python layer has NO Django import,
  so it's genuinely unit-tested with plain `python3 -m unittest` — 15/15
  passing (see commit). This is the only code path with real execution
  evidence.

## Frontend — not implemented at all

This build is backend-only. No client-side (React) code for ELM exists
anywhere in `client/src`.

- `registry.py`'s `NAV_ITEMS` declares three sidebar links
  (`/elm/my-requests`, `/elm/apply`, `/elm/approvals`), so the server-driven
  sidebar WILL show "Leave" / "Employee Leave Management" to any
  principal holding the relevant permission.
- Every one of those links currently goes nowhere: `client/src` has no
  ELM routes, no pages, nothing. Clicking any of them would hit the
  client's NotFound route. Confirmed by the repo's own check:
  `ops/checks/nav_matches_routes.py` fails with exactly these three
  mismatches, and is part of `make check`.
- Net effect: ELM is reachable only via direct HTTP calls to
  `/api/v1/elm/*` (curl, Postman, the test suite). There is no way for an
  actual user to submit, view, or decide on a leave request through
  Fusion's UI.
- Not attempted in this repair pass — out of scope per instruction. Building
  the three pages (My Leave Requests, Apply for Leave, Leave Approvals) is
  the next real step before this module is usable, separate from any of the
  backend gaps below.

## Not implemented at all
- **Entitlement/balance accounting** (BR-EL-002–009, 025, 027–028): no
  per-category annual entitlement, no carry-forward, no VL→EL year-end
  conversion. `LeaveRequest` has no balance field. BR-EL-023's "restores
  already-deducted balance" on cancellation is therefore a no-op here —
  only the status transitions.
- **Higher-sanction routing beyond Unit Head** (BR-EL-018, 019): for
  SCL/EL/COL/VL, a Unit Head recommendation is recorded
  (`unit_head_recommended` / `unit_head_not_recommended`) and the request
  stops there — it never reaches `approved`/`rejected`. No Dean/Registrar/
  Director/Establishment step exists. Faking a final decision here would
  misrepresent an unenforced rule, so it's left genuinely incomplete rather
  than stubbed.
- **Extension** (BR-EL-025) and **Resumption** (BR-EL-027/028): no
  endpoints, no model fields.
- **Year-end processing** (section 13 of the Problem Statement).
- **SLA reminders/escalation** (BR-EL-032/033/035/038): no scheduler, no
  threshold config, no notification delivery.
- **Offline-sanctioned leave entry** (BR-EL-029/037): no Leave
  Administrator retrospective-entry endpoint.
- **Substitute re-nomination after decline** (BR-EL-015's second sentence):
  a decline is recorded, but the applicant can't nominate a replacement —
  only withdraw-and-resubmit.
- **Holiday/RH calendar** (BR-EL-003, 031) and **Academic Calendar
  vacation periods** (BR-EL-006): RH/VL requests are accepted by category
  alone; no calendar-applicability check exists.
- Admin UI/config endpoints for policy parameters and hierarchy
  (BR-EL-030) and SLA thresholds (BR-EL-038).

## Implemented and spec-checked (this build's actual scope)
- BR-EL-001 (category set), BR-EL-010 (half-day CL only), BR-EL-012
  (overlap incl. half-day exception), BR-EL-013 (Station Leave fields on
  the same application), BR-EL-014/015 (substitute eligibility + consent
  gate, decline recorded), BR-EL-016 (Unit Head final for CL/RH),
  BR-EL-017 (Unit Head recommendation for SCL/EL/COL/VL, see routing gap
  above), BR-EL-022/034 (withdraw only while pending), BR-EL-023 (cancel
  only approved + pre-start, balance caveat above), BR-EL-036
  (role-based authorization via `HasModuleGrant`/`HasPermission` on every
  endpoint — 6 real HTTP-level tests in
  `modules/elm/tests/test_api_authorization.py`: anonymous rejected,
  module-not-granted rejected, missing-specific-permission rejected,
  authorized employee submit/list, authorized Unit Head decide,
  decide-without-permission rejected; full suite 27/27).

**Caveat — authorization seeding not verified:** the above tests prove
`HasModuleGrant`/`HasPermission` enforce correctly *given* a session that
already carries `modules`/`permissions` (via `stub_iam`, which sets those
directly on the fake session). They do NOT exercise the real seeding
pipeline (`manage.py seed_modules`, which is supposed to read
`registry.py`'s `ROLE_GRANTS`/`PERMISSIONS` into the actual grants
table) — that command was not inspected or run. So "the DRF permission
logic is correct" is verified; "a Unit Head actually receives
`elm.leave_request.decide` in a real deployment" is not.
