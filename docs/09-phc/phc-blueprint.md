# Primary Health Centre (PHC) Module Blueprint

**Module Code**: `phc`  
**Base Path**: `/phc`  
**Specification Reference**: `01_PHC_Problem_Statement_v1.0_STUDENT_BASELINE.docx` through `06_PHC_Traceability_Matrix_v1.1_FINAL_SYNCHRONIZED.xlsx`  
**Standard**: Conforming to `docs/03-platform/platform-structure.md`, `definition-of-done.md`, and Placement Cell reference architecture.

---

## 1. Domain Summary & Actor Consolidations

The Primary Health Centre (PHC) Module provides healthcare management for students and employees:
1. **Doctor Schedule & Real-Time Availability**: Master weekly schedule creation, maintenance, publication, and real-time attendance marking (Available / Departed). Combined view for patients (BR-01). Consolidated PHC Staff actor (includes PHC Administrator).
2. **Patient Visit Records & Prescriptions**: Lookup of patient profiles (from `modules.directory`), consultation visit records, digitized prescriptions with scanned document links. Secure read-only access for patients with PDF download capability (BR-02).
3. **Medical Bill Reimbursement**: Progression for eligible employees only (students strictly excluded per BR-04). Requires linked prescription recorded in system (BR-05) and expense date within submission window (BR-06). Ordered forward sequence: Employee submission -> PHC Staff review -> Accounts & Audit verification -> Approving Authority sanction -> Accounts & Audit payment (BR-08). Rejection at sanction is terminal; no in-place modification/reopening (BR-14). Notifications sent upon status changes (BR-13).
4. **Inventory & Procurement Requisition**: Stock management (add/deduct) with automatic threshold comparison triggering low-stock alert when stock < reorder threshold (BR-07). Procurement requisition lifecycle: PHC Staff submit -> Approving Authority decide (Approve/Reject) -> Originator notified (BR-11) -> PHC Staff marks Fulfilled after delivery (BR-10).
5. **Ambulance & Health Announcements**: Ambulance usage logging (patient name, destination, departure/return timestamps) and public health announcements visible on patient dashboards.
6. **Reporting & Privacy**: Administrative reports on demographics, service utilization, and inventory consumption with strict patient anonymization (BR-12).
7. **Audit Trail**: Immutable append-only audit trail for sensitive data operations: patient clinical records, inventory stock updates, and reimbursement claim status transitions (BR-09, AFR-037).

---

## 2. Requirement Traceability Matrix (CFR -> AFR -> Implementation)

| CFR ID | AFR ID(s) | Business Rules | Use Cases | Workflows | Implementation Components |
|---|---|---|---|---|---|
| CFR-PHC-001 | AFR-001, 002, 003, 004, 005 | PHC-BR-01 | UC-01, 07, 08, 22 | N/A | `Doctor`, `DoctorSchedule`, `DoctorAttendance` models; `DoctorAvailabilityPage` |
| CFR-PHC-002 | AFR-006, 007, 008, 009, 010, 011, 012 | PHC-BR-02, 03 | UC-02, 03, 06 | N/A | `PatientVisit`, `Prescription` models; `MedicalHistoryPage`, `PatientVisitsManagementPage` |
| CFR-PHC-003 | AFR-013, 014, 015, 016 | PHC-BR-04, 05, 06, 08 | UC-04 | BW-PHC-01, 02; CW-PHC-01 | `ReimbursementClaim` submission service; `ReimbursementApplyPage` |
| CFR-PHC-004 | AFR-017, 018, 019, 020, 021, 038 | PHC-BR-08, 14 | UC-15, 19, 20, 21 | BW-PHC-01, 02; CW-PHC-01 | `ReimbursementStateMachine`, services; `ReimbursementReviewPage` |
| CFR-PHC-005 | AFR-022, 023 | PHC-BR-13 | UC-04, 05, 15, 19, 20, 21 | CW-PHC-01 | `ReimbursementActionHistory`, notifications; `ReimbursementTrackingPage` |
| CFR-PHC-006 | AFR-024, 025, 026 | PHC-BR-07 | UC-09 | N/A | `InventoryItem`, `InventoryStockAdjustment`; `InventoryStockPage` |
| CFR-PHC-007 | AFR-027, 028, 029, 030, 031 | PHC-BR-10, 11 | UC-10, 14, 16 | BW-PHC-03, 04; CW-PHC-02 | `ProcurementRequisition`, `RequisitionItem`; `ProcurementRequisitionsPage` |
| CFR-PHC-008 | AFR-032 | N/A | UC-11 | N/A | `AmbulanceLog` model, service; `AmbulanceLogsPage` |
| CFR-PHC-009 | AFR-033 | N/A | UC-12 | N/A | `HealthAnnouncement` model, service; `HealthAnnouncementsPage` |
| CFR-PHC-010 | AFR-034, 035 | PHC-BR-12 | UC-13 | N/A | Report generation service with PII anonymization; `PHCReportsPage` |
| CFR-PHC-011 | AFR-036 | PHC-BR-03 | UC-01..16, 19..22 | All | Permission guards in `registry.py` and `api/permissions.py` |
| CFR-PHC-012 | AFR-037 | PHC-BR-09 | UC-06, 09, 15, 19, 20, 21 | CW-PHC-01 | `PHCAuditTrail` immutable log, service; `PHCAuditTrailPage` |

