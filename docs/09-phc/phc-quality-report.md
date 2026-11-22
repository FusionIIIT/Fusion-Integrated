# PHC — Quality report

This report describes the final A9 tree on branch `phc-21`. All figures were captured on
2026-11-22 from the working tree described in the run records listed under **Gates**.

## Blueprint approval

The PHC blueprint ([`phc-blueprint.md`](phc-blueprint.md)) was approved by Student 2
(Vikrant Kumar, roll 24BCS160) on 2026-11-22 before implementation began. The approved
Step 3 sections and the live/retired id map are retained in that document.

## Architecture

`modules/phc/api/views.py` is a thin transport layer: it parses input, applies the two
authorization gates and serialises output. The rules live below it:

| Layer | Files | Responsibility |
|---|---|---|
| `domain/` | `policy.py`, `state_machine.py`, `pdf.py` | Pure policy, declarative transition tables, PDF bytes. No Django/DRF/Celery import. |
| `services/` | `audit.py`, `notifications.py`, `schedules.py`, `records.py`, `claims.py`, `inventory.py`, `ambulance.py`, `advisories.py`, `reports.py` | All writes, `transaction.atomic` + `select_for_update`, outbox writes, append-only audit. |
| `selectors/scoping.py` | one module | All reads; ownership narrows the queryset so a foreign id is 404. |
| `contracts.py` | `get_phc_profiles` | The only public surface other modules may import. |
| `api/` | `views.py`, `serializers.py`, `permissions.py`, `urls.py` | Transport only. |

`.importlinter` enforces 5 contracts (up from 4), including the PHC layering and the rule
that domain must not import Django, DRF or Celery: **5 kept, 0 broken**.

## Spec-id coverage

Ids come from the PHC v1.1 specification set. Paths are relative to `/api/v1/phc/`. The
v1.1 use-case registry has 20 live ids (01–16 and 19–22); PHC-UC-17 and PHC-UC-18 are marked
`Retired` and are not claimed. The historical `FR-PHC-nnn` numbering survives only as the
verbatim text of `AFR-PHC-nnn`; all enforcement below cites the AFR id.

Enforcement is named at the service/domain function that holds the rule; the view that
calls it remains the HTTP gate.

### Coherent requirements

| Spec id | Where implemented |
|---|---|
| CFR-PHC-001 | `services/schedules.py::{create,maintain,publish,mark_attendance}`, `selectors/scoping.py::{published_schedules,attendance_on}` |
| CFR-PHC-002 | `services/records.py::{search,create_visit,create_prescription,record_copy}`, `selectors/scoping.py::{visits_for,prescriptions_for}` |
| CFR-PHC-003 | `services/claims.py::submit`, `domain/policy.py::{is_reimbursable_kind,expense_within_window}` |
| CFR-PHC-004 | `domain/state_machine.py::CLAIM_TRANSITIONS`, `services/claims.py::advance`, `services/claims.py::submit` for reapplication |
| CFR-PHC-005 | `selectors/scoping.py::claims_for`, `services/audit.py::record`, `services/claims.py::advance` |
| CFR-PHC-006 | `services/inventory.py::adjust_stock`, `domain/policy.py::{stock_after_adjustment,is_low_stock}`, `services/notifications.py::low_stock_notice` |
| CFR-PHC-007 | `services/inventory.py::{submit_requisition,decide_requisition,fulfill_requisition}`, `services/notifications.py::requisition_notice` |
| CFR-PHC-008 | `services/ambulance.py::log_usage` |
| CFR-PHC-009 | `services/advisories.py::publish`, `selectors/scoping.py::published_advisories` |
| CFR-PHC-010 | `services/reports.py::generate` (demographics, utilization, inventory) |
| CFR-PHC-011 | `api/permissions.py::_HasPhcPermission.has_permission`, `registry.py::{PERMISSIONS,ROLE_GRANTS}` |
| CFR-PHC-012 | `services/audit.py::record`, `selectors/scoping.py::audit_logs`, `ops/db/roles.sql` |

### Atomic requirements

