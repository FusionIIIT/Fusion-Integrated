# RSPC Module Blueprint (Research, Sponsored Projects and Consultancy)

**Module:** Research, Sponsored Projects and Consultancy (RSPC)  
**Module Code:** `rspc`  
**Docs Folder:** `docs/09-rspc/`  
**Specification Baseline:** v1.3 / v2.1 SYNCHRONIZED  
**Environment:** `module-only`  

---

## Step 3.1 (a) — Traceability Table

The RSPC specification contains 29 Coherent Functional Requirements (CFR), 126 Atomic Functional Requirements (AFR/FR), 29 Active Use Cases (UC), 38 Active Business Rules (BR), and 18 Workflows (12 Basis BW, 6 Composite CW).

| Id | What it requires | Layer it belongs in | Enforcement point | Notes |
|:---|:---|:---|:---|:---|
| **RSPC-CFR-001** | Proposal Creation and Submission | `services/` | `services/proposal.py::create_proposal` | Validates mandatory proposal metadata and budget heads |
| **RSPC-CFR-002** | Department Endorsement (HoD) | `services/` | `services/proposal.py::endorse_proposal` | Validates HoD role and transitions proposal |
| **RSPC-CFR-003** | Institutional Approval (Dean-RSPC) | `services/` | `services/proposal.py::approve_proposal` | Validates Dean role and records approval review |
| **RSPC-CFR-004** | Project Sanction and Registration | `services/` | `services/project.py::sanction_and_register_project` | Creates project instance with sanctioned amount and dates |
| **RSPC-CFR-005** | Financial Ledger and Head Allocation | `models/` | `models/ledger.py::ProjectFundTransaction` | Append-only ledger; budget allocation and disbursement rows |
| **RSPC-CFR-006** | Fund Requisition and Disbursement | `services/` | `services/finance.py::disburse_funds` | Verifies available budget head balance before debit |
| **RSPC-CFR-010** | Extension and Revision Handling | `services/` | `services/extension.py::request_project_extension` | Validates PI ownership and records requested timeline |
| **RSPC-CFR-011** | Project Closure Protocol | `services/` | `services/extension.py::approve_project_closure` | Updates project status to closed upon approval |
| **BR-RSPC-004** | Dean Routing Decision Gate | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Validates actor role for forward/approve/reject transitions |
| **BR-RSPC-013** | Mandatory Proposal Completeness on Submit | `services/` | `services/proposal.py::submit_proposal` | Rejects incomplete proposals with DomainError (422) |
| **BR-RSPC-014** | Institutional Overhead Policy Validation | `domain/` | `domain/invariants.py::calculate_institutional_overheads` | Overheads must match approved policy rate |
| **BR-RSPC-016** | Decision Remarks Recorded in Review | `models/` | `models/proposal.py::ProposalReview` | Records decision, comments, and reviewer user_id |
| **BR-RSPC-027** | Disbursement within Sanctioned Budget | `services/` | `services/finance.py::disburse_funds` | Ensures disbursement does not exceed available balance |
| **BR-RSPC-028** | Budget Deficit Prohibition | `domain/` | `domain/invariants.py::validate_disbursement` | Raises InvariantViolationError (422) on deficit attempt |
| **BR-RSPC-035** | Budget Head Positive Balance Invariant | `domain/` | `domain/invariants.py::validate_budget_head_positive` | Budget head allocations must be non-negative |
| **BR-RSPC-040** | Approved Closure Updates Project Lifecycle | `services/` | `services/extension.py::approve_project_closure` | Sets project status to closed |
| **BR-RSPC-041** | Pending Closure Keeps Project Active | `services/` | `services/extension.py::request_project_closure` | Marks closure_pending while project remains unarchived |
| **BR-RSPC-045** | Scoped Project Query Narrowing | `selectors/` | `selectors/scoping.py::scope_projects` | Narrows queryset by principal identity and role |
| **BR-RSPC-046** | Out-of-Scope Query Returns 404 | `selectors/` | `selectors/scoping.py::get_project_or_404` | Returns 404, never 403, preventing existence disclosure |
| **BR-RSPC-069** | Director Approval on Cumulative Extensions | `domain/` | `domain/invariants.py::validate_extension_request` | Extensions > 12 months require Director approval |
| **RSPC-UC-001** | View Own Project Portfolio | `selectors/` | `selectors/scoping.py::scope_projects` | Filtered by PI/Co-PI user_id or department |
| **RSPC-UC-002** | Submit Research Proposal | `services/` | `services/proposal.py::submit_proposal` | Validates completeness and dispatches HoD review |
| **RSPC-UC-003** | Endorse Proposal as HoD | `services/` | `services/proposal.py::endorse_proposal` | Transition from SUBMITTED_HOD to ENDORSED_HOD |
| **RSPC-UC-004** | Approve Proposal as Dean-RSPC | `services/` | `services/proposal.py::approve_proposal` | Transition from ENDORSED_HOD to APPROVED_DEAN |
| **RSPC-UC-005** | Track Financial Ledger and Heads | `services/` | `services/finance.py::allocate_budget_head` | Head allocations and balance tracking |
| **RSPC-UC-006** | Disburse Project Funds | `services/` | `services/finance.py::disburse_funds` | Verifies balance and writes append-only ledger transaction |
| **RSPC-UC-011** | Request Project Extension | `services/` | `services/extension.py::request_project_extension` | PI submits extension request with justification |
| **RSPC-UC-012** | Review Project Extension | `services/` | `services/extension.py::review_project_extension` | Dean/Director reviews and extends project end_date |
| **RSPC-UC-015** | Request and Approve Project Closure | `services/` | `services/extension.py::approve_project_closure` | Final closure transitions project to closed |
| **BW-RSPC-01**  | Proposal Formulation to Approval | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Multi-step sequential gate |
| **BW-RSPC-02**  | Project Sanction to Operational | `services/` | `services/project.py::sanction_and_register_project` | Sanction registration with budget heads |
| **BW-RSPC-03**  | Fund Disbursement and Accounting | `services/` | `services/finance.py::disburse_funds` | Balance verification -> ledger debit |
| **BW-RSPC-04**  | Project Closure and Clearance | `services/` | `services/extension.py::approve_project_closure` | Submission -> review -> final closure |
| **CW-RSPC-01**  | Composite Multi-stage Proposal Evaluation | `domain/` | `domain/state_machine.py::ProposalStateMachine` | Distinct outcome states for HoD and Dean stages |

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

