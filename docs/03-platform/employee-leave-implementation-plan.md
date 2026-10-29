# Employee Leave Management (ELM) — Implementation Plan

**Branch:** `module/elm`
**Status:** Proposed — awaiting mentor approval
**Purpose:** Track implementation against ELM specifications and Fusion module conventions.

## 1. Working rules

- Treat the ELM specification documents as the source of truth.
- Follow `docs/03-platform/module-authoring-guide.md`.
- Review `docs/03-platform/shared-kernel-reference.md` before proposing shared-kernel changes.
- Keep ELM isolated in its own bounded context.
- Do not introduce cross-module database foreign keys or import another module's internals.
- Use selectors for reads and services for writes.
- Keep domain rules in pure Python wherever possible.
- Keep leave-specific rules and approval workflows inside ELM; do not build a generic approval engine in `core/`.
- Do not add to `core/` unless the shared-kernel admission criteria are met and affected module owners review the change.
- Check the actual repository before using any shared component marked planned in the reference document.
- Integrate across module boundaries through public contracts and approved event schemas, not another module's internals.
- Do not activate the module until its implementation and verification are complete.
- Do not commit unrelated changes, including the existing `.gitignore` change, without reviewing them.
- Do not implement the module until the mentor has reviewed and approved the blueprint.

## 2. Mentor approval gate

- [ ] Confirm module code and package name.
- [ ] Confirm employee identity and organizational-unit references.
- [ ] Confirm role names, permission grants and approval hierarchy configuration.
- [ ] Confirm how academic calendars and attendance/resumption synchronization are accessed.
- [ ] Confirm year-end processing trigger, retry and audit requirements.
- [ ] Confirm frontend scope and navigation requirements.
- [ ] Confirm cross-module contracts and events.
- [ ] Record mentor feedback and approval date.

## 3. Phase A — Repository preparation

- [x] Review ELM problem statement.
- [x] Review functional requirements.
- [x] Review use-case specifications.
- [x] Review business-rule specifications.
- [x] Review traceability matrix.
- [x] Review workflow specifications.
- [x] Review Fusion module-authoring conventions.
- [x] Review the reference Placement module architecture.
- [ ] Confirm working-tree changes and preserve unrelated work.
- [ ] Obtain mentor approval before application implementation.

## 4. Phase B — Module foundation

- [ ] Scaffold the approved module using repository conventions.
- [ ] Add the module app configuration and registry.
- [ ] Define module permissions, role grants and navigation.
- [ ] Add the module to the appropriate settings and architecture-layer configuration.
- [ ] Define public contracts and events only where justified.
- [ ] Keep the module status non-active during development.
- [ ] Run the permission manifest checks.

## 5. Phase C — Domain rules and tests

- [ ] Define leave categories and explicit lifecycle states.
- [ ] Implement category eligibility and entitlement rules.
- [ ] Implement half-day CL and category-specific date counting.
- [ ] Implement overlap validation and holiday/calendar checks.
- [ ] Implement substitute eligibility and consent gates.
- [ ] Model Unit Head recommendations separately from final decisions.
- [ ] Implement configurable approval routing and the Director exception.
- [ ] Implement withdrawal, cancellation, extension and resumption rules.
- [ ] Test invalid transitions, boundary dates and policy exceptions.
- [ ] Keep domain tests independent of Django and external services.

## 6. Phase D — Data and persistence

- [ ] Design module-owned application and workflow-history records.
- [ ] Design balance accounts and auditable balance transactions.
- [ ] Design substitute assignments and approval tasks/decisions.
- [ ] Design policy configuration and published calendar references.
- [ ] Design extension, cancellation, resumption and offline-entry records.
- [ ] Add explicit constraints and indexes.
- [ ] Add migrations and required database-role grants.
- [ ] Verify migration consistency and avoid cross-module foreign keys.
- [ ] Define concurrency-safe, idempotent balance updates.

## 7. Phase E — Services, selectors and APIs

- [ ] Implement selectors for scoped reads.
- [ ] Implement transactional services for all writes.
- [ ] Lock relevant records where concurrent decisions or balance updates require it.
- [ ] Record auditable state transitions and decisions.
- [ ] Enforce permissions and ownership at the service/API boundaries.
- [ ] Implement APIs and serializers for approved use cases.
- [ ] Return consistent validation, authorization and conflict errors.
- [ ] Generate and validate OpenAPI documentation.
- [ ] Add API authorization, isolation and query-budget tests.

## 8. Phase F — Workflows and scheduled processing