| Spec id | Where implemented |
|---|---|
| AFR-PHC-001 | `selectors/scoping.py::{published_schedules,attendance_on}` |
| AFR-PHC-002 | `services/schedules.py::maintain` |
| AFR-PHC-003 | `services/schedules.py::mark_attendance` |
| AFR-PHC-004 | `services/schedules.py::create` |
| AFR-PHC-005 | `services/schedules.py::publish` (`is_published`, `published_at`) |
| AFR-PHC-006 | `services/records.py::search` |
| AFR-PHC-007 | `services/records.py::create_visit` |
| AFR-PHC-008 | `services/records.py::create_prescription` (visit/patient link checked) |
| AFR-PHC-009 | `selectors/scoping.py::visits_for` |
| AFR-PHC-010 | `selectors/scoping.py::prescriptions_for` |
| AFR-PHC-011 | `services/records.py::record_copy`, `domain/pdf.py::render_pdf` (real PDF bytes) |
| AFR-PHC-012 | `selectors/scoping.py::{visits_for,prescriptions_for}`, `api/permissions.py` |
| AFR-PHC-013 | `domain/policy.py::is_reimbursable_kind` |
| AFR-PHC-014 | `selectors/scoping.py::prescription_for_claimant` |
| AFR-PHC-015 | `domain/policy.py::expense_within_window` (90 days; future dates rejected in `serializers.py`) |
| AFR-PHC-016 | `services/claims.py::submit` (creates `submitted`) |
| AFR-PHC-017 | `domain/state_machine.py::CLAIM_TRANSITIONS`; each view filters on the required from-state |
| AFR-PHC-018 | `services/claims.py::advance(..., "review")` |
| AFR-PHC-019 | `services/claims.py::advance(..., "verify")` |
| AFR-PHC-020 | `services/claims.py::advance(..., "sanction_approve" / "sanction_reject")` |
| AFR-PHC-021 | `services/claims.py::advance(..., "payment")` |
| AFR-PHC-022 | `selectors/scoping.py::claims_for` (own claims with `action_history`) |
| AFR-PHC-023 | `services/claims.py::advance` (`action_history` + audit + outbox notice) |
| AFR-PHC-024 | `services/inventory.py::adjust_stock` (over-deduction is a 422, not floored) |
| AFR-PHC-025 | `domain/policy.py::is_low_stock` (strict `<`) |
| AFR-PHC-026 | `services/inventory.py::adjust_stock`, `services/notifications.py::low_stock_notice` |
| AFR-PHC-027 | `services/inventory.py::submit_requisition` (unknown item ids rejected) |
| AFR-PHC-028 | `services/inventory.py::{submit_requisition,decide_requisition}` |
| AFR-PHC-029 | `domain/state_machine.py::REQUISITION_TRANSITIONS`, `services/inventory.py::decide_requisition` |
| AFR-PHC-030 | `services/inventory.py::decide_requisition`, `services/notifications.py::requisition_notice` |
| AFR-PHC-031 | `services/inventory.py::fulfill_requisition` (no stock posting) |
| AFR-PHC-032 | `services/ambulance.py::log_usage` |
| AFR-PHC-033 | `services/advisories.py::publish`, `selectors/scoping.py::published_advisories` |
| AFR-PHC-034 | `services/reports.py::generate` (three categories) |
| AFR-PHC-035 | `services/reports.py::generate` (counts/aggregates only, no patient identifiers) |
| AFR-PHC-036 | `api/permissions.py`, `registry.py::ROLE_GRANTS` |
| AFR-PHC-037 | `services/audit.py::record`, `selectors/scoping.py::audit_logs` |
| AFR-PHC-038 | `services/claims.py::submit` and `domain/state_machine.py::CLAIM_TRANSITIONS`; no edit/reopen route |

### Use cases

| Spec id | Where implemented |
|---|---|
| PHC-UC-01 | `selectors/scoping.py::{published_schedules,attendance_on}` |
| PHC-UC-02 | `selectors/scoping.py::{visits_for,prescriptions_for}` |
| PHC-UC-03 | `services/records.py::record_copy` |
| PHC-UC-04 | `services/claims.py::submit` |
| PHC-UC-05 | `selectors/scoping.py::claims_for` |
| PHC-UC-06 | `services/records.py::{create_visit,create_prescription}` |
| PHC-UC-07 | `services/schedules.py::maintain` |
| PHC-UC-08 | `services/schedules.py::mark_attendance` |
| PHC-UC-09 | `services/inventory.py::{adjust_stock,create_item}` |
| PHC-UC-10 | `services/inventory.py::submit_requisition` |
| PHC-UC-11 | `services/ambulance.py::log_usage` |
| PHC-UC-12 | `services/advisories.py::publish` |
| PHC-UC-13 | `services/reports.py::generate` |
| PHC-UC-14 | `services/inventory.py::fulfill_requisition` |
| PHC-UC-15 | `services/claims.py::advance(..., "review")` |
| PHC-UC-16 | `services/inventory.py::decide_requisition` |
| PHC-UC-19 | `services/claims.py::advance(..., "verify")` |
| PHC-UC-20 | `services/claims.py::advance(..., "sanction_*")` |
| PHC-UC-21 | `services/claims.py::advance(..., "payment")` |
| PHC-UC-22 | `services/schedules.py::{create,publish}` |

