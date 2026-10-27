# Phase 2 — Single Broad Review and Improvement Prompt

This is a reconstructed task prompt based on the recorded Assignment 6 context, the existing Employee Leave Management implementation, and the final improvements. It is not a verified verbatim execution transcript and does not establish which model executed it. No intermediate prompt rounds are asserted.

**Model label:** gpt-oss-20b

**Original Phase 1 commit:** `c182f5cb4946006ef9c50ea62fb23a8e8decfca9`

**Recorded final Phase 2 commit:** `aec4c752d374908e88c9b093a5eb295b2a3140d5`

**Final Phase 2 diff:** 17 changed files; 1,827 added lines; 392 deleted lines.

**Phase 2 PR:** https://github.com/FusionIIIT/Fusion-Integrated/pull/382

## Prompt

```text
Continue improving the Employee Leave Management (ELM) implementation
developed in Assignment 6 Phase 1.

Work on the existing Fusion-Integrated codebase using the original
Phase 1 implementation as the starting point.

Read the supplied ELM specifications, business rules, workflow
definitions and traceability requirements. Inspect the existing
modules/leave implementation, application services, domain logic,
database models, API endpoints and relevant Fusion architecture.

The objective is to review, correct and improve the existing ELM
implementation rather than regenerate the module from scratch.

Preserve the existing modules/leave structure, application
registration, database integration, frontend routes and shared
Fusion infrastructure.

Focus on implementation correctness, security, validation,
workflow consistency, data integrity, error handling and
regression testing.

1. Review Existing Implementation

Perform a systematic review of the existing Employee Leave
Management implementation.

Identify incomplete business rules, invalid workflow transitions,
incorrect validation, authorization weaknesses, duplicate
operations, accounting inconsistencies and potential failures.

Inspect the leave application lifecycle, permissions, models,
database transactions, leave balances, year-end processing,
Celery tasks and REST API behavior.

Compare the implementation against the provided ELM workflow
specifications and relevant business rules.

Prioritize actionable defects affecting correctness, security
and data integrity.

Avoid rewriting stable components unnecessarily.

2. Improve Application and Approval Workflows

Review the application state machine and correct invalid or
incomplete workflow transitions.

Improve Unit Head recommendation handling and distinguish
recommendations from final approval or rejection decisions.

Ensure that the correct authority processes each workflow
transition according to the applicable leave category.

Validate sanction decisions and reject unsupported outcomes.

Review leave submission, substitute decisions, application
withdrawal, cancellation and extension workflows.

Prevent duplicate pending cancellation or extension requests
for the same approved leave application.

Reject conflicting application actions and ensure workflow
state changes are performed atomically.

Use row-level locking where necessary to prevent concurrent
requests from creating inconsistent application states.

3. Strengthen Leave Validation and Day Counting

Review leave-date validation and calculation rules for each
supported leave category.

Ensure that start dates, end dates and leave categories are
validated consistently.

Reject reversed date ranges and unsupported leave types.

Handle working days, weekends and holidays according to the
relevant category rules.

Validate half-day leave requests and prevent invalid half-day
combinations.

Ensure that categories requiring chargeable working days
do not accept zero-day leave periods.

Propagate domain validation errors through the existing
API validation mechanisms rather than exposing unexpected
server errors.

4. Correct Resumption and Leave Accounting

Review the implementation of employee resumption after
approved leave.

Support early and late resumption by comparing the actual
resumption date with the approved leave period.

Reconcile leave balance adjustments when the actual leave
duration differs from the originally approved duration.

Ensure that the appropriate accounting transaction is
recorded for a valid adjustment.

Prevent repeated review of an already processed resumption
record and avoid duplicate leave balance modifications.

Reject invalid future resumption dates.

Handle synchronization with attendance-related systems
without incorrectly reporting a successful synchronization
when an external operation fails.

Strengthen ledger transaction idempotency so that the same
source key cannot silently represent conflicting postings.

Preserve financial and leave balance consistency during
repeated or concurrent operations.

5. Improve Administrative and Year-End Processing

Review policy management, authority routing, leave accounting,
administrative corrections and year-end processing.

Improve validation of employee eligibility, leave category
rules and applicable policy configuration.

Check that year-end carry-forward and leave conversion rules
are applied only to eligible employees and categories.

Handle invalid balances, duplicate employee identities and
inconsistent policy data safely.

Prevent duplicate year-end ledger postings.

Ensure that repeated processing cannot silently create
conflicting transactions.

Review scheduled tasks and SLA processing for consistency
with the existing application architecture.

Use appropriate transaction boundaries and error handling
for operations that modify persistent records.

6. Review API Permissions and Data Isolation

Inspect the ELM REST API endpoints and permission handling.

Verify that application creation, viewing, review, approval,
cancellation, extension, resumption and administrative actions
require the appropriate Fusion permissions.

Respect existing module grants and the Principal-based
authentication model.

Ensure that users cannot perform unauthorized actions or
access another employee's private leave information.

Review API response handling and validation errors.

Preserve the existing Fusion authentication and IAM
infrastructure instead of introducing duplicate mechanisms.

7. Add Regression Tests

Create focused automated tests for the corrected functionality.

Cover important successful and failing cases involving:
- Leave application authorization and permissions
- Application lifecycle state transitions
- Unit Head recommendation and sanction decisions
- Duplicate cancellation and extension prevention
- Invalid workflow actions
- Leave category and day-counting validation
- Early and late resumption
- Duplicate resumption processing
- Leave balance adjustments
- Ledger transaction idempotency
- Year-end processing safeguards

Include tests for invalid input, unauthorized requests,
duplicate operations and data integrity failures.

Keep tests within the existing modules/leave test structure.

Avoid relying exclusively on successful-path tests.

8. Review Database and Integration Changes

Inspect the existing ELM models and database schema for
inconsistencies affecting the corrected workflows.

Create any necessary database migrations while preserving
existing application data and migration history.

Review the resumption state representation and ensure the
database field supports the required workflow status values.

Maintain consistency between models, service operations,
API serializers and workflow logic.

Preserve the module's existing integration with Fusion,
including routing, permissions, database configuration
and Celery scheduling.

Do not introduce a separate ELM module or duplicate the
existing implementation.

9. Static Analysis and Verification

Perform static analysis and code review on the resulting
changes.

Check Python syntax, formatting, lint warnings, unused
imports, invalid references and architectural consistency.

Review security boundaries, transaction handling,
authorization and error propagation.

Where execution is available and authorized, run focused
regression tests and relevant integration checks.

Verify database migration consistency and application
startup where possible.

Inspect the final changes for unintended modifications,
unnecessary complexity and unrelated files.

Correct defects discovered during review.

Report which checks actually passed, which failed and
which could not be executed.

Do not claim unperformed tests or complete production
integration where evidence is unavailable.

10. Finalize the Improved Implementation

Keep all improvements within the existing Fusion
Employee Leave Management module.

Preserve the original Phase 1 implementation history.

Prepare a consolidated set of improvements covering
workflow correctness, validation, leave accounting,
administrative operations, permission handling and
regression coverage.

Document the actual changes and known limitations.

Avoid unrelated frontend rewrites, unnecessary new
modules and changes outside the approved scope.
```

