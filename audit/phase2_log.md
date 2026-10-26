# Assignment 6B progress log

## Starting point

- Working branch: `phase2` (already one commit ahead of `origin-myfork/phase2`).
- Existing ELM baseline: 3 tests passed.
- Qwen 14B is installed locally. GPU initialization failed, so a local Ollama
  variant was created with partial GPU offload and passed a smoke prompt.

## Completed locally

1. Updated `modules/leave/registry.py` to module code `leave`, the specified 13
   permission tuples, new navigation permission references, and the specified
   role grants. Qwen's first role output was rejected by the checker. A later
   Qwen output passed the permission checker; formatting-only line wraps were
   applied by hand to meet the 100-character limit.
2. Added IAM module and action permission checks to the existing ELM views.
   Actor IDs and employee kind now come from the authenticated principal; the
   views no longer trust `X-User-Id` or `X-User-Role` headers or fallback IDs.
   Qwen's proposed patches were rejected because they used nonexistent APIs or
   left actions unguarded. This authorization correction was applied by hand
   using the existing `fusion_auth.permissions` pattern.
3. Added API tests for module grants, action-specific permissions, invalid
   resumption actions, and identity scoping. The initial Qwen test draft used
   nonexistent paths and permission codes, so the test file was corrected by
   hand to match the current URL table and models.

## Verification

- `manage.py check`: passed.
- Ruff on the changed registry, views, and API test: passed.
- ELM tests: 16 passed.
- Client typecheck: passed.
- Client tests: 35 passed.
- Client production build: passed (Vite reported its existing large-chunk warning).
- Full pytest using SQLite with migrations disabled: one failure remains in
  `test_the_committed_manifest_matches_the_registries`; it reports the four
  declared permissions below have no endpoint or service check.
- Full default pytest could not run in this environment because Docker is not
  installed and the configured PostgreSQL service is unavailable. SQLite with
  migrations enabled also fails on the existing `document_profile_idx` migration.

## Remaining blockers

The checkout and shared Claude snapshot do not contain the authoritative ELM
spec bundle. The shared snapshot hides its attachments. The project guide says to
stop when required specifications are missing, so no new leave behavior was
invented. The permission manifest still identifies these missing features:

- `leave.request.view`: approval-queue listing.
- `leave.policy.manage`: policy configuration endpoint.
- `leave.calendar.publish`: holiday/RH calendar maintenance and publishing.
- `leave.record.manage`: offline sanctioned-leave entry endpoint.

The exact BR, UC, workflow, requirement, and traceability files are needed to
implement and test those flows. The repository assignment guide also requires
mentor readiness before commit or pull request; these changes remain local and
uncommitted.

## Follow-up after authoritative spec bundle was supplied (2026-10-12)

The ELM specification bundle is now available at the user-provided path. This supersedes the earlier blocker statement that the bundle was unavailable; prior implementation was done before access to the authoritative bundle and now requires reconciliation against it.

### Offline synchronization (CFR-EL-027 / UC-016 / BR-EL-029, 036, 037)

- Requirements confirmed: only authorized administrators may record leave already sanctioned through an authorized offline/paper process when ELM could not be used; capture sanction/reference evidence; validate record consistency; synchronize balance/history; do not create a second approval workflow.
- Open specification details: acceptable ELM-unavailable reasons are not enumerated; evidence format/authenticity checks are not specified; detailed consistency/duplicate criteria and balance/chargeable-day reconciliation are not defined in the supplied atomic FR/UC text. Do not implement speculative checks or expose the existing unvalidated sync service until these acceptance rules are resolved.
- Rejected both Qwen-generated endpoint proposals. They invent or reference nonexistent validators/selectors, omit a view definition or tests, use an unregistered permission in the first version, and/or bypass the project's IAM principal permission pattern. No generated patch was applied.

### Other requirement review

- `CFR-EL-024` / `UC-014`: baseline uses current configured policy/hierarchy values and explicitly does not require policy draft/publish/effective-versioning. `LeavePolicyConfig` models current per-category parameters, but no policy/hierarchy maintenance API or hierarchy configuration model was found. Existing request creation still has hard-coded unit-head/sanctioning defaults, so configured routing is not established.
- `CFR-EL-025` / `UC-015`: calendar replacements must remain unpublished until explicitly published, with the currently published calendar governing validation. `HolidayCalendar` has a per-date `is_published` flag (default true) and unique date, but no maintenance/publish API or replacement lifecycle was found; this does not establish the required publish-before-effective behavior.
- `CFR-EL-026` / `UC-017`: authorized record correction must be scoped by role and must not create/replace sanction decisions. No record-maintenance API was found.
- Approval-queue permission `leave.request.view` remains declared/granted but no endpoint/service check is found.

