# Institute Accounts and Audits (IAA) Module Blueprint

Module Code: `iaa`
Specification ID Prefixes: `IAA-BR-`, `IAA-UC-`, `BW-IAA-`, `CW-IAA-`, `CFR-IAA-`, `AFR-IAA-`
Environment: `module-only`

---

## 1. Traceability Table

### Business Rules (19 Active, 0 Retired)

| Id | Rule Name | Layer | Enforcement Point | Notes |
|---|---|---|---|---|
| `IAA-BR-001` | Segregation of Duties | `services/` | `approvals.py::record_decision` | Approver cannot equal creator/claimant |
| `IAA-BR-002` | Configured Approval Routing | `services/`, `domain/` | `approvals.py::determine_next_approver` | Determined by amount, type, department, hierarchy rules |
| `IAA-BR-003` | Explicit Active-Role Selection | `api/` | `permissions.py::ActiveRolePermission` | Actions authorized and logged with active role |
| `IAA-BR-004` | System Admin Operational Separation | `api/`, `selectors/` | `scoping.py::apply_role_scoping` | System admin has configuration access, no operational data access |
| `IAA-BR-005` | Approval Decision Remarks | `services/`, `domain/` | `approvals.py::record_decision` | Mandatory non-empty remarks for approval or rejection |
| `IAA-BR-006` | Internal Processing Is Non-Monetary | `services/` | `requests.py::record_processing`, `travel.py::record_processing` | Terminal recorded state is internal record completion only |
| `IAA-BR-101` | Submission Completeness Validation | `domain/`, `services/` | `rules.py::validate_submission_completeness` | Incomplete allowed for Draft, blocked on formal submission |
| `IAA-BR-102` | Budget Availability Validation | `services/` | `requests.py::validate_finance`, `anomalies.py::check_budget` | Insufficiency creates anomaly, not auto-rejection |
| `IAA-BR-103` | Material Anomaly Trigger and Tracking | `services/`, `models/` | `anomalies.py::create_anomaly` | Tracks Open -> Resolved / Escalated |
| `IAA-BR-104` | Post-Submission Record Lock | `services/`, `domain/` | `requests.py`, `travel.py` | Locked against ordinary edits after submission |
| `IAA-BR-201` | TA Verification Policy | `domain/`, `services/` | `travel.py::verify_claim` | Verified against policy parameters and receipts |
| `IAA-BR-202` | High-Value TA Approval | `domain/`, `services/` | `travel.py::verify_claim` | Claims >= threshold require HoD/Dean/Director approval route |
| `IAA-BR-301` | Audit Observation Lifecycle | `domain/`, `models/` | `state_machine.py`, `audit.py` | States: Open -> Responded -> Closed (no Reopened) |
| `IAA-BR-302` | Audit Closure Verification | `services/` | `audit.py::review_response` | Closed only when satisfactory, else returns to Open |
| `IAA-BR-401` | Approval Timeout Escalation | `tasks.py`, `services/` | `tasks.py::escalate_overdue_approvals` | Event-triggered transition when timeout duration exceeded |
| `IAA-BR-501` | Role-Based Access and Data Visibility | `selectors/`, `api/` | `scoping.py`, `permissions.py` | Role-scoped visibility (yields 404 for out of scope) |
| `IAA-BR-502` | Historical Role Integrity | `services/`, `models/` | `audit_trail.py::record_log` | Historical logs immutable and preserve original acting role |
| `IAA-BR-503` | Complete Audit Logging | `services/`, `models/` | `audit_trail.py` | Immutable audit trail for all state changes & config |
| `IAA-BR-504` | Notification Trigger Matrix | `services/` | `notifications.py` | Fusion notifications on submission, status change, anomalies |

### Use Cases (27 Active, 0 Retired)

