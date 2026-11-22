# Module Blueprint — Human Resource - Employee Information System (HR-EIS)

## §0 — Module Metadata

- **Module Name**: Human Resource - Employee Information System (HR-EIS)
- **Module Code**: `hreis`
- **Specification ID Prefixes**: `HR-CFR-`, `HR-AFR-`, `HR-UC-`, `BR-HR-`, `BW-HR-`, `CW-HR-`
- **Environment**: `module-only`
- **Specification Source**: Module 10 Synchronized Specification Package v1.3_FINAL

---

## §1 — Step 3.1: Traceability Table

| Requirement / Spec ID | Description | Domain Component | Django Model | Service / Selector | API Endpoint | Frontend Screen | Test Case |
|---|---|---|---|---|---|---|---|
| **HR-CFR-001** (HR-AFR-001, 094–101) | RBAC Enforcement & Data Access Security | `domain.authz` | All Models (user scoping) | `selectors.scoping` | All Endpoints (DRF permission classes) | Shell / Nav Guards | `test_privilege_escalation.py` |
| **HR-CFR-002** (HR-AFR-002, 004) | Employee Request Self-Service & Status Tracking | `domain.requests` | `LeaveRequest`, `AppraisalSubmission`, `LtcRequest`, `CpdaRequest` | `services.requests`, `selectors.requests` | `/api/v1/hreis/my-requests/` | `OverviewPage`, `LeavesPage`, `LtcPage`, `CpdaPage` | `test_employee_self_service.py` |
| **HR-CFR-003** (HR-AFR-006–009, 070–076, 106) | Approval Authority Routing & Order Integrity | `domain.workflow` | `LeaveRequest`, `LtcRequest`, `CpdaRequest` (`approval_history`) | `services.workflow` | `/api/v1/hreis/approvals/`, `/decide/` | `ApprovalsPage` | `test_approval_workflow.py` |
| **HR-CFR-004** (HR-AFR-010–014) | HR Administrator Operational Capabilities | `domain.admin` | `EmployeeServiceRecord`, `WorkflowConfiguration`, `HrAuditLog` | `services.service_records`, `services.workflow_config` | `/api/v1/hreis/service-records/`, `/verification/`, `/workflows/` | `AdminSettingsPage`, `VerificationQueuePage` | `test_admin_capabilities.py` |
| **HR-CFR-005** (HR-AFR-015–018) | Accountant Claim Processing & Financial Settlement | `domain.finance` | `LtcRequest`, `CpdaRequest` (`payment_status`, `disbursement_details`) | `services.settlement` | `/api/v1/hreis/settlement/`, `/settle/` | `SettlementQueuePage` | `test_finance_settlement.py` |
| **HR-CFR-006** (HR-AFR-003, 019–028, 102–103, 107) | Centralized Service Record Management & Read-Only Access | `domain.service_record` | `EmployeeServiceRecord` | `services.service_records`, `selectors.service_records` | `/api/v1/hreis/service-records/me/`, `/service-records/` | `ServiceRecordPage`, `AdminSettingsPage` | `test_service_record.py` |
| **HR-CFR-007** (HR-AFR-029–043) | Leave Management Lifecycle (Casual, Restricted, Medical, Earned, Vacation, Sabbatical) | `domain.leave` | `LeaveRequest`, `EmployeeServiceRecord` | `services.leaves`, `selectors.leaves` | `/api/v1/hreis/leaves/`, `/leaves/<id>/decide/` | `LeavesPage` | `test_leave_lifecycle.py` |
| **HR-CFR-008** (HR-AFR-044–049) | Yearly Appraisal Lifecycle & Reviewer Assignment | `domain.appraisal` | `AppraisalSubmission` | `services.appraisals`, `selectors.appraisals` | `/api/v1/hreis/appraisals/`, `/review/`, `/finalize/` | `AppraisalsPage`, `AppraisalAdminPage` | `test_appraisal_lifecycle.py` |
| **HR-CFR-009** (HR-AFR-050–059) | LTC Lifecycle (Advance & Reimbursement) | `domain.ltc` | `LtcRequest` | `services.ltc`, `selectors.ltc` | `/api/v1/hreis/ltc/`, `/verify/`, `/decide/`, `/settle/` | `LtcPage`, `VerificationQueuePage`, `SettlementQueuePage` | `test_ltc_lifecycle.py` |
| **HR-CFR-010** (HR-AFR-060–069) | CPDA Lifecycle (Advance & Reimbursement) | `domain.cpda` | `CpdaRequest`, `EmployeeServiceRecord` | `services.cpda`, `selectors.cpda` | `/api/v1/hreis/cpda/`, `/verify/`, `/decide/`, `/settle/` | `CpdaPage`, `VerificationQueuePage`, `SettlementQueuePage` | `test_cpda_lifecycle.py` |
| **HR-CFR-011** (HR-AFR-005, 077–082) | Notifications (Submission, Approval, Reminders, Policy) | `domain.notifications` | `HrNotification` | `services.notifications`, `selectors.notifications` | `/api/v1/hreis/notifications/` | `NotificationsPage`, `OverviewPage` | `test_notifications.py` |
| **HR-CFR-012** (HR-AFR-083–089) | Immutable Audit Trail & Compliance Evidence | `domain.audit` | `HrAuditLog` | `services.audit`, `selectors.audit` | `/api/v1/hreis/audit-logs/` | `AuditLogsPage` | `test_audit_logging.py` |
| **HR-CFR-013** (HR-AFR-090–093) | External Systems Integration Boundary (Payroll & Finance) | `domain.integration` | `LtcRequest`, `CpdaRequest` (status synchronization) | `services.integration` | `/api/v1/hreis/integration/status/` | `SettlementQueuePage` | `test_integration.py` |
| **HR-CFR-014** (HR-AFR-104–105) | Payroll & Salary Scope Boundary Enforcement | `domain.invariants` | None (boundary check) | None (explicit non-modification rule) | None | None | `test_scope_boundaries.py` |

