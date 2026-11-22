# Hostel Management (hostel) — Architectural Blueprint

**Module Name**: Hostel Management  
**Module Code**: `hostel`  
**Docs Directory**: `docs/15-hostel/`  
**Environment**: `module-only`  
**Author**: Student 1 (Akshar Jasoliya - 24BCS101)  
**Approver**: Student 2 (24BCS071)  

---

## §3.1 — Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-HM-001 | Hostel-Specific Role Binding and Change Recording | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-002 | Student Hostel-Specific Access Basis | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-003 | Super Admin Institution-Level Access Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-004 | Time-Bound Role Validity Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-005 | RBAC Data and Function Restriction | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-006 | Role Reassignment Pending-Record Visibility | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-007 | Operational Handover Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-008 | Allotment Algorithm Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-009 | Room Assignment History Retention | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-010 | Room Capacity Limit Enforcement | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-011 | Attendance Record Retention | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-012 | Attendance Procedure Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-013 | Leave History Retention | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-014 | External Leave Policy Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-015 | Complaint Core Data Capture | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-016 | Hostel-Related Complaint Scope | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-017 | Central Complaint Integration Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-018 | Guest-Room Booking History Retention | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-019 | Guest-Room Booking Scope Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-020 | Extended-Stay Charge Recording Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-021 | Extended-Stay Compliance Recording Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-022 | Extended-Stay Application Window Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-023 | Extended-Stay Payment Processing Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-024 | Extended-Stay Appeal and Expedited Handling Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-025 | Fine Mandatory Data Fields | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-026 | Fine Lifecycle and Policy Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-027 | Inventory and Staff Coordination Boundary and Logging | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-028 | Security Scope Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-029 | Assigned-Hostel Notice Publishing | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-030 | Notice History Retention | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-031 | Authorized Notice Board Visibility | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-032 | Predefined HM Reports Boundary | domain | `modules/hostel/domain/policies.py` | Core Business Rule |
| BR-HM-033 | Advanced Analytics Exclusion | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-034 | Configured Notification Event Scope | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| BR-HM-035 | Caretaker Assigned Hostel and Shift Context | selectors | `modules/hostel/selectors/scoping.py` | Core Business Rule |
| HM-UC-001 | Create Hostel Record | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-002 | Activate or Deactivate Hostel Record | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-003 | Manage Warden Role Binding | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-004 | Manage Caretaker Role Binding | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-005 | Submit Hostel Accommodation Request | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-006 | Record Hostel and Room Allotment Decisions | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-007 | Record Central Re-allotment or Formal Room-Vacation Update | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-008 | View Room Allocation Information | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-009 | Maintain Room Availability and Occupancy | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-010 | Record Individual Room Exchange | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-011 | Review Room Assignments and Occupancy | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-012 | Record and Monitor Student Attendance | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-013 | View Own Attendance Information | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-014 | Submit Leave Request | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-015 | Review and Record Leave Decision | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-016 | View Own Leave Status and History | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-017 | Submit Hostel-Related Complaint | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-018 | Review, Update, and Escalate Complaint | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-019 | Monitor Complaint Status and History | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-020 | Submit Guest Room Booking Request | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-021 | Review Guest Room Booking Request | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-022 | View Own Guest-Room Booking Status | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-023 | Submit Extended-Stay Request | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-024 | Review and Record Extended-Stay Decision | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-025 | Record Extended-Stay Charge or Compliance Information | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-026 | Record Hostel Fine | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-027 | View Own Fine Records and History | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-028 | Maintain Hostel Inventory Records | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-029 | Maintain or View Hostel-Operational Staff Coordination Information | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-030 | Maintain Security Guard Shift Schedule | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-031 | Publish Hostel Notice or Announcement | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-032 | View Hostel Notices | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-033 | Generate Reports and Operational Summaries | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-034 | Issue HM Notifications or Status Updates | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-035 | Retired as standalone RBAC access UC | N/A (retired) | Retired | Cross-cutting RBAC covered by BR-HM-002–007 |
| HM-UC-036 | Review Attendance Summaries, Trends, and Exceptions | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-037 | Review Leave Information and Summaries | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-038 | Review Fine Summaries and Disciplinary Patterns | services / api | `modules/hostel/services/` | Active Use Case |
| HM-UC-039 | Review Hostel-Operational Staff Assignments or Shift Information | services / api | `modules/hostel/services/` | Active Use Case |
| BW-HM-01 | Accommodation Request to Initial Allotment | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-02 | Leave Approval Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-03 | Leave Rejection Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-04 | Complaint Resolution Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-05 | Complaint Escalation Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-06 | Guest-Room Booking Approval Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-07 | Guest-Room Booking Rejection Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-08 | Extended-Stay Approval Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| BW-HM-09 | Extended-Stay Rejection Path | domain / services | `modules/hostel/domain/state_machines.py` | State transition path |
| AFR-HM-001 | The system shall allow the Super Admin to create hostel records. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-001) |
| AFR-HM-002 | The system shall allow the Super Admin to activate or deactivate hostel records. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-001) |
| AFR-HM-003 | The system shall allow the Super Admin to assign, reassign, activate, and deactivate Warden role bindings for hostels. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-004 | The system shall allow the Super Admin to assign, reassign, activate, and deactivate Caretaker role bindings for hostels. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-005 | The system shall maintain hostel-specific role bindings and record role changes made by the Super Admin. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-006 | The system shall allow Students to submit hostel accommodation requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-003) |
| AFR-HM-007 | The system shall record accommodation application details and status. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-003) |
| AFR-HM-008 | The system shall allow the Super Admin to record hostel and room allotment decisions in batch-oriented institutional processes. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-009 | The system shall allow the Super Admin to manage centrally controlled room re-allotments and formal room-vacation updates. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-010 | The system shall record allotment decisions and update room assignment information without prescribing an allotment algorithm unless explicitly specified. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-011 | The system shall maintain room assignment history for audit, traceability, and review. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-012 | The system shall allow Students to view their own current and historical room allocation information. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-005) |
| AFR-HM-013 | The system shall allow Caretakers to maintain hostel-level room availability and occupancy information. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-006) |
| AFR-HM-014 | The system shall update room occupancy based on approved allotments, re-allotments, formal room-vacation updates, and recorded individual exchanges. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-015 | The system shall allow Caretakers to record individual room exchange operations within their assigned hostel. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-007) |
| AFR-HM-016 | The system shall prevent room occupancy from exceeding defined room capacity. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-017 | The system shall update occupancy records after allotments, re-allotments, formal room-vacation updates, and recorded room exchanges. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-004) |
| AFR-HM-018 | The system shall allow Wardens to review room assignments and occupancy patterns for planning, discipline, and compliance-oriented oversight. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-008) |
| AFR-HM-019 | The system shall maintain up-to-date room status information needed for hostel operations. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-006) |
| AFR-HM-020 | The system shall allow Caretakers to record and monitor student attendance. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-009) |
| AFR-HM-021 | The system shall make attendance information available for leave review, disciplinary review, reporting, and supervisory oversight. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-009) |
| AFR-HM-022 | The system shall allow Wardens to view attendance summaries, trends, and exceptions for oversight. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-010) |
| AFR-HM-023 | The system shall retain attendance records for reporting, monitoring, and compliance-oriented review. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-009) |
| AFR-HM-024 | The system shall allow Students to view attendance status or attendance-related information made available to them. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-010) |
| AFR-HM-025 | The detailed hostel attendance-taking procedure shall remain outside HM system scope unless explicitly specified as system-enforced rules or configured workflow. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-011) |
| AFR-HM-026 | The system shall allow Students to submit leave requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-012) |
| AFR-HM-027 | The system shall provide fields for supporting leave information or documents where such fields are configured in the leave-request form. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-012) |
| AFR-HM-028 | The system shall allow Caretakers to review leave requests and record approval or rejection decisions. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-013) |
| AFR-HM-029 | The system shall issue status updates to Students for submitted leave requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-013) |
| AFR-HM-030 | The system shall make leave records available for attendance-related review, security coordination, and supervisory planning where such visibility is supported. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-014) |
| AFR-HM-031 | The system shall retain leave history for audit, review, and reporting. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-014) |
| AFR-HM-032 | The system shall allow Students to view leave status and leave-history information made available to them. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-014) |
| AFR-HM-033 | The system shall allow Wardens to review leave information and leave summaries for oversight, control, and supervisory planning. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-014) |
| AFR-HM-034 | External leave eligibility rules, approval hierarchies, document rules, and institutional leave policy shall remain outside HM system-scoring scope unless explicitly specified as system-enforced or system-routed behavior. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-015) |
| AFR-HM-035 | The system shall allow Students to submit hostel-related complaints. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-016) |
| AFR-HM-036 | The system shall capture complaint category and description, and shall support optional attachment capture where the complaint form provides such a field. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-016) |
| AFR-HM-037 | The system shall allow Caretakers to review hostel-related complaints, record action taken, update complaint status, and escalate unresolved or supervisory complaints to the Warden when escalation is supported by the HM workflow. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-017) |
| AFR-HM-038 | The system shall allow Wardens to monitor unresolved, delayed, or escalated hostel-related complaints. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-017) |
| AFR-HM-039 | The system shall track complaint history and resolution status for review and reporting. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-017) |
| AFR-HM-040 | The HM module shall cover hostel-related complaints only. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-018) |
| AFR-HM-041 | If a central Complaint Management module exists, HM shall handle hostel-local complaints or record/escalate hostel complaints only according to explicitly defined integration scope. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-018) |
| AFR-HM-042 | Non-hostel complaints shall remain outside HM scope. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-018) |
| AFR-HM-043 | The system shall allow Students to submit guest-room booking requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-019) |
| AFR-HM-044 | The system shall record guest-room booking requests and provide guest-room availability information needed for approval or rejection decisions. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-019) |
| AFR-HM-045 | The system shall allow Caretakers to verify guest-room availability and record approval or rejection decisions for guest-room booking requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-019) |
| AFR-HM-046 | The system shall maintain guest-room booking history for audit, planning, and security-oriented review. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-019) |
| AFR-HM-047 | Guest-room management in HM shall be limited to booking-request handling and booking-status tracking. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-020) |
| AFR-HM-048 | Guest check-in, guest check-out, room inspection, guest-room charge collection, and settlement shall remain outside HM scope unless explicitly integrated. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-020) |
| AFR-HM-049 | The system shall allow Students to submit extended-stay requests during vacations or semester breaks. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-021) |
| AFR-HM-050 | The system shall record the extended-stay request, requested period, and decision status. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-021) |
| AFR-HM-051 | The system shall record applicable payment, charge, or fee amount for extended stay where such charges are applicable and represented in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-022) |
| AFR-HM-052 | The system shall record payment deadline and payment/deadline compliance status relevant to extended-stay decision and continuation of stay where such information is maintained in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-022) |
| AFR-HM-053 | The system shall allow the Warden to record approval or rejection of extended-stay requests. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-021) |
| AFR-HM-054 | The system shall make extended-stay request details, payment/deadline compliance information where configured, and decision status visible to the Warden. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-021) |
| AFR-HM-055 | Application-window enforcement for extended-stay requests shall remain outside HM scope unless a configured application window is explicitly provided and enforced by the system. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-023) |
| AFR-HM-056 | Actual payment collection, receipt generation, financial settlement, and accounting reconciliation for extended stay shall remain outside HM scope unless explicitly integrated with the institute payment/accounting module. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-023) |
| AFR-HM-057 | Appeal handling and expedited handling for extended-stay requests shall remain outside HM scope. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-023) |
| AFR-HM-058 | The system shall allow Caretakers to record fines imposed for hostel-related rule violations, damages, or disciplinary reasons. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-024) |
| AFR-HM-059 | Each fine record shall include at least the reason, amount, date, and affected student reference. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-024) |
| AFR-HM-060 | The system shall allow Students to view imposed fines and fine history relevant to them. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-024) |
| AFR-HM-061 | The system shall allow Wardens to review fine summaries and disciplinary patterns for oversight. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-024) |
| AFR-HM-062 | Fine payment, waiver, settlement, and appeal handling shall remain outside HM scope. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-025) |
| AFR-HM-063 | Fine-reason policy validation shall remain outside HM system-scoring scope unless explicitly specified as system-enforced behavior. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-025) |
| AFR-HM-064 | The system shall allow Caretakers to maintain hostel-operational inventory records relevant to hostel functioning. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-026) |
| AFR-HM-065 | The system shall allow authorized hostel roles to view or maintain hostel-operational staff coordination information such as assigned staff, duty/shift information, or contact/reference information where such records are maintained in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-026) |
| AFR-HM-066 | The system shall allow Wardens and Super Admin to review relevant hostel-operational staff assignments or shift information made available through the system. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-026) |
| AFR-HM-067 | The system shall log inventory updates and usage-relevant changes maintained in HM for accountability. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-026) |
| AFR-HM-068 | HM inventory and staff coordination shall be limited to hostel-operational records, visibility, and accountability logs. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-026) |
| AFR-HM-069 | Procurement, stock purchase, payroll, formal HR records, and employee service administration shall remain outside HM scope unless explicitly integrated. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-027) |
| AFR-HM-070 | The system shall allow Wardens to maintain, update, and review hostel-level security guard shift schedules. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-028) |
| AFR-HM-071 | The system shall make security-related schedules and records maintained in HM available for monitoring and review. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-028) |
| AFR-HM-072 | Detailed incident investigation workflows, security staff employment records, payroll, and non-hostel security administration shall remain outside HM scope unless explicitly specified. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-029) |
| AFR-HM-073 | The system shall allow Caretakers and Wardens to publish hostel notices and announcements for hostels assigned to them in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-030) |
| AFR-HM-074 | The system shall provide Students visibility or notification for relevant notices and announcements. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-030) |
| AFR-HM-075 | The system shall maintain notice history for reference, transparency, and auditability. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-030) |
| AFR-HM-076 | The system shall provide a hostel notice board for displaying relevant notices and announcements to authorized users. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-030) |
| AFR-HM-077 | The system shall support predefined reports and operational summaries derived from HM records. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-078 | The system shall provide occupancy and room-utilization reports. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-079 | The system shall provide attendance and leave summaries. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-080 | The system shall provide fine and disciplinary summaries. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-081 | The system shall provide complaint and resolution statistics. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-082 | The system shall provide extended-stay summaries. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-083 | The system shall provide hostel-level operational reports for Caretakers. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-084 | The system shall provide supervisory reports for Wardens. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-085 | The system shall provide institution-level or cross-hostel monitoring reports for Super Admin. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-031) |
| AFR-HM-086 | Advanced analytics, predictive analysis, or external data analysis shall remain outside HM scope unless explicitly specified. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-032) |
| AFR-HM-087 | The system shall issue notifications or status updates to relevant users for supported HM events through the Fusion notification infrastructure or a configured notification mechanism. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-088 | Supported notification/status-update events shall include room allotment and room allocation changes. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-089 | Supported notification/status-update events shall include leave request submission and leave decisions. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-090 | Supported notification/status-update events shall include complaint submission, complaint update, and complaint resolution. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-091 | Supported notification/status-update events shall include guest-room booking status. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-092 | Supported notification/status-update events shall include extended-stay request status. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-093 | Supported notification/status-update events shall include payment/deadline alerts where such information is maintained in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-094 | Supported notification/status-update events shall include fine imposition. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-095 | Supported notification/status-update events shall include notices and announcements. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-033) |
| AFR-HM-096 | The system shall support Caretaker operations within the assigned hostel and shift context. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-034) |
| AFR-HM-097 | The system shall maintain hostel-specific Warden and Caretaker role assignments. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-098 | The system shall apply hostel-specific access control for Students based on their hostel allocation or relevant student-hostel association. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-035) |
| AFR-HM-099 | Super Admin access shall be institution-level unless explicitly restricted by HM configuration. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-036) |
| AFR-HM-100 | The system shall record role activation/deactivation status for hostel-specific Warden and Caretaker bindings. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-101 | Time-bound role validity shall be in scope only if start and end dates are configured and enforced in HM. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-037) |
| AFR-HM-102 | Role changes shall take effect when recorded by the Super Admin in the system. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-002) |
| AFR-HM-103 | When a Warden or Caretaker role is reassigned, the newly assigned role holder shall be able to view pending HM records associated with the assigned hostel, subject to RBAC. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-038) |
| AFR-HM-104 | Operational handover outside system-visible responsibility records shall remain outside HM scope. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-038) |
| AFR-HM-105 | RBAC shall ensure users access only the hostel data and functions permitted for their role and hostel assignment. | domain / services / models | `modules/hostel/` | Atomic Functional Requirement (CFR-HM-039) |

