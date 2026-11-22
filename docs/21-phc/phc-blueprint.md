# PHC module blueprint

**Module:** `phc`
**Environment:** module-only
**Specification set:** `/home/apurva/phc-specs-md`
**Decision basis:** Phase 1 and section (h) decisions approved 2026-11-22 and 2026-11-23, plus the active specification files listed below.
**Status:** approved 2026-11-23 by Apurva Verma (24BEC013), solo execution and module approver.

## (a) Traceability table

The BR and UC source documents leave their related CFR/AFR mapping fields blank. Those links are derived from each rule and use case; the populated CFR–AFR links come from `AFR_lean.csv`. Retired IDs are not included. `CFR-PHC-*` and `AFR-PHC-*` are included as the requirements layer.

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `PHC-BR-01` | Doctor Availability Display Logic: The patient-facing doctor-availability display shall present the static/master weekly schedule together with the doctor's current-day real-time attendance status. | selector + API | `modules/phc/selectors/scoping.py::schedules_for_patients + modules/phc/api/views.py::DoctorAvailabilityView` |  |
| `PHC-BR-02` | Patient Medical Data Access Control: A patient may access only their own medical records and prescriptions, and patient access shall be read-only; PHC Staff access is limited to role-authorized record-management functions. | selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py` |  |
| `PHC-BR-03` | Role-Based Access Control: Access to PHC functions shall be restricted according to the authenticated user's assigned role. | IAM manifest + API permission gates | `modules/phc/registry.py + modules/phc/api/views.py` |  |
| `PHC-BR-04` | Reimbursement Eligibility - Employee Only: Only institute employees may submit medical bill reimbursement claims; students are not eligible to submit such claims. | directory contract + service | `modules/phc/services/reimbursements.py + modules/directory/contracts.py::is_employee` |  |
| `PHC-BR-05` | Reimbursement Prescription Prerequisite: A reimbursement claim shall be accepted only when it is linked to a valid prescription already recorded in the system for the claimant. | services | `modules/phc/services/reimbursements.py` |  |
| `PHC-BR-06` | Reimbursement Submission Window: A reimbursement claim shall be accepted only when it is submitted within the currently configured submission window measured from the medical expense date. | domain + services + effective policy | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` |  |
| `PHC-BR-07` | Inventory Low-Stock Alert Trigger: When an updated inventory stock level is below the item's reorder threshold, the system shall generate a low-stock alert for PHC Staff. | domain + services | `modules/phc/services/inventory.py + modules/phc/models/inventory.py` |  |
| `PHC-BR-08` | Reimbursement Workflow Routing: Every accepted reimbursement claim shall follow the stated progression: Employee submission -\> PHC Staff -\> Accounts & Audit -\> Approving Authority -\> Accounts & Audit payment. | declarative domain table + transactional service | `modules/phc/domain/reimbursements.py::CLAIM_TRANSITIONS + modules/phc/services/reimbursements.py` |  |
| `PHC-BR-09` | Immutable Sensitive-Data Audit Trail: Successful actions that create, modify, or delete sensitive patient records, inventory levels, or reimbursement-claim status shall be recorded in an immutable audit trail. | models + transactional services | `modules/phc/models/audit.py + services/` |  |
| `PHC-BR-10` | Inventory Requisition Approval Requirement: A submitted inventory requisition shall be routed to the Approving Authority, and procurement shall not proceed unless the requisition is approved. | declarative domain table + transactional service | `modules/phc/domain/requisitions.py::REQUISITION_TRANSITIONS + modules/phc/services/requisitions.py` |  |
| `PHC-BR-11` | Requisition Status Notification: When an inventory requisition is approved or rejected, the system shall notify the PHC Staff member who originated the requisition. | services + outbox task | `modules/phc/services/requisitions.py + modules/phc/tasks.py` |  |
| `PHC-BR-12` | Report Privacy and Anonymization: Generated PHC reports shall protect patient-identifiable information and shall present patient-derived reporting data in anonymized form. | aggregate selectors + report service | `modules/phc/selectors/reports.py + modules/phc/services/reports.py` |  |
| `PHC-BR-13` | Reimbursement Status Notification: When a reimbursement claim status changes, the system shall notify the claimant; the PS explicitly includes claim rejection and payment processed as examples. | services + outbox task | `modules/phc/services/reimbursements.py + modules/phc/tasks.py` |  |
| `PHC-BR-14` | Reimbursement Claim Immutability and Fresh Reapplication: A submitted reimbursement claim shall not be modified or reopened. If an employee needs to change a submitted claim or reapply after rejection, the employee shall submit a new reimbursement claim. | domain transition table + database trigger | `modules/phc/domain/reimbursements.py + modules/phc/migrations/0001_initial.py` |  |
| `PHC-UC-01` | View Doctor Schedule & Availability: View the static weekly doctor schedule together with current-day real-time attendance status. | API + selectors | modules/phc/api/views.py::DoctorAvailabilityView |  |
| `PHC-UC-02` | View Medical History & Prescriptions: View the authenticated patient's own medical history and associated prescriptions in read-only form. | API + scoped selectors | modules/phc/api/views.py::PatientRecordsView |  |
| `PHC-UC-03` | Download Medical Records: Download a PDF copy of selected records from the patient's own medical history. | API + PDF service | modules/phc/api/views.py::PatientRecordsPdfView |  |
| `PHC-UC-04` | Apply for Medical Bill Reimbursement: Submit an eligible medical bill reimbursement claim. | API + reimbursement service | modules/phc/services/reimbursements.py::submit_claim |  |
| `PHC-UC-05` | Track Reimbursement Status: View the current status and action history of the employee's submitted reimbursement claims. | API + scoped selectors | modules/phc/api/views.py::ClaimsView |  |
| `PHC-UC-06` | Record Patient Visit & Prescription: Find a patient and record a visit together with a digitized prescription. | API + patient-record service | modules/phc/services/records.py::create_visit |  |
| `PHC-UC-07` | Maintain Doctor Master Schedule: Maintain the static weekly schedule of visiting doctors. | API + schedule service | modules/phc/services/schedules.py::update_slot |  |
| `PHC-UC-08` | Mark Doctor Attendance: Update a visiting doctor's real-time attendance status when the doctor arrives or departs. | API + attendance service | modules/phc/services/schedules.py::set_attendance |  |
| `PHC-UC-09` | Manage Inventory Stock: Add to or deduct from inventory stock levels and obtain low-stock alerts when required. | API + inventory service | modules/phc/services/inventory.py::adjust_stock |  |
| `PHC-UC-10` | Submit Inventory Requisition: Create and submit an inventory procurement requisition. | API + requisition service | modules/phc/services/requisitions.py::submit_requisition |  |
| `PHC-UC-11` | Log Ambulance Usage: Record each use of the PHC ambulance with the required audit information. | API + ambulance service | modules/phc/services/operations.py::record_ambulance_usage |  |
| `PHC-UC-12` | Broadcast Health Announcements: Publish health advisories to patient dashboards. | API + advisory service | modules/phc/services/operations.py::publish_advisory |  |
| `PHC-UC-13` | Generate System Reports: Generate administrative reports on patient demographics, service utilization, or inventory consumption without exposing patient-identifiable information. | API + aggregate report selectors | modules/phc/services/reports.py::aggregate_report |  |
| `PHC-UC-14` | Mark Requisition as Fulfilled: Close an approved inventory requisition after the ordered supplies are delivered. | API + requisition service | modules/phc/services/requisitions.py::transition_requisition |  |
| `PHC-UC-15` | Review Reimbursement Claim: Review a submitted reimbursement claim at the PHC stage and forward it to Accounts & Audit on the supported progression path. | API + reimbursement state service | modules/phc/services/reimbursements.py::transition_claim |  |
| `PHC-UC-16` | Decide Inventory Requisition: Approve or reject a pending inventory requisition. | API + requisition state service | modules/phc/services/requisitions.py::transition_requisition |  |
| `PHC-UC-19` | Verify Reimbursement Claim: Verify the financial details of a reimbursement claim and forward it for sanction on the supported progression path. | API + reimbursement state service | modules/phc/services/reimbursements.py::transition_claim |  |
| `PHC-UC-20` | Decide Reimbursement Sanction: Approve or reject the reimbursement sanction for a verified claim. | API + reimbursement state service | modules/phc/services/reimbursements.py::transition_claim |  |
| `PHC-UC-21` | Process Reimbursement Payment: Process the final payment for an approved reimbursement claim and close it as reimbursed. | API + reimbursement state service | modules/phc/services/reimbursements.py::transition_claim |  |
| `PHC-UC-22` | Create & Publish Doctor Schedule: Create a doctor schedule and publish it for patient visibility. | API + schedule service | modules/phc/services/schedules.py::publish_slot |  |
| `BW-PHC-01` | Reimbursement - Approved and Reimbursed: Represent the supported success path from employee claim submission to completed reimbursement. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | basis |
| `BW-PHC-02` | Reimbursement - Rejected at Sanction: Represent the explicitly supported rejection outcome at the Approving Authority stage. Rejection is terminal for the current claim; a later application is a new claim. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | basis |
| `BW-PHC-03` | Inventory Requisition - Approved and Fulfilled: Represent the path from PHC Staff requisition submission through approval and post-delivery fulfillment. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | basis |
| `BW-PHC-04` | Inventory Requisition - Rejected: Represent the rejection outcome for a submitted inventory requisition. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | basis |
| `CW-PHC-01` | Medical Bill Reimbursement Progression: Integrate the supported reimbursement approval/payment and sanction-rejection outcomes around the common submission, PHC review, and Accounts & Audit verification prefix. Rejected claims are terminal; any reapplication starts a new claim instance. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | composite |
| `CW-PHC-02` | Inventory Procurement Requisition Progression: Integrate approval/fulfillment and rejection outcomes around the shared requisition submission and authority decision. | domain state machine + transactional service | `modules/phc/domain/reimbursements.py + modules/phc/domain/requisitions.py + modules/phc/services/reimbursements.py + modules/phc/services/requisitions.py` | composite |
| `AFR-PHC-001` | The system shall provide a patient access to the static weekly doctor schedule together with the current-day real-time doctor attendance status. | domain + selectors + services | `modules/phc/api/views.py::DoctorAvailabilityView + modules/phc/services/schedules.py` | mapped from CFR-PHC-001 in AFR_lean.csv |
| `AFR-PHC-002` | The system shall allow PHC Staff to maintain the static weekly schedule of visiting doctors. | domain + selectors + services | `modules/phc/api/views.py::DoctorAvailabilityView + modules/phc/services/schedules.py` | mapped from CFR-PHC-001 in AFR_lean.csv |
| `AFR-PHC-003` | The system shall allow PHC Staff to mark a visiting doctor as Available or Departed in real time. | domain + selectors + services | `modules/phc/api/views.py::DoctorAvailabilityView + modules/phc/services/schedules.py` | mapped from CFR-PHC-001 in AFR_lean.csv |
| `AFR-PHC-004` | The system shall allow PHC Staff to create doctor schedules. | domain + selectors + services | `modules/phc/api/views.py::DoctorAvailabilityView + modules/phc/services/schedules.py` | mapped from CFR-PHC-001 in AFR_lean.csv |
| `AFR-PHC-005` | The system shall allow PHC Staff to publish a doctor schedule for patient visibility. | domain + selectors + services | `modules/phc/api/views.py::DoctorAvailabilityView + modules/phc/services/schedules.py` | mapped from CFR-PHC-001 in AFR_lean.csv |
| `AFR-PHC-006` | The system shall allow PHC Staff to search for a patient profile. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-007` | The system shall allow PHC Staff to create a patient visit record. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-008` | The system shall allow PHC Staff to digitize a physical prescription and link it to the corresponding patient record. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-009` | The system shall provide a patient read-only access to their own medical history. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-010` | The system shall provide a patient access to prescriptions associated with their own medical history. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-011` | The system shall allow a patient to download PDF copies of their own medical records. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-012` | The system shall restrict access to patient medical data according to role and shall prevent a patient from accessing another patient's records. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/records.py + modules/phc/api/views.py` | mapped from CFR-PHC-002 in AFR_lean.csv |
| `AFR-PHC-013` | The system shall restrict medical bill reimbursement submission to institute employees and shall exclude students from this feature. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-003 in AFR_lean.csv |
| `AFR-PHC-014` | The system shall require each reimbursement claim to be linked to a valid prescription already recorded in the system for the claimant. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-003 in AFR_lean.csv |
| `AFR-PHC-015` | The system shall enforce the configured reimbursement submission window against the medical expense date. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-003 in AFR_lean.csv |
| `AFR-PHC-016` | The system shall allow an eligible employee to submit a medical bill reimbursement claim. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-003 in AFR_lean.csv |
| `AFR-PHC-017` | The system shall move a submitted reimbursement claim through PHC Staff review, Accounts & Audit verification, Approving Authority sanction, and Accounts & Audit payment processing in that order. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `AFR-PHC-018` | The system shall allow PHC Staff to review a submitted reimbursement claim and forward it to Accounts & Audit for financial verification. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `AFR-PHC-019` | The system shall allow Accounts & Audit to verify the financial details of a reimbursement claim. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `AFR-PHC-020` | The system shall allow the Approving Authority to approve or reject a reimbursement sanction. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `AFR-PHC-021` | The system shall allow Accounts & Audit to process the final payment for an approved reimbursement claim. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `AFR-PHC-022` | The system shall provide an employee access to the current status and action history of each reimbursement claim they submitted. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/reimbursements.py + modules/phc/tasks.py` | mapped from CFR-PHC-005 in AFR_lean.csv |
| `AFR-PHC-023` | The system shall notify the claimant when a reimbursement claim status changes, including rejection and payment processing events. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/services/reimbursements.py + modules/phc/tasks.py` | mapped from CFR-PHC-005 in AFR_lean.csv |
| `AFR-PHC-024` | The system shall allow PHC Staff to add to or deduct from inventory stock levels. | domain + selectors + services | `modules/phc/models/inventory.py + services/inventory.py` | mapped from CFR-PHC-006 in AFR_lean.csv |
| `AFR-PHC-025` | The system shall compare an updated inventory stock level with the item's reorder threshold. | domain + selectors + services | `modules/phc/models/inventory.py + services/inventory.py` | mapped from CFR-PHC-006 in AFR_lean.csv |
| `AFR-PHC-026` | The system shall notify PHC Staff when an inventory item's stock level falls below its reorder threshold. | domain + selectors + services | `modules/phc/models/inventory.py + services/inventory.py` | mapped from CFR-PHC-006 in AFR_lean.csv |
| `AFR-PHC-027` | The system shall allow PHC Staff to create and submit an inventory procurement requisition containing the required items and quantities. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` | mapped from CFR-PHC-007 in AFR_lean.csv |
| `AFR-PHC-028` | The system shall move a submitted inventory requisition to the Approving Authority for decision. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` | mapped from CFR-PHC-007 in AFR_lean.csv |
| `AFR-PHC-029` | The system shall allow the Approving Authority to approve or reject a pending inventory requisition. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` | mapped from CFR-PHC-007 in AFR_lean.csv |
| `AFR-PHC-030` | The system shall notify the originating PHC Staff member when an inventory requisition is approved or rejected. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` | mapped from CFR-PHC-007 in AFR_lean.csv |
| `AFR-PHC-031` | The system shall allow PHC Staff to mark an approved inventory requisition as Fulfilled after the supplies are delivered. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` | mapped from CFR-PHC-007 in AFR_lean.csv |
| `AFR-PHC-032` | The system shall allow PHC Staff to record ambulance usage with timestamp, patient name, and destination. | domain + selectors + services | `modules/phc/services/operations.py` | mapped from CFR-PHC-008 in AFR_lean.csv |
| `AFR-PHC-033` | The system shall allow PHC Staff to publish health advisories that are visible to all patients on their dashboard. | domain + selectors + services | `modules/phc/services/operations.py + client/src/modules/phc/pages/AdvisoriesPage.tsx` | mapped from CFR-PHC-009 in AFR_lean.csv |
| `AFR-PHC-034` | The system shall allow PHC Staff to generate reports on patient demographics, service utilization, and inventory consumption. | selectors + services | `modules/phc/selectors/reports.py + modules/phc/api/serializers.py` | mapped from CFR-PHC-010 in AFR_lean.csv |
| `AFR-PHC-035` | The system shall anonymize report output and protect patient-identifiable information in generated reports. | selectors + services | `modules/phc/selectors/reports.py + modules/phc/api/serializers.py` | mapped from CFR-PHC-010 in AFR_lean.csv |
| `AFR-PHC-036` | The system shall restrict access to every PHC function according to the authenticated user's assigned role. | registry + API permissions | `modules/phc/registry.py + modules/phc/api/views.py` | mapped from CFR-PHC-011 in AFR_lean.csv |
| `AFR-PHC-037` | The system shall record an immutable audit trail for actions that create, modify, or delete sensitive patient records, inventory levels, or reimbursement-claim status. | models + services | `modules/phc/models/audit.py + modules/phc/services/common.py` | mapped from CFR-PHC-012 in AFR_lean.csv |
| `AFR-PHC-038` | The system shall require any post-submission change or post-rejection resubmission of a reimbursement claim to be made as a new claim rather than by modifying or reopening the existing claim. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` | mapped from CFR-PHC-004 in AFR_lean.csv |
| `CFR-PHC-001` | The system shall support doctor schedule and availability management by enabling PHC Staff to create, maintain, and publish the master weekly doctor schedule, update visiting-doctor real-time attendance, and provide patients the published schedule together with current-day attendance status. | domain + selectors + services | `modules/phc/api/views.py + modules/phc/services/schedules.py` |  |
| `CFR-PHC-002` | The system shall support patient visit and prescription records by enabling PHC Staff to locate patients, record visits and digitized prescriptions, while allowing patients secure read-only access to and download of only their own medical history and prescriptions. | domain + selectors + services | `modules/phc/services/records.py + modules/phc/selectors/scoping.py + modules/phc/api/views.py` |  |
| `CFR-PHC-003` | The system shall support medical bill reimbursement submission for eligible institute employees by enforcing employee-only eligibility, a valid recorded prescription prerequisite, the configured submission window, and creation of a valid claim that enters reimbursement processing. | domain + selectors + services | `modules/phc/services/reimbursements.py + modules/phc/domain/reimbursements.py` |  |
| `CFR-PHC-004` | The system shall process accepted reimbursement claims through PHC Staff review, Accounts & Audit financial verification, Approving Authority sanction decision, and Accounts & Audit payment in the defined order, while preserving each submitted claim as a non-editable workflow instance so that any changed or post-rejection application is a new claim. | domain + selectors + services | `modules/phc/domain/reimbursements.py + modules/phc/services/reimbursements.py` |  |
| `CFR-PHC-005` | The system shall provide each employee visibility of the current status and action history of their own reimbursement claims and shall notify the claimant whenever claim status changes, including rejection and payment-processing events. | domain + selectors + services | `modules/phc/selectors/scoping.py + modules/phc/tasks.py` |  |
| `CFR-PHC-006` | The system shall support PHC inventory stock control by allowing PHC Staff to adjust stock quantities, evaluating the updated quantity against the item reorder threshold, and alerting PHC Staff when stock falls below that threshold. | domain + selectors + services | `modules/phc/services/inventory.py + modules/phc/models/inventory.py` |  |
| `CFR-PHC-007` | The system shall support inventory procurement requisitions by enabling PHC Staff to create and submit required items/quantities, routing the requisition to the Approving Authority, recording approval or rejection and notifying the originator, and allowing an approved requisition to be marked Fulfilled after delivery. | domain + selectors + services | `modules/phc/domain/requisitions.py + modules/phc/services/requisitions.py + modules/phc/tasks.py` |  |
| `CFR-PHC-008` | The system shall allow PHC Staff to record ambulance usage with timestamp, patient name, and destination. | domain + selectors + services | `modules/phc/services/operations.py` |  |
| `CFR-PHC-009` | The system shall allow PHC Staff to publish health advisories that are visible to all patients on their dashboards. | domain + selectors + services | `modules/phc/services/operations.py + client/src/modules/phc/pages/AdvisoriesPage.tsx` |  |
| `CFR-PHC-010` | The system shall allow PHC Staff to generate administrative reports on patient demographics, service utilization, and inventory consumption while anonymizing patient-derived output and protecting patient-identifiable information. | services + selectors | `modules/phc/selectors/reports.py + modules/phc/api/serializers.py` |  |
| `CFR-PHC-011` | The system shall restrict access to PHC functions according to the authenticated user's assigned role. | registry + API permissions | `modules/phc/registry.py + modules/phc/api/views.py` |  |
| `CFR-PHC-012` | The system shall maintain an immutable audit trail for successful actions that create, modify, or delete sensitive patient records, inventory levels, or reimbursement-claim status. | models + services | `modules/phc/models/audit.py + modules/phc/services/common.py` |  |