## Recorded Implementation Output

The final Phase 2 commit includes:

- Improved leave workflow transitions and Unit Head recommendation handling.
- Stronger cancellation, extension and sanction validation.
- Additional leave-day and half-day validation safeguards.
- Early and late resumption reconciliation with leave balance adjustments.
- Duplicate resumption processing and ledger posting protection.
- Improved year-end processing and eligibility safeguards.
- Strengthened application authorization and API validation.
- Database migration for resumption state handling.
- Additional regression tests for permissions, workflows, recommendations, resumptions, accounting and year-end safeguards.
- Python lint and formatting corrections.

## Recorded Changed Files

**Modified files:**

- `config/celery.py`
- `modules/leave/api/views.py`
- `modules/leave/domain/counting.py`
- `modules/leave/domain/workflow.py`
- `modules/leave/models.py`
- `modules/leave/services/accounts.py`
- `modules/leave/services/administration.py`
- `modules/leave/services/applications.py`
- `modules/leave/services/sla.py`
- `modules/leave/services/year_end.py`
- `modules/leave/tasks.py`

**New files:**

- `modules/leave/migrations/0002_resumption_state_length.py`
- `modules/leave/tests/test_api_permissions.py`
- `modules/leave/tests/test_lifecycle.py`
- `modules/leave/tests/test_ported_safeguards.py`
- `modules/leave/tests/test_recommendation.py`
- `modules/leave/tests/test_resumption.py`

## Implementation Evidence

**Original Phase 1 commit:** `c182f5cb4946006ef9c50ea62fb23a8e8decfca9`

**Final Phase 2 commit:** `aec4c752d374908e88c9b093a5eb295b2a3140d5`

**Pull Request:** https://github.com/FusionIIIT/Fusion-Integrated/pull/382

**Recorded Phase 2 changes:** 17 files, 1,827 additions, 392 deletions.
