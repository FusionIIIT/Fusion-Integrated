# Architectural Blueprint: Module 10 — Human Resource — Human Resource (HR-EIS)

## 1. Executive Summary & Specification Scope
- **Module Name:** Human Resource — Human Resource (HR-EIS)
- **Assigned Module:** Module 10
- **Module Code:** `eis`
- **Governing Baseline:** HR-EIS Problem Statement v1.2_SYNCHRONIZED, Requirements Registry v1.3_FINAL, Use Case Specs v1.3_FINAL, Business Rules v1.3_FINAL, Workflows v1.3_FINAL.
- **Reference Standard:** `modules/placement` architecture and quality conventions.

## 2. Domain Entities & Database Schema
1. **`EmployeeProfile`**: Central authoritative record for institute faculty and staff. Enforces BR-HR-003, BR-HR-004, BR-HR-005, BR-HR-006.
2. **`LeaveBalance` & `LeaveRequest`**: Enforces leave entitlement quotas, validation, approval hierarchies, and automatic deduction (BR-HR-007, BR-HR-008, BR-HR-009, BR-HR-010, BR-HR-011, BR-HR-034).
3. **`AppraisalCycle` & `AppraisalRecord`**: Annual appraisal cycles with strict window constraints, reviewer assignment, and immutable archival upon finalization (BR-HR-012, BR-HR-013, BR-HR-014, BR-HR-015).
4. **`LtcClaim` & `CpdaClaim`**: Financial entitlement advance and reimbursement processing with HR verification, authority approval, and accountant settlement (BR-HR-016, BR-HR-017, BR-HR-018, BR-HR-019, BR-HR-020, BR-HR-021, BR-HR-022, BR-HR-031, BR-HR-035).
5. **`AuditLog` & `NotificationRecord`**: Immutable transactional audit records and event notifications (BR-HR-024, BR-HR-025, BR-HR-026, BR-HR-033).
6. **`WorkflowSetting`**: Configuration of routing thresholds and authority matrices (BR-HR-017).

## 3. Workflow State Machines
- **Leave Application (`CW-HR-01`)**: `SUBMITTED` -> `RECOMMENDED` -> `APPROVED` (or `REJECTED` / `CANCELLED`).
- **Yearly Appraisal (`CW-HR-02`)**: `DRAFT` -> `SUBMITTED` -> `UNDER_REVIEW` -> `FINALIZED` -> `ARCHIVED` (Immutable).
- **LTC Claim (`CW-HR-03`)**: `SUBMITTED` -> `VERIFIED_HR` -> `APPROVED_AUTHORITY` -> `SETTLED_FINANCE` (or `REJECTED`).
- **CPDA Claim (`CW-HR-04`)**: `SUBMITTED` -> `VERIFIED_HR` -> `APPROVED_AUTHORITY` -> `SETTLED_FINANCE` (or `REJECTED`).

## 4. Role-Based Access Control (RBAC) Matrix
- `Employee (Faculty/Staff)`: View own service record, apply for leave, submit appraisal, submit LTC/CPDA claims.
- `HOD`: Recommend/approve department employee leave requests, review initial appraisals and claims.
- `Registrar`: Approve staff leave, endorse staff claims, compliance oversight.
- `Director`: Final approving authority for faculty leaves, appraisals, and institute-level exceptions.
- `HR Administrator`: Maintain employee master records, verify claim documentation, assign appraisal reviewers, monitor compliance.
- `Accountant`: Verify financial correctness and process disbursement settlements for approved LTC/CPDA claims.

## 5. Architectural Approval Gate
- **Reviewed by Student 2:** Uttkarsh Gautam (24BCS259)
- **Status:** APPROVED IN WRITING
- **Date:** 2026-11-22
- **Approval Note:** The proposed HR-EIS architecture adheres strictly to all synchronized specification documents (PS, CFR/AFR, UC, BR, WF) without unwarranted scope expansion. The separation of concerns between domain rules, state machines, and REST views mirrors the placement reference implementation.