| Id | Name | Primary Actor | Enforcement Point |
|---|---|---|---|
| `IAA-UC-101` | Create Expense / Voucher Request | Basic User | `services/requests.py::create_request` |
| `IAA-UC-102` | Submit Expense / Voucher Request | Basic User | `services/requests.py::submit_request` |
| `IAA-UC-103` | Review & Validate Request (Finance) | Finance Staff | `services/requests.py::review_and_validate` |
| `IAA-UC-104` | Respond to Finance Clarification Query | Basic User | `services/requests.py::respond_to_query` |
| `IAA-UC-105` | Process & Record Approved Request | Finance Staff | `services/requests.py::record_processing` |
| `IAA-UC-201` | Approve / Reject Request | HoD / Dean / Director | `services/approvals.py::record_decision` |
| `IAA-UC-202` | Handle Escalated Approval | Next Approving Authority | `services/approvals.py::record_escalated_decision` |
| `IAA-UC-203` | Escalate Overdue Approval | System (Event/Beat) | `tasks.py::escalate_overdue_approvals` |
| `IAA-UC-302` | Flag Anomaly | Finance Staff / Auditor | `services/anomalies.py::flag_manual_anomaly` |
| `IAA-UC-303` | Resolve or Escalate Anomaly | Designated Resolver | `services/anomalies.py::resolve_or_escalate` |
| `IAA-UC-304` | Create Automatic Anomaly | System (Event) | `services/anomalies.py::create_automatic_anomaly` |
| `IAA-UC-401` | Submit TA Form | Basic User (Employee) | `services/travel.py::submit_claim` |
| `IAA-UC-402` | Verify TA Form | Finance Staff | `services/travel.py::verify_claim` |
| `IAA-UC-403` | Approve / Reject High-Value TA Form | HoD / Dean / Director | `services/travel.py::record_authority_decision` |
| `IAA-UC-404` | Process & Record TA Request | Finance Staff | `services/travel.py::record_processing` |
| `IAA-UC-501` | Raise Audit Observation | Auditor | `services/audit.py::raise_observation` |
| `IAA-UC-502` | Respond to Audit Observation | Basic User / Dept Rep | `services/audit.py::respond_to_observation` |
| `IAA-UC-503` | Review and Close Audit Observation | Auditor | `services/audit.py::review_and_close` |
| `IAA-UC-504` | Review Financial Records for Audit | Auditor | `selectors/audit.py::list_audit_records` |
| `IAA-UC-601` | View Reports & Dashboards | Finance / Approver / Auditor | `selectors/reports.py::get_dashboard_metrics` |
| `IAA-UC-602` | Export Report | Finance / Approver / Auditor | `api/views.py::ExportReportView` |
| `IAA-UC-603` | Track Own Request / TA Status | Basic User | `selectors/scoping.py::get_own_requests` |
| `IAA-UC-604` | View Notifications & Pending Actions | All Roles | `selectors/scoping.py::get_pending_actions` |
| `IAA-UC-701` | Switch Active IAA Role | Authenticated Multi-role User | `services/configuration.py::switch_active_role` |
| `IAA-UC-702` | Manage IAA Role Assignments | System Admin | `services/configuration.py::assign_user_role` |
| `IAA-UC-703` | Configure Approval Hierarchy & Thresholds | System Admin | `services/configuration.py::save_hierarchy_rule` |
| `IAA-UC-704` | Configure Financial Year & Policy Parameters | System Admin | `services/configuration.py::save_policy` |

---

## 2. Domain Model

Entities sit in `fusion_integrated` (no user/role table duplicates; plain `user_id` integers):

### `ExpenseVoucherRequest` (`models/requests.py`)
- `id`: AutoField
- `user_id`: IntegerField (db_index=True)
- `department`: CharField(max_length=64)
- `request_type`: CharField(choices=['expense', 'voucher'])
- `title`: CharField(max_length=255)
- `description`: TextField
- `total_amount`: DecimalField(max_digits=12, decimal_places=2)
- `status`: CharField(choices=['draft', 'submitted', 'query_raised', 'query_responded', 'finance_validated', 'approval_pending', 'approved', 'rejected', 'escalated', 'recorded'])
- `current_approval_level`: PositiveIntegerField(default=1)
- `required_approval_levels`: PositiveIntegerField(default=1)
- `assigned_approver_role`: CharField(max_length=64, blank=True)
- `assigned_approver_id`: IntegerField(null=True, blank=True)
- `approval_assigned_at`: DateTimeField(null=True, blank=True)
- `is_locked`: BooleanField(default=False)
- Timestamps: `created_at`, `updated_at`

