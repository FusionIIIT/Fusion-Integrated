# HR-EIS quality report — Assignment 9 (Student 1)

**As of:** 2026-11-22; latest checkpoint in section 25, earlier sections are historical.
**Branch:** `module/hreis`
**Status:** DEVELOPMENT / NOT APPROVED / NOT READY FOR A 10/10 CLAIM

This is an evidence record, not a completion certificate. The blueprint at
[`hreis-blueprint.md`](hreis-blueprint.md) is not approved by Student 2.
[`procedure-deviation.md`](procedure-deviation.md) records the explicit
instruction to continue development and the absence of the required independent
approval. There has been no Student 2 specification-test baseline or review.

## 1. Automated repository gates

- `make check` (WSL Ubuntu 24.04, database environment sourced from local
  development credentials): **PASS**, exit code 0 on 2026-11-21, after the latest
  request-list optimization and query-budget tests. Output confirms Django system check 0 issues,
  `makemigrations --check --dry-run` no changes, Ruff pass, all five import
  contracts kept, no cross-module foreign keys, consistent plural contract
  getters, navigation/route agreement, permission manifest agreement,
  OpenAPI agreement, and the complete pytest regression suite passing.
- `npm run typecheck; npm test; npm run build` (Windows): **PASS**, exit code
  0. Six frontend test files / **38 tests passed**; Vite production build
  succeeded. The bundle size warning is nonfatal.
- `make check-client` (WSL): first attempt failed because Windows-installed
  `node_modules` lacked Linux Rollup binaries. The lockfile-defined Linux
  packages were reinstalled using `npm ci --no-audit --no-fund`; the
  TypeScript checks and all 38 Vitest tests then passed. The production
  Vite build also **passed** (exit code 0; 31.87 seconds, nonfatal large-chunk
  advisory). The exact `make check-client` wrapper **passed** on
  2026-11-21 with exit code 0 (38/38 frontend tests, successful Vite build).
- `git diff --check`: no whitespace errors in the tracked-file diff.
- Generated `openapi/fusion-integrated.v1.yaml`,
  `registry/permissions.json` and
  `docs/02-iam/permission-catalog.generated.md` were regenerated after the
  API/permission changes.

## 2. Coverage runs

- `pytest modules/hreis/tests --cov=modules.hreis --cov-report=term-missing -q`:
  **PASS**, exit code 0; **90% statement coverage**, 1,173 statements,
  115 missed. This measures the module's Student 1 tests and is not a
  substitute for specification-derived independent tests.
- `pytest modules/hreis --cov=modules/hreis --cov-branch --cov-report=term-missing --cov-fail-under=90 -q`:
  **PASS**, exit code 0 on 2026-11-21, **90.47% combined statement/branch coverage**;
  1,179 statements, 88 missed, 300 branches and 49 partial branches.
  All 214 builder-side tests passed. The threshold is 90%.
- `pytest modules/hreis --cov=modules/hreis/domain --cov-branch --cov-report=term-missing --cov-fail-under=95 -q`:
  **PASS**, exit code 0 on 2026-11-21, **95.73% combined statement/branch coverage**;
  203 statements, 6 missed, 78 branches and 6 partial branches. The threshold is 95%.
- These are builder-authored tests, not Student 2's independent spec tests.
  A separate all-Fusion coverage baseline has not been recorded.

## 3. Test inventory and journeys

The Student 1 tests cover state-machine guards, leave/claim validation,
effective-dated policy publication, role/owner queryset scoping, records,
append-only database constraints, transaction rollback, leave ledger debit,
LTC/CPDA verification, authority forwarding, appraisals and final archival.

The HTTP write-path tests added on 2026-11-21 exercise real DRF permissions,
serializers and routes for leave submission, policies, and LTC verification.
The appraisal service test also verifies that HR-admin edits cannot remove or
rewrite archived appraisals. A shared-session regression test proves that
switching to an authorized IAM designation returns the correct new active role.

The six builder-side Playwright tests in `client/e2e/hreis/flows.spec.ts`
exercise authenticated employee record access, role and data-scope separation,
invalid leave rejection, student access denial, HR administrator policy/audit
screens, and an HR-admin create/update → employee read → audit event path.
Their scenario names are documented in Section 8. These tests are **not**
Student 2's frozen FR, UC, BR and WF spec-test suites.

The collected module test counts are:

| Test file | Collected cases |
| --- | ---: |
| test_appraisals_service.py | 3 |
| test_domain.py | 102 |
| test_http.py | 6 |
| test_http_actions.py | 3 |
| test_immutability.py | 4 |
| test_journeys.py | 8 |
| test_models.py | 9 |
| test_policy.py | 11 |
| test_query_budgets.py | 2 |
| test_records_service.py | 13 |
| test_requests_service.py | 6 |
| test_routing_claims.py | 34 |
| test_selectors.py | 9 |
| test_transitions_service.py | 4 |
| **Total** | **214** |

The 214 tests were executed in the database-backed module coverage run on 2026-11-21.
New HTTP journeys cover submitted/approved/rejected leave, LTC and CPDA
verification, appraisal assignment and closure, service-record security,
and negative paths. Query-budget tests measure actual SQL requests using 2 and
20 list items. The exact UI journey-to-UC mapping remains incomplete; no claim
of full coverage of the blueprint's 193 live traceability entries has been
made.

## 4. Five deliberate broken-on-purpose rules

The prescribed Step 5.15 mutation/broken-rule exercise **PASS** (2026-11-21).
Each row describes one temporary single-rule mutation, the targeted test that
failed, and the same test passing once the exact original bytes were restored.
Backups, full raw pytest logs and `SUMMARY.txt` are outside Git under
`D:\HR(EIS)\lab 9\mutation-results`.

| Broken rule | Targeted test (under `modules/hreis/tests/`) | Mutated fails | Restored passes |
|---|---|---|---|
| Employee scoping filter removed | `test_selectors.py::test_employee_only_sees_own_record_even_with_view_permission` | Yes | Yes |
| IAM permission gate disabled | `test_policy.py::test_bad_roles_cannot_publish_policy` | Yes | Yes |
| Leave balance threshold disabled | `test_requests_service.py::test_leave_requires_explicit_config_and_trusted_ledger` | Yes | Yes |
| Nonfinal authority could approve | `test_transitions_service.py::test_leave_requires_current_role_and_final_authority` | Yes | Yes |
| Duplicate request key guard disabled | `test_requests_service.py::test_request_replay_and_role_denial_do_not_mutate` | Yes | Yes |

All five original source files were verified byte-for-byte against their backups.

## 5. Adversarial pass

Security/functional problems tested and addressed include:
- Non-active or ungranted HR role attempting to create/update master records:
  denied.
- Employee attempting to read another employee's record: 404.
- A duplicate request or stale service-record revision: rejected without a
  second transaction.
- Missing institutional policy, missing leave ledger credit and absent
  mandatory claim evidence: refused rather than fabricated.
- An approver attempting to skip a route step: refused.
- A general HR administrator attempting to alter a finalized appraisal entry
  in service history: refused (2026-11-21 regression fix).

A complete recorded adversarial questionnaire under Step 5.11 has not been
conducted and remains an open gate.

## 6. Security self-audit

