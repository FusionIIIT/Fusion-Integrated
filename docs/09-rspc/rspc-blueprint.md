# RSPC Module Architecture Blueprint (Step 3)

**Module Name:** Research, Sponsored Projects & Consultancy (RSPC)  
**Module Code:** `rspc`  
**Folder / NN:** `docs/09-rspc/`  
**Spec ID Prefix:** `RSPC-` (BR-RSPC-, CFR-RSPC-, UC-RSPC-, CW-RSPC-, BW-RSPC-)  
**Environment:** Module-only (Django + Vite/React + Postgres + Redis)  
**Authors:** Student 1 (`24BCS176`) & Student 2 (`24BSM043`)  
**Pair ID:** `PAIR-RSPC-03`  
**Approval Status:** Approved by Student 2 (`24BSM043`) on 2026-11-22  

---

## 3.1 Traceability Table

The table below maps each specification requirement (Problem Statement, Business Rules, Use Cases, Core Functional Requirements, and Workflows) to its database model, API endpoint, client view, and permission code.

| Spec ID | Requirement / Rule Name | DB Model / Entity | Backend API Endpoint | Client Route | Permission Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CFR-RSPC-001** | Research & Consultancy Directory | `ResearchProposal`, `ConsultancyProject` | `GET /api/v1/rspc/proposals`, `GET /api/v1/rspc/consultancies` | `/rspc/proposals`, `/rspc/consultancy` | `rspc.proposal.view`, `rspc.consultancy.view` |
| **CFR-RSPC-006** | Research Proposal Submission | `ResearchProposal` | `POST /api/v1/rspc/proposals` | `/rspc/proposals` | `rspc.proposal.submit` |
| **CFR-RSPC-007** | Multi-Tier Proposal Review & Approval | `ResearchProposal`, `RSPCAuditTrail` | `POST /api/v1/rspc/proposals/{id}/transition` | `/rspc/proposals` | `rspc.proposal.recommend_hod`, `rspc.proposal.verify_admin`, `rspc.proposal.approve_dean` |
| **CFR-RSPC-009** | Consultancy Registration & Overhead | `ConsultancyProject` | `POST /api/v1/rspc/consultancies` | `/rspc/consultancy` | `rspc.consultancy.register` |
| **CFR-RSPC-010** | Consultancy Approval Workflow | `ConsultancyProject`, `RSPCAuditTrail` | `PATCH /api/v1/rspc/consultancies/{id}` | `/rspc/consultancy` | `rspc.consultancy.recommend_hod`, `rspc.consultancy.approve_dean` |
| **CFR-RSPC-012** | Project Staff Appointment | `ProjectStaffAppointment` | `POST /api/v1/rspc/staff`, `GET /api/v1/rspc/staff` | `/rspc/proposals` | `rspc.staff.request`, `rspc.staff.manage` |
| **CFR-RSPC-015** | Fund Utilization / Expenditure Request | `FinancialRequest` | `POST /api/v1/rspc/financial` | `/rspc/financial` | `rspc.financial.request` |
| **CFR-RSPC-016** | Financial Sanction Approval Delegation | `FinancialRequest`, `RSPCAuditTrail` | `PATCH /api/v1/rspc/financial/{id}` | `/rspc/financial` | `rspc.financial.approve_dean`, `rspc.financial.authorize_director` |
| **CFR-RSPC-017** | Equipment / Consumables Procurement | `ProcurementRequest` | `POST /api/v1/rspc/procurement` | `/rspc/financial` | `rspc.procurement.request`, `rspc.procurement.approve` |
| **CFR-RSPC-018** | Periodic Progress & Utilization Reports | `ProgressReport` | `POST /api/v1/rspc/reports` | `/rspc/reports` | `rspc.report.submit` |
| **CFR-RSPC-020** | Project Closure & Archival Processing | `ProjectClosure` | `POST /api/v1/rspc/closures` | `/rspc/reports` | `rspc.closure.submit`, `rspc.closure.approve` |
| **CFR-RSPC-021** | Notifications & Event Alerts | `RSPCNotification` | Internal domain event dispatch | Shell Header | System internal |
| **CFR-RSPC-022** | Audit Trail & Compliance Logging | `RSPCAuditTrail` | `GET /api/v1/rspc/audit` | `/rspc/reports` | `rspc.audit.view` |
| **BR-RSPC-004** | Strategic Proposal Director Escalation | `ResearchProposal` | `POST /api/v1/rspc/proposals/{id}/transition` | `/rspc/proposals` | `rspc.proposal.authorize_director` |
| **BR-RSPC-005** | Large Funding Threshold (≥ 10 Lakhs) | `ResearchProposal` | `POST /api/v1/rspc/proposals/{id}/transition` | `/rspc/proposals` | `rspc.proposal.authorize_director` |
| **BR-RSPC-006** | High-Value Expenditure (≥ 2 Lakhs) | `FinancialRequest` | `PATCH /api/v1/rspc/financial/{id}` | `/rspc/financial` | `rspc.financial.authorize_director` |
| **BR-RSPC-013** | Mandatory Proposal Fields Validation | Pure Domain Rule | `validate_research_proposal` | `/rspc/proposals` | `rspc.proposal.submit` |
| **BR-RSPC-014** | Positive Timeline Duration (months > 0) | Pure Domain Rule | `validate_research_proposal` | `/rspc/proposals` | `rspc.proposal.submit` |
| **BR-RSPC-022** | Minimum 20% Institutional Overhead | Pure Domain Rule | `validate_consultancy_project` | `/rspc/consultancy` | `rspc.consultancy.register` |
| **BR-RSPC-032** | Dean Delegation Limit (2 Lakhs) | Pure Domain Rule | `validate_financial_request` | `/rspc/financial` | `rspc.financial.approve_dean` |
| **BR-RSPC-035** | Procurement Within Budget Constraint | Pure Domain Rule | `validate_procurement_request` | `/rspc/financial` | `rspc.procurement.request` |
| **BR-RSPC-043** | Settlement Prior to Archival Constraint | Pure Domain Rule | `validate_project_closure` | `/rspc/reports` | `rspc.closure.approve` |
| **BR-RSPC-065** | Lifecycle Permitted Updates Restriction | Pure Domain Rule | `can_update_project` | All endpoints | All roles |
| **CW-RSPC-01** | Proposal Workflow State Machine Guard | Pure Domain Rule | `validate_workflow_transition` | `/rspc/proposals` | All approval roles |