---

## §2 — Step 3.2: Domain Model

```
+-------------------------------------------------------------+
|                   EmployeeServiceRecord                     |
| - user_id: int (unique, indexed)                            |
| - employee_id: str                                          |
| - department: str                                           |
| - designation: str                                          |
| - category: str (faculty | staff)                           |
| - appointment_date: date                                    |
| - retirement_date: date                                     |
| - retirement_status: str (active | retired | resigned)       |
| - service_history: list[dict]                               |
| - leave_balances: dict[str, float]                          |
| - cpda_balance: Decimal                                     |
| - ltc_eligible_block: str                                   |
| - is_active: bool                                           |
+-------------------------------------------------------------+
                               | 1
                               | owns
        +----------------------+-----------------------+
        |                      |                       |
+------------------+   +-------------------+   +------------------+
|   LeaveRequest   |   |   AppraisalSub    |   |    LtcRequest    |
| - user_id: int   |   | - user_id: int    |   | - user_id: int   |
| - leave_type     |   | - academic_year   |   | - request_type   |
| - start/end_date |   | - status          |   | - block_year     |
| - duration_days  |   | - content: dict   |   | - amount / pass  |
| - justification  |   | - reviewers: list |   | - doc_links: list|
| - status         |   | - score / remarks |   | - verif_status   |
| - approval_hist  |   | - is_immutable    |   | - payment_status |
+------------------+   +-------------------+   +------------------+
                               |
                               +-----------------------+
                                                       |
                                               +------------------+
                                               |   CpdaRequest    |
                                               | - user_id: int   |
                                               | - request_type   |
                                               | - purpose: str   |
                                               | - amount: Decimal|
                                               | - doc_links: list|
                                               | - verif_status   |
                                               | - disb_status    |
                                               | - disb_details   |
                                               +------------------+
```

---