---

## §3.2 — Domain Model

All tables reside in `fusion_integrated` and are namespaced with `hostel_`.

### Entities & Invariants:

- **`Hostel`**: Physical hostel building. Invariant: `name` and `code` unique.

- **`HostelRoleBinding`**: Active role bindings for Warden and Caretaker scoped to a hostel.

- **`Room`**: Rooms belonging to a hostel. Invariant: `(hostel, room_number)` unique. `capacity` positive integer.

- **`AccommodationRequest`**: Student requests for accommodation.

- **`RoomAllotment`**: Assignment of student `user_id` to `Room`. Invariant: Concurrent active occupancy <= Room.capacity.

- **`RoomExchange`**: Individual student room exchange record within assigned hostel.

- **`StudentAttendance`**: Date, student `user_id`, hostel, status (present/absent), marked_by.

- **`LeaveRequest`**: Student leave request with state machine (`PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`).

- **`HostelComplaint`**: Complaint tracking with escalation state machine (`LOGGED`, `IN_PROGRESS`, `ESCALATED`, `RESOLVED`, `CLOSED`).

- **`GuestRoomBooking`**: Guest room booking request with state machine (`REQUESTED`, `APPROVED`, `REJECTED`, `CANCELLED`).

- **`ExtendedStayRequest`**: Vacation/break stay request with state machine (`SUBMITTED`, `APPROVED`, `REJECTED`).

