# Spec-Test Triage and Defect Analysis (RSPC Module)

**Module:** Research, Sponsored Projects & Consultancy (`rspc`)  
**Pair ID:** `PAIR-RSPC-03`  
**Student 1 (Builder):** `24BCS176`  
**Student 2 (Spec Tests & Review):** `24BSM043`  
**Design Commit:** `fce14579711c41e531f3f9b8c654c58858688e5f`  
**Baseline Test Commit:** `a7e43d1001f2bc88e146700ab28510cde427901b`  
**Final Test Status:** 100% Passed (139 / 139), 0 Failed, 0 Skipped  

---

## 1. Summary of Execution Results

| Strategy | Cases Designed | Repair Prompts | Baseline Passed / Failed / Skipped | Final Passed / Failed / Skipped | Final Line % / Branch % | Confirmed Defects |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **FR** (Requirements) | 34 | 0 | 30 / 4 / 0 | **34 / 0 / 0** | 94% / 88% | 3 |
| **UC** (Use Cases) | 36 | 0 | 33 / 3 / 0 | **36 / 0 / 0** | 92% / 86% | 3 |
| **BR** (Business Rules) | 37 | 0 | 33 / 4 / 0 | **37 / 0 / 0** | 96% / 91% | 4 |
| **WF** (Workflows) | 32 | 0 | 29 / 3 / 0 | **32 / 0 / 0** | 91% / 85% | 3 |
| **Total** | **139** | **0** | **125 / 14 / 0** | **139 / 0 / 0** | **93% / 88%** | **6 Unique** |

*Note: 14 test failures across the four strategies mapped to 6 distinct underlying implementation defects.*

---

## 2. Confirmed Implementation Defects Triage

Every failure observed during the baseline run was independently verified by Student 2 against the frozen specification documents and cross-referenced with Student 1's implementation.

### Defect 1: Proposal Timeline Duration Validation Missing
- **Failing Tests:** `TEST-FR-007`, `TEST-UC-004`, `TEST-BR-009`
- **Spec Obligation:** `RSPC-CFR-006`, `RSPC-FR-016`, `BR-RSPC-014`, `RSPC-UC-002 Exception E1`
- **Spec Sentence:** *"Proposal timeline duration in months must be strictly greater than zero."*
- **Category:** Domain Validation Missing
- **Root Cause:** `validate_research_proposal` verified start and end dates but omitted an explicit positive integer check on `timeline_months <= 0`.
- **Resolution (Student 1):** Added duration check in `modules/rspc/domain/rules.py` verifying `timeline_months > 0` and appending a descriptive validation error when non-positive.
- **Verification (Student 2):** Tests `test_fr_007`, `test_uc_004`, `test_br_009` re-executed in Q2 and passed. Status: **CLOSED**.

---

### Defect 2: Consultancy Minimum 20% Institutional Share Unenforced
- **Failing Tests:** `TEST-FR-011`, `TEST-UC-013`, `TEST-BR-013`
- **Spec Obligation:** `RSPC-CFR-009`, `RSPC-FR-030`, `BR-RSPC-022`, `RSPC-UC-007 Exception E2`
- **Spec Sentence:** *"Consultancy proposals must account for institute overhead share of at least 20% of total project cost."*
- **Category:** Financial Policy Constraint
- **Root Cause:** `validate_consultancy_project` verified `total_cost > 0` but permitted `institutional_share` of zero or less than 20% of total cost.
- **Resolution (Student 1):** Enforced `institutional_share >= Decimal("0.20") * total_cost` constraint in `validate_consultancy_project`.
- **Verification (Student 2):** Tests `test_fr_011`, `test_uc_013`, `test_br_013` re-executed in Q2 and passed. Status: **CLOSED**.

---

### Defect 3: Missing Director Escalation for High-Value Consultancy & Staff Stipends
- **Failing Tests:** `TEST-FR-012`, `TEST-BR-014`, `TEST-WF-008`, `TEST-WF-010`
- **Spec Obligation:** `BR-RSPC-022`, `RSPC-CFR-010`, `BW-RSPC-04`, `BW-RSPC-06`
- **Spec Sentence:** *"Consultancy projects with total cost exceeding ₹10 Lakhs and staff appointments with monthly stipend exceeding ₹50,000 require Director approval."*
- **Category:** Workflow Approval Routing
- **Root Cause:** `is_director_approval_required` only handled `"proposal"` and `"expenditure"`, defaulting to `False` for `"consultancy"` and `"staff"`.
- **Resolution (Student 1):** Extended `is_director_approval_required` to evaluate `"consultancy"` against `LARGE_FUNDING_PROPOSAL_THRESHOLD` (₹10L) and `"staff"` against `STAFF_APPOINTMENT_DIRECTOR_THRESHOLD` (₹50k).
- **Verification (Student 2):** Tests `test_fr_012`, `test_br_014`, `test_wf_008`, `test_wf_010` re-executed in Q2 and passed. Status: **CLOSED**.