## Step 3.8 (h) — Open Questions, Known Gaps, and Approvals

### 1. Architectural Alignment
1. **Role Mapping:** Mapped to Fusion designations `"faculty"`, `"Head of Department"`, `"Dean (RSPC)"`, and `"Director"`.
2. **Ledger Integrity:** Implemented strictly via append-only rows in `ProjectFundTransaction` with zero `UPDATE` or `DELETE` capabilities.
3. **Scoping Isolation:** Out-of-scope resources return 404 (NotFoundError), never 403, preventing existence disclosure.

### 2. Known Gaps (Deferred Features)
Per dimension 1 of the module review rubric, features deferred beyond the core research grant lifecycle are formally catalogued here:
- **Consultancy Project Lifecycle (UC-007, UC-008, BR-022, CW-02):** Consultancy formulation, dynamic client billing, and revenue share distributions are deferred to subsequent milestone.
- **Staff Appointment Workflows (UC-009, UC-010, UC-022, UC-023, BR-026, CW-03):** JRF/SRF/Project Assistant vacancy notifications, selection committee minutes, and payroll appointments are deferred.
- **Procurement Requisitions (UC-013, UC-025, UC-026, BR-035, BR-036, CW-05):** Central store equipment indent tracking and purchase approval workflows are deferred.
- **Progress and Utilization Reporting (UC-014, UC-017):** Complex periodic milestone progress reports and SE/UC generation beyond project status metrics are deferred.
- **Notification Services (UC-016, UC-031):** Email notifications and outbox queue dispatch are deferred.
- **Cross-Module Integrations (UC-029, UC-030):** Direct external funding agency sync protocols are deferred.
- **Administrative Stage Verification & Director Forwarding Routing:** RSPC-Admin pre-verification and multi-tier escalation beyond the core 12-month extension director threshold are deferred.

### 3. Approver Written Sign-off
> "Approved known gaps for initial release on 2026-11-22: The core RSPC lifecycle (proposal drafting, submission, HoD endorsement, Dean approval, project sanction, budget head allocation, append-only fund disbursement, project extension review, and closure) constitutes the complete viable baseline. Consultancy, staff appointments, procurement, and external agency integrations are accepted as deferred release gaps."
> — ruthvikgundelli (2026-11-22)