- Identity, roles and login are owned by IAM. HR-EIS stores IAM user IDs, not
  credentials or replicated identity/permission tables.
- Read requests are scoped on the server; frontend permission checks are only
  an additional UX gate.
- Write services check module, permission and active role.
- Audit, transition, revision and leave-ledger records are append-only with
  PostgreSQL protections; transactional writes include their audit events.
- Idempotency keys and row locking are used for request decisions and
  leave-balance deductions.
- No payment, payroll write or financial settlement is executed by HR-EIS.
- Unverified file references are not represented as uploaded or validated
  claim documents.

A further independent security review is still mandatory. No secure transport
or external delivery integration is certified by these local checks.

## 7. Fresh-install proof

A disposable-database migration rehearsal **passed** on 2026-11-21
(Section 15): all migrations applied, both HR-EIS migrations rolled back and
reapplied, `seed_modules` and Django checks passed, and the temporary database
was verified cleaned up. However this does **not** meet the complete Step 7.8
fresh-install requirement: a clone from only committed Student 1 changes,
institutional policy seeding, verified IAM grants, a module readiness command,
and the first action in a browser against the new database remain unverified.
At this 2026-11-21 checkpoint there were two unmerged HR-EIS migrations; subsequent finance-history work added two further migrations, for four in the final working tree.

## 8. Live browser walkthrough

**PASS:** `E2E_IAM_DIR=/mnt/d/fusion/Fusion_System_Administrator-A9 make e2e`,
run on 2026-11-21 against the A9-only IAM, PostgreSQL and Redis services:
**15 passed (44.7 seconds), exit code 0** in the latest run after the
query and security fixes, including nine existing platform
regressions and six builder-side HR-EIS tests:

| Real browser scenario | Outcome |
|---|---|
| Synthetic staff sees HR-EIS and read-only own service record | Pass |
| Staff denied HR administration; record list constrained to own row | Pass |
| Invalid leave duration rejected by HTTP without submitted request | Pass |
| Student cannot access HR-EIS pages or request API | Pass |
| HR administrator accesses service records, policy and audit UI | Pass |
| HR administrator creates/edits synthetic record; employee sees update and audit event | Pass |

Three setup issues had first prevented actual browser execution: the older IAM
checkout did not have the required role-assignment management command; the
clean A9 IAM instance lacked a local credential environment and usable Redis
client; and Linux Chromium was not installed. The correct clean IAM checkout
and a Git-ignored local configuration fixed those environment issues.
IAM permission/navigation grants were seeded from the generated Fusion manifest
(**123 added, zero revoked**) in the A9 isolated database.

A valid, existing **local-only IAM service credential** was supplied to the
A9 backend through its process environment. The backend needs that credential
to verify employee identities through the protected directory endpoint;
without it service-record creation correctly fails closed. No credential
value is stored in the repository or recorded here.

The first real HR-EIS browser pass also exposed a cross-cutting defect in
`fusion_auth/views.py`: the role-switch PATCH response used its stale,
pre-switch principal, so an accepted `hradmin` selection reverted in the
UI. An explicit failing Django regression was added and the view now refreshes
its IAM principal before returning. The regression and browser test both pass.

All browser tests use the **public synthetic development fixture**.
This evidence does not demonstrate external integrations, every spec use case,
or Student 2 independent testing.

## 9. Scheduled tasks

No HR-EIS scheduled reminder or official email dispatch task has been
implemented or run by hand. The transactional notification/outbox records
exist, but queued events must not be mistaken for delivered mail.

## 10. Unresolved specification/operation gaps (NOT APPROVED)

- **HR-CFR-007:** The specification does not provide numeric leave
  entitlements/accrual allocations. Requests check real ledger balances, but
  a verified institutional opening-balance import/update procedure is not
  complete. No default credit has been invented.
- **HR-CFR-008:** Annual appraisal submission depends on an approved
  effective-dated institutional window and route.
- **HR-CFR-005, HR-CFR-009, HR-CFR-010, HR-CFR-013:** An exact IAM Accountant
  designation, external finance/payroll handoff, financial policy and
  claim-payment status integration are unavailable; the module cannot
  represent financial settlement as completed.
- **HR-CFR-009 / HR-CFR-010:** Secure upload, document integrity and external
  eligibility evidence verification remain to be integrated. Submitted
  references alone are not verified attachments.
- **HR-CFR-011:** Official email delivery, reminder timing, retries and
  effective reminder scheduling are not implemented.
- **HR-CFR-003:** Department, employee category and request-family-specific
  authority routes must come from approved institutional policy; arbitrary
  defaults are forbidden.

These gaps are *recorded*, not accepted or waived. No Student 2 approval has
been received for them.

## 11. Required approval records

- Blueprint: **MISSING** — Student 2 written approval not received.
- Known gaps: **MISSING** — not waived.
- Shared-file registration and shared-authentication changes: **MISSING**
  — no Student 2 approval. The role-switch regression fix touches
  `fusion_auth/views.py`, `fusion_auth/tests/test_auth.py` and shared test
  fixture `conftest.py` as well as the generated registration files.
- Dependencies: existing lockfile/package requirements only; no new
  application dependency introduced in the HR-EIS module. The Redis Python
  dependency was installed into the local development IAM environment only,
  with no IAM repository source or requirements changes.
- Student 1's instruction to continue independently is documented in
  `procedure-deviation.md` and does not replace the independent approvals.

## 12. Independent review rounds and final verdict

No compliant fresh committed-clone review scorecard exists, and Student 2's
four frozen FR/UC/BR/WF suites have not been submitted. **There is no 10/10
verdict.** This branch has not been committed, pushed or submitted as a PR.

## Shared files changed

`.importlinter`, `config/settings/base.py`, `config/urls.py`,
`client/src/app/registry.ts`, `fusion_auth/views.py`,
`fusion_auth/tests/test_auth.py`, `conftest.py`,
`client/e2e/accounts.ts`, the generated OpenAPI schema, the generated
IAM permission manifest and the generated permission catalogue.
The builder-side browser tests are in `client/e2e/hreis/flows.spec.ts`.
All additions remain local and uncommitted.

## 14. Continuation audit — 2026-11-21

- Inspected the existing A9 checkout rather than reusing or overwriting the old A8 repository.
  `git fetch upstream main` succeeded; `HEAD...upstream/main` returned `0 0`.
- Found an adversarial authorization gap: an employee holding an authority designation
  could potentially act on the employee's own request; the authority queue could display it.
  Added a same-owner refusal to leave/LTC/CPDA decisions, claim HR verification
  and appraisal reviews, excluded own requests from authority queues, and
  forbade choosing the appraisal owner as an assigned reviewer.
- Added one regression each to `test_transitions_service.py`,
  `test_selectors.py` and `test_appraisals_service.py`. `pytest --collect-only`
  now discovers **204** builder-side cases. Do not count the three new cases as
  passing until a database-backed run proves them.
- `.venv/bin/ruff check modules/hreis`: **PASS** after these edits.
- The separate database-independent domain runs
  `pytest test_domain.py test_routing_claims.py --cov=modules/hreis/domain
  --cov-branch --cov-fail-under=95` passed **136 tests**, measuring **95.73%**
  combined line/branch coverage for domain code. This is a partial floor check,
  not the exact full-suite Step 5.14 gate.
