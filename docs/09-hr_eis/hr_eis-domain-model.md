# HR-EIS domain model

This document describes the current HR-EIS data model. It records implementation behavior and does not define institutional leave policy.

## Leave records

| Record | Relationship and invariant | Purpose |
|---|---|---|
| `EmployeeRecord` | One employee record may have one balance per supported leave type. | Employee category, department, and identity scope used to select the leave route. |
| `LeaveBalance` | Unique by employee and leave type; `available_days` cannot be negative. | HR-maintained available days and eligibility for a supported type. |
| `WorkflowRoute` | Unique by employee category and request type. | Configured approval authorities; leave routes allow one or two steps. |
| `LeaveRequest` | Belongs to an employee; retains the configured route snapshot and current authority. | Submitted type, duration, justification, status, and workflow position. |
| `LeaveLedgerEntry` | References a balance and optionally a request; update and delete are refused in application code and by a database trigger. | Append-only balance configuration, adjustment, and approved-leave entries. |

The six leave types are Casual, Restricted, Medical, Earned, Vacation, and Sabbatical. Eligibility and balances are configured by an authorized HR officer; this module does not calculate entitlements or accrual.

## Balance changes

HR configuration writes a ledger entry for each balance adjustment. Approval locks the request and balance in one transaction, checks current eligibility and funds, deducts the approved duration, and records the deduction. Rejection does not deduct days. A request cannot be decided by its submitter, by an actor without the approval permission, or by someone other than its current assigned authority.