- **`HostelFine`**: Fine assessment record (student `user_id`, amount, reason, date, status).

- **`HostelInventory`**: Physical inventory items, counts, conditions.

- **`SecurityShift`**: Guard shift assignment and schedule.

- **`HostelNotice`**: Published notices visible to residents of specific hostels.


---

## §3.3 — Declarative State Machines

State machines defined as immutable transition tables in `modules/hostel/domain/state_machines.py`:

```python
LEAVE_TRANSITIONS = {
    ("PENDING", "approve", "caretaker"): "APPROVED",
    ("PENDING", "reject", "caretaker"): "REJECTED",
    ("PENDING", "cancel", "student"): "CANCELLED",
}

COMPLAINT_TRANSITIONS = {
    ("LOGGED", "start_review", "caretaker"): "IN_PROGRESS",
    ("IN_PROGRESS", "escalate", "caretaker"): "ESCALATED",
    ("IN_PROGRESS", "resolve", "caretaker"): "RESOLVED",
    ("ESCALATED", "resolve", "warden"): "RESOLVED",
    ("RESOLVED", "close", "student"): "CLOSED",
}

GUEST_ROOM_TRANSITIONS = {
    ("REQUESTED", "approve", "caretaker"): "APPROVED",
    ("REQUESTED", "reject", "caretaker"): "REJECTED",
    ("REQUESTED", "cancel", "student"): "CANCELLED",
}

EXTENDED_STAY_TRANSITIONS = {
    ("SUBMITTED", "approve", "warden"): "APPROVED",
    ("SUBMITTED", "reject", "warden"): "REJECTED",
}
```