## (b) Domain model

All person references are integer IDs. PHC business tables live in `fusion_integrated`; no IAM, ERP, or other-module model is copied into this module. No cross-module or user foreign keys are permitted.

| Aggregate / record | Planned data | Invariants and database enforcement |
|---|---|---|
| Doctor master and weekly schedule | Doctor display name, specialization, active flag; weekly day/start/end time in institute local timezone; `draft` / `published` state and timestamps | Published schedules pass validation. Same-doctor slots on the same weekday may not overlap; enforce with a PostgreSQL exclusion constraint over a generated weekly minute range, with a check that the range matches the weekday and start/end times. Institute timezone comes from the configured `TIME_ZONE`. |
| Doctor attendance | Doctor reference, attendance date, status (`Available` / `Departed`), actor ID and timestamps | One current-day status per doctor/date; named unique constraint. Attendance writes use a single service. |
| Patient visit | `patient_user_id`, `visited_on`, `notes`, `recorded_by_user_id`, timestamps | Patient ID is resolved from the directory before write. Notes are private clinical text. No user FK. Patient access is read-only and owner-scoped. |
| Prescription | Visit reference, `details`, `issued_on`, `issued_by_user_id`, timestamps | Visit and prescription are created atomically. Prescription ownership is derived through its visit; reimbursement validation confirms claimant ownership. |
| Reimbursement policy | Immutable effective-dated version and `submission_window_days`; seed 30 days effective 2026-01-01 | No in-place edits. New versions supersede by date; a PostgreSQL exclusion constraint prevents overlapping effective periods. The initial version is effective 2026-01-01 and seeded on first install. |
| Reimbursement claim | Claimant `user_id`, linked prescription, expense date, submitted timestamp, amount and the minimum financial details needed for verification, current state, timestamps | Employee-directory membership is checked at submission. Expense must not be future-dated; `(submission_date - expense_date).days <= 30`. Submitted claim content is immutable. State and audit changes commit together. Amount/currency and financial fields not defined by the spec remain open (h). |
| Reimbursement action history | Claim ID, from/to state, actor `user_id`, action, timestamp | Append-only. A database constraint protects event shape; service transitions lock the claim row. No event update/delete path. |
| Inventory item | Item name, unit (default `units`), positive integer reorder threshold, stock quantity derived from movements, active flag, timestamps | Stock is not stored as an independently editable balance. Derived quantity cannot be negative; quantity is a non-negative integer derived from append-only movements; no sample inventory is seeded in production. |
| Inventory movement | Item ID, signed quantity delta, reason, actor ID, timestamp | Append-only ledger. Database check rejects zero deltas; transaction locks the item and prevents a negative resulting quantity. Reversal is a new opposite movement. |
| Low-stock alert | Item ID, stock and threshold snapshot, generated timestamp | Created in the same transaction as every movement that leaves stock below threshold; no alert is generated at or above threshold. |
| Inventory requisition and lines | Originator ID, state, item/quantity lines, decision actor, timestamps | Submitted line set becomes immutable. Requisition transitions are locked and state-checked. Requisition lines carry only the approved item reference and quantity fields; stock is adjusted separately after delivery. |
| Ambulance usage | Timestamp, patient name, destination, recorder ID, timestamps | PHC Staff only. Patient name is sensitive and is never placed in logs or aggregate reports. Audit coverage is not expanded beyond the spec without approval. |
| Health advisory | Patient-facing content, publication state, publisher ID and timestamps | Only published advisories are visible to patient roles. Content fields beyond the requirement are open (h). |
| PHC audit event | Actor ID, action, object type/ID, timestamp and minimal non-PII event metadata | Append-only; no names, user display data, clinical notes, or request bodies. Database permissions/trigger prevent update and delete. Covers patient records, inventory movements, and claim status, as PHC-BR-09 states. |
| Notification outbox | Event type, target user ID, safe payload, created/delivered timestamps and idempotency key | Written in the same transaction as the triggering change. Unique idempotency key prevents duplicate delivery effects. Payload excludes clinical or personal details. |