## §3 — Step 3.3: State Machines

### 1. Leave Request State Machine (`CW-HR-01`)
- **SUBMITTED** (Initial): Balances checked against quota (BR-HR-008). Deducts provisional balance.
- **FORWARDED**: Intermediate authority (e.g. HOD forwards to Director for faculty sabbatical/extended leave).
- **APPROVED**: Final authority decision (HOD / Registrar / Director). Deducts leave balance permanently. Permanent audit log written.
- **REJECTED**: Terminal state. Restores provisional balance. Full audit trail recorded.

### 2. Yearly Appraisal State Machine (`CW-HR-02`)
- **DRAFT**: Employee prepares form within submission window (BR-HR-012).
- **SUBMITTED**: Submitted during window; locked against employee modifications.
- **UNDER_REVIEW**: Assigned reviewers (BR-HR-013) evaluate and record recommendations.
- **FINALIZED**: Reviewing/Approving Authority commits final score and remarks. Record marked immutable (`is_immutable=True`) and archived in service record (BR-HR-015).

### 3. LTC Request State Machine (`CW-HR-03`)
- **SUBMITTED**: Employee submits Advance or Reimbursement form.
- **VERIFIED**: HR Administrator verifies documentation and eligibility (BR-HR-017).
- **FORWARDED / PENDING_APPROVAL**: Enters approval hierarchy based on category (HOD -> Director / Registrar).
- **APPROVED**: Authority approves claim.
- **SETTLED**: Accountant verifies financial correctness and records payment reference (disbursed/paid) (BR-HR-018, BR-HR-035).

### 4. CPDA Request State Machine (`CW-HR-04`)
- **SUBMITTED**: Employee submits claim with purpose, amount, and supporting documents (BR-HR-020).
- **VERIFIED**: HR Administrator verifies eligibility and claim documentation (BR-HR-021).
- **APPROVED / FORWARDED**: Approving authority sanctions claim.
- **SETTLED / DISBURSED**: Accountant verifies financial correctness and records disbursement voucher details (BR-HR-022, BR-HR-035).

---

## §4 — Step 3.4: Permission List & Role Grants

### Permissions
1. `hr_eis.service_record.view_self` — View own service record
2. `hr_eis.service_record.manage` — Create and update service records (HR Admin)
3. `hr_eis.service_record.view_all` — View all employee service records (HR Admin)
4. `hr_eis.leave.apply` — Submit leave application (Employee)
5. `hr_eis.leave.view_self` — View own leave applications
6. `hr_eis.leave.review` — Approve, reject, or forward leaves (HOD, Registrar, Director)
7. `hr_eis.appraisal.submit` — Submit annual appraisal (Employee)
8. `hr_eis.appraisal.view_self` — View own appraisals
9. `hr_eis.appraisal.assign_reviewer` — Assign appraisal reviewers (HR Admin)
10. `hr_eis.appraisal.review` — Review and add appraisal feedback (Reviewer, HOD, Director)
11. `hr_eis.appraisal.finalize` — Finalize appraisal (Director, Registrar)
12. `hr_eis.ltc.apply` — Submit LTC requests (Employee)
13. `hr_eis.ltc.view_self` — View own LTC requests
14. `hr_eis.ltc.verify` — Verify LTC eligibility & documents (HR Admin)
15. `hr_eis.ltc.approve` — Approve or forward LTC requests (Approver)
16. `hr_eis.ltc.settle` — Record settlement and payment status (Accountant)
17. `hr_eis.cpda.apply` — Submit CPDA requests (Employee)
18. `hr_eis.cpda.view_self` — View own CPDA requests
19. `hr_eis.cpda.verify` — Verify CPDA claim (HR Admin)
20. `hr_eis.cpda.approve` — Approve CPDA requests (Approver)
21. `hr_eis.cpda.settle` — Record CPDA disbursement (Accountant)
22. `hr_eis.workflow.configure` — Configure submission windows and quotas (HR Admin)
23. `hr_eis.audit.view` — Review compliance and immutable audit logs (HR Admin)
24. `hr_eis.notification.view_self` — Receive and view system notifications