### Business rules

| Spec id | Where implemented |
|---|---|
| PHC-BR-01 | `selectors/scoping.py::{published_schedules,attendance_on}` (one combined response) |
| PHC-BR-02 | `selectors/scoping.py::{visits_for,visits_for_patient,prescriptions_for}` |
| PHC-BR-03 | Every `permission_classes` declaration plus `HasModuleGrant("phc")` |
| PHC-BR-04 | `domain/policy.py::is_reimbursable_kind` |
| PHC-BR-05 | `selectors/scoping.py::prescription_for_claimant` |
| PHC-BR-06 | `domain/policy.py::expense_within_window` |
| PHC-BR-07 | `domain/policy.py::is_low_stock` |
| PHC-BR-08 | `domain/state_machine.py::CLAIM_TRANSITIONS` (no backward edge exists) |
| PHC-BR-09 | `services/audit.py::record` + `ops/db/roles.sql` (INSERT/SELECT only) |
| PHC-BR-10 | `domain/state_machine.py::REQUISITION_TRANSITIONS` |
| PHC-BR-11 | `services/notifications.py::requisition_notice` (durable deduplicated outbox row) |
| PHC-BR-12 | `services/reports.py::generate` |
| PHC-BR-13 | `services/notifications.py::claim_status_notice` |
| PHC-BR-14 | `domain/state_machine.py::CLAIM_TRANSITIONS` (terminal states) |

### Workflows

| Spec id | Where implemented |
|---|---|
| BW-PHC-01 | `claims.submit → advance("review") → advance("verify") → advance("sanction_approve") → advance("payment")` |
| BW-PHC-02 | `claims.submit → advance("review") → advance("verify") → advance("sanction_reject")` (terminal) |
| BW-PHC-03 | `inventory.submit_requisition → decide_requisition("approve") → fulfill_requisition` |
| BW-PHC-04 | `inventory.submit_requisition → decide_requisition("reject")` (terminal) |

The two composite workflow ids are the union of the step sequences in the two pairs of basis
workflows above; they share those endpoints and have no separate code path.

## Previously open items — now closed

Two specification details recorded as gaps at the earlier review are now fully implemented:

- **AFR-PHC-011 / PHC-UC-03 — real PDF.** `services/records.py::record_copy` renders bytes via
  `domain/pdf.py::render_pdf`. `test_wf_adv_record_pdf_has_bytes_and_own_content` asserts
  `%PDF-1.4`, the record's own medicine and notes, and `%%EOF`.
- **AFR-PHC-023, AFR-PHC-030, PHC-BR-11 and PHC-BR-13 — notifications.**
  `services/notifications.py::{claim_status_notice,requisition_notice,low_stock_notice}` write
  deduplicated `NotificationOutbox` rows inside the source transaction. The BR adversarial
  module asserts recipient, channel/topic, subject, body, payload and the audit side effect.