Concurrency-critical uniqueness and nonnegative-stock conditions belong in PostgreSQL constraints/locking, not only Python. Person IDs and doctors are plain references, never foreign keys across ownership boundaries. Every index will be named and tied to a concrete selector filter/order; final index definitions are part of the approved model review against endpoint queries.

## (c) State machines

Transitions are declared as immutable data and resolved through one service choke point. Services use `transaction.atomic()` and `select_for_update()`, verify the expected source state and actor, append history/audit events, and enqueue notifications before commit.

### Reimbursement claim

| State | Event | Actor | Next state |
|---|---|---|---|
| absent | submit valid claim | employee | Pending PHC Review |
| Pending PHC Review | forward after review | Compounder / PHC Staff | Pending Accounts Verification |
| Pending Accounts Verification | record successful verification | Accounts Admin / Accounts & Audit | Pending Sanction |
| Pending Sanction | approve sanction | Registrar / Approving Authority | Approved for Payment |
| Pending Sanction | reject sanction | Registrar / Approving Authority | Rejected (terminal) |
| Approved for Payment | record completed payment | Accounts Admin / Accounts & Audit | Reimbursed (terminal) |

No reject, return, clarification, amendment, reopening, or payment-undo transition is defined. A correction or reapplication is a new claim. All state changes notify the claimant and append history/audit rows. Every non-table state/event/actor combination is refused.