### Role Grants
- `faculty`:
  - `hr_eis.service_record.view_self`
  - `hr_eis.leave.apply`, `hr_eis.leave.view_self`
  - `hr_eis.appraisal.submit`, `hr_eis.appraisal.view_self`
  - `hr_eis.ltc.apply`, `hr_eis.ltc.view_self`
  - `hr_eis.cpda.apply`, `hr_eis.cpda.view_self`
  - `hr_eis.notification.view_self`
- `staff`:
  - `hr_eis.service_record.view_self`
  - `hr_eis.leave.apply`, `hr_eis.leave.view_self`
  - `hr_eis.appraisal.submit`, `hr_eis.appraisal.view_self`
  - `hr_eis.ltc.apply`, `hr_eis.ltc.view_self`
  - `hr_eis.cpda.apply`, `hr_eis.cpda.view_self`
  - `hr_eis.notification.view_self`
- `hod`:
  - Faculty grants + `hr_eis.leave.review`, `hr_eis.appraisal.review`, `hr_eis.ltc.approve`, `hr_eis.cpda.approve`
- `registrar`:
  - Staff grants + `hr_eis.leave.review`, `hr_eis.appraisal.review`, `hr_eis.appraisal.finalize`, `hr_eis.ltc.approve`, `hr_eis.cpda.approve`
- `director`:
  - Faculty grants + `hr_eis.leave.review`, `hr_eis.appraisal.review`, `hr_eis.appraisal.finalize`, `hr_eis.ltc.approve`, `hr_eis.cpda.approve`
- `hr_admin`:
  - `hr_eis.service_record.view_self`, `hr_eis.service_record.manage`, `hr_eis.service_record.view_all`
  - `hr_eis.appraisal.assign_reviewer`
  - `hr_eis.ltc.verify`
  - `hr_eis.cpda.verify`
  - `hr_eis.workflow.configure`
  - `hr_eis.audit.view`
  - `hr_eis.notification.view_self`
- `accountant`:
  - `hr_eis.service_record.view_self`
  - `hr_eis.ltc.settle`
  - `hr_eis.cpda.settle`
  - `hr_eis.notification.view_self`

---

## §5 — Step 3.5: Endpoint List