Other findings closed in the same pass: thin API views; 27 `@extend_schema` examples (one per
endpoint) with a regenerated OpenAPI file; permission codes renamed from
`phc.inventory.requisition.*` to `phc.requisition.*` (manifest, catalog and schema regenerated);
valid Phosphor icons with a client parity test; `?limit=abc` returns a 400; over-deduction is a
422 with no partial write; unknown requisition items are a 422; future expense dates are a 400;
transaction locks and stale-version 409s on all transitions; and the defect where four views
passed `expected_updated_at` as the `note` argument. A second independent pass found two more
issues, both closed: the client fetched the PDF download as JSON and crashed the record drawer
(it now buffers a blob and saves it, with a Playwright regression case), and `ops/db/roles.sql`
was silently ignored by the global `*.sql` rule (an explicit negation now keeps it in the
commit). A third pass found two more issues, also closed: `services/reports.py::generate` now
runs its audit write inside `@transaction.atomic`, and `MAX_INT4` bounds on serializer integer
fields turn oversized stock/reorder/requisition values into validation errors instead of
unhandled 500s. A fourth pass found four more, all closed: the committed OpenAPI schema was
stale and is regenerated; a negative `reorder_threshold` is now a 400 (`min_value=0`); two
cumulative near-limit adds can no longer overflow the int4 column because the shared
`domain/policy.py::MAX_INT4` ceiling raises `StockOverflow`, translated by
`services/inventory.py` into a 400 with code `stock_overflow`; and this report's gate figures
were corrected to the final passing values. A fifth pass found four more, all closed:
`max_length` bounds on `dosage` (120), `unit` (40) and `reason` (200) turn over-length strings
into 400s before they can overflow their `varchar` columns, and duplicate doctor/day schedule
create or maintain is pre-checked and guarded with a savepoint, raising 409 `schedule_exists`
instead of an unhandled `IntegrityError`. The same robustness sweep found and closed a fifth
500 path: a staff requisition originator who had never been a patient had no `phc_patient`
row for the `originator` FK, so `services/inventory.py::submit_requisition` now projects the
IAM principal with `get_or_create` before writing the requisition.

### Remaining open question (not a gap in the promised scope)

The specification does not name a consumer for the `NotificationOutbox`. The module guarantees
the durable, deduplicated row with recipient and content; whether the platform delivers it by
in-app list, email or SMS is a platform-owner decision and is not guessed here. There are no
scheduled tasks: `SYSTEM_PERMISSIONS` is empty.

## Changes outside module folders

Every line below was approved by Student 2. No access-control table was added and no other
module's business code was changed.

- `config/settings/base.py` — `DOMAIN_MODULES` entry `"modules.phc"`; rate limit `"phc_submit": "10/hour"`.
- `config/urls.py` — `path("api/v1/phc/", include("modules.phc.api.urls"))`.
- `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`, `openapi/fusion-integrated.v1.yaml` — regenerated from the registries and annotated views; `permission_manifest --check` and `schema-check` both pass.
- `.importlinter` — PHC added to four architecture contracts (five total).
- `ops/db/roles.sql` — idempotent role/grant block; `platform_app` has INSERT+SELECT on `phc_audit_log` and no UPDATE/DELETE.
- `client/src/app/registry.ts` — `phc` registry entry with lazy routes.
- `client/package.json`, `client/package-lock.json` — Playwright + axe-core dev dependencies and `test:e2e` script.
- `client/src/ui/components/{DataTable,PageHeader}.tsx`, `client/src/ui/layout/AppShellLayout.tsx` — dimmed text and Logout colours darkened to pass WCAG AA (shared shell, needed by the PHC axe run).
- `client/src/test/phc-icon-parity.test.ts` — asserts every nav icon is a valid Phosphor name.
- Deleted from the working tree: `modules/phc/tests/a8/`, `modules/phc/a8_design/` and `modules/phc/a8_results/`. Their contents are frozen in the submitted A8 ZIP; the canonical A9 suite is `modules/phc/tests/spec/`.

## Gates

Run from the repository root on 2026-11-22; consolidated output in `/tmp/opencode/a9-final-gates.log`.

| Gate | Result | Observed |
|---|---|---|
| `manage.py check` | PASS | No issues (0 silenced). |
| `manage.py makemigrations --check --dry-run` | PASS | No changes detected. |
| `ruff check .` | PASS | All checks passed. |
| `lint-imports` | PASS | 5 contracts kept, 0 broken. |
| `ops/checks/no_cross_module_fk.py` | PASS | no cross-module foreign keys. |
| `ops/checks/contracts_are_plural.py` | PASS | all contract getters are plural. |
| `ops/checks/nav_matches_routes.py` | PASS | nav items and client routes agree. |
| `manage.py permission_manifest --check` | PASS | permission manifest matches the registries. |
| `schema-check` | PASS | openapi schema matches the code. |
| full `pytest` (in `make check`) | PASS | **567 passed, 0 failed, 0 skipped** in 11.55s. |
| `pytest modules/phc/tests/spec/` | PASS | **187 passed**, 0 failed, 0 skipped. |
| `client: npm run typecheck` | PASS | clean. |
| `client: npm test` | PASS | 5 files, 37 tests passed. |
| `client: npm run build` | PASS | Vite build succeeded (chunk-size advisory only). |
| `cd client && npx playwright test` | PASS | 2 passed: schedule loads (axe WCAG A/AA clean, keyboard reachable); record drawer renders and downloads a real PDF. |