### Inventory requisition

| State | Event | Actor | Next state |
|---|---|---|---|
| absent | submit valid requisition | Compounder / PHC Staff | Pending Approval |
| Pending Approval | approve | Registrar / Approving Authority | Approved |
| Pending Approval | reject | Registrar / Approving Authority | Rejected (terminal) |
| Approved | confirm delivered supplies | Compounder / PHC Staff | Fulfilled (terminal) |

Only approved requisitions can be marked fulfilled. Approval/rejection notifies the originator. Fulfilling does not automatically change inventory; the spec explicitly assigns stock adjustment to its separate inventory action.

Doctor schedule publication is a draft-to-published operation with validation. Attendance is a daily status replacement under a locked doctor/date row, not a multistep workflow. Inventory stock is represented by append-only movements, not a mutable workflow state.

## (d) Permissions and role grants

`MODULE` is `{code: "phc", label: "Primary Health Centre", icon: "FirstAid", base_path: "/phc", nav_section: "Health", sort_order: 21, status: "active"}`. `FirstAid` is a Fusion-client Phosphor icon name. All nav entries carry the exact permission shown in the endpoint and route plan.

Permissions use only the closed RBAC verbs (`view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`). `manage` is used only for Accounts Admin reimbursement verification and payment, because “verify” and “process” are not valid verbs and are semantically distinct from the Registrar’s sanction approval.