---

## 3.2 Domain Model & Relational Boundaries

In compliance with **ADR-0013** (No cross-module foreign keys):
- All references to users, actors, or external resources use plain integer identifiers (`pi_id`, `requested_by_id`, `actor_id`, `recipient_id`).
- All cross-module identity and directory resolution happens through `modules.directory` contracts or the IAM client (`fusion_auth.client`).
- Relational integrity within the RSPC domain is strictly enforced through indexed lookup fields and status tracking.

### Entity Overview
1. **ResearchProposal** (`rspc_research_proposal`): Core research project proposals with timeline, sanctioned budget, and approval status.
2. **ConsultancyProject** (`rspc_consultancy_project`): Industrial and government consultancy agreements with client details, deliverables, total cost, and institutional overhead share.
3. **ProjectStaffAppointment** (`rspc_staff_appointment`): Research personnel appointments (JRF, SRF, Project Assistant) linked to projects.
4. **FinancialRequest** (`rspc_financial_request`): Fund utilization, travel, and expenditure requests against sanctioned project budgets.
5. **ProcurementRequest** (`rspc_procurement_request`): Equipment and consumable acquisition requests.
6. **ProgressReport** (`rspc_progress_report`): Periodic technical and financial utilization reports submitted by PIs.
7. **ProjectClosure** (`rspc_project_closure`): Terminal completion, asset transfer declaration, and financial settlement records.
8. **RSPCAuditTrail** (`rspc_audit_trail`): Immutable operational log recording all review decisions, comments, and actors.
9. **RSPCNotification** (`rspc_notification`): System event alerts for review actions, approvals, and reminders.

---

## 3.3 State Machines