- [ ] Implement new leave submission and substitute-consent paths.
- [ ] Implement CL/RH final decisions and higher-sanction routing.
- [ ] Implement immediate withdrawal while processing is pending.
- [ ] Implement approved-leave cancellation before leave starts.
- [ ] Implement ongoing EL/COL/VL extension with incremental-only posting.
- [ ] Implement resumption review and required attendance synchronization.
- [ ] Implement authorized offline-sanctioned leave recording.
- [ ] Implement year-end lapse, carry-forward and VL-to-EL conversion.
- [ ] Implement pending-only SLA reminders and escalations.
- [ ] Test retries, duplicate events and idempotency.

## 9. Phase G — Frontend and integration

- [ ] Confirm screens and navigation with the mentor.
- [ ] Implement employee application and history screens.
- [ ] Implement substitute response and approval work queues.
- [ ] Implement authorized administration and configuration screens.
- [ ] Implement balance, status and decision visibility.
- [ ] Add printable/exportable application support.
- [ ] Verify frontend permissions match the module registry.
- [ ] Test integration with IAM and approved platform contracts.

## 10. Phase H — Final verification

- [ ] Run domain and module tests.
- [ ] Run relevant integration and API tests.
- [ ] Check migrations and database constraints.
- [ ] Run permission-manifest validation.
- [ ] Validate OpenAPI output.
- [ ] Check import-layer rules and cross-module boundaries.
- [ ] Check query budgets and authorization isolation.
- [ ] Verify workflow paths against the authoritative workflow state-transition tables.
- [ ] Verify audit history and balance transactions.
- [ ] Verify year-end and SLA processing can safely retry.
- [ ] Obtain mentor review before activating the module.

## 11. Specification coverage

Use these specification versions as the baseline, subject to mentor confirmation:

- Problem Statement: v1.4
- Functional Requirements: v1.5
- Use-Case Specifications: v1.4
- Business-Rule Specifications: v1.4
- Traceability Matrix: v1.5
- Workflow Specifications: v1.6

### Traceability requirements

- [ ] Map each applicable functional requirement and business rule to its implementing component and verification test.
- [ ] Map each active use case to its workflow path, authorization checks and relevant tests.
- [ ] Verify workflow behavior against the authoritative state-transition tables, including valid and invalid transitions.
- [ ] Record the applicable specification ID and version in the traceability evidence.
- [ ] Identify retired requirements and use cases; do not implement them as active behavior unless the mentor approves a specification change.
- [ ] Cover category-specific entitlement, date counting, carry-forward, lapse and conversion rules.
- [ ] Cover substitute consent, approval routing, withdrawal, cancellation, extension, resumption and offline-sanctioned leave.
- [ ] Verify year-end processing, SLA reminders/escalations, audit history and retry/idempotency behavior.
- [ ] Record test results, uncovered requirements, exceptions and outstanding decisions.
- [ ] Review the completed traceability evidence with the mentor before module activation.

Implementation remains blocked until the mentor approves the blueprint. The workflow state-transition tables remain authoritative for workflow behavior.

## 12. Decisions and risks to resolve

### A. Decisions requiring mentor or module-owner confirmation

- [ ] Approve the ELM bounded context, module code and package name.
- [ ] Confirm the authoritative employee identity and organizational-unit references.
- [ ] Confirm ELM roles, permission grants and the configurable approval hierarchy.
- [ ] Confirm approved academic-calendar and attendance/resumption integration contracts.
- [ ] Confirm cross-module contracts, event schemas and notification ownership.
- [ ] Confirm year-end processing schedule, retry behavior, audit evidence and exception handling.
- [ ] Confirm frontend scope, navigation and module activation criteria.
- [ ] Record each decision, its owner, date and any specification impact.

### B. Repository investigation before implementation

- [ ] Inspect existing module registration, permission-manifest and import-layer patterns.
- [ ] Check which shared APIs, contracts, event infrastructure and scheduling facilities actually exist.
- [ ] Inspect the approved integration patterns for employee, organizational-unit, academic-calendar and attendance data.
- [ ] Identify required database-role grants, migration checks and test commands.
- [ ] Document findings and unresolved questions without adding application code.

### C. Implementation gate

- [ ] Keep application implementation, migrations and database changes blocked until the mentor approves the blueprint.
- [ ] Revisit this checklist after feedback and update the plan to reflect approved decisions.



## 13. Progress log

| Date | Phase | Change or verification | Result |
|---|---|---|---|
| 2026-10-27 | Preparation | Reviewed specifications and Fusion architecture | Completed |
| 2026-10-27 | Blueprint | Proposed module design | Awaiting mentor approval |
| | | | |
