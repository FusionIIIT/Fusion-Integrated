# RSPC Module Blueprint (Research, Sponsored Projects and Consultancy)

**Module:** Research, Sponsored Projects and Consultancy (RSPC)  
**Module Code:** `rspc`  
**Docs Folder:** `docs/09-rspc/`  
**Specification Baseline:** v1.3 / v2.1 SYNCHRONIZED  
**Environment:** `module-only`  

---

## Step 3.1 (a) — Traceability Table

The RSPC specification contains 29 Coherent Functional Requirements (CFR), 126 Atomic Functional Requirements (AFR/FR), 29 Active Use Cases (UC), 38 Active Business Rules (BR), and 18 Workflows (12 Basis BW, 6 Composite CW).

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|:---|:---|:---|:---|:---|
| **RSPC-CFR-01** | Proposal Creation and Submission | `services/` | `services/proposal.py::create_proposal` | Validates mandatory proposal metadata and budget heads |
| **RSPC-CFR-02** | Department Endorsement (HoD) | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Restricts transition to verified HoD role |
| **RSPC-CFR-03** | Institutional Approval (Dean-RSPC) | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Validates institutional commitment and overheads |
| **RSPC-CFR-04** | Project Sanction and Registration | `services/` | `services/project.py::register_project` | Creates project instance, budget heads, and audit record |
| **RSPC-CFR-05** | Financial Ledger and Head Allocation | `models/` | `models/ledger.py::ProjectFundTransaction` | Append-only ledger; budget ceiling constraint |
| **RSPC-CFR-06** | Fund Requisition and Approvals | `services/` | `services/finance.py::request_fund_disbursement` | Verifies available budget head balance before debit |
| **RSPC-CFR-07** | Project Staff Appointment Workflow | `services/` | `services/staff.py::create_appointment_request` | Checks active project lifecycle and manpower head |
| **RSPC-CFR-08** | Procurement Requisition Tracking | `services/` | `services/procurement.py::create_procurement_item` | Checks consumable/equipment head allocations |
| **RSPC-CFR-09** | Progress and Utilization Reporting | `models/` | `models/report.py::ProgressReport` | Verification of periodic reports and UC certificates |
| **RSPC-CFR-10** | Extension and Revision Handling | `domain/` | `domain/state_machine.py::ExtensionStateMachine` | Enforces deadline and justification invariants |
| **RSPC-CFR-11** | Project Closure and NOC Protocol | `domain/` | `domain/state_machine.py::ClosureStateMachine` | Requires zero open fund requisitions and final UC |
| **RSPC-CFR-12** | Audit Trail and Event Logging | `models/` | `models/audit.py::RSPCEventLog` | Immutable event log with principal user_id |
| **BR-RSPC-001** | Principal Investigator Eligibility | `domain/` | `domain/invariants.py::validate_pi_eligibility` | Only regular faculty with active tenure may be PI |
| **BR-RSPC-002** | Institutional Overhead Computation | `domain/` | `domain/calculations.py::calculate_overheads` | Overheads must match funding agency guidelines |
| **BR-RSPC-003** | Budget Head Deficit Prohibition | `models/` | `models/ledger.py::CheckConstraint` | Available balance in any head must remain >= 0 |
| **BR-RSPC-004** | Dual Role Approval Prohibition | `domain/` | `domain/state_machine.py::guard_no_self_approval` | PI cannot approve their own proposal as HoD/Dean |
| **BR-RSPC-005** | Project Extension Limits | `domain/` | `domain/invariants.py::validate_extension_duration` | Cumulative extension cannot exceed 12 months without Director |
| **BR-RSPC-006** | Append-Only Financial Transactions | `models/` | `models/ledger.py::ProjectFundTransaction` | No UPDATE/DELETE on ledger entries; corrections via reversal |
| **RSPC-UC-001** | View Own Project Portfolio | `selectors/` | `selectors/scoping.py::get_faculty_projects` | Filtered by PI/Co-PI user_id |
| **RSPC-UC-002** | Submit Research Proposal | `services/` | `services/proposal.py::submit_proposal` | Validates completeness and dispatches HoD review |
| **RSPC-UC-003** | Endorse Proposal as HoD | `services/` | `services/proposal.py::endorse_proposal` | Transition from SUBMITTED_HOD to ENDORSED_HOD |
| **RSPC-UC-004** | Approve Proposal as Dean-RSPC | `services/` | `services/proposal.py::approve_proposal` | Transition from ENDORSED_HOD to APPROVED_DEAN |
| **RSPC-UC-005** | Track Financial Ledger and Disburse | `selectors/` | `selectors/finance.py::get_project_ledger` | Ledger breakdown by budget heads |
| **BW-RSPC-01**  | Proposal Formulation to Approval | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Multi-step sequential gate |
| **BW-RSPC-02**  | Project Sanction to Operational | `domain/` | `domain/state_machine.py::ProjectLifecycleStateMachine` | Activation gate upon fund receipt |
| **BW-RSPC-03**  | Fund Disbursement and Accounting | `domain/` | `domain/state_machine.py::FundRequestStateMachine` | Balance verification -> approval -> disbursement |
| **BW-RSPC-04**  | Project Closure and Clearance | `domain/` | `domain/state_machine.py::ClosureStateMachine` | Submission -> Financial Audit -> Final Closure |