### `ExpenseItem` (`models/requests.py`)
- `request`: ForeignKey(ExpenseVoucherRequest, related_name='items', on_delete=CASCADE)
- `description`: CharField(max_length=255)
- `category`: CharField(max_length=64)
- `amount`: DecimalField(max_digits=12, decimal_places=2)
- `receipt_reference`: CharField(max_length=128, blank=True)

### `TAClaim` (`models/travel.py`)
- `id`: AutoField
- `user_id`: IntegerField(db_index=True)
- `department`: CharField(max_length=64)
- `purpose`: CharField(max_length=255)
- `departure_date`: DateField
- `arrival_date`: DateField
- `source_location`: CharField(max_length=128)
- `destination_location`: CharField(max_length=128)
- `claimed_amount`: DecimalField(max_digits=12, decimal_places=2)
- `status`: CharField(choices=['submitted', 'query_raised', 'query_responded', 'verified', 'approval_pending', 'approved', 'rejected', 'escalated', 'recorded'])
- `is_high_value`: BooleanField(default=False)
- `assigned_approver_role`: CharField(max_length=64, blank=True)
- `assigned_approver_id`: IntegerField(null=True, blank=True)
- `approval_assigned_at`: DateTimeField(null=True, blank=True)
- `is_locked`: BooleanField(default=True)
- Timestamps: `created_at`, `updated_at`

### `ApprovalAction` (`models/approvals.py`)
- `content_type`: CharField(max_length=32, choices=['request', 'travel'])
- `object_id`: IntegerField(db_index=True)
- `actor_id`: IntegerField()
- `actor_role`: CharField(max_length=64)
- `decision`: CharField(choices=['approve', 'reject', 'escalate', 'query'])
- `remarks`: TextField()
- `level`: PositiveIntegerField(default=1)
- `created_at`: DateTimeField(auto_now_add=True)

### `ClarificationQuery` (`models/approvals.py`)
- `content_type`: CharField(max_length=32)
- `object_id`: IntegerField()
- `sender_id`: IntegerField()
- `query_text`: TextField()
- `response_text`: TextField(blank=True)
- `status`: CharField(choices=['pending', 'responded'])
- `created_at`, `responded_at`: DateTimeFields

### `Anomaly` (`models/anomalies.py`)
- `id`: AutoField
- `category`: CharField(choices=['budget_insufficient', 'policy_violation', 'duplicate_claim', 'manual_flag'])
- `description`: TextField()
- `reference_type`: CharField(max_length=32)
- `reference_id`: IntegerField()
- `status`: CharField(choices=['open', 'resolved', 'escalated'])
- `flagged_by_id`: IntegerField(null=True, blank=True)
- `flagged_by_role`: CharField(max_length=64)
- `resolver_role`: CharField(max_length=64)
- `resolution_remarks`: TextField(blank=True)
- `created_at`, `resolved_at`: DateTimeFields

### `AuditObservation` (`models/audit.py`)
- `id`: AutoField
- `auditor_id`: IntegerField()
- `department`: CharField(max_length=64)
- `reference_type`: CharField(max_length=32)
- `reference_id`: IntegerField()
- `title`: CharField(max_length=255)
- `description`: TextField()
- `status`: CharField(choices=['open', 'responded', 'closed'])
- `response_text`: TextField(blank=True)
- `responded_by_id`: IntegerField(null=True, blank=True)
- `responded_at`: DateTimeField(null=True, blank=True)
- `closure_remarks`: TextField(blank=True)
- `closed_at`: DateTimeField(null=True, blank=True)
- `created_at`, `updated_at`: DateTimeFields

