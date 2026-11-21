# HR-EIS module blueprint  -  Assignment 9 (Phase 2)

**Status:** DRAFT / NOT APPROVED  -  implementation gate closed. Prepared by Student 1 (24BCS230), paired with Student 2 (24BCS163), pair 2. Approval must come in writing from Student 2; a message from Student 1 is not sufficient.

- **Module:** Human Resource / Employee Information System (HR-EIS), code `hreis`, module-only environment, docs `docs/09-hreis/`.
- **Spec folder:** `D:\HR(EIS)\specifications`, six source files including `06_HR_Traceability_Matrix_v1.3_FINAL.xlsx`.
- **Implementation snapshot:** `D:\fusion\Fusion-Integrated-A9-HREIS`, `module/hreis`, upstream `5595be6628b4cdc6f8b47cf74bac267a2470f780` at design preparation. This is not an approved code change or a design-freeze commit.
- **Architecture:** only Fusion-Integrated + Fusion_System_Administrator; public `fusion-dev.dump`, three isolated DBs; reference module `modules/placement`.
- **Inventory:** 14 live CFR + 107 live AFR + 21 live UC + 34 live BR + 17 live workflows (13 basis BW + 4 composite CW) = **193 traceability entries**. Do not count retired `HR-UC-020` or retired `BR-HR-032` as live. UC-020 is replaced by event-based `HR-UC-021` / `HR-UC-022`; BR-032's notification delivery rules moved to live AFR/notification requirements.
- **RTM caveat:** the supplied Excel matrix's UC/BR/workflow-to-AFR mapping cells are empty; the mappings below were derived from the actual specification language, not inferred from those empty cells.

## 3.1  -  Traceability: all live source obligations