---

## Step 3.2 (b) — Domain Model

All identity references are plain integer `user_id`s in compliance with ADR-0002 and Step 2.3.

### 1. Proposal (`models/proposal.py`)
- `id` (BigAutoField, PK)
- `proposal_type` (CharField: SPONSORED_RESEARCH, CONSULTANCY)
- `title` (CharField, max_length=255)
- `pi_user_id` (BigIntegerField, indexed)
- `department` (CharField, max_length=64)
- `funding_agency` (CharField, max_length=128)
- `proposed_budget` (DecimalField, max_digits=14, decimal_places=2)
- `overhead_amount` (DecimalField, max_digits=12, decimal_places=2)
- `submission_deadline` (DateField)
- `status` (CharField: DRAFT, SUBMITTED_HOD, ENDORSED_HOD, APPROVED_DEAN, REJECTED, REVISION_REQUESTED)
- `created_at`, `updated_at` (DateTimeField)
- **Constraints:**
  - `CheckConstraint(check=Q(proposed_budget__gt=0), name="proposal_budget_positive")`

### 2. Project (`models/project.py`)
- `id` (BigAutoField, PK)
- `project_code` (CharField, unique, max_length=64) — e.g., `RSPC/2026/EE/001`
- `project_type` (CharField: SPONSORED, CONSULTANCY)
- `title` (CharField, max_length=255)
- `pi_user_id` (BigIntegerField, indexed)
- `department` (CharField, max_length=64)
- `funding_agency` (CharField, max_length=128)
- `sanction_order_no` (CharField, max_length=128)
- `sanction_date` (DateField)
- `start_date` (DateField)
- `end_date` (DateField)
- `sanctioned_amount` (DecimalField, max_digits=14, decimal_places=2)
- `status` (CharField: SANCTIONED, ACTIVE, EXTENSION_REQUESTED, CLOSURE_PENDING, CLOSED, TERMINATED)
- **Constraints:**
  - `CheckConstraint(check=Q(end_date__gte=F("start_date")), name="project_end_after_start")`
  - `CheckConstraint(check=Q(sanctioned_amount__gt=0), name="project_amount_positive")`

### 3. ProjectBudgetHead (`models/budget.py`)
- `id` (BigAutoField, PK)
- `project` (ForeignKey to Project, on_delete=CASCADE, related_name="budget_heads")
- `head_type` (CharField: EQUIPMENT, CONSUMABLES, MANPOWER, TRAVEL, CONTINGENCY, OVERHEADS)
- `allocated_amount` (DecimalField, max_digits=14, decimal_places=2)
- `spent_amount` (DecimalField, max_digits=14, decimal_places=2, default=0)
- `committed_amount` (DecimalField, max_digits=14, decimal_places=2, default=0)
- **Constraints:**
  - `UniqueConstraint(fields=["project", "head_type"], name="unique_project_head")`
  - `CheckConstraint(check=Q(allocated_amount__gte=0), name="budget_allocated_non_negative")`
  - `CheckConstraint(check=Q(spent_amount__gte=0), name="budget_spent_non_negative")`

### 4. ProjectFundTransaction (`models/ledger.py`)
- `id` (BigAutoField, PK)
- `project` (ForeignKey to Project, on_delete=PROTECT)
- `budget_head` (ForeignKey to ProjectBudgetHead, on_delete=PROTECT)
- `transaction_type` (CharField: ALLOCATION, DISBURSEMENT, REVERSAL)
- `amount` (DecimalField, max_digits=14, decimal_places=2)
- `reference_no` (CharField, max_length=128)
- `description` (TextField)
- `created_by_user_id` (BigIntegerField)
- `created_at` (DateTimeField, auto_now_add=True)
- **Append-only ledger:** No UPDATE or DELETE permitted at service or model layer.