---

## §3.4 — Permission List & Registry Specification

Module registration: `MODULE["code"] = "hostel"`, `base_path = "/hostel"`.

Permissions conform to `<module>.<resource>.<action>` with closed verb list:

- `hostel.accommodation.create` (Student)

- `hostel.accommodation.view` (Student / Staff)

- `hostel.allotment.manage` (Super Admin)

- `hostel.room.manage` (Super Admin / Caretaker)

- `hostel.room.view` (Student / Staff / Caretaker / Warden)

- `hostel.leave.create` (Student)

- `hostel.leave.review` (Caretaker)

- `hostel.leave.view` (Student / Caretaker / Warden)

- `hostel.complaint.create` (Student)

- `hostel.complaint.review` (Caretaker / Warden)

- `hostel.complaint.view` (Student / Caretaker / Warden)

- `hostel.guest_room.create` (Student)

- `hostel.guest_room.review` (Caretaker)

- `hostel.extended_stay.create` (Student)

- `hostel.extended_stay.review` (Warden)

- `hostel.attendance.create` (Caretaker)

- `hostel.attendance.view` (Student / Caretaker / Warden)

- `hostel.fine.create` (Caretaker / Warden)

- `hostel.fine.view` (Student / Caretaker / Warden)

- `hostel.notice.publish` (Caretaker / Warden)

