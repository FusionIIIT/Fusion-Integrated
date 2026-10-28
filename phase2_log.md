# Phase 2 ELM Engineering Log

## Scope and baseline preservation

This log records the material findings from reviewing and improving the inherited
Phase-1 ELM implementation against the supplied ELM specifications and Fusion
module conventions. The original implementation is preserved in
`phase2_evidence/phase1-final-baseline-933548f.zip`; the starting Phase-2
workspace is also archived as `phase2_evidence/phase2-starting-workspace-9bf0e38.zip`.
The original source was taken from the `phase1-final` tag because the selected
ELM source was not present on the initial Phase-2 branch.

The v1.6 workflow specification is treated as the current workflow reference.
The older v1.5 traceability matrix has a conflicting count of basis workflows
(17 versus 19); this discrepancy is recorded below rather than silently
reconciling the two documents.

## Issue register

### P2-01 — ELM was not reachable as a complete Fusion module

- **Severity/status:** High — resolved for the implemented scope.
- **Finding and impact:** The inherited module had domain/model/service code but
  lacked the Fusion-mounted ELM API, migrations, client routes/pages, and
  registration needed to exercise it as an ERP module. The Fusion configuration
  referenced ELM entry points that were absent.
- **Specification/integration basis:** ELM workflows require user and staff
  access through the integrated system; Fusion module patterns require
  configuration, route, permission, and client registration.
- **Change:** Added ELM API serializers/views/URLs and migrations; registered
  the module in Django settings and URL routing, the client registry and routes,
  and the generated permission catalog. Added employee leave, approval, and
  year-end screens.
- **Verification/evidence:** `phase2_evidence/test-results/phase2-elm-backend-tests-final.txt`,
  `phase2_evidence/test-results/phase2-client-typecheck-final.txt`,
  `phase2_evidence/test-results/phase2-client-tests.txt`,
  `phase2_evidence/test-results/phase2-client-build-final.txt`,
  `phase2_evidence/test-results/phase2-permission-manifest-check.txt`, and
  `phase2_evidence/test-results/phase2-nav-route-check.txt`.

### P2-02 — Cross-year leave did not account against every year's balance

- **Severity/status:** High — resolved.
- **Finding and impact:** The inherited leave accounting treated a request as
  belonging to its start-year account. A request spanning a calendar-year
  boundary could therefore under-debit, validate against the wrong balance, or
  restore only part of its debit when cancelled.
- **Specification basis:** Leave entitlement and year-end rules are calendar-year
  based; leave used in a year must be charged to that year's account.
- **Change:** Split chargeable days and ledger transactions by calendar year;
  validate each year's available balance and restore all corresponding debits.
- **Verification/evidence:** Regression tests
  `test_cross_year_leave_uses_and_debits_each_years_balance` and
  `test_cancellation_restores_all_debits` in `modules/elm/tests/test_services.py`;
  final ELM test run in `phase2_evidence/test-results/phase2-elm-backend-tests-final.txt`.

### P2-03 — Resumption accounting and state could be incorrect

- **Severity/status:** High — resolved for covered rules.
- **Finding and impact:** Resumption used calendar-day differences in place of
  chargeable leave, could make a balance negative, and could mark the original
  approved leave completed rather than preserving that approval record. The
  specification also makes resumption on the approved end date a no-adjustment
  case.
- **Specification basis:** ELM resumption workflow and leave-account adjustment
  rules in the supplied workflow and business-rule specifications.
- **Change:** Apply chargeable-day adjustments by year, reject insufficient
  balance, preserve the original approved request, and record the resumption on
  its follow-up request. Equality with the approved end date does not adjust the
  balance.
- **Verification/evidence:** Regression tests
  `test_late_resumption_adjustment_cannot_create_negative_balance` and
  `test_early_resumption_restores_chargeable_days` in
  `modules/elm/tests/test_services.py`; final ELM test evidence above.

### P2-04 — Substitute decline/replacement state allowed invalid transitions

- **Severity/status:** High — resolved for the reviewed workflow.
- **Finding and impact:** After declining, a substitute could respond again
  without the applicant action/replacement gate; repeated replacements could
  also bypass the intended one-time limit.
- **Specification basis:** Substitute acceptance/decline and applicant
  replacement workflow in the ELM workflow specification.