### 5. ProjectExtensionRequest (`models/extension.py`)
- `id` (BigAutoField, PK)
- `project` (ForeignKey to Project, on_delete=CASCADE)
- `requested_end_date` (DateField)
- `months_requested` (PositiveIntegerField)
- `justification` (TextField)
- `status` (CharField: SUBMITTED, HOD_RECOMMENDED, DEAN_APPROVED, REJECTED)
- `reviewed_by_user_id` (BigIntegerField, null=True)

### 6. ProjectClosureRequest (`models/closure.py`)
- `id` (BigAutoField, PK)
- `project` (OneToOneField to Project, on_delete=CASCADE)
- `utilization_certificate_submitted` (BooleanField, default=False)
- `completion_report_submitted` (BooleanField, default=False)
- `unspent_balance_refunded` (BooleanField, default=False)
- `noc_status` (CharField: PENDING, APPROVED, REJECTED)
- `closed_at` (DateTimeField, null=True)

---

## Step 3.3 (c) — State Machine

Declarative state transitions ensuring illegal transitions are structurally impossible.

```python
# Declarative State Machine Tables
PROPOSAL_TRANSITIONS = {
    ("DRAFT", "submit", "faculty"): "SUBMITTED_HOD",
    ("SUBMITTED_HOD", "endorse", "hod"): "ENDORSED_HOD",
    ("SUBMITTED_HOD", "request_revision", "hod"): "REVISION_REQUESTED",
    ("REVISION_REQUESTED", "resubmit", "faculty"): "SUBMITTED_HOD",
    ("SUBMITTED_HOD", "reject", "hod"): "REJECTED",
    ("ENDORSED_HOD", "approve", "dean"): "APPROVED_DEAN",
    ("ENDORSED_HOD", "reject", "dean"): "REJECTED",
}

PROJECT_TRANSITIONS = {
    ("SANCTIONED", "activate", "rspc_admin"): "ACTIVE",
    ("ACTIVE", "request_extension", "faculty"): "EXTENSION_REQUESTED",
    ("EXTENSION_REQUESTED", "grant_extension", "dean"): "ACTIVE",
    ("EXTENSION_REQUESTED", "reject_extension", "dean"): "ACTIVE",
    ("ACTIVE", "initiate_closure", "faculty"): "CLOSURE_PENDING",
    ("CLOSURE_PENDING", "approve_closure", "dean"): "CLOSED",
    ("ACTIVE", "terminate", "dean"): "TERMINATED",
}
```

---

## Step 3.4 (d) — Permission List

The exact content for `modules/rspc/registry.py`:

```python
MODULE = {
    "code": "rspc",
    "label": "Research and Consultancy",
    "icon": "FolderGit2",
    "base_path": "/rspc",
    "nav_section": "Research",
    "sort_order": 25,
    "status": "active",
}

PERMISSIONS = [
    # Proposals
    "rspc.proposal.create",
    "rspc.proposal.view",
    "rspc.proposal.endorse",
    "rspc.proposal.approve",
    
    # Projects
    "rspc.project.create",
    "rspc.project.view",
    "rspc.project.manage",
    
    # Financials and Disbursements
    "rspc.fund.request",
    "rspc.fund.approve",
    "rspc.fund.view",
    
    # Extensions and Closures
    "rspc.extension.request",
    "rspc.extension.approve",
    "rspc.closure.request",
    "rspc.closure.approve",
    
    # Reporting
    "rspc.report.view",
]

SYSTEM_PERMISSIONS = [
    "rspc.schedule.check_deadlines",
]

SCOPE_PERMISSIONS = [
    "rspc.project.view",
    "rspc.proposal.view",
]

ROLE_GRANTS = {
    "faculty": [
        "rspc.proposal.create",
        "rspc.proposal.view",
        "rspc.project.view",
        "rspc.fund.request",
        "rspc.fund.view",
        "rspc.extension.request",
        "rspc.closure.request",
    ],
    "Head of Department": [
        "rspc.proposal.view",
        "rspc.proposal.endorse",
        "rspc.project.view",
        "rspc.fund.view",
        "rspc.report.view",
    ],
    "Dean (RSPC)": [
        "rspc.proposal.view",
        "rspc.proposal.approve",
        "rspc.project.create",
        "rspc.project.view",
        "rspc.project.manage",
        "rspc.fund.view",
        "rspc.fund.approve",
        "rspc.extension.approve",
        "rspc.closure.approve",
        "rspc.report.view",
    ],
    "Director": [
        "rspc.proposal.view",
        "rspc.project.view",
        "rspc.report.view",
        "rspc.closure.approve",
    ],
    "admin": [
        "rspc.project.create",
        "rspc.project.view",
        "rspc.project.manage",
        "rspc.fund.view",
        "rspc.report.view",
    ],
}
```