| Permission | Purpose | Granted to |
|---|---|---|
| `phc.doctor_schedule.view` | See published doctor schedule | `student`, `faculty`, `staff`, `Compounder` |
| `phc.doctor_schedule.create` | Create schedule | `Compounder` |
| `phc.doctor_schedule.update` | Maintain schedule | `Compounder` |
| `phc.doctor_schedule.publish` | Publish schedule | `Compounder` |
| `phc.doctor_attendance.update` | Mark current-day doctor attendance | `Compounder` |
| `phc.patient_record.view` | Read patient history and prescriptions within own scope or PHC staff scope | `student`, `faculty`, `staff`, `Compounder` |
| `phc.patient_record.create` | Record visit and prescription | `Compounder` |
| `phc.record.export` | Generate own medical-record PDF | `student`, `faculty`, `staff`, `Compounder` |
| `phc.reimbursement.view` | View own claims or authorized processing queue | `faculty`, `staff`, `Compounder`, `Accounts Admin`, `Registrar` |
| `phc.reimbursement.create` | Submit reimbursement claim | `faculty`, `staff` (service additionally verifies membership in employee directory) |
| `phc.reimbursement.review` | PHC review/forward | `Compounder` |
| `phc.reimbursement.manage` | Accounts verification and payment processing | `Accounts Admin` |
| `phc.reimbursement.approve` | Sanction or reject claim | `Registrar` |
| `phc.inventory.view` | View inventory and low-stock alerts | `Compounder` |
| `phc.inventory.create` | Create inventory item | `Compounder` |
| `phc.inventory.update` | Record stock movement / threshold change | `Compounder` |
| `phc.requisition.view` | View own-originated or approval queue requisitions | `Compounder`, `Registrar` |
| `phc.requisition.create` | Submit requisition | `Compounder` |
| `phc.requisition.approve` | Approve/reject requisition | `Registrar` |
| `phc.requisition.update` | Mark approved requisition fulfilled | `Compounder` |
| `phc.ambulance_usage.view` | View ambulance log | `Compounder` |
| `phc.ambulance_usage.create` | Record ambulance use | `Compounder` |
| `phc.advisory.view` | Read published health advisories | `student`, `faculty`, `staff`, `Compounder` |
| `phc.advisory.publish` | Publish health advisory | `Compounder` |
| `phc.report.view` | Generate aggregate-only operational reports | `Compounder` |
| `phc.notification.view` | View notifications addressed to the caller | `faculty`, `staff`, `Compounder`, `Accounts Admin`, `Registrar` |
| `phc.notification.manage` | Deliver outbox events as scheduled system work | system only |