- **Change:** A decline transitions the request to `applicant_action_required`;
  replacement returns it to `substitute_pending`; the replacement limit is
  enforced. Expanded the status field and added a migration.
- **Verification/evidence:** Regression test
  `test_substitute_decline_allows_only_one_replacement` in
  `modules/elm/tests/test_services.py`; test run and migration-drift output in
  `phase2_evidence/test-results/phase2-elm-backend-tests-final.txt` and
  `phase2_evidence/test-results/phase2-migration-drift-final.txt`.

### P2-05 — Approval route selection could prefer the global fallback

- **Severity/status:** High — resolved.
- **Finding and impact:** Ordering nullable unit identifiers descending did not
  reliably guarantee that the more-specific unit route was selected before a
  global route, particularly under PostgreSQL NULL ordering.
- **Specification basis:** Approval routing must select the applicable
  category/unit/designation route.
- **Change:** Select route specificity explicitly before the global fallback.
- **Verification/evidence:** Regression test
  `test_unit_specific_approval_route_precedes_global_fallback` in
  `modules/elm/tests/test_services.py`; final ELM test evidence above.

### P2-06 — Missing leave policy could be silently replaced by defaults

- **Severity/status:** Medium — resolved.
- **Finding and impact:** Implicitly creating default policy for an unconfigured
  year could accept a leave request under entitlements that had never been
  authorized by the institution.
- **Specification basis:** Leave balances must use the configured policy for
  their calendar year; absent configuration is not an entitlement.
- **Change:** Fail explicitly with a conflict when the policy is missing.
  Validate non-negative entitlements and positive, ordered SLA thresholds.
- **Verification/evidence:** API regression
  `test_employee_cannot_create_leave_without_configured_policy` and
  `test_policy_manager_must_set_positive_sla_thresholds` in
  `modules/elm/tests/test_api.py`; final ELM tests.

### P2-07 — New API access required server-side module, permission, and ownership checks

- **Severity/status:** High — addressed and regression-tested for covered APIs.
- **Finding and impact:** Adding endpoints without Fusion authorization and
  scoped data access could expose employee records or allow an unrelated user
  to act on an approval task.
- **Specification/integration basis:** ELM roles and actors in the requirements;
  Fusion IAM module grants and permission conventions.
- **Change:** Apply Fusion module grants and permission checks to ELM views;
  scope applicant/substitute/task queries to the principal and assignment.
- **Verification/evidence:** Tests
  `test_employee_without_module_grant_cannot_access_elm`,
  `test_employee_can_submit_and_list_only_own_requests`,
  `test_applicant_cannot_see_another_employees_request`, and
  `test_unassigned_user_cannot_decide_task` in `modules/elm/tests/test_api.py`.
  The permission manifest check passes.
- **Limit:** This is targeted API/service coverage, not a full institutional
  role matrix or live Fusion IAM deployment test.

### P2-08 — OpenAPI generation was incomplete and warning-prone

- **Severity/status:** Medium — resolved.
- **Finding and impact:** APIViews lacked explicit request/response schemas and
  schema generation evaluated principal-dependent querysets. Multiple choice
  sets named `status`/`category` also caused schema enum collision warnings.
- **Change:** Added explicit API schema annotations and response serializers;
  return empty querysets for schema-generation fake views; use consistent
  leave-category labels and explicit string serializers for status fields.
- **Verification/evidence:** `manage.py spectacular --fail-on-warn
  --file openapi/fusion-integrated.v1.yaml` succeeds without warnings.
  Captured output and schema: `phase2_evidence/test-results/phase2-openapi-check.txt`
  and `phase2_evidence/test-results/phase2-openapi-generated.yaml`.
  The generated document contains 26 ELM paths; this check is captured in
  `phase2_evidence/test-results/phase2-openapi-path-check.txt`.
  The initial warning/error is preserved separately in
  `phase2_evidence/test-results/phase2-openapi-initial-attempt.txt`.

### P2-09 — Phase-1 had insufficient regression coverage; standard local DB setup
was not usable for the legacy project migrations

- **Severity/status:** ELM coverage gap resolved; production database migration
  path remains unverified (see P2-15).
- **Finding and impact:** No ELM regression suite protected the inherited
  workflows. The historical Placement migration sequence attempts PostgreSQL-
  specific behavior and cannot run unchanged on SQLite.