---

## Step 3.5 (e) — Endpoint List

All endpoints live under `/api/v1/rspc/`:

| Method | Path | Required Permission | What it returns | Rules Enforced |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/rspc/proposals/` | `rspc.proposal.view` | List of proposals (scoped by role) | Scoping rule |
| `POST` | `/api/v1/rspc/proposals/` | `rspc.proposal.create` | Created Proposal DTO | `BR-RSPC-001`, `BR-RSPC-002` |
| `GET` | `/api/v1/rspc/proposals/{id}/` | `rspc.proposal.view` | Proposal Detail DTO | Scoping rule |
| `POST` | `/api/v1/rspc/proposals/{id}/endorse/` | `rspc.proposal.endorse` | Updated Proposal DTO | `BR-RSPC-004` (No self-approval) |
| `POST` | `/api/v1/rspc/proposals/{id}/approve/` | `rspc.proposal.approve` | Updated Proposal DTO | `BR-RSPC-004` |
| `GET` | `/api/v1/rspc/projects/` | `rspc.project.view` | List of active/all projects | Scoping rule |
| `GET` | `/api/v1/rspc/projects/{id}/` | `rspc.project.view` | Project Details and Budget Summary | Scoping rule |
| `POST` | `/api/v1/rspc/projects/` | `rspc.project.create` | Created Project DTO | `BR-RSPC-001` |
| `GET` | `/api/v1/rspc/projects/{id}/ledger/` | `rspc.fund.view` | List of Ledger Transactions | `BR-RSPC-006` |
| `POST` | `/api/v1/rspc/projects/{id}/disburse/` | `rspc.fund.request` | Created Fund Transaction DTO | `BR-RSPC-003` (No deficit) |
| `POST` | `/api/v1/rspc/projects/{id}/extensions/` | `rspc.extension.request` | Created Extension Request DTO | `BR-RSPC-005` |
| `POST` | `/api/v1/rspc/projects/{id}/closure/` | `rspc.closure.request` | Created Closure Request DTO | `CFR-11` |

### Client Routes and Navigation

```typescript
// client/src/modules/rspc/routes.tsx
export const routes: RouteObject[] = [
  { path: "/rspc", element: <RspcDashboardPage /> },
  { path: "/rspc/proposals", element: <ProposalsListPage /> },
  { path: "/rspc/projects", element: <ProjectsListPage /> },
  { path: "/rspc/finance", element: <FinanceLedgerPage /> },
];
```

Nav Items:
- Dashboard: `RequirePermission(rspc.project.view)`
- My Proposals: `RequirePermission(rspc.proposal.view)`
- Sponsored Projects: `RequirePermission(rspc.project.view)`
- Financial Ledger: `RequirePermission(rspc.fund.view)`

---

## Step 3.6 (f) — Public Contracts

File: `modules/rspc/contracts.py`

```python
"""RSPC module public contracts surface. Plural signatures only."""
from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass

@dataclass(frozen=True)
class FacultyProjectSummaryDTO:
    user_id: int
    active_project_count: int
    total_sanctioned_amount: float

def get_faculty_project_summaries(user_ids: Sequence[int]) -> dict[int, FacultyProjectSummaryDTO]:
    """Return project count and grant volume for a sequence of faculty user IDs."""
    ...
```

---

## Step 3.7 (g) — Scheduled Work

File: `modules/rspc/schedule.py`

```python
"""Celery beat scheduled tasks for RSPC."""
SCHEDULE = {
    "rspc-check-project-deadlines": {
        "task": "modules.rspc.tasks.check_project_deadlines",
        "schedule": 86400.0, # Daily at midnight
    },
}
```

---

## Step 3.8 (h) — Open Questions and Approvals

1. **Role Mapping:** Mapped to Fusion designations `"faculty"`, `"Head of Department"`, `"Dean (RSPC)"`, and `"Director"`.
2. **Ledger Integrity:** Implemented strictly via append-only rows in `ProjectFundTransaction`.
3. **Approval Status:** Written and staged for Student 2 review and written sign-off.