### Research Proposal Lifecycle (`CW-RSPC-01`, `BR-RSPC-012`)
```
[DRAFT]
   │ (submit)
   ▼
[SUBMITTED_HOD] ──────────► [REJECTED_HOD] ──► [DRAFT]
   │ (recommend)
   ▼
[RECOMMENDED_HOD]
   │ (verify)
   ▼
[VERIFIED_ADMIN] ─────────► [REJECTED_ADMIN] ──► [DRAFT]
   │
   ├─► (budget < 10L, Dean approves) ──► [APPROVED_DEAN] ──► [ARCHIVED / CLOSED]
   ├─► (budget < 10L, Dean rejects)  ──► [REJECTED_DEAN] ──► [DRAFT]
   └─► (budget ≥ 10L or strategic)   ──► [FORWARDED_DIRECTOR]
                                              │
                                              ├─► (Director approves) ──► [APPROVED_DIRECTOR] ──► [ARCHIVED / CLOSED]
                                              └─► (Director rejects)  ──► [REJECTED_DIRECTOR] ──► [DRAFT]
```

### Consultancy Project Lifecycle (`BR-RSPC-022`)
```
[DRAFT] ──► [SUBMITTED_HOD] ──► [RECOMMENDED_HOD] ──► [VERIFIED_ADMIN]
                                                            │
                                                            ├─► [APPROVED_DEAN] (cost < 10L)
                                                            └─► [FORWARDED_DIRECTOR] ──► [APPROVED_DIRECTOR] (cost ≥ 10L)
```

---

## 3.4 Permissions Catalog & Role Grants

Registered in `modules/rspc/registry.py` and synced into IAM:

| Permission Code | Description | Role Grants |
| :--- | :--- | :--- |
| `rspc.proposal.view` | View proposals and directories | Faculty, HoD, RSPC Admin, Dean RSPC, Director |
| `rspc.proposal.submit` | Draft and submit new proposals | Faculty, HoD |
| `rspc.proposal.recommend_hod` | HoD endorsement / rejection | HoD |
| `rspc.proposal.verify_admin` | Administrative compliance verification | RSPC Admin, Dean RSPC, Director |
| `rspc.proposal.approve_dean` | Dean financial and administrative sanction | Dean RSPC, Director |
| `rspc.proposal.authorize_director`| Director authorization for high-value / strategic projects | Director |
| `rspc.consultancy.view` | View consultancy projects | Faculty, HoD, RSPC Admin, Dean RSPC, Director |
| `rspc.consultancy.register` | Register new consultancy contracts | Faculty, HoD |
| `rspc.consultancy.recommend_hod`| HoD recommendation for consultancy | HoD |
| `rspc.consultancy.approve_dean` | Dean approval for consultancy contracts | Dean RSPC, Director |
| `rspc.staff.request` | Create project staff requisition | Faculty, HoD |
| `rspc.staff.manage` | Process staff appointment candidates | RSPC Admin, Dean RSPC, Director |
| `rspc.financial.request` | Create expenditure / advance request | Faculty, HoD |
| `rspc.financial.verify` | Administrative budget audit | RSPC Admin, Dean RSPC, Director |
| `rspc.financial.approve_dean` | Dean financial approval (within 2 Lakhs) | Dean RSPC, Director |
| `rspc.financial.authorize_director`| Director expenditure authorization (≥ 2 Lakhs) | Director |
| `rspc.procurement.request` | Create equipment procurement request | Faculty, HoD, RSPC Admin |
| `rspc.procurement.approve` | Approve procurement requisitions | Dean RSPC, Director |
| `rspc.report.submit` | Submit periodic progress / utilization report | Faculty, HoD, RSPC Admin |
| `rspc.closure.submit` | Initiate formal project closure | Faculty, HoD |
| `rspc.closure.approve` | Final closure and archival authorization | RSPC Admin, Dean RSPC, Director |
| `rspc.audit.view` | View compliance logs and decision remarks | RSPC Admin, Dean RSPC, Director |

---

## 3.5 API Endpoints & Route Guards