- **Change:** Added domain, service/workflow, and API regression coverage.
  Test settings use in-memory SQLite and disable only the historical Placement
  migration sequence; ELM migrations remain enabled and checked.
- **Verification/evidence:** 26 ELM backend tests pass;
  `phase2_evidence/test-results/phase2-migration-drift-final.txt` reports no
  migration drift.

### P2-10 — Zero-TTL directory cache did not refetch stale rows

- **Severity/status:** Low — resolved.
- **Finding and impact:** A zero-second cache TTL could still treat an identity
  row as fresh because its timestamp and the calculated boundary had different
  database precision.
- **Change:** TTL zero now bypasses the freshness query and always refreshes
  requested identities.
- **Verification/evidence:** All directory synchronization tests pass in
  `phase2_evidence/test-results/phase2-directory-sync-final.txt`; the complete
  backend suite passes in `phase2_evidence/test-results/phase2-full-backend-final.txt`.

### P2-11 — SLA thresholds had no scheduled reminder/escalation processing

- **Severity/status:** Medium — resolved for notification-only processing.
- **Finding and impact:** Policy thresholds existed without a scheduled worker,
  delivery, or auditable event logging.
- **Specification basis:** EL-UC-018/021 and BR-EL-032/033/035/038.
- **Change:** Added a five-minute SLA sweep and one-minute notification worker
  to Fusion Celery. The worker rechecks pending state, sends idempotent
  assignment/reminder/escalation messages through an outbox, logs events, resets
  the SLA clock when waiting tasks become actionable, and supports a configured
  escalation user with workflow-authority fallback.
- **Verification/evidence:** ELM tests cover pending-only processing,
  deduplication, configured escalation, email delivery, and task activation.
  See `phase2_evidence/test-results/phase2-elm-backend-final.txt` and
  `phase2_evidence/test-results/phase2-elm-celery-registration.txt`.
- **Limit:** Celery worker/beat and SMTP were not run against live deployment
  services.

### P2-12 — Offline-sanctioned leave had no synchronization workflow

- **Severity/status:** Medium — resolved for validated record entry.
- **Finding and impact:** An offline reference could be stored, but no authorized
  way existed to update leave balances/history without a second approval.
- **Specification basis:** EL-UC-016 and BR-EL-029/036/037.
- **Change:** Added a processor-only endpoint and admin form requiring an
  employee, dates/category/purpose, sanction reference/date, and reason ELM was
  unavailable. It checks policy, calendar, overlap, duplicate reference, and
  balance; records an approved request and ledger debit; and creates no
  sanctioning workflow.
- **Verification/evidence:** Service/API regression tests cover evidence,
  duplicate references, balance, permissions, and the absence of approval tasks
  in the final ELM test run.

### P2-13 — Resumption-to-attendance synchronization lacks an integration contract

- **Severity/status:** Medium — blocked; the supplied follow-up is generic guidance,
  not an authoritative integration contract.
- **Finding and impact:** No attendance module, client, or adapter exists in
  `modules/` or `core/`. ELM records resumption and adjusts leave balances but
  cannot safely update an unknown attendance system.
- **Specification basis:** EL-UC-011 and the resumption workflow require
  synchronizing actual leave and attendance records.
- **Follow-up received:** The user supplied suggested event fields (`eventId`,
  employee/leave IDs, action, and original/updated dates), attendance recalculation
  semantics, idempotency, retry, and partial-result guidance. The example
  `https://sandbox.example.com/api` is explicitly a placeholder. The user does
  not know the actual attendance service.
- **Handling:** Did not invent an endpoint or implement against generic examples.
  The guidance is useful for future acceptance criteria but does not establish
  the provider API, authentication flow/scopes, concrete payload schema, or
  environment. No reliable integration test can run without those details.
- **Required input:** An authoritative attendance service/API and owner, its
  real endpoint and operation contract, configured token mechanism/scopes, and
  non-production endpoint/test records. This remains a deployment blocker until
  supplied and integration-tested.

### P2-14 — Print/export and administrative workflows were incomplete

- **Severity/status:** Low/Medium — addressed for implemented admin surfaces.
- **Finding and impact:** Employees lacked print/export representations, while
  key configuration and record-maintenance APIs had no admin UI.