`SCOPE_PERMISSIONS` is exactly `("phc.patient_record.view", "phc.record.export", "phc.reimbursement.view", "phc.requisition.view", "phc.notification.view")`. Selectors narrow patient records and PDFs to the caller unless the acting role is `Compounder`; claims and notifications are owner-scoped for employees and role-queue-scoped for office actors; requisitions are originator-scoped for Compounder and pending-decision-scoped for Registrar. Scope changes rows returned, never the permission set.

The `ROLE_GRANTS` mapping is:

```python
ROLE_GRANTS = {
    "student": ["phc.doctor_schedule.view", "phc.patient_record.view",
                "phc.record.export", "phc.advisory.view"],
    "faculty": ["phc.doctor_schedule.view", "phc.patient_record.view",
                "phc.advisory.view", "phc.record.export",
                "phc.reimbursement.view", "phc.reimbursement.create",
                "phc.notification.view"],
    "staff": ["phc.doctor_schedule.view", "phc.patient_record.view",
              "phc.advisory.view", "phc.record.export",
              "phc.reimbursement.view", "phc.reimbursement.create",
              "phc.notification.view"],
    "Compounder": ["phc.doctor_schedule.view", "phc.doctor_schedule.create",
                   "phc.doctor_schedule.update", "phc.doctor_schedule.publish",
                   "phc.doctor_attendance.update", "phc.patient_record.view",
                   "phc.patient_record.create", "phc.reimbursement.view",
                   "phc.reimbursement.review", "phc.inventory.view",
                   "phc.inventory.create", "phc.inventory.update",
                   "phc.requisition.view", "phc.requisition.create",
                   "phc.requisition.update", "phc.ambulance_usage.view",
                   "phc.ambulance_usage.create", "phc.advisory.view",
                   "phc.advisory.publish", "phc.report.view",
                   "phc.notification.view"],
    "Accounts Admin": ["phc.reimbursement.view", "phc.reimbursement.manage",
                       "phc.notification.view"],
    "Registrar": ["phc.reimbursement.view", "phc.reimbursement.approve",
                  "phc.requisition.view", "phc.requisition.approve",
                  "phc.notification.view"],
}
```

`ROLE_GRANTS` is keyed by the exact approved designation strings `Compounder`, `Accounts Admin`, and `Registrar`; basic roles `student`, `faculty`, and `staff` receive only the patient-facing permissions listed above. Accounts Admin and Registrar receive the PHC module grant because they have PHC actions. `SYSTEM_PERMISSIONS` contains only `phc.notification.manage`. No new designation or local role model is introduced. Employee submission is additionally checked against the employee directory, so an ordinary staff/faculty-kind account absent from that projection cannot submit.

### Nav plan

| Nav code | Label | Icon | Route | Required permission |
|---|---|---|---|---|
| `phc.dashboard` | Patient Dashboard | House | `/phc/patient-dashboard` | `phc.patient_record.view` |
| `phc.doctor-availability` | Doctor Availability | CalendarDots | `/phc/doctor-availability` | `phc.doctor_schedule.view` |
| `phc.medical-records` | My Medical Records | FirstAid | `/phc/medical-records` | `phc.patient_record.view` |
| `phc.reimbursements` | My Reimbursement Claims | Receipt | `/phc/reimbursements` | `phc.reimbursement.view` |
| `phc.staff-visits` | Patient Visits | ClipboardText | `/phc/staff/visits` | `phc.patient_record.create` |
| `phc.staff-schedules` | Doctor Schedules | CalendarPlus | `/phc/staff/schedules` | `phc.doctor_schedule.update` |
| `phc.staff-attendance` | Doctor Attendance | UserCheck | `/phc/staff/attendance` | `phc.doctor_attendance.update` |
| `phc.staff-inventory` | Inventory | Package | `/phc/staff/inventory` | `phc.inventory.view` |
| `phc.staff-requisitions` | Inventory Requisitions | ListChecks | `/phc/staff/requisitions` | `phc.requisition.view` |
| `phc.staff-ambulance` | Ambulance Log | Ambulance | `/phc/staff/ambulance` | `phc.ambulance_usage.view` |
| `phc.staff-advisories` | Health Advisories | Megaphone | `/phc/staff/advisories` | `phc.advisory.publish` |
| `phc.staff-reports` | PHC Reports | ChartBar | `/phc/staff/reports` | `phc.report.view` |
| `phc.notifications` | PHC Notifications | Bell | `/phc/notifications` | `phc.notification.view` |
| `phc.accounts-claims` | Reimbursement Verification and Payment | Receipt | `/phc/accounts/claims` | `phc.reimbursement.manage` |
| `phc.authority-claims` | Reimbursement Sanctions | Stamp | `/phc/authority/claims` | `phc.reimbursement.approve` |
| `phc.authority-requisitions` | Requisition Decisions | Stamp | `/phc/authority/requisitions` | `phc.requisition.approve` |