### `AuditLogEntry` (`models/audit.py`)
- `id`: AutoField
- `user_id`: IntegerField()
- `acting_role`: CharField(max_length=64)
- `action`: CharField(max_length=64)
- `target_type`: CharField(max_length=32)
- `target_id`: IntegerField()
- `resulting_status`: CharField(max_length=32, blank=True)
- `details`: JSONField(default=dict)
- `created_at`: DateTimeField(auto_now_add=True)

### `IAAConfiguration` & `ApprovalHierarchyRule` (`models/configuration.py`)
- `financial_year`: CharField(max_length=16)
- `high_value_ta_threshold`: DecimalField(max_digits=12, decimal_places=2, default=50000.00)
- `approval_timeout_days`: PositiveIntegerField(default=3)
- `hierarchy_rules`: Department / threshold -> Approver role route rules
- `department_budgets`: Department -> allocated budget amount

---

## 3. State Machines

Declarative transition tables in `modules/iaa/domain/state_machine.py`:

```python
EXPENSE_TRANSITIONS = {
    ("draft", "submit", "basic_user"): "submitted",
    ("submitted", "raise_query", "finance_staff"): "query_raised",
    ("query_raised", "respond_query", "basic_user"): "query_responded",
    ("query_responded", "validate", "finance_staff"): "finance_validated",
    ("submitted", "validate", "finance_staff"): "finance_validated",
    ("finance_validated", "approve_level", "approving_authority"): "approval_pending",
    ("finance_validated", "approve_final", "approving_authority"): "approved",
    ("finance_validated", "reject", "approving_authority"): "rejected",
    ("finance_validated", "timeout_escalate", "system"): "escalated",
    ("approval_pending", "approve_level", "approving_authority"): "approval_pending",
    ("approval_pending", "approve_final", "approving_authority"): "approved",
    ("approval_pending", "reject", "approving_authority"): "rejected",
    ("approval_pending", "timeout_escalate", "system"): "escalated",
    ("escalated", "approve_level", "approving_authority"): "approval_pending",
    ("escalated", "approve_final", "approving_authority"): "approved",
    ("escalated", "reject", "approving_authority"): "rejected",
    ("approved", "record", "finance_staff"): "recorded",
}

TA_TRANSITIONS = {
    ("not_submitted", "submit", "basic_user"): "submitted",
    ("submitted", "raise_query", "finance_staff"): "query_raised",
    ("query_raised", "respond_query", "basic_user"): "query_responded",
    ("submitted", "verify_standard", "finance_staff"): "verified",
    ("query_responded", "verify_standard", "finance_staff"): "verified",
    ("submitted", "verify_high_value", "finance_staff"): "approval_pending",
    ("query_responded", "verify_high_value", "finance_staff"): "approval_pending",
    ("submitted", "reject", "finance_staff"): "rejected",
    ("query_responded", "reject", "finance_staff"): "rejected",
    ("approval_pending", "approve_level", "approving_authority"): "approval_pending",
    ("approval_pending", "approve_final", "approving_authority"): "approved",
    ("approval_pending", "reject", "approving_authority"): "rejected",
    ("approval_pending", "timeout_escalate", "system"): "escalated",
    ("escalated", "approve_final", "approving_authority"): "approved",
    ("escalated", "reject", "approving_authority"): "rejected",
    ("verified", "record", "finance_staff"): "recorded",
    ("approved", "record", "finance_staff"): "recorded",
}

ANOMALY_TRANSITIONS = {
    ("none", "flag_manual", "finance_or_auditor"): "open",
    ("none", "flag_automatic", "system"): "open",
    ("open", "resolve", "resolver"): "resolved",
    ("open", "escalate", "resolver"): "escalated",
    ("escalated", "resolve", "resolver"): "resolved",
}

AUDIT_TRANSITIONS = {
    ("none", "create", "auditor"): "open",
    ("open", "respond", "basic_user"): "responded",
    ("responded", "close", "auditor"): "closed",
    ("responded", "reject_response", "auditor"): "open",
}
```