| Method | Path | Description | Required Permission |
|---|---|---|---|
| `GET` | `/api/v1/hreis/service-records/me/` | Get current user's service record | `hr_eis.service_record.view_self` |
| `GET` | `/api/v1/hreis/service-records/` | List all service records (HR Admin) | `hr_eis.service_record.view_all` |
| `POST` | `/api/v1/hreis/service-records/` | Create new employee service record | `hr_eis.service_record.manage` |
| `PATCH` | `/api/v1/hreis/service-records/<id>/` | Update employee service record | `hr_eis.service_record.manage` |
| `GET` | `/api/v1/hreis/leaves/` | List leaves (scoping: self or assigned for review) | `hr_eis.leave.view_self` or `.review` |
| `POST` | `/api/v1/hreis/leaves/` | Submit leave request | `hr_eis.leave.apply` |
| `GET` | `/api/v1/hreis/leaves/<id>/` | Leave request detail | `hr_eis.leave.view_self` or `.review` |
| `POST` | `/api/v1/hreis/leaves/<id>/decide/` | Approve, reject, or forward leave | `hr_eis.leave.review` |
| `GET` | `/api/v1/hreis/appraisals/` | List appraisals (scoping: self or reviewable) | `hr_eis.appraisal.view_self` or `.review` |
| `POST` | `/api/v1/hreis/appraisals/` | Submit appraisal form | `hr_eis.appraisal.submit` |
| `GET` | `/api/v1/hreis/appraisals/<id>/` | Appraisal detail | `hr_eis.appraisal.view_self` or `.review` |
| `POST` | `/api/v1/hreis/appraisals/<id>/assign-reviewers/` | Assign reviewers to appraisal | `hr_eis.appraisal.assign_reviewer` |
| `POST` | `/api/v1/hreis/appraisals/<id>/review/` | Submit reviewer feedback | `hr_eis.appraisal.review` |
| `POST` | `/api/v1/hreis/appraisals/<id>/finalize/` | Finalize and archive appraisal | `hr_eis.appraisal.finalize` |
| `GET` | `/api/v1/hreis/ltc/` | List LTC claims (scoping) | `hr_eis.ltc.view_self`, `.verify`, `.approve`, `.settle` |
| `POST` | `/api/v1/hreis/ltc/` | Submit LTC Advance or Reimbursement | `hr_eis.ltc.apply` |
| `GET` | `/api/v1/hreis/ltc/<id>/` | LTC claim detail | `hr_eis.ltc.view_self`, etc. |
| `POST` | `/api/v1/hreis/ltc/<id>/verify/` | HR Admin verify LTC claim | `hr_eis.ltc.verify` |
| `POST` | `/api/v1/hreis/ltc/<id>/decide/` | Approver decide on LTC claim | `hr_eis.ltc.approve` |
| `POST` | `/api/v1/hreis/ltc/<id>/settle/` | Accountant record payment status | `hr_eis.ltc.settle` |
| `GET` | `/api/v1/hreis/cpda/` | List CPDA claims (scoping) | `hr_eis.cpda.view_self`, `.verify`, `.approve`, `.settle` |
| `POST` | `/api/v1/hreis/cpda/` | Submit CPDA Advance or Reimbursement | `hr_eis.cpda.apply` |
| `GET` | `/api/v1/hreis/cpda/<id>/` | CPDA claim detail | `hr_eis.cpda.view_self`, etc. |
| `POST` | `/api/v1/hreis/cpda/<id>/verify/` | HR Admin verify CPDA claim | `hr_eis.cpda.verify` |
| `POST` | `/api/v1/hreis/cpda/<id>/decide/` | Approver decide on CPDA claim | `hr_eis.cpda.approve` |
| `POST` | `/api/v1/hreis/cpda/<id>/settle/` | Accountant record disbursement details | `hr_eis.cpda.settle` |
| `GET` | `/api/v1/hreis/workflows/settings/` | View workflow settings | `hr_eis.workflow.configure` |
| `PUT` | `/api/v1/hreis/workflows/settings/` | Update workflow settings | `hr_eis.workflow.configure` |
| `GET` | `/api/v1/hreis/audit-logs/` | List immutable audit logs | `hr_eis.audit.view` |
| `GET` | `/api/v1/hreis/notifications/` | List notifications for current user | `hr_eis.notification.view_self` |
| `PATCH` | `/api/v1/hreis/notifications/<id>/read/` | Mark notification as read | `hr_eis.notification.view_self` |
| `GET` | `/api/v1/hreis/stats/` | Dashboard metrics and pending queues | Authenticated HR user |

---

## §6 — Step 3.6: Public Contracts (`contracts.py`)

```python
def get_employee_record(user_id: int) -> EmployeeRecordDTO | None: ...
def get_leave_balance(user_id: int, leave_type: str) -> float | None: ...
```

---

## §7 — Step 3.7: Scheduled Work (`schedule.py`)

- `send_pending_action_reminders`: Daily job checking pending approvals older than 48 hours and generating reminder notifications (`HR-UC-021`).
- `send_deadline_notifications`: Checks upcoming appraisal window closures and alerts eligible employees (`HR-UC-022`).

---

## §8 — Step 3.8: Boundaries and Non-Goals

- HR-EIS does not execute bank transfers, alter salary components, or modify payroll rules (`HR-CFR-014`).
- All institute people are referenced strictly via integer `user_id` values (ADR 0013).
- Audit logs are immutable (`delete` and `update` prohibited).
