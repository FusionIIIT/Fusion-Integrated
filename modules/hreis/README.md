# HR employee information backend

Backend APIs for employee service records, configured leave requests and LTC/CPDA claims. This module starts from Fusion's base application and is independent of the Employee Leave Management trial. It supplies no frontend.

## Scope

- HR administrators maintain employee appointment/category/department/designation, service history and retirement state. Employees read their own records.
- Administrators configure supported HR leave categories, category eligibility, account balances and ordered approval routes. No institutional entitlement values or authority hierarchy are silently hardcoded.
- Employees submit their own leave requests or documented LTC/CPDA advance/reimbursement claims. Request ownership, route, stage and status are server controlled.
- Leave submission validates dates, category eligibility, overlap and balance including outstanding reservations. Only the currently assigned authority can advance a request; approval is final only at the last configured step and debits the account once.
- Financial claims require HR verification before approval routing. An accountant records an external settlement reference only after approval. The module does not execute payments or modify payroll rules.
- Mutations create audit events. Audit endpoints are read-only; notifications are persisted for the owning employee. External email/dashboard delivery is not implemented.

## API

Mounted under `/api/v1/hreis/`:

| Resource | Operations |
| --- | --- |
| `employees/` | List/retrieve; authorized HR create/update |
| `policies/`, `accounts/`, `routes/` | Scoped reads; authorized configuration create/update |
| `requests/` | List/retrieve/submit; no generic update/delete |
| `requests/{id}/verify/` | HR verification for financial claims |
| `requests/{id}/decide/` | `APPROVE`, `REJECT` or `FORWARD`, with optional note |
| `requests/{id}/settle/` | Record external settlement reference |
| `audit/` | Authorized read-only audit history |
| `notifications/` | Current employee's stored notification events |

Authentication uses Fusion's existing IAM Principal. Every endpoint requires the `hreis` module grant and its action permission. `registry.py` declares permissions and role grants; IAM operators must map the institutional designation names and sync the manifest. This backend intentionally publishes no navigation entries for screens that do not exist.

Before submitting requests, HR must create an employee record, active leave policy with eligible categories, account balance and appropriate workflow route. Routes contain explicit ordered external authority user IDs and may be department-specific or category-wide. Missing configuration fails closed. Financial claim routes are resolved when HR verifies the claim; leave routes are snapshotted at submission.

## Partial implementation limits

Yearly appraisals, reviewer assignment and archival are not implemented. Institutional leave counting/holiday/eligibility rules are not fully modeled: this initial backend uses inclusive calendar-day leave duration and explicitly configured balances/category eligibility. Entitlements, annual crediting and policy-specific calculations require further work. Evidence documents are reference strings, not an uploaded-file management service. Reminder/deadline notification processing and real-time payroll/finance/identity synchronization are not implemented. Stored notifications require a delivery integration. Live IAM integration and deployed end-to-end operation have not been demonstrated.

Audit immutability is enforced by the read-only API and instance-level model guards; it is not claimed as database-level tamper protection against privileged SQL or bulk ORM writes. Review, deployment configuration and broader workflow/concurrency verification remain necessary before production use. This is a coherent partial backend, not full specification coverage.