- **Specification basis:** Printable/exportable applications and EL-UC-016/017/018,
  plus policy, approval-route, calendar, vacation-period, and employee-profile
  administration.
- **Change:** Added print view and owner-scoped formula-safe CSV export.
  Added administrative screens for policy/SLA setup, offline leave entry,
  approval routes, holiday calendars and publication, vacation periods,
  organizational units, employee profiles, and audited record corrections.
  Corrections cannot change dates/category, workflow, or sanction state.
- **Verification/evidence:** Client typecheck/tests/build, API export tests, and
  strict OpenAPI generation pass; see
  `phase2_evidence/test-results/phase2-client-typecheck-complete.txt`,
  `phase2_evidence/test-results/phase2-client-tests-final.txt`,
  `phase2_evidence/test-results/phase2-client-build-final.txt`, and
  `phase2_evidence/test-results/phase2-openapi-final.txt`.

### P2-15 — Production PostgreSQL/Redis deployment was not available

- **Severity/status:** High deployment risk — blocked/unverified.
- **Finding and impact:** No Docker executable, PostgreSQL, or Redis service was
  available. SQLite tests cannot prove PostgreSQL migrations/constraints,
  distributed locking, SMTP, Celery, or live Fusion IAM behavior.
- **Change:** Kept SQLite configuration isolated to test settings. Added and
  drift-checked ELM migrations; the complete suite applies ELM migrations.
- **Evidence:** `phase2_evidence/test-results/phase2-environment-readiness.txt`.
- **Next step:** Apply migrations and run acceptance tests against supported
  PostgreSQL/Redis/Fusion deployment services.

### P2-16 — Workflow specification and traceability versions disagree

- **Severity/status:** Low — unresolved specification clarification.
- **Finding and impact:** The v1.6 workflow specification reports 17 basis
  workflows while the v1.5 traceability matrix reports 19.
- **Handling:** Used v1.6 as workflow authority; retained the 128-item AFR index
  at `phase2_evidence/test-results/spec-functional-requirement-index.txt`.
- **Next step:** Reconcile against an authoritative version-aligned package.

### P2-17 — Local code-LLM review timed out and contained unverified claims

- **Severity/status:** Method limitation — mitigated.
- **Finding and impact:** The local Aider/Qwen review timed out and returned
  claims contradicted by source/spec review.
- **Handling:** No code change was accepted solely from that response; original
  output remains in `phase2_evidence/test-results/local-llm-initial-review.txt`.

### P2-18 — Audit status columns could not hold the new workflow state

- **Severity/status:** High for PostgreSQL deployment — resolved in schema.
- **Finding and impact:** `RequestEvent` status fields allowed 24 characters,
  but `applicant_action_required` is 25. SQLite does not enforce varchar
  lengths, masking the risk.
- **Change:** Widened both fields to 32 characters in migration
  `0005_workflow_event_status_length`.
- **Verification/evidence:** Substitute-decline test verifies stored state
  length; full backend suite and migration-drift checks pass.

## Verification summary

- ELM-specific backend tests pass, including offline entry, SLA processing,
  notifications, maintenance, export authorization, and workflow transitions.
- The complete backend suite passes; the former directory-cache failure is
  fixed and its focused suite passes.
- Frontend tests: **35 passed**; TypeScript typecheck and production build pass.
- Django check, targeted Ruff, import-linter, permission manifest, migration
  drift, and strict OpenAPI generation pass.
- Final module-boundary, plural-contract, navigation/route consistency, and
  whitespace checks pass; exact ELM collection lists 13 API, 6 domain, and 20
  service tests. Evidence is stored in
  `phase2_evidence/test-results/phase2-no-cross-module-fk-final.txt`,
  `phase2_evidence/test-results/phase2-contracts-final.txt`,
  `phase2_evidence/test-results/phase2-nav-route-check-final.txt`,
  `phase2_evidence/test-results/phase2-elm-test-collection.txt`, and
  `phase2_evidence/test-results/phase2-diff-check-final.txt`.
- Production build still reports the existing large-chunk advisory.
- PostgreSQL/Redis/SMTP/Celery execution, live Fusion IAM, and attendance
  integration remain unverified. Attendance contract, spec version mismatch,
  and deployment environment remain release gates; do not claim unconditional
  production readiness.