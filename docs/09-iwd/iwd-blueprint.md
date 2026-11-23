# Institute Work Department (IWD) Module Blueprint

## Specification & Module Metadata
- **Module Name**: Institute Work Department (IWD)
- **Module Code**: `iwd`
- **Specification ID Prefixes**: `CFR-IWD-`, `AFR-IWD-`, `BR-IWD-`, `UC-IWD-`, `BW-IWD-`, `CW-IWD-`
- **Environment**: `module-only`
- **Docs Folder**: `docs/09-iwd/`
- **Specification Baseline**: DIRECT_FINAL_v2 (v1.4, August 2026)

---

## 3.1 (a) Traceability Table

| ID | What it Requires | Architectural Layer | Enforcement Point (Planned) | Notes |
|---|---|---|---|---|
| **CFR-IWD-01** / AFR-001–006 | Maintenance complaint submission (civil/electrical, location, urgency, remarks) | `domain/` & `services/` | `services/complaints.py::submit_complaint` | Validates category & required fields |
| **CFR-IWD-02** / AFR-007–009 | Automatic engineer assignment by workload & discipline | `domain/` & `services/` | `domain/assignment.py::assign_engineer` | Assigns based on active complaint count |
| **CFR-IWD-03** / AFR-010–013 | Technical repair assessment & estimate preparation (time, materials, cost) | `domain/` & `services/` | `services/estimates.py::submit_estimate` | Captures repair estimate dossier |
| **CFR-IWD-04** / AFR-014–015, 018, 021 | Three-tier cost-band classification & approval routing | `domain/` | `domain/cost_bands.py::classify_band` | &lt;25k (Low), 25k–2.5L (Mid), &gt;2.5L (High) |
| **CFR-IWD-05** / AFR-016–017 | Low-cost approval by IWD Admin; quotation route when procurement needed | `domain/` & `services/` | `services/approvals.py::review_low_cost` | BW-IWD-02, BW-IWD-07, BR-IWD-004 |
| **CFR-IWD-06** / AFR-019–020 | Mid-range committee review & Department Head decision (Approve/Reject/Forward) | `domain/` & `services/` | `services/approvals.py::review_mid_range` | BW-IWD-03, BW-IWD-04, BR-IWD-005, 006 |
| **CFR-IWD-07** / AFR-022–023 | High-cost Director review authorizing external competitive bidding & vendor selection | `domain/` & `services/` | `services/bidding.py::authorize_bidding` | BW-IWD-05, BR-IWD-007, BR-IWD-008 |
| **CFR-IWD-08** / AFR-024–026 | Rejection reason retention & modified resubmission | `domain/` & `services/` | `services/estimates.py::resubmit_estimate` | BW-IWD-12–14, BR-IWD-009 |
| **CFR-IWD-09** / AFR-027–031 | Inventory stock check before procurement & work-linked material movement audit | `domain/` & `services/` | `services/inventory.py::issue_or_procure` | BW-IWD-06–08, BR-IWD-010, BR-IWD-011 |
| **CFR-IWD-10** / AFR-032–034 | Work execution progress & urgent fast-track review (preserves cost controls) | `domain/` & `services/` | `services/execution.py`, `services/urgent.py` | BW-IWD-15, BR-IWD-012 |
| **CFR-IWD-11** / AFR-035–037 | Audit logging of all approval, modification, and rejection decisions | `domain/` & `models.py` | `domain/audit.py::log_decision` | BR-IWD-013 immutable audit entries |
| **CFR-IWD-12** / AFR-038–039 | Physical verification by Department Head required before marking Resolved | `domain/` & `services/` | `services/verification.py::verify_work` | BR-IWD-014; max 1 rework traversal (BW-IWD-10) |
| **CFR-IWD-13** / AFR-040–045 | Post-verification final bill submission, Auditor validation, Director approval, Accounts settlement | `services/` | `services/settlement.py::settle_bill` | BW-IWD-11, BR-IWD-015, BR-IWD-016 |
| **CFR-IWD-14** / AFR-046–048 | Post-resolution feedback, rating, and post-repair incident reporting | `services/` | `services/feedback.py::submit_feedback` | BR-IWD-017; only permitted when is_resolved=True |
| **CFR-IWD-15** / AFR-049–053 | IWD Notification events (submission, assignment, decisions, escalation) | `services/` | `services/notifications.py` | Event-triggered operational notifications |
| **CFR-IWD-16** / AFR-054–057, 060 | Role-based authorization & strict separation of Department Head and Dean | `registry.py` & `domain/` | `domain/roles.py::validate_role` | BR-IWD-001, BR-IWD-018 distinct identities |
| **CFR-IWD-17** / AFR-058 | Consistency with shared Fusion ERP data & identity services | `contracts.py` | `contracts.py` | Plain integer user IDs |