---

## 3. Data Architecture & Isolation

All database tables are owned by the `phc` module with `db_table = "phc_<entity>"`.
Cross-module entities (such as users) are referenced strictly via integer `user_id` without database ForeignKeys (per ADR-0013 and `ops/checks/no_cross_module_fk.py`). User directory details are retrieved via batched contract `modules.directory.contracts.get_users`.

---

## 4. Permissions & Role Grants

| Permission Code | Description | Role Grants |
|---|---|---|
| `phc.doctor_schedule.view` | View published schedule & live attendance | `student`, `faculty`, `staff`, `phc_staff` |
| `phc.doctor_schedule.manage` | Create/edit/publish schedule & mark attendance | `phc_staff`, `compounder`, `phc_admin` |
| `phc.patient_record.view_self` | View own medical history & prescriptions | `student`, `faculty`, `staff` |
| `phc.patient_record.download_self`| Download own medical record PDF | `student`, `faculty`, `staff` |
| `phc.patient_record.manage` | Create visit records & digitize prescriptions | `phc_staff`, `compounder`, `phc_admin` |
| `phc.reimbursement.create` | Submit reimbursement claim | `faculty`, `staff` (Employees only) |
| `phc.reimbursement.view_self` | View own claims and action history | `faculty`, `staff` |
| `phc.reimbursement.review` | Review claim and forward to Accounts | `phc_staff`, `phc_admin` |
| `phc.reimbursement.verify` | Financial verification and forward for sanction | `accounts_audit`, `accountant` |
| `phc.reimbursement.sanction` | Approve or reject claim sanction | `approving_authority`, `director`, `dean_admin` |
| `phc.reimbursement.pay` | Process payment and complete claim | `accounts_audit`, `accountant` |
| `phc.inventory.view` | View inventory stock levels | `phc_staff`, `phc_admin` |
| `phc.inventory.adjust` | Add or deduct inventory stock | `phc_staff`, `phc_admin` |
| `phc.requisition.create` | Submit inventory procurement requisition | `phc_staff`, `phc_admin` |
| `phc.requisition.fulfill` | Mark delivered requisition fulfilled | `phc_staff`, `phc_admin` |
| `phc.requisition.decide` | Approve or reject procurement requisition | `approving_authority`, `director`, `dean_admin` |
| `phc.ambulance.manage` | Record ambulance usage logs | `phc_staff`, `phc_admin` |
| `phc.announcement.view` | View health announcements | `student`, `faculty`, `staff`, `phc_staff` |
| `phc.announcement.manage` | Create and publish health announcements | `phc_staff`, `phc_admin` |
| `phc.report.view` | Generate anonymized administrative reports | `phc_staff`, `approving_authority`, `phc_admin` |
| `phc.audit.view` | View immutable audit trail | `phc_staff`, `approving_authority`, `phc_admin` |
