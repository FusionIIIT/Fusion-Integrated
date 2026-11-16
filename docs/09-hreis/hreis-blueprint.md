# HR-EIS pilot module blueprint

## Source baseline

This module is based on the synchronized Human Resource (Employee Information System) specification package: problem statement v1.2, requirements registry (14 CFRs and 107 AFRs) v1.3, use cases v1.3, business rules v1.3, workflow specifications v1.3 and traceability matrix v1.3. The specification folder is maintained separately from the platform repository.

This is an initial integration pilot, **not a claim of full AFR or production readiness**.

## Module boundaries

- Module code: `hreis`; Django application: `modules.hreis`; routes: `/api/v1/hreis/`; client: `/hreis`.
- Fusion IAM owns accounts, authentication, role assignments and permissions. HR-EIS stores only IAM integer user IDs as references, never passwords or an independent user table.
- HR-EIS owns its service-record, leave, appraisal, LTC/CPDA claim, workflow configuration, notification and audit tables. Cross-module access is through `contracts.py` and does not use foreign keys into other modules.
- RBAC permissions are declared in the module registry and published in the generated permission manifest. Active role strings must be confirmed with the institutional IAM administrator before demonstrating approvals.

## Pilot workflows

| Domain | Supported transitions | Specification anchor |
|---|---|---|
| Service records | HR admin create/update; employee view own record | HR-UC-001/002, BR-HR-003 through BR-HR-006 |
| Leave | Apply after balance/route checks; active authority approve/reject/forward; approval deducts balance atomically | HR-UC-003/004, CW-HR-01, BR-HR-007 through BR-HR-011 |
| Appraisal | Submit in configured window; HR assigns reviewer sequence; authority reviews; final step closes | HR-UC-006/007/008, CW-HR-02, BR-HR-012 through BR-HR-015 |
| LTC and CPDA | Advance/reimbursement request, HR verification, authority decision and accountant status recording | HR-UC-009 through HR-UC-016, CW-HR-03/04, BR-HR-016 through BR-HR-023 |
| Administration | Configure separate faculty/staff approval routes and appraisal windows | HR-UC-017, BR-HR-009/023 |
| Audit and notifications | Record HR actions with actor/time, expose role-restricted audit history and own notifications | HR-UC-018/019, BR-HR-024 through BR-HR-026 |

New leave and claim submissions preserve an ordered copy of their approval roles, so changing an HR configuration cannot silently redirect an in-progress request. Missing route configuration fails closed instead of inventing institute policy. Self-service read/query endpoints derive the employee identity from the Fusion session, never an ID supplied by the client.

## Important outstanding integration/policy work

- Exact institutional approval matrices, eligibility rules, appraisal review ordering and leave balance policy require confirmed institution configuration. The app does not infer these from employee category alone.
- LTC prescribed-form templates, actual document upload/storage and external document authentication remain outside this pilot; existing document references can be recorded.
- Dashboard/email delivery, periodic reminders, policy update fan-out and live real-time payroll/finance synchronization are not connected. HR-EIS records internal notifications and externally supplied settlement status/reference only; it does not initiate disbursements.
- Role names and module slug `hreis` should be confirmed with the assigned faculty/mentor before PR review. The role names currently modeled are Employee, HOD, Registrar, Director, HR Administrator and Accountant.
- This pilot has not been demonstrated against a clean IAM/database fixture or exhaustively traced against every AFR. Final rollout requires that validation.

## Setup notes

After restoring the standard Fusion environment, apply the new HR-EIS migrations, seed the module and run the platform's permission manifest generator before provisioning roles in IAM. For basic structure checks run `python manage.py check`, the local policy tests, the repository import checker, and the navigation-to-route checker. The backend intentionally contains no HR-EIS-level login or IAM role administration.