---

## 4. Permission List & Registry

### Permissions (`registry.py`)
- `iaa.request.create`
- `iaa.request.view_self`
- `iaa.request.view_all`
- `iaa.request.validate`
- `iaa.request.approve`
- `iaa.request.record`
- `iaa.travel.create`
- `iaa.travel.view_self`
- `iaa.travel.view_all`
- `iaa.travel.verify`
- `iaa.travel.approve`
- `iaa.travel.record`
- `iaa.anomaly.view`
- `iaa.anomaly.flag`
- `iaa.anomaly.resolve`
- `iaa.audit.view`
- `iaa.audit.raise`
- `iaa.audit.respond`
- `iaa.audit.close`
- `iaa.report.view`
- `iaa.config.manage`

### System Permissions (Celery Beat)
- `iaa.approval.timeout_escalate`
- `iaa.anomaly.auto_create`

### Role Grants (Mapped to Standard Designations)
- `student`, `faculty`, `staff` (Basic User):
  - `iaa.request.create`, `iaa.request.view_self`, `iaa.travel.create`, `iaa.travel.view_self`, `iaa.audit.respond`
- `finance_staff`:
  - `iaa.request.view_all`, `iaa.request.validate`, `iaa.request.record`, `iaa.travel.view_all`, `iaa.travel.verify`, `iaa.travel.record`, `iaa.anomaly.view`, `iaa.anomaly.flag`, `iaa.anomaly.resolve`, `iaa.report.view`
- `hod`, `dean`, `director` (Approving Authorities):
  - `iaa.request.view_all`, `iaa.request.approve`, `iaa.travel.view_all`, `iaa.travel.approve`, `iaa.anomaly.view`, `iaa.anomaly.resolve`, `iaa.report.view`
- `auditor`:
  - `iaa.request.view_all`, `iaa.travel.view_all`, `iaa.anomaly.view`, `iaa.anomaly.flag`, `iaa.audit.view`, `iaa.audit.raise`, `iaa.audit.close`, `iaa.report.view`
- `system_admin`:
  - `iaa.config.manage`

---

## 5. Endpoint List (`/api/v1/iaa/`)