---

## 3.2 (b) Domain Model & Database Invariants

All models inherit from `UserScopedModel` or standard Django models using plain integer `user_id` values (no cross-service foreign keys to IAM).

### Entities
1. **`Complaint` (`iwd_complaint`)**:
   - `id`: AutoField
   - `requester_user_id`: IntegerField (indexed)
   - `category`: CharField (`Civil`, `Electrical`)
   - `location`: CharField(max_length=255)
   - `urgency`: CharField (`Low`, `Medium`, `High`, `Urgent`)
   - `remarks`: TextField
   - `assigned_engineer_id`: IntegerField (nullable, indexed)
   - `status`: CharField(max_length=50, default='Submitted')
   - `is_urgent`: BooleanField(default=False)
   - `urgent_remarks`: TextField
   - `is_resolved`: BooleanField(default=False)
   - `rework_count`: IntegerField(default=0)
   - `created_at`, `updated_at`: DateTimeField
   - *Database Invariants*: `CheckConstraint(check=Q(rework_count__lte=1), name='iwd_complaint_max_one_rework')`

2. **`Estimate` (`iwd_estimate`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `engineer_user_id`: IntegerField
   - `estimated_days`: IntegerField
   - `materials_description`: TextField
   - `total_cost`: DecimalField(max_digits=12, decimal_places=2)
   - `cost_band`: CharField (`LOW`, `MID`, `HIGH`)
   - `committee_review`: TextField
   - `dept_head_decision`: CharField(max_length=50)
   - `director_decision`: CharField(max_length=50)
   - `rejection_reason`: TextField
   - `resubmission_count`: IntegerField(default=0)
   - `status`: CharField(max_length=50)
   - *Database Invariants*: `CheckConstraint(check=Q(total_cost__gte=0), name='iwd_estimate_cost_positive')`

3. **`InventoryItem` (`iwd_inventory_item`)**:
   - `id`: AutoField
   - `name`: CharField(max_length=200, unique=True)
   - `category`: CharField(max_length=50)
   - `unit`: CharField(max_length=50)
   - `unit_price`: DecimalField(max_digits=10, decimal_places=2)
   - `stock_quantity`: IntegerField(default=0)
   - *Database Invariants*: `CheckConstraint(check=Q(stock_quantity__gte=0), name='iwd_stock_non_negative')`

4. **`MaterialIssue` (`iwd_material_issue`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `item_id`: ForeignKey(`InventoryItem`, on_delete=CASCADE)
   - `quantity`: IntegerField
   - `issued_by_user_id`: IntegerField
   - `issued_at`: DateTimeField(auto_now_add=True)

5. **`VerificationRecord` (`iwd_verification_record`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `verifier_user_id`: IntegerField
   - `outcome`: CharField (`Approved`, `Rework Required`)
   - `remarks`: TextField
   - `verified_at`: DateTimeField(auto_now_add=True)

6. **`FinalBill` (`iwd_final_bill`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `total_amount`: DecimalField(max_digits=12, decimal_places=2)
   - `auditor_status`: CharField (`Pending`, `Validated`, `Query`)
   - `auditor_remarks`: TextField
   - `director_approved`: BooleanField(default=False)
   - `settled`: BooleanField(default=False)
   - `settlement_reference`: CharField(max_length=100)

7. **`ComplaintFeedback` (`iwd_complaint_feedback`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `employee_user_id`: IntegerField
   - `rating`: IntegerField (1–5)
   - `comments`: TextField
   - `post_repair_issue`: BooleanField(default=False)
   - `post_repair_remarks`: TextField

8. **`DecisionAuditTrail` (`iwd_decision_audit_trail`)**:
   - `id`: AutoField
   - `complaint_id`: ForeignKey(`Complaint`, on_delete=CASCADE)
   - `actor_user_id`: IntegerField(nullable=True)
   - `actor_role`: CharField(max_length=50)
   - `action`: CharField(max_length=100)
   - `previous_state`: CharField(max_length=50)
   - `new_state`: CharField(max_length=50)
   - `remarks`: TextField
   - `timestamp`: DateTimeField(auto_now_add=True)

---

## 3.3 (c) Declarative State-Transition Table

```python
TRANSITIONS = {
    # BW-IWD-01: Intake
    "Submitted": {"assign": "Assigned"},
    "Assigned": {"assess": "Assessed", "flag_urgent": "Urgent Review Pending"},
    "Assessed": {
        "submit_low": "Low-Cost Review Pending",
        "submit_mid": "Mid-Range Committee Review Pending",
        "submit_high": "Director Review Pending (High-Cost)",
        "flag_urgent": "Urgent Review Pending",
    },
    # Approvals
    "Low-Cost Review Pending": {"approve": "Estimate Approved", "reject": "Rejected - Low-Cost"},
    "Mid-Range Committee Review Pending": {"record_committee": "Department Head Review Pending"},
    "Department Head Review Pending": {
        "approve": "Estimate Approved",
        "reject": "Rejected - Mid-Range",
        "forward": "Director Review Pending (Mid-Range)",
    },
    "Director Review Pending (Mid-Range)": {"approve": "Estimate Approved", "reject": "Rejected - Director Route"},
    "Director Review Pending (High-Cost)": {"approve": "Bidding Authorized", "reject": "Rejected - Director Route"},
    "Bidding Authorized": {"select_vendor": "Vendor/Contractor Selected"},
    "Vendor/Contractor Selected": {"finalize_vendor": "Ready for Execution"},
    # Resubmission
    "Rejected - Low-Cost": {"modify_resubmit": "Low-Cost Review Pending"},
    "Rejected - Mid-Range": {"modify_resubmit": "Mid-Range Committee Review Pending"},
    "Rejected - Director Route": {"modify_resubmit": "Director Review Pending (High-Cost)"},
    # Inventory
    "Estimate Approved": {
        "issue_stock": "Materials Issued",
        "shortage_low": "Procurement Needed (Low)",
        "shortage_mid": "Procurement Needed (Mid)",
    },
    "Procurement Needed (Low)": {"procure_complete": "Materials Available"},
    "Procurement Needed (Mid)": {"procure_complete": "Materials Available"},
    "Materials Available": {"issue_stock": "Materials Issued"},
    "Materials Issued": {"start_execution": "Ready for Execution"},
    # Execution & Verification
    "Ready for Execution": {"work_complete": "Verification Pending"},
    "Verification Pending": {"verify_approved": "Resolved", "verify_rework": "Rework Required"},
    "Rework Required": {"rework_complete": "Verification Pending"},
    # Settlement
    "Resolved": {"submit_bill": "Audit Pending"},
    "Audit Pending": {"audit_validate": "Director Payment Approval Pending", "audit_query": "Audit Pending"},
    "Director Payment Approval Pending": {"director_approve_payment": "Accounts Settlement Pending"},
    "Accounts Settlement Pending": {"accounts_settle": "Settled"},
}
```

---

## 3.4 (d) Permissions and Role Grants (`registry.py`)

- **Permissions**:
  - `iwd.complaint.create`
  - `iwd.complaint.view`
  - `iwd.complaint.assess`
  - `iwd.estimate.create`
  - `iwd.estimate.review_admin`
  - `iwd.estimate.review_dept_head`
  - `iwd.estimate.review_director`
  - `iwd.inventory.manage`
  - `iwd.work.execute`
  - `iwd.work.verify`
  - `iwd.bill.submit`
  - `iwd.bill.audit`
  - `iwd.bill.settle`
  - `iwd.feedback.submit`
  - `iwd.feedback.view`

- **Role Grants**:
  - `student`, `faculty`, `staff` (Institute Employee): `complaint.create`, `complaint.view`, `feedback.submit`
  - `iwd_engineer` (Engineer): `complaint.view`, `complaint.assess`, `estimate.create`, `work.execute`, `bill.submit`
  - `iwd_admin` (IWD Admin): `estimate.review_admin`, `inventory.manage`, `feedback.view`
  - `iwd_department_head` (Department Head): `estimate.review_dept_head`, `work.verify`, `feedback.view`
  - `iwd_dean` (Dean): Separate role; distinct authority in accordance with BR-IWD-001 & BR-IWD-018
  - `iwd_director` (Director): `estimate.review_director`, `bill.settle`, `feedback.view`
  - `iwd_auditor` (Auditor): `bill.audit`, `feedback.view`
  - `iwd_accounts` (Accounts Department): `bill.settle`

---

## 3.5 (e) API Surface (`api/`)

Base URL: `/api/v1/iwd/`

1. `POST /complaints/` — Submit complaint (`UC-IWD-001`)
2. `GET /complaints/` — Track complaints / scoped listing (`UC-IWD-005`, `AFR-IWD-009`)
3. `GET /complaints/<id>/` — Complaint detail & status history
4. `POST /complaints/<id>/assess/` — Record assessment (`UC-IWD-015`)
5. `POST /complaints/<id>/estimates/` — Submit cost estimate (`UC-IWD-021`)
6. `POST /complaints/<id>/flag-urgent/` — Flag urgent repair (`UC-IWD-025`)
7. `POST /complaints/<id>/review-urgent/` — Review urgent escalation (`UC-IWD-055`)
8. `POST /complaints/<id>/review-low-cost/` — IWD Admin decision (`UC-IWD-031`)
9. `POST /complaints/<id>/review-mid-range/` — Committee & Dept Head review (`UC-IWD-041`)
10. `POST /complaints/<id>/review-director/` — Director decision (`UC-IWD-051`)
11. `POST /complaints/<id>/issue-material/` — Stock check & material issue (`UC-IWD-061`)
12. `POST /complaints/<id>/coordinate-procurement/` — Procure stock shortage (`UC-IWD-071`)
13. `POST /complaints/<id>/complete-work/` — Engineer marks work complete (`UC-IWD-091`)
14. `POST /complaints/<id>/verify/` — Department Head physical verification (`UC-IWD-101`)
15. `POST /complaints/<id>/final-bill/` — Submit final bill (`UC-IWD-111`)
16. `POST /complaints/<id>/audit/` — Auditor bill validation (`UC-IWD-121`)
17. `POST /complaints/<id>/settle/` — Director approve & Accounts settle (`UC-IWD-131`)
18. `POST /complaints/<id>/feedback/` — Submit feedback & post-repair report (`UC-IWD-141`)
19. `POST /complaints/<id>/resubmit/` — Modify & resubmit rejected request (`UC-IWD-151`)

---

## 3.6 (f) Frontend Pages (`client/src/modules/iwd/`)

1. `pages/ComplaintsListPage.tsx`: Displays submitted/assigned maintenance requests.
2. `pages/ComplaintSubmitPage.tsx`: Complaint intake form with category, location, urgency, remarks.
3. `pages/ComplaintDetailPage.tsx`: Complete complaint lifecycle dashboard, assessment, estimate, and audit log.
4. `pages/ApprovalDashboardPage.tsx`: Role-specific approval inbox (IWD Admin, Dept Head, Director).
5. `pages/VerificationPage.tsx`: Department Head physical verification interface.
6. `pages/BillingSettlementPage.tsx`: Final bill submission, Auditor validation, and settlement tracking.

---

## 3.7 (g) Background Jobs & Outbox

- Timestamp-based tracking on all state changes via `DecisionAuditTrail`.
- Event notifications handled on synchronous state transitions. No periodic Celery beat workers required.

---

## 3.8 (h) Testing Strategy & Known Gaps

- Comprehensive isolated backend tests covering:
  - Role authorization and security checks (`test_privilege_escalation.py`).
  - Queryset scoping per role (`test_scoping.py`).
  - State machine transitions & guard validations (`test_state_machine.py`).
  - Full lifecycle execution from intake to accounts settlement (`test_lifecycle.py`).
- **Known Gaps**: None. All 15 Basis Workflows and 18 Business Rules are fully specified.