Each requirement/BR row represents the written obligation; each UC row includes the main success/alternative/exception behavior; each workflow row maps the explicit finite path or composite lifecycle. The final column identifies boundary conditions, not permission to invent missing policy. Before implementation Student 2 must confirm unresolved scope/actor issues in Section 3.8.

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| HR-CFR-001 | HR-EIS shall enforce Fusion-assigned role-based access across module functions, support authorized multi-role use, restrict sensitive and employee-specific data appropriately, prevent unauthorized access or modification, and respect institutional control of role assignment and reassignment. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-CFR-002 | HR-EIS shall allow an Employee to initiate supported HR requests and track the status of the Employee's own submitted requests. | services/ + selectors/ | `request_service.py / request_scoping.py` | Preserve owner scope and a complete status history. |
| HR-CFR-003 | HR-EIS shall select and enforce the applicable approval authority and configured request progression by employee category and request type, support approved/rejected/forwarded outcomes where applicable, enforce authority RBAC, and prevent bypass or alteration of workflow order. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-CFR-004 | HR-EIS shall provide the HR Administrator with authorized capabilities to manage employee master/service records, perform supported HR-request verification, configure in-scope workflow settings, assign appraisal reviewers, and review compliance/audit information. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-CFR-005 | HR-EIS shall allow the Accountant to verify financial correctness and record HR-EIS-side processing for approved LTC and CPDA claims, including payment or disbursement status received from payroll or finance systems. | domain/ + services/ | `claims.py / record_financial_processing()` | Do not settle money; reject missing financial policy and unapproved claim. |
| HR-CFR-006 | HR-EIS shall maintain a centralized authoritative service record for each employee with the specified record content, restrict official record creation/modification to HR Administrators, provide Employees read-only access to their own records, and preserve record consistency during updates. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-CFR-007 | HR-EIS shall support Employee leave application for the stated leave types, require and validate the specified request information, route valid requests through the applicable approval hierarchy, update leave balance on approval, and permanently log leave transactions. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-CFR-008 | HR-EIS shall support yearly appraisal submission within configured windows, reviewer assignment, review/finalization through designated authorities, archival of finalized appraisals in the service record, and immutability after closure. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-CFR-009 | HR-EIS shall support LTC advance and reimbursement submission using prescribed forms, HR verification of documentation and eligibility, approval routing, Accountant-side settlement recording, payment-status linkage, and retention of audit history for rejected or returned requests. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-CFR-010 | HR-EIS shall support CPDA advance and reimbursement requests with required purpose, amount, and supporting documents, HR verification before approval routing, Accountant processing of approved claims, and auditable disbursement recording. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-CFR-011 | HR-EIS shall generate and expose notifications for request submissions, approval/rejection/forwarding events, pending-action reminders, and configured policy/deadline updates, with delivery through the Fusion dashboard and official email path. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-CFR-012 | HR-EIS shall log HR transactions with actor identity, timestamp, and action, keep audit logs immutable and access-controlled, and support authorized compliance review using logged HR-EIS evidence. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-CFR-013 | HR-EIS shall exchange relevant claim-status/accounting information with payroll and finance systems and identity/role-consistency information with other Fusion modules, with automatic real-time synchronization where configured and without taking ownership of external-system execution semantics. | contracts/ + adapters/ | `iam_projection / finance status adapter` | External status only; no ERP writes, payroll or salaries. |
| HR-CFR-014 | HR-EIS shall not modify payroll rules or salary structures while recording and exchanging supported HR-related financial statuses. | contracts/ + services/ | `finance boundary / deny writes` | No HR-EIS payroll computation, execution or salary rule edits. |
| HR-AFR-001 | HR-EIS shall operate under Fusion RBAC for actor permissions. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-094 | HR-EIS shall enforce Fusion RBAC for HR-EIS functions. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-095 | HR-EIS shall support users holding multiple roles simultaneously. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-096 | HR-EIS shall allow role assignment only by institutional authorities. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-097 | HR-EIS shall allow role reassignment only by institutional authorities. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-098 | HR-EIS shall restrict access to sensitive data to authorized roles only. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-099 | HR-EIS shall restrict Employees to accessing only their own employee data. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-100 | HR-EIS shall prevent unauthorized access to HR-EIS data. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-101 | HR-EIS shall prevent unauthorized modification of HR-EIS data. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | IAM grants and record-level scope are independent; sensitive rows return 404. |
| HR-AFR-002 | HR-EIS shall allow an Employee to submit HR-related requests. | services/ + selectors/ | `request_service.py / request_scoping.py` | Preserve owner scope and a complete status history. |
| HR-AFR-004 | HR-EIS shall allow an Employee to track statuses of HR-related requests submitted by the Employee. | services/ + selectors/ | `request_service.py / request_scoping.py` | Preserve owner scope and a complete status history. |
| HR-AFR-006 | HR-EIS shall route department-level approvals to the Head of Department where applicable. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-007 | HR-EIS shall route non-teaching staff approvals to the Registrar where applicable. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-008 | HR-EIS shall route faculty-level approvals to the Director where applicable. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-009 | HR-EIS shall determine approval authority strictly by employee category and request type. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-070 | HR-EIS shall route all HR requests through rule-based workflows. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-071 | HR-EIS shall support the request outcome or transition: Approved. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-072 | HR-EIS shall support the request outcome or transition: Rejected. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-073 | HR-EIS shall support the request outcome or transition: Forwarded to next authority. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-074 | HR-EIS shall enforce authority roles using RBAC during HR request workflows. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-075 | HR-EIS shall prevent any authority from bypassing workflow order. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-076 | HR-EIS shall prevent any authority from altering workflow order. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-106 | HR-EIS shall not allow manual bypass of approval workflows. | domain/ + services/ | `workflow.py / transition_request()` | Route is a versioned, configured policy; forwarding never skips authority. |
| HR-AFR-010 | HR-EIS shall allow HR Administrator to manage employee master and service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-011 | HR-EIS shall allow HR Administrator to verify HR requests. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-012 | HR-EIS shall allow HR Administrator to configure HR workflows where configuration is within HR-EIS scope. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-013 | HR-EIS shall allow HR Administrator to assign appraisal reviewers. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-014 | HR-EIS shall allow HR Administrator to monitor compliance and audits using authorized HR-EIS records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-015 | HR-EIS shall allow Accountant to process approved LTC claims for financial settlement recording. | domain/ + services/ | `claims.py / record_financial_processing()` | Do not settle money; reject missing financial policy and unapproved claim. |
| HR-AFR-016 | HR-EIS shall allow Accountant to process approved CPDA claims for financial settlement recording. | domain/ + services/ | `claims.py / record_financial_processing()` | Do not settle money; reject missing financial policy and unapproved claim. |
| HR-AFR-017 | HR-EIS shall allow Accountant to verify financial correctness of LTC and CPDA claims. | domain/ + services/ | `claims.py / record_financial_processing()` | Do not settle money; reject missing financial policy and unapproved claim. |
| HR-AFR-018 | HR-EIS shall record payment or disbursement status for approved financial claims when received from payroll or finance systems. | domain/ + services/ | `claims.py / record_financial_processing()` | Do not settle money; reject missing financial policy and unapproved claim. |
| HR-AFR-003 | HR-EIS shall allow an Employee to view the Employee's own service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-019 | HR-EIS shall maintain a centralized service record for each employee. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-020 | HR-EIS shall include appointment details in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-021 | HR-EIS shall include department in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-022 | HR-EIS shall include designation in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-023 | HR-EIS shall include service history in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-024 | HR-EIS shall include leave balances in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-025 | HR-EIS shall include retirement status in the employee service record. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-026 | HR-EIS shall restrict creation of employee service records to HR Administrators. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-027 | HR-EIS shall restrict modification of employee service records to HR Administrators. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-028 | HR-EIS shall allow Employees to view their own service records in read-only mode. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-102 | HR-EIS shall preserve service record consistency during updates. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-103 | HR-EIS shall prevent partial updates from corrupting service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-107 | HR-EIS shall not permit Employees to alter official service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Employee read-only; HR-admin audited atomic update. |
| HR-AFR-029 | HR-EIS shall allow Employees to apply for leave requests. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-030 | HR-EIS shall support Casual leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-031 | HR-EIS shall support Restricted leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-032 | HR-EIS shall support Medical leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-033 | HR-EIS shall support Earned leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-034 | HR-EIS shall support Vacation leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-035 | HR-EIS shall support Sabbatical leave as an available leave request type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-036 | HR-EIS shall require each leave request to specify leave type. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-037 | HR-EIS shall require each leave request to specify leave duration. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-038 | HR-EIS shall require each leave request to specify justification. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-039 | HR-EIS shall validate leave balance before accepting a leave request submission. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-040 | HR-EIS shall validate leave eligibility before accepting a leave request submission. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-041 | HR-EIS shall route leave requests through a predefined approval hierarchy. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-042 | HR-EIS shall update leave balances automatically when leave is approved. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-043 | HR-EIS shall permanently log all leave transactions. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Six named types; checked eligibility; balance changed only on approval. |
| HR-AFR-044 | HR-EIS shall allow Employees to submit yearly appraisal forms. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-045 | HR-EIS shall restrict yearly appraisal form submission to configured submission windows. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-046 | HR-EIS shall allow HR Administrator to assign reviewers for appraisal evaluation. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-047 | HR-EIS shall route appraisal workflows through designated authorities for review and finalization. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-048 | HR-EIS shall archive finalized appraisals in the employee service record. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-049 | HR-EIS shall prevent modification of appraisal records after closure. | domain/ + services/ | `appraisal.py / transition_request()` | Configured annual window and reviewers; final archive immutable. |
| HR-AFR-050 | HR-EIS shall allow Employees to submit LTC advance requests using prescribed forms. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-051 | HR-EIS shall allow Employees to submit LTC reimbursement requests using prescribed forms. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-052 | HR-EIS shall allow HR Administrator to verify LTC documentation. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-053 | HR-EIS shall allow HR Administrator to verify LTC eligibility. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-054 | HR-EIS shall route verified LTC requests through the approval hierarchy. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-055 | HR-EIS shall allow Accountant to process approved LTC claims for financial settlement recording. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-056 | HR-EIS shall record payment status for LTC claims. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-057 | HR-EIS shall link LTC payment status to payroll systems without modifying payroll rules. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-058 | HR-EIS shall retain full audit history for rejected LTC requests. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-059 | HR-EIS shall retain full audit history for returned LTC requests. | domain/ + services/ | `claims.py / transition_request()` | LTC subtype; documentation; HR verification precedes approvals. |
| HR-AFR-060 | HR-EIS shall allow Employees to submit CPDA advance requests. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-061 | HR-EIS shall allow Employees to submit CPDA reimbursement requests. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-062 | HR-EIS shall require each CPDA request to include purpose. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-063 | HR-EIS shall require each CPDA request to include amount. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-064 | HR-EIS shall require each CPDA request to include supporting documents. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-065 | HR-EIS shall allow HR Administrator to verify CPDA claims before approval routing. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-066 | HR-EIS shall route verified CPDA claims through approval routing. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-067 | HR-EIS shall allow Accountant to process approved CPDA claims. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-068 | HR-EIS shall record CPDA disbursement details. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-069 | HR-EIS shall make CPDA disbursement records auditable. | domain/ + services/ | `claims.py / transition_request()` | CPDA subtype; purpose, amount, documents; same gates. |
| HR-AFR-005 | HR-EIS shall notify an Employee about relevant HR request and policy/deadline events. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-077 | HR-EIS shall generate notifications for request submission. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-078 | HR-EIS shall generate notifications for approval, rejection, or forwarding. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-079 | HR-EIS shall generate notifications for pending action reminders. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-080 | HR-EIS shall generate notifications for policy or deadline updates. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-081 | HR-EIS shall deliver notifications through the system dashboard. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-082 | HR-EIS shall deliver notifications through official email. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Idempotent, scoped, dashboard + authorized official-email handoff. |
| HR-AFR-083 | HR-EIS shall log every HR transaction. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-084 | HR-EIS audit logs shall include actor identity. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-085 | HR-EIS audit logs shall include timestamp. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-086 | HR-EIS audit logs shall include action performed. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-087 | HR-EIS audit logs shall be immutable. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-088 | HR-EIS shall restrict audit log access to authorized roles only. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-089 | HR-EIS shall support compliance with institutional HR and financial policies through logged HR-EIS transactions. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Append-only event in same transaction as state change. |
| HR-AFR-090 | HR-EIS shall integrate with the payroll system for disbursement-status exchange related to approved claims. | contracts/ + adapters/ | `iam_projection / finance status adapter` | External status only; no ERP writes, payroll or salaries. |
| HR-AFR-091 | HR-EIS shall integrate with the finance system for accounting-status exchange related to approved claims. | contracts/ + adapters/ | `iam_projection / finance status adapter` | External status only; no ERP writes, payroll or salaries. |
| HR-AFR-092 | HR-EIS shall integrate with other Fusion modules for identity and role consistency. | contracts/ + adapters/ | `iam_projection / finance status adapter` | External status only; no ERP writes, payroll or salaries. |
| HR-AFR-093 | HR-EIS shall synchronize integration data automatically and in real time where configured. | contracts/ + adapters/ | `iam_projection / finance status adapter` | External status only; no ERP writes, payroll or salaries. |
| HR-AFR-104 | HR-EIS shall not modify payroll rules. | contracts/ + services/ | `finance boundary / deny writes` | No HR-EIS payroll computation, execution or salary rule edits. |
| HR-AFR-105 | HR-EIS shall not modify salary structures. | contracts/ + services/ | `finance boundary / deny writes` | No HR-EIS payroll computation, execution or salary rule edits. |
| HR-UC-001 | View Own Service Record: View the employee's own official service record in read-only mode. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-002 | Maintain Employee Master and Service Records: Create or modify official employee master/service-record information within authorized HR-EIS scope. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-003 | Submit Leave Request: Submit a valid leave request for routing through the applicable approval hierarchy. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-004 | Review and Decide HR Request: Review a routed HR request and apply the permitted approval outcome without bypassing workflow order. | domain/ + services/ | `workflow.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Approving Authority. |
| HR-UC-005 | Track Submitted HR Request Status: View the current status and traceable progression of HR requests submitted by the Employee. | services/ + selectors/ | `request_service.py / request_scoping.py` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-006 | Submit Yearly Appraisal: Submit the yearly appraisal form during an allowed submission window. | domain/ + services/ | `appraisal.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-007 | Assign Appraisal Reviewers: Assign the reviewer(s) required for appraisal evaluation. | domain/ + services/ | `appraisal.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-008 | Review and Finalize Appraisal: Review an assigned appraisal and finalize it through the designated appraisal authority path. | domain/ + services/ | `appraisal.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Approving Authority. |
| HR-UC-009 | Submit LTC Advance Request: Submit an LTC advance request using the prescribed form for HR verification. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-010 | Submit LTC Reimbursement Request: Submit an LTC reimbursement request using the prescribed form for HR verification. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-011 | Verify LTC Request: Verify LTC documentation and eligibility before approval routing. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-012 | Process Approved LTC Claim for Settlement Recording: Process an approved LTC claim within HR-EIS for financial settlement recording and related status exchange. | domain/ + services/ | `claims.py / record_financial_processing()` | Main + explicitly supplied alternative and exception paths; actor: Accountant. |
| HR-UC-013 | Submit CPDA Advance Request: Submit a CPDA advance request containing the required information. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-014 | Submit CPDA Reimbursement Request: Submit a CPDA reimbursement request containing the required information. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-015 | Verify CPDA Claim: Verify a submitted CPDA claim before approval routing. | domain/ + services/ | `claims.py / transition_request()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-016 | Process Approved CPDA Claim: Process an approved CPDA claim within HR-EIS and record auditable disbursement/status information. | domain/ + services/ | `claims.py / record_financial_processing()` | Main + explicitly supplied alternative and exception paths; actor: Accountant. |
| HR-UC-017 | Configure HR-EIS Workflow Settings: Configure HR-EIS workflow settings that are explicitly within module scope and authorized by institutional policy. | models/ + services/ | `configure_policy_version()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-018 | Review Compliance and Audit Records: Monitor HR compliance and audit evidence using authorized immutable HR-EIS records. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Main + explicitly supplied alternative and exception paths; actor: HR Administrator. |
| HR-UC-019 | View HR-EIS Notifications: View HR-EIS notifications that have been generated for relevant HR events. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Main + explicitly supplied alternative and exception paths; actor: Employee. |
| HR-UC-021 | Generate Pending-Action Reminder Notifications: Generate an authorized reminder notification when a pending HR-EIS action reaches a configured reminder condition, without changing the underlying request state. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Main + explicitly supplied alternative and exception paths; actor: N.A.  -  Event-triggered. |
| HR-UC-022 | Generate Policy / Deadline Update Notifications: Generate an authorized notification for a configured or represented HR policy/deadline event without inventing policy content outside HR-EIS. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Main + explicitly supplied alternative and exception paths; actor: N.A.  -  Event-triggered. |
| BR-HR-001 | HR-EIS Module Scope and Authoritative Data: HR-EIS shall remain limited to employee-centric information, HR service workflows, employee service records, leave, appraisal, LTC, CPDA, approvals, audit trails, and integration/status information explicitly within the PS scope. | domain/ + api/ | `module registry / service surface` | Exclusions: Functions outside the PS scope remain outside HR-EIS. |
| BR-HR-002 | Fusion RBAC Enforcement: HR-EIS shall enforce Fusion RBAC for all HR-EIS functions and actor permissions. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | Exclusions: Platform authentication/account administration and Fusion-wide RBAC administration remain outside HR-EIS. |
| BR-HR-003 | Employee Own-Record Access: Under the Employee role, a user may view only the user's own HR-EIS data/service record and that service-record view is read-only; any additional access requires another explicitly authorized role. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | Exclusions: Additional access may arise only through another authorized role. |
| BR-HR-004 | Employee Service Record Composition: An employee service record shall include appointment details, department, designation, service history, leave balances, and retirement status. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Exclusions: Only fields supported by the PS are asserted here. |
| BR-HR-005 | Service Record Create/Modify Authority: Only HR Administrators may create or modify official employee service records; Employees may not alter official service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Exclusions: None. |
| BR-HR-006 | Service Record Integrity: HR-EIS shall preserve service-record consistency and shall not permit downtime or partial updates to corrupt employee service records. | models/ + services/ + selectors/ | `service_record_service.py / scoped_records()` | Exclusions: None. |
| BR-HR-007 | Leave Request Required Fields: A leave request shall specify leave type, duration, and justification before submission is accepted. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Exclusions: None. |
| BR-HR-008 | Leave Balance and Eligibility Validation: HR-EIS shall validate leave balance and leave eligibility before accepting a leave request submission. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Exclusions: Policy values may be external/configured; only represented validations are asserted. |
| BR-HR-009 | Approval Authority Selection and Routing: For HR requests that use an approval hierarchy, HR-EIS shall determine the current approval authority from employee category and request type: department-level approval is routed to HOD where applicable, non-teaching staff approval to Registrar where applicable, and faculty-level/final-authority approval to Director where applicable. | domain/ + services/ | `workflow.py / transition_request()` | Exclusions: The exact approval matrix is institutional policy/configuration outside the PS. |
| BR-HR-010 | Approved Leave Balance Update: When a leave request is approved, HR-EIS shall update the employee leave balance automatically. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Exclusions: None. |
| BR-HR-011 | Leave Transaction Audit Logging: All leave transactions shall be permanently logged. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Exclusions: None. |
| BR-HR-012 | Appraisal Submission Window: Yearly appraisal submission shall be accepted only within configured submission windows. | domain/ + services/ | `appraisal.py / transition_request()` | Exclusions: Submission-window values are configured/external policy values consumed by HR-EIS. |
| BR-HR-013 | Appraisal Reviewer Assignment: HR Administrator shall assign reviewer(s) for appraisal evaluation. | domain/ + services/ | `appraisal.py / transition_request()` | Exclusions: None. |
| BR-HR-014 | Appraisal Review Routing and Finalization: Appraisal workflows shall pass through designated authorities for review and finalization in the configured order. | domain/ + services/ | `appraisal.py / transition_request()` | Exclusions: No rejection/return outcome is asserted by the PS. |
| BR-HR-015 | Finalized Appraisal Archive and Immutability: Finalized appraisals shall be archived in the employee service record and shall not be modified after closure. | domain/ + services/ | `appraisal.py / transition_request()` | Exclusions: None. |
| BR-HR-016 | LTC Request Types and Prescribed Forms: HR-EIS shall support LTC Advance and LTC Reimbursement requests submitted using prescribed forms. | domain/ + services/ | `claims.py / transition_request()` | Exclusions: Prescribed forms are external templates/content sources unless represented in HR-EIS. |
| BR-HR-017 | LTC Documentation and Eligibility Verification: HR Administrator shall verify LTC documentation and eligibility before an LTC request enters approval routing. | domain/ + services/ | `claims.py / transition_request()` | Exclusions: Eligibility policy values are external/configured unless represented as HR-EIS validations. |
| BR-HR-018 | LTC Approval and Settlement Recording: A verified LTC request shall enter the applicable approval hierarchy; an approved LTC claim shall be available to the Accountant for HR-EIS-side financial settlement processing/recording. | domain/ + services/ | `claims.py / transition_request()` | Exclusions: Actual payroll/finance/bank disbursement remains outside HR-EIS. |
| BR-HR-019 | LTC Payroll Boundary and Audit History: HR-EIS shall record/link LTC payment status with payroll or finance systems without modifying payroll rules, and shall retain full audit history for rejected or returned LTC requests. | contracts/ + adapters/ | `iam_projection / finance status adapter` | Exclusions: The PS does not identify the actor/transition that creates a Returned LTC state; no such workflow transition is invented. |
| BR-HR-020 | CPDA Required Request Information: Each CPDA request shall include purpose, amount, and supporting documents before submission is accepted. | domain/ + services/ | `claims.py / transition_request()` | Exclusions: None. |
| BR-HR-021 | CPDA Verification and Approval Routing: HR Administrator shall verify CPDA claims before approval routing; a verified CPDA claim shall enter the applicable approval route. | domain/ + services/ | `claims.py / transition_request()` | Exclusions: None. |
| BR-HR-022 | CPDA Financial Processing and Auditability: Accountant shall process approved CPDA claims in HR-EIS, record disbursement details, and keep those records auditable. | domain/ + services/ | `claims.py / record_financial_processing()` | Exclusions: Actual external disbursement execution remains outside HR-EIS. |
| BR-HR-023 | Approval Outcomes and Workflow Order: For routed HR requests, HR-EIS shall support Approved, Rejected, and Forwarded to next authority outcomes and shall prevent manual bypass or alteration of configured workflow order. | domain/ + services/ | `workflow.py / transition_request()` | Exclusions: Appraisal finalization is governed separately by BR-HR-014. |
| BR-HR-024 | Notification Events and Channels: HR-EIS shall generate notifications for request submission, approval/rejection/forwarding, pending-action reminders, and configured/represented policy or deadline updates; notifications are exposed through the Fusion dashboard and official email delivery path. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Exclusions: Policy/deadline notifications apply only where such information is configured or represented in HR-EIS. |
| BR-HR-025 | Audit Log Content and Immutability: Every HR transaction shall be logged with actor identity, timestamp, and action performed, and audit logs shall be immutable. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Exclusions: None. |
| BR-HR-026 | Audit Log Access and Compliance Support: Audit-log access shall be restricted to authorized roles, and HR-EIS shall support compliance through configured validations, routing, logging, and access restrictions. | models/ + services/ + selectors/ | `append_audit_event() / scoped_audit()` | Exclusions: None. |
| BR-HR-027 | Payroll and Finance Integration Boundary: HR-EIS shall exchange/record payment, disbursement, or accounting status related to approved LTC/CPDA claims with payroll and finance systems where applicable; external systems retain their execution semantics. | contracts/ + adapters/ | `iam_projection / finance status adapter` | Exclusions: HR-EIS does not execute external payroll, accounting, or bank-disbursement operations. |
| BR-HR-028 | Fusion Identity and Role Consistency Boundary: HR-EIS shall exchange identity and role-consistency information with other Fusion modules where applicable, and shall synchronize integration data automatically and in real time where configured. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | Exclusions: Other Fusion modules retain their own domain semantics; this is system-level integration rather than an actor-goal UC. |
| BR-HR-029 | Role Assignment and Reassignment Authority: HR-EIS shall consume assigned roles controlled by institutional authorities and shall not expose routine HR-request actors as authorities for role assignment or reassignment. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | Exclusions: Platform/Fusion-wide role administration remains outside routine HR-EIS processing. |
| BR-HR-030 | Sensitive Data Access Restriction: Access to sensitive HR-EIS data shall be restricted to authorized roles, and unauthorized access or data modification shall be prevented. | selectors/ + services/ | `scoping.py / permission gate / IAM active role` | Exclusions: None. |
| BR-HR-031 | Payroll Rules and Salary Structure Exclusion: HR-EIS shall not modify payroll rules or salary structures and shall not execute payroll/accounting/bank-disbursement operations. | contracts/ + services/ | `finance boundary / deny writes` | Exclusions: None. |
| BR-HR-033 | Dashboard and Email Infrastructure Boundary: HR-EIS is responsible for generating/recording notification events; Fusion dashboard and official-email delivery infrastructure remain external delivery boundaries. | services/ + tasks/ | `notifications.py / outbox dispatch / reminder task` | Exclusions: None. |
| BR-HR-034 | Supported Leave Types: HR-EIS shall offer Casual, Restricted, Medical, Earned, Vacation, and Sabbatical as supported leave request types. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | Exclusions: No additional leave types or eligibility policy is inferred beyond the PS. |
| BR-HR-035 | Approved Claim Financial Correctness Verification: Before recording financial settlement processing for an approved LTC or CPDA claim, the Accountant shall verify financial correctness according to applicable configured rules. | domain/ + services/ | `claims.py / record_financial_processing()` | Exclusions: Policy/calculation details not stated in the PS are not invented. |
| BW-HR-01 | Leave Direct Approval: One finite path from a draft leave request to approved leave without a forwarding traversal. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | basis workflow; all 2 explicit transitions in Step 3.3. |
| BW-HR-02 | Leave Rejection: One finite path from draft leave request to rejection. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | basis workflow; all 2 explicit transitions in Step 3.3. |
| BW-HR-03 | Leave Forward  -  One Traversal: Represent exactly one traversal of the approval-authority forwarding loop. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | basis workflow; all 2 explicit transitions in Step 3.3. |
| CW-HR-01 | Leave Request Lifecycle: Combine valid leave submission with approval, rejection, and forwarding outcomes while keeping validation/routing guards explicit. | domain/ + services/ | `leave.py / transition_request() / ledger.py` | composite workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-04 | Appraisal Finalization  -  No Intermediate Traversal: Appraisal path with zero additional designated-authority traversal before finalization. | domain/ + services/ | `appraisal.py / transition_request()` | basis workflow; all 3 explicit transitions in Step 3.3. |
| BW-HR-05 | Appraisal Finalization  -  One Additional Authority: Appraisal path with exactly one additional designated-authority traversal before finalization. | domain/ + services/ | `appraisal.py / transition_request()` | basis workflow; all 4 explicit transitions in Step 3.3. |
| CW-HR-02 | Yearly Appraisal Lifecycle: Combine appraisal submission, reviewer assignment, designated-authority review, and final archive/closure. | domain/ + services/ | `appraisal.py / transition_request()` | composite workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-06 | LTC Advance  -  Approved and Processed: Finite path for an LTC Advance request through verification, direct approval, and Accountant processing. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-07 | LTC Reimbursement  -  Approved and Processed: Finite path for an LTC Reimbursement request through verification, direct approval, and Accountant processing. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-08 | LTC Rejection: Finite LTC path from submitted request through HR verification to rejection. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 2 explicit transitions in Step 3.3. |
| BW-HR-09 | LTC Forward  -  One Traversal: Represent exactly one forwarding traversal after LTC verification. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 2 explicit transitions in Step 3.3. |
| CW-HR-03 | LTC Request Lifecycle: Combine LTC Advance/Reimbursement submission with HR verification, approval/rejection/forwarding, and approved-claim financial processing. | domain/ + services/ | `claims.py / transition_request()` | composite workflow; all 7 explicit transitions in Step 3.3. |
| BW-HR-10 | CPDA Advance  -  Approved and Processed: Finite path for CPDA Advance through validation, HR verification, direct approval, and Accountant processing. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-11 | CPDA Reimbursement  -  Approved and Processed: Finite path for CPDA Reimbursement through validation, HR verification, direct approval, and Accountant processing. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 4 explicit transitions in Step 3.3. |
| BW-HR-12 | CPDA Rejection: Finite CPDA path from submitted claim through HR verification to rejection. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 2 explicit transitions in Step 3.3. |
| BW-HR-13 | CPDA Forward  -  One Traversal: Represent exactly one forwarding traversal after CPDA verification. | domain/ + services/ | `claims.py / transition_request()` | basis workflow; all 2 explicit transitions in Step 3.3. |
| CW-HR-04 | CPDA Request Lifecycle: Combine CPDA Advance/Reimbursement submission, HR verification, approval/rejection/forwarding, and approved-claim processing. | domain/ + services/ | `claims.py / transition_request()` | composite workflow; all 7 explicit transitions in Step 3.3. |

## 3.2  -  Domain model, integrity and ownership

**Bounded context:** one HR-EIS module: service-record maintenance and employee HR request lifecycles are tightly coupled through the person's service attributes and effective-dated HR policy. Finance execution, payroll, user provisioning, identity designations, official mail delivery, and institute-wide notification transport are external contexts. HR-EIS only stores its own transaction and status projection.

| Entity / responsibility | Proposed fields (non-exhaustive) | Invariant and database constraint |
|---|---|---|
| `EmployeeServiceRecord` | `user_id` (plain integer), official appointment data, department/designation snapshots, service chronology, retirement status, revision | `UniqueConstraint(user_id)`; HR-authorized versioned update only, never write ERP identity/designation |
| `ServiceRecordRevision` | `record_id`, `revision_number`, changed fields, actor/user/active role, timestamp | append-only; `UniqueConstraint(record_id, revision_number)`; atomic with record change |
| `HRRequest` | `id`, `owner_user_id`, `request_type` (leave/appraisal/LTC/CPDA), subtype, current state, route snapshot/version, current step, creation/submission timestamps, row version | `CheckConstraint` for request family/subtype consistency; state may change only in one locked transactional service; never merge independent request families |
| `LeaveRequestDetail` | `request_id`, exactly one supported leave type, start/end, duration, reason, eligibility policy version | `UniqueConstraint(request_id)`; six named types; validated against current effective policy; no implicit entitlement |
| `LeaveEntitlementLedger` | `owner_user_id`, leave type, signed quantity, origin event key, policy version, recorded timestamp | append-only; unique event key; approval posts exactly once, correction via reversal; balance = sum of entries; lock entitlement scope on concurrent approvals |
| `AppraisalDetail` | `request_id`, appraisal year, submission window policy version, reviewer-assignment version, review/result metadata, final archive reference | one active appraisal per employee and institutional cycle when period definition approved; archive immutable after finalization; avoid presuming calendar-year policy |
| `ClaimDetail` | `request_id`, type LTC/CPDA, advance/reimbursement, amount, purpose where required, prescribed-form/document references, eligibility/verifier results, policy version | one-to-one request; positive money amount and currency/precision from policy; HR verification before authority decision; status is not a bank transfer |
| `ClaimDocument` | `claim_id`, document purpose, secure object reference, integrity digest, uploader, submitted timestamp | sensitive attachments never publicly served; canonical storage/virus-scan contract is an open external dependency |
| `ApprovalRouteSnapshot` | `request_id`, policy version, employee category/request type, ordered authority designations and step numbers | `UniqueConstraint(request_id, step_number)`; current step cannot jump; cycle-free route and exact-current-authority check |
| `DecisionEvent` | `request_id`, decision, actor user_id, acting designation, step number, reason, timestamp, transition key | append-only; unique idempotency key, no duplicate forward/approve on retries |
| `RequestPolicyVersion` | domain/kind, version, effective_from/to, rule payload, approved_by user_id, activation timestamp | historical versions immutable; unique domain/version; nonoverlapping active intervals enforced transactionally (database range constraint if PostgreSQL representation supports it); no fallback guessed values |
| `AuditEvent` | actor, acting role, action, aggregate/id, before/after digests and permitted metadata, timestamp, correlation id | append-only, same DB transaction as domain change; restricted query selector; redact PII from broad event payload |
| `Notification` | recipient user_id, event type, request reference, safe message metadata, read/delivery status | recipient-only read scope; create only after committed event and authorized recipient resolution |
| `OutboxEvent` | unique event key, category, minimal payload, publish attempts/status/time | `UniqueConstraint(event_key)`; recorded in business transaction, idempotent dispatcher; never leak confidential data to wrong official email |
| `FinancialStatusProjection` | claim/request id, observed settlement status, source, external reference, recorded_at | records available external status only; no payroll rules, salary structures, payments or bank disbursement in this module |

All foreign keys in this table are **within the HR-EIS module only**. Every referenced person is a plain integer `user_id`, never a ForeignKey to an ERP/IAM user table. User-scoped reads begin in `selectors/scoping.py`, which returns not-found (404) when a record is outside the active role's scope. Unique keys and `select_for_update` protect idempotency and double spending; concurrent approval of two requests must not overdraw the ledger. Where the specification omits quantity units, threshold or calendar policy, the corresponding write remains an actionable configuration error, not a hard-coded default.

**Mutability classification:** policy versions, finalized appraisals, service-history revisions, routing/decision history, ledger entries and audit events are append-only. Mutable current-state projections are derived/maintained in the same transaction. Cancellation, deletion, and a "returned for correction" state are **not** introduced without a cited live spec provision.

## 3.3  -  Declarative state machines

The canonical transition dictionary will be keyed by `(request_family, source_state, event, actor_kind)`, with a separate guard/policy resolver; no conditional fallback can invent a new workflow edge. The table below transcribes **each transition of the four live composite workflows**. Basis flows `BW-HR-01..13` are finite paths through these same transition sets and are individually traced in Section 3.1. A forward increments the configured route step and resumes `PENDING_CURRENT_AUTHORITY`; no phantom extra terminal state is added. A persisted terminal state refuses further movement.

| Spec transition | From | Authorized actor | Required guard / event condition | To |
|---|---|---|---|---|
| CW-HR-01 / 1 | Draft Leave Request | Employee | Supported leave type; required fields; balance and eligibility valid | Pending Current Authority |
| CW-HR-01 / 2 | Pending Current Authority | Approving Authority | Approved | Approved  -  Leave Balance Updated |
| CW-HR-01 / 3 | Pending Current Authority | Approving Authority | Rejected | Rejected |
| CW-HR-01 / 4 | Pending Current Authority | Approving Authority | Forwarded to next authority | Pending Next Authority -> treated as Pending Current Authority for next traversal |
| CW-HR-02 / 1 | Appraisal Not Submitted | Employee | Submission window active | Submitted |
| CW-HR-02 / 2 | Submitted | HR Administrator | Reviewer(s) assigned | Reviewer Assigned / Pending Review |
| CW-HR-02 / 3 | Reviewer Assigned / Pending Review | Approving Authority | Not final designated authority | Pending Next Appraisal Authority |
| CW-HR-02 / 4 | Reviewer Assigned / Pending Review OR Pending Next Appraisal Authority | Approving Authority | Final designated authority finalizes | Finalized  -  Archived  -  Closed |
| CW-HR-03 / 1 | Draft LTC Advance | Employee | Prescribed form submitted | Submitted / Awaiting HR Verification |
| CW-HR-03 / 2 | Draft LTC Reimbursement | Employee | Prescribed form submitted | Submitted / Awaiting HR Verification |
| CW-HR-03 / 3 | Submitted / Awaiting HR Verification | HR Administrator | Documentation and eligibility verified | Pending Current Authority |
| CW-HR-03 / 4 | Pending Current Authority | Approving Authority | Approved | Approved LTC Claim |
| CW-HR-03 / 5 | Pending Current Authority | Approving Authority | Rejected | Rejected |
| CW-HR-03 / 6 | Pending Current Authority | Approving Authority | Forwarded to next authority | Pending Next Authority -> treated as Pending Current Authority for next traversal |
| CW-HR-03 / 7 | Approved LTC Claim | Accountant | Financial correctness verified; HR-EIS-side processing/status recorded | Financial Processing Recorded / Status Recorded when available |
| CW-HR-04 / 1 | Draft CPDA Advance | Employee | Purpose, amount, supporting documents present | Submitted / Awaiting HR Verification |
| CW-HR-04 / 2 | Draft CPDA Reimbursement | Employee | Purpose, amount, supporting documents present | Submitted / Awaiting HR Verification |
| CW-HR-04 / 3 | Submitted / Awaiting HR Verification | HR Administrator | Verified | Pending Current Authority |
| CW-HR-04 / 4 | Pending Current Authority | Approving Authority | Approved | Approved CPDA Claim |
| CW-HR-04 / 5 | Pending Current Authority | Approving Authority | Rejected | Rejected |
| CW-HR-04 / 6 | Pending Current Authority | Approving Authority | Forwarded to next authority | Pending Next Authority -> treated as Pending Current Authority for next traversal |
| CW-HR-04 / 7 | Approved CPDA Claim | Accountant | Financial correctness verified; processing/disbursement details recorded | Financial Processing / Disbursement Recorded |

**Atomic write algorithm:** lock request and relevant entitlement/route rows -> verify active IAM role and actual row scope -> validate declared transition and its effective-dated policy -> validate current step/actor and optimistic version -> apply state change plus leave ledger/claim financial status where applicable -> append immutable decision and audit events -> persist idempotent notification outbox event -> commit. Only after commit may a worker deliver dashboard/email events. Any failure rolls back all of these changes.

**State/role caveats:**
- Only the six specified leave types are accepted. Leave rejection does not deduct balance. A forwarding hop does not spend entitlement; only final approval does.
- Appraisal reviews are performed by the configured reviewer/approval hierarchy. The source does not authorize a fabricated rejection/return loop for finalized appraisals.
- Claims are distinct LTC versus CPDA, each with Advance and Reimbursement. HR-verification gates the approval queue; Accountant must check financial correctness before recording settlement status, and **no direct payment is initiated**.
- Each of the 13 basis workflow tests must still independently exercise its named path, even though their transition implementation is shared.
- No guessed reminder frequency or payment settlement duration becomes a clock-triggered transition.

## 3.4  -  Role mapping, exact permission and registry proposal

**Role inventory from the live UC/BR/workflow actors**:
- **Employee** (HR-UC-001/003/005/006/009/010/013/014; BR-HR-003): IAM basic `faculty` or `staff` (both exist). Only self-service data; `student` not granted.
- **HR Administrator** (HR-UC-002/007/011/015/017/018; BR-HR-005/013/017/021): exact `globals_designation` = `hradmin`. `SectionHead_HR` also exists, but is **not automatically substituted**; whether it should receive HR-admin grants requires approval.
- **Approving Authority** (HR-UC-004/008; BR-HR-009/014/023; BW-HR-01/02/03/04/05/08/09/12/13): exact designations `HOD (CSE)`, `HOD (Design)`, `HOD (ECE)`, `HOD (Liberal Arts)`, `HOD (ME)`, `HOD (NS)`, `Registrar`, `Director`. An approval permission alone does not authorize any request: only the *currently routed* authority acting in that role may decide.
- **Accountant** (HR-UC-012/016; BR-HR-018/022/035; CW-HR-03/04): **not found as an exact designation**. IAM has `Accounts Admin`, `dealing assistant`, and other account-related designations; neither is selected without partner/institute ruling. Until resolved, no financial settlement role grant is safe to ship.
- **Scheduled system actor** (HR-UC-021/022; BR-HR-024/033): internal task identity, not a designation, no IAM human role grant.

Permission codes use the exact three-segment convention `hreis.<singular_resource>.<closed_verb>`; no `edit`, `self`, `send` or invented verb. **Proposed manifest fields**, pending approval of the missing Accountant designation (a blocked slot cannot be silently granted):

```python
MODULE = {
    "code": "hreis", "label": "Human Resources", "icon": "Users",
    "base_path": "/hreis", "nav_section": "Administration",
    "sort_order": 30, "status": "active",
}

