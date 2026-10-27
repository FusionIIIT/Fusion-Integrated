# Phase 1 — Single Broad Implementation Prompt

This is a reconstructed task prompt based on the recorded Assignment 6 context, ELM specifications, and final implementation. It is not a verified verbatim execution transcript and does not establish which model executed it. No intermediate prompt rounds are asserted.

**Model label:** gpt-oss-20b

**Recorded final commit:** `c182f5cb4946006ef9c50ea62fb23a8e8decfca9`

**Final diff:** 45 changed files; 5,060 added lines; 7 deleted lines.

**Original PR:** https://github.com/FusionIIIT/Fusion-Integrated/pull/91

## Prompt

```text
Work on the provided Fusion-Integrated ERP repository using the
Assignment 6 instructions and the complete Employee Leave Management
(ELM) specification package.

Read the problem statement, functional requirements, business rules,
use cases, workflow specifications, traceability matrix, and relevant
Fusion architecture documentation before implementing the module.

Inspect the existing repository, including its Django backend,
reference modules, IAM authentication and permission system,
database configuration, frontend components, module registration,
routing, and background-task infrastructure.

Implement Employee Leave Management as an integrated Fusion module,
not as an independent application.

1. Backend Models and Domain Rules

Create the modules/leave application using the existing Django
architecture.

Support the following leave categories:
- Casual Leave (CL)
- Restricted Holiday (RH)
- Special Casual Leave (SCL)
- Earned Leave (EL)
- Compensatory Leave (COL)
- Vacation Leave (VL)

Implement appropriate models for leave applications, employee
balances, accounting transactions, leave policies, authority
routing, holiday calendars, workflow records, notifications,
and resumption records.

Implement leave-day counting and workflow state transitions
according to the supplied ELM specifications.

Generate the required database migrations.

2. Application and Approval Workflows

Implement employee leave submission with validation of dates,
leave policies, available balances, overlapping requests,
and substitute requirements.

Support substitute acceptance or rejection, Unit Head review,
Establishment routing, final sanction decisions, and Director
self-sanction where applicable.

Implement application withdrawal, approved-leave cancellation,
leave extension, and employee resumption workflows.

Keep workflow transitions consistent with the specification
and enforce authorization for each operation.

3. Accounting and Administrative Operations

Implement leave balance management and accounting transactions.

Provide administrative functions for leave policies, authority
routes, holiday calendars, offline leave recording, record
corrections, and SLA configuration.

Implement year-end leave processing according to the relevant
business rules.

Use the existing Celery infrastructure for scheduled year-end
processing, SLA checks, notification delivery, and resumption
synchronization.

4. REST API Integration

Create Django REST Framework serializers, views, and URL routes
for the leave module.

Expose endpoints for leave applications, employee balances,
workflow actions, assigned tasks, cancellations, extensions,
resumptions, and administrative operations.

Integrate these endpoints with Fusion's existing authentication,
Principal/IAM interfaces, and permission checks.

Prevent unauthorized access to employee records and ensure
state-changing operations use the appropriate service logic.

5. Frontend Implementation

Integrate Employee Leave Management into Fusion's existing
React and TypeScript frontend.

Register the module using the shared client registry and
lazy-loaded routes.

Implement pages for:
- Applying for leave
- Viewing personal leave applications
- Checking leave balances
- Handling assigned workflow tasks
- Recording and reviewing resumptions
- Managing administrative settings

Create reusable TypeScript API types and hooks using the
existing authenticated HTTP client and TanStack Query.

Provide appropriate loading states, error handling,
form validation, and updates after successful actions.

Reuse existing UI components and navigation conventions.

6. Permissions and System Integration

Register ELM permissions and module contracts using the
existing Fusion mechanisms.

Synchronize the generated permission manifest and catalogue.

Update the OpenAPI specification for the ELM endpoints,
request bodies, responses, and schemas.

Update import-layer contracts so the Leave module follows
the established architecture.

Do not create a duplicate login system, independent IAM
implementation, or unnecessary parallel infrastructure.

7. Verification and Limitations

Review the implementation for consistency with the supplied
ELM specifications and existing Fusion architecture.

Where possible, check:
- Django application initialization and configuration
- Database migrations and model consistency
- Application submission and workflow transitions
- Permissions and employee-data isolation
- Leave balance and accounting operations
- Cancellation, extension, and resumption behavior
- Administrative and year-end operations
- Frontend TypeScript compatibility and production build
- REST API and OpenAPI synchronization
- Import-layer and module registration rules

Resolve identified implementation and integration errors.

Clearly distinguish completed functionality from incomplete
features or unavailable external integrations.

Report which checks actually passed, which failed,
and which could not be executed.

Do not invent institutional policy details, expose credentials,
or claim tests were performed when no test evidence exists.
```

## Recorded Implementation Output

The final commit contains:

- Django leave module, models, domain rules, and initial migration.
- Leave application, cancellation, extension, and resumption workflows.
- Accounting, administration, year-end, SLA, and notification services.
- REST API serializers, endpoints, and routing.
- IAM permission declarations and module contracts.
- React/TypeScript leave pages, API hooks, and routes.
- Celery configuration and background tasks.
- OpenAPI updates, architecture contracts, and an implementation blueprint.

## Implementation Evidence

**Commit:** `c182f5cb4946006ef9c50ea62fb23a8e8decfca9`

**Pull Request:** https://github.com/FusionIIIT/Fusion-Integrated/pull/91

**Recorded changes:** 45 files, 5,060 additions, 7 deletions.
