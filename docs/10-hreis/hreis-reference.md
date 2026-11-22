# HR-EIS Module Reference Architecture (Module 10)

## Overview
The Human Resource - Employee Information System (HR-EIS) manages institutional employee service records, multi-tier leave lifecycles, annual faculty performance appraisals, LTC claims, CPDA claims, and workflow configuration.

- **Module Code:** `hreis` (IAM identifier `hr_eis`)
- **Module Number:** 10
- **Prefix:** `HR-`
- **Base Route:** `/hr`
- **API Base:** `/api/v1/hreis/`

---

## Directory Layout

### Backend (`modules/hreis/`)
- `domain/`: Pure-python business rules, state machines, and validators (zero Django ORM dependencies).
  - `leave.py`: Quota calculations and leave validation logic.
  - `appraisal.py`: Cycle window evaluation and score range constraints.
  - `claims.py`: Financial ceilings, travel block years, and settlement validation.
  - `workflow.py`: Authority traversal order and transition tables.
- `models/`: Django ORM models with audit immutability mixins.
  - `records.py`: `EmployeeServiceRecord` (profile, balances, history).
  - `leaves.py`: `LeaveRequest` (dates, type, status, history).
  - `appraisals.py`: `AppraisalSubmission` (academic year, review scores).
  - `claims.py`: `LtcRequest` and `CpdaRequest` (amounts, vouchers, settlement).
  - `audit.py`: `HrAuditLog` (append-only ledger) and `HrNotification`.
  - `workflow.py`: `WorkflowConfiguration` (institutional settings).
- `services/`: Transactional orchestrators (`@transaction.atomic`).
  - `service_records.py`: Profile maintenance and projection.
  - `leaves.py`: Submission and decision handling with balance deductions.
  - `appraisals.py`: Submission, reviewer assignment, multi-review, and finalization.
  - `claims.py`: LTC and CPDA lifecycle verification, approval, and settlement.
  - `workflow_config.py`: Institutional policy settings persistence.
  - `audit.py`: Append-only audit logger.
  - `notifications.py`: Event-driven in-app notifications.
- `selectors/`: Query scoping and isolation helpers.
- `api/`: REST views and serializers with permission guards.
- `schedule.py` & `tasks.py`: Celery scheduled jobs for reminders and deadlines.

### Frontend (`client/src/modules/hreis/`)
- `routes.tsx`: Lazy-loaded module routes with `RequirePermission` guards.
- `pages/`: Role-specific and common user-facing views:
  - `OverviewPage.tsx`: Dashboard with pending actions and metrics.
  - `ServiceRecordPage.tsx`: Personal service history and leave balances.
  - `LeavesPage.tsx`: Leave application form and status list.
  - `AppraisalsPage.tsx`: Annual appraisal form and submitted scores.
  - `LtcPage.tsx` & `CpdaPage.tsx`: Claim submission and status tracking.
  - `ApprovalsPage.tsx`: Multi-tier approval dashboard for HOD / Director.
  - `VerificationQueuePage.tsx`: HR Admin document verification queue.
  - `AppraisalAdminPage.tsx`: Reviewer assignment for HR Admin.
  - `SettlementQueuePage.tsx`: Accountant settlement and voucher entry.
  - `AdminSettingsPage.tsx`: Configurable approval hierarchies and windows.
  - `AuditLogsPage.tsx`: Compliance audit trail viewer.
  - `NotificationsPage.tsx`: Personal in-app alerts and reminders.

---

## Permission Catalog

| Permission Code | Description | Default Roles |
|---|---|---|
| `hr_eis.service_record.view_self` | View own service record | Employee, HOD, Director, HR Admin |
| `hr_eis.service_record.manage` | Create/update service records | HR Admin |
| `hr_eis.service_record.view_all` | View all employee records | HR Admin |
| `hr_eis.leave.apply` | Submit leave requests | Employee, HOD, Director |
| `hr_eis.leave.view_self` | View personal leaves | Employee, HOD, Director |
| `hr_eis.leave.review` | Review/approve leaves | HOD, Dean, Registrar, Director |
| `hr_eis.appraisal.submit` | Submit annual appraisal | Employee, Faculty |
| `hr_eis.appraisal.view_self` | View own appraisals | Employee, Faculty |
| `hr_eis.appraisal.assign_reviewer` | Assign reviewers | HR Admin |
| `hr_eis.appraisal.review` | Evaluate appraisal submission | Designated Reviewers (HOD, Dean) |
| `hr_eis.appraisal.finalize` | Finalize annual appraisal | Director, Registrar |
| `hr_eis.ltc.apply` | Submit LTC claim | Employee, Faculty |
| `hr_eis.ltc.view_self` | View own LTC claims | Employee, Faculty |
| `hr_eis.ltc.verify` | Verify LTC documents | HR Admin |
| `hr_eis.ltc.approve` | Approve LTC requests | HOD, Registrar, Director |
| `hr_eis.ltc.settle` | Settle LTC claim | Accountant |
| `hr_eis.cpda.apply` | Submit CPDA claim | Faculty |
| `hr_eis.cpda.view_self` | View own CPDA claims | Faculty |
| `hr_eis.cpda.verify` | Verify CPDA documents | HR Admin |
| `hr_eis.cpda.approve` | Approve CPDA requests | HOD, Director |
| `hr_eis.cpda.settle` | Settle CPDA claim | Accountant |
| `hr_eis.workflow.configure` | Configure module policies | HR Admin |
| `hr_eis.audit.view` | View immutable audit trail | HR Admin |
| `hr_eis.notification.view_self`| View personal alerts | All authenticated users |
