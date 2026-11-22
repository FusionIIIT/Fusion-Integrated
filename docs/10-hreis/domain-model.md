# HR-EIS Domain Model (Module 10)

Comprehensive entity specification, relationship graphs, constraints, and invariants for `modules/hreis`.

---

## Entity Relationship Overview

```
User (IAM erp_user_id)
  │
  ├── 1──1 EmployeeServiceRecord (leave_balances, cpda_balance, service_history)
  │
  ├── 1──* LeaveRequest (type, dates, duration, status, approval_history)
  │
  ├── 1──* AppraisalSubmission (academic_year, content, status, reviews, final_score)
  │
  ├── 1──* LtcRequest (request_type, block_year, amounts, verification, settlement)
  │
  ├── 1──* CpdaRequest (request_type, purpose, amount, verification, disbursement)
  │
  ├── 1──* HrNotification (category, title, message, is_read)
  │
  └── 1──* HrAuditLog (actor, action, entity_type, entity_id, timestamp [Immutable])
```

> **ADR-0013 Compliance:** Every `user_id` and `actor_id` is an integer reference across boundaries, never a database foreign key. Cross-module profile data is projected via `modules.directory.contracts.get_users`.

---

## Core Domain Entities

### 1. `EmployeeServiceRecord` (`hreis_service_record`)
- `user_id`: Integer, unique index. Primary identity link to IAM.
- `employee_id`: String(32), unique index (e.g., `PF-0101`, `EMP0245`).
- `department`: String(64) (e.g., `CSE`, `ECE`, `ME`, `Administration`).
- `designation`: String(64) (e.g., `Professor`, `Assistant Professor`).
- `category`: String(32) (`faculty` or `staff`).
- `appointment_date`: Date, null=True.
- `retirement_date`: Date, null=True.
- `retirement_status`: String(32) (`active`, `retired`, `suspended`).
- `leave_balances`: JSONField holding balance mapping:
  - `casual`: Initial 8.0 days
  - `restricted`: Initial 2.0 days
  - `medical`: Initial 15.0 days
  - `earned`: Initial 30.0 days
  - `vacation`: Initial 60.0 days
  - `sabbatical`: Initial 180.0 days
- `cpda_balance`: Decimal(10, 2), default `300000.00` INR (3-year block).
- `ltc_eligible_block`: String(32), default `2022-2025`.
- `service_history`: JSONField list of milestone objects (`event`, `date`, `designation`, `department`).
- `is_active`: Boolean, default True.

### 2. `LeaveRequest` (`hreis_leave_request`)
- `user_id`: Integer, indexed.
- `leave_type`: Choice (`casual`, `restricted`, `medical`, `earned`, `vacation`, `sabbatical`).
- `start_date`: Date.
- `end_date`: Date.
- `duration_days`: Decimal(4, 1), minimum 0.5.
- `justification`: TextField.
- `status`: Choice (`pending`, `forwarded`, `approved`, `rejected`).
- `current_authority_role`: String(64) (`hod`, `dean`, `registrar`, `director`).
- `approval_history`: JSONField list of audit trail transitions (`action`, `actor_id`, `role`, `timestamp`, `remarks`).

### 3. `AppraisalSubmission` (`hreis_appraisal_submission`)
- `user_id`: Integer, indexed.
- `academic_year`: String(32), indexed (e.g. `2025-2026`).
- `content`: JSONField containing self-appraisal payload (teaching, research, service).
- `status`: Choice (`draft`, `submitted`, `under_review`, `finalized`).
- `assigned_reviewers`: JSONField list of user integers (`[401, 402]`).
- `reviews`: JSONField list of review evaluations (`reviewer_id`, `role`, `score`, `comments`, `timestamp`).
- `final_score`: Decimal(4, 2), range 0.00 to 10.00.
- `final_remarks`: TextField.
- `finalized_at`: DateTime.
- `is_immutable`: Boolean, default False. Set True upon finalization (BR-HR-015).

### 4. `LtcRequest` (`hreis_ltc_request`)
- `user_id`: Integer, indexed.
- `request_type`: Choice (`advance`, `reimbursement`).
- `block_year`: String(32), indexed (`2022-2025`, `2026-2029`).
- `travel_from`: String(128).
- `travel_to`: String(128).
- `travel_start_date`: Date.
- `travel_end_date`: Date.
- `estimated_amount`: Decimal(10, 2).
- `claimed_amount`: Decimal(10, 2), null=True.
- `passed_amount`: Decimal(10, 2), null=True.
- `supporting_documents`: JSONField list of document URLs/hashes.
- `verification_status`: Choice (`pending`, `verified`, `returned`, `rejected`).
- `verification_remarks`: TextField.
- `status`: Choice (`submitted`, `pending_approval`, `forwarded`, `approved`, `rejected`, `settled`, `returned`).
- `current_authority_role`: String(64) (`hod`, `registrar`, `director`).
- `payment_status`: Choice (`unpaid`, `processing`, `paid`).
- `payment_reference`: String(128) (e.g. NEFT transaction reference).
- `settlement_details`: JSONField (`passed_amount`, `reference_id`, `accountant_id`, `settled_at`).

### 5. `CpdaRequest` (`hreis_cpda_request`)
- `user_id`: Integer, indexed.
- `request_type`: Choice (`advance`, `reimbursement`).
- `purpose`: String(255) (e.g., Books, Hardware, Conference).
- `amount`: Decimal(10, 2).
- `passed_amount`: Decimal(10, 2), null=True.
- `supporting_documents`: JSONField list.
- `verification_status`: Choice (`pending`, `verified`, `returned`, `rejected`).
- `verification_remarks`: TextField.
- `status`: Choice (`submitted`, `pending_approval`, `forwarded`, `approved`, `rejected`, `settled`, `returned`).
- `current_authority_role`: String(64) (`hod`, `director`).
- `disbursement_status`: Choice (`unpaid`, `processing`, `paid`).
- `disbursement_details`: JSONField (`passed_amount`, `voucher_no`, `accountant_id`, `disbursed_at`).

### 6. `HrAuditLog` (`hreis_audit_log`)
- `actor_id`: Integer, indexed.
- `actor_username`: String(150).
- `actor_role`: String(64).
- `action`: String(128) (e.g. `submit_leave_request`, `decide_leave_request`, `settle_ltc_claim`).
- `entity_type`: String(64), indexed (`leave_request`, `ltc_request`, `cpda_request`, `appraisal_submission`, `service_record`).
- `entity_id`: String(64), indexed.
- `details`: JSONField.
- `ip_address`: String(45).
- `timestamp`: DateTime, auto_now_add=True, indexed.
- **Immutability Guarantee:** Overridden `save` and `delete` methods raise `PermissionDenied` to prevent modification or deletion.

### 7. `HrNotification` (`hreis_notification`)
- `user_id`: Integer, indexed.
- `title`: String(255).
- `message`: TextField.
- `category`: Choice (`submission`, `approval`, `rejection`, `forwarding`, `reminder`, `policy`).
- `link`: String(255).
- `is_read`: Boolean, default False.
- `created_at`: DateTime, auto_now_add=True.

### 8. `WorkflowConfiguration` (`hreis_workflow_configuration`)
- `setting_key`: String(64), unique index.
- `setting_value`: JSONField.
- `description`: String(255).