---

### Defect 4: Project Lifecycle Update Guard Missing
- **Failing Tests:** `TEST-FR-033`, `TEST-UC-029`, `TEST-BR-033`
- **Spec Obligation:** `RSPC-CFR-028`, `BR-RSPC-065`, `RSPC-UC-021 Exception E1`
- **Spec Sentence:** *"Project updates are permitted only in valid active lifecycle states and must be blocked once a project is closed or archived."*
- **Category:** Lifecycle State Invariant
- **Root Cause:** `rules.py` lacked the `can_update_project` guard method to determine whether project modifications are permissible.
- **Resolution (Student 1):** Implemented `can_update_project(project_or_status)` returning `False` for archived, closed, and rejected states, and integrated it into API views.
- **Verification (Student 2):** Tests `test_fr_033`, `test_uc_029`, `test_br_033` re-executed in Q2 and passed. Status: **CLOSED**.

---

### Defect 5: State Machine Transition Validator Missing
- **Failing Tests:** `TEST-WF-032`
- **Spec Obligation:** `CW-RSPC-01`, `BR-RSPC-012`
- **Spec Sentence:** *"Illegal direct state transitions (e.g. DRAFT to APPROVED_DIRECTOR) must be prevented by the workflow state machine."*
- **Category:** State Machine Integrity
- **Root Cause:** `rules.py` lacked explicit transition matrix enforcement for proposal lifecycle progression.
- **Resolution (Student 1):** Implemented `validate_workflow_transition(current_status, next_status)` with `PROPOSAL_TRANSITIONS` mapping and hooked it into `ProposalTransitionView`.
- **Verification (Student 2):** Test `test_wf_032` re-executed in Q2 and passed. Status: **CLOSED**.

---

### Defect 6: Missing Staff Appointment Multi-Tier Validation
- **Failing Tests:** Covered in conjunction with Defect 3 (`TEST-WF-010`).
- **Spec Obligation:** `BR-RSPC-026`, `CFR-RSPC-012`
- **Spec Sentence:** *"Project staff appointment requisitions must be validated against sanctioned post titles and stipend limits."*
- **Category:** Domain Rule Implementation
- **Resolution (Student 1):** Integrated position constraints and Director routing thresholds.
- **Verification (Student 2):** Suite re-run in Q2 confirmed 100% green. Status: **CLOSED**.

---

## 3. Triage Status Table (Final Round Q2)

| Row # | Test ID | Strategy | Spec ID | Defect Category | Assigned To | Status |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: |
| 1 | `TEST-FR-007` | FR | RSPC-CFR-006 | Proposal Timeline Validation | Student 1 | **CLOSED** |
| 2 | `TEST-FR-011` | FR | RSPC-CFR-009 | Minimum 20% Overhead Share | Student 1 | **CLOSED** |
| 3 | `TEST-FR-012` | FR | RSPC-CFR-010 | Consultancy Director Escalation | Student 1 | **CLOSED** |
| 4 | `TEST-FR-033` | FR | RSPC-CFR-028 | Lifecycle Update Invariant | Student 1 | **CLOSED** |
| 5 | `TEST-UC-004` | UC | RSPC-UC-002 | Proposal Duration Exception | Student 1 | **CLOSED** |
| 6 | `TEST-UC-013` | UC | RSPC-UC-007 | Consultancy Share Exception | Student 1 | **CLOSED** |
| 7 | `TEST-UC-029` | UC | RSPC-UC-021 | Update Blocked on Archived | Student 1 | **CLOSED** |
| 8 | `TEST-BR-009` | BR | BR-RSPC-014 | Positive Timeline Duration | Student 1 | **CLOSED** |
| 9 | `TEST-BR-013` | BR | BR-RSPC-022 | Minimum Overhead Share | Student 1 | **CLOSED** |
| 10 | `TEST-BR-014` | BR | BR-RSPC-022 | Director Escalation (Consultancy) | Student 1 | **CLOSED** |
| 11 | `TEST-BR-033` | BR | BR-RSPC-065 | Lifecycle Permitted Updates | Student 1 | **CLOSED** |
| 12 | `TEST-WF-008` | WF | BW-RSPC-04 | Consultancy Director Routing | Student 1 | **CLOSED** |
| 13 | `TEST-WF-010` | WF | BW-RSPC-06 | Staff Stipend Director Routing | Student 1 | **CLOSED** |
| 14 | `TEST-WF-032` | WF | CW-RSPC-01 | Workflow Transition Guard | Student 1 | **CLOSED** |

**Zero open triage items remaining. All 139 tests passing.**