### Verification after spec review

- `pytest modules/leave --ds=config.settings.local_sqlite --nomigrations`: 16 passed; pytest emitted a cache write permission warning.
- `manage.py permission_manifest --check`: still fails for the four declared permissions without endpoint/service checks: `leave.calendar.publish`, `leave.policy.manage`, `leave.record.manage`, and `leave.request.view`.
- No application code was changed during this follow-up.

### Leave entitlement and day-counting review (CFR-EL-004–010; BR-EL-002–011)

- `submit_leave_request` calculates chargeable days and checks an existing account balance, but it creates a missing account with `balance=0.0`. No account provisioning/credit service was found (`rg` over `modules/leave` shows only these account reads/writes and no use of `LeavePolicyConfig.annual_entitlement`). Thus baseline annual entitlements are not granted by the ELM implementation: CL 8, RH 2, SCL up to 15, non-faculty EL 30, faculty VL 60, and COL 20 are not established for new accounts.
- The policy model's `annual_entitlement` is not consumed by request submission, and its default is 0.0. Existing API tests seed a CL account manually, so they do not cover entitlement creation or year transitions.
- `calculate_days` has a CL half-day shortcut and category-specific continuous-day counting. `submit_leave_request` checks start <= end and published RH/VL constraints before calculation. Existing domain tests only exercise one weekly EL/CL interval, one opposite-half overlap, and a faculty year-end conversion; there is no coverage for RH/SCL holiday exclusion, half-day balance deduction through approval, policy-configured entitlement, or account provisioning.
- Follow-up needed: add entitlement credit/provisioning and applicable rule tests only after reconciliation with the configured policy and external academic-calendar requirements. Do not silently hard-code conflicting defaults while `LeavePolicyConfig` is intended to hold current policy values.

### Additional category, year-end, and resumption gaps

- `LeavePolicyConfig.requires_medical_proof` exists, but no leave request field/API payload or service validation captures or checks required COL medical evidence. Search found no ELM medical-evidence/document integration.
- `AcademicVacationPeriod` is an ELM table queried directly by VL submission. The requirement names vacation periods supplied by the institute Academic Calendar maintained outside ELM; no external-calendar adapter/import was found in the ELM module. Confirm whether this table is intended to be an imported mirror.
- CFR-EL-028/UC-020 require an event-triggered operation that updates persisted accounts, records account transactions, and reports exceptions. Current code only has the pure `rules.execute_year_end_processing` calculator and one calculation test; no service/job persists year-end results or produces transaction/exception records.
- CFR-EL-021 requires reviewed early/late returns to record the actual leave period and synchronize relevant leave/attendance records. `review_resumption` adjusts the balance and stores `actual_resumption_date`, but does not update the approved period (`end_date`) or invoke a leave/attendance synchronization integration. Treat this as a functional gap; confirm expected attendance integration boundary.

### Verified Phase 2 improvement: new-account entitlement and RH day counting

- Confirmed the Phase 1 source is preserved by the `phase1-final` tag before Phase 2 changes.
- Updated `submit_leave_request` so a newly created account uses the current `LeavePolicyConfig.annual_entitlement` when configured and otherwise uses the applicable baseline amount from CFR-EL-004–009: CL 8, RH 2, SCL 15, staff EL 30, COL 20, and faculty VL 60. Faculty EL remains zero absent a configured entitlement because CFR-EL-007 states 30 EL only for non-faculty.
- Fixed RH calculation: an applicable published RH date now counts as one RH day instead of being discarded as a holiday by the generic working-day calculation. The service already limits RH requests to one date and validates that it is a published RH date.
- Added regression coverage for baseline account provisioning, configured entitlement override, and chargeable RH date.
- Verification: ELM pytest suite: 24 passed; Django system check: passed; Ruff on the new tests and import ordering: passed.
- Limitation: existing account rows are not retroactively credited. Automatically adding entitlement to a pre-existing zero balance could incorrectly restore a genuinely exhausted balance; a controlled migration/reconciliation is needed for existing data.

### Verified Phase 2 improvement: assigned-authority checks

- `review_unit_head` now rejects decisions from an actor other than the request's recorded `unit_head_id`.
- `sanction_decision` now rejects decisions from an actor other than the recorded `sanctioning_authority_id`, while retaining the specified Director self-sanction exception.
- `review_resumption` now requires the recorded sanctioning authority.
- Added three service regression tests proving mismatched actors are rejected without changing workflow state.
- ELM suite after both code improvements: 27 passed. Full SQLite suite: 406 passed, one known failure in `test_the_committed_manifest_matches_the_registries`, which still reports the four unimplemented permission capabilities. Django system check and targeted Ruff checks pass.
- Routing limitation remains: the API accepts `unit_head_id` and `sanctioning_authority_id` from the applicant, while the supplied Fusion/IAM integration has no hierarchy resolver. Actor-to-recorded-ID checks improve enforcement but cannot prove that the stored routing assignment came from the current configured hierarchy. Do not expose a queue as trustworthy until routing is resolved from authorized configuration.