Shared patient-facing pages are route-accessible to each role granted the matching permission; their controls remain permission-gated. Office-only routes use `RequirePermission` with exactly the nav permission, so the page does not mount or fetch for other roles. Every nav item has a route; record detail and decision forms use drawers/modals on their queue/list pages.

## (e) Endpoint and client-route plan

All paths below are under `/api/v1/phc/`. Every endpoint has `HasModuleGrant("phc")` first and the listed permission second. Every write has a named DRF throttle scope. Reads start from `selectors/scoping.py`; an out-of-scope object ID returns 404. Every endpoint will have an OpenAPI request/response example.

| Method and path | Permission | Throttle scope | Response / purpose | IDs |
|---|---|---|---|---|
| GET `/doctor-availability` | `phc.doctor_schedule.view` | — | Published weekly schedules plus current-day attendance | BR-01, UC-01, UC-08, UC-22, CFR-001, AFR-001–005 |
| GET `/records` | `phc.patient_record.view` | — | Caller’s own visits and prescriptions | BR-02, UC-02, CFR-002, AFR-009–010, AFR-012 |
| POST `/records/pdf` | `phc.record.export` | `phc_pdf` | PDF for selected caller-owned records; no partial response on failure | BR-02, UC-03, CFR-002, AFR-011–012 |
| GET `/directory/patients?q=` | `phc.patient_record.create` | — | Bounded user search via directory contract; no ERP query | UC-06, CFR-002, AFR-006 |
| POST `/visits` | `phc.patient_record.create` | `phc_write` | Create visit and prescription atomically | BR-02, BR-09, UC-06, CFR-002, AFR-007–008, AFR-037 |
| GET `/doctor-schedules` | `phc.doctor_schedule.view` | — | Staff schedule list | BR-01, UC-07, UC-22, CFR-001, AFR-002, AFR-004–005 |
| POST `/doctor-schedules` | `phc.doctor_schedule.create` | `phc_write` | Create schedule draft | UC-22, CFR-001, AFR-004 |
| PATCH `/doctor-schedules/{id}` | `phc.doctor_schedule.update` | `phc_write` | Maintain schedule | UC-07, UC-22, CFR-001, AFR-002 |
| POST `/doctor-schedules/{id}/publish` | `phc.doctor_schedule.publish` | `phc_write` | Validate and publish schedule | BR-01, UC-22, CFR-001, AFR-005 |
| POST `/doctor-attendance` | `phc.doctor_attendance.update` | `phc_write` | Set doctor Available/Departed for current day | BR-01, UC-08, CFR-001, AFR-003 |
| GET `/doctor-attendance` | `phc.doctor_attendance.update` | — | Current-day attendance records for staff | UC-08, CFR-001, AFR-003 |
| GET `/reimbursements` | `phc.reimbursement.view` | — | Own claims or scoped staff processing queue | BR-08, BR-14, UC-05, UC-15, UC-19–21, CFR-004–005, AFR-017–023, AFR-038 |
| POST `/reimbursements` | `phc.reimbursement.create` | `phc_write` | Validate employee, prescription, expense date and policy; submit | BR-04–06, BR-08, BR-14, UC-04, CFR-003–004, AFR-013–016, AFR-038 |
| POST `/reimbursements/{id}/review` | `phc.reimbursement.review` | `phc_write` | Forward pending PHC review claim | BR-08, BR-09, BR-13, UC-15, CFR-004–005, AFR-017–018, AFR-022–023, AFR-037 |
| POST `/reimbursements/{id}/verification` | `phc.reimbursement.manage` | `phc_write` | Record Accounts verification and forward | BR-08, BR-09, BR-13, UC-19, CFR-004–005, AFR-017, AFR-019, AFR-022–023, AFR-037 |
| POST `/reimbursements/{id}/sanction` | `phc.reimbursement.approve` | `phc_write` | Approve or terminally reject sanction | BR-08–09, BR-13–14, UC-20, CFR-004–005, AFR-017, AFR-020, AFR-022–023, AFR-037–038 |
| POST `/reimbursements/{id}/payment` | `phc.reimbursement.manage` | `phc_write` | Record payment completion | BR-08–09, BR-13, UC-21, CFR-004–005, AFR-017, AFR-021–023, AFR-037 |
| GET `/inventory` | `phc.inventory.view` | — | Item stock and threshold | BR-07, UC-09, CFR-006, AFR-024–026 |
| POST `/inventory` | `phc.inventory.create` | `phc_write` | Create item after catalogue-field decisions | UC-09, CFR-006, AFR-024–025 |
| POST `/inventory/{id}/movements` | `phc.inventory.update` | `phc_write` | Append stock adjustment and possibly low-stock alert | BR-07, BR-09, UC-09, CFR-006, AFR-024–026, AFR-037 |
| GET `/inventory/low-stock-alerts` | `phc.inventory.view` | — | Alerts created when current stock is below threshold | BR-07, UC-09, CFR-006, AFR-026 |
| GET `/requisitions` | `phc.requisition.view` | — | Originator’s own requisitions or Registrar queue | BR-10–11, UC-10, UC-14, UC-16, CFR-007, AFR-027–031 |
| POST `/requisitions` | `phc.requisition.create` | `phc_write` | Submit required item/quantity lines | BR-10, UC-10, CFR-007, AFR-027–028 |
| POST `/requisitions/{id}/decision` | `phc.requisition.approve` | `phc_write` | Approve or reject pending requisition | BR-10–11, UC-16, CFR-007, AFR-028–030 |
| POST `/requisitions/{id}/fulfill` | `phc.requisition.update` | `phc_write` | Mark approved requisition fulfilled | BR-10, UC-14, CFR-007, AFR-031 |
| GET `/ambulance-usage` | `phc.ambulance_usage.view` | — | PHC ambulance log | UC-11, CFR-008, AFR-032 |
| POST `/ambulance-usage` | `phc.ambulance_usage.create` | `phc_write` | Record timestamp, patient name, destination | UC-11, CFR-008, AFR-032 |
| GET `/advisories` | `phc.advisory.view` | — | Published advisories for patient module page | UC-12, CFR-009, AFR-033 |
| POST `/advisories` | `phc.advisory.publish` | `phc_write` | Publish advisory for patient page | UC-12, CFR-009, AFR-033 |
| GET `/reports/{report_type}` | `phc.report.view` | — | Aggregate-only counts/totals/breakdowns; no PII or free text | BR-12, UC-13, CFR-010, AFR-034–035 |
| GET `/notifications` | `phc.notification.view` | — | Current role’s recipient notifications, scoped to caller | BR-11, BR-13, CFR-005, AFR-023, AFR-030 |