- `hostel.notice.view` (All authenticated residents)

- `hostel.inventory.manage` (Caretaker)

- `hostel.security.manage` (Warden)

- `hostel.report.view` (Warden / Super Admin)


---

## §3.5 — Endpoint List

| Method | URL Path | Permission Gate | Scope Narrowing | Description |
|---|---|---|---|---|
| GET | `/api/v1/hostel/hostels/` | `hostel.room.view` | Active / Assigned hostels | List hostels |
| POST | `/api/v1/hostel/hostels/` | `hostel.room.manage` | Global admin | Create hostel |
| GET | `/api/v1/hostel/accommodations/` | `hostel.accommodation.view` | User scope / Admin | List requests |
| POST | `/api/v1/hostel/accommodations/` | `hostel.accommodation.create` | Self student | Submit accommodation |
| GET | `/api/v1/hostel/leaves/` | `hostel.leave.view` | Student self / Caretaker hostel | List leaves |
| POST | `/api/v1/hostel/leaves/` | `hostel.leave.create` | Self student | Submit leave request |
| POST | `/api/v1/hostel/leaves/{id}/action/` | `hostel.leave.review` | Caretaker assigned hostel | Approve/Reject leave |
| GET | `/api/v1/hostel/complaints/` | `hostel.complaint.view` | Student self / Caretaker / Warden | List complaints |
| POST | `/api/v1/hostel/complaints/` | `hostel.complaint.create` | Self student | Submit complaint |
| POST | `/api/v1/hostel/complaints/{id}/action/` | `hostel.complaint.review` | Caretaker / Warden | Update/Escalate/Resolve complaint |
| GET | `/api/v1/hostel/attendances/` | `hostel.attendance.view` | Student self / Caretaker hostel | List attendance |
| POST | `/api/v1/hostel/attendances/` | `hostel.attendance.create` | Caretaker hostel | Record attendance |
| GET | `/api/v1/hostel/fines/` | `hostel.fine.view` | Student self / Caretaker / Warden | List fines |
| POST | `/api/v1/hostel/fines/` | `hostel.fine.create` | Caretaker / Warden | Impose fine |
| GET | `/api/v1/hostel/notices/` | `hostel.notice.view` | Visible to hostel residents | List notices |
| POST | `/api/v1/hostel/notices/` | `hostel.notice.publish` | Caretaker / Warden | Publish notice |
| GET | `/api/v1/hostel/reports/summary/` | `hostel.report.view` | Warden / Admin | Summary operational report |

---

## §3.6 — Contracts

`modules/hostel/contracts.py` exposes plural getters:

- `get_student_hostel_allocations(user_ids: Sequence[int]) -> Sequence[dict]`

- `get_hostel_summaries(hostel_ids: Sequence[int]) -> Sequence[dict]`

External dependencies: Uses `modules.directory.contracts.py` for student profile information.


---

## §3.7 — Scheduled Work

Celery beat schedule in `modules/hostel/schedule.py`:

- `hostel.auto_expire_guest_bookings`: Runs daily at 00:00. Cancels unapproved past booking dates.

- `hostel.attendance_daily_summary`: Runs daily at 23:00. Aggregates daily absenteeism exceptions.


---

## §3.8 — Open Questions & Approvals

1. **Extended-stay charges (ISS-HM-014)**: System records charge metadata without collecting live payment in module-only environment. (Approved by Student 2)

2. **Role designations**: Caretaker and Warden are mapped to functional/office roles with hostel-specific binding stored in `hostel_role_binding`. (Approved by Student 2)

3. **Approval Record**: Blueprint approved in writing by Student 2 (24BCS071) on 2026-11-16.