### Verified Phase 2 improvement: reviewed resumption period correction (CFR-EL-021; BR-EL-028)

- On an authority-reviewed early or late resumption, `review_resumption` now updates the request's recorded `end_date` to the actual resumption date, alongside the existing balance adjustment. Normal resumption leaves the approved period and balance unchanged.
- Added service regression tests for early return, normal return, and late return. The ELM suite passes: 30 passed.
- Full SQLite suite: 409 passed, 1 failed. The only failure remains `test_the_committed_manifest_matches_the_registries`, which reports the four existing unimplemented permissions/features: calendar publish, policy management, record maintenance, and request view/approval queue.
- Limitation: the repository contains no attendance module or integration contract. The resumption workflow can now persist the corrected leave period, but cannot synchronize attendance records without an available interface. No speculative attendance API was introduced.


### Verified Phase 2 improvements: administrative, routing, and calendar capabilities

- Added actor-scoped `GET /requests/inbox/` and filter logic for substitute, Unit Head, Establishment, sanction, and resumption tasks. New requests store a foreign key to the hierarchy configuration used at submission; the inbox and decision services reject legacy requests without trusted route provenance. The request API ignores client-supplied authority IDs and uses the authenticated IAM department and active role. Missing routes fail closed.
- Added current policy and hierarchy maintenance under `leave.policy.manage`. Policy values now affect new requests: entitlement, half-day eligibility, continuous-day counting, and required substitute behavior. Added SLA threshold configuration under the same administrative permission.
- Added staged holiday-calendar releases. A draft can be revised without changing effective validation dates; explicit publication atomically replaces the currently effective release. Existing legacy date rows remain effective until the first release is published.
- Added offline synchronization and record-correction endpoints under `leave.record.manage`. Offline sync is additionally restricted to the Leave Administrator role; evidence and ELM-unavailable reason are required, chargeable days are server-calculated, invalid dates/categories/RH/VL intervals and existing overlaps are rejected, insufficient or mismatched balances are rejected, and a database uniqueness constraint prevents repeated applicant/reference entries. The resulting record is immediately `APPROVED` with a synchronization audit action; no second sanction workflow is created. Administrative correction allows descriptive fields only, requires an audit reason, and cannot change decision/status fields.
- Added ELM schema migrations `0001`�`0003`, including trusted route provenance, calendar release/entry tables, hierarchy configuration, and offline duplicate protection. Fixed a pre-existing ordering defect in placement migration `0009` (remove the index before removing its field) because it broke fresh database migration/test setup.
- Expanded service and API tests for route spoofing, fail-closed missing hierarchy, actor-scoped queues, current policy behavior, calendar draft/revision/publication, offline sync and balance updates, record correction, and role/permission denial.
- Verification: full SQLite suite with migrations: 429 passed; Django system check passed; permission manifest check passed; `makemigrations --check --dry-run` reports no changes. Ruff passes on API views/serializers/URLs, services, selectors, auth changes, and the new focused tests. A full `ruff check modules/leave` still reports pre-existing wildcard re-export and model-style findings outside these targeted files.

### Remaining integration limits after this pass

- The repository has no Attendance module or attendance API. A transactional `AttendanceSyncOutbox` now records the approved and corrected leave periods, actual resumption date, employee, category, and action when a resumption review commits. The event is durable and idempotency-keyed, but there is no Attendance consumer to deliver it; actual attendance rows remain unsynchronized until that module/contract is supplied.
- `LeaveSLASettings` can now be maintained, but there is no ELM event-triggered SLA processor/notification consumer in this repository to act on reminder and escalation thresholds.
- Offline evidence is captured as an operator-entered reference and reason. The specification bundle does not define an accepted-reason catalogue or an evidence-verification integration, so the service cannot independently establish that the referenced paper sanction is authentic.
- Record maintenance is deliberately limited to descriptive text fields because the specification does not define which roles may alter dates, categories, or balances. Correcting those fields safely needs explicit reconciliation rules and transaction history.
- Existing deployments that already created ELM tables without migration history need a baseline/fake-initial migration procedure before applying the new initial migration; a fresh test database applies the migrations successfully.

- Resumption outbox verification: early, normal, and late reviewed returns commit an event in the same transaction as period/balance changes. The early-return test confirms both original approved end date and corrected recorded end date are present in the event payload.