PERMISSIONS = [
    ("hreis.service_record.view", "Read scoped employee records"),
    ("hreis.service_record.create", "Create an official service record"),
    ("hreis.service_record.update", "Maintain an official service record"),
    ("hreis.request.view", "Track scoped HR requests"),
    ("hreis.leave.create", "Submit own leave"),
    ("hreis.leave.approve", "Decide a currently routed leave"),
    ("hreis.appraisal.create", "Submit own appraisal"),
    ("hreis.appraisal.assign", "Assign appraisal reviewers"),
    ("hreis.appraisal.approve", "Finalize authorized appraisal"),
    ("hreis.claim.create", "Submit own LTC or CPDA claim"),
    ("hreis.claim.review", "HR documentation and eligibility verification"),
    ("hreis.claim.approve", "Decide a currently routed claim"),
    ("hreis.finance.review", "Verify financial correctness of approved claim"),
    ("hreis.finance.update", "Record external financial processing status"),
    ("hreis.policy.view", "View effective HR workflow configuration"),
    ("hreis.policy.manage", "Version institutional HR policy"),
    ("hreis.audit.view", "Read authorized compliance audit events"),
    ("hreis.notification.view", "Read own notifications"),
    ("hreis.notification.publish", "System-generated notification"),
    ("hreis.reminder.publish", "System-generated pending reminder"),
]
SYSTEM_PERMISSIONS = ["hreis.notification.publish", "hreis.reminder.publish"]