- An attempt to run the exact full-module branch-coverage gate without a
  configured local DB password finished with **136 passed, 65 database setup errors**
  (`fe_sendauth: no password supplied`). Its reported coverage was invalid
  because DB-dependent tests never ran. No production behavior failure is
  inferred from these setup errors. A secure local `DB_PASSWORD` must be
  configured before running all gates again.
- A mechanical citation audit of the 193 live blueprint IDs against the builder
  test source found **2 explicitly cited IDs and 191 without citations**.
  These IDs require accurate tests/traceability, not superficial citation injection.
  This is still an open Step 5.13 requirement.
- No Student 2 approval, independent review, spec-test baseline, commit, push,
  pull request or production deployment is claimed.


## 15. Reconnected-session verification, repairs and outstanding gates (2026-11-21)

This section supersedes earlier intermediate test counts in the chronological
notes of Section 14. Evidence is held **outside** the Git repository under
`D:\HR(EIS)\lab 9\evidence\`, alongside the mutation logs, and must not
be mistaken for a Student 2 review.

### Latest passing quality gates

| Gate | Latest outcome | Key evidence |
|---|---|---|
| `make check` | **PASS**, exit 0 | Zero Django issues, no migration changes, Ruff clean, all five import contracts kept, schema/permission manifests match, whole pytest regression suite passes |
| `make check-client` | **PASS**, exit 0 | 38/38 Vitest cases, TypeScript typecheck, production Vite build |
| Builder backend `--cov=modules/hreis --cov-branch --cov-fail-under=90` | **PASS**, exit 0 | 214 builder cases passed, 90.47% combined statement/branch coverage |
| Builder domain `--cov=modules/hreis/domain --cov-branch --cov-fail-under=95` | **PASS**, exit 0 | 214 builder cases passed, 95.73% combined statement/branch coverage |
| `E2E_IAM_DIR=/mnt/d/fusion/Fusion_System_Administrator-A9 make e2e` | **PASS**, exit 0 | 15 Playwright tests, 44.7 s, including 6 HR-EIS browser scenarios |
| Deliberately broken rules | **PASS**, 5/5 | Each mutation caused its targeted test to fail; original sources restored byte-for-byte and passing tests rerun |

### Actual bugs discovered and repaired

- **Unassigned appraisal visibility/action:** a user holding the same authority
  designation as an HR-assigned reviewer could see and act on a first-stage
  appraisal despite not being the assigned reviewer. Queue scoping and the
  appraisal decision service now require the reviewer user ID at the first
  stage; an HTTP regression drove the fix.
- **Approval conflicts:** employees are prevented from acting on their own
  leave, LTC/CPDA or appraisal approvals; HR claim verifiers cannot verify their
  own requests; an appraisal owner cannot be nominated as their own reviewer.
  The authority queue excludes self-owned requests. Builder regressions pass.
- **Malformed-object request crash:** passing a JSON array to an object-based
  HR-EIS input serializer raised an uncaught `ValueError` and HTTP 500. The
  serializer now returns a proper HTTP 400 validation response; a regression
  verifies that no HR request or audit record was created.
- **N+1 request-list SQL:** two claim summaries used 3 SQL queries and twenty
  used 21 before the fix. The scoped request queryset now eagerly loads its
  one-to-one `claim` relation. Both 2-versus-20 query-budget tests pass after
  the fix, including the service-record list baseline. No test expectation
  was weakened.

### Disposable database installation proof (partial, not final)

A unique local throwaway database `fusion_integrated_a9_proof_20261121` was
created and tested in the isolated A9 development Postgres instance. Actual
command results:

1. `make migrate`: all platform migrations applied; `hreis.0001_initial`
   and `hreis.0002_immutable_records` both **OK**.
2. `manage.py migrate hreis zero`: both HR-EIS migrations unapplied **OK**.
3. `make migrate`: both HR-EIS migrations reapplied **OK**.
4. `manage.py seed_modules`: `registered placement_cell (active)`,
   `registered hreis (active)`, 2 modules registered.
5. `manage.py check`: `System check identified no issues (0 silenced).`
6. The disposable database was dropped and confirmed absent after exit.

**Readiness finding:** the clean database had no institutional HR-EIS policies,
yet `seed_modules` registered HR-EIS as active. `modules/hreis/registry.py`
does not currently provide the required `readiness()` prerequisite checks,
and there is no HR-EIS readiness/approved-policy-seeding management command.
A complete clean install is therefore **NOT** proven. Institutional
leave allocations, appraisal windows, routes, Accountant mapping and
integration behavior cannot safely be invented. These must be approved and
configured, and the readiness/first-user-action evidence completed, before
calling the module deployment-ready.

### Traceability and handoff blockers

- The live blueprint lists **193** source IDs. The current builder tests
  explicitly cite **19**; **174** still lack explicit builder-test citations.
  The exact audit is in `D:\HR(EIS)\lab 9\traceability-audit.txt`.
  A citation is not a substitute for an asserted behavior; the remaining
  test obligations must be completed based on the source documents.
- The remaining workflow/notification scheduling, finance/payment-status
  interface, secure claim-file validation, institutional policy inputs,
  full frontend page-state tests, explicit concurrency/query budgets for
  other endpoints, and formal adversarial questionnaire are not complete.
- Student 2 has not given the written blueprint, gap or shared-file approvals.
  There has been no independent committed-clone reviewer round, no 10/10 in
  nine dimensions, and no Student 2 frozen FR/UC/BR/WF test baseline.
- No local Git commit, remote push, PR, or deployment occurred in these runs.


## 16. Specification-driven completion pass — 2026-11-21 (provisional Student 1)

This section **supersedes older test counts and open-feature descriptions above**
where new code has since been implemented. Source of truth: the six files at
`D:\HR(EIS)\specifications`, the Fusion integration contract and the existing
HR-A6 reference; no unspecified institutional numeric policies have been
adopted. Student 2 agreement was reported **verbally**, without written
documentation (see `procedure-deviation.md`). These facts do not certify an
independent 10/10 review.

### Implemented in this pass

1. **Configuration readiness:** `modules/hreis/registry.py::readiness` now
   gives specific prerequisites for effective leave/appraisal/LTC/CPDA
   policies. `hreis_readiness` returns a failing exit code and actionable
   reasons when unconfigured. `seed_modules` now correctly stores and prints
   `planned`, not `active`, on an empty installation. Policy versions remain
   append-only; no arbitrary quota, routing matrix or appraisal dates were
   installed. Four database-backed readiness tests passed.
2. **Accountant finance-status evidence:** `hreis.claim.process` permission,
   IAM manifest grant for `Accountant`, protected API
   `POST /api/v1/hreis/requests/<id>/financial-processing/`, service
   `services/finance.py`, and corresponding UI controls. Only an independently
   HR-verified approved LTC/CPDA claim can record an external finance/payroll
   status with attestation and external reference. Self-processing and
   unauthorized use are denied. This **does not execute payroll**, move money,
   verify external settlement independently or replace a live finance adapter.
   Five database-backed tests and three frontend action tests passed.
3. **Configured reminders and mail handoff:** `services/notifications.py`
   generates one dashboard, audit and outbox event per authorized pending
   action or configured policy/deadline notice; no timings, roles, recipients
   or notices are invented. A scheduled Celery task and manual
   `hreis_notifications` command support generation, email handoff,
   status and retry. Failed IAM lookup or SMTP handoff leaves mail pending.
   Nineteen database-backed notification tests passed, including retry,
   idempotency and wrong-reviewer cases. Real institutional SMTP/provider
   delivery and end-recipient designation validation remain unproven.
4. **Official leave balance visibility and evidenced credits:** the service
   record API now projects ledger-derived, employee-scoped leave balances with
   batched aggregation; the read-only employee page shows them. A protected
   HR-admin screen and `hreis.balance.manage` endpoint allow positive,
   audited credits **only with an evidence reference, verified employee identity
   and effective eligibility policy**; no default credit is granted.
   Duplicate and self-credit operations are denied. Builder unit/API
   regressions pass. Corrective negative-ledger workflows remain governed by
   the immutable ledger/evidence policy.
5. **Frontend states and mixed deployment robustness:** 10 builder-authored
   tests cover loading, empty, error, success and forbidden-related states
   of HR requests, own record, notices and audits. Browser testing found
   `Object.keys(undefined)` when the running API omitted the new balances
   field; the page now fails gracefully to the no-verified-credit message
   rather than crashing. A new test covers partial API responses.

### Test results and fresh-install rehearsal

- Repository `make check` **PASS** after the new services and self-credit
  protection (Django check, migrations, Ruff, imports, permission manifest,
  OpenAPI consistency, full pytest regression suite).
- `make check-client` **PASS** on the new Accountant/credit UI; 51 Vitest
  tests and successful production Vite build at the last complete checkpoint.
  A further run including the latest missing-balance regression is being
  verified before this report can be treated as final.
- Builder whole-module combined statement/branch coverage:
  **91.14%** (required 90%), before the last self-credit-only regression
  adjustment. The domain combined coverage remains subject to the latest
  exact gate run; never infer an unperformed result.
- Latest browser E2E after the backward-compatible balance-page fix:
  **15/15 PASS**, including six HR-EIS cases, in Chromium. This is the
  current development database, not the clean test database.
- New isolated clean DB script
  `D:\HR(EIS)\lab 9\fresh_a9_readiness_proof.sh` **PASS**:
  created an empty throwaway DB, applied migrations, verified HR-EIS
  status `planned` and four named readiness failures, injected clearly
  marked synthetic test policies in that database **only**, reran
  `seed_modules`/readiness to activation, created the first actual
  workflow-level leave request and audited events, passed Django checks,
  and dropped the throwaway DB. This is **NOT** a genuine institution
  policy rollout, IAM grant seed or actual first *browser* action against
  the clean DB. All synthetic quantities/routes were throwaway test data.
- Existing five deliberate source-mutation checks remain 5/5 detected,
  restored and passing, as evidenced in Section 15 and lab9 artifacts.
- `docs/09-hreis/hreis-traceability-status.md` lists **all 193** live
  source IDs with original requirement language and currently cited
  builder-side tests; **36 direct citations, 157 without direct citation at this earlier checkpoint**. This historical count is superseded by the latest audit in the final Student 1 section below.
  This is a truthful progress audit, not proof of 193 complete independent
  specification tests.

### Incomplete formal release gates

- Written Student 2 blueprint, gap and shared-file approvals have not
  been supplied. The user reports verbal agreement; this cannot silently
  be presented as written proof.
- No configured institution-backed leave allocations, appraisal dates,
  external Accountant identity mapping, institution-approved reminder
  recipient schedule, real SMTP provider delivery or live finance status
  integration has been demonstrated. The supplied problem statement
  intentionally omits the actual institutional numbers and matrices.
- The core upload service in this repository is explicitly **read-only**;
  HR claim references and human HR attestation must not be mistaken for
  uploaded/hashed/validated document bytes. Implementing a secure upload
  adapter or obtaining approved external Drive/evidence interfaces remains
  open.
- Per-ID traceability needs manual reconciliation of every UC/FR/BR/WF
  success/failure/guard; direct citation counts do not equate to complete
  behavioral coverage.
- The formal **fresh committed-clone** independent nine-dimension reviewer
  scorecard is still absent. No 10/10 is claimed. Student 2's separate,
  independently frozen FR/UC/BR/WF suites have not started.
- The implementation remains uncommitted on `module/hreis`, with no Git
  push, PR or deployment until explicit final review and handoff.


## 17. Review-driven Student 1 repair pass — 2026-11-21

This section documents the later **uncommitted** code, superseding earlier
intermediate code-review and test counts only where actual evidence exists.

### Independent preflight (not the official review)

An independent read-only preflight examined the uncommitted working tree and
returned **NOT APPROVED** with several concrete functional and security
findings. The original complete output is saved at
`D:\HR(EIS)\lab 9\evidence\A9-20261121-preflight-independent-review-uncommitted.txt`.
This was **not** a clean committed-clone round and was **not** a valid 10/10
scorecard. The preflight's stale statement that 191 of 193 IDs lacked citations
does not match the later regenerated source-based audit: that later audit had
43 direct builder-test references and 150 still unlinked.

### Follow-up repairs and tests

1. **Appraisal visibility:** authorized owner/HR/assigned approvers now receive
   the actual `AppraisalDetail.submitted_form` through a scoped, read-only
   `appraisal_summary` response. Reviewer drawer presents it explicitly.
   Querysets use batched related-object loading to avoid N+1 queries.
   HTTP and frontend regressions verify scope and real submitted data.
2. **HR self-edit segregation:** even an HR administrator with elevated IAM
   grants cannot create or update their own official service record.
   Failed attempts leave audit/revision history unchanged.
3. **Notification delivery:** HR request submission and transition events
   now enqueue the same `hreis.notification` type processed by the configured
   email worker; unrelated policy/workflow event types stay untouched.
   The worker batches outbox key lookup, refuses disabled recipients and
   retains retry/error evidence. Tests simulate successful backend handoff,
   not actual institutional SMTP delivery.
4. **Policy succession and concurrency:** a higher-version successor may
   supersede an immutable open-ended previous policy, whether the new window
   is finite or open-ended. When a finite successor expires, the historical
   predecessor does **not** revive. Per-family PostgreSQL transaction advisory
   locks prevent overlapping concurrent publications (two-thread regression).
   Readiness uses the matching latest-version semantics. No institutional
   numeric values were invented.
5. **Accountant lifecycle:** after an independently attested initial
   `processing`/`payment_pending` status, authorized accountants can
   record later externally referenced status evidence without restarting the
   HR approval workflow. Every change receives an immutable AuditEvent,
   owner notification and email outbox event. Already finalized reported
   statuses cannot be silently changed. **No actual payment execution or
   external finance confirmation is claimed.**
6. **Approval queue and UX:** the route now uses a dedicated
   `hreis.approval.view` grant shared across authorized HOD/Registrar/Director
   roles, instead of binding the page to `hreis.leave.approve`.
   A separate API endpoint requires that grant, checks the active authority,
   and returns only scope-filtered requests; employees cannot open it.
   The UI reads frozen route length and offers intermediate forwarding versus
   final approval appropriately. Lists prefetch routes to retain bounded SQL.
7. **Record-edit safety and input validation:** frontend sends only changed
   official fields, excluding unchanged appraisals from a routine edit;
   nested JSON comparisons disregard key ordering. CPDA/LTC form fields
   receive client-side required-value validation.
8. **Contract compliance:** permissions and OpenAPI were regenerated, and
   Ruff/import-linter/schema-generation checks were rerun. New builder tests
   live only in the Student 1 test directory; Student 2's future spec-test
   folders remain untouched.

### Evidence and remaining blockers

- Targeted database-backed tests passed for the new appraisal view, self-edit
  guards, outbound mail handoff, finance status updates, bounded policy
  succession/concurrency and authority queue. Targeted React tests also pass.
- Exact current full `make check`, `make check-client`, Playwright and
  both coverage gates must be recorded **after these latest edits**.
  Older green values are historical evidence and are not automatically current.
- The 193-live-ID FR/UC/BR/WF traceability reconciliation is incomplete.
  Direct comment/name citations by themselves are not quality proof.
- Written Student 2 approval for blueprint, non-module files and dependencies
  has not been supplied; only verbal agreement was reported. No independent
  final clean-clone 10/10 nine-dimension round, signed scorecard or Student 2
  frozen independent test baseline exists.
- The institution-specific exact leave allocations, authority matrices,
  appraisal windows, live IAM Accountant provisioning, real evidence-file
  storage, email provider, finance integration, and first browser action on
  a clean committed clone remain dependent on supplied integration/policy
  evidence. Synthetic disposable-database demonstrations were labeled as such.
- No Git commit, remote push, PR or production deployment has been made.


## 18. HR compliance-status visibility and broader browser guard verification (2026-11-21)

- The independent read-only preflight's finding C.1 (HRAdmin cannot see
  historical leave/claim request statuses) was reconciled without opening up
  private request bodies: a separate, `hreis.audit.view`-guarded
  `GET /api/v1/hreis/compliance/requests/` returns **status-only**
  fields (`id`, `user_id`, `family`, `state`, timestamps). Only a
  currently acting `hradmin` receives the historical records. The employee
  and permission-only wrong-role paths remain empty/forbidden. The response
  deliberately omits medical type, reasons, claim document references and
  submitted appraisal forms. The Audit page exposes a dedicated
  “Request compliance status” section with loading/error/empty/success states.
- `test_http.py` now includes an HTTP regression checking historical leave
  and processed CPDA visibility plus field-level redaction and wrong-role
  refusal. `PageStates.test.tsx` includes the corresponding compliance
  display regression. **Both targeted suites passed**.
- Generated OpenAPI initially warned about a `family` enum collision;
  compliance serializer now uses a read-only string, and OpenAPI generated
  cleanly with `--fail-on-warn`. Architecture/Ruff checks passed.
- Browser E2E expanded from 15 to **17 cases**. After restarting the
  development backend (original `--noreload` process lacked the newest
  approval-queue endpoint), all 17 Playwright Chromium tests passed. The
  restarted backend serves the same A9 checkout and IAM on port 8001 was
  untouched. Two new browser cases verify employee denial of approval and
  finance deep links and correct category-specific employee forms.
- Latest traceability audit:
  **193 live source IDs, 46 directly cited in builder test functions,
  147 without direct references.** This is not yet complete per-ID
  behavioral verification. Source:
  `docs/09-hreis/hreis-traceability-status.md`.
- Draft Student 2 review/approval record:
  `docs/09-hreis/student2-approval-request.md`. It lists every changed
  non-module shared file and unresolved institute/external-system dependency,
  expressly marked **PENDING**, never passed off as Student 2's written
  signature or as a final scorecard.
- The uncommitted branch remains `module/hreis`, with no commit, push, PR
  or deployment. Formal independent fresh-committed-clone nine-dimensional
  10/10 review is still absent. No Student 2 frozen FR/UC/BR/WF tests have
  been used or modified.


## 19. Student 1 specification-completion pass — 2026-11-22

This section supersedes older implementation/test counts above after the final
verification evidence below is generated. Source of truth remains the five
HR-EIS documents and live RTM in `D:\HR(EIS)\specifications`; no
institutional leave quota, appraisal date, monetary transfer or attachment
storage service was invented.

### Concrete repairs

- **Finance IAM/API consistency:** the prior `hreis.claim.process` guard
  conflicted with the blueprint's declared finance verbs and generated
  permission manifest. Processing now requires **both** `hreis.finance.review`
  and `hreis.finance.update` at first attestation and requires
  `hreis.finance.update` for subsequent externally reported status
  changes. The route, service, React guards and synthetic actor tests use
  matching codes. An existing IAM designation **`Accounts Admin`** is used
  as a **provisional mapping** of the HR specification's Accountant actor:
  this is an implementation assumption to make the manifest reachable and
  demonstrable, **not proof of institutional authorization**. It grants no
  new IAM designation or institution policy and must be confirmed before
  real HR finance deployment. No payments, bank calls or payroll writes run.
- **Immutable external financial history:** the previous mutable latest-value
  JSON projection is now backed by a separate relational
  `FinancialStatusProjection` row **per status attestation**, with event key,
  external system/reference, review evidence, reporting actor and timestamp.
  Migrations `0003` and `0004` create the schema and PostgreSQL
  UPDATE/DELETE rejection trigger. A rollback-safe audit event accompanies
  each row; direct ORM bulk changes/deletions fail.
- **Specification test coverage:** tests now exercise both advance and
  reimbursement for **both** LTC and CPDA; a missing appraisal route branch
  with direct one-stage finalization; rejected and single-forwarded LTC/CPDA
  journeys with audit/terminal checks; and explicit staff-to-Registrar
  policy routing. A new boundary test checks that no HR-EIS-owned write
  surface adds payroll/salary mutations or local IAM role assignments.
  Existing tests now identify the exact HR-CFR/AFR/UC/BR/WF obligations they
  truly assert instead of using slash notation that hides separate IDs.
  The regenerated Student 1 direct-evidence audit currently reports
  **193 live source IDs, 187 linked to builder tests, 6 not directly linked**.
  This is not a Student 2 independent test score and not proof that every
  possible exception has been verified.
- **Minor UI fix:** the invalid replacement character in the reviewer
  drawer header has been replaced with a proper separator.

### Six outstanding requirements with specific, non-fabricated limitations

1. **HR-CFR-013:** composite payroll/finance/directory exchange and
   consistency needs real external providers and an approved integration
   contract. Current Finance status references and directory projections
   do not prove two-way live synchronization.
2. **HR-AFR-090:** no live payroll endpoint/credentials or payroll data
   exchange has been provided; HR-EIS records an *attested* payroll-origin
   status only.
3. **HR-AFR-091:** no live finance accounting API/credentials or
   provider-confirmed exchange has been supplied; HR-EIS records external
   finance references with immutable evidence.
4. **HR-AFR-092:** the Fusion directory contracts and IAM session
   projection are used, but authority/role assignment and live
   cross-system identity consistency must be verified in deployed IAM.
5. **HR-AFR-093:** automatic real-time exchange with external payroll
   or finance remains configuration/provider dependent; local Celery
   reminders and local outbox delivery do not constitute it.
6. **HR-AFR-059:** the RTM requests preservation of *returned* LTC
   histories, but the source workflow and BR rules provide **no
   defined LTC return action**. Rejected LTC is tested and audited;
   inventing a return transition would contradict the supplied
   canonical workflows. A source-spec ruling is necessary.

### Formal paperwork is deferred per assignment owner

The owner reports Student 2's verbal acceptance of the plan and will seek
written approval, shared-file change approval, any provider/rule rulings
and the independent Student 2 testing **on handoff**. No such written
approval is fabricated here. No clean committed-clone nine-dimensional
10/10 verdict has been obtained, and no automated Git commit, push, PR, or
production rollout occurred. The independent preflight is not a substitute.

**Final checks:** Record the exact post-change `make check`,
`make check-client`, browser E2E, two coverage gates, fresh-install proof,
and the read-only independent preflight in this report only when each
has actually exited successfully, with raw logs under
`D:\HR(EIS)\lab 9\evidence`.


## 20. Independent preflight R1 follow-up and first real browser action (2026-11-22)

The unedited independent read-only preflight report is saved at
D:\HR(EIS)\lab 9\evidence\A9-20261122-preflight-independent-uncommitted-NOT-APPROVED.txt.
Its verdict was **NOT APPROVED** on uncommitted code. It is NOT the required
formal clean committed-clone nine-dimension scorecard.

### Corrected preflight findings

- R1-02: HR administrator cannot assign reviewers to own appraisal,
  including when other user IDs are supplied. Regression included.
- R1-03/R1-10: frontend finance guard now matches the navigation IAM
  permission. A backend static route test verifies every HR-EIS nav path.
- R1-04: separate finance correctness-review endpoint, guarded by
  hreis.finance.review; review-only users audit manual evidence without
  changing payment state. The hreis.finance.update action requires either
  the same actor's review permission or an exact prior immutable
  correctness-review reference. Independently scoped review/update tests
  and a frontend review-only workflow regression cover the separation.
- R1-06: all 13 mutating HR-EIS API views use a shared per-IAM-identity
  write throttle, while GETs remain unthrottled. A regression checks
  the third malformed write returns HTTP 429.
- R1-09: hreis_import_policies command imports explicit source-approved
  JSON policy versions using a fresh live IAM session from the environment
  variable HREIS_OPERATOR_IAM_TOKEN; it enforces active HR-admin status and
  policy.manage grants, rejects conflicting version definitions and
  atomically refuses partial imports. No policy values are invented.
- R1-11: deterministic generator ops/docs/hreis_reference.py produces
  docs/09-hreis/hreis-reference.md from real registry and
  workflow declarations. It includes caveats for external providers.
- R1-12: a real PostgreSQL two-thread test submitted two independent
  two-day final leave approvals against one three-day balance: one succeeds,
  one is refused, the ledger remains one day. No double debit occurs.
- R1-13: claim-summary API exposes timestamped immutable external
  financial-status history, with prefetching to prevent list N+1 queries.
- R1-14: HR-only, redacted detail endpoint for historical compliance
  request statuses. Medical/form/claim evidence stays inaccessible.
- R1-16: explicit rationale for broad email-provider failure handling,
  preserving retryable outbox rows.
- R1-18: early coverage and migration counts in this report are explicitly
  historical, superseded by the latest post-change evidence.
- R1-19: two generated migration-header banners removed without changing
  the migration operations.

### Fresh first browser action — PASS, synthetic fixture only

D:\HR(EIS)\lab 9\fresh_a9_browser_proof.sh used a new uniquely named
disposable PostgreSQL database, migrated all applications, reversed and
reapplied all four HR-EIS migrations, and verified HR-EIS remained PLANNED
without institutional rules. Four explicitly SYNTHETIC policy versions were
then loaded into that disposable database, its readiness became ACTIVE and
a genuine development IAM staff account used Chromium to submit a one-day
leave from the actual React page. The backend returned HTTP 201, the
scoped UI rendered request #1 and DB assertions verified its immutable
leave_submit audit event, dashboard notification, and unchanged ledger
until authority approval. All temporary services and the throwaway DB
were removed. Screenshot is available at
D:\HR(EIS)\lab 9\evidence\A9-20261122-fresh-first-browser.png.
This proves a synthetic first-browser journey, NOT institutional policy
approval, production SMTP, payment or real payroll integration.

### Accurately deferred and unresolved

- R1-01: written Student 2 blueprint/gap/shared-file approvals deferred
  by the user until handoff; none has been forged.
- R1-05: the specification provides designated appraisal authority
  transitions but does not prescribe how multiple independent peer
  reviewers collectively authorize a stage. The route enforces its
  assigned first reviewer and authority; collective-review semantics
  require a source/workflow ruling before expanding the state machine.
- R1-07/R1-08: prior E2E coverage includes employee role denials,
  HR admin and navigation, plus the new isolated successful leave
  browser action, but NOT all 21 use cases end-to-end with live
  institutional IAM identities and provider accounts. Server-side
  builder tests exercise the wider workflow and bad paths.
- R1-15: the module retains four independent reversible migrations,
  including two database-level immutability triggers. Both the live
  dev database and clean disposable DB passed migration and reverse/
  reapply checks. Rewriting migration history before handoff risks
  existing development data; no schema drift is hidden.
- R1-17: some well-tested workflow, validation and React functions
  remain longer than a suggested size guideline. This style finding
  does not supersede successful correctness and architecture gates.
- Exactly 6/193 source requirements remain without direct builder-test
  references: HR-CFR-013, HR-AFR-090, HR-AFR-091, HR-AFR-092,
  HR-AFR-093 (real external sync/integration), and HR-AFR-059
  (returned LTC claims lack a canonical return transition).
- Existing Accounts Admin designation remains a PROVISIONAL mapping
  to the source HR Accountant actor, not an institutional ruling.
- No automated Git commit, push, PR, student-written approval, Student 2
  independent specification tests or formal clean-clone 10/10 review
  has been performed by the builder. The original NOT APPROVED
  preflight output remains preserved.


## 21. Final Student 1 post-change execution evidence (2026-11-22)

All checks in this section were made **after the R1 code corrections** and
use the local, uncommitted module/hreis checkout. The full raw output
of each command, including test exit status, is preserved in
D:\HR(EIS)\lab 9\evidence under these filenames:

| Verified gate | Exact latest result | Raw evidence file |
|---|---|---|
| make check | PASS, exit 0; Django, migration drift, Ruff, architecture, nav, permission manifest, OpenAPI and full pytest suite | A9-20261122-final-make-check.txt |
| make check-client | PASS, exit 0; TypeScript + **61/61 Vitest** + Vite production build | A9-20261122-final-check-client-61.txt |
| HR-EIS whole-module combined statement/branch coverage | PASS: **91.36%**, required >=90% | A9-20261122-final-module-coverage-91-36.txt |
| HR-EIS pure-domain combined statement/branch coverage | PASS: **95.73%**, required >=95% | A9-20261122-final-domain-coverage-95-73.txt |
| Chromium browser E2E (single worker because IAM developer role refresh collides under parallel login) | PASS: **18/18** | A9-20261122-final-browser-18-pass.txt |
| Clean disposable DB reversal/reapplication and actual first UI leave request | PASS: synthetic real browser POST 201, scoped request render, immutable audit, owner notice, unchanged balance, disposable DB dropped | A9-20261122-final-fresh-browser-proof-pass.txt; A9-20261122-fresh-first-browser.png |
| Concurrent leave balance double-spend regression | PASS: one of two approvals allowed, other conflict, ledger has exactly one debit | A9-20261122-final-concurrent-leave-pass.txt |
| Policy-file import, immutable financial history and request permission regressions | PASS (focused) | A9-20261122-policy-import-finance-guard-tests.txt |
| Source ID to direct builder-test reconciliation | **187/193 linked**, 6 explicit external/source ambiguities | docs/09-hreis/hreis-traceability-status.md |

The first parallel Chromium attempt returned a shared IAM role-refresh race;
its complete failure output was saved, the Playwright worker count was set to
one, and subsequent full runs passed. No failed round was hidden. Prior
mutation exercise: **5/5 controlled mutations detected and restored** on the
earlier checkpoint, not rerun after the latest API changes; previous mutation
evidence remains in D:\HR(EIS)\lab 9\mutation-results.

### Truthful readiness for human handoff

**Student 1 technical builder work is ready for human review of the
remaining explicit exceptions**, not equivalent to an approved 10/10
submission or a production deployment. The only remaining external/source
requirements without direct tests are HR-CFR-013, HR-AFR-090/091/092/093
(live payroll/finance/IAM synchronization) and HR-AFR-059 (returned LTC state
not specified in canonical transitions). Shared file approvals, blueprint
approval, provisional Accounts Admin IAM designation mapping, institutional
policy values, external provider access, full live-role manual testing and
Student 2's separate specification suites remain pending. The 2026-11-22
independent read-only preflight returned NOT APPROVED **before these latest
fixes**; there is no new post-fix formal reviewer verdict. A fresh committed
clone review requires a human Student 1 Git commit and separate session.

The handoff index is docs/09-hreis/student1-handoff.md. The source, local DB
volumes, and all evidence are preserved. No automated commit, push, PR, bank
execution, external sync, or fabricated student approval has occurred.

## 22. Post-fix mutation and deployment supplement (2026-11-22)

An additional **post-fix** five-mutation experiment has now completed (not merely
the earlier round referenced in section 21). The corrected local-only runner
`D:\HR(EIS)\lab 9\verify_five_mutations_postfix.py` uses an adjusted
service-record scope anchor to match current source, and writes distinct logs to
`D:\HR(EIS)\lab 9\mutation-results-postfix-20261122\` so earlier evidence
is preserved. All five deliberate mutations were detected by the assigned
tests: employee record scope, permission gate, available leave balance,
approval-route finality, and request idempotency. Each targeted test then
**passed after restoration**. SHA-256 comparisons against the saved original
bytes confirmed **all five files restored exactly**, and the run exited 0.

The separate CI-shaped production Django deployment check exited **0**:
`System check identified no issues (2 silenced).` It was run with the
repository's documented local-only `config.settings.prod` inspection values,
not real deployment credentials. Raw command evidence is
`D:\HR(EIS)\lab 9\evidence\A9-20261122-postfix-prod-deploy-check.txt`.
The deterministic `ops/docs/hreis_reference.py` regeneration also exited
0 and produced a byte-identical reference. `git diff --check` remains clean;
`HEAD...upstream/main` remains `0 0`. No source changes made by mutation
testing are left in the checkout.

**Unclosed technical verification boundary:** the 18-case full Playwright
suite contains 9 HR-EIS-specific cases. The separate disposable-database
Chromium proof exercises a successful employee leave submission, but the
repository Playwright suite has not yet independently exercised each of the
21 live HR-UC main flows with all authority, Accountant and scheduled actors
as Step 6.9 requires. The backend HTTP journey and domain tests provide
broader flow coverage, but are not a substitute for those live-role browser
runs. This limitation cannot be represented as complete browser use-case
coverage or a formal 10/10 verdict. Real external identity, payment and
notification-provider claims remain unverified by design.

Student 2 communication/approvals remain deferred by the assignment owner.
No commits, pushes, PRs or deployment were executed in this supplement.

## 23. Isolated mobile Chromium clean-install follow-up (2026-11-22)

A distinct disposable database `fusion_integrated_a9_readiness_mobile_20261122`
was used to repeat the clean-install and first-user-action proof at a **390 x
844 px mobile Chromium viewport**. The supplementary lab-only scripts are
`D:\HR(EIS)\lab 9\fresh_a9_mobile_browser_proof.sh`,
`seed_a9_synthetic_mobile_only.py`, and `fresh_browser_mobile_click.cjs`.
They explicitly refuse an existing database, require synthetic authorization,
and do not edit institutional settings or the production/default database.

The final run exited **0**. All migrations applied; HR-EIS migrations
reversed and reapplied; `seed_modules` marked the policy-free module PLANNED;
four synthetic family policies enabled ACTIVE readiness. The real Chromium
leave form returned **HTTP 201**, created a pending-authority request, and
showed the request on the employee's scoped page. Browser measurements
reported `{viewport:390, content:390}` (no document-level horizontal
overflow). SQL verification found the leave-submission audit event, one
employee notification, and no premature balance debit. The temporary DB
was dropped, its absence verified, and ports 8002 and 5173 were released.
The screenshot is `D:\HR(EIS)\lab 9\evidence\A9-20261122-fresh-mobile-first-browser.png`;
the separate text summary is `A9-20261122-postfix-mobile-proof-pass.txt`.
The mobile table uses a horizontal inner scroll container for remaining
columns, so this is not a claim that every column fits simultaneously.

These results verify a narrow **synthetic** mobile submission journey only,
not live institution workflows across every HR-UC or the independent 10/10
review. No Student 2 communication or Git commit/push/PR was performed.

An additional **read-only** post-fix external audit was attempted on the
uncommitted checkout, but it returned no report after approximately ten
minutes and was stopped. It supplies **no** verdict, score or cleared
finding, and no independent review approval is claimed from that attempt.


## 24. Complete Student 1 technical verification (2026-11-22)

This checkpoint supersedes earlier test counts and the earlier browser-coverage
limitation. It does not supply written Student 2 approvals or an independent
10/10 verdict.

| Final builder gate | Result |
| --- | --- |
| Complete `make check` | PASS, 721 tests, architecture, migration drift, permissions and OpenAPI checks |
| `make check-client` | PASS, TypeScript, 65 Vitest tests, production build |
| Module combined statement/branch coverage | PASS, 292 tests, 91.50% against 90% |
| Pure domain combined statement/branch coverage | PASS, 292 tests, 95.73% against 95% |
| Production-settings deployment check | PASS, no unsilenced issues |
| Frontend dependency audit after security updates | 0 known vulnerabilities |
| Installed Python dependency audit | 0 known vulnerabilities; local editable application excluded |
| Final Chromium suite | PASS, 33/33 tests, including 24 HR-EIS cases mapping all 21 live use cases |

Raw logs are outside Git at `D:\HR(EIS)\lab 9\evidence\A9-20261122-quality-*.log`.
Dependency evidence is in `A9-20261122-dependency-audit-fixed.json` and
`A9-20261122-python-dependency-audit.json` in the same directory.

`browser-coverage.md` maps each of the 21 live use cases to the real browser
journeys. The expanded suite adds all four claim subtypes through HR verification,
HOD forwarding, Registrar approval and Accountant review/status recording;
rejected claims cannot enter finance. It also covers appraisal assignment,
forwarding and final archive, record creation and stale revisions, owner isolation,
CSRF, rejection reasons, and real reminder/deadline generation with idempotency.
The event-triggered cases use production notification services and verify their
actual dashboard output; they do not pretend that a scheduler or SMTP is deployed.

The isolated runner applies, reverses and reapplies HR migrations, checks that
policy-free installation fails readiness, loads guarded synthetic policies and
records using real IAM IDs, and drops its unique database at exit. An explicitly
opted-in synthetic IAM credential is held only in memory and revoked at cleanup.
No development/default HR database is reseeded by these browser tests.
The final run ended with ready policy status, successful database removal and
revocation of its temporary IAM service credential. Ports 8002 and 5173 were
released before preparing the independent-review checkout.

Newly reproduced and repaired issues:

- Nonscalar policy routing scope caused an HTTP 500; malformed settings now
  return 400 without a policy or audit write.
- Omitting the optional policy end date caused an HTTP 500; the serializer now
  supplies an open-ended default, with a successful HTTP regression.
- A validation notification could cover the drawer submit button and prevent
  a retry while hovered; HR request notifications now use the top-center position.
- Request tracking lacked the maintained workflow history required by HR-UC-005.
  A scoped detail response and read-only drawer now show chronological authority
  actions, reasons and recorded financial history. Foreign request IDs return 404.
- Malformed role-switch bodies caused an exception; transport validation now
  rejects them without changing the session.
- Role switching retained previous-role query data; outstanding scoped queries
  are canceled and their cached values removed before the new session is exposed.
- The shared frontend dependency audit reported 9 advisories, including high and
  critical entries. Vite, its React plugin, Vitest, React Router and the affected
  redirect dependency were updated. Obsolete router migration flags were removed;
  the complete frontend gate passes and the repeat audit is empty.

Shared-file changes include registration and generated manifests/schema, the
role-switch endpoint and regression fixtures, scoped frontend cache eviction,
router/dependency compatibility updates, and browser account/setup configuration.
They are part of the owner's requested technical work; independent written
Student 2 approval remains deferred and is not fabricated.

The 187/193 direct source-ID builder-test mapping remains distinct from browser
use-case coverage. Six source/integration obligations remain explicitly open in
the traceability record: test-only manual references cannot prove institutional
finance exchange, secure document storage, real provider delivery, or an undefined
LTC return transition. Student 2's independently authored suites are untouched.

The old GitHub branch contains a prior Student 1 prototype. Its history will be
preserved while the current implementation remains based on latest upstream main.
The owner explicitly requested the current commit/push handoff. No institutional
pull request, production deployment, external payment or Student 2 message is
part of this technical handoff.

## 25. Review-driven technical verification (2026-11-22)

This checkpoint supersedes section 24's counts. It records technical evidence;
the required written approvals, protected-file ruling and final independent
verdict remain distinct. Student 2's reserved tests/spec and spec-tests folders
have not been authored or changed.

| Quality gate | Latest completed result |
|---|---|
| Complete backend `make check` | PASS, 806 test outcomes; Django, lint, architecture, FK boundaries, plural contracts, route/nav, migrations, permissions and OpenAPI checks |
| Complete frontend `make check-client` | PASS, 67 tests, TypeScript and production build; nonfatal 514.84 kB main-chunk warning |
| Module combined coverage | PASS, 377 tests, 92.13% against 90% |
| Pure domain combined coverage | PASS, 377 tests, 95.79% against 95% |
| Complete Chromium suite | PASS, 58 tests: 49 HR-EIS cases and 9 shared/platform cases |
| Production-settings deployment checks | PASS, zero unsilenced issues; existing production settings silence two documented warnings |
| Frontend dependency audit | Zero known vulnerabilities |
| Installed Python dependency audit | Zero known vulnerabilities; editable local application excluded |
| Schema/client/reference consistency | OpenAPI regenerated, wire types derived from it, 193 enforcement links resolve, deterministic output checks pass |
| Migration lifecycle | One initial migration; fresh apply, reverse-to-zero and reapply succeed with immutable triggers retained |

The backend outcome count is read from the completed pytest progress output
(the repository's double-quiet configuration omits the numerical summary).
The exact coverage commands remain those in section 24. Final logs and audit
JSON are in `D:\HR(EIS)\lab 9\evidence\A9-20261122-quality-*.log`,
`A9-20261122-dependency-audit-final.json` and
`A9-20261122-python-dependency-audit-final.json`.

The synthetic browser suite covers all 21 live use cases, both unavailable
external-status alternatives, all twelve registry designations, ten direct
permission-negative routes and a keyboard-only leave submission.
[`browser-walkthrough.md`](browser-walkthrough.md) contains actor/dump-account
rows with actual matched runserver lines; [`browser-coverage.md`](browser-coverage.md)
describes the test isolation and use-case map. Full raw logs remain outside Git.
Each run drops its disposable database, restores temporary IAM permissions and
revokes its temporary service credential. No institutional policy or provider is seeded.

New technical changes and their regression evidence are listed individually in
[`review-remediation.md`](review-remediation.md). Important corrections include
database-enforced appraisal uniqueness, finite input bounds, independently
permission-gated controls, unknown external status with later immutable history,
service-owned notification writes, platform throttling, complete endpoint gate
and query-budget matrices, concurrent task redelivery, actual directory refresh,
HTTP-boundary frontend tests and generated API examples/types.

The initial migration is for this unmerged module's clean installation. The
development database was backed up and upgraded through the interim integrity
migration before consolidation; its records were preserved. Both the old chain
and `dev-before-r1-integrity.dump` remain outside Git. Do not reverse or reset a
database containing records to adopt this clean initial set; older draft schemas
need a separately checked data-preserving upgrade.

Direct builder-test citations now cover 188/193 live IDs. Five remain uncited;
six broader source/integration obligations remain unresolved, including the
partially verified identity-consistency obligation. No unresolved requirement is
treated as a signed accepted gap. External storage, finance/payroll exchange,
official delivery configuration, the provisional Accounts Admin mapping and
the undefined LTC return outcome retain the limitations stated in the blueprint.

Independent round 1 reviewed clean committed checkout
`e93cc164218353145556f591d672d5f1c78c8ef5` and returned **not yet**.
Its scores were **3 / 1 / 7 / 4 / 0 / 1 / 3 / 2 / 9**, in the prescribed order.
The full output and SHA-256 are recorded in review-remediation.md. The candidate
addresses its technical findings, while R1-01, R1-02 and the unresolved part of
R1-06 remain explicit. No 10/10 is inferred from passing automated gates.

A second fresh checkout with its own dependencies is prepared for the next
committed-clone review. The branch's earlier Student 1 prototype history was
preserved by a merge; the verified implementation remains based on upstream
main `5595be6628b4cdc6f8b47cf74bac267a2470f780`. The owner's current request
authorizes the technical Git handoff. It does not supply Student 2 signatures,
a production deployment or the final institutional pull request.