**Client routes and guards:** `/patient-dashboard`, `/doctor-availability`, `/medical-records`, `/reimbursements`, `/staff/visits`, `/staff/schedules`, `/staff/attendance`, `/staff/inventory`, `/staff/requisitions`, `/staff/ambulance`, `/advisories`, `/staff/advisories`, `/staff/reports`, `/accounts/claims`, `/authority/claims`, `/authority/requisitions`, `/notifications`. Patient-facing routes are separately guarded by their own nav permission; shared patient actions are gated with `can()`. Office routes are each wrapped in `RequirePermission` matching their nav item. `test_client_route_guards.py` pins the permission-to-nav match and verifies direct-link denial with no page fetch.

**Fusion-client sidebar handoff:** add `{ id: "phc", label: "Primary Health Centre", icon: "FirstAid", to: "/phc", section: "Health" }` to `INTEGRATED_MODULES`. This entry is not editable in this module-only checkout.

## (f) Contracts

PHC imports only `modules.directory.contracts` for identity projection:

- `search(q, kind, limit)` / a plural batched user getter to resolve PHC Staff patient search and display names. The existing module contract currently has `search` and `get_users`; no new IAM endpoint is needed.
- `is_employee(user_ids)` for batched reimbursement eligibility, implemented using the directory’s local employee projection from IAM `iter_employees`. PHC will not query `fusionlab` or IAM tables directly.
- `get_users(user_ids: Sequence[int])` for batched names on staff lists and display-only details; missing optional identity fields must not fail a request.

The approved batched `modules.directory.contracts.is_employee(user_ids: Sequence[int])` contract is implemented over the existing local directory projection populated by IAM `iter_employees`. It returns matching employee IDs; PHC never queries IAM or ERP directly. No IAM endpoint or client method was added.

## (g) Scheduled work

| Task | Cadence | Queue | Effect / failure consequence |
|---|---|---|---|
| `phc.deliver_notifications` | Every 60 seconds, expiring before the next tick | `notifications` | Delivers committed reimbursement and requisition status notifications. Low-stock alerts are persisted and displayed by the alert endpoint, without outbox notifications. A stalled task delays notifications but does not roll back or duplicate business transitions; outbox idempotency makes redelivery safe. |

No claim or inventory state expires on a clock. The 30-day rule is evaluated synchronously at submission and uses the effective policy active on the submission date. No other Celery beat entry is needed.

## (h) Open questions and accepted gaps

The following implementation decisions are settled by the written approval below. They are recorded here as accepted blueprint resolutions, not as unresolved gaps.

| Blueprint gap | Approved resolution |
|---|---|
| Claim financial fields | Store `claim_amount` as decimal, `expense_date`, optional text `bill_reference`, and optional text `remarks`. Do not add file uploads absent a separate requirement. |
| Initial reimbursement policy | Seed an immutable 30-calendar-day policy effective 2026-01-01. The 30th day is inclusive; future expense dates are refused. |
| Doctor and schedule shape | Doctor has display name, specialization, active flag. Weekly slots store weekday and local start/end time; schedule state is `draft` or `published`. Reject overlap for the same doctor and weekday. |
| Inventory | Item name, unit (default `units`), positive integer reorder threshold; quantity is a non-negative integer derived from append-only movements. Do not seed sample production items. |
| Employee verification | Add batched `is_employee(user_ids)` to `modules/directory/contracts.py`, backed by existing IAM `iter_employees`. PHC performs no direct IAM or ERP query. |
| PDF export | Use `patient_user_id` as identifier and include chronological visits (date and clinical notes) and linked prescriptions (issue date and details). ReportLab is approved and is now a project dependency. The endpoint returns selected caller-owned visits chronologically, with the patient ID, visit notes and linked prescription details. |
| Requisition, ambulance and advisory fields | Requisitions contain item and quantity; ambulance usage stores timestamp, patient name and destination; advisories have title, body and published_at. Add no extra workflow branches. |
| Audit retention | PHC audit events are append-only and retained indefinitely; no automatic purge. |
| PHC Staff clinical access | `Compounder` creates visits/prescriptions and views PHC clinical records. Patients have read-only, self-scoped access. |

The decisions in section (h) are settled and implemented. The only open build item is whether a Unicode font asset may be bundled to render Devanagari and other non-Latin clinical text; ReportLab built-in fonts cannot render those scripts.

Approval record (2026-11-23): “Blueprint and open-gap decisions approved on 2026-11-23 (solo execution by Apurva Verma, 24BEC013; acting as approver for the module blueprint). I approve the PHC module blueprint (sections a–g) and settle/accept the open questions (section h) as follows.” The approver accepted the original h-items and supplied the specifics recorded in this section. This includes the `modules/directory/contracts.py` employee-check change. A separate approval dated 2026-11-23 authorized version-2 manifest support in the IAM seeder (while retaining v1) and adding ReportLab for `POST /api/v1/phc/records/pdf` / `PHC-UC-03`.