_EMPLOYEE = [
    "hreis.service_record.view", "hreis.request.view",
    "hreis.leave.create", "hreis.appraisal.create",
    "hreis.claim.create", "hreis.notification.view",
]
_HR_ADMIN = [
    "hreis.service_record.view", "hreis.service_record.create",
    "hreis.service_record.update", "hreis.request.view",
    "hreis.appraisal.assign", "hreis.claim.review",
    "hreis.policy.view", "hreis.policy.manage",
    "hreis.audit.view", "hreis.notification.view",
]
_AUTHORITY = [
    "hreis.service_record.view", "hreis.request.view",
    "hreis.leave.approve", "hreis.appraisal.approve",
    "hreis.claim.approve", "hreis.notification.view",
]
_ACCOUNTANT_PENDING_APPROVAL = [
    "hreis.request.view", "hreis.finance.review",
    "hreis.finance.update", "hreis.notification.view",
]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE, "staff": _EMPLOYEE,
    "hradmin": _HR_ADMIN,
    "HOD (CSE)": _AUTHORITY, "HOD (Design)": _AUTHORITY,
    "HOD (ECE)": _AUTHORITY, "HOD (Liberal Arts)": _AUTHORITY,
    "HOD (ME)": _AUTHORITY, "HOD (NS)": _AUTHORITY,
    "Registrar": _AUTHORITY, "Director": _AUTHORITY,
    # No Accountant entry until the institute approves an existing designation.
}
SCOPE_PERMISSIONS = {
    "owner": [
        "hreis.service_record.view", "hreis.request.view",
        "hreis.notification.view",
    ],
    "assigned_actor": [
        "hreis.leave.approve", "hreis.appraisal.approve",
        "hreis.claim.approve", "hreis.claim.review",
        "hreis.finance.review", "hreis.finance.update",
    ],
    "hr_admin_records": [
        "hreis.service_record.create", "hreis.service_record.update",
        "hreis.audit.view",
    ],
}
NAV_ITEMS = [
    {"code": "hreis.my_record", "label": "My Service Record", "icon": "IdentificationCard",
     "to": "/hreis/my-record", "required_permission": "hreis.service_record.view", "sort_order": 10},
    {"code": "hreis.my_requests", "label": "My Requests", "icon": "ClipboardText",
     "to": "/hreis/requests", "required_permission": "hreis.request.view", "sort_order": 20},
    {"code": "hreis.leave", "label": "Leave", "icon": "CalendarBlank",
     "to": "/hreis/leave", "required_permission": "hreis.leave.create", "sort_order": 30},
    {"code": "hreis.appraisals", "label": "Appraisals", "icon": "FileText",
     "to": "/hreis/appraisals", "required_permission": "hreis.appraisal.create", "sort_order": 40},
    {"code": "hreis.claims", "label": "LTC / CPDA", "icon": "Receipt",
     "to": "/hreis/claims", "required_permission": "hreis.claim.create", "sort_order": 50},
    {"code": "hreis.approvals", "label": "Approval Queue", "icon": "Checks",
     "to": "/hreis/approvals", "required_permission": "hreis.leave.approve", "sort_order": 60},
    {"code": "hreis.hr_admin", "label": "HR Administration", "icon": "Users",
     "to": "/hreis/administration", "required_permission": "hreis.service_record.update", "sort_order": 70},
    {"code": "hreis.financial", "label": "Claim Processing", "icon": "CurrencyInr",
     "to": "/hreis/finance", "required_permission": "hreis.finance.review", "sort_order": 80},
    {"code": "hreis.audit", "label": "HR Audit", "icon": "ShieldCheck",
     "to": "/hreis/audit", "required_permission": "hreis.audit.view", "sort_order": 90},
    {"code": "hreis.notifications", "label": "Notifications", "icon": "Bell",
     "to": "/hreis/notifications", "required_permission": "hreis.notification.view", "sort_order": 100},
]
```

**Approval corrections required in registry before coding:** `NAV_ITEMS` can only express one permission per link; the Approvals page must be reachable by appraisal/claim approvers even if they have no leave approval grant, so the approved manifest must either give all applicable authority roles the `leave.approve` gate (as provisionally proposed) or add separately gated list routes. Likewise `faculty`/`staff` and specialized HR/authority designations are active **one at a time**, not additive; the user's current role determines view and row scope. Roles and permission data live in IAM only; no HR-EIS auth tables.

## 3.5  -  HTTP API, permission gates, UI routes and sidebar

Every path is under `/api/v1/hreis/`. All authenticated requests first pass **`HasModuleGrant("hreis")`** and then **`HasPermission(code)`**, based on the **one active role**, followed by scoped selector/route-step checks. Public module health probes are platform-owned. 404 hides records outside the caller's accessible scope; bad query parameters yield 400. Mutations use idempotency/version checks, and return structured, human-readable domain errors.

| Method | Relative endpoint | Required permission (second gate) | Return / change | Core source IDs |
|---|---|---|---|---|
| GET | `service-records/me/` | `service_record.view` | Own service record (read-only) | HR-UC-001, BR-HR-003/004 |
| GET | `service-records/` | `service_record.view` | HR-visible scoped list only | HR-UC-002, BR-HR-005/030 |
| POST | `service-records/` | `service_record.create` | Atomic, audited official record creation | HR-UC-002, BR-HR-005/006 |
| PATCH | `service-records/{id}/` | `service_record.update` | Audited official field revision | HR-UC-002, BR-HR-005/006 |
| GET | `requests/` | `request.view` | Own / assigned / administered requests, scoped | HR-UC-005, HR-AFR-006..009 |
| GET | `requests/{id}/` | `request.view` | Scoped details and decision timeline | HR-UC-005 |
| POST | `leave/` | `leave.create` | Six-type validated leave submission | HR-UC-003, BR-HR-007/008/034 |
| GET | `leave/balances/` | `service_record.view` | Ledger-derived own/authorized balance | HR-CFR-007, BR-HR-008/010 |
| POST | `leave/{id}/decision/` | `leave.approve` | Approve, reject or forward only at current step | HR-UC-004, CW-HR-01 |
| POST | `appraisals/` | `appraisal.create` | Submit inside configured window | HR-UC-006, BR-HR-012 |
| POST | `appraisals/{id}/reviewers/` | `appraisal.assign` | Assign authorized reviewer(s) | HR-UC-007, BR-HR-013 |
| POST | `appraisals/{id}/decision/` | `appraisal.approve` | Configured advance/finalize + archive | HR-UC-008, CW-HR-02 |
| POST | `claims/` | `claim.create` | LTC/CPDA, advance/reimbursement validated submit | HR-UC-009/010/013/014 |
| POST | `claims/{id}/verification/` | `claim.review` | HR document/eligibility verification | HR-UC-011/015, BR-HR-017/021 |
| POST | `claims/{id}/decision/` | `claim.approve` | Current authority approve/reject/forward | HR-UC-004, CW-HR-03/04 |
| POST | `claims/{id}/financial-verification/` | `finance.review` | Accountant financial correctness decision | BR-HR-035 |
| POST | `claims/{id}/processing-status/` | `finance.update` | Record verified, externally observed processing | HR-UC-012/016, BR-HR-022/027 |
| GET | `policies/` | `policy.view` | Current effective configuration + versions | HR-UC-017 |
| POST | `policies/versions/` | `policy.manage` | Create effective-dated, audited revision | HR-UC-017, BR-HR-009 |
| GET | `audit/` | `audit.view` | Restricted redacted audit search | HR-UC-018, BR-HR-025/026 |
| GET | `notifications/` | `notification.view` | Own authorized dashboard notifications | HR-UC-019/021/022 |
| POST | `notifications/{id}/read/` | `notification.view` | Mark own notification read | HR-UC-019 |

**Approval queue source:** `GET requests/` scoped to the acting approval role + current route step. A designated HR Administrator sees only its authorized queue; Accountant claim detail appears only under approved finance permissions. Do not introduce broad "all requests" read access via the shared `request.view` verb.

**Client (this repository's native React shell):**

| Route / proposed nav item | Route component responsibility | Route guard |
|---|---|---|
| `/hreis/my-record` / My Service Record | Own read-only record and balances | `RequirePermission(service_record.view)` |
| `/hreis/requests` / My Requests | Scoped request list/status, record drawer | `RequirePermission(request.view)` |
| `/hreis/leave` / Leave | New leave wizard + own leave history drawer | `RequirePermission(leave.create)` |
| `/hreis/appraisals` / Appraisals | Annual self submission + own status drawer | `RequirePermission(appraisal.create)` |
| `/hreis/claims` / LTC / CPDA | Advance/reimbursement prescribed-form submissions | `RequirePermission(claim.create)` |
| `/hreis/approvals` / Approval Queue | Current-step decision modal; role+route scope | `RequirePermission(leave.approve)` provisionally for every authority |
| `/hreis/administration` / HR Administration | Employee record editor, verification and policy versioning in panels | `RequirePermission(service_record.update)` |
| `/hreis/finance` / Claim Processing | Approved claim finance verification/status | `RequirePermission(finance.review)`  -  role pending approval |
| `/hreis/audit` / HR Audit | Restricted compliance trace search | `RequirePermission(audit.view)` |
| `/hreis/notifications` / Notifications | Own notifications only | `RequirePermission(notification.view)` |

Every nav item corresponds to precisely one route, and every route appears in `NAV_ITEMS` (Section 3.4), with row details in drawers/modals (not unregistered detail routes). Any page sections with additional capabilities (e.g. policy editor) carry their own permission gate in the client **and** the API.

**Full-platform handoff (not modified in module-only):** add to `Fusion-client/src/ui/nav/navigation.js` `INTEGRATED_MODULES` exactly:
```js
{ id: "hreis", label: "Human Resources", icon: "Users", to: "/hreis", section: "Administration" }
```
The full-platform `PluggedModule` iframe needs `?embed=1`; the module-only frontend is directly usable without that checkout.

## 3.6  -  Public contracts and external dependencies

Proposed plural, read-only functions in `modules/hreis/contracts.py` for other modules (no direct ORM import across the boundary):
- `get_employee_service_summaries(user_ids: Sequence[int])` -> minimal, scoped service-record DTOs, no private attachments.
- `get_employee_leave_balances(user_ids: Sequence[int], leave_type: str)` -> ledger-derived balances only where caller contract authorizes.
- `get_request_statuses(request_ids: Sequence[int])` -> scoped type/status/current step, not salaries or payment credentials.
- `get_approved_claim_statuses(request_ids: Sequence[int])` -> confirmed HR-EIS processing projection, never proof of external bank transfer.

**Inbound contracts**:
1. IAM Fusion auth/session via existing `fusion_auth/client.py`: authenticated `user_id`, `active_role`, effective permissions and module grant. Verified live client methods: `get_users`, `search_users`, `iter_employees`, `employee_page`. Verified module boundary: `modules/directory/contracts.py::get_users`, `get_employees`, `search`. Use the existing plural directory contract, not a fabricated `FakeIam` endpoint. No direct `fusionlab` access. `globals_designation` is used read-only during planning, not queried by HR-EIS business logic.
2. Staff directory/HR master identity projection: confirmed `UserDTO` supplies `user_id`, `kind`, `department`, `email`, name and active-employee filtering; it does **not** expose a designation/office assignment or retirement status. Route-policy input and role identity must therefore come from the session's acting designation and an approved HR service-record source (or a separately approved IAM projection extension). Never infer missing designation/retirement fields from employee names or directly query ERP.
3. Dashboard + official-email infrastructure: HR-EIS can produce scoped outbox messages; the transport must be an agreed existing platform adapter. If no contract exists, mailbox delivery and cross-shell notification integration are an explicit external blocker (BR-HR-024/033; UC-021/022), not a fake "sent" flag.
4. Finance/payroll: accept verified status/acknowledgement from an agreed external integration where available. Never calculate payroll, change salary structures, initiate money movement or claim that a locally recorded status is external settlement (BR-HR-027/031/035). Names, authentication, retry contract, reconciliation path and whether endpoint already exists require approval.
5. Secure document storage for claim forms: use existing approved attachment service/storage only after verified; otherwise treat claim-document workflow as blocked pending a secure service choice. No ad-hoc publicly accessible media files.

**Isolation and authentication:** no cross-module FK, no SQL writes to IAM/ERP, no HTTP calls inside DB transactions. Outbox + Celery provide idempotent delivery. Missing external dependencies must fail visibly to the authorized actor and preserve pending state. In no case reveal another employee's record existence to an unauthorized caller.

## 3.7  -  Scheduled / event-triggered work

| Intended task | Cadence / event | Mechanism | Failure if absent |
|---|---|---|---|
| Pending-action reminder (HR-UC-021) | **Cadence undefined in supplied spec; wait for configured versioned reminder policy** | Beat scans due pending actions; unique `(request, step, reminder_policy, due_at)` outbox key | Authorized authority not reminded; never silently auto-advance workflow |
| Policy/deadline notification (HR-UC-022) | On configured policy/deadline trigger; exact schedule **not specified** | Beat/transactional outbox from effective event | Recipients miss policy/deadline change; no mutation of request state |
| Dashboard/official-email dispatch (BR-HR-024/033) | On commit, async retry/backoff per approved infrastructure | Celery worker drains outbox, idempotency key and scoped recipient resolution | Queued delivery accumulates; requests remain committed |
| Finance status reconciliation (BR-HR-027) | **Only if** approved external status adapter specifies polling or webhook | Webhook/beat adapter, idempotent status versioning | Locally visible financial status becomes stale, never presume paid |
| Annual leave entitlement/revision (BR-HR-008/010) | **Only if** actual entitlement policy explicitly prescribes credit/reset schedule | Append-only ledger credit task tied to policy version | Crediting stopped; do not invent yearly grant/reset |

For every enabled beat task record timezone, configured schedule, replay behavior, monitoring and a failure alert before deployment. Scheduler and worker are required in production where policies demand them; unconfigured schedules must not execute guessed defaults.

## 3.8  -  Questions and approval decisions (all unresolved items block relevant coding)

1. **Accountant designation blocker (mandatory):** The spec's `Accountant` actor has **no exact** `globals_designation`. Which existing designation must receive financial verification/status rights - `Accounts Admin`, another precisely named designation, or an institute-created designation? Finance routes and grants cannot be released until answered.
2. **HR admin/authority scope:** Is exact `hradmin` the sole HR Administrator, or also `SectionHead_HR`? Confirm the approval matrix per employee kind, department, request type, HOD/Registrar/Director order and ability to forward; how are vacancies/delegations handled? Exact six HOD role names were verified but routability and department equivalence are not inferred.
3. **Self-service entitlement:** Can every basic `faculty`/`staff` employee file every named leave type and LTC/CPDA claim, or does policy restrict categories/grades? Clarify required service record, leave fields and sensitive department scoping.
4. **Leave policies:** Provide initial, versioned rules for eligibility, balances, accrued credit, leave unit and partial-day behavior, overlapping requests, holiday/weekend counting, approval-time check, reservations and correction/reversal behavior. No numeric quota or reset date was in the current written spec.
5. **Appraisal policies:** Which periods/windows, required fields, reviewer assignment constraints, authority chain, storage/archive format, missing-reviewer behavior and retention/access rules govern yearly appraisals? Does any external system already own the appraisal cycle?
6. **LTC/CPDA policies:** Approved advance/reimbursement form templates, obligatory documents, financial amount/eligibility limits, currency precision, HR checks and Accountant correctness criteria; what happens to a claim that fails HR verification? Do not infer a new Returned state or approval bypass.
7. **Notification channel:** Where is the institute's official-email address/projection and delivery API? How is Fusion dashboard notification integration authorized? Reminder timing, recipient choice, content limits, retries and audit must be agreed.
8. **Payments:** Which external payroll/finance endpoint or reconciliation feed actually exists? "Financial processing recorded" is only a module-side trace. External payment success cannot be claimed without its source and status contract. HR-EIS must not change payroll rules or salary structures.
9. **Secure attachments/audit:** Which existing document store is approved for LTC/CPDA proofs? What audit retention, sensitive-field redaction, role-restricted reporting and subject-access rules apply?
10. **Routing identity availability:** Verified the directory contract provides employee `kind` and `department` but not explicit current designation, reporting chain or retirement status. Confirm how the active role, institutional HOD mapping and HR maintained record combine for routing. Approve an IAM API/projection extension only if the missing authoritative data cannot be obtained through already approved contracts. Module-only public `fusion-dev.dump` has sparse academic projection and cannot be treated as policy truth.
11. **Approval queue nav:** Confirm that all designated approvers may have a common `hreis.leave.approve` capability to display the shared approval queue while per-request operation still checks exact claim/appraisal permissions, or request separately gated views. The URL/manifest mapping must satisfy `nav_matches_routes.py`.
12. **Policy/version ownership:** Who is authorized to create/effectuate `RequestPolicyVersion` changes and who signs off? The current proposal limits it to the `hradmin` role; institute approval is required.
13. **External shared-file edits:** Only the six Section 4.0 module registration files, native module pages, module docs/tests, E2E role accounts and generated artifacts are pre-approved by the template. Any IAM extension, new library, shared abstraction, new schema/system dependency or legacy Fusion-client edit requires a **separate dated written Student-2 approval**.
14. **LTC returned audit without transition:** BR-HR-019, HR-CFR-009 and HR-AFR-059 require retaining the history of a returned LTC request, but the live LTC workflow does not define who returns it or an inbound Returned edge. Confirm whether this is an external return event to record, or a missing workflow transition. No state edge will be invented.
15. **Acceptance of known gaps:** Even if external infrastructure is unavailable, which specification workflows may be left blocked without pretending completion? Any accepted gap must be individually recorded in the final quality report.

### Approval register and development handoff

- Blueprint author: Student 1 **24BCS230**. Approver required: Student 2 **24BCS163**, pair 2.
- **Current status: awaiting independent written approval.** No implied consent, no date/quote/link manufactured.
- Before Step 4.0, the other student must review Section Section 3.1-3.8 and return (a) an explicit dated blueprint approval, and (b) answers/accepted gaps to the above blockers. Record that exact response in the quality report when it exists. A new user message from Student 1 cannot substitute for it.
- Until then **no backend/frontend application code, migrations, or policy defaults**; no test claim of success beyond observed environment checks; no commit/push/PR without separate user instruction.
- After approval: register hreis; build pure domain -> DB constraints/migrations -> scoped selectors -> transactional services -> DRF API and IAM manifest -> React routes/nav; run per-layer and end-to-end validation; get a fresh independent review to 10/10 in every dimension and fix only confirmed defects; preserve Student-2 frozen test designs and never rewrite tests to hide a failure. Capture actual coverage and JUnit/pytest logs.