| Method | Path | Gates | Return | Enforces |
|---|---|---|---|---|
| `GET` | `/requests/` | `HasModuleGrant('iaa')`, `ScopedCollection` | Paginated list | `IAA-BR-501`, `IAA-UC-603` |
| `POST` | `/requests/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.create')` | Created request | `IAA-BR-101`, `IAA-UC-101` |
| `GET` | `/requests/{id}/` | `HasModuleGrant('iaa')`, `ScopedCollection` | Request detail | `IAA-BR-501` |
| `POST` | `/requests/{id}/submit/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.create')` | Submitted request | `IAA-BR-101`, `IAA-BR-104`, `IAA-UC-102` |
| `POST` | `/requests/{id}/validate/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.validate')` | Validated status | `IAA-BR-102`, `IAA-UC-103` |
| `POST` | `/requests/{id}/query/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.validate')` | Query raised | `IAA-BR-504`, `IAA-UC-103` |
| `POST` | `/requests/{id}/respond-query/`| `HasModuleGrant('iaa')`, `HasPermission('iaa.request.create')` | Query responded | `IAA-BR-104`, `IAA-UC-104` |
| `POST` | `/requests/{id}/decide/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.approve')` | Approval decision | `IAA-BR-001`, `IAA-BR-002`, `IAA-BR-005`, `IAA-UC-201`, `IAA-UC-202` |
| `POST` | `/requests/{id}/record/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.request.record')` | Recorded completion | `IAA-BR-006`, `IAA-UC-105` |
| `GET` | `/travel/` | `HasModuleGrant('iaa')`, `ScopedCollection` | Paginated list | `IAA-BR-501`, `IAA-UC-603` |
| `POST` | `/travel/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.travel.create')` | Created claim | `IAA-BR-101`, `IAA-UC-401` |
| `GET` | `/travel/{id}/` | `HasModuleGrant('iaa')`, `ScopedCollection` | Claim detail | `IAA-BR-501` |
| `POST` | `/travel/{id}/verify/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.travel.verify')` | Verified / Routed | `IAA-BR-201`, `IAA-BR-202`, `IAA-UC-402` |
| `POST` | `/travel/{id}/decide/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.travel.approve')` | Authority decision | `IAA-BR-001`, `IAA-BR-005`, `IAA-UC-403` |
| `POST` | `/travel/{id}/record/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.travel.record')` | Recorded completion | `IAA-BR-006`, `IAA-UC-404` |
| `GET` | `/anomalies/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.anomaly.view')` | Anomaly list | `IAA-BR-103`, `IAA-UC-302` |
| `POST` | `/anomalies/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.anomaly.flag')` | Created anomaly | `IAA-BR-103`, `IAA-UC-302` |
| `POST` | `/anomalies/{id}/resolve/`| `HasModuleGrant('iaa')`, `HasPermission('iaa.anomaly.resolve')`| Resolved status | `IAA-BR-103`, `IAA-UC-303` |
| `POST` | `/anomalies/{id}/escalate/`| `HasModuleGrant('iaa')`, `HasPermission('iaa.anomaly.resolve')`| Escalated status | `IAA-BR-103`, `IAA-UC-303` |
| `GET` | `/audit/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.audit.view')` | Observation list | `IAA-BR-301`, `IAA-UC-504` |
| `POST` | `/audit/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.audit.raise')` | Created observation | `IAA-BR-301`, `IAA-UC-501` |
| `POST` | `/audit/{id}/respond/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.audit.respond')` | Responded status | `IAA-BR-301`, `IAA-UC-502` |
| `POST` | `/audit/{id}/close/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.audit.close')` | Closed status | `IAA-BR-302`, `IAA-UC-503` |
| `GET` | `/reports/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.report.view')` | Aggregated report | `IAA-BR-501`, `IAA-UC-601` |
| `GET` | `/reports/export/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.report.view')` | CSV Stream | `IAA-BR-501`, `IAA-UC-602` |
| `GET` | `/config/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.config.manage')` | Policy config | `IAA-BR-004`, `IAA-UC-703`, `IAA-UC-704` |
| `PUT` | `/config/` | `HasModuleGrant('iaa')`, `HasPermission('iaa.config.manage')` | Updated config | `IAA-BR-004`, `IAA-UC-703`, `IAA-UC-704` |

### Portal `INTEGRATED_MODULES` Sidebar Entry:
```js
{
  id: "iaa",
  label: "Institute Accounts & Audits",
  icon: "Receipt",
  to: "/iaa",
  section: "Administration"
}
```

---

## 6. Contracts (`modules/iaa/contracts.py`)

Plural contract methods exposed to other modules:
- `get_requests(request_ids: Sequence[int]) -> Sequence[RequestDTO]`
- `get_claims(claim_ids: Sequence[int]) -> Sequence[ClaimDTO]`
- `get_anomalies_for_targets(target_type: str, target_ids: Sequence[int]) -> Sequence[AnomalyDTO]`

---

## 7. Scheduled Work (`schedule.py`)

- `iaa.tasks.escalate_overdue_approvals`: Runs hourly (`0 * * * *`). Checks all pending approval requests and high-value TA claims where `approval_assigned_at + approval_timeout_days < now()`. Escalates to next authority, writes audit log, emits notifications (`IAA-BR-401`, `IAA-UC-203`).

---

## 8. Open Questions & Policy Defaults
- Configured defaults: High-value TA threshold = 50,000 INR; Approval timeout = 3 days; Budget allocation per department configurable via System Admin command/UI.