All endpoints are mounted under `/api/v1/rspc/` and enforced via `HasModuleGrant("rspc")` and `HasPermission(...)`.

| Method | Endpoint | Purpose | Required Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/rspc/proposals` | List proposals | `rspc.proposal.view` |
| `POST` | `/api/v1/rspc/proposals` | Create / submit proposal | `rspc.proposal.submit` |
| `GET` | `/api/v1/rspc/proposals/{id}` | Retrieve proposal detail | `rspc.proposal.view` |
| `PATCH`| `/api/v1/rspc/proposals/{id}` | Update proposal (if active) | `rspc.proposal.submit` |
| `POST` | `/api/v1/rspc/proposals/{id}/transition`| Advance proposal lifecycle | `rspc.proposal.view` (role-checked) |
| `GET` | `/api/v1/rspc/consultancies` | List consultancy projects | `rspc.consultancy.view` |
| `POST` | `/api/v1/rspc/consultancies` | Register consultancy | `rspc.consultancy.register` |
| `GET` | `/api/v1/rspc/consultancies/{id}` | Retrieve consultancy detail | `rspc.consultancy.view` |
| `PATCH`| `/api/v1/rspc/consultancies/{id}` | Update consultancy | `rspc.consultancy.register` |
| `GET` | `/api/v1/rspc/staff` | List staff appointments | `rspc.staff.request` |
| `POST` | `/api/v1/rspc/staff` | Create staff requisition | `rspc.staff.request` |
| `GET` | `/api/v1/rspc/financial` | List financial requests | `rspc.financial.request` |
| `POST` | `/api/v1/rspc/financial` | Submit expenditure request | `rspc.financial.request` |
| `GET` | `/api/v1/rspc/procurement` | List procurement items | `rspc.procurement.request` |
| `POST` | `/api/v1/rspc/procurement` | Submit procurement request | `rspc.procurement.request` |
| `GET` | `/api/v1/rspc/reports` | List progress reports | `rspc.report.submit` |
| `POST` | `/api/v1/rspc/reports` | Submit progress report | `rspc.report.submit` |
| `GET` | `/api/v1/rspc/closures` | List closure requests | `rspc.closure.submit` |
| `POST` | `/api/v1/rspc/closures` | Request project closure | `rspc.closure.submit` |
| `GET` | `/api/v1/rspc/audit` | View audit trail records | `rspc.audit.view` |

---

## 3.6 Cross-Module Contracts (ADR-0007)

Defined in `modules/rspc/contracts.py`. Complies strictly with plural getter conventions returning typed dataclasses:

1. `get_user_proposals(user_ids: Sequence[int]) -> dict[int, list[ResearchProposalContract]]`
2. `get_user_consultancies(user_ids: Sequence[int]) -> dict[int, list[ConsultancyProjectContract]]`
3. `get_proposals_by_ids(proposal_ids: Sequence[int]) -> dict[int, ResearchProposalContract | None]`

No external module directly queries RSPC database tables; all access uses these plural contract getters.

---

## 3.7 Migrations & Indexing

- Migration: `modules/rspc/migrations/0001_initial.py`
- Indices added for:
  - `ResearchProposal.status` (for dashboard filtering and lifecycle queries)
  - `ConsultancyProject.status`
  - `ProjectStaffAppointment.status`
  - `FinancialRequest.status`
  - `ProcurementRequest.status`
  - `ProjectClosure.status`
  - `RSPCAuditTrail.timestamp`
  - `RSPCNotification.recipient_id`

---

## 3.8 Open Questions & Approvals

1. **Overhead Calculation Policy:** Institutional overhead share for consultancies was clarified in BR-RSPC-022 to be a minimum of 20% of total project cost. Approved by Student 2.
2. **Approval Thresholds:** Director escalation threshold established at ₹10 Lakhs for proposals and consultancies, ₹2 Lakhs for financial expenditures and procurements, and ₹50,000 for staff appointments. Approved by Student 2.
3. **Blueprint Sign-Off:** Student 2 (`24BSM043`) formally reviewed and approved this blueprint on 2026-11-22 prior to production implementation.