Per-strategy spec results with JUnit, Cobertura coverage XML and the raw pytest log are in
`/home/atharva/Documents/Fusion/spec-results/final/{fr,uc,br,wf}/`; the triage record is
[`spec-tests/triage.md`](spec-tests/triage.md). Final counts: FR 74, UC 48, BR 47, WF 18 —
all zero failures and zero skips.

## Adversarial pass (Step 5.11)

31 adversarial tests were added after review, across
`modules/phc/tests/spec/{fr,br,wf}/test_adversarial.py`:

- **FR (18):** anonymous 401; module-grant and permission gates independently 403; both gates allow 200; invalid `?limit=abc` 400 with an actionable message; out-of-range limit 400; over-deduction 422 with no `StockAdjustment`; unknown requisition item 422; future expense date 400; 11th rapid claim submission 429 with `throttled`; oversized int4 inputs return 400 instead of a `DataError` 500; negative `reorder_threshold` 400 with no item created; two cumulative near-limit adds return 400 with `stock_overflow` and leave the quantity and adjustment rows unchanged; over-length `dosage`, `unit` and `reason` strings are 400s with no write; duplicate doctor/day schedule create and maintain are 409 `schedule_exists` with no extra row; a staff requisition originator with no prior patient profile is projected from the IAM session instead of failing the FK; query-budget constant as rows grow from 0 to 30.
- **BR (7):** submission/status/decision/low-stock notifications assert recipient, topic, subject, body, payload and audit side effect; cross-patient record access 404; patient cannot reach staff or audit routes; role switch changes capability.
- **WF (6):** stale `expected_updated_at` 409 with `conflict`; double-click 409 with one audit row; wrong-stage transition 404 with the "earlier stage" message; rejected claim immutable; requisition double decision 409; PDF has real content.

No spec test failed, so no production behaviour was changed to satisfy a test. The one genuine
defect the adversarial pass exposed — `expected_updated_at` bound to the wrong argument in four
views — was fixed in `modules/phc/api/views.py`.

## Fresh environment proof

Executed against a brand-new PostgreSQL database `phc_fresh_proof` on real Postgres (not
pytest-django): `migrate → seed_modules → ops/db/roles.sql → first user action`. Output is in
`/tmp/opencode/fresh-proof.log`:

```
first read  GET  /api/v1/phc/schedule -> 200 keys= ['attendance', 'schedules']
first write POST /api/v1/phc/claims    -> 201 state= submitted
notification outbox rows               -> 1 topic= claim.status_changed
inventory item count (empty schema)    -> 0
```

The append-only audit grant was then verified under `SET ROLE platform_app`: INSERT succeeded
(`insert ok: 2`), while `UPDATE` and `DELETE` both returned
`ERROR: permission denied for table phc_audit_log`.

## Independent review record

Independent nine-dimension reviews were run iteratively on 2026-11-22. The first returned
eight 10/10 dimensions plus Frontend 8/10 and Hygiene 9/10 (PDF download and `roles.sql`
tracking); the second returned Arch 9/10 and Code 9/10 (transactional audit write and
oversized-integer 500s); the third returned Code 8/10, Tests 9/10 and Ops 8/10 (negative
threshold, cumulative overflow, stale schema and stale report figures); the fourth returned
Code 8/10 (over-length `varchar` inputs and duplicate doctor/day schedules). Every finding
from every round was fixed and re-verified. A final independent review then returned
**10/10 in all nine dimensions with zero findings**; its output is retained at
`/tmp/opencode/a9-final-review.txt`. The consolidated gate log is
`/tmp/opencode/a9-final-gates.log` and the fresh-environment log is
`/tmp/opencode/fresh-proof.log`.

## Final verdict

All specification ids are implemented at a named enforcement point. Every independent-review
finding is closed, all nine review dimensions are addressed, every gate is green, there are no
failures or skips in 187 spec tests, and a fresh-environment first-action proof is recorded.
The module is complete and ready for submission.
