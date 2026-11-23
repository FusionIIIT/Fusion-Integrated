
## Prompt 001 Backend foundation

UTC: 2026-10-12T13:22:45.976667+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 8192}`

Implement the Employee Leave Management module inside the supplied Fusion ERP base. This is the first implementation stage, not a code review. Use the provided specification context to generate backend data models, the pure-Python domain definitions/calculations, app configuration, module permissions/navigation/role grants and batched public contracts. Reuse Fusion identity; employee references must be integer IAM user IDs, not Django user foreign keys. Models must contain all data needed by the provided leave workflows, policy/calendar/hierarchy configuration, balances, audit, notifications, SLA and year-end processing. Code package is modules.leave_elm, module code is leave_elm, frontend base is /leave and backend prefix is /api/v1/leave/. Plan three nav paths /leave/mine, /leave/queue, /leave/admin. registry.py is plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label), ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list. Use names from the supplied actor registry. Include faculty and staff grants for employee actions. Do not create login/user models or tests. Return only the foundational files requested; later stages will implement services/API/UI against your definitions. Use only installed Django/standard-library dependencies. Domain must not import Django/DRF/Celery. contracts.py getters must accept sequences. AppConfig name modules.leave_elm, label leave_elm, default_auto_field django.db.models.BigAutoField. All fields should be syntactically valid Django fields. Keep the output compact enough to return all files.

Required output paths:
modules/leave_elm/__init__.py
modules/leave_elm/apps.py
modules/leave_elm/models.py
modules/leave_elm/domain/__init__.py
modules/leave_elm/domain/policy.py
modules/leave_elm/registry.py
modules/leave_elm/contracts.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.

# ELM supplied specification context

This is extracted from the supplied specification artifacts. Historical and retired IDs are not active requirements. Workflow v1.6 STTs take precedence over older v1.5 workflow registries.


## Problem statement v1.4
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

## Consolidated requirements v1.5
CFR-EL-001 Role-based ELM access: The system shall restrict ELM capabilities to users authorized for the corresponding employee, processing, sanctioning, or administrative roles.
CFR-EL-002 Create and submit leave application: The system shall allow an eligible employee to create and submit one leave application for CL, RH, SCL, EL, COL, or VL, capturing the leave category, requested period, purpose/reason, and other required information; when Station Leave applies, its details shall be captured within the same application rather than through a separate leave-request process.
CFR-EL-003 Validate a leave request before progression: Before a new leave request is allowed to proceed, the system shall validate the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date shall not be treated as overlapping when they occupy different halves.
CFR-EL-004 Casual Leave (CL) entitlement and treatment: The system shall maintain an annual CL entitlement of 8 days for each employee, support first-half and second-half CL with an approved half day consuming 0.5 CL day, and lapse unused CL at year end without carry-forward.
CFR-EL-005 Restricted Holiday (RH) entitlement and treatment: The system shall maintain an annual RH entitlement of 2 days for each employee, permit an RH request only for an applicable Restricted Holiday in the currently effective published holiday/RH calendar, and lapse unused RH at year end without carry-forward.
CFR-EL-006 Special Casual Leave (SCL) entitlement and treatment: The system shall support up to 15 SCL days per calendar year for each employee for a special purpose considered admissible by the applicable sanctioning authority, and shall lapse unused SCL at year end without carry-forward.
CFR-EL-007 Earned Leave (EL) entitlement and carry-forward: The system shall credit each non-faculty employee with 30 EL days per year and carry forward unused EL according to policy.
CFR-EL-008 Faculty Vacation Leave (VL) and VL-to-EL conversion: The system shall maintain 60 VL for each faculty member for vacation periods supplied through the institute Academic Calendar, permit VL only during an applicable vacation period, and at year end convert all unused VL to EL at 2 VL : 1 EL including fractional conversion; VL itself shall not carry forward, while the converted EL shall be credited to the faculty member’s EL balance, may carry forward, and may subsequently be used.
CFR-EL-009 Commuted Leave (COL) entitlement and treatment: The system shall maintain an annual COL entitlement of 20 days for each eligible employee in this baseline, treat COL as medical/balance-controlled leave, require supporting medical evidence where applicable, and carry forward unused COL according to policy.
CFR-EL-010 Continuous-day counting: For EL, COL, and VL, the system shall count intervening weekends and closed holidays within a continuous approved leave interval as leave days; this continuous-day rule shall not apply to CL, SCL, or RH.
CFR-EL-011 Nominate an eligible substitute: When responsibility coverage is required, the system shall allow the applicant to nominate one substitute who is another employee, is not the applicant, and has no overlapping pending or approved leave during the responsibility period.
CFR-EL-012 Obtain substitute response and enforce consent gate: The system shall allow the nominated substitute to accept or decline the responsibility assignment; approval routing shall not proceed until required substitute consent is accepted, and after a decline the applicant shall be allowed to nominate another eligible substitute or withdraw the pending request.
CFR-EL-013 CL/RH Unit Head final decision: For CL and RH, including associated Station Leave, the system shall route the submitted request to the applicant’s Unit Head and allow the Unit Head to make the final approve/reject decision, except where the Director-specific self-sanction rule applies.
CFR-EL-014 Higher-sanction leave progression to final decision: For SCL, EL, COL, and VL, the system shall route the request to the Unit Head for review and recording of Recommended or Not Recommended, shall not treat Not Recommended as a final rejection, and shall then route the request through the configured hierarchy to the resolved final Sanctioning Authority for an approve/reject decision. The route shall be resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration, and may include an Establishment processing step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director where configured.
CFR-EL-015 Director self-sanction: When the Director is the applicant, the system shall apply the Director-specific self-sanction path instead of the normal Unit Head/higher-authority routing path.
CFR-EL-016 Record and communicate the final leave decision: On a final leave decision, the system shall record the decision and notify the employee. When the decision is approval, the system shall also update the employee’s leave record/account. Intermediate processing decisions and state changes need not generate general notifications but shall be available to the employee through status/history inquiry.
CFR-EL-017 No post-submission modification of a pending request: The system shall not permit a submitted pending leave request to be modified in place. A pending request that requires change may instead be withdrawn before final approval, after which a new leave application may be submitted if needed.
CFR-EL-018 Immediate withdrawal of a pending request: The system shall allow an employee to withdraw a pending leave application at any time before final approval and, upon successful withdrawal, shall make the withdrawal effective immediately, terminate all remaining approval processing for that application, prevent any later approve/reject action, and notify the concerned roles of the withdrawal. After final approval, withdrawal shall no longer be available and the approved-leave cancellation process shall apply where relevant.
CFR-EL-019 Cancel approved leave before start: The system shall allow an employee to request cancellation of an approved leave before its start date, process the cancellation through the same applicable approval hierarchy to a final decision, and shall not edit the approved leave in place. If cancellation is approved, the system shall mark the leave Cancelled and restore or adjust any leave balance already deducted for that approval; if cancellation is rejected, the original approved leave shall remain unchanged. If revised leave is still needed after cancellation, a fresh application shall be submitted. Once the leave has begun, the pre-start cancellation path shall no longer apply.
CFR-EL-020 Extend ongoing EL/COL/VL: The system shall allow an employee on ongoing EL, COL, or VL to request additional leave time, validate the extension against applicable eligibility, balance, substitute, calendar, and approval conditions, obtain required substitute consent before routing, and process the extension through the applicable Unit Head and configured higher-sanction path. If approved, only the incremental additional leave period shall be posted while preserving the original approved leave as the base; if rejected, the original approved leave shall remain unchanged.
CFR-EL-021 Review resumption and adjust actual leave where required: The system shall allow an employee returning from EL, COL, or VL to submit the actual resumption date and required details for review by the applicable Sanctioning Authority. When the employee resumes on the approved end date, the authority shall review the resumption without changing the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, the system shall, after the resumption review, record the actual leave period, adjust the leave balance accordingly, and synchronize the relevant leave/attendance records.
CFR-EL-022 View leave balances and history: The system shall allow an employee to view current leave balances and leave-account/request history, including the current status and recorded final decisions of the employee’s leave requests.
CFR-EL-023 Obtain printable/exportable leave application: The system shall allow an employee to obtain a printable/exportable representation of a leave application accessible to that employee.
CFR-EL-024 Maintain policy parameters and hierarchy configuration: The system shall allow authorized administrative roles to create and revise leave-policy parameters and maintain the hierarchy configuration used for validation and routing; ELM shall use the current configured policy and hierarchy values. No draft/publish/effective-version lifecycle is required for leave-policy parameters in this baseline.
CFR-EL-025 Maintain and publish the holiday/RH calendar: The system shall allow authorized administrative roles to create, revise, and publish the holiday/RH calendar, and date/RH validation shall use the currently effective published holiday/RH calendar until a replacement is published.
CFR-EL-026 Maintain authorized leave records: The system shall allow authorized administrative roles to maintain or correct leave records where their role permits such record maintenance, while preserving the distinction between administrative record maintenance and leave sanctioning.
CFR-EL-027 Record already-sanctioned offline leave: The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized paper/offline process when ELM could not be used, shall capture the sanction/reference evidence, validate the entry for record consistency, and update the relevant leave balance/history. This operation is record synchronization and shall not initiate a second approval workflow.
CFR-EL-028 Execute and record year-end leave-account processing: At year end, the system shall execute the applicable leave-account outcomes defined by policy: lapse unused CL, RH, and SCL; perform the faculty VL-to-EL conversion; carry forward EL and COL; record the resulting leave-account transactions; and report processing exceptions.
CFR-EL-029 Configure workflow-task SLA thresholds: The system shall support configurable reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
CFR-EL-030 Notify a user when an actionable task is assigned: When an actionable workflow task is assigned to a user, the system shall notify the assigned user of that task.
CFR-EL-031 Remind on a still-pending SLA task: When an SLA-controlled actionable task reaches its configured reminder threshold and is still pending, the system shall remind the responsible user and log the reminder action; if the task is no longer pending at the threshold, the corresponding reminder shall not be issued.
CFR-EL-032 Escalate a still-pending SLA task: When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action to the configured higher/responsible authority and log the action; if the task is no longer pending at the threshold, the corresponding escalation shall not be issued.

## Atomic requirements v1.5
AFR-EL-001.1: The system shall permit a user to perform only those ELM capabilities authorized for the user’s employee, processing, sanctioning, or administrative role(s).
AFR-EL-002.1: The system shall allow an eligible employee to create and submit a leave request.
AFR-EL-002.2: The system shall support CL, RH, SCL, EL, COL, and VL as leave categories within the ELM baseline.
AFR-EL-002.3: The system shall capture leave category, requested period, purpose/reason, and other required information in a leave application.
AFR-EL-002.4: When Station Leave applies, the system shall capture its required details within the associated leave application.
AFR-EL-002.5: The system shall treat Station Leave information as coupled to the associated leave application and shall not create a separate leave-request process for it.
AFR-EL-003.1: Before a new leave request proceeds, the system shall validate requested leave-category eligibility using the current configured leave-policy parameters.
AFR-EL-003.2: Before a new leave request proceeds, the system shall validate the employee’s available leave entitlement/balance for the requested leave.
AFR-EL-003.3: The system shall calculate chargeable leave days using the applicable leave-counting rule and calendar data.
AFR-EL-003.4: The system shall detect and prevent impermissible overlap between a new leave request and the employee’s active pending or approved leave.
AFR-EL-003.5: The system shall treat first-half and second-half CL on the same date as non-overlapping when they occupy different halves.
AFR-EL-003.6: The system shall use the currently effective published holiday/RH calendar for date and RH validation until a replacement is published.
AFR-EL-004.1: The system shall maintain an annual CL entitlement of 8 days for each employee.
AFR-EL-004.2: At year end, the system shall lapse unused CL and shall not carry it forward.
AFR-EL-004.3: The system shall support CL for the first half or the second half of a day.
AFR-EL-004.4: On approval of a half-day CL, the system shall consume 0.5 CL day.
AFR-EL-005.1: The system shall maintain an annual RH entitlement of 2 days for each employee.
AFR-EL-005.2: The system shall permit an RH request only when the requested date corresponds to an applicable Restricted Holiday in the currently effective published holiday/RH calendar.
AFR-EL-005.3: At year end, the system shall lapse unused RH and shall not carry it forward.
AFR-EL-006.1: The system shall support up to 15 SCL days per calendar year for each employee.
AFR-EL-006.2: The system shall use the applicable Sanctioning Authority’s decision to determine whether the stated special purpose is admissible for SCL; no separate encoded admissibility criterion is required.
AFR-EL-006.3: At year end, the system shall lapse unused SCL and shall not carry it forward.
AFR-EL-007.1: The system shall credit each non-faculty employee with 30 EL days per year.
AFR-EL-007.2: The system shall carry forward unused EL according to policy.
AFR-EL-008.1: The system shall maintain 60 VL for each faculty member.
AFR-EL-008.2: The system shall obtain the applicable faculty vacation periods from the institute Academic Calendar maintained outside ELM.
AFR-EL-008.3: The system shall allow VL to be availed only during an applicable vacation period supplied through the institute Academic Calendar.
AFR-EL-008.4: At year end, the system shall convert all unused faculty VL to EL at a ratio of 2 VL to 1 EL.
AFR-EL-008.5: The system shall preserve fractional results when performing the year-end VL-to-EL conversion.
AFR-EL-008.6: After year-end VL-to-EL conversion, the system shall not carry forward any unused VL as VL.
AFR-EL-008.7: The system shall credit EL generated by VL conversion to the faculty member’s EL balance; that converted EL may carry forward and may subsequently be availed.
AFR-EL-009.1: The system shall maintain an annual COL entitlement of 20 days for each eligible employee in this baseline.
AFR-EL-009.2: The system shall carry forward unused COL according to policy.
AFR-EL-009.3: The system shall validate COL against the employee’s applicable available COL balance before progression.
AFR-EL-009.4: The system shall support required medical evidence for COL where the applicable case requires such evidence.
AFR-EL-010.1: For EL, COL, and VL, the system shall count intervening weekends and closed holidays inside a continuous approved leave interval as leave days.
AFR-EL-010.2: The system shall not apply the EL/COL/VL continuous-day counting rule to CL, SCL, or RH.
AFR-EL-011.1: When responsibility coverage is required, the system shall allow the applicant to nominate one substitute.
AFR-EL-011.2: The system shall reject a substitute nomination if the nominee is not another employee.
AFR-EL-011.3: The system shall reject a substitute nomination when the nominee is the applicant.
AFR-EL-011.4: The system shall reject a substitute nomination when the nominee has overlapping pending or approved leave during the responsibility period.
AFR-EL-012.1: The system shall allow the nominated substitute to accept or decline the responsibility assignment.
AFR-EL-012.2: When substitute consent is required, the system shall prevent approval routing until the nominated substitute accepts.
AFR-EL-012.3: After a required substitute declines, the system shall allow the applicant to nominate another eligible substitute.
AFR-EL-012.4: After a required substitute declines, the system shall allow the applicant to withdraw the still-pending request where withdrawal is applicable.
AFR-EL-013.1: For a submitted CL or RH request, the system shall route the request to the applicant’s Unit Head except where the Director-specific self-sanction rule applies.
AFR-EL-013.2: For CL and RH, including associated Station Leave, the system shall treat the applicant’s Unit Head as the final sanctioning authority except for the Director-specific self-sanction case.
AFR-EL-013.3: The system shall allow the Unit Head to approve or reject CL and RH within Unit Head authority.
AFR-EL-014.1: For SCL, EL, COL, and VL, the system shall route the submitted request to the applicant’s Unit Head for review, except where Director self-sanction applies.
AFR-EL-014.2: For SCL, EL, COL, and VL, the system shall allow the Unit Head to record Recommended or Not Recommended.
AFR-EL-014.3: The system shall not treat the Unit Head’s Not Recommended outcome for SCL, EL, COL, or VL as a final rejection.
AFR-EL-014.4: After Unit Head review, the system shall route SCL, EL, COL, and VL through the configured hierarchy to the resolved final Sanctioning Authority.
AFR-EL-014.5: The system shall resolve the processing/sanctioning path from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration.
AFR-EL-014.6: The system shall support configured higher-sanction paths that may include Deputy Registrar (Estt.), Dean, Registrar, and Director.
AFR-EL-014.7: Where configured, the system shall support an Establishment-level verification/routing step before forwarding higher-sanction leave to the resolved competent authority.
AFR-EL-014.8: The system shall allow the resolved final Sanctioning Authority to approve or reject a routed higher-sanction request.
AFR-EL-015.1: When the Director is the applicant, the system shall replace the normal Unit Head/higher-authority route with the Director-specific self-sanction path.
AFR-EL-016.1: On a final leave decision, the system shall record the final approve/reject outcome.
AFR-EL-016.2: On a final leave decision, the system shall notify the employee of the final outcome.
AFR-EL-016.3: When a new leave request is finally approved, the system shall update the employee’s leave record/account according to the applicable leave-category rules.
AFR-EL-016.4: The system shall make intermediate processing states and recorded decisions available to the employee through status/history inquiry without requiring a general notification for every intermediate state change.
AFR-EL-017.1: The system shall not permit a submitted pending leave request to be modified in place.
AFR-EL-017.2: If a submitted pending request requires change before final approval, the system shall support change by withdrawal of the pending request followed, if needed, by submission of a new leave application.
AFR-EL-018.1: The system shall allow an employee to withdraw a pending leave application at any time before final approval and shall make the withdrawal effective immediately.
AFR-EL-018.2: Upon successful withdrawal, the system shall terminate all remaining approval processing and close/cancel remaining actionable tasks for that application.
AFR-EL-018.3: After a request is withdrawn, the system shall prevent any later approve or reject action on that request.
AFR-EL-018.4: Upon successful withdrawal, the system shall notify the concerned processing/sanctioning roles of the withdrawal.
AFR-EL-018.5: After final approval, the system shall not offer pending-request withdrawal; approved-leave cancellation shall apply where its preconditions are satisfied.
AFR-EL-019.1: The system shall allow an employee to request cancellation of an approved leave only before the approved leave begins.
AFR-EL-019.2: The system shall route an approved-leave cancellation through the same applicable hierarchy as the original leave.
AFR-EL-019.3: The system shall not edit the approved leave in place as part of cancellation processing.
AFR-EL-019.4: When cancellation is finally approved, the system shall mark the approved leave as Cancelled.
AFR-EL-019.5: When cancellation is finally approved, the system shall restore or adjust any leave balance already deducted for the original approval.
AFR-EL-019.6: When a cancellation request is finally rejected, the system shall leave the original approved leave unchanged.
AFR-EL-019.7: If revised leave is still needed after successful cancellation, the system shall require a fresh leave application.
AFR-EL-019.8: Once the approved leave has begun, the system shall direct applicable change handling to extension or resumption rather than the pre-start cancellation path.
AFR-EL-020.1: The system shall allow an employee on ongoing EL, COL, or VL to submit a separate extension request for additional leave time.
AFR-EL-020.2: The system shall limit the defined extension capability to ongoing EL, COL, and VL.
AFR-EL-020.3: Before an extension proceeds, the system shall validate applicable eligibility, balance, leave-counting, calendar, and other extension conditions.
AFR-EL-020.4: When responsibility coverage is required for an extension, the system shall obtain valid substitute consent before approval routing proceeds.
AFR-EL-020.5: The system shall route a valid extension through the applicable Unit Head and configured higher-sanction path.
AFR-EL-020.6: When an extension is finally approved, the system shall post only the incremental additional leave period while preserving the original approved leave as the base.
AFR-EL-020.7: When an extension request is finally rejected, the system shall leave the original approved leave unchanged.
AFR-EL-021.1: The system shall allow an employee returning from EL, COL, or VL to submit resumption of duty information.
AFR-EL-021.2: The system shall support a resumption date earlier than the approved end date for EL, COL, or VL.
AFR-EL-021.3: The system shall capture the employee’s actual resumption date and required resumption details.
AFR-EL-021.4: The system shall route submitted resumption information to the applicable Sanctioning Authority for review.
AFR-EL-021.5: When the actual resumption date equals the approved end date, the Sanctioning Authority shall review the resumption and the system shall make no change to the approved leave period or leave balance.
AFR-EL-021.6: When actual resumption is earlier or later than the approved end date, the system shall, after Sanctioning Authority review, record the actual leave period.
AFR-EL-021.7: When resumption is earlier than the approved end date, the system shall restore the unused portion of approved EL/COL/VL only after the required resumption review.
AFR-EL-021.8: When resumption is later than the approved end date, the system shall adjust the leave balance to reflect the reviewed actual leave period.
AFR-EL-021.9: After reviewed early or late resumption, the system shall synchronize the relevant leave and attendance records with the actual leave period.
AFR-EL-021.10: The system shall not create a generic leave-closure state solely because a normal resumption has been reviewed.
AFR-EL-022.1: The system shall allow an employee to view the employee’s current leave balances.
AFR-EL-022.2: The system shall allow an employee to view the employee’s leave-account and leave-request history.
AFR-EL-022.3: The system shall allow an employee to view the current processing status of the employee’s leave requests.
AFR-EL-022.4: The system shall allow an employee to view recorded final decisions for the employee’s leave requests.
AFR-EL-023.1: The system shall allow an employee to obtain a printable/exportable representation of a leave application accessible to that employee.
AFR-EL-024.1: The system shall allow authorized administrative roles to create and revise the current leave-policy parameters.
AFR-EL-024.2: The system shall allow authorized administrative roles to maintain the current hierarchy configuration used for routing.
AFR-EL-024.3: The system shall use the current configured policy and hierarchy values for leave validation and routing.
AFR-EL-024.4: The system shall not require a draft/publish/effective-version lifecycle for leave-policy parameters in this baseline.
AFR-EL-025.1: The system shall allow authorized administrative roles to create and revise the holiday/RH calendar.
AFR-EL-025.2: The system shall allow authorized administrative roles to publish a replacement holiday/RH calendar.
AFR-EL-025.3: The system shall continue using the currently effective published holiday/RH calendar for date/RH validation until a replacement is published.
AFR-EL-026.1: The system shall allow an authorized administrative role to maintain or correct leave records within the scope permitted to that role.
AFR-EL-026.2: The system shall ensure that administrative leave-record maintenance or correction does not itself create or replace a leave sanctioning decision.
AFR-EL-027.1: The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized offline/paper process when ELM could not be used.
AFR-EL-027.2: The system shall treat retrospective offline-sanctioned leave entry as record synchronization and shall not initiate a second approval workflow.
AFR-EL-027.3: For each retrospective offline-sanctioned leave entry, the system shall capture sanction/reference evidence.
AFR-EL-027.4: Before completing retrospective synchronization, the system shall validate the offline-sanctioned leave entry for record consistency.
AFR-EL-027.5: After a valid retrospective offline-sanctioned leave entry is recorded, the system shall update the relevant leave balance and history.
AFR-EL-028.1: At year end, the system shall execute lapse of unused CL, RH, and SCL according to their applicable policies.
AFR-EL-028.2: At year end, the system shall execute the defined faculty VL-to-EL conversion, including fractional conversion and no VL carry-forward.
AFR-EL-028.3: At year end, the system shall carry forward EL and COL according to their applicable policies.
AFR-EL-028.4: The system shall record the leave-account transactions produced by year-end processing.
AFR-EL-028.5: The system shall report exceptions encountered during year-end leave-account processing.
AFR-EL-029.1: The system shall allow an authorized administrative role to configure the reminder threshold for SLA-controlled actionable workflow tasks.
AFR-EL-029.2: The system shall allow an authorized administrative role to configure the escalation threshold for SLA-controlled actionable workflow tasks.
AFR-EL-030.1: When an actionable workflow task is assigned to a user, the system shall notify the assigned user of that task.
AFR-EL-031.1: When an SLA-controlled actionable task reaches its configured reminder threshold, the system shall determine whether the task is still pending.
AFR-EL-031.2: If an SLA-controlled actionable task is still pending at its configured reminder threshold, the system shall remind the responsible user.
AFR-EL-031.3: When an SLA reminder is issued, the system shall log the reminder action.
AFR-EL-031.4: If the task is no longer pending when the configured reminder threshold is reached, the system shall not issue the reminder.
AFR-EL-032.1: When an SLA-controlled actionable task passes its configured escalation threshold, the system shall determine whether the task remains pending.
AFR-EL-032.2: If an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall notify or escalate to the configured higher/responsible authority.
AFR-EL-032.3: When an SLA escalation/authority notification is issued, the system shall log the escalation action.
AFR-EL-032.4: If the task is no longer pending when the configured escalation threshold is evaluated, the system shall not issue the corresponding escalation.

## 04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx
BR-EL-001 — Supported leave-category eligibility
A new leave request shall use only CL, RH, SCL, EL, COL, or VL and shall satisfy the category-applicability conditions in the current configured ELM policy.
BR-EL-002 — Casual Leave entitlement and lapse
Each employee has 8 CL days per year; unused CL lapses at year end and does not carry forward.
BR-EL-003 — Restricted Holiday entitlement and applicability
Each employee has 2 RH days per year; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH lapses at year end.
BR-EL-004 — Special Casual Leave entitlement and admissibility
Each employee may use up to 15 SCL days per calendar year for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility criterion is required; unused SCL lapses at year end.
BR-EL-005 — Non-faculty Earned Leave credit and carry-forward
Each non-faculty employee shall receive 30 EL days per year and unused EL shall carry forward according to policy.
BR-EL-006 — Faculty Vacation Leave entitlement and vacation-period applicability
Each faculty member shall have 60 VL associated with vacation periods supplied by the institute Academic Calendar, and VL may be availed only during an applicable vacation period.
BR-EL-007 — VL-to-EL year-end conversion
At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward.
BR-EL-008 — Treatment of EL created by VL conversion
EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed.
BR-EL-009 — Commuted Leave entitlement and treatment
Eligible employees have 20 COL days/year in this baseline; COL is medical/balance-controlled, supporting medical evidence may be required where applicable, and unused COL carries forward.
BR-EL-010 — Half-day CL treatment
CL shall support first-half and second-half requests; an approved half day consumes 0.5 CL day.
BR-EL-011 — Continuous-day counting
For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days; this rule does not apply to CL, SCL, or RH.
BR-EL-012 — Applicant non-overlap with half-day CL exception
A new request shall not impermissibly overlap the employee's active pending or approved leave; first-half and second-half CL on the same date are non-overlapping when they occupy different halves.
BR-EL-013 — Station Leave coupling
Station Leave permission/details, when applicable, shall be captured within the same leave application and shall not create a separate leave-request process.
BR-EL-014 — Substitute eligibility
When responsibility coverage is required, exactly one substitute is nominated; the substitute must be another employee, must not be the applicant, and must have no overlapping pending or approved leave during the responsibility period.
BR-EL-015 — Substitute consent gate and decline recovery
Required approval routing shall not proceed until the nominated substitute accepts. A decline leaves the consent gate closed; the applicant may nominate another eligible substitute or withdraw the pending request where applicable.
BR-EL-016 — Unit Head final scope for CL/RH
For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority except for the Director-specific self-sanction case.
BR-EL-017 — Unit Head recommendation for higher-sanction leave
For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended; Not Recommended is not a final rejection and both outcomes continue through the applicable higher-sanction path.
BR-EL-018 — Higher-sanction routing
SCL, EL, COL, and VL requests requiring higher sanction shall proceed through the current configured hierarchy to the resolved final Sanctioning Authority.
BR-EL-019 — Authority resolution and optional Establishment step
The processing/sanctioning path shall be resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration; an Establishment step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director occur only where configured.
BR-EL-020 — Director self-sanction
When the Director is the applicant, the Director-specific self-sanction path replaces the normal Unit Head/higher-authority route.
BR-EL-021 — RETIRED — Modify Pending Request
The former rule permitting pending-request modification is retired. Post-submission modification is not part of the synchronized baseline.
BR-EL-022 — Immediate withdrawal of pending request
A pending request may be withdrawn at any time before final approval; withdrawal is immediate, terminates remaining approval processing, blocks later approve/reject actions, and informs concerned roles. After final approval, withdrawal is unavailable.
BR-EL-023 — Cancellation of approved leave before start
An approved leave may be cancelled only before its start date; cancellation uses the same applicable hierarchy, does not edit the approved leave in place, approval marks the leave Cancelled and restores/adjusts already deducted balance, while rejection leaves the original approval unchanged.
BR-EL-024 — Fresh application after cancellation
If revised leave is still required after cancellation, a fresh leave application shall be submitted rather than editing the approved leave in place.
BR-EL-025 — Extension of ongoing EL/COL/VL
Extension is available only for ongoing EL/COL/VL; it uses applicable eligibility, balance, substitute, calendar and sanction rules; approval posts only the incremental additional period while rejection preserves the original approved leave.
BR-EL-026 — RETIRED IDENTIFIER
No active rule is assigned to this identifier.
BR-EL-027 — Resumption applicability and review authority
Formal resumption review applies to EL, COL, and VL; the employee submits actual resumption information and the applicable Sanctioning Authority reviews it.
BR-EL-028 — Normal, early, and late resumption outcome
If actual resumption equals the approved end date, review causes no adjustment to approved leave period or balance. If actual resumption is earlier or later, after review ELM records the actual leave period, adjusts leave balance accordingly, and synchronizes relevant leave/attendance records.
BR-EL-029 — Offline-sanctioned leave synchronization
Only leave already sanctioned through an authorized offline/paper process may be retrospectively recorded; sanction/reference evidence shall be captured, record consistency validated, relevant balance/history synchronized, and no second approval workflow initiated.
BR-EL-030 — Current configured policy and hierarchy
ELM validation and routing shall use the current configured leave-policy parameters and hierarchy configuration. No draft/publish/effective-version lifecycle applies to leave-policy parameters in this baseline.
BR-EL-031 — Effective published holiday/RH calendar
Date and RH validation shall use the currently effective published holiday/RH calendar until a replacement calendar is published.
BR-EL-032 — SLA reminder on still-pending task
When an SLA-controlled actionable task reaches its configured reminder threshold, issue a reminder to the responsible user and log it only if the task is still pending; otherwise issue no reminder.
BR-EL-033 — SLA escalation on still-pending task
When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action: notify the configured higher/responsible authority and, where the escalation configuration changes routing/responsibility, apply that routing/responsibility change; the escalation action shall be logged. If the task is no longer pending, no escalation shall be issued.
BR-EL-034 — No post-submission modification
A submitted pending leave request shall not be modified in place. If change is needed before final approval, the employee may withdraw and submit a new application if needed.
BR-EL-035 — Actionable task assignment notification
When an actionable workflow task is assigned to a user, ELM shall notify the assigned user.
BR-EL-036 — Role-based authorization
ELM capabilities shall be available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role.
BR-EL-037 — Administrative maintenance is not sanctioning
Authorized leave-record maintenance/correction shall not itself create a new sanctioning decision; retrospective offline entry is also synchronization rather than a second approval.
BR-EL-038 — Configurable SLA thresholds
Reminder and escalation thresholds for SLA-controlled actionable workflow tasks shall be configurable by an authorized administrative role and shall govern EL-UC-021 event-triggered SLA processing.

## 03_ELM_Use_Case_Specifications_v1.4_FINAL.docx
EL-UC-001 — Apply for Leave
Create and submit a valid new leave application and place it into the applicable processing path.
EL-UC-002 — Respond to Substitute Request
Accept or decline a nominated responsibility assignment.
EL-UC-003 — Review Leave-Related Request at Unit Head
Review a routed new-leave, cancellation, or extension request and record the decision/recommendation permitted by the applicable policy.
EL-UC-004 — Verify and Route Higher-Sanction Request
Perform the configured Establishment-level verification/routing step and forward the request to the resolved competent authority.
EL-UC-005 — Make Final Sanctioning Decision
Record the final approve/reject decision for a routed higher-sanction new-leave, cancellation, or extension request.
EL-UC-007 — Withdraw Pending Request
Immediately terminate a pending request before final approval.
EL-UC-008 — Request Cancellation of Approved Leave
Request pre-start cancellation of an approved leave without editing the approved leave in place.
EL-UC-009 — Request Extension of Ongoing Leave
Request additional leave time while ongoing EL, COL, or VL is being availed.
EL-UC-010 — Submit Resumption of Duty
Submit actual return-to-duty information after EL, COL, or VL for review.
EL-UC-011 — Review Resumption
Review the submitted resumption and apply only the adjustments required by the actual return date.
EL-UC-012 — View Leave Balances and History
Inspect own current leave balances and leave-account/request history, including request status and final decisions.
EL-UC-013 — Obtain Printable/Exportable Leave Application
Obtain a printable or exportable representation of an accessible leave application.
EL-UC-014 — Maintain Policy and Hierarchy Configuration
Create/revise current ELM leave-policy parameters and maintain hierarchy configuration used for validation and routing.
EL-UC-015 — Maintain and Publish Holiday/RH Calendar
Create, revise, and publish the holiday/RH calendar used by date and RH validation.
EL-UC-016 — Record Already-Sanctioned Offline Leave
Synchronize ELM with leave already sanctioned through an authorized offline/paper process when ELM could not originally be used.
EL-UC-017 — Maintain Authorized Leave Records
Maintain or correct leave records within the actor's authorized record-maintenance scope without creating a sanctioning decision.
EL-UC-018 — Configure Workflow SLA Thresholds
Configure reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
EL-UC-019 — Nominate Replacement Substitute After Decline
Recover from a substitute decline by nominating one replacement eligible substitute.
EL-UC-020 — Execute Year-End Leave Processing
Apply the defined year-end leave-account outcomes and record the resulting processing evidence.
EL-UC-021 — Process SLA Threshold Event
Process a configured SLA reminder or escalation threshold for an actionable workflow task.

## 06_ELM_Workflow_Specifications_v1.6_FINAL.docx
CW-EL-01 — New Leave Processing and Pending Withdrawal
Type | Composite
Purpose / Scope | Provide the end-to-end progression for a new leave request, including substitute consent/recovery, Unit-Head-final CL/RH decisions, higher-sanction routing, the Director-specific self-sanction route, and immediate withdrawal from every valid pending pre-final state.
Trigger | Employee submits a valid new leave request.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority; Director in self-sanction case
Constituent Workflows | BW-EL-01–09
Related Workflows | CW-EL-02; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-002–003, CFR-EL-011–018
Related UCs | EL-UC-001–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001–020, BR-EL-022, BR-EL-030–035
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; substitute required | Awaiting Substitute Response | BR-EL-001–015, BR-EL-030–031
2 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is Director | Awaiting Director Self-Sanction | BR-EL-001–013, BR-EL-020, BR-EL-030–031
3 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is not Director | Awaiting Unit Head Review | BR-EL-001–013, BR-EL-030–031
4 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is Director | Awaiting Director Self-Sanction | BR-EL-014–015, BR-EL-020
5 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is not Director | Awaiting Unit Head Review | BR-EL-014–015
6 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Applicant Action Required | BR-EL-014–015
7 | Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Substitute Response | BR-EL-014–015
8 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Approve | Approved | BR-EL-016
9 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Reject | Rejected | BR-EL-016
10 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; Establishment configured | Awaiting Establishment Routing | BR-EL-017–019, BR-EL-030
11 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; no Establishment step | Awaiting Final Sanction Decision | BR-EL-017–019, BR-EL-030
12 | Awaiting Establishment Routing | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Awaiting Final Sanction Decision | BR-EL-018–019, BR-EL-030
13 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-004, BR-EL-017–019
14 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-004, BR-EL-017–019
15 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-020
16 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-020
17 | Awaiting Substitute Response; Applicant Action Required; Awaiting Unit Head Review; Awaiting Establishment Routing; Awaiting Final Sanction Decision; Awaiting Director Self-Sanction | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds before final approval | Withdrawn | BR-EL-022, BR-EL-034
CW-EL-02 — Approved Leave Cancellation
Type | Composite
Purpose / Scope | Represent cancellation of approved leave before its start through the same applicable decision hierarchy, with distinct cancellation-approved and cancellation-rejected effects. A later revised leave request is a fresh New Leave instance, not part of this workflow.
Trigger | Employee requests cancellation of an approved leave before its start date.
Participants | Employee; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-10–11
Related Workflows | CW-EL-01; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-019
Related UCs | EL-UC-008, EL-UC-003–005
Related BRs | BR-EL-016–019, BR-EL-023–024, BR-EL-030
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Approved / Not Started | Employee | EL-UC-008 / Request Cancellation of Approved Leave | Cancellation eligible | Cancellation Pending — Unit Head Review | BR-EL-023
2 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-016, BR-EL-023
3 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Reject cancellation | Approved / Unchanged | BR-EL-016, BR-EL-023
4 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; Establishment configured | Cancellation Pending — Establishment | BR-EL-017–019, BR-EL-023, BR-EL-030
5 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; no Establishment step | Cancellation Pending — Final Decision | BR-EL-017–019, BR-EL-023, BR-EL-030
6 | Cancellation Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Cancellation Pending — Final Decision | BR-EL-018–019, BR-EL-023, BR-EL-030
7 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-023
8 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject cancellation | Approved / Unchanged | BR-EL-023
CW-EL-03 — Ongoing Leave Extension
Type | Composite
Purpose / Scope | Represent an extension of ongoing EL/COL/VL through applicable validation, substitute consent/recovery where required, Unit Head recommendation, configured higher-sanction decision, and immediate withdrawal of the pending extension request where applicable.
Trigger | Employee on ongoing EL/COL/VL requests additional leave time.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-12–14
Related Workflows | CW-EL-01; CW-EL-02; CW-EL-04
Related CFRs | CFR-EL-020, CFR-EL-018 where pending-extension withdrawal applies
Related UCs | EL-UC-009, EL-UC-002–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001, BR-EL-005–019, BR-EL-022, BR-EL-025, BR-EL-030–031
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; substitute required | Awaiting Extension Substitute Response | BR-EL-001, BR-EL-005–015, BR-EL-025, BR-EL-030–031
2 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; no substitute required | Awaiting Extension Unit Head Review | BR-EL-001, BR-EL-005–013, BR-EL-025, BR-EL-030–031
3 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept | Awaiting Extension Unit Head Review | BR-EL-014–015, BR-EL-025
4 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Extension Applicant Action Required | BR-EL-014–015, BR-EL-025
5 | Extension Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Extension Substitute Response | BR-EL-014–015
6 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; Establishment configured | Extension Pending — Establishment | BR-EL-017–019, BR-EL-025, BR-EL-030
7 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; no Establishment step | Extension Pending — Final Decision | BR-EL-017–019, BR-EL-025, BR-EL-030
8 | Extension Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Extension Pending — Final Decision | BR-EL-018–019, BR-EL-025, BR-EL-030
9 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Extended Leave in Effect — Incremental Period Posted | BR-EL-025
10 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Original Ongoing Leave Unchanged | BR-EL-025
11 | Awaiting Extension Substitute Response; Extension Applicant Action Required; Awaiting Extension Unit Head Review; Extension Pending — Establishment; Extension Pending — Final Decision | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds while extension request remains pending | Extension Request Withdrawn — Original Leave Unchanged | BR-EL-022
CW-EL-04 — Resumption Review
Type | Composite
Purpose / Scope | Coordinate employee submission of actual resumption information with review by the applicable Sanctioning Authority, distinguishing normal, early, and late return without inventing a generic leave-closure state.
Trigger | Employee returns from EL/COL/VL and submits actual resumption information.
Participants | Employee; applicable Sanctioning Authority
Constituent Workflows | BW-EL-15–17
Related Workflows | CW-EL-02; CW-EL-03
Related CFRs | CFR-EL-021
Related UCs | EL-UC-010, EL-UC-011
Related BRs | BR-EL-027–028
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Returned from EL/COL/VL | Employee | EL-UC-010 / Submit Resumption of Duty | Actual resumption details submitted | Resumption Review Pending | BR-EL-027
2 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date = approved end date | Resumption Reviewed — No Adjustment | BR-EL-027–028
3 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date < approved end date | Resumption Reviewed — Early Return Synchronized | BR-EL-028
4 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date > approved end date | Resumption Reviewed — Late Return Synchronized | BR-EL-028
6. Cross-Cutting Automatic SLA Routing / Responsibility Escalation Pattern
Pattern ID | XTP-EL-01
Applies To | Any SLA-controlled actionable task state in CW-EL-01–04 where the configured escalation changes routing/responsibility.
Trigger | Configured escalation threshold reached.
Performer | System (workflow transition performer; not a UC actor).
Related UC | EL-UC-021 / Process SLA Threshold Event
Related BRs | BR-EL-033, BR-EL-038
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Any SLA-controlled actionable task state that remains pending | System | EL-UC-021 / Process SLA Threshold Event | Escalation threshold reached; task still pending; configured action changes routing/responsibility | Same business process state; actionable task responsibility/routing updated to configured higher/responsible authority | BR-EL-033, BR-EL-038
Artifact | Reason outside Workflow Registry | Retained Representation
EL-UC-006 | Retired. Pending in-place modification is not part of the synchronized baseline. | Retired identifier + BR-EL-034 no-modification rule
EL-UC-012 / EL-UC-013 | Informational inquiry/export capabilities; no connected persistent business-state progression. | Use Cases
EL-UC-014 / EL-UC-015 / EL-UC-017 / EL-UC-018 | Administrative configuration/maintenance interactions; isolated actor-goal functions rather than connected process progression. | Use Cases + applicable BRs
EL-UC-016 | Retrospective synchronization of already-sanctioned offline leave; explicitly not a second approval progression. | Use Case + BR-EL-029
EL-UC-020 | Event-triggered year-end leave-account processing; an isolated timed operation applying year-end BRs, not by itself a connected workflow progression. | Event-triggered Use Case + BR-EL-002–009
EL-UC-021 reminder / notification-only escalation | Event-triggered threshold behavior that does not change process routing/responsibility. | Event-triggered Use Case + BR-EL-032/033/038
BR-EL-035 task-assignment notification | Notification effect attached to actionable task assignment; not a standalone workflow. | Business Rule / UC effect
Previous Workflow | Disposition | Replacement | Rationale
WF-EL-01 Apply and Decide Leave | Reconstructed | CW-EL-01 + BW-EL-01–09 | Uses complete new-leave Basis paths; substitute consent/recovery fragments are embedded within the applicable CL/RH, higher-sanction, and Director paths.
WF-EL-02 Modify or Withdraw Pending Request | Retired / redistributed | Withdrawal in CW-EL-01 and CW-EL-03; no Modify workflow | Pending in-place modification is removed. Withdrawal is represented where it is actually valid.
WF-EL-03 Cancel Approved Leave | Reconstructed | CW-EL-02 + BW-EL-10–11 | Uses complete cancellation paths with terminal approve/reject alternatives; fresh application remains outside cancellation.
WF-EL-04 Extend Ongoing Leave | Reconstructed | CW-EL-03 + BW-EL-12–14 | Uses complete extension paths for no-substitute, accepted-consent, and one decline/replacement traversal variants.
WF-EL-05 Resume Duty and Close Leave | Reconstructed | CW-EL-04 + BW-EL-15–17 | Replaces “closure” and verifier semantics with Sanctioning Authority review and normal/early/late outcomes.
WF-EL-06 Record Offline-Sanctioned Leave | Retired as workflow | EL-UC-016 + BR-EL-029 | Record synchronization, not a second approval progression.
WF-EL-07 Year-End Leave Processing | Retired as workflow | EL-UC-020 + BR-EL-002–009 | Event-triggered isolated system operation; no SF representation type.
WF-EL-08 SLA Reminder / Escalation | Retired as standalone workflow | EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing changes | Reminder/notification-only behavior is UC+BR; routing-changing escalation is cross-cutting System transition only.


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file modules/directory/contracts.py
```
"""directory's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef
from modules.directory.services.sync import ensure_users_cached


@dataclass(frozen=True)
class UserDTO:
    user_id: int
    username: str
    display_name: str
    kind: str
    email: str = ""
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None
    #: Maintained on the ERP portal's profile page, read here.
    resume_link: str = ""
    profile_completed: bool = False


def _to_dto(r: UserRef) -> UserDTO:
    return UserDTO(
        user_id=r.user_id, username=r.username, display_name=r.display_name,
        kind=r.kind, email=r.email, department=r.department,
        programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
        resume_link=r.resume_link, profile_completed=r.profile_completed,
    )


def get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]:
    """Batched. A missing id is simply absent from the mapping — a visible,
    testable case rather than a silent None three layers up."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    ensure_users_cached(ids)
    return {r.user_id: _to_dto(r) for r in UserRef.objects.filter(user_id__in=ids)}


def user_ids_in_discipline(discipline: str) -> list[int]:
    return list(
        UserRef.objects.filter(discipline=discipline, kind="student", is_active=True)
        .values_list("user_id", flat=True)
    )


def get_employees() -> list[UserDTO]:
    """Everyone on the payroll: faculty and staff, not students."""
    return [
        _to_dto(r)
        for r in UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).order_by("user_id")
    ]


def held_employee_ids() -> set[int]:
    return set(
        UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).values_list("user_id", flat=True)
    )


def employee_projection_disagreement() -> tuple[list[int], list[int]] | None:
    """Where this service and the identity service disagree about the payroll."""
    held = held_employee_ids()
    try:
        known = {r.user_id for r in get_client().iter_employees()}
    except IamUnavailable:
        return None
    return sorted(known - held), sorted(held - known)


def search(q: str = "", kind: str | None = None, limit: int = 25) -> list[UserDTO]:
    qs = UserRef.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(display_name__icontains=q)
    return [_to_dto(r) for r in qs.order_by("display_name")[:limit]]

```


### Repository file core/db/mixins.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    """A row belonging to a person.

    `user_id` is the IAM user id. It is a plain integer and NOT a ForeignKey —
    there is no user table in this database, and cross-boundary references must
    stay unconstrained so a module can be extracted later without schema
    surgery.
    """

    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

```


### Repository file modules/placement/registry.py
```
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement_cell.application.auto_withdraw",
    "placement_cell.offer.expire",
]

_STUDENT = [
    "placement_cell.registration.self",
    "placement_cell.job_posting.view",
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.application.delete",
    "placement_cell.offer.respond",
]

_COORDINATOR = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.application.review",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
]

_OFFICER = [
    *_COORDINATOR,
    "placement_cell.job_posting.manage",
    "placement_cell.interview.schedule",
    "placement_cell.offer.issue",
    "placement_cell.offer.revoke",
    "placement_cell.company.manage",
    "placement_cell.announcement.publish",
    "placement_cell.registration.manage",
    "placement_cell.registration.debar",
    "placement_cell.record.manage",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
    "placement_cell.announcement.publish",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_coordinator": _COORDINATOR,
    "placement_officer": _OFFICER,
    "placement_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}

```


## Prompt 002 Retry foundation: compact models only

UTC: 2026-10-12T13:30:46.864753+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 4096}`

The prior multi-file attempt exceeded the output limit while repeating model methods, and no files could be applied. Retry as a SMALL single-file initial implementation attempt. Generate only modules/leave_elm/models.py as Django data-model definitions. Maximum approximately 180 lines. Do not put business functions, save overrides, can_* methods, getters, placeholders, duplicate class definitions or validation methods in models.py. Use compact fields and choices, and plain integer IAM user IDs. The foundation should store employee leave requests and their workflow status, leave balances, configurable policy/hierarchy/calendar, substitution, cancellation/extension/resumption data, history, notifications and pending tasks/SLA. You may use JSONField for configuration details to keep the model representation compact. Include data only; later service files will implement operations against these actual fields. Do not create Django user/login models. This is initial generation of previously unapplied output, not a functional review. Return a complete valid JSON response and a complete models.py without code fences.

Required output paths:
modules/leave_elm/models.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file docs/08-delivery/elm-qwen-trial/specification-context-compact.md
```
# ELM supplied specification context

This is extracted from the supplied specification artifacts. Historical and retired IDs are not active requirements. Workflow v1.6 STTs take precedence over older v1.5 workflow registries.


## Problem statement v1.4
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

## Consolidated requirements v1.5
CFR-EL-001 Role-based ELM access: The system shall restrict ELM capabilities to users authorized for the corresponding employee, processing, sanctioning, or administrative roles.
CFR-EL-002 Create and submit leave application: The system shall allow an eligible employee to create and submit one leave application for CL, RH, SCL, EL, COL, or VL, capturing the leave category, requested period, purpose/reason, and other required information; when Station Leave applies, its details shall be captured within the same application rather than through a separate leave-request process.
CFR-EL-003 Validate a leave request before progression: Before a new leave request is allowed to proceed, the system shall validate the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date shall not be treated as overlapping when they occupy different halves.
CFR-EL-004 Casual Leave (CL) entitlement and treatment: The system shall maintain an annual CL entitlement of 8 days for each employee, support first-half and second-half CL with an approved half day consuming 0.5 CL day, and lapse unused CL at year end without carry-forward.
CFR-EL-005 Restricted Holiday (RH) entitlement and treatment: The system shall maintain an annual RH entitlement of 2 days for each employee, permit an RH request only for an applicable Restricted Holiday in the currently effective published holiday/RH calendar, and lapse unused RH at year end without carry-forward.
CFR-EL-006 Special Casual Leave (SCL) entitlement and treatment: The system shall support up to 15 SCL days per calendar year for each employee for a special purpose considered admissible by the applicable sanctioning authority, and shall lapse unused SCL at year end without carry-forward.
CFR-EL-007 Earned Leave (EL) entitlement and carry-forward: The system shall credit each non-faculty employee with 30 EL days per year and carry forward unused EL according to policy.
CFR-EL-008 Faculty Vacation Leave (VL) and VL-to-EL conversion: The system shall maintain 60 VL for each faculty member for vacation periods supplied through the institute Academic Calendar, permit VL only during an applicable vacation period, and at year end convert all unused VL to EL at 2 VL : 1 EL including fractional conversion; VL itself shall not carry forward, while the converted EL shall be credited to the faculty member’s EL balance, may carry forward, and may subsequently be used.
CFR-EL-009 Commuted Leave (COL) entitlement and treatment: The system shall maintain an annual COL entitlement of 20 days for each eligible employee in this baseline, treat COL as medical/balance-controlled leave, require supporting medical evidence where applicable, and carry forward unused COL according to policy.
CFR-EL-010 Continuous-day counting: For EL, COL, and VL, the system shall count intervening weekends and closed holidays within a continuous approved leave interval as leave days; this continuous-day rule shall not apply to CL, SCL, or RH.
CFR-EL-011 Nominate an eligible substitute: When responsibility coverage is required, the system shall allow the applicant to nominate one substitute who is another employee, is not the applicant, and has no overlapping pending or approved leave during the responsibility period.
CFR-EL-012 Obtain substitute response and enforce consent gate: The system shall allow the nominated substitute to accept or decline the responsibility assignment; approval routing shall not proceed until required substitute consent is accepted, and after a decline the applicant shall be allowed to nominate another eligible substitute or withdraw the pending request.
CFR-EL-013 CL/RH Unit Head final decision: For CL and RH, including associated Station Leave, the system shall route the submitted request to the applicant’s Unit Head and allow the Unit Head to make the final approve/reject decision, except where the Director-specific self-sanction rule applies.
CFR-EL-014 Higher-sanction leave progression to final decision: For SCL, EL, COL, and VL, the system shall route the request to the Unit Head for review and recording of Recommended or Not Recommended, shall not treat Not Recommended as a final rejection, and shall then route the request through the configured hierarchy to the resolved final Sanctioning Authority for an approve/reject decision. The route shall be resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration, and may include an Establishment processing step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director where configured.
CFR-EL-015 Director self-sanction: When the Director is the applicant, the system shall apply the Director-specific self-sanction path instead of the normal Unit Head/higher-authority routing path.
CFR-EL-016 Record and communicate the final leave decision: On a final leave decision, the system shall record the decision and notify the employee. When the decision is approval, the system shall also update the employee’s leave record/account. Intermediate processing decisions and state changes need not generate general notifications but shall be available to the employee through status/history inquiry.
CFR-EL-017 No post-submission modification of a pending request: The system shall not permit a submitted pending leave request to be modified in place. A pending request that requires change may instead be withdrawn before final approval, after which a new leave application may be submitted if needed.
CFR-EL-018 Immediate withdrawal of a pending request: The system shall allow an employee to withdraw a pending leave application at any time before final approval and, upon successful withdrawal, shall make the withdrawal effective immediately, terminate all remaining approval processing for that application, prevent any later approve/reject action, and notify the concerned roles of the withdrawal. After final approval, withdrawal shall no longer be available and the approved-leave cancellation process shall apply where relevant.
CFR-EL-019 Cancel approved leave before start: The system shall allow an employee to request cancellation of an approved leave before its start date, process the cancellation through the same applicable approval hierarchy to a final decision, and shall not edit the approved leave in place. If cancellation is approved, the system shall mark the leave Cancelled and restore or adjust any leave balance already deducted for that approval; if cancellation is rejected, the original approved leave shall remain unchanged. If revised leave is still needed after cancellation, a fresh application shall be submitted. Once the leave has begun, the pre-start cancellation path shall no longer apply.
CFR-EL-020 Extend ongoing EL/COL/VL: The system shall allow an employee on ongoing EL, COL, or VL to request additional leave time, validate the extension against applicable eligibility, balance, substitute, calendar, and approval conditions, obtain required substitute consent before routing, and process the extension through the applicable Unit Head and configured higher-sanction path. If approved, only the incremental additional leave period shall be posted while preserving the original approved leave as the base; if rejected, the original approved leave shall remain unchanged.
CFR-EL-021 Review resumption and adjust actual leave where required: The system shall allow an employee returning from EL, COL, or VL to submit the actual resumption date and required details for review by the applicable Sanctioning Authority. When the employee resumes on the approved end date, the authority shall review the resumption without changing the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, the system shall, after the resumption review, record the actual leave period, adjust the leave balance accordingly, and synchronize the relevant leave/attendance records.
CFR-EL-022 View leave balances and history: The system shall allow an employee to view current leave balances and leave-account/request history, including the current status and recorded final decisions of the employee’s leave requests.
CFR-EL-023 Obtain printable/exportable leave application: The system shall allow an employee to obtain a printable/exportable representation of a leave application accessible to that employee.
CFR-EL-024 Maintain policy parameters and hierarchy configuration: The system shall allow authorized administrative roles to create and revise leave-policy parameters and maintain the hierarchy configuration used for validation and routing; ELM shall use the current configured policy and hierarchy values. No draft/publish/effective-version lifecycle is required for leave-policy parameters in this baseline.
CFR-EL-025 Maintain and publish the holiday/RH calendar: The system shall allow authorized administrative roles to create, revise, and publish the holiday/RH calendar, and date/RH validation shall use the currently effective published holiday/RH calendar until a replacement is published.
CFR-EL-026 Maintain authorized leave records: The system shall allow authorized administrative roles to maintain or correct leave records where their role permits such record maintenance, while preserving the distinction between administrative record maintenance and leave sanctioning.
CFR-EL-027 Record already-sanctioned offline leave: The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized paper/offline process when ELM could not be used, shall capture the sanction/reference evidence, validate the entry for record consistency, and update the relevant leave balance/history. This operation is record synchronization and shall not initiate a second approval workflow.
CFR-EL-028 Execute and record year-end leave-account processing: At year end, the system shall execute the applicable leave-account outcomes defined by policy: lapse unused CL, RH, and SCL; perform the faculty VL-to-EL conversion; carry forward EL and COL; record the resulting leave-account transactions; and report processing exceptions.
CFR-EL-029 Configure workflow-task SLA thresholds: The system shall support configurable reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
CFR-EL-030 Notify a user when an actionable task is assigned: When an actionable workflow task is assigned to a user, the system shall notify the assigned user of that task.
CFR-EL-031 Remind on a still-pending SLA task: When an SLA-controlled actionable task reaches its configured reminder threshold and is still pending, the system shall remind the responsible user and log the reminder action; if the task is no longer pending at the threshold, the corresponding reminder shall not be issued.
CFR-EL-032 Escalate a still-pending SLA task: When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action to the configured higher/responsible authority and log the action; if the task is no longer pending at the threshold, the corresponding escalation shall not be issued.



## 04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx
BR-EL-001 — Supported leave-category eligibility
A new leave request shall use only CL, RH, SCL, EL, COL, or VL and shall satisfy the category-applicability conditions in the current configured ELM policy.
BR-EL-002 — Casual Leave entitlement and lapse
Each employee has 8 CL days per year; unused CL lapses at year end and does not carry forward.
BR-EL-003 — Restricted Holiday entitlement and applicability
Each employee has 2 RH days per year; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH lapses at year end.
BR-EL-004 — Special Casual Leave entitlement and admissibility
Each employee may use up to 15 SCL days per calendar year for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility criterion is required; unused SCL lapses at year end.
BR-EL-005 — Non-faculty Earned Leave credit and carry-forward
Each non-faculty employee shall receive 30 EL days per year and unused EL shall carry forward according to policy.
BR-EL-006 — Faculty Vacation Leave entitlement and vacation-period applicability
Each faculty member shall have 60 VL associated with vacation periods supplied by the institute Academic Calendar, and VL may be availed only during an applicable vacation period.
BR-EL-007 — VL-to-EL year-end conversion
At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward.
BR-EL-008 — Treatment of EL created by VL conversion
EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed.
BR-EL-009 — Commuted Leave entitlement and treatment
Eligible employees have 20 COL days/year in this baseline; COL is medical/balance-controlled, supporting medical evidence may be required where applicable, and unused COL carries forward.
BR-EL-010 — Half-day CL treatment
CL shall support first-half and second-half requests; an approved half day consumes 0.5 CL day.
BR-EL-011 — Continuous-day counting
For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days; this rule does not apply to CL, SCL, or RH.
BR-EL-012 — Applicant non-overlap with half-day CL exception
A new request shall not impermissibly overlap the employee's active pending or approved leave; first-half and second-half CL on the same date are non-overlapping when they occupy different halves.
BR-EL-013 — Station Leave coupling
Station Leave permission/details, when applicable, shall be captured within the same leave application and shall not create a separate leave-request process.
BR-EL-014 — Substitute eligibility
When responsibility coverage is required, exactly one substitute is nominated; the substitute must be another employee, must not be the applicant, and must have no overlapping pending or approved leave during the responsibility period.
BR-EL-015 — Substitute consent gate and decline recovery
Required approval routing shall not proceed until the nominated substitute accepts. A decline leaves the consent gate closed; the applicant may nominate another eligible substitute or withdraw the pending request where applicable.
BR-EL-016 — Unit Head final scope for CL/RH
For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority except for the Director-specific self-sanction case.
BR-EL-017 — Unit Head recommendation for higher-sanction leave
For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended; Not Recommended is not a final rejection and both outcomes continue through the applicable higher-sanction path.
BR-EL-018 — Higher-sanction routing
SCL, EL, COL, and VL requests requiring higher sanction shall proceed through the current configured hierarchy to the resolved final Sanctioning Authority.
BR-EL-019 — Authority resolution and optional Establishment step
The processing/sanctioning path shall be resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration; an Establishment step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director occur only where configured.
BR-EL-020 — Director self-sanction
When the Director is the applicant, the Director-specific self-sanction path replaces the normal Unit Head/higher-authority route.
BR-EL-021 — RETIRED — Modify Pending Request
The former rule permitting pending-request modification is retired. Post-submission modification is not part of the synchronized baseline.
BR-EL-022 — Immediate withdrawal of pending request
A pending request may be withdrawn at any time before final approval; withdrawal is immediate, terminates remaining approval processing, blocks later approve/reject actions, and informs concerned roles. After final approval, withdrawal is unavailable.
BR-EL-023 — Cancellation of approved leave before start
An approved leave may be cancelled only before its start date; cancellation uses the same applicable hierarchy, does not edit the approved leave in place, approval marks the leave Cancelled and restores/adjusts already deducted balance, while rejection leaves the original approval unchanged.
BR-EL-024 — Fresh application after cancellation
If revised leave is still required after cancellation, a fresh leave application shall be submitted rather than editing the approved leave in place.
BR-EL-025 — Extension of ongoing EL/COL/VL
Extension is available only for ongoing EL/COL/VL; it uses applicable eligibility, balance, substitute, calendar and sanction rules; approval posts only the incremental additional period while rejection preserves the original approved leave.
BR-EL-026 — RETIRED IDENTIFIER
No active rule is assigned to this identifier.
BR-EL-027 — Resumption applicability and review authority
Formal resumption review applies to EL, COL, and VL; the employee submits actual resumption information and the applicable Sanctioning Authority reviews it.
BR-EL-028 — Normal, early, and late resumption outcome
If actual resumption equals the approved end date, review causes no adjustment to approved leave period or balance. If actual resumption is earlier or later, after review ELM records the actual leave period, adjusts leave balance accordingly, and synchronizes relevant leave/attendance records.
BR-EL-029 — Offline-sanctioned leave synchronization
Only leave already sanctioned through an authorized offline/paper process may be retrospectively recorded; sanction/reference evidence shall be captured, record consistency validated, relevant balance/history synchronized, and no second approval workflow initiated.
BR-EL-030 — Current configured policy and hierarchy
ELM validation and routing shall use the current configured leave-policy parameters and hierarchy configuration. No draft/publish/effective-version lifecycle applies to leave-policy parameters in this baseline.
BR-EL-031 — Effective published holiday/RH calendar
Date and RH validation shall use the currently effective published holiday/RH calendar until a replacement calendar is published.
BR-EL-032 — SLA reminder on still-pending task
When an SLA-controlled actionable task reaches its configured reminder threshold, issue a reminder to the responsible user and log it only if the task is still pending; otherwise issue no reminder.
BR-EL-033 — SLA escalation on still-pending task
When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action: notify the configured higher/responsible authority and, where the escalation configuration changes routing/responsibility, apply that routing/responsibility change; the escalation action shall be logged. If the task is no longer pending, no escalation shall be issued.
BR-EL-034 — No post-submission modification
A submitted pending leave request shall not be modified in place. If change is needed before final approval, the employee may withdraw and submit a new application if needed.
BR-EL-035 — Actionable task assignment notification
When an actionable workflow task is assigned to a user, ELM shall notify the assigned user.
BR-EL-036 — Role-based authorization
ELM capabilities shall be available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role.
BR-EL-037 — Administrative maintenance is not sanctioning
Authorized leave-record maintenance/correction shall not itself create a new sanctioning decision; retrospective offline entry is also synchronization rather than a second approval.
BR-EL-038 — Configurable SLA thresholds
Reminder and escalation thresholds for SLA-controlled actionable workflow tasks shall be configurable by an authorized administrative role and shall govern EL-UC-021 event-triggered SLA processing.

## 03_ELM_Use_Case_Specifications_v1.4_FINAL.docx
EL-UC-001 — Apply for Leave
Create and submit a valid new leave application and place it into the applicable processing path.
EL-UC-002 — Respond to Substitute Request
Accept or decline a nominated responsibility assignment.
EL-UC-003 — Review Leave-Related Request at Unit Head
Review a routed new-leave, cancellation, or extension request and record the decision/recommendation permitted by the applicable policy.
EL-UC-004 — Verify and Route Higher-Sanction Request
Perform the configured Establishment-level verification/routing step and forward the request to the resolved competent authority.
EL-UC-005 — Make Final Sanctioning Decision
Record the final approve/reject decision for a routed higher-sanction new-leave, cancellation, or extension request.
EL-UC-007 — Withdraw Pending Request
Immediately terminate a pending request before final approval.
EL-UC-008 — Request Cancellation of Approved Leave
Request pre-start cancellation of an approved leave without editing the approved leave in place.
EL-UC-009 — Request Extension of Ongoing Leave
Request additional leave time while ongoing EL, COL, or VL is being availed.
EL-UC-010 — Submit Resumption of Duty
Submit actual return-to-duty information after EL, COL, or VL for review.
EL-UC-011 — Review Resumption
Review the submitted resumption and apply only the adjustments required by the actual return date.
EL-UC-012 — View Leave Balances and History
Inspect own current leave balances and leave-account/request history, including request status and final decisions.
EL-UC-013 — Obtain Printable/Exportable Leave Application
Obtain a printable or exportable representation of an accessible leave application.
EL-UC-014 — Maintain Policy and Hierarchy Configuration
Create/revise current ELM leave-policy parameters and maintain hierarchy configuration used for validation and routing.
EL-UC-015 — Maintain and Publish Holiday/RH Calendar
Create, revise, and publish the holiday/RH calendar used by date and RH validation.
EL-UC-016 — Record Already-Sanctioned Offline Leave
Synchronize ELM with leave already sanctioned through an authorized offline/paper process when ELM could not originally be used.
EL-UC-017 — Maintain Authorized Leave Records
Maintain or correct leave records within the actor's authorized record-maintenance scope without creating a sanctioning decision.
EL-UC-018 — Configure Workflow SLA Thresholds
Configure reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
EL-UC-019 — Nominate Replacement Substitute After Decline
Recover from a substitute decline by nominating one replacement eligible substitute.
EL-UC-020 — Execute Year-End Leave Processing
Apply the defined year-end leave-account outcomes and record the resulting processing evidence.
EL-UC-021 — Process SLA Threshold Event
Process a configured SLA reminder or escalation threshold for an actionable workflow task.

## 06_ELM_Workflow_Specifications_v1.6_FINAL.docx
CW-EL-01 — New Leave Processing and Pending Withdrawal
Type | Composite
Purpose / Scope | Provide the end-to-end progression for a new leave request, including substitute consent/recovery, Unit-Head-final CL/RH decisions, higher-sanction routing, the Director-specific self-sanction route, and immediate withdrawal from every valid pending pre-final state.
Trigger | Employee submits a valid new leave request.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority; Director in self-sanction case
Constituent Workflows | BW-EL-01–09
Related Workflows | CW-EL-02; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-002–003, CFR-EL-011–018
Related UCs | EL-UC-001–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001–020, BR-EL-022, BR-EL-030–035
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; substitute required | Awaiting Substitute Response | BR-EL-001–015, BR-EL-030–031
2 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is Director | Awaiting Director Self-Sanction | BR-EL-001–013, BR-EL-020, BR-EL-030–031
3 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is not Director | Awaiting Unit Head Review | BR-EL-001–013, BR-EL-030–031
4 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is Director | Awaiting Director Self-Sanction | BR-EL-014–015, BR-EL-020
5 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is not Director | Awaiting Unit Head Review | BR-EL-014–015
6 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Applicant Action Required | BR-EL-014–015
7 | Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Substitute Response | BR-EL-014–015
8 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Approve | Approved | BR-EL-016
9 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Reject | Rejected | BR-EL-016
10 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; Establishment configured | Awaiting Establishment Routing | BR-EL-017–019, BR-EL-030
11 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; no Establishment step | Awaiting Final Sanction Decision | BR-EL-017–019, BR-EL-030
12 | Awaiting Establishment Routing | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Awaiting Final Sanction Decision | BR-EL-018–019, BR-EL-030
13 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-004, BR-EL-017–019
14 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-004, BR-EL-017–019
15 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-020
16 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-020
17 | Awaiting Substitute Response; Applicant Action Required; Awaiting Unit Head Review; Awaiting Establishment Routing; Awaiting Final Sanction Decision; Awaiting Director Self-Sanction | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds before final approval | Withdrawn | BR-EL-022, BR-EL-034
CW-EL-02 — Approved Leave Cancellation
Type | Composite
Purpose / Scope | Represent cancellation of approved leave before its start through the same applicable decision hierarchy, with distinct cancellation-approved and cancellation-rejected effects. A later revised leave request is a fresh New Leave instance, not part of this workflow.
Trigger | Employee requests cancellation of an approved leave before its start date.
Participants | Employee; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-10–11
Related Workflows | CW-EL-01; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-019
Related UCs | EL-UC-008, EL-UC-003–005
Related BRs | BR-EL-016–019, BR-EL-023–024, BR-EL-030
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Approved / Not Started | Employee | EL-UC-008 / Request Cancellation of Approved Leave | Cancellation eligible | Cancellation Pending — Unit Head Review | BR-EL-023
2 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-016, BR-EL-023
3 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Reject cancellation | Approved / Unchanged | BR-EL-016, BR-EL-023
4 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; Establishment configured | Cancellation Pending — Establishment | BR-EL-017–019, BR-EL-023, BR-EL-030
5 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; no Establishment step | Cancellation Pending — Final Decision | BR-EL-017–019, BR-EL-023, BR-EL-030
6 | Cancellation Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Cancellation Pending — Final Decision | BR-EL-018–019, BR-EL-023, BR-EL-030
7 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-023
8 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject cancellation | Approved / Unchanged | BR-EL-023
CW-EL-03 — Ongoing Leave Extension
Type | Composite
Purpose / Scope | Represent an extension of ongoing EL/COL/VL through applicable validation, substitute consent/recovery where required, Unit Head recommendation, configured higher-sanction decision, and immediate withdrawal of the pending extension request where applicable.
Trigger | Employee on ongoing EL/COL/VL requests additional leave time.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-12–14
Related Workflows | CW-EL-01; CW-EL-02; CW-EL-04
Related CFRs | CFR-EL-020, CFR-EL-018 where pending-extension withdrawal applies
Related UCs | EL-UC-009, EL-UC-002–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001, BR-EL-005–019, BR-EL-022, BR-EL-025, BR-EL-030–031
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; substitute required | Awaiting Extension Substitute Response | BR-EL-001, BR-EL-005–015, BR-EL-025, BR-EL-030–031
2 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; no substitute required | Awaiting Extension Unit Head Review | BR-EL-001, BR-EL-005–013, BR-EL-025, BR-EL-030–031
3 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept | Awaiting Extension Unit Head Review | BR-EL-014–015, BR-EL-025
4 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Extension Applicant Action Required | BR-EL-014–015, BR-EL-025
5 | Extension Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Extension Substitute Response | BR-EL-014–015
6 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; Establishment configured | Extension Pending — Establishment | BR-EL-017–019, BR-EL-025, BR-EL-030
7 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; no Establishment step | Extension Pending — Final Decision | BR-EL-017–019, BR-EL-025, BR-EL-030
8 | Extension Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Extension Pending — Final Decision | BR-EL-018–019, BR-EL-025, BR-EL-030
9 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Extended Leave in Effect — Incremental Period Posted | BR-EL-025
10 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Original Ongoing Leave Unchanged | BR-EL-025
11 | Awaiting Extension Substitute Response; Extension Applicant Action Required; Awaiting Extension Unit Head Review; Extension Pending — Establishment; Extension Pending — Final Decision | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds while extension request remains pending | Extension Request Withdrawn — Original Leave Unchanged | BR-EL-022
CW-EL-04 — Resumption Review
Type | Composite
Purpose / Scope | Coordinate employee submission of actual resumption information with review by the applicable Sanctioning Authority, distinguishing normal, early, and late return without inventing a generic leave-closure state.
Trigger | Employee returns from EL/COL/VL and submits actual resumption information.
Participants | Employee; applicable Sanctioning Authority
Constituent Workflows | BW-EL-15–17
Related Workflows | CW-EL-02; CW-EL-03
Related CFRs | CFR-EL-021
Related UCs | EL-UC-010, EL-UC-011
Related BRs | BR-EL-027–028
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Returned from EL/COL/VL | Employee | EL-UC-010 / Submit Resumption of Duty | Actual resumption details submitted | Resumption Review Pending | BR-EL-027
2 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date = approved end date | Resumption Reviewed — No Adjustment | BR-EL-027–028
3 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date < approved end date | Resumption Reviewed — Early Return Synchronized | BR-EL-028
4 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date > approved end date | Resumption Reviewed — Late Return Synchronized | BR-EL-028
6. Cross-Cutting Automatic SLA Routing / Responsibility Escalation Pattern
Pattern ID | XTP-EL-01
Applies To | Any SLA-controlled actionable task state in CW-EL-01–04 where the configured escalation changes routing/responsibility.
Trigger | Configured escalation threshold reached.
Performer | System (workflow transition performer; not a UC actor).
Related UC | EL-UC-021 / Process SLA Threshold Event
Related BRs | BR-EL-033, BR-EL-038
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Any SLA-controlled actionable task state that remains pending | System | EL-UC-021 / Process SLA Threshold Event | Escalation threshold reached; task still pending; configured action changes routing/responsibility | Same business process state; actionable task responsibility/routing updated to configured higher/responsible authority | BR-EL-033, BR-EL-038
Artifact | Reason outside Workflow Registry | Retained Representation
EL-UC-006 | Retired. Pending in-place modification is not part of the synchronized baseline. | Retired identifier + BR-EL-034 no-modification rule
EL-UC-012 / EL-UC-013 | Informational inquiry/export capabilities; no connected persistent business-state progression. | Use Cases
EL-UC-014 / EL-UC-015 / EL-UC-017 / EL-UC-018 | Administrative configuration/maintenance interactions; isolated actor-goal functions rather than connected process progression. | Use Cases + applicable BRs
EL-UC-016 | Retrospective synchronization of already-sanctioned offline leave; explicitly not a second approval progression. | Use Case + BR-EL-029
EL-UC-020 | Event-triggered year-end leave-account processing; an isolated timed operation applying year-end BRs, not by itself a connected workflow progression. | Event-triggered Use Case + BR-EL-002–009
EL-UC-021 reminder / notification-only escalation | Event-triggered threshold behavior that does not change process routing/responsibility. | Event-triggered Use Case + BR-EL-032/033/038
BR-EL-035 task-assignment notification | Notification effect attached to actionable task assignment; not a standalone workflow. | Business Rule / UC effect
Previous Workflow | Disposition | Replacement | Rationale
WF-EL-01 Apply and Decide Leave | Reconstructed | CW-EL-01 + BW-EL-01–09 | Uses complete new-leave Basis paths; substitute consent/recovery fragments are embedded within the applicable CL/RH, higher-sanction, and Director paths.
WF-EL-02 Modify or Withdraw Pending Request | Retired / redistributed | Withdrawal in CW-EL-01 and CW-EL-03; no Modify workflow | Pending in-place modification is removed. Withdrawal is represented where it is actually valid.
WF-EL-03 Cancel Approved Leave | Reconstructed | CW-EL-02 + BW-EL-10–11 | Uses complete cancellation paths with terminal approve/reject alternatives; fresh application remains outside cancellation.
WF-EL-04 Extend Ongoing Leave | Reconstructed | CW-EL-03 + BW-EL-12–14 | Uses complete extension paths for no-substitute, accepted-consent, and one decline/replacement traversal variants.
WF-EL-05 Resume Duty and Close Leave | Reconstructed | CW-EL-04 + BW-EL-15–17 | Replaces “closure” and verifier semantics with Sanctioning Authority review and normal/early/late outcomes.
WF-EL-06 Record Offline-Sanctioned Leave | Retired as workflow | EL-UC-016 + BR-EL-029 | Record synchronization, not a second approval progression.
WF-EL-07 Year-End Leave Processing | Retired as workflow | EL-UC-020 + BR-EL-002–009 | Event-triggered isolated system operation; no SF representation type.
WF-EL-08 SLA Reminder / Escalation | Retired as standalone workflow | EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing changes | Reminder/notification-only behavior is UC+BR; routing-changing escalation is cross-cutting System transition only.

```


### Repository file core/db/mixins.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    """A row belonging to a person.

    `user_id` is the IAM user id. It is a plain integer and NOT a ForeignKey —
    there is no user table in this database, and cross-boundary references must
    stay unconstrained so a module can be extracted later without schema
    surgery.
    """

    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


## Prompt 003 App, domain, registry and contracts

UTC: 2026-10-12T13:32:43.533307+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 6000}`

Generate the remaining foundation files for the ELM implementation using YOUR actual models.py definitions supplied below. Use compact complete implementations and do not rename model fields. domain/policy.py must be pure Python, with the leave categories, basic entitlement/counting and workflow state definitions needed by your later service code. registry.py is a plain MODULE dictionary, NAV_ITEMS list of dictionaries, PERMISSIONS list of (code,label), ROLE_GRANTS mapping role names to permission-code lists, SYSTEM_PERMISSIONS list. Module code leave_elm, UI base_path /leave. Exactly three nav routes: /leave/mine (employee), /leave/queue (assigned tasks), /leave/admin (administrative configuration). Grant employee actions to faculty/staff/Employee and the named domain roles in the specification; use only leave_elm.*.* permission strings. AppConfig name modules.leave_elm, label leave_elm, default_auto_field django.db.models.BigAutoField. contracts.py public getters must accept sequences of user IDs and use your actual models. __init__.py files may be empty. Do not create login or tests. Keep the TOTAL response under about 220 lines. Return all requested files in the required JSON shape.

Required output paths:
modules/leave_elm/__init__.py
modules/leave_elm/apps.py
modules/leave_elm/domain/__init__.py
modules/leave_elm/domain/policy.py
modules/leave_elm/registry.py
modules/leave_elm/contracts.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file docs/08-delivery/elm-qwen-trial/specification-context-compact.md
```
# ELM supplied specification context

This is extracted from the supplied specification artifacts. Historical and retired IDs are not active requirements. Workflow v1.6 STTs take precedence over older v1.5 workflow registries.


## Problem statement v1.4
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

## Consolidated requirements v1.5
CFR-EL-001 Role-based ELM access: The system shall restrict ELM capabilities to users authorized for the corresponding employee, processing, sanctioning, or administrative roles.
CFR-EL-002 Create and submit leave application: The system shall allow an eligible employee to create and submit one leave application for CL, RH, SCL, EL, COL, or VL, capturing the leave category, requested period, purpose/reason, and other required information; when Station Leave applies, its details shall be captured within the same application rather than through a separate leave-request process.
CFR-EL-003 Validate a leave request before progression: Before a new leave request is allowed to proceed, the system shall validate the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date shall not be treated as overlapping when they occupy different halves.
CFR-EL-004 Casual Leave (CL) entitlement and treatment: The system shall maintain an annual CL entitlement of 8 days for each employee, support first-half and second-half CL with an approved half day consuming 0.5 CL day, and lapse unused CL at year end without carry-forward.
CFR-EL-005 Restricted Holiday (RH) entitlement and treatment: The system shall maintain an annual RH entitlement of 2 days for each employee, permit an RH request only for an applicable Restricted Holiday in the currently effective published holiday/RH calendar, and lapse unused RH at year end without carry-forward.
CFR-EL-006 Special Casual Leave (SCL) entitlement and treatment: The system shall support up to 15 SCL days per calendar year for each employee for a special purpose considered admissible by the applicable sanctioning authority, and shall lapse unused SCL at year end without carry-forward.
CFR-EL-007 Earned Leave (EL) entitlement and carry-forward: The system shall credit each non-faculty employee with 30 EL days per year and carry forward unused EL according to policy.
CFR-EL-008 Faculty Vacation Leave (VL) and VL-to-EL conversion: The system shall maintain 60 VL for each faculty member for vacation periods supplied through the institute Academic Calendar, permit VL only during an applicable vacation period, and at year end convert all unused VL to EL at 2 VL : 1 EL including fractional conversion; VL itself shall not carry forward, while the converted EL shall be credited to the faculty member’s EL balance, may carry forward, and may subsequently be used.
CFR-EL-009 Commuted Leave (COL) entitlement and treatment: The system shall maintain an annual COL entitlement of 20 days for each eligible employee in this baseline, treat COL as medical/balance-controlled leave, require supporting medical evidence where applicable, and carry forward unused COL according to policy.
CFR-EL-010 Continuous-day counting: For EL, COL, and VL, the system shall count intervening weekends and closed holidays within a continuous approved leave interval as leave days; this continuous-day rule shall not apply to CL, SCL, or RH.
CFR-EL-011 Nominate an eligible substitute: When responsibility coverage is required, the system shall allow the applicant to nominate one substitute who is another employee, is not the applicant, and has no overlapping pending or approved leave during the responsibility period.
CFR-EL-012 Obtain substitute response and enforce consent gate: The system shall allow the nominated substitute to accept or decline the responsibility assignment; approval routing shall not proceed until required substitute consent is accepted, and after a decline the applicant shall be allowed to nominate another eligible substitute or withdraw the pending request.
CFR-EL-013 CL/RH Unit Head final decision: For CL and RH, including associated Station Leave, the system shall route the submitted request to the applicant’s Unit Head and allow the Unit Head to make the final approve/reject decision, except where the Director-specific self-sanction rule applies.
CFR-EL-014 Higher-sanction leave progression to final decision: For SCL, EL, COL, and VL, the system shall route the request to the Unit Head for review and recording of Recommended or Not Recommended, shall not treat Not Recommended as a final rejection, and shall then route the request through the configured hierarchy to the resolved final Sanctioning Authority for an approve/reject decision. The route shall be resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration, and may include an Establishment processing step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director where configured.
CFR-EL-015 Director self-sanction: When the Director is the applicant, the system shall apply the Director-specific self-sanction path instead of the normal Unit Head/higher-authority routing path.
CFR-EL-016 Record and communicate the final leave decision: On a final leave decision, the system shall record the decision and notify the employee. When the decision is approval, the system shall also update the employee’s leave record/account. Intermediate processing decisions and state changes need not generate general notifications but shall be available to the employee through status/history inquiry.
CFR-EL-017 No post-submission modification of a pending request: The system shall not permit a submitted pending leave request to be modified in place. A pending request that requires change may instead be withdrawn before final approval, after which a new leave application may be submitted if needed.
CFR-EL-018 Immediate withdrawal of a pending request: The system shall allow an employee to withdraw a pending leave application at any time before final approval and, upon successful withdrawal, shall make the withdrawal effective immediately, terminate all remaining approval processing for that application, prevent any later approve/reject action, and notify the concerned roles of the withdrawal. After final approval, withdrawal shall no longer be available and the approved-leave cancellation process shall apply where relevant.
CFR-EL-019 Cancel approved leave before start: The system shall allow an employee to request cancellation of an approved leave before its start date, process the cancellation through the same applicable approval hierarchy to a final decision, and shall not edit the approved leave in place. If cancellation is approved, the system shall mark the leave Cancelled and restore or adjust any leave balance already deducted for that approval; if cancellation is rejected, the original approved leave shall remain unchanged. If revised leave is still needed after cancellation, a fresh application shall be submitted. Once the leave has begun, the pre-start cancellation path shall no longer apply.
CFR-EL-020 Extend ongoing EL/COL/VL: The system shall allow an employee on ongoing EL, COL, or VL to request additional leave time, validate the extension against applicable eligibility, balance, substitute, calendar, and approval conditions, obtain required substitute consent before routing, and process the extension through the applicable Unit Head and configured higher-sanction path. If approved, only the incremental additional leave period shall be posted while preserving the original approved leave as the base; if rejected, the original approved leave shall remain unchanged.
CFR-EL-021 Review resumption and adjust actual leave where required: The system shall allow an employee returning from EL, COL, or VL to submit the actual resumption date and required details for review by the applicable Sanctioning Authority. When the employee resumes on the approved end date, the authority shall review the resumption without changing the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, the system shall, after the resumption review, record the actual leave period, adjust the leave balance accordingly, and synchronize the relevant leave/attendance records.
CFR-EL-022 View leave balances and history: The system shall allow an employee to view current leave balances and leave-account/request history, including the current status and recorded final decisions of the employee’s leave requests.
CFR-EL-023 Obtain printable/exportable leave application: The system shall allow an employee to obtain a printable/exportable representation of a leave application accessible to that employee.
CFR-EL-024 Maintain policy parameters and hierarchy configuration: The system shall allow authorized administrative roles to create and revise leave-policy parameters and maintain the hierarchy configuration used for validation and routing; ELM shall use the current configured policy and hierarchy values. No draft/publish/effective-version lifecycle is required for leave-policy parameters in this baseline.
CFR-EL-025 Maintain and publish the holiday/RH calendar: The system shall allow authorized administrative roles to create, revise, and publish the holiday/RH calendar, and date/RH validation shall use the currently effective published holiday/RH calendar until a replacement is published.
CFR-EL-026 Maintain authorized leave records: The system shall allow authorized administrative roles to maintain or correct leave records where their role permits such record maintenance, while preserving the distinction between administrative record maintenance and leave sanctioning.
CFR-EL-027 Record already-sanctioned offline leave: The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized paper/offline process when ELM could not be used, shall capture the sanction/reference evidence, validate the entry for record consistency, and update the relevant leave balance/history. This operation is record synchronization and shall not initiate a second approval workflow.
CFR-EL-028 Execute and record year-end leave-account processing: At year end, the system shall execute the applicable leave-account outcomes defined by policy: lapse unused CL, RH, and SCL; perform the faculty VL-to-EL conversion; carry forward EL and COL; record the resulting leave-account transactions; and report processing exceptions.
CFR-EL-029 Configure workflow-task SLA thresholds: The system shall support configurable reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
CFR-EL-030 Notify a user when an actionable task is assigned: When an actionable workflow task is assigned to a user, the system shall notify the assigned user of that task.
CFR-EL-031 Remind on a still-pending SLA task: When an SLA-controlled actionable task reaches its configured reminder threshold and is still pending, the system shall remind the responsible user and log the reminder action; if the task is no longer pending at the threshold, the corresponding reminder shall not be issued.
CFR-EL-032 Escalate a still-pending SLA task: When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action to the configured higher/responsible authority and log the action; if the task is no longer pending at the threshold, the corresponding escalation shall not be issued.



## 04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx
BR-EL-001 — Supported leave-category eligibility
A new leave request shall use only CL, RH, SCL, EL, COL, or VL and shall satisfy the category-applicability conditions in the current configured ELM policy.
BR-EL-002 — Casual Leave entitlement and lapse
Each employee has 8 CL days per year; unused CL lapses at year end and does not carry forward.
BR-EL-003 — Restricted Holiday entitlement and applicability
Each employee has 2 RH days per year; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH lapses at year end.
BR-EL-004 — Special Casual Leave entitlement and admissibility
Each employee may use up to 15 SCL days per calendar year for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility criterion is required; unused SCL lapses at year end.
BR-EL-005 — Non-faculty Earned Leave credit and carry-forward
Each non-faculty employee shall receive 30 EL days per year and unused EL shall carry forward according to policy.
BR-EL-006 — Faculty Vacation Leave entitlement and vacation-period applicability
Each faculty member shall have 60 VL associated with vacation periods supplied by the institute Academic Calendar, and VL may be availed only during an applicable vacation period.
BR-EL-007 — VL-to-EL year-end conversion
At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward.
BR-EL-008 — Treatment of EL created by VL conversion
EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed.
BR-EL-009 — Commuted Leave entitlement and treatment
Eligible employees have 20 COL days/year in this baseline; COL is medical/balance-controlled, supporting medical evidence may be required where applicable, and unused COL carries forward.
BR-EL-010 — Half-day CL treatment
CL shall support first-half and second-half requests; an approved half day consumes 0.5 CL day.
BR-EL-011 — Continuous-day counting
For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days; this rule does not apply to CL, SCL, or RH.
BR-EL-012 — Applicant non-overlap with half-day CL exception
A new request shall not impermissibly overlap the employee's active pending or approved leave; first-half and second-half CL on the same date are non-overlapping when they occupy different halves.
BR-EL-013 — Station Leave coupling
Station Leave permission/details, when applicable, shall be captured within the same leave application and shall not create a separate leave-request process.
BR-EL-014 — Substitute eligibility
When responsibility coverage is required, exactly one substitute is nominated; the substitute must be another employee, must not be the applicant, and must have no overlapping pending or approved leave during the responsibility period.
BR-EL-015 — Substitute consent gate and decline recovery
Required approval routing shall not proceed until the nominated substitute accepts. A decline leaves the consent gate closed; the applicant may nominate another eligible substitute or withdraw the pending request where applicable.
BR-EL-016 — Unit Head final scope for CL/RH
For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority except for the Director-specific self-sanction case.
BR-EL-017 — Unit Head recommendation for higher-sanction leave
For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended; Not Recommended is not a final rejection and both outcomes continue through the applicable higher-sanction path.
BR-EL-018 — Higher-sanction routing
SCL, EL, COL, and VL requests requiring higher sanction shall proceed through the current configured hierarchy to the resolved final Sanctioning Authority.
BR-EL-019 — Authority resolution and optional Establishment step
The processing/sanctioning path shall be resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration; an Establishment step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director occur only where configured.
BR-EL-020 — Director self-sanction
When the Director is the applicant, the Director-specific self-sanction path replaces the normal Unit Head/higher-authority route.
BR-EL-021 — RETIRED — Modify Pending Request
The former rule permitting pending-request modification is retired. Post-submission modification is not part of the synchronized baseline.
BR-EL-022 — Immediate withdrawal of pending request
A pending request may be withdrawn at any time before final approval; withdrawal is immediate, terminates remaining approval processing, blocks later approve/reject actions, and informs concerned roles. After final approval, withdrawal is unavailable.
BR-EL-023 — Cancellation of approved leave before start
An approved leave may be cancelled only before its start date; cancellation uses the same applicable hierarchy, does not edit the approved leave in place, approval marks the leave Cancelled and restores/adjusts already deducted balance, while rejection leaves the original approval unchanged.
BR-EL-024 — Fresh application after cancellation
If revised leave is still required after cancellation, a fresh leave application shall be submitted rather than editing the approved leave in place.
BR-EL-025 — Extension of ongoing EL/COL/VL
Extension is available only for ongoing EL/COL/VL; it uses applicable eligibility, balance, substitute, calendar and sanction rules; approval posts only the incremental additional period while rejection preserves the original approved leave.
BR-EL-026 — RETIRED IDENTIFIER
No active rule is assigned to this identifier.
BR-EL-027 — Resumption applicability and review authority
Formal resumption review applies to EL, COL, and VL; the employee submits actual resumption information and the applicable Sanctioning Authority reviews it.
BR-EL-028 — Normal, early, and late resumption outcome
If actual resumption equals the approved end date, review causes no adjustment to approved leave period or balance. If actual resumption is earlier or later, after review ELM records the actual leave period, adjusts leave balance accordingly, and synchronizes relevant leave/attendance records.
BR-EL-029 — Offline-sanctioned leave synchronization
Only leave already sanctioned through an authorized offline/paper process may be retrospectively recorded; sanction/reference evidence shall be captured, record consistency validated, relevant balance/history synchronized, and no second approval workflow initiated.
BR-EL-030 — Current configured policy and hierarchy
ELM validation and routing shall use the current configured leave-policy parameters and hierarchy configuration. No draft/publish/effective-version lifecycle applies to leave-policy parameters in this baseline.
BR-EL-031 — Effective published holiday/RH calendar
Date and RH validation shall use the currently effective published holiday/RH calendar until a replacement calendar is published.
BR-EL-032 — SLA reminder on still-pending task
When an SLA-controlled actionable task reaches its configured reminder threshold, issue a reminder to the responsible user and log it only if the task is still pending; otherwise issue no reminder.
BR-EL-033 — SLA escalation on still-pending task
When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action: notify the configured higher/responsible authority and, where the escalation configuration changes routing/responsibility, apply that routing/responsibility change; the escalation action shall be logged. If the task is no longer pending, no escalation shall be issued.
BR-EL-034 — No post-submission modification
A submitted pending leave request shall not be modified in place. If change is needed before final approval, the employee may withdraw and submit a new application if needed.
BR-EL-035 — Actionable task assignment notification
When an actionable workflow task is assigned to a user, ELM shall notify the assigned user.
BR-EL-036 — Role-based authorization
ELM capabilities shall be available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role.
BR-EL-037 — Administrative maintenance is not sanctioning
Authorized leave-record maintenance/correction shall not itself create a new sanctioning decision; retrospective offline entry is also synchronization rather than a second approval.
BR-EL-038 — Configurable SLA thresholds
Reminder and escalation thresholds for SLA-controlled actionable workflow tasks shall be configurable by an authorized administrative role and shall govern EL-UC-021 event-triggered SLA processing.

## 03_ELM_Use_Case_Specifications_v1.4_FINAL.docx
EL-UC-001 — Apply for Leave
Create and submit a valid new leave application and place it into the applicable processing path.
EL-UC-002 — Respond to Substitute Request
Accept or decline a nominated responsibility assignment.
EL-UC-003 — Review Leave-Related Request at Unit Head
Review a routed new-leave, cancellation, or extension request and record the decision/recommendation permitted by the applicable policy.
EL-UC-004 — Verify and Route Higher-Sanction Request
Perform the configured Establishment-level verification/routing step and forward the request to the resolved competent authority.
EL-UC-005 — Make Final Sanctioning Decision
Record the final approve/reject decision for a routed higher-sanction new-leave, cancellation, or extension request.
EL-UC-007 — Withdraw Pending Request
Immediately terminate a pending request before final approval.
EL-UC-008 — Request Cancellation of Approved Leave
Request pre-start cancellation of an approved leave without editing the approved leave in place.
EL-UC-009 — Request Extension of Ongoing Leave
Request additional leave time while ongoing EL, COL, or VL is being availed.
EL-UC-010 — Submit Resumption of Duty
Submit actual return-to-duty information after EL, COL, or VL for review.
EL-UC-011 — Review Resumption
Review the submitted resumption and apply only the adjustments required by the actual return date.
EL-UC-012 — View Leave Balances and History
Inspect own current leave balances and leave-account/request history, including request status and final decisions.
EL-UC-013 — Obtain Printable/Exportable Leave Application
Obtain a printable or exportable representation of an accessible leave application.
EL-UC-014 — Maintain Policy and Hierarchy Configuration
Create/revise current ELM leave-policy parameters and maintain hierarchy configuration used for validation and routing.
EL-UC-015 — Maintain and Publish Holiday/RH Calendar
Create, revise, and publish the holiday/RH calendar used by date and RH validation.
EL-UC-016 — Record Already-Sanctioned Offline Leave
Synchronize ELM with leave already sanctioned through an authorized offline/paper process when ELM could not originally be used.
EL-UC-017 — Maintain Authorized Leave Records
Maintain or correct leave records within the actor's authorized record-maintenance scope without creating a sanctioning decision.
EL-UC-018 — Configure Workflow SLA Thresholds
Configure reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
EL-UC-019 — Nominate Replacement Substitute After Decline
Recover from a substitute decline by nominating one replacement eligible substitute.
EL-UC-020 — Execute Year-End Leave Processing
Apply the defined year-end leave-account outcomes and record the resulting processing evidence.
EL-UC-021 — Process SLA Threshold Event
Process a configured SLA reminder or escalation threshold for an actionable workflow task.

## 06_ELM_Workflow_Specifications_v1.6_FINAL.docx
CW-EL-01 — New Leave Processing and Pending Withdrawal
Type | Composite
Purpose / Scope | Provide the end-to-end progression for a new leave request, including substitute consent/recovery, Unit-Head-final CL/RH decisions, higher-sanction routing, the Director-specific self-sanction route, and immediate withdrawal from every valid pending pre-final state.
Trigger | Employee submits a valid new leave request.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority; Director in self-sanction case
Constituent Workflows | BW-EL-01–09
Related Workflows | CW-EL-02; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-002–003, CFR-EL-011–018
Related UCs | EL-UC-001–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001–020, BR-EL-022, BR-EL-030–035
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; substitute required | Awaiting Substitute Response | BR-EL-001–015, BR-EL-030–031
2 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is Director | Awaiting Director Self-Sanction | BR-EL-001–013, BR-EL-020, BR-EL-030–031
3 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is not Director | Awaiting Unit Head Review | BR-EL-001–013, BR-EL-030–031
4 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is Director | Awaiting Director Self-Sanction | BR-EL-014–015, BR-EL-020
5 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is not Director | Awaiting Unit Head Review | BR-EL-014–015
6 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Applicant Action Required | BR-EL-014–015
7 | Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Substitute Response | BR-EL-014–015
8 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Approve | Approved | BR-EL-016
9 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Reject | Rejected | BR-EL-016
10 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; Establishment configured | Awaiting Establishment Routing | BR-EL-017–019, BR-EL-030
11 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; no Establishment step | Awaiting Final Sanction Decision | BR-EL-017–019, BR-EL-030
12 | Awaiting Establishment Routing | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Awaiting Final Sanction Decision | BR-EL-018–019, BR-EL-030
13 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-004, BR-EL-017–019
14 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-004, BR-EL-017–019
15 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-020
16 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-020
17 | Awaiting Substitute Response; Applicant Action Required; Awaiting Unit Head Review; Awaiting Establishment Routing; Awaiting Final Sanction Decision; Awaiting Director Self-Sanction | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds before final approval | Withdrawn | BR-EL-022, BR-EL-034
CW-EL-02 — Approved Leave Cancellation
Type | Composite
Purpose / Scope | Represent cancellation of approved leave before its start through the same applicable decision hierarchy, with distinct cancellation-approved and cancellation-rejected effects. A later revised leave request is a fresh New Leave instance, not part of this workflow.
Trigger | Employee requests cancellation of an approved leave before its start date.
Participants | Employee; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-10–11
Related Workflows | CW-EL-01; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-019
Related UCs | EL-UC-008, EL-UC-003–005
Related BRs | BR-EL-016–019, BR-EL-023–024, BR-EL-030
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Approved / Not Started | Employee | EL-UC-008 / Request Cancellation of Approved Leave | Cancellation eligible | Cancellation Pending — Unit Head Review | BR-EL-023
2 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-016, BR-EL-023
3 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Reject cancellation | Approved / Unchanged | BR-EL-016, BR-EL-023
4 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; Establishment configured | Cancellation Pending — Establishment | BR-EL-017–019, BR-EL-023, BR-EL-030
5 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; no Establishment step | Cancellation Pending — Final Decision | BR-EL-017–019, BR-EL-023, BR-EL-030
6 | Cancellation Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Cancellation Pending — Final Decision | BR-EL-018–019, BR-EL-023, BR-EL-030
7 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-023
8 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject cancellation | Approved / Unchanged | BR-EL-023
CW-EL-03 — Ongoing Leave Extension
Type | Composite
Purpose / Scope | Represent an extension of ongoing EL/COL/VL through applicable validation, substitute consent/recovery where required, Unit Head recommendation, configured higher-sanction decision, and immediate withdrawal of the pending extension request where applicable.
Trigger | Employee on ongoing EL/COL/VL requests additional leave time.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-12–14
Related Workflows | CW-EL-01; CW-EL-02; CW-EL-04
Related CFRs | CFR-EL-020, CFR-EL-018 where pending-extension withdrawal applies
Related UCs | EL-UC-009, EL-UC-002–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001, BR-EL-005–019, BR-EL-022, BR-EL-025, BR-EL-030–031
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; substitute required | Awaiting Extension Substitute Response | BR-EL-001, BR-EL-005–015, BR-EL-025, BR-EL-030–031
2 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; no substitute required | Awaiting Extension Unit Head Review | BR-EL-001, BR-EL-005–013, BR-EL-025, BR-EL-030–031
3 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept | Awaiting Extension Unit Head Review | BR-EL-014–015, BR-EL-025
4 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Extension Applicant Action Required | BR-EL-014–015, BR-EL-025
5 | Extension Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Extension Substitute Response | BR-EL-014–015
6 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; Establishment configured | Extension Pending — Establishment | BR-EL-017–019, BR-EL-025, BR-EL-030
7 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; no Establishment step | Extension Pending — Final Decision | BR-EL-017–019, BR-EL-025, BR-EL-030
8 | Extension Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Extension Pending — Final Decision | BR-EL-018–019, BR-EL-025, BR-EL-030
9 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Extended Leave in Effect — Incremental Period Posted | BR-EL-025
10 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Original Ongoing Leave Unchanged | BR-EL-025
11 | Awaiting Extension Substitute Response; Extension Applicant Action Required; Awaiting Extension Unit Head Review; Extension Pending — Establishment; Extension Pending — Final Decision | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds while extension request remains pending | Extension Request Withdrawn — Original Leave Unchanged | BR-EL-022
CW-EL-04 — Resumption Review
Type | Composite
Purpose / Scope | Coordinate employee submission of actual resumption information with review by the applicable Sanctioning Authority, distinguishing normal, early, and late return without inventing a generic leave-closure state.
Trigger | Employee returns from EL/COL/VL and submits actual resumption information.
Participants | Employee; applicable Sanctioning Authority
Constituent Workflows | BW-EL-15–17
Related Workflows | CW-EL-02; CW-EL-03
Related CFRs | CFR-EL-021
Related UCs | EL-UC-010, EL-UC-011
Related BRs | BR-EL-027–028
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Returned from EL/COL/VL | Employee | EL-UC-010 / Submit Resumption of Duty | Actual resumption details submitted | Resumption Review Pending | BR-EL-027
2 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date = approved end date | Resumption Reviewed — No Adjustment | BR-EL-027–028
3 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date < approved end date | Resumption Reviewed — Early Return Synchronized | BR-EL-028
4 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date > approved end date | Resumption Reviewed — Late Return Synchronized | BR-EL-028
6. Cross-Cutting Automatic SLA Routing / Responsibility Escalation Pattern
Pattern ID | XTP-EL-01
Applies To | Any SLA-controlled actionable task state in CW-EL-01–04 where the configured escalation changes routing/responsibility.
Trigger | Configured escalation threshold reached.
Performer | System (workflow transition performer; not a UC actor).
Related UC | EL-UC-021 / Process SLA Threshold Event
Related BRs | BR-EL-033, BR-EL-038
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Any SLA-controlled actionable task state that remains pending | System | EL-UC-021 / Process SLA Threshold Event | Escalation threshold reached; task still pending; configured action changes routing/responsibility | Same business process state; actionable task responsibility/routing updated to configured higher/responsible authority | BR-EL-033, BR-EL-038
Artifact | Reason outside Workflow Registry | Retained Representation
EL-UC-006 | Retired. Pending in-place modification is not part of the synchronized baseline. | Retired identifier + BR-EL-034 no-modification rule
EL-UC-012 / EL-UC-013 | Informational inquiry/export capabilities; no connected persistent business-state progression. | Use Cases
EL-UC-014 / EL-UC-015 / EL-UC-017 / EL-UC-018 | Administrative configuration/maintenance interactions; isolated actor-goal functions rather than connected process progression. | Use Cases + applicable BRs
EL-UC-016 | Retrospective synchronization of already-sanctioned offline leave; explicitly not a second approval progression. | Use Case + BR-EL-029
EL-UC-020 | Event-triggered year-end leave-account processing; an isolated timed operation applying year-end BRs, not by itself a connected workflow progression. | Event-triggered Use Case + BR-EL-002–009
EL-UC-021 reminder / notification-only escalation | Event-triggered threshold behavior that does not change process routing/responsibility. | Event-triggered Use Case + BR-EL-032/033/038
BR-EL-035 task-assignment notification | Notification effect attached to actionable task assignment; not a standalone workflow. | Business Rule / UC effect
Previous Workflow | Disposition | Replacement | Rationale
WF-EL-01 Apply and Decide Leave | Reconstructed | CW-EL-01 + BW-EL-01–09 | Uses complete new-leave Basis paths; substitute consent/recovery fragments are embedded within the applicable CL/RH, higher-sanction, and Director paths.
WF-EL-02 Modify or Withdraw Pending Request | Retired / redistributed | Withdrawal in CW-EL-01 and CW-EL-03; no Modify workflow | Pending in-place modification is removed. Withdrawal is represented where it is actually valid.
WF-EL-03 Cancel Approved Leave | Reconstructed | CW-EL-02 + BW-EL-10–11 | Uses complete cancellation paths with terminal approve/reject alternatives; fresh application remains outside cancellation.
WF-EL-04 Extend Ongoing Leave | Reconstructed | CW-EL-03 + BW-EL-12–14 | Uses complete extension paths for no-substitute, accepted-consent, and one decline/replacement traversal variants.
WF-EL-05 Resume Duty and Close Leave | Reconstructed | CW-EL-04 + BW-EL-15–17 | Replaces “closure” and verifier semantics with Sanctioning Authority review and normal/early/late outcomes.
WF-EL-06 Record Offline-Sanctioned Leave | Retired as workflow | EL-UC-016 + BR-EL-029 | Record synchronization, not a second approval progression.
WF-EL-07 Year-End Leave Processing | Retired as workflow | EL-UC-020 + BR-EL-002–009 | Event-triggered isolated system operation; no SF representation type.
WF-EL-08 SLA Reminder / Escalation | Retired as standalone workflow | EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing changes | Reminder/notification-only behavior is UC+BR; routing-changing escalation is cross-cutting System transition only.

```


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(models.Model, TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(models.Model, TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file modules/placement/registry.py
```
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement_cell.application.auto_withdraw",
    "placement_cell.offer.expire",
]

_STUDENT = [
    "placement_cell.registration.self",
    "placement_cell.job_posting.view",
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.application.delete",
    "placement_cell.offer.respond",
]

_COORDINATOR = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.application.review",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
]

_OFFICER = [
    *_COORDINATOR,
    "placement_cell.job_posting.manage",
    "placement_cell.interview.schedule",
    "placement_cell.offer.issue",
    "placement_cell.offer.revoke",
    "placement_cell.company.manage",
    "placement_cell.announcement.publish",
    "placement_cell.registration.manage",
    "placement_cell.registration.debar",
    "placement_cell.record.manage",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
    "placement_cell.announcement.publish",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_coordinator": _COORDINATOR,
    "placement_officer": _OFFICER,
    "placement_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}

```


## Prompt 004 Small contracts file after truncated output

UTC: 2026-10-12T13:39:33.749712+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 1500}`

Generate ONLY modules/leave_elm/contracts.py, using the actual models supplied below. This is the incomplete final file from the previous initial-generation request. Maximum 45 source lines. Expose just TWO public batched getter functions for leave balances and leave application summaries. Each first argument must be user_ids: Sequence[int]. Use actual model/field names. Return plain dictionaries/lists or QuerySets as appropriate. Do not implement any leave workflow, policy validation, model property, can_* method, dataclass, per-field accessor, placeholder, or unrelated helper here. Those belong to the later services stage. Return a compact complete file in the required JSON shape.

Required output paths:
modules/leave_elm/contracts.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(models.Model, TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(models.Model, TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


## Prompt 005 Backend services and selectors

UTC: 2026-10-12T13:41:44.024919+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 6500}`

Continue the same ELM implementation trial. Generate the service layer and selectors against YOUR supplied foundation files, without renaming or redefining their models/fields. Implement the ELM operations described in the supplied specification: applications, balance inquiries, substitutes and response/replacement, approval routing and decisions, withdrawal, cancellation, extensions, resumption, offline-sanctioned entry, record maintenance, notifications, configuration helpers, year-end and SLA processing. Reuse request.principal / actor.user_id and actor.has_permission(code); use the exact leave_elm permission codes in your registry. All user identities are from modules.directory.contracts; only contracts may be imported across module boundaries. Do not import DRF into services. Use core.api.exceptions domain errors, transaction.atomic for writes, and functions with clear parameters that a later API stage can call. Getters/selectors return QuerySets or simple serializable data. Do not create tests or run functional correctness checks. This is initial implementation generation, not a business-rule review or hardening pass. Return complete compact service code, no placeholders, and only the requested files. The services/__init__.py and selectors/__init__.py may be empty. Do not create login/authentication/database connection infrastructure. Do not invent observed results. Keep this initial output compact, with no repeated methods or placeholder functions. Limit the TOTAL batch to about 280 source lines and at most twelve public service functions; use compact action dispatch rather than generating repetitive per-field methods. Leave unrelated getters to contracts.py. Do not include placeholder pass methods. Keep it small enough to finish the output.

Required output paths:
modules/leave_elm/services/__init__.py
modules/leave_elm/services/leave.py
modules/leave_elm/selectors/__init__.py
modules/leave_elm/selectors/leave.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file docs/08-delivery/elm-qwen-trial/specification-context-compact.md
```
# ELM supplied specification context

This is extracted from the supplied specification artifacts. Historical and retired IDs are not active requirements. Workflow v1.6 STTs take precedence over older v1.5 workflow registries.


## Problem statement v1.4
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

## Consolidated requirements v1.5
CFR-EL-001 Role-based ELM access: The system shall restrict ELM capabilities to users authorized for the corresponding employee, processing, sanctioning, or administrative roles.
CFR-EL-002 Create and submit leave application: The system shall allow an eligible employee to create and submit one leave application for CL, RH, SCL, EL, COL, or VL, capturing the leave category, requested period, purpose/reason, and other required information; when Station Leave applies, its details shall be captured within the same application rather than through a separate leave-request process.
CFR-EL-003 Validate a leave request before progression: Before a new leave request is allowed to proceed, the system shall validate the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date shall not be treated as overlapping when they occupy different halves.
CFR-EL-004 Casual Leave (CL) entitlement and treatment: The system shall maintain an annual CL entitlement of 8 days for each employee, support first-half and second-half CL with an approved half day consuming 0.5 CL day, and lapse unused CL at year end without carry-forward.
CFR-EL-005 Restricted Holiday (RH) entitlement and treatment: The system shall maintain an annual RH entitlement of 2 days for each employee, permit an RH request only for an applicable Restricted Holiday in the currently effective published holiday/RH calendar, and lapse unused RH at year end without carry-forward.
CFR-EL-006 Special Casual Leave (SCL) entitlement and treatment: The system shall support up to 15 SCL days per calendar year for each employee for a special purpose considered admissible by the applicable sanctioning authority, and shall lapse unused SCL at year end without carry-forward.
CFR-EL-007 Earned Leave (EL) entitlement and carry-forward: The system shall credit each non-faculty employee with 30 EL days per year and carry forward unused EL according to policy.
CFR-EL-008 Faculty Vacation Leave (VL) and VL-to-EL conversion: The system shall maintain 60 VL for each faculty member for vacation periods supplied through the institute Academic Calendar, permit VL only during an applicable vacation period, and at year end convert all unused VL to EL at 2 VL : 1 EL including fractional conversion; VL itself shall not carry forward, while the converted EL shall be credited to the faculty member’s EL balance, may carry forward, and may subsequently be used.
CFR-EL-009 Commuted Leave (COL) entitlement and treatment: The system shall maintain an annual COL entitlement of 20 days for each eligible employee in this baseline, treat COL as medical/balance-controlled leave, require supporting medical evidence where applicable, and carry forward unused COL according to policy.
CFR-EL-010 Continuous-day counting: For EL, COL, and VL, the system shall count intervening weekends and closed holidays within a continuous approved leave interval as leave days; this continuous-day rule shall not apply to CL, SCL, or RH.
CFR-EL-011 Nominate an eligible substitute: When responsibility coverage is required, the system shall allow the applicant to nominate one substitute who is another employee, is not the applicant, and has no overlapping pending or approved leave during the responsibility period.
CFR-EL-012 Obtain substitute response and enforce consent gate: The system shall allow the nominated substitute to accept or decline the responsibility assignment; approval routing shall not proceed until required substitute consent is accepted, and after a decline the applicant shall be allowed to nominate another eligible substitute or withdraw the pending request.
CFR-EL-013 CL/RH Unit Head final decision: For CL and RH, including associated Station Leave, the system shall route the submitted request to the applicant’s Unit Head and allow the Unit Head to make the final approve/reject decision, except where the Director-specific self-sanction rule applies.
CFR-EL-014 Higher-sanction leave progression to final decision: For SCL, EL, COL, and VL, the system shall route the request to the Unit Head for review and recording of Recommended or Not Recommended, shall not treat Not Recommended as a final rejection, and shall then route the request through the configured hierarchy to the resolved final Sanctioning Authority for an approve/reject decision. The route shall be resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration, and may include an Establishment processing step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director where configured.
CFR-EL-015 Director self-sanction: When the Director is the applicant, the system shall apply the Director-specific self-sanction path instead of the normal Unit Head/higher-authority routing path.
CFR-EL-016 Record and communicate the final leave decision: On a final leave decision, the system shall record the decision and notify the employee. When the decision is approval, the system shall also update the employee’s leave record/account. Intermediate processing decisions and state changes need not generate general notifications but shall be available to the employee through status/history inquiry.
CFR-EL-017 No post-submission modification of a pending request: The system shall not permit a submitted pending leave request to be modified in place. A pending request that requires change may instead be withdrawn before final approval, after which a new leave application may be submitted if needed.
CFR-EL-018 Immediate withdrawal of a pending request: The system shall allow an employee to withdraw a pending leave application at any time before final approval and, upon successful withdrawal, shall make the withdrawal effective immediately, terminate all remaining approval processing for that application, prevent any later approve/reject action, and notify the concerned roles of the withdrawal. After final approval, withdrawal shall no longer be available and the approved-leave cancellation process shall apply where relevant.
CFR-EL-019 Cancel approved leave before start: The system shall allow an employee to request cancellation of an approved leave before its start date, process the cancellation through the same applicable approval hierarchy to a final decision, and shall not edit the approved leave in place. If cancellation is approved, the system shall mark the leave Cancelled and restore or adjust any leave balance already deducted for that approval; if cancellation is rejected, the original approved leave shall remain unchanged. If revised leave is still needed after cancellation, a fresh application shall be submitted. Once the leave has begun, the pre-start cancellation path shall no longer apply.
CFR-EL-020 Extend ongoing EL/COL/VL: The system shall allow an employee on ongoing EL, COL, or VL to request additional leave time, validate the extension against applicable eligibility, balance, substitute, calendar, and approval conditions, obtain required substitute consent before routing, and process the extension through the applicable Unit Head and configured higher-sanction path. If approved, only the incremental additional leave period shall be posted while preserving the original approved leave as the base; if rejected, the original approved leave shall remain unchanged.
CFR-EL-021 Review resumption and adjust actual leave where required: The system shall allow an employee returning from EL, COL, or VL to submit the actual resumption date and required details for review by the applicable Sanctioning Authority. When the employee resumes on the approved end date, the authority shall review the resumption without changing the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, the system shall, after the resumption review, record the actual leave period, adjust the leave balance accordingly, and synchronize the relevant leave/attendance records.
CFR-EL-022 View leave balances and history: The system shall allow an employee to view current leave balances and leave-account/request history, including the current status and recorded final decisions of the employee’s leave requests.
CFR-EL-023 Obtain printable/exportable leave application: The system shall allow an employee to obtain a printable/exportable representation of a leave application accessible to that employee.
CFR-EL-024 Maintain policy parameters and hierarchy configuration: The system shall allow authorized administrative roles to create and revise leave-policy parameters and maintain the hierarchy configuration used for validation and routing; ELM shall use the current configured policy and hierarchy values. No draft/publish/effective-version lifecycle is required for leave-policy parameters in this baseline.
CFR-EL-025 Maintain and publish the holiday/RH calendar: The system shall allow authorized administrative roles to create, revise, and publish the holiday/RH calendar, and date/RH validation shall use the currently effective published holiday/RH calendar until a replacement is published.
CFR-EL-026 Maintain authorized leave records: The system shall allow authorized administrative roles to maintain or correct leave records where their role permits such record maintenance, while preserving the distinction between administrative record maintenance and leave sanctioning.
CFR-EL-027 Record already-sanctioned offline leave: The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized paper/offline process when ELM could not be used, shall capture the sanction/reference evidence, validate the entry for record consistency, and update the relevant leave balance/history. This operation is record synchronization and shall not initiate a second approval workflow.
CFR-EL-028 Execute and record year-end leave-account processing: At year end, the system shall execute the applicable leave-account outcomes defined by policy: lapse unused CL, RH, and SCL; perform the faculty VL-to-EL conversion; carry forward EL and COL; record the resulting leave-account transactions; and report processing exceptions.
CFR-EL-029 Configure workflow-task SLA thresholds: The system shall support configurable reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
CFR-EL-030 Notify a user when an actionable task is assigned: When an actionable workflow task is assigned to a user, the system shall notify the assigned user of that task.
CFR-EL-031 Remind on a still-pending SLA task: When an SLA-controlled actionable task reaches its configured reminder threshold and is still pending, the system shall remind the responsible user and log the reminder action; if the task is no longer pending at the threshold, the corresponding reminder shall not be issued.
CFR-EL-032 Escalate a still-pending SLA task: When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action to the configured higher/responsible authority and log the action; if the task is no longer pending at the threshold, the corresponding escalation shall not be issued.



## 04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx
BR-EL-001 — Supported leave-category eligibility
A new leave request shall use only CL, RH, SCL, EL, COL, or VL and shall satisfy the category-applicability conditions in the current configured ELM policy.
BR-EL-002 — Casual Leave entitlement and lapse
Each employee has 8 CL days per year; unused CL lapses at year end and does not carry forward.
BR-EL-003 — Restricted Holiday entitlement and applicability
Each employee has 2 RH days per year; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH lapses at year end.
BR-EL-004 — Special Casual Leave entitlement and admissibility
Each employee may use up to 15 SCL days per calendar year for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility criterion is required; unused SCL lapses at year end.
BR-EL-005 — Non-faculty Earned Leave credit and carry-forward
Each non-faculty employee shall receive 30 EL days per year and unused EL shall carry forward according to policy.
BR-EL-006 — Faculty Vacation Leave entitlement and vacation-period applicability
Each faculty member shall have 60 VL associated with vacation periods supplied by the institute Academic Calendar, and VL may be availed only during an applicable vacation period.
BR-EL-007 — VL-to-EL year-end conversion
At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward.
BR-EL-008 — Treatment of EL created by VL conversion
EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed.
BR-EL-009 — Commuted Leave entitlement and treatment
Eligible employees have 20 COL days/year in this baseline; COL is medical/balance-controlled, supporting medical evidence may be required where applicable, and unused COL carries forward.
BR-EL-010 — Half-day CL treatment
CL shall support first-half and second-half requests; an approved half day consumes 0.5 CL day.
BR-EL-011 — Continuous-day counting
For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days; this rule does not apply to CL, SCL, or RH.
BR-EL-012 — Applicant non-overlap with half-day CL exception
A new request shall not impermissibly overlap the employee's active pending or approved leave; first-half and second-half CL on the same date are non-overlapping when they occupy different halves.
BR-EL-013 — Station Leave coupling
Station Leave permission/details, when applicable, shall be captured within the same leave application and shall not create a separate leave-request process.
BR-EL-014 — Substitute eligibility
When responsibility coverage is required, exactly one substitute is nominated; the substitute must be another employee, must not be the applicant, and must have no overlapping pending or approved leave during the responsibility period.
BR-EL-015 — Substitute consent gate and decline recovery
Required approval routing shall not proceed until the nominated substitute accepts. A decline leaves the consent gate closed; the applicant may nominate another eligible substitute or withdraw the pending request where applicable.
BR-EL-016 — Unit Head final scope for CL/RH
For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority except for the Director-specific self-sanction case.
BR-EL-017 — Unit Head recommendation for higher-sanction leave
For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended; Not Recommended is not a final rejection and both outcomes continue through the applicable higher-sanction path.
BR-EL-018 — Higher-sanction routing
SCL, EL, COL, and VL requests requiring higher sanction shall proceed through the current configured hierarchy to the resolved final Sanctioning Authority.
BR-EL-019 — Authority resolution and optional Establishment step
The processing/sanctioning path shall be resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration; an Establishment step and the roles Deputy Registrar (Estt.), Dean, Registrar, and Director occur only where configured.
BR-EL-020 — Director self-sanction
When the Director is the applicant, the Director-specific self-sanction path replaces the normal Unit Head/higher-authority route.
BR-EL-021 — RETIRED — Modify Pending Request
The former rule permitting pending-request modification is retired. Post-submission modification is not part of the synchronized baseline.
BR-EL-022 — Immediate withdrawal of pending request
A pending request may be withdrawn at any time before final approval; withdrawal is immediate, terminates remaining approval processing, blocks later approve/reject actions, and informs concerned roles. After final approval, withdrawal is unavailable.
BR-EL-023 — Cancellation of approved leave before start
An approved leave may be cancelled only before its start date; cancellation uses the same applicable hierarchy, does not edit the approved leave in place, approval marks the leave Cancelled and restores/adjusts already deducted balance, while rejection leaves the original approval unchanged.
BR-EL-024 — Fresh application after cancellation
If revised leave is still required after cancellation, a fresh leave application shall be submitted rather than editing the approved leave in place.
BR-EL-025 — Extension of ongoing EL/COL/VL
Extension is available only for ongoing EL/COL/VL; it uses applicable eligibility, balance, substitute, calendar and sanction rules; approval posts only the incremental additional period while rejection preserves the original approved leave.
BR-EL-026 — RETIRED IDENTIFIER
No active rule is assigned to this identifier.
BR-EL-027 — Resumption applicability and review authority
Formal resumption review applies to EL, COL, and VL; the employee submits actual resumption information and the applicable Sanctioning Authority reviews it.
BR-EL-028 — Normal, early, and late resumption outcome
If actual resumption equals the approved end date, review causes no adjustment to approved leave period or balance. If actual resumption is earlier or later, after review ELM records the actual leave period, adjusts leave balance accordingly, and synchronizes relevant leave/attendance records.
BR-EL-029 — Offline-sanctioned leave synchronization
Only leave already sanctioned through an authorized offline/paper process may be retrospectively recorded; sanction/reference evidence shall be captured, record consistency validated, relevant balance/history synchronized, and no second approval workflow initiated.
BR-EL-030 — Current configured policy and hierarchy
ELM validation and routing shall use the current configured leave-policy parameters and hierarchy configuration. No draft/publish/effective-version lifecycle applies to leave-policy parameters in this baseline.
BR-EL-031 — Effective published holiday/RH calendar
Date and RH validation shall use the currently effective published holiday/RH calendar until a replacement calendar is published.
BR-EL-032 — SLA reminder on still-pending task
When an SLA-controlled actionable task reaches its configured reminder threshold, issue a reminder to the responsible user and log it only if the task is still pending; otherwise issue no reminder.
BR-EL-033 — SLA escalation on still-pending task
When an SLA-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action: notify the configured higher/responsible authority and, where the escalation configuration changes routing/responsibility, apply that routing/responsibility change; the escalation action shall be logged. If the task is no longer pending, no escalation shall be issued.
BR-EL-034 — No post-submission modification
A submitted pending leave request shall not be modified in place. If change is needed before final approval, the employee may withdraw and submit a new application if needed.
BR-EL-035 — Actionable task assignment notification
When an actionable workflow task is assigned to a user, ELM shall notify the assigned user.
BR-EL-036 — Role-based authorization
ELM capabilities shall be available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role.
BR-EL-037 — Administrative maintenance is not sanctioning
Authorized leave-record maintenance/correction shall not itself create a new sanctioning decision; retrospective offline entry is also synchronization rather than a second approval.
BR-EL-038 — Configurable SLA thresholds
Reminder and escalation thresholds for SLA-controlled actionable workflow tasks shall be configurable by an authorized administrative role and shall govern EL-UC-021 event-triggered SLA processing.

## 03_ELM_Use_Case_Specifications_v1.4_FINAL.docx
EL-UC-001 — Apply for Leave
Create and submit a valid new leave application and place it into the applicable processing path.
EL-UC-002 — Respond to Substitute Request
Accept or decline a nominated responsibility assignment.
EL-UC-003 — Review Leave-Related Request at Unit Head
Review a routed new-leave, cancellation, or extension request and record the decision/recommendation permitted by the applicable policy.
EL-UC-004 — Verify and Route Higher-Sanction Request
Perform the configured Establishment-level verification/routing step and forward the request to the resolved competent authority.
EL-UC-005 — Make Final Sanctioning Decision
Record the final approve/reject decision for a routed higher-sanction new-leave, cancellation, or extension request.
EL-UC-007 — Withdraw Pending Request
Immediately terminate a pending request before final approval.
EL-UC-008 — Request Cancellation of Approved Leave
Request pre-start cancellation of an approved leave without editing the approved leave in place.
EL-UC-009 — Request Extension of Ongoing Leave
Request additional leave time while ongoing EL, COL, or VL is being availed.
EL-UC-010 — Submit Resumption of Duty
Submit actual return-to-duty information after EL, COL, or VL for review.
EL-UC-011 — Review Resumption
Review the submitted resumption and apply only the adjustments required by the actual return date.
EL-UC-012 — View Leave Balances and History
Inspect own current leave balances and leave-account/request history, including request status and final decisions.
EL-UC-013 — Obtain Printable/Exportable Leave Application
Obtain a printable or exportable representation of an accessible leave application.
EL-UC-014 — Maintain Policy and Hierarchy Configuration
Create/revise current ELM leave-policy parameters and maintain hierarchy configuration used for validation and routing.
EL-UC-015 — Maintain and Publish Holiday/RH Calendar
Create, revise, and publish the holiday/RH calendar used by date and RH validation.
EL-UC-016 — Record Already-Sanctioned Offline Leave
Synchronize ELM with leave already sanctioned through an authorized offline/paper process when ELM could not originally be used.
EL-UC-017 — Maintain Authorized Leave Records
Maintain or correct leave records within the actor's authorized record-maintenance scope without creating a sanctioning decision.
EL-UC-018 — Configure Workflow SLA Thresholds
Configure reminder and escalation thresholds for SLA-controlled actionable workflow tasks.
EL-UC-019 — Nominate Replacement Substitute After Decline
Recover from a substitute decline by nominating one replacement eligible substitute.
EL-UC-020 — Execute Year-End Leave Processing
Apply the defined year-end leave-account outcomes and record the resulting processing evidence.
EL-UC-021 — Process SLA Threshold Event
Process a configured SLA reminder or escalation threshold for an actionable workflow task.

## 06_ELM_Workflow_Specifications_v1.6_FINAL.docx
CW-EL-01 — New Leave Processing and Pending Withdrawal
Type | Composite
Purpose / Scope | Provide the end-to-end progression for a new leave request, including substitute consent/recovery, Unit-Head-final CL/RH decisions, higher-sanction routing, the Director-specific self-sanction route, and immediate withdrawal from every valid pending pre-final state.
Trigger | Employee submits a valid new leave request.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority; Director in self-sanction case
Constituent Workflows | BW-EL-01–09
Related Workflows | CW-EL-02; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-002–003, CFR-EL-011–018
Related UCs | EL-UC-001–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001–020, BR-EL-022, BR-EL-030–035
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; substitute required | Awaiting Substitute Response | BR-EL-001–015, BR-EL-030–031
2 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is Director | Awaiting Director Self-Sanction | BR-EL-001–013, BR-EL-020, BR-EL-030–031
3 | Draft / Not Submitted | Employee | EL-UC-001 / Apply for Leave | Submission valid; no substitute required; applicant is not Director | Awaiting Unit Head Review | BR-EL-001–013, BR-EL-030–031
4 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is Director | Awaiting Director Self-Sanction | BR-EL-014–015, BR-EL-020
5 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept; applicant is not Director | Awaiting Unit Head Review | BR-EL-014–015
6 | Awaiting Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Applicant Action Required | BR-EL-014–015
7 | Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Substitute Response | BR-EL-014–015
8 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Approve | Approved | BR-EL-016
9 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | CL/RH; outcome = Reject | Rejected | BR-EL-016
10 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; Establishment configured | Awaiting Establishment Routing | BR-EL-017–019, BR-EL-030
11 | Awaiting Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction; Recommended or Not Recommended; no Establishment step | Awaiting Final Sanction Decision | BR-EL-017–019, BR-EL-030
12 | Awaiting Establishment Routing | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Awaiting Final Sanction Decision | BR-EL-018–019, BR-EL-030
13 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-004, BR-EL-017–019
14 | Awaiting Final Sanction Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-004, BR-EL-017–019
15 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Approved | BR-EL-020
16 | Awaiting Director Self-Sanction | Director (Sanctioning Authority role) | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Rejected | BR-EL-020
17 | Awaiting Substitute Response; Applicant Action Required; Awaiting Unit Head Review; Awaiting Establishment Routing; Awaiting Final Sanction Decision; Awaiting Director Self-Sanction | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds before final approval | Withdrawn | BR-EL-022, BR-EL-034
CW-EL-02 — Approved Leave Cancellation
Type | Composite
Purpose / Scope | Represent cancellation of approved leave before its start through the same applicable decision hierarchy, with distinct cancellation-approved and cancellation-rejected effects. A later revised leave request is a fresh New Leave instance, not part of this workflow.
Trigger | Employee requests cancellation of an approved leave before its start date.
Participants | Employee; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-10–11
Related Workflows | CW-EL-01; CW-EL-03; CW-EL-04
Related CFRs | CFR-EL-019
Related UCs | EL-UC-008, EL-UC-003–005
Related BRs | BR-EL-016–019, BR-EL-023–024, BR-EL-030
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Approved / Not Started | Employee | EL-UC-008 / Request Cancellation of Approved Leave | Cancellation eligible | Cancellation Pending — Unit Head Review | BR-EL-023
2 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-016, BR-EL-023
3 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Original leave Unit-Head-final; outcome = Reject cancellation | Approved / Unchanged | BR-EL-016, BR-EL-023
4 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; Establishment configured | Cancellation Pending — Establishment | BR-EL-017–019, BR-EL-023, BR-EL-030
5 | Cancellation Pending — Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Higher-sanction cancellation; recommendation recorded; no Establishment step | Cancellation Pending — Final Decision | BR-EL-017–019, BR-EL-023, BR-EL-030
6 | Cancellation Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Cancellation Pending — Final Decision | BR-EL-018–019, BR-EL-023, BR-EL-030
7 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve cancellation | Cancelled; deducted balance restored/adjusted | BR-EL-023
8 | Cancellation Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject cancellation | Approved / Unchanged | BR-EL-023
CW-EL-03 — Ongoing Leave Extension
Type | Composite
Purpose / Scope | Represent an extension of ongoing EL/COL/VL through applicable validation, substitute consent/recovery where required, Unit Head recommendation, configured higher-sanction decision, and immediate withdrawal of the pending extension request where applicable.
Trigger | Employee on ongoing EL/COL/VL requests additional leave time.
Participants | Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final Sanctioning Authority
Constituent Workflows | BW-EL-12–14
Related Workflows | CW-EL-01; CW-EL-02; CW-EL-04
Related CFRs | CFR-EL-020, CFR-EL-018 where pending-extension withdrawal applies
Related UCs | EL-UC-009, EL-UC-002–005, EL-UC-007, EL-UC-019
Related BRs | BR-EL-001, BR-EL-005–019, BR-EL-022, BR-EL-025, BR-EL-030–031
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; substitute required | Awaiting Extension Substitute Response | BR-EL-001, BR-EL-005–015, BR-EL-025, BR-EL-030–031
2 | Ongoing EL/COL/VL | Employee | EL-UC-009 / Request Extension of Ongoing Leave | Valid extension; no substitute required | Awaiting Extension Unit Head Review | BR-EL-001, BR-EL-005–013, BR-EL-025, BR-EL-030–031
3 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Accept | Awaiting Extension Unit Head Review | BR-EL-014–015, BR-EL-025
4 | Awaiting Extension Substitute Response | Substitute / Responsibility Holder | EL-UC-002 / Respond to Substitute Request | Outcome = Decline | Extension Applicant Action Required | BR-EL-014–015, BR-EL-025
5 | Extension Applicant Action Required | Employee | EL-UC-019 / Nominate Replacement Substitute After Decline | Eligible replacement nominated | Awaiting Extension Substitute Response | BR-EL-014–015
6 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; Establishment configured | Extension Pending — Establishment | BR-EL-017–019, BR-EL-025, BR-EL-030
7 | Awaiting Extension Unit Head Review | Unit Head | EL-UC-003 / Review Leave-Related Request at Unit Head | Recommendation recorded; no Establishment step | Extension Pending — Final Decision | BR-EL-017–019, BR-EL-025, BR-EL-030
8 | Extension Pending — Establishment | Establishment | EL-UC-004 / Verify and Route Higher-Sanction Request | Routing context valid | Extension Pending — Final Decision | BR-EL-018–019, BR-EL-025, BR-EL-030
9 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Approve | Extended Leave in Effect — Incremental Period Posted | BR-EL-025
10 | Extension Pending — Final Decision | Sanctioning Authority | EL-UC-005 / Make Final Sanctioning Decision | Outcome = Reject | Original Ongoing Leave Unchanged | BR-EL-025
11 | Awaiting Extension Substitute Response; Extension Applicant Action Required; Awaiting Extension Unit Head Review; Extension Pending — Establishment; Extension Pending — Final Decision | Employee | EL-UC-007 / Withdraw Pending Request | Withdrawal succeeds while extension request remains pending | Extension Request Withdrawn — Original Leave Unchanged | BR-EL-022
CW-EL-04 — Resumption Review
Type | Composite
Purpose / Scope | Coordinate employee submission of actual resumption information with review by the applicable Sanctioning Authority, distinguishing normal, early, and late return without inventing a generic leave-closure state.
Trigger | Employee returns from EL/COL/VL and submits actual resumption information.
Participants | Employee; applicable Sanctioning Authority
Constituent Workflows | BW-EL-15–17
Related Workflows | CW-EL-02; CW-EL-03
Related CFRs | CFR-EL-021
Related UCs | EL-UC-010, EL-UC-011
Related BRs | BR-EL-027–028
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Returned from EL/COL/VL | Employee | EL-UC-010 / Submit Resumption of Duty | Actual resumption details submitted | Resumption Review Pending | BR-EL-027
2 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date = approved end date | Resumption Reviewed — No Adjustment | BR-EL-027–028
3 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date < approved end date | Resumption Reviewed — Early Return Synchronized | BR-EL-028
4 | Resumption Review Pending | Applicable Sanctioning Authority | EL-UC-011 / Review Resumption | Actual date > approved end date | Resumption Reviewed — Late Return Synchronized | BR-EL-028
6. Cross-Cutting Automatic SLA Routing / Responsibility Escalation Pattern
Pattern ID | XTP-EL-01
Applies To | Any SLA-controlled actionable task state in CW-EL-01–04 where the configured escalation changes routing/responsibility.
Trigger | Configured escalation threshold reached.
Performer | System (workflow transition performer; not a UC actor).
Related UC | EL-UC-021 / Process SLA Threshold Event
Related BRs | BR-EL-033, BR-EL-038
S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s)
1 | Any SLA-controlled actionable task state that remains pending | System | EL-UC-021 / Process SLA Threshold Event | Escalation threshold reached; task still pending; configured action changes routing/responsibility | Same business process state; actionable task responsibility/routing updated to configured higher/responsible authority | BR-EL-033, BR-EL-038
Artifact | Reason outside Workflow Registry | Retained Representation
EL-UC-006 | Retired. Pending in-place modification is not part of the synchronized baseline. | Retired identifier + BR-EL-034 no-modification rule
EL-UC-012 / EL-UC-013 | Informational inquiry/export capabilities; no connected persistent business-state progression. | Use Cases
EL-UC-014 / EL-UC-015 / EL-UC-017 / EL-UC-018 | Administrative configuration/maintenance interactions; isolated actor-goal functions rather than connected process progression. | Use Cases + applicable BRs
EL-UC-016 | Retrospective synchronization of already-sanctioned offline leave; explicitly not a second approval progression. | Use Case + BR-EL-029
EL-UC-020 | Event-triggered year-end leave-account processing; an isolated timed operation applying year-end BRs, not by itself a connected workflow progression. | Event-triggered Use Case + BR-EL-002–009
EL-UC-021 reminder / notification-only escalation | Event-triggered threshold behavior that does not change process routing/responsibility. | Event-triggered Use Case + BR-EL-032/033/038
BR-EL-035 task-assignment notification | Notification effect attached to actionable task assignment; not a standalone workflow. | Business Rule / UC effect
Previous Workflow | Disposition | Replacement | Rationale
WF-EL-01 Apply and Decide Leave | Reconstructed | CW-EL-01 + BW-EL-01–09 | Uses complete new-leave Basis paths; substitute consent/recovery fragments are embedded within the applicable CL/RH, higher-sanction, and Director paths.
WF-EL-02 Modify or Withdraw Pending Request | Retired / redistributed | Withdrawal in CW-EL-01 and CW-EL-03; no Modify workflow | Pending in-place modification is removed. Withdrawal is represented where it is actually valid.
WF-EL-03 Cancel Approved Leave | Reconstructed | CW-EL-02 + BW-EL-10–11 | Uses complete cancellation paths with terminal approve/reject alternatives; fresh application remains outside cancellation.
WF-EL-04 Extend Ongoing Leave | Reconstructed | CW-EL-03 + BW-EL-12–14 | Uses complete extension paths for no-substitute, accepted-consent, and one decline/replacement traversal variants.
WF-EL-05 Resume Duty and Close Leave | Reconstructed | CW-EL-04 + BW-EL-15–17 | Replaces “closure” and verifier semantics with Sanctioning Authority review and normal/early/late outcomes.
WF-EL-06 Record Offline-Sanctioned Leave | Retired as workflow | EL-UC-016 + BR-EL-029 | Record synchronization, not a second approval progression.
WF-EL-07 Year-End Leave Processing | Retired as workflow | EL-UC-020 + BR-EL-002–009 | Event-triggered isolated system operation; no SF representation type.
WF-EL-08 SLA Reminder / Escalation | Retired as standalone workflow | EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing changes | Reminder/notification-only behavior is UC+BR; routing-changing escalation is cross-cutting System transition only.

```


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/domain/policy.py
```
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(models.Model, TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(models.Model, TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name

```


### Repository file modules/leave_elm/registry.py
```
from django.urls import path
from . import views

urlpatterns = [
    path('mine/', views.LeaveMineView.as_view(), name='leave_mine'),
    path('queue/', views.LeaveQueueView.as_view(), name='leave_queue'),
    path('admin/', views.LeaveAdminView.as_view(), name='leave_admin'),
]

```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file modules/directory/contracts.py
```
"""directory's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef
from modules.directory.services.sync import ensure_users_cached


@dataclass(frozen=True)
class UserDTO:
    user_id: int
    username: str
    display_name: str
    kind: str
    email: str = ""
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None
    #: Maintained on the ERP portal's profile page, read here.
    resume_link: str = ""
    profile_completed: bool = False


def _to_dto(r: UserRef) -> UserDTO:
    return UserDTO(
        user_id=r.user_id, username=r.username, display_name=r.display_name,
        kind=r.kind, email=r.email, department=r.department,
        programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
        resume_link=r.resume_link, profile_completed=r.profile_completed,
    )


def get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]:
    """Batched. A missing id is simply absent from the mapping — a visible,
    testable case rather than a silent None three layers up."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    ensure_users_cached(ids)
    return {r.user_id: _to_dto(r) for r in UserRef.objects.filter(user_id__in=ids)}


def user_ids_in_discipline(discipline: str) -> list[int]:
    return list(
        UserRef.objects.filter(discipline=discipline, kind="student", is_active=True)
        .values_list("user_id", flat=True)
    )


def get_employees() -> list[UserDTO]:
    """Everyone on the payroll: faculty and staff, not students."""
    return [
        _to_dto(r)
        for r in UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).order_by("user_id")
    ]


def held_employee_ids() -> set[int]:
    return set(
        UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).values_list("user_id", flat=True)
    )


def employee_projection_disagreement() -> tuple[list[int], list[int]] | None:
    """Where this service and the identity service disagree about the payroll."""
    held = held_employee_ids()
    try:
        known = {r.user_id for r in get_client().iter_employees()}
    except IamUnavailable:
        return None
    return sorted(known - held), sorted(held - known)


def search(q: str = "", kind: str | None = None, limit: int = 25) -> list[UserDTO]:
    qs = UserRef.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(display_name__icontains=q)
    return [_to_dto(r) for r in qs.order_by("display_name")[:limit]]

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


## Prompt 006 Correct Fusion registry interface

UTC: 2026-10-12T13:49:25.135580+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 3000}`

Mechanical integration correction only. The previous registry.py incorrectly contains Django urlpatterns and imports a nonexistent .views module. Replace it with the REQUIRED Fusion registry interface shown in modules/placement/registry.py: MODULE plain dictionary, NAV_ITEMS list of dictionaries, PERMISSIONS list of (code,label), ROLE_GRANTS dict of designation strings to permission strings, SYSTEM_PERMISSIONS list. This file must not import views, django.urls, Django, or services. MODULE code leave_elm, label Employee Leave Management, base_path /leave, nav_section Employee, icon CalendarBlank, status active, sort_order 30. Exactly three NAV_ITEMS to /leave/mine, /leave/queue, /leave/admin, each with its own matching permission. Use leave_elm prefixed permission codes, and include application.view_self, application.create, application.review, application.approve, substitute.respond, task.view, configuration.manage and record.manage under the leave_elm prefix. Declare employee role grants for faculty/staff/Employee, reviewer/authority grants for Unit Head/Deputy Registrar (Estt.)/Dean/Registrar/Director and admin grants for Leave Administrator, as named by the original problem statement. Every declared permission must have a holder. No URLs or view classes belong in registry.py. Do not modify any other file or business logic. Maximum 100 lines.

Required output paths:
modules/leave_elm/registry.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file modules/placement/registry.py
```
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement_cell.application.auto_withdraw",
    "placement_cell.offer.expire",
]

_STUDENT = [
    "placement_cell.registration.self",
    "placement_cell.job_posting.view",
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.application.delete",
    "placement_cell.offer.respond",
]

_COORDINATOR = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.application.review",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
]

_OFFICER = [
    *_COORDINATOR,
    "placement_cell.job_posting.manage",
    "placement_cell.interview.schedule",
    "placement_cell.offer.issue",
    "placement_cell.offer.revoke",
    "placement_cell.company.manage",
    "placement_cell.announcement.publish",
    "placement_cell.registration.manage",
    "placement_cell.registration.debar",
    "placement_cell.record.manage",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
    "placement_cell.announcement.publish",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_coordinator": _COORDINATOR,
    "placement_officer": _OFFICER,
    "placement_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}

```


### Repository file docs/08-delivery/elm-qwen-trial/problem-statement-context.md
```
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

```


### Repository file modules/leave_elm/registry.py
```
from django.urls import path
from . import views

urlpatterns = [
    path('mine/', views.LeaveMineView.as_view(), name='leave_mine'),
    path('queue/', views.LeaveQueueView.as_view(), name='leave_queue'),
    path('admin/', views.LeaveAdminView.as_view(), name='leave_admin'),
]

```


## Prompt 007 Focused initial leave service

UTC: 2026-10-12T13:50:57.250323+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 3500}`

INITIAL GENERATION of a compact ELM service file; the earlier broad service response was incomplete and was never applied. Produce ONLY modules/leave_elm/services/leave.py, maximum about 140 lines, with exactly five MODULE-LEVEL public functions (not a class): submit_application(actor,data), list_applications(actor), own_balances(actor), decide_application(actor,application_id,action,comment=""), withdraw_application(actor,application_id). Use YOUR actual models and domain helpers supplied below, with actual field names and Fusion Principal.user_id / .has_permission. Initial request and decision behavior should follow the supplied problem statement. Use existing leave_elm permission codes from registry.py. Reuse Django ORM/configuration and core.api.exceptions, without DRF in services. Keep all operations compact. Do not add getters for every field, repeated process_* functions, can_* methods, dataclasses, dummy pass functions or unrelated workflows to this file. Later small files will hold follow-up requests/admin/year-end/SLA. Do not change model fields or existing helper logic. Return one complete file and stop.

Required output paths:
modules/leave_elm/services/leave.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence.


### Repository file docs/08-delivery/elm-qwen-trial/problem-statement-context.md
```
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

```


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/domain/policy.py
```
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(models.Model, TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(models.Model, TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name

```


### Repository file modules/leave_elm/registry.py
```
from django.urls import path
from . import views

urlpatterns = [
    path('mine/', views.LeaveMineView.as_view(), name='leave_mine'),
    path('queue/', views.LeaveQueueView.as_view(), name='leave_queue'),
    path('admin/', views.LeaveAdminView.as_view(), name='leave_admin'),
]
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


## Prompt 008 Retry registry with current task after references

UTC: 2026-10-12T13:54:54.492969+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 2500}`

REFERENCE MATERIAL ONLY


### Repository file modules/placement/registry.py
```
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement_cell.application.auto_withdraw",
    "placement_cell.offer.expire",
]

_STUDENT = [
    "placement_cell.registration.self",
    "placement_cell.job_posting.view",
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.application.delete",
    "placement_cell.offer.respond",
]

_COORDINATOR = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.application.review",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
]

_OFFICER = [
    *_COORDINATOR,
    "placement_cell.job_posting.manage",
    "placement_cell.interview.schedule",
    "placement_cell.offer.issue",
    "placement_cell.offer.revoke",
    "placement_cell.company.manage",
    "placement_cell.announcement.publish",
    "placement_cell.registration.manage",
    "placement_cell.registration.debar",
    "placement_cell.record.manage",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
    "placement_cell.announcement.publish",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_coordinator": _COORDINATOR,
    "placement_officer": _OFFICER,
    "placement_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}

```


### Repository file docs/08-delivery/elm-qwen-trial/problem-statement-context.md
```
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

```


END OF REFERENCES

CURRENT TASK

Mechanical integration correction only. The previous registry.py incorrectly contains Django urlpatterns and imports a nonexistent .views module. Replace it with the REQUIRED Fusion registry interface shown in modules/placement/registry.py: MODULE plain dictionary, NAV_ITEMS list of dictionaries, PERMISSIONS list of (code,label), ROLE_GRANTS dict of designation strings to permission strings, SYSTEM_PERMISSIONS list. This file must not import views, django.urls, Django, or services. MODULE code leave_elm, label Employee Leave Management, base_path /leave, nav_section Employee, icon CalendarBlank, status active, sort_order 30. Exactly three NAV_ITEMS to /leave/mine, /leave/queue, /leave/admin, each with its own matching permission. Use leave_elm prefixed permission codes, and include application.view_self, application.create, application.review, application.approve, substitute.respond, task.view, configuration.manage and record.manage under the leave_elm prefix. Declare employee role grants for faculty/staff/Employee, reviewer/authority grants for Unit Head/Deputy Registrar (Estt.)/Dean/Registrar/Director and admin grants for Leave Administrator, as named by the original problem statement. Every declared permission must have a holder. No URLs or view classes belong in registry.py. Do not modify any other file or business logic. Maximum 100 lines. Your output must begin with a MODULE dictionary and contain NAV_ITEMS, PERMISSIONS, ROLE_GRANTS, SYSTEM_PERMISSIONS assignments. It must NOT contain urlpatterns, path(), imports of views, or any view class. Those are a different interface. Generate the requested registry definitions now.

Required output paths:
modules/leave_elm/registry.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 009 Focused initial leave service with current task last

UTC: 2026-10-12T13:56:28.938302+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 3500}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen-trial/problem-statement-context.md
```
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

```


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/registry.py
```
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "reviewer": ["leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.review", "leave_elm.application.approve", "leave_elm.substitute.respond"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}

SYSTEM_PERMISSIONS = [
    "leave_elm.application.approve",
    "leave_elm.application.review",
    "leave_elm.application.create",
    "leave_elm.application.view_self",
    "leave_elm.substitute.respond",
    "leave_elm.task.view",
    "leave_elm.configuration.manage",
    "leave_elm.record.manage",
]

```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

INITIAL GENERATION of a compact ELM service file; the earlier broad service response was incomplete and was never applied. Produce ONLY modules/leave_elm/services/leave.py, maximum about 140 lines, with exactly five MODULE-LEVEL public functions (not a class): submit_application(actor,data), list_applications(actor), own_balances(actor), decide_application(actor,application_id,action,comment=""), withdraw_application(actor,application_id). Use YOUR actual models  supplied below, with actual field names and Fusion Principal.user_id / .has_permission. Initial request and decision behavior should follow the supplied problem statement. Use existing leave_elm permission codes from registry.py. Reuse Django ORM/configuration and core.api.exceptions, without DRF in services. Keep all operations compact. Do not add getters for every field, repeated process_* functions, can_* methods, dataclasses, dummy pass functions or unrelated workflows to this file. Later small files will hold follow-up requests/admin/year-end/SLA. Do not change model fields or existing helper logic. Return one complete file and stop. Use only the actual registered models from models.py. Do not import domain/policy.py: it currently contains misplaced Django model definitions and is being corrected as a separate integration issue. Generate exactly the five named functions, with real operation bodies; do not copy model definitions or core error classes. Finish the JSON object and stop.

Required output paths:
modules/leave_elm/services/leave.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 010 Small leave query service with repetition control

UTC: 2026-10-12T14:00:24.682797+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file modules/leave_elm/registry.py
```
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "reviewer": ["leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.review", "leave_elm.application.approve", "leave_elm.substitute.respond"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}

SYSTEM_PERMISSIONS = [
    "leave_elm.application.approve",
    "leave_elm.application.review",
    "leave_elm.application.create",
    "leave_elm.application.view_self",
    "leave_elm.substitute.respond",
    "leave_elm.task.view",
    "leave_elm.configuration.manage",
    "leave_elm.record.manage",
]

```


END OF REFERENCES

CURRENT TASK

Create ONE short Python file, services/queries.py. It must contain exactly three MODULE-LEVEL functions and no classes: list_applications(actor), own_balances(actor), assigned_tasks(actor). Return Django QuerySets from LeaveApplication, LeaveBalance and LeaveTask, filtered to actor.user_id using actual user_id fields. Reuse Fusion actor.has_permission with application.view_self or task.view permission codes as appropriate; raise core.api.exceptions.PermissionDeniedError if access is not granted. Use only existing registered model classes and fields shown in reference. No business workflow decisions, validation, getters per field, declarations of models, placeholder pass functions, repeated if blocks or other public functions. Maximum 45 source lines. Return the complete file in JSON and then stop.

Required output paths:
modules/leave_elm/services/queries.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 011 Correct pure domain module placement

UTC: 2026-10-12T14:04:49.905471+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1200, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/domain/policy.py
```
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(models.Model, TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(models.Model, TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(models.Model, TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(models.Model, TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name

```


END OF REFERENCES

CURRENT TASK

Mechanical Fusion layer correction only: domain/policy.py currently duplicates the Django model definitions already present in models.py. Domain modules must not import Django, DRF, ORM models or Celery, and must not declare Django model classes. Replace the duplicated model definitions in this file with a compact PURE-PYTHON constants module, maximum 35 lines. Export the six leave category names and the leave-policy entitlement defaults already present in the supplied LeavePolicy model. Do not add workflow algorithms, validate requirements, change any default value, modify any model file, or introduce new rules. These are only constant names for the existing definitions, not a business-rule repair. Return only this pure constants file.

Required output paths:
modules/leave_elm/domain/policy.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 012 Initial application creation service

UTC: 2026-10-12T14:05:09.825243+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

Generate the initial ELM submission service using the existing models. Exactly one function submit_application(actor, data) in services/applications.py, maximum 45 lines. data is serializer validated data with leave_type, start_date, end_date, purpose. Enforce the existing application.create permission via actor.has_permission, set user_id from Principal and record submission history/task using existing fields. Use transaction.atomic. Use the existing core.api.exceptions error interfaces. Do not redefine models or generate other operations. This is initial code generation, not correction of business logic.

Required output paths:
modules/leave_elm/services/applications.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 013 Initial application actions service

UTC: 2026-10-12T14:05:34.618876+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen-trial/problem-statement-context.md
```
Employee Leave Management (ELM)
Synchronized Problem Statement and Controlled Context
Status: FINAL SYNCHRONIZED BASELINE | Version 1.4
Revision basisThis final synchronized baseline incorporates the 18 domain adjudications made after the Phase-2 materials, the coherent-CFR / atomic-AFR requirements arrangement, and the finalized UC/WF formalism. The historical SRS-EL-001…107 set remains the immutable as-administered student baseline and is preserved through the companion crosswalk.
1. Context
Fusion is the institute ERP used to provide administrative, academic, student, and related services. Users may hold one or more roles, and access to ELM capabilities is controlled through role-based permissions.
ELM supports leave-related activities for institute employees. Employees are Faculty or Staff, each with a designation and an organizational unit such as a Department, Section, or Office. Each organizational unit has a Unit Head. Depending on leave type and hierarchy, the Unit Head either gives the final decision or reviews and records Recommended / Not Recommended before the request moves through the applicable higher-sanction path.
2. Leave categories and Station Leave
ELM supports CL, RH, SCL, EL, COL, and VL. Station Leave permission/details are captured within the same leave application when the employee will be outside Jabalpur; Station Leave is not a separate leave-request process.
3. Entitlement, applicability, and carry-forward
CL: 8 days/year for each employee; first-half and second-half CL are supported; an approved half day consumes 0.5 CL day; unused CL does not carry forward.
RH: 2 days/year for each employee; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH does not carry forward.
SCL: up to 15 days/year for each employee for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility rule is required in this baseline; unused SCL does not carry forward.
EL: non-faculty employees receive 30 days/year directly; unused EL carries forward.
VL: faculty receive 60 VL associated with vacation periods supplied through the institute Academic Calendar. VL may be availed only during an applicable vacation period. At year end, all unused VL converts to EL at 2 VL : 1 EL, including fractional conversion. VL itself does not carry forward; converted EL is credited to the faculty member’s EL balance, may carry forward, and may later be availed.
COL: 20 days/year in this baseline for each eligible employee; COL is medical/balance-controlled leave, supporting medical evidence may be required where applicable, and unused COL carries forward.
4. Leave-day counting
For EL, COL, and VL, leave is counted continuously across the approved leave interval. Intervening weekends and closed holidays within the interval count as leave days. This continuing-count rule does not apply to CL, SCL, or RH.
5. Applying for leave and validation
The employee submits one leave application containing leave category, requested period, purpose/reason, and other required information. Station Leave details are included in the same application when applicable.
Before a new request is allowed to proceed, ELM validates the employee’s leave-category eligibility, available entitlement/balance, applicable leave-counting and calendar conditions, and impermissible overlap with the employee’s active pending or approved leave. First-half and second-half CL on the same date are not treated as overlapping when they occupy different halves.
Leave-policy parameters do not use a draft/publish/effective-version lifecycle in this baseline. Validation uses the current configured leave-policy parameters. Date and RH validation use the currently effective published holiday/RH calendar.
6. Substitute / responsibility coverage
When responsibility coverage is required, the applicant nominates one substitute. The substitute must be another employee, must not be the applicant, and must not have overlapping pending or approved leave during the responsibility period.
The nominated substitute may accept or decline the assignment. Required substitute consent must be accepted before approval routing continues. If the substitute declines, the applicant may nominate another eligible substitute or withdraw the pending request.
7. Review, sanction, and decision communication
For CL and RH, including associated Station Leave, the request is routed to the applicant’s Unit Head and the Unit Head is the final authority.
For SCL, EL, COL, and VL, the Unit Head reviews the request and records Recommended or Not Recommended. Not Recommended is not a final rejection for these categories. The request then proceeds through the configured hierarchy to the appropriate final Sanctioning Authority.
The processing/sanctioning path is resolved from the applicant, organizational unit, designation/role, leave category, and current hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar, and Director. An Establishment processing step occurs where configured. The Director’s own leave follows the Director-specific self-sanction rule.
On a final decision, the decision is recorded and the employee is notified. On final approval, the employee’s leave record/account is also updated. Intermediate decisions and state changes need not generate general notifications; the employee can inspect them through leave status/history.
8. Pending request, withdrawal, and approved-leave cancellation
A submitted pending leave request is not modified in place. If a change is required before final approval, the employee may withdraw the pending request and submit a new application if needed.
A pending request may be withdrawn immediately at any time before final approval. Upon successful withdrawal, the withdrawal becomes effective immediately, all remaining approval processing for that request terminates, later approve/reject actions are prevented, and the concerned roles are informed.
After final approval, withdrawal is no longer available. Before the approved leave begins, the employee may request cancellation. Cancellation follows the same applicable hierarchy as the original leave and the approved leave is not edited in place. If cancellation is finally approved, the leave is marked Cancelled and any leave balance already deducted for the approval is restored or adjusted accordingly. If cancellation is rejected, the original approved leave remains unchanged. If revised leave is still required after cancellation, a fresh application is submitted.
Once leave has begun, pre-start cancellation no longer applies; change is handled through the applicable extension or resumption process.
9. Extension
An employee already on ongoing EL, COL, or VL may request additional leave time. The extension is validated using the applicable eligibility, balance, substitute, calendar, and approval conditions; required substitute consent is obtained before approval routing continues; and the extension follows the applicable Unit Head and configured higher-sanction path.
When an extension is approved, only the incremental additional leave period is posted and the original approved leave remains the base. When an extension is rejected, the original approved leave remains unchanged.
10. Resumption
Resumption is supported for EL, COL, and VL. After returning, the employee submits the actual resumption date and required resumption details through ELM for review by the applicable Sanctioning Authority.
When the employee resumes on the approved end date, the Sanctioning Authority reviews the resumption and no adjustment is made to the approved leave period or leave balance. When the employee resumes earlier or later than the approved end date, ELM records the actual leave period after review, adjusts the leave balance accordingly, and synchronizes the relevant leave/attendance records.
11. Inquiry and employee-accessible records
ELM provides employees with access to their current leave balances and leave-account/request history, including request status and recorded final decisions. ELM also provides an employee-accessible printable/exportable representation of a leave application.
12. Administrative functions and calendars
Authorized administrative roles maintain leave-policy parameters, the relevant hierarchy configuration, and leave records where authorized. Policy parameters do not require a draft/publish/effective-version lifecycle; ELM uses the current configured policy and hierarchy values.
Authorized administrative roles create, revise, and publish the holiday/RH calendar. Date/RH validation uses the currently effective published holiday/RH calendar until a replacement is published.
Vacation periods used for VL are supplied through the institute Academic Calendar, which is maintained outside ELM by the appropriate academic module/service and is assumed to be available to ELM.
Authorized Leave Administrators may retrospectively record leave already sanctioned through an authorized paper/offline process where ELM could not be used because of illness, connectivity, server unavailability, or another acceptable reason. The entry captures sanction/reference evidence, is validated for record consistency, and updates the relevant leave balance/history. This is record synchronization, not a second approval workflow.
13. Event-triggered year-end processing
When the configured year-end boundary is reached, ELM applies the defined category outcomes: unused CL, RH, and SCL lapse; unused faculty VL is converted to EL; EL and COL carry forward according to policy. The resulting leave-account transactions are recorded and processing exceptions are reported. The year-end boundary is an event trigger, not an ELM actor.
14. SLA
Actionable workflow tasks use configurable reminder and escalation thresholds. When a task is assigned, the assigned user is notified. If the task is still pending at the reminder threshold, the responsible user is reminded and the action is logged; no reminder is issued if the task is no longer pending. If the task remains pending past the escalation threshold, ELM notifies or escalates to the configured higher/responsible authority and logs the escalation; no escalation is issued if the task is no longer pending.
15. Scope boundary
This ELM baseline limits leave categories to CL, RH, SCL, EL, COL, VL, and Station Leave as defined above. Other leave types and low-level design/implementation details are outside this requirements baseline. The Academic Calendar is an external dependency for VL vacation-period data.
Appendix A — Actor, Role, and External Dependency Registry
ID
Preferred term
Responsibility
ACT-01
Employee
Faculty or Staff member applying for and managing own leave.
ACT-02
Substitute / Responsibility Holder
Employee nominated to accept responsibility during the applicant’s absence.
ACT-03
Unit Head
Head of Department/Section/Office; final authority for CL/RH or reviewer/recommender for higher-sanction leave.
ACT-04
Deputy Registrar (Estt.) / Establishment Processing Role
Performs establishment-level verification/routing/record functions where configured.
ACT-05
Dean
Competent authority where applicable.
ACT-06
Registrar
Competent authority where applicable.
ACT-07
Director
Highest competent authority; Director-specific self-sanction rule applies.
ACT-08
Leave Administrator
Maintains authorized ELM configuration/records and records offline-sanctioned leave where authorized.
EXT-01
Academic Calendar service/module
External source of published vacation periods used for VL applicability.
EVT-01
Year-end boundary
Event trigger for EL-UC-020 year-end leave processing; not an actor.
EVT-02
Configured SLA threshold reached
Event trigger for EL-UC-021 SLA threshold processing; not an actor.
Faculty and Staff are employee categories. Unit Head, Substitute, Leave Administrator, Deputy Registrar (Estt.), Dean, Registrar, and Director are roles/authorities. EXT-01 is an external information dependency rather than an ELM actor performing a leave workflow action. EVT-01 and EVT-02 are event triggers; they initiate event-triggered use cases but are not actors.
Appendix B — Controlled Glossary
Term
Meaning
Employee
Faculty or Staff member using ELM for own leave activity.
Applicant
Employee whose leave request is being processed.
Unit Head
Head of the applicant’s Department, Section, or Office.
Substitute / Responsibility Holder
One eligible employee nominated to carry responsibility during the applicant’s absence.
Sanctioning Authority
Competent authority with final approval/rejection power for the applicable routed request.
Station Leave
Permission/details associated with leaving Jabalpur, captured inside the same leave application.
Withdrawal
Immediate termination of a pending request before final approval, including termination of remaining approval processing.
Cancellation
Pre-start reversal request for an approved leave, processed through the applicable hierarchy.
Extension
Request for additional leave time while EL/COL/VL is ongoing.
Resumption
Employee declaration of actual return to duty after EL/COL/VL, reviewed by the applicable Sanctioning Authority.
Early resumption
Return before the approved end date, followed after review by actual-period/balance adjustment.
Late resumption
Return after the approved end date, followed after review by actual-period/balance adjustment.
Offline-sanctioned leave
Leave already authorized through a valid paper/offline route and later entered into ELM for synchronization with sanction/reference evidence.
SLA
Configurable response-time expectation for actionable workflow tasks, with pending-only reminder and escalation.

```


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/registry.py
```
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "reviewer": ["leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.review", "leave_elm.application.approve", "leave_elm.substitute.respond"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}

SYSTEM_PERMISSIONS = [
    "leave_elm.application.approve",
    "leave_elm.application.review",
    "leave_elm.application.create",
    "leave_elm.application.view_self",
    "leave_elm.substitute.respond",
    "leave_elm.task.view",
    "leave_elm.configuration.manage",
    "leave_elm.record.manage",
]

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

Generate initial ELM action service in services/actions.py, maximum 90 lines. Provide act_on_application(actor, application_id, action, data) supporting approve, reject, withdraw, cancel, extend, resume, substitute and recommend. Reuse the existing model fields and permission names, ORM lookups, history and followup models. No new schema or duplicate models. Followup actions are available as described in the original problem statement. Return one concise file. Do not add repeated branches for identical actions. This is initial model implementation; no correctness audit or business-rule repair is requested.

Required output paths:
modules/leave_elm/services/actions.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 014 Initial API serializer interfaces

UTC: 2026-10-12T14:06:48.436330+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


END OF REFERENCES

CURRENT TASK

Generate api/serializers.py using DRF ModelSerializer. Maximum 80 lines. Classes LeaveApplicationSerializer, LeaveBalanceSerializer, LeaveTaskSerializer, LeavePolicySerializer, LeaveCalendarSerializer. Use the exact existing model field names. Application accepts leave_type, start_date, end_date, purpose; id,user_id,status,timestamps and followup state read only. Other serializers use fields="__all__". No service code or new models.

Required output paths:
modules/leave_elm/api/serializers.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 015 Initial employee and action API views

UTC: 2026-10-12T14:07:11.736415+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/services/queries.py
```
from django.db.models import Q
from core.api.exceptions import PermissionDeniedError
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveTask

def list_applications(actor):
    if not actor.has_permission('leave_elm.application.view_self'):
        raise PermissionDeniedError()
    return LeaveApplication.objects.filter(user_id=actor.user_id)


def own_balances(actor):
    if not actor.has_permission('leave_elm.configuration.manage'):
        raise PermissionDeniedError()
    return LeaveBalance.objects.filter(user_id=actor.user_id)


def assigned_tasks(actor):
    if not actor.has_permission('leave_elm.task.view'):
        raise PermissionDeniedError()
    return LeaveTask.objects.filter(leave_application__user_id=actor.user_id)
```


### Repository file modules/leave_elm/services/applications.py
```


from django.db import transaction
from modules.leave_elm.models import LeaveApplication, LeaveHistory, LeaveTask
from fusion_auth.principal import Principal
from core.api.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError, PermissionDeniedError
import datetime

@transaction.atomic
def submit_application(actor, data):
    if not actor.has_permission('leave_elm.application.create'):
        raise PermissionDeniedError()

    try:
        # Create a new leave application
        leave_application = LeaveApplication(
            user_id=actor.user_id,
            leave_type=data['leave_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            purpose=data['purpose'],
        )
        leave_application.save()

        # Record history for submission
        leave_history = LeaveHistory(
            leave_application=leave_application,
            status='Submitted',
        )
        leave_history.save()

        # Record task for submission
        leave_task = LeaveTask(
            leave_application=leave_application,
            task_type='Submission',
            status='Pending',
        )
        leave_task.save()

        return leave_application

    except Exception as e:
        raise DomainError(str(e))

```


### Repository file modules/leave_elm/services/actions.py
```
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from core.api.exceptions import DomainError, NotFoundError, PermissionDeniedError
from modules.leave_elm.models import LeaveApplication, LeaveHistory, LeaveTask, LeaveSubstitution, LeaveExtension, LeaveResumption

def act_on_application(actor, application_id, action, data):
    try:
        leave_app = LeaveApplication.objects.get(id=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError(message='Leave Application not found')

    if actor.kind != 'faculty' and actor.kind != 'staff':
        raise PermissionDeniedError(message='Only faculty/staff can perform leave-related actions')

    with transaction.atomic():
        if action == 'approve':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot approve an already approved/rejected/cancelled application')

            leave_app.approved_by = actor
            leave_app.approved_at = timezone.now()
            leave_app.status = 'Approved'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Approved',
                decision=data['decision'] or 'Approved by ' + str(actor.username),
            )

            # Update balance
            update_leave_balance(leave_app.user_id, leave_app.leave_category, -leave_app.days)

        elif action == 'reject':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot reject an already approved/rejected/cancelled application')

            leave_app.status = 'Rejected'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Rejected',
                decision=data['decision'] or 'Rejected by ' + str(actor.username),
            )

        elif action == 'withdraw':
            if leave_app.status not in ['Pending', 'Submitted']:
                raise DomainError(message='Only pending/submitted applications can be withdrawn')

            leave_app.status = 'Withdrawn'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Withdrawn',
                decision=data['decision'] or 'Withdrawn by ' + str(actor.username),
            )

        elif action == 'cancel':
            if leave_app.status not in ['Approved', 'Cancelled']:
                raise DomainError(message='Only approved/cancelled applications can be cancelled')

            leave_app.status = 'Cancelled'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Cancelled',
                decision=data['decision'] or 'Cancelled by ' + str(actor.username),
            )

            # Update balance
            update_leave_balance(leave_app.user_id, leave_app.leave_category, -leave_app.days)

        elif action == 'extend':
            if leave_app.status != 'Approved' or leave_app.extension_requested:
                raise DomainError(message='Cannot extend an application that is not yet approved or has already been extended')

            leave_app.extension_requested = True
            leave_app.extension_start_date = data.get('extension_start_date', leave_app.end_date + timedelta(days=1))
            leave_app.extension_end_date = data.get('extension_end_date', leave_app.end_date + timedelta(days=30))

            leave_app.save()

            # Create task for extension approval
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Extension Approval',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'resume':
            if leave_app.status != 'Approved' or leave_app.resumption_start_date:
                raise DomainError(message='Cannot resume an application that is not yet approved or has already been resumed')

            leave_app.resumption_start_date = data['actual_resumption_date']

            leave_app.save()

            # Create task for resumption review
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Resumption Review',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'substitute':
            if leave_app.status != 'Pending' or leave_app.substitution_requested:
                raise DomainError(message='Cannot request a substitute for an application that is not pending or has already been requested')

            substitution_user_id = data.get('substitute_user_id')

            try:
                substitute_user = User.objects.get(id=substitution_user_id)
            except User.DoesNotExist:
                raise NotFoundError(message='Substitute user not found')

            leave_app.substitution_requested = True
            leave_app.substitute_user_id = substitution_user_id

            leave_app.save()

            # Create task for substitute approval
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Substitute Approval',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'recommend':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot recommend an application that is not yet pending')

            leave_app.status = 'Recommended'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Recommended',
                decision=data['decision'] or 'Recommended by ' + str(actor.username),
            )

    actor.notify_leave_status(leave_app.id, leave_app.status)

    return leave_app
```


### Repository file modules/leave_elm/api/serializers.py
```
from rest_framework import serializers
from .models import LeaveApplication, LeaveBalance, LeaveTask, LeavePolicy, LeaveCalendar

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'user_id', 'status'] + [field.name for field in LeaveApplication._meta.fields if field.name != 'id' and field.name != 'user_id' and field.name != 'status']
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'cancelled_by', 'extension_requested', 'extension_approved', 'extension_start_date', 'extension_end_date', 'extension_approved_by', 'extension_approved_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'


class LeaveTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = '__all__'


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = '__all__'
```


### Repository file fusion_auth/permissions.py
```
"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})

```


### Repository file modules/leave_elm/registry.py
```
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "reviewer": ["leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.review", "leave_elm.application.approve", "leave_elm.substitute.respond"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}

SYSTEM_PERMISSIONS = [
    "leave_elm.application.approve",
    "leave_elm.application.review",
    "leave_elm.application.create",
    "leave_elm.application.view_self",
    "leave_elm.substitute.respond",
    "leave_elm.task.view",
    "leave_elm.configuration.manage",
    "leave_elm.record.manage",
]

```


END OF REFERENCES

CURRENT TASK

Generate one concise DRF APIView file, maximum 100 lines. ApplicationListView GET calls list_applications(request.principal) serialized many=True, POST validates LeaveApplicationSerializer and calls submit_application. BalanceListView GET own_balances. TaskListView GET assigned_tasks. ApplicationActionView POST calls act_on_application(request.principal, pk, request.data.get("action"), request.data). Use supplied actual service names exactly, serializers and HasModuleGrant("leave_elm")/HasPermission for the matching existing registry permission interfaces. Return Response serialized model or errors via supplied platform handler. Synchronous views. No new logic in views or models.

Required output paths:
modules/leave_elm/api/views.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 016 Initial configuration API views

UTC: 2026-10-12T14:07:43.473592+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2300, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/api/serializers.py
```
from rest_framework import serializers
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveTask, LeavePolicy, LeaveCalendar

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'user_id', 'status'] + [field.name for field in LeaveApplication._meta.fields if field.name != 'id' and field.name != 'user_id' and field.name != 'status']
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'cancelled_by', 'extension_requested', 'extension_approved', 'extension_start_date', 'extension_end_date', 'extension_approved_by', 'extension_approved_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'


class LeaveTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = '__all__'


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = '__all__'
```


### Repository file fusion_auth/permissions.py
```
"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})

```


END OF REFERENCES

CURRENT TASK

Generate a compact DRF API view file (max 75 lines) providing ConfigurationView GET current LeavePolicy, LeaveCalendar and LeaveType rows; PUT saves submitted policy and calendar configuration using existing serializers and models. Include RecordListView GET LeaveHistory and LeaveNotification rows for request.principal.user_id as JSON values. Use existing configuration.manage and record.manage permission interfaces, HasModuleGrant, no duplicate models. This is initial implementation for configuration and records, not a request to audit or repair workflow logic.

Required output paths:
modules/leave_elm/api/configuration.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 017 API URL interface registration

UTC: 2026-10-12T14:08:07.577294+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY



END OF REFERENCES

CURRENT TASK

Generate api/urls.py only, concise urlpatterns for paths without trailing slash: applications -> ApplicationListView; balances -> BalanceListView; tasks -> TaskListView; applications/<int:pk>/action -> ApplicationActionView; configuration -> ConfigurationView; records -> RecordListView. Import existing view names from .views and .configuration. No other code.

Required output paths:
modules/leave_elm/api/urls.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 018 Repair configuration syntax and Fusion permission interfaces

UTC: 2026-10-12T14:08:39.452925+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2500, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/api/configuration.py
```

from rest_framework import generics
from modules.leave_elm.models import LeavePolicy, LeaveCalendar, LeaveType
from modules.leave_elm.api.serializers import LeavePolicySerializer, LeaveCalendarSerializer
from fusion_auth.permissions import HasModuleGrant, HasPermission
import json

@HasModuleGrant('configuration')
class ConfigurationView(generics.ListCreateAPIView):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.principal.user_id)

    @HasPermission('record.manage', require_all=True)
def save_configuration(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        policy_serializer = LeavePolicySerializer(data=data['policy'])
        calendar_serializer = LeaveCalendarSerializer(data=data['calendar'])

        if policy_serializer.is_valid() and calendar_serializer.is_valid():
            policy_serializer.save(user=request.principal.user_id)
            calendar_serializer.save(user=request.principal.user_id)

            response_data = {
                'policy': policy_serializer.data,
                'calendar': calendar_serializer.data
            }

            return Response(response_data, status=201)
        else:
            return Response(policy_serializer.errors or calendar_serializer.errors, status=400)

@HasModuleGrant('configuration')
class RecordListView(generics.ListAPIView):
    queryset = LeaveHistory.objects.all()
    serializer_class = LeaveHistorySerializer

    def get_queryset(self):
        return self.queryset.filter(leave_application__user=self.request.principal.user_id)

    @HasModuleGrant('record.manage', require_all=True)
def record_view(request):
    history_query = LeaveHistory.objects.filter(leave_application__user=request.principal.user_id)
    notifications_query = LeaveNotification.objects.filter(leave_application__user=request.principal.user_id)

    history_serializer = LeaveHistorySerializer(history_query, many=True)
    notifications_serializer = LeaveNotificationSerializer(notifications_query, many=True)

    return Response({'history': history_serializer.data, 'notifications': notifications_serializer.data})
```


### Repository file fusion_auth/permissions.py
```
"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})

```


END OF REFERENCES

CURRENT TASK

Mechanical build repair only to existing api/configuration.py. Its indentation before module-level save_configuration and record_view is invalid; HasModuleGrant and HasPermission are class factories for DRF permission_classes, not decorators. Adapt to supplied interfaces: remove invalid decorators, use permission_classes on the existing ConfigurationView/RecordListView with module leave_elm and the existing configuration.manage/record.manage names. Add missing existing Response, LeaveHistory and LeaveNotification imports. The referenced LeaveHistorySerializer and LeaveNotificationSerializer are absent: add those two simple ModelSerializer classes using fields="__all__" in the same configuration.py file before the views. Preserve all existing queryset filters, function bodies, save arguments and response behavior; do not repair business or query logic. Return the entire configuration.py only, max100 lines.

Required output paths:
modules/leave_elm/api/configuration.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 019 Initial scheduled ELM events

UTC: 2026-10-12T14:09:29.551241+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name
```


### Repository file modules/leave_elm/domain/policy.py
```
LEAVE_CATEGORY_NAMES = ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']

LEAVE_POLICY_DEFAULTS = {
    'CL': 8,
    'RH': 2,
    'SCL': 15,
    'EL': 30,
    'COL': 20,
    'VL': 60
}

```


END OF REFERENCES

CURRENT TASK

Generate a concise services/events.py module (maximum 55 lines) with year_end_rollover() and process_task_sla() implementations using existing LeaveBalance/LeavePolicy/LeaveTask/LeaveNotification models. Year-end balances and pending task reminder/escalation in-app notifications are the two ELM scheduled events from the specifications. No Celery decorators in services. Use only existing model fields. Do not change model schema, audit business rules, or systematically test functionality.

Required output paths:
modules/leave_elm/services/events.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 020 Scheduled task and worker registration

UTC: 2026-10-12T14:10:07.356156+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1300, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/services/events.py
```
from django.core.mail import send_mail
from datetime import timedelta
from .models import LeaveBalance, LeavePolicy, LeaveTask, LeaveNotification


def year_end_rollover():
    # Logic to calculate new leave balance for each user based on policy defaults
    current_year = timezone.now().year
    policies = LeavePolicy.objects.all()
    for policy in policies:
        category_defaults = LEAVE_POLICY_DEFAULTS.get(policy.name)
        if category_defaults is None:
            continue
        for leave_category in LEAVE_CATEGORY_NAMES:
            balance = LeaveBalance.objects.filter(leave_category__name=leave_category).aggregate(total_balance=models.Sum('balance'))['total_balance'] or 0
            new_balance = balance + (category_defaults - balance / 12) * 12
            LeaveBalance.objects.update_or_create(
                leave_category__name=leave_category,
                defaults={'balance': new_balance}
            )


def process_task_sla():
    # Logic to check and notify pending tasks that are approaching SLA thresholds
    threshold_days = {
        'Reminder': 60,
        'Escalation': 120
    }
    now = timezone.now()
    for task in LeaveTask.objects.filter(status='Pending'):
        reminder_threshold = threshold_days.get(task.task_type, 30)
        escalation_threshold = threshold_days.get(task.task_type, 90)
        if now > task.reminder_threshold and not task.notification_sent:
            send_mail(
                subject=f'Leave Task Reminder: {task.leave_application.id} - {task.task_type}',
                message=f'Reminder: Your leave task is due on {task.reminder_threshold.strftime('%Y-%m-%d')}.
Please update the status of your leave application.',
                from_email='noreply@yourdomain.com',
                recipient_list=[task.leave_application.user.email],
                fail_silently=False
            )
            task.notification_sent = True
            task.save()
        elif now > task.escalation_threshold and not task escalated:
            send_mail(
                subject=f'Leave Task Escalation: {task.leave_application.id} - {task.task_type}',
                message=f'Escalation: Your leave task has exceeded its SLA of {task.escalation_threshold.days} days.
Please escalate the issue to a higher authority.',
                from_email='noreply@yourdomain.com',
                recipient_list=[task.leave_application.user.email],
                fail_silently=False
            )
            task.escalated = True
            task.save()
```


### Repository file modules/placement/schedule.py
```
"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before, which meant `expire_overdue_offers` never ran:
an offer nobody answered stayed `issued` forever and kept its student blocked
from the pool, with no way out but a manual database edit.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "placement.deliver_notifications": {"queue": "notifications"},
    "placement.rebuild_active_stats": {"queue": "reports"},
    "placement.rebuild_stats": {"queue": "reports"},
    # Offer expiry stays on default so it never queues behind a report.
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "placement.deliver-notifications": {
        "task": "placement.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # PC-BR-013: five minutes is what a student experiences as the deadline.
    "placement.expire-overdue-offers": {
        "task": "placement.expire_overdue_offers",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # Snapshots back the stats page, so it never reads transactional tables.
    "placement.rebuild-active-stats": {
        "task": "placement.rebuild_active_stats",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}

```


### Repository file config/celery.py
```
import os

from celery import Celery

from modules.placement.schedule import (
    BEAT_SCHEDULE as PLACEMENT_SCHEDULE,
)
from modules.placement.schedule import (
    TASK_ROUTES as PLACEMENT_ROUTES,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
app = Celery("fusion_integrated")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Each module owns its timers; this only merges them, so modules stay removable.
app.conf.beat_schedule = {**PLACEMENT_SCHEDULE}
app.conf.task_routes = {**PLACEMENT_ROUTES}

```


END OF REFERENCES

CURRENT TASK

Generate tasks.py and schedule.py, max 50 lines total. tasks.py has Celery shared_task wrappers elm_year_end_rollover and elm_task_sla invoking existing services/events.py functions. schedule.py exports BEAT_SCHEDULE for annual rollover at Jan1 midnight and SLA each 15 minutes, and TASK_ROUTES mapping modules.leave_elm.tasks.* to queue default. Use the supplied Fusion Celery interfaces; wrappers only, no new business logic.

Required output paths:
modules/leave_elm/tasks.py
modules/leave_elm/schedule.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 021 Missing record serializer interface definitions

UTC: 2026-10-12T14:10:32.369180+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY



END OF REFERENCES

CURRENT TASK

Generate api/record_serializers.py only, at most20 lines. Import DRF serializers and existing LeaveHistory/LeaveNotification from modules.leave_elm.models. Declare LeaveHistorySerializer and LeaveNotificationSerializer as ModelSerializer, Meta model respectively and fields="__all__". No other code.

Required output paths:
modules/leave_elm/api/record_serializers.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 022 Repair incomplete Celery schedule configuration

UTC: 2026-10-12T14:11:02.135640+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY



END OF REFERENCES

CURRENT TASK

Return only complete schedule.py, maximum25 lines. Import crontab from celery.schedules. BEAT_SCHEDULE dict has two entries: elm-year-end-rollover task modules.leave_elm.tasks.elm_year_end_rollover schedule crontab(month_of_year=1,day_of_month=1,hour=0,minute=0); elm-task-sla task modules.leave_elm.tasks.elm_task_sla schedule crontab(minute="*/15"). TASK_ROUTES={"modules.leave_elm.tasks.*":{"queue":"default"}}. Close every string, bracket and dictionary. This is worker configuration only.

Required output paths:
modules/leave_elm/schedule.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 023 Initial typed frontend API client

UTC: 2026-10-12T14:11:29.712426+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2300, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/api/urls.py
```

from django.urls import path
from .views import ApplicationListView, BalanceListView, TaskListView, ApplicationActionView
from .configuration import ConfigurationView, RecordListView

urlpatterns = [
    path('applications', ApplicationListView.as_view(), name='application-list'),
    path('balances', BalanceListView.as_view(), name='balance-list'),
    path('tasks', TaskListView.as_view(), name='task-list'),
    path('applications/<int:pk>/action', ApplicationActionView.as_view(), name='application-action'),
    path('configuration', ConfigurationView.as_view(), name='configuration-view'),
    path('records', RecordListView.as_view(), name='record-list'),
]

```


### Repository file modules/leave_elm/api/serializers.py
```
from rest_framework import serializers
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveTask, LeavePolicy, LeaveCalendar

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'user_id', 'status'] + [field.name for field in LeaveApplication._meta.fields if field.name != 'id' and field.name != 'user_id' and field.name != 'status']
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'cancelled_by', 'extension_requested', 'extension_approved', 'extension_start_date', 'extension_end_date', 'extension_approved_by', 'extension_approved_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'


class LeaveTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = '__all__'


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = '__all__'
```


### Repository file modules/leave_elm/api/configuration.py
```

from rest_framework import generics
from modules.leave_elm.models import LeavePolicy, LeaveCalendar, LeaveType, LeaveHistory, LeaveNotification
from modules.leave_elm.api.serializers import LeavePolicySerializer, LeaveCalendarSerializer
from .record_serializers import LeaveHistorySerializer, LeaveNotificationSerializer
from fusion_auth.permissions import HasModuleGrant, HasPermission
import json
from rest_framework.response import Response

class ConfigurationView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave_elm"), HasPermission("leave_elm.configuration.manage")]
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.principal.user_id)

def save_configuration(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        policy_serializer = LeavePolicySerializer(data=data['policy'])
        calendar_serializer = LeaveCalendarSerializer(data=data['calendar'])

        if policy_serializer.is_valid() and calendar_serializer.is_valid():
            policy_serializer.save(user=request.principal.user_id)
            calendar_serializer.save(user=request.principal.user_id)

            response_data = {
                'policy': policy_serializer.data,
                'calendar': calendar_serializer.data
            }

            return Response(response_data, status=201)
        else:
            return Response(policy_serializer.errors or calendar_serializer.errors, status=400)

class RecordListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave_elm"), HasPermission("leave_elm.record.manage")]
    queryset = LeaveHistory.objects.all()
    serializer_class = LeaveHistorySerializer

    def get_queryset(self):
        return self.queryset.filter(leave_application__user=self.request.principal.user_id)

def record_view(request):
    history_query = LeaveHistory.objects.filter(leave_application__user=request.principal.user_id)
    notifications_query = LeaveNotification.objects.filter(leave_application__user=request.principal.user_id)

    history_serializer = LeaveHistorySerializer(history_query, many=True)
    notifications_serializer = LeaveNotificationSerializer(notifications_query, many=True)

    return Response({'history': history_serializer.data, 'notifications': notifications_serializer.data})
```


### Repository file client/src/lib/http.ts
```
/** One axios instance for the whole app, with the interceptors the legacy
 *  academic SPA never had. */
import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,          // the session cookie, never a JS-readable token
  timeout: 15000,
});

/** Paired with the session cookie. Held in memory rather than a readable
 *  cookie, which the SPA could not read cross-origin in development. */
let csrfToken = "";
export function setCsrfToken(value: string) {
  csrfToken = value ?? "";
}

const UNSAFE = new Set(["post", "put", "patch", "delete"]);

http.interceptors.request.use((config) => {
  if (csrfToken && UNSAFE.has((config.method ?? "get").toLowerCase())) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

http.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) onUnauthorized?.();
    return Promise.reject(error);
  },
);

/** Pull a usable message out of the platform's error envelope. */
export function errorMessage(e: unknown): string {
  const env = (e as { response?: { data?: { error?: {
    message?: string; details?: { message?: string }[] } } } })
    ?.response?.data?.error;
  if (!env) return "Something went wrong. Please try again.";
  if (env.details?.length) {
    return env.details.map((d) => d.message).filter(Boolean).join(" ") ||
      env.message || "Request failed.";
  }
  return env.message ?? "Request failed.";
}

/** A `responseType: "blob"` request delivers the *error* body as a Blob too,
 *  which hides the envelope from errorMessage. Read it back before rethrowing. */
export async function readBlobError(e: unknown): Promise<unknown> {
  const res = (e as { response?: { data?: unknown } })?.response;
  if (res?.data instanceof Blob) {
    try {
      res.data = JSON.parse(await res.data.text());
    } catch {
      res.data = undefined;             // an HTML page, not our envelope
    }
  }
  return e;
}

export function errorStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } })?.response?.status;
}

export function requestId(e: unknown): string | undefined {
  return (e as { response?: { data?: { error?: { request_id?: string } } } })
    ?.response?.data?.error?.request_id;
}

```


END OF REFERENCES

CURRENT TASK

Generate a compact TypeScript api.ts file for the ELM React module (max110 lines). Import http from ../../../lib/http. Export interfaces LeaveApplication, LeaveBalance, LeaveTask, Configuration and NewApplication, plus async functions listApplications(), listBalances(), listTasks(), submitApplication(data: NewApplication), applicationAction(id:number, action:string, data:Record<string,unknown>), getConfiguration(), saveConfiguration(data:Configuration), getRecords(). Existing API routes use /leave/applications etc and return bare arrays. Match existing generated model fields; no new dependencies, no fetch or custom auth. NewApplication has leave_type:number,start_date:string,end_date:string,purpose:string. Keep response types explicit for TypeScript. Configuration shape policy and calendar can use Record<string,unknown> arrays as needed. Use supplied API shapes, do not fix backend logic.

Required output paths:
client/src/modules/leave_elm/api.ts

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 024 Initial employee leave page

UTC: 2026-10-12T14:12:01.128637+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 4000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../../lib/http';

interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

interface LeaveBalance {
  // Define your LeaveBalance interface here
}

interface LeaveTask {
  // Define your LeaveTask interface here
}

interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/configuration');
  return response.data as Configuration;
}

async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/configuration', data);
}

async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React18/Mantine7 page with default export MyLeavePage, max150 lines. Use the supplied api.ts functions and types; ReactQuery5 object-form useQuery/useMutation. Show applications and balances, form with numeric leave_type and string date fields and purpose, submit via submitApplication; actions withdraw/cancel/extend/resume via applicationAction. Use PageHeader from ../../../ui/components/PageHeader and errorMessage from ../../../lib/http. Basic form fields for extension and actual resumption dates if needed. Show pending/error states and invalidate queries after mutation. Use standard Mantine Stack/Text/Table/TextInput/NumberInput/Textarea/Button etc and React types compatible with existing dependency versions. No new packages or fake backend data. Backend workflow logic stays untouched.

Required output paths:
client/src/modules/leave_elm/pages/MyLeavePage.tsx

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 025 Initial leave work queue page

UTC: 2026-10-12T14:12:49.119682+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React18/Mantine7 page with default export LeaveTasksPage, max110 lines. useQuery object syntax for listTasks and listApplications, render task/application rows, decision comment and action buttons approve/reject/recommend/substitute using applicationAction. Use supplied api.ts exact names/types, PageHeader from ../../../ui/components/PageHeader, errorMessage from ../../../lib/http. useMutation object syntax and invalidate affected queries. Basic loading/error indicators, no fake data, no invented dependencies. Do not change backend workflow.

Required output paths:
client/src/modules/leave_elm/pages/LeaveTasksPage.tsx

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 026 Repair incomplete employee page React interfaces

UTC: 2026-10-12T14:13:30.887059+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


END OF REFERENCES

CURRENT TASK

The previous MyLeavePage.tsx is truncated and cannot compile. Return a complete concise default-export FUNCTION COMPONENT MyLeavePage (not class), maximum65 lines. React18, Mantine7 (Textarea not TextArea; Group gap not spacing), ReactQuery5 object useQuery syntax and useQueryClient.invalidateQueries({queryKey:["applications"]}). Import exact functions listApplications/listBalances/submitApplication/applicationAction and NewApplication from ../api. Import named PageHeader from ../../../ui/components/PageHeader. Show applications/balances as JSON; simple TextInput start_date/end_date/purpose and NumberInput leave_type form with useState<NewApplication>; submit button calls submitApplication. For each application keep action buttons withdraw/cancel/extend/resume calling applicationAction with empty data. Use current application ids and status values, do not repair backend logic or evaluate requirements. Keep rendering and calls basic so the file is complete. All existing generated API calls and behavior stay as they are.

Required output paths:
client/src/modules/leave_elm/pages/MyLeavePage.tsx

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 027 Repair incomplete employee page React interfaces raw source

UTC: 2026-10-12T14:14:27.061208+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


END OF REFERENCES

CURRENT TASK

The previous MyLeavePage.tsx is truncated and cannot compile. Return a complete concise default-export FUNCTION COMPONENT MyLeavePage (not class), maximum65 lines. React18, Mantine7 (Textarea not TextArea; Group gap not spacing), ReactQuery5 object useQuery syntax and useQueryClient.invalidateQueries({queryKey:["applications"]}). Import exact functions listApplications/listBalances/submitApplication/applicationAction and NewApplication from ../api. Import named PageHeader from ../../../ui/components/PageHeader. Show applications/balances as JSON; simple TextInput start_date/end_date/purpose and NumberInput leave_type form with useState<NewApplication>; submit button calls submitApplication. For each application keep action buttons withdraw/cancel/extend/resume calling applicationAction with empty data. Use current application ids and status values, do not repair backend logic or evaluate requirements. Keep rendering and calls basic so the file is complete. All existing generated API calls and behavior stay as they are. Return complete source; close JSX tags, function and export. No commentary or JSON.

Output file: client/src/modules/leave_elm/pages/MyLeavePage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 028 Initial leave work queue page raw source

UTC: 2026-10-12T14:14:55.367901+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React18/Mantine7 page with default export LeaveTasksPage, max110 lines. useQuery object syntax for listTasks and listApplications, render task/application rows, decision comment and action buttons approve/reject/recommend/substitute using applicationAction. Use supplied api.ts exact names/types, PageHeader from ../../../ui/components/PageHeader, errorMessage from ../../../lib/http. useMutation object syntax and invalidate affected queries. Basic loading/error indicators, no fake data, no invented dependencies. Do not change backend workflow. Return complete source; close JSX tags, function and export. No commentary or JSON.

Output file: client/src/modules/leave_elm/pages/LeaveTasksPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 029 Initial leave configuration page raw source

UTC: 2026-10-12T14:15:21.261941+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React18/Mantine7 page with default export LeaveAdminPage, max110 lines. Use actual getConfiguration/saveConfiguration/getRecords exports from supplied api.ts. Provide policy/calendar JSON editor textareas, save via existing endpoint, record/history display. ReactQuery5 object syntax; show loading/error and mutation status. Use PageHeader from ../../../ui/components/PageHeader and errorMessage from ../../../lib/http. Use Mantine components; no new packages, no new backend code or workflow corrections. Return complete source; close JSX tags, function and export. No commentary or JSON.

Output file: client/src/modules/leave_elm/pages/LeaveAdminPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 030 Frontend route registration

UTC: 2026-10-12T14:15:59.645634+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.3, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY



END OF REFERENCES

CURRENT TASK

Generate routes.tsx only exporting routes:RouteObject[] with index Navigate to mine, path mine MyLeavePage, queue LeaveTasksPage, admin LeaveAdminPage. Use React lazy static imports of existing ./pages/*.tsx default exports and react-router-dom Navigate/RouteObject. Paths are relative. No other code.

Output file: client/src/modules/leave_elm/routes.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 031 Frontend response type interfaces

UTC: 2026-10-12T14:16:30.094223+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 900, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY



END OF REFERENCES

CURRENT TASK

Generate only types.ts, max45 lines, exported TypeScript interfaces matching existing backend serializer/model fields: LeaveApplication(id:number,user_id:number,status:string,leave_type:number,start_date:string,end_date:string,purpose:string), LeaveBalance(id:number,user_id:number,leave_category:number,balance:string), LeaveTask(id:number,user_id:number,leave_application:number,task_type:string,status:string). LeaveTask title and description optional string for existing generated UI assumptions, without changing backend. LeaveHistory(id:number,status:string,decision:string) and LeaveNotification(id:number,message:string). No runtime code or business fixes.

Output file: client/src/modules/leave_elm/types.ts
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 032 Compiler interface repair LeaveTasksPage

UTC: 2026-10-12T14:17:37.793686+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3500, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/pages/LeaveTasksPage.tsx
```
import { useEffect } from 'react';
import { Group, Stack, Text, Title, Button, LoadingOverlay, Alert, Container } from '@mantine/core';
import { useQuery, useMutation } from '@tanstack/react-query';
import { http } from '../../lib/http';

export const LeaveTasksPage = () => {
  const [approveTask] = useMutation((data) =>
    http.post(`/leave/applications/${data.id}/action`, { action: 'approve', data })
  );
  const [rejectTask] = useMutation((data) =>
    http.post(`/leave/applications/${data.id}/action`, { action: 'reject', data })
  );
  const [recommendTask] = useMutation((data) =>
    http.post(`/leave/applications/${data.id}/action`, { action: 'recommend', data })
  );
  const [substituteTask] = useMutation((data) =>
    http.post(`/leave/applications/${data.id}/action`, { action: 'substitute', data })
  );

  const { isLoading, isError, error, data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: listTasks,
  });

  useEffect(() => {
    if (isError && error instanceof Error) {
      console.error('Error fetching leave tasks:', error.message);
    }
  }, [isError, error]);

  return (
    <Container>
      <LoadingOverlay visible={isLoading} />
      {isError && (
        <Alert title="Error" color="red">
          {error?.message}
        </Alert>
      )}
      <PageHeader title="Leave Tasks" subtitle="Manage pending leave applications" />

      <Stack spacing="lg">
        {!isLoading && !isError && tasks.map((task) => (
          <Group key={task.id}>
            <Title order={3}>{task.title}</Title>
            <Text c="dimmed">{task.description}</Text>

            <Button onClick={() => approveTask({ id: task.id })}>Approve</Button>
            <Button onClick={() => rejectTask({ id: task.id })}>Reject</Button>
            <Button onClick={() => recommendTask({ id: task.id })}>Recommend</Button>
            <Button onClick={() => substituteTask({ id: task.id })}>Substitute</Button>
          </Group>
        ))}
      </Stack>
    </Container>
  );
};

export default LeaveTasksPage;

```


### Repository file client/src/modules/leave_elm/api.ts
```


import { http } from '../../lib/http';

export interface LeaveApplication {
  id?: number;
  user_id?: string;
  status?: string;
}

export interface LeaveBalance {
  // Define your LeaveBalance export interface here
}

export interface LeaveTask {
  // Define your LeaveTask export interface here
}

export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


END OF REFERENCES

CURRENT TASK

Fix only TypeScript/import/library interface errors in the existing file, returning its complete raw source. Correct http import to ../../../lib/http; add imports listTasks from ../api and named PageHeader. useMutation returns an object, not tuple: use {mutate:approveTask} = useMutation({mutationFn:(data:{id:number}) => http.post(...)}) for all four operations, keeping URL/payload exactly as they are. Stack spacing must be gap. tasks may be undefined: use tasks!.map preserving existing loading/error guard. Do not change task.id, task.title or task.description assumptions, actions, payloads or authorization. Remove unused imports required by noUnusedLocals. Do not rewrite or add features. No workflow/business fixes. Close all JSX.

Output file: client/src/modules/leave_elm/pages/LeaveTasksPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 033 Compiler interface repair LeaveAdminPage

UTC: 2026-10-12T14:18:15.757946+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3500, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/pages/LeaveAdminPage.tsx
```
import { useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Group, Stack, Text, Title, TextInput, TextArea, LoadingOverlay, Alert, Container, Paper, Table, Thead, Tbody, Tr, Th, Td, Pagination, Center } from "@mantine/core";
import { useRouter } from "next/router";
import { http } from '../../lib/http';

const LeaveAdminPage = () => {
  const router = useRouter();
  const [policyJSON, setPolicyJSON] = useState('');
  const [calendarJSON, setCalendarJSON] = useState('');

  // Fetch configuration data initially
  const { isLoading, isError, error, data } = useQuery(['configuration'], async () => {
    return await getConfiguration();
  });

  useEffect(() => {
    if (data) {
      setPolicyJSON(JSON.stringify(data.policy || [], null, 2));
      setCalendarJSON(JSON.stringify(data.calendar || [], null, 2));
    }
  }, [data]);

  const saveConfigurationMutation = useMutation({
    mutationFn: async (newData) => {
      return await saveConfiguration(newData);
    },
    onSuccess: () => {
      alert('Configuration saved successfully!');
    },
    onError: (error) => {
      console.error(error);
      alert('Failed to save configuration.');
    },
  });

  const handleSavePolicyClick = () => {
    try {
      const parsedPolicy = JSON.parse(policyJSON);
      saveConfigurationMutation.mutate({ policy: parsedPolicy });
    } catch (e) {
      alert('Invalid JSON format for policy');
    }
  };

  const handleSaveCalendarClick = () => {
    try {
      const parsedCalendar = JSON.parse(calendarJSON);
      saveConfigurationMutation.mutate({ calendar: parsedCalendar });
    } catch (e) {
      alert('Invalid JSON format for calendar');
    }
  };

  // Fetch records
  const { isLoadingRecords, isErrorRecords, errorRecords, dataRecords } = useQuery(['records'], async () => {
    return await getRecords();
  });

  useEffect(() => {
    if (dataRecords && dataRecords.history) {
      setHistory(dataRecords.history);
    }

    if (dataRecords && dataRecords.notifications) {
      setNotifications(dataRecords.notifications);
    }
  }, [dataRecords]);

  const history = [];
  const notifications = [];

  return (
    <Container size="lg" mt={40}>
      <PageHeader title="Leave Admin" subtitle="Manage leave policies and configurations." />

      {/* Policy Editor */}
      <Paper shadow="sm" p="md">
        <Title order={3}>Policy</Title>
        <TextArea value={policyJSON} onChange={(event) => setPolicyJSON(event.target.value)} rows={15} />
        <Group position="right" mt="xs">
          <Button onClick={handleSavePolicyClick} color="blue">Save Policy</Button>
        </Group>
      </Paper>

      {/* Calendar Editor */}
      <Paper shadow="sm" p="md" mt={20}>
        <Title order={3}>Calendar</Title>
        <TextArea value={calendarJSON} onChange={(event) => setCalendarJSON(event.target.value)} rows={15} />
        <Group position="right" mt="xs">
          <Button onClick={handleSaveCalendarClick} color="green">Save Calendar</Button>
        </Group>
      </Paper>

      {isLoading || isLoadingRecords ? (
        <LoadingOverlay visible={true} overlayBlur={2} />
      ) : isError || isErrorRecords ? (
        <Alert severity="error">{errorMessage(error)}</Alert>
      ) : (
        <>
          <Title order={4} mt={20}>History</Title>
          <Table striped highlightRowOnHover>
            <Thead>
              <Tr>
                <Th>Date</Th>
                <Th>Details</Th>
              </Tr>
            </Thead>
            <Tbody>
              {history.map((record, index) => (
                <Tr key={index}>
                  <Td>{new Date(record.date).toLocaleDateString()}</Td>
                  <Td>{record.details}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>

          <Title order={4} mt={20}>Notifications</Title>
          <Table striped highlightRowOnHover>
            <Thead>
              <Tr>
                <Th>Title</Th>
                <Th>Description</Th>
                <Th>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {notifications.map((notification, index) => (
                <Tr key={index}>
                  <Td>{notification.title}</Td>
                  <Td>{notification.description}</Td>
                  <Td>{notification.status}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </>
      )}
    </Container>
  );
};

export default LeaveAdminPage;

```


### Repository file client/src/modules/leave_elm/api.ts
```
import type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";
export type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";


import { http } from '../../lib/http';




export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


END OF REFERENCES

CURRENT TASK

Fix only TypeScript/import/library interface errors in the existing file, returning its complete raw source. Remove unused Next router import/variable and unused http import. Add useState, named PageHeader, errorMessage and getConfiguration/saveConfiguration/getRecords plus type Configuration imports from existing paths. Mantine7 uses Textarea, Table.Thead/Table.Tbody/Table.Tr/Table.Th/Table.Td, Group justify, LoadingOverlay overlayProps={{blur:2}}, Alert color="red", Table highlightOnHover. ReactQuery5 useQuery({queryKey:[...],queryFn:existing_callback}); map result property names with aliases isLoading:isLoadingRecords etc. Annotate mutationFn(newData:Configuration). Adapt missing state setters to typed useState<Record<string,any>[]>([]) for history and notifications, removing existing const arrays. Preserve payloads, HTTP calls, field assumptions (record.date/details, notification.title/description/status), dialogs and effects; do not correct business logic or audit requirements. Remove unused imports required by noUnusedLocals. Do not rewrite or add features. No workflow/business fixes. Close all JSX.

Output file: client/src/modules/leave_elm/pages/LeaveAdminPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 034 Compiler interface repair MyLeavePage

UTC: 2026-10-12T14:19:02.279440+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/pages/MyLeavePage.tsx
```


import { useEffect } from 'react';
import { Button, Grid, Input, Select, Textarea, Title, Tooltip } from '@mantine/core';
import { useForm } from 'react-hook-form';
import { useQuery, useQueryClient } from 'react-query';

import { ListApplicationsResponse, SubmitApplicationRequest } from '../api';

const MyLeavePage = () => {
  const queryClient = useQueryClient();
  const [applicationData, setApplicationData] = useForm<SubmitApplicationRequest>({
    defaultValues: {
      leave_type: '',
      start_date: '',
      end_date: '',
      purpose: ''
    }
  });

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const applications = await listApplications();
        console.log('Applications:', applications);
      } catch (error) {
        console.error('Error fetching applications:', error);
      }
    };

    fetchApplications();
  }, []);

  return (
    <Grid>
      <Grid.Col span={12}>
        <Title order={3}>Your Leave Applications</Title>
        <Textarea value={JSON.stringify(queryClient.getQueryData<ListApplicationsResponse>(['applications']), null, 2)} />
      </Grid.Col>

      <Grid.Col span={6}>
        <Title order={4}>New Application Form</Title>
        <form onSubmit={handleSubmit((data) => submitApplication(data))}>
          <Input
            label="Start Date"
            type="date"
            {...register('start_date')}
          />

          <Input
            label="End Date"
            type="date"
            {...register('end_date')}
          />

          <Select
            label="Leave Type"
            placeholder="Choose a leave type"
            data={[
              { value: 'vacation', label: 'Vacation' },
              { value: 'sick_leave', label: 'Sick Leave' },
              // Add more options as needed
            ]}
            {...register('leave_type')}
          />

          <Textarea
            label="Purpose"
            {...register('purpose')}
          />

          <Button type="submit">Submit Application</Button>
        </form>
      </Grid.Col>

      {/* Render application actions here */}
    </Grid>
  );
};

export default MyLeavePage;

```


### Repository file client/src/modules/leave_elm/api.ts
```
import type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";
export type { LeaveApplication, LeaveBalance, LeaveTask, LeaveHistory, LeaveNotification } from "./types";


import { http } from '../../lib/http';




export interface Configuration {
  policy?: Record<string, unknown>[];
  calendar?: Record<string, unknown>[];
}

export interface NewApplication {
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export async function listApplications(): Promise<LeaveApplication[]> {
  const response = await http.get('/leave/applications');
  return response.data as LeaveApplication[];
}

export async function listBalances(): Promise<LeaveBalance[]> {
  const response = await http.get('/leave/balances');
  return response.data as LeaveBalance[];
}

export async function listTasks(): Promise<LeaveTask[]> {
  const response = await http.get('/leave/tasks');
  return response.data as LeaveTask[];
}

export async function submitApplication(data: NewApplication): Promise<void> {
  await http.post('/leave/applications', data);
}

export async function applicationAction(id: number, action: string, data: Record<string, unknown>): Promise<void> {
  await http.post(`/leave/applications/${id}/action`, { action, data });
}

export async function getConfiguration(): Promise<Configuration> {
  const response = await http.get('/leave/configuration');
  return response.data as Configuration;
}

export async function saveConfiguration(data: Configuration): Promise<void> {
  await http.post('/leave/configuration', data);
}

export async function getRecords(): Promise<{ history?: LeaveHistory[], notifications?: LeaveNotification[] }> {
  const response = await http.get('/leave/records');
  return response.data as { history?: LeaveHistory[], notifications?: LeaveNotification[] };
}

```


END OF REFERENCES

CURRENT TASK

Repair only the existing React/TypeScript/library interfaces; preserve JSX, options and HTTP behavior. Return complete raw source. Install react-hook-form is done. Correct react-query import to @tanstack/react-query, remove unused useQuery and Tooltip. Add api imports listApplications,submitApplication and type LeaveApplication,NewApplication. ListApplicationsResponse is LeaveApplication[]. SubmitApplicationRequest is Omit<NewApplication,"leave_type"> & {leave_type:string}, preserving existing string defaults and vacation/sick_leave choices. useForm returns object: const {handleSubmit,register,setValue}=useForm<SubmitApplicationRequest>({defaultValues:existing}). Replace Mantine Input with TextInput for label prop. In Select only, replace {...register("leave_type")} with onChange={value => setValue("leave_type",value ?? "")}, adapting Mantine select string callback. handleSubmit sends data via submitApplication(data as unknown as NewApplication), preserving current payload string value rather than introducing new values. Do not correct categories, cache behavior or backend logic. No features added.

Output file: client/src/modules/leave_elm/pages/MyLeavePage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 035 Generate module documentation

UTC: 2026-10-12T14:21:41.645541+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1900, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen-trial/observed-results.json
```
{
  "model": "qwen2.5-coder:3b",
  "model_details": {
    "parent_model": "",
    "format": "gguf",
    "family": "qwen2",
    "families": [
      "qwen2"
    ],
    "parameter_size": "3.1B",
    "quantization_level": "Q4_K_M"
  },
  "ollama_version": {
    "version": "0.40.3"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "hardware": [
    {
      "machine_model": "Mac16,12",
      "chip_type": "Apple M4",
      "number_processors": "proc 10:0:4:6",
      "physical_memory": "16 GB"
    }
  ],
  "os": "ProductName:\t\tmacOS\nProductVersion:\t\t27.0.1\nBuildVersion:\t\t26A434",
  "trial_count": 1,
  "generation_requests": 34,
  "generation_seconds": 1734.58,
  "generation_failures_length": 5,
  "requests": [
    {
      "prompt": "001",
      "label": "Backend foundation",
      "wall_seconds": 402.12,
      "input_tokens": 19203,
      "output_tokens": 8192,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "002",
      "label": "Retry foundation: compact models only",
      "wall_seconds": 77.81,
      "input_tokens": 12714,
      "output_tokens": 1351,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/models.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "003",
      "label": "App, domain, registry and contracts",
      "wall_seconds": 312.32,
      "input_tokens": 15261,
      "output_tokens": 6000,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": {
        "utc": "2026-10-12T13:39:31.408238+00:00",
        "reason": "Truncated final contracts.py JSON string; recovered only preceding complete JSON string values without modifying source content",
        "paths": [
          "modules/leave_elm/__init__.py",
          "modules/leave_elm/apps.py",
          "modules/leave_elm/domain/__init__.py",
          "modules/leave_elm/domain/policy.py",
          "modules/leave_elm/registry.py"
        ],
        "sha256": {
          "modules/leave_elm/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "modules/leave_elm/apps.py": "723ef6145d3a874ec8aab1996772dd7582f75e036547f02c57aa9b41fd77a4b5",
          "modules/leave_elm/domain/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "modules/leave_elm/domain/policy.py": "9a7886bacbed715d23b86737c7304c3b2445b9fc6acee03d42706d33be2b99a9",
          "modules/leave_elm/registry.py": "78e3f2cb6be4d5d8a66be789f0370d6c013fe58d8e565ff928addf78a709027d"
        }
      }
    },
    {
      "prompt": "004",
      "label": "Small contracts file after truncated output",
      "wall_seconds": 6.15,
      "input_tokens": 1466,
      "output_tokens": 130,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/contracts.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "005",
      "label": "Backend services and selectors",
      "wall_seconds": 334.38,
      "input_tokens": 16730,
      "output_tokens": 6500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "006",
      "label": "Correct Fusion registry interface",
      "wall_seconds": 13.22,
      "input_tokens": 4560,
      "output_tokens": 100,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/registry.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "007",
      "label": "Focused initial leave service",
      "wall_seconds": 110.63,
      "input_tokens": 6689,
      "output_tokens": 3500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "008",
      "label": "Retry registry with current task after references",
      "wall_seconds": 27.41,
      "input_tokens": 4585,
      "output_tokens": 692,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/registry.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "009",
      "label": "Focused initial leave service with current task last",
      "wall_seconds": 113.31,
      "input_tokens": 6095,
      "output_tokens": 3500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "010",
      "label": "Small leave query service with repetition control",
      "wall_seconds": 11.42,
      "input_tokens": 2499,
      "output_tokens": 198,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/queries.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "011",
      "label": "Correct pure domain module placement",
      "wall_seconds": 6.05,
      "input_tokens": 2742,
      "output_tokens": 113,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/domain/policy.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "012",
      "label": "Initial application creation service",
      "wall_seconds": 9.37,
      "input_tokens": 2676,
      "output_tokens": 297,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/applications.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "013",
      "label": "Initial application actions service",
      "wall_seconds": 46.28,
      "input_tokens": 5558,
      "output_tokens": 1264,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/actions.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "014",
      "label": "Initial API serializer interfaces",
      "wall_seconds": 7.32,
      "input_tokens": 1474,
      "output_tokens": 289,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/serializers.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "015",
      "label": "Initial employee and action API views",
      "wall_seconds": 19.64,
      "input_tokens": 3086,
      "output_tokens": 519,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/views.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "016",
      "label": "Initial configuration API views",
      "wall_seconds": 13.54,
      "input_tokens": 2142,
      "output_tokens": 485,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/configuration.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "017",
      "label": "API URL interface registration",
      "wall_seconds": 5.18,
      "input_tokens": 258,
      "output_tokens": 212,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/urls.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "018",
      "label": "Repair configuration syntax and Fusion permission interfaces",
      "wall_seconds": 14.06,
      "input_tokens": 1185,
      "output_tokens": 514,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/configuration.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "019",
      "label": "Initial scheduled ELM events",
      "wall_seconds": 14.65,
      "input_tokens": 1575,
      "output_tokens": 592,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/events.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "020",
      "label": "Scheduled task and worker registration",
      "wall_seconds": 7.47,
      "input_tokens": 1349,
      "output_tokens": 207,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/tasks.py",
        "modules/leave_elm/schedule.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "021",
      "label": "Missing record serializer interface definitions",
      "wall_seconds": 2.51,
      "input_tokens": 252,
      "output_tokens": 97,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/record_serializers.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "022",
      "label": "Repair incomplete Celery schedule configuration",
      "wall_seconds": 4.51,
      "input_tokens": 318,
      "output_tokens": 174,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/schedule.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "023",
      "label": "Initial typed frontend API client",
      "wall_seconds": 14.79,
      "input_tokens": 1850,
      "output_tokens": 468,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/api.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "024",
      "label": "Initial employee leave page",
      "wall_seconds": 24.01,
      "input_tokens": 1367,
      "output_tokens": 921,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "025",
      "label": "Initial leave work queue page",
      "wall_seconds": 10.09,
      "input_tokens": 1337,
      "output_tokens": 318,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "026",
      "label": "Repair incomplete employee page React interfaces",
      "wall_seconds": 7.98,
      "input_tokens": 797,
      "output_tokens": 319,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "027",
      "label": "Repair incomplete employee page React interfaces raw source",
      "wall_seconds": 12.13,
      "input_tokens": 707,
      "output_tokens": 470,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "028",
      "label": "Initial leave work queue page raw source",
      "wall_seconds": 13.4,
      "input_tokens": 1247,
      "output_tokens": 505,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "029",
      "label": "Initial leave configuration page raw source",
      "wall_seconds": 24.11,
      "input_tokens": 1241,
      "output_tokens": 1034,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveAdminPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "030",
      "label": "Frontend route registration",
      "wall_seconds": 2.81,
      "input_tokens": 149,
      "output_tokens": 110,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/routes.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "031",
      "label": "Frontend response type interfaces",
      "wall_seconds": 4.19,
      "input_tokens": 203,
      "output_tokens": 167,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/types.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "032",
      "label": "Compiler interface repair LeaveTasksPage",
      "wall_seconds": 14.34,
      "input_tokens": 1170,
      "output_tokens": 522,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "033",
      "label": "Compiler interface repair LeaveAdminPage",
      "wall_seconds": 33.92,
      "input_tokens": 1756,
      "output_tokens": 1293,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveAdminPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "034",
      "label": "Compiler interface repair MyLeavePage",
      "wall_seconds": 13.46,
      "input_tokens": 1180,
      "output_tokens": 477,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    }
  ],
  "checks": [
    {
      "label": "Foundation Python compilation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.12
    },
    {
      "label": "Foundation Python compilation after batch recovery",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.06
    },
    {
      "label": "Django foundation import and registration",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.45
    },
    {
      "label": "Django registration after mixin inheritance correction",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.59
    },
    {
      "label": "Generate schema migration from Qwen models",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "leave_elm",
        "--noinput"
      ],
      "wall_seconds": 0.27
    },
    {
      "label": "Django model registration after related-name correction",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.63
    },
    {
      "label": "Generate schema migration from registered Qwen models",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "leave_elm",
        "--noinput"
      ],
      "wall_seconds": 0.43
    },
    {
      "label": "backend-import-registration",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.53
    },
    {
      "label": "backend-api-imports",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.38
    },
    {
      "label": "backend-api-imports-corrected",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.3
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.03
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "migrate",
        "--noinput"
      ],
      "wall_seconds": 0.39
    },
    {
      "label": "schema-model-drift",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run"
      ],
      "wall_seconds": 0.34
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "migrate",
        "--noinput"
      ],
      "wall_seconds": 0.96
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "seed_modules"
      ],
      "wall_seconds": 0.25
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/no_cross_module_fk.py"
      ],
      "wall_seconds": 0.15
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/lint-imports"
      ],
      "wall_seconds": 0.16
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.49
    },
    {
      "label": "frontend-after-interface-retries",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.33
    },
    {
      "label": "frontend-current-typecheck",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.26
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.18
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/nav_matches_routes.py"
      ],
      "wall_seconds": 0.17
    },
    {
      "label": "frontend-production-build",
      "returncode": 0,
      "command": [
        "npm",
        "run",
        "build"
      ],
      "wall_seconds": 3.56
    }
  ],
  "validation_scope": "Build/integration only. No functional, BR, security, missing-requirement, maintainability or optimization review. User requested bugs be retained. No deliberate mistakes inserted. Full temporary SQLite migration fails existing Placement0009 missing document_profile_idx; isolated ELM migration passes. PostgreSQL unverified."
}

```


### Repository file modules/leave_elm/api/urls.py
```

from django.urls import path
from .views import ApplicationListView, BalanceListView, TaskListView, ApplicationActionView
from .configuration import ConfigurationView, RecordListView

urlpatterns = [
    path('applications', ApplicationListView.as_view(), name='application-list'),
    path('balances', BalanceListView.as_view(), name='balance-list'),
    path('tasks', TaskListView.as_view(), name='task-list'),
    path('applications/<int:pk>/action', ApplicationActionView.as_view(), name='application-action'),
    path('configuration', ConfigurationView.as_view(), name='configuration-view'),
    path('records', RecordListView.as_view(), name='record-list'),
]

```


### Repository file modules/leave_elm/registry.py
```
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.application.review", "leave_elm.application.approve"],
    "reviewer": ["leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.review", "leave_elm.application.approve", "leave_elm.substitute.respond"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}

SYSTEM_PERMISSIONS = [
    "leave_elm.application.approve",
    "leave_elm.application.review",
    "leave_elm.application.create",
    "leave_elm.application.view_self",
    "leave_elm.substitute.respond",
    "leave_elm.task.view",
    "leave_elm.configuration.manage",
    "leave_elm.record.manage",
]

```


END OF REFERENCES

CURRENT TASK

Write concise README.md in Markdown for the generated ELM module, max100 lines. Describe actual file structure, existing route paths and mechanical integration setup, not requirements compliance. Explain use existing Fusion auth/config/DB; python manage.py migrate, seed_modules and client npm run build are integration commands. State only build/structural checks performed and workflow correctness unverified; preserve bugs, no functional/security audit. Do not claim API operations work or requirements complete. Link evidence directory ../../docs/08-delivery/elm-qwen-trial for logs and exact check commands. Do not put author/model labels in module documentation. No invented test results, roll numbers, successful server run or seeded data. Return Markdown only.

Output file: modules/leave_elm/README.md
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 036 Generate genuine local-model trial record

UTC: 2026-10-12T14:23:08.221372+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3600, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen-trial/observed-results.json
```
{
  "model": "qwen2.5-coder:3b",
  "model_details": {
    "parent_model": "",
    "format": "gguf",
    "family": "qwen2",
    "families": [
      "qwen2"
    ],
    "parameter_size": "3.1B",
    "quantization_level": "Q4_K_M"
  },
  "ollama_version": {
    "version": "0.40.3"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "hardware": [
    {
      "machine_model": "Mac16,12",
      "chip_type": "Apple M4",
      "number_processors": "proc 10:0:4:6",
      "physical_memory": "16 GB"
    }
  ],
  "os": "ProductName:\t\tmacOS\nProductVersion:\t\t27.0.1\nBuildVersion:\t\t26A434",
  "trial_count": 1,
  "generation_requests": 34,
  "generation_seconds": 1734.58,
  "generation_failures_length": 5,
  "requests": [
    {
      "prompt": "001",
      "label": "Backend foundation",
      "wall_seconds": 402.12,
      "input_tokens": 19203,
      "output_tokens": 8192,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "002",
      "label": "Retry foundation: compact models only",
      "wall_seconds": 77.81,
      "input_tokens": 12714,
      "output_tokens": 1351,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/models.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "003",
      "label": "App, domain, registry and contracts",
      "wall_seconds": 312.32,
      "input_tokens": 15261,
      "output_tokens": 6000,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": {
        "utc": "2026-10-12T13:39:31.408238+00:00",
        "reason": "Truncated final contracts.py JSON string; recovered only preceding complete JSON string values without modifying source content",
        "paths": [
          "modules/leave_elm/__init__.py",
          "modules/leave_elm/apps.py",
          "modules/leave_elm/domain/__init__.py",
          "modules/leave_elm/domain/policy.py",
          "modules/leave_elm/registry.py"
        ],
        "sha256": {
          "modules/leave_elm/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "modules/leave_elm/apps.py": "723ef6145d3a874ec8aab1996772dd7582f75e036547f02c57aa9b41fd77a4b5",
          "modules/leave_elm/domain/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "modules/leave_elm/domain/policy.py": "9a7886bacbed715d23b86737c7304c3b2445b9fc6acee03d42706d33be2b99a9",
          "modules/leave_elm/registry.py": "78e3f2cb6be4d5d8a66be789f0370d6c013fe58d8e565ff928addf78a709027d"
        }
      }
    },
    {
      "prompt": "004",
      "label": "Small contracts file after truncated output",
      "wall_seconds": 6.15,
      "input_tokens": 1466,
      "output_tokens": 130,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/contracts.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "005",
      "label": "Backend services and selectors",
      "wall_seconds": 334.38,
      "input_tokens": 16730,
      "output_tokens": 6500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "006",
      "label": "Correct Fusion registry interface",
      "wall_seconds": 13.22,
      "input_tokens": 4560,
      "output_tokens": 100,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/registry.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "007",
      "label": "Focused initial leave service",
      "wall_seconds": 110.63,
      "input_tokens": 6689,
      "output_tokens": 3500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "008",
      "label": "Retry registry with current task after references",
      "wall_seconds": 27.41,
      "input_tokens": 4585,
      "output_tokens": 692,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/registry.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "009",
      "label": "Focused initial leave service with current task last",
      "wall_seconds": 113.31,
      "input_tokens": 6095,
      "output_tokens": 3500,
      "done_reason": "length",
      "files_applied": [],
      "recovered_files": null
    },
    {
      "prompt": "010",
      "label": "Small leave query service with repetition control",
      "wall_seconds": 11.42,
      "input_tokens": 2499,
      "output_tokens": 198,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/queries.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "011",
      "label": "Correct pure domain module placement",
      "wall_seconds": 6.05,
      "input_tokens": 2742,
      "output_tokens": 113,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/domain/policy.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "012",
      "label": "Initial application creation service",
      "wall_seconds": 9.37,
      "input_tokens": 2676,
      "output_tokens": 297,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/applications.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "013",
      "label": "Initial application actions service",
      "wall_seconds": 46.28,
      "input_tokens": 5558,
      "output_tokens": 1264,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/actions.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "014",
      "label": "Initial API serializer interfaces",
      "wall_seconds": 7.32,
      "input_tokens": 1474,
      "output_tokens": 289,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/serializers.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "015",
      "label": "Initial employee and action API views",
      "wall_seconds": 19.64,
      "input_tokens": 3086,
      "output_tokens": 519,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/views.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "016",
      "label": "Initial configuration API views",
      "wall_seconds": 13.54,
      "input_tokens": 2142,
      "output_tokens": 485,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/configuration.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "017",
      "label": "API URL interface registration",
      "wall_seconds": 5.18,
      "input_tokens": 258,
      "output_tokens": 212,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/urls.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "018",
      "label": "Repair configuration syntax and Fusion permission interfaces",
      "wall_seconds": 14.06,
      "input_tokens": 1185,
      "output_tokens": 514,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/configuration.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "019",
      "label": "Initial scheduled ELM events",
      "wall_seconds": 14.65,
      "input_tokens": 1575,
      "output_tokens": 592,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/services/events.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "020",
      "label": "Scheduled task and worker registration",
      "wall_seconds": 7.47,
      "input_tokens": 1349,
      "output_tokens": 207,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/tasks.py",
        "modules/leave_elm/schedule.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "021",
      "label": "Missing record serializer interface definitions",
      "wall_seconds": 2.51,
      "input_tokens": 252,
      "output_tokens": 97,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/api/record_serializers.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "022",
      "label": "Repair incomplete Celery schedule configuration",
      "wall_seconds": 4.51,
      "input_tokens": 318,
      "output_tokens": 174,
      "done_reason": "stop",
      "files_applied": [
        "modules/leave_elm/schedule.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "023",
      "label": "Initial typed frontend API client",
      "wall_seconds": 14.79,
      "input_tokens": 1850,
      "output_tokens": 468,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/api.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "024",
      "label": "Initial employee leave page",
      "wall_seconds": 24.01,
      "input_tokens": 1367,
      "output_tokens": 921,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "025",
      "label": "Initial leave work queue page",
      "wall_seconds": 10.09,
      "input_tokens": 1337,
      "output_tokens": 318,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "026",
      "label": "Repair incomplete employee page React interfaces",
      "wall_seconds": 7.98,
      "input_tokens": 797,
      "output_tokens": 319,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "027",
      "label": "Repair incomplete employee page React interfaces raw source",
      "wall_seconds": 12.13,
      "input_tokens": 707,
      "output_tokens": 470,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "028",
      "label": "Initial leave work queue page raw source",
      "wall_seconds": 13.4,
      "input_tokens": 1247,
      "output_tokens": 505,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "029",
      "label": "Initial leave configuration page raw source",
      "wall_seconds": 24.11,
      "input_tokens": 1241,
      "output_tokens": 1034,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveAdminPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "030",
      "label": "Frontend route registration",
      "wall_seconds": 2.81,
      "input_tokens": 149,
      "output_tokens": 110,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/routes.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "031",
      "label": "Frontend response type interfaces",
      "wall_seconds": 4.19,
      "input_tokens": 203,
      "output_tokens": 167,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/types.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "032",
      "label": "Compiler interface repair LeaveTasksPage",
      "wall_seconds": 14.34,
      "input_tokens": 1170,
      "output_tokens": 522,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveTasksPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "033",
      "label": "Compiler interface repair LeaveAdminPage",
      "wall_seconds": 33.92,
      "input_tokens": 1756,
      "output_tokens": 1293,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/LeaveAdminPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "034",
      "label": "Compiler interface repair MyLeavePage",
      "wall_seconds": 13.46,
      "input_tokens": 1180,
      "output_tokens": 477,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/leave_elm/pages/MyLeavePage.tsx"
      ],
      "recovered_files": null
    }
  ],
  "checks": [
    {
      "label": "Foundation Python compilation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.12
    },
    {
      "label": "Foundation Python compilation after batch recovery",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.06
    },
    {
      "label": "Django foundation import and registration",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.45
    },
    {
      "label": "Django registration after mixin inheritance correction",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.59
    },
    {
      "label": "Generate schema migration from Qwen models",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "leave_elm",
        "--noinput"
      ],
      "wall_seconds": 0.27
    },
    {
      "label": "Django model registration after related-name correction",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.63
    },
    {
      "label": "Generate schema migration from registered Qwen models",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "leave_elm",
        "--noinput"
      ],
      "wall_seconds": 0.43
    },
    {
      "label": "backend-import-registration",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.53
    },
    {
      "label": "backend-api-imports",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.38
    },
    {
      "label": "backend-api-imports-corrected",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.3
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/leave_elm"
      ],
      "wall_seconds": 0.03
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "migrate",
        "--noinput"
      ],
      "wall_seconds": 0.39
    },
    {
      "label": "schema-model-drift",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run"
      ],
      "wall_seconds": 0.34
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "migrate",
        "--noinput"
      ],
      "wall_seconds": 0.96
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "seed_modules"
      ],
      "wall_seconds": 0.25
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/no_cross_module_fk.py"
      ],
      "wall_seconds": 0.15
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/lint-imports"
      ],
      "wall_seconds": 0.16
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.49
    },
    {
      "label": "frontend-after-interface-retries",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.33
    },
    {
      "label": "frontend-current-typecheck",
      "returncode": 2,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.26
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0,
      "command": [
        "C:/Users/sachg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        "node_modules/typescript/bin/tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.18
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/nav_matches_routes.py"
      ],
      "wall_seconds": 0.17
    },
    {
      "label": "frontend-production-build",
      "returncode": 0,
      "command": [
        "npm",
        "run",
        "build"
      ],
      "wall_seconds": 3.56
    }
  ],
  "validation_scope": "Build/integration only. No functional, BR, security, missing-requirement, maintainability or optimization review. User requested bugs be retained. No deliberate mistakes inserted. Full temporary SQLite migration fails existing Placement0009 missing document_profile_idx; isolated ELM migration passes. PostgreSQL unverified."
}

```


### Repository file docs/08-delivery/elm-qwen-trial/mechanical-corrections.md
```
# Mechanical integration corrections

Prompt 003 reached its output limit in the final contracts.py string. Complete preceding file strings were decoded and written unchanged; the incomplete file was not applied. See responses/003.recovery.json and the retained raw response.

Registered modules.leave_elm in config/settings/base.py DOMAIN_MODULES. No application business logic was changed.

Removed redundant models.Model inheritance where Fusion TimeStampedModel/UserScopedModel already supply it, resolving the observed Django MRO failure. Added the missing Sequence, LeaveApplication and LeaveBalance imports in contracts.py. No field, calculation, workflow or method body was changed. Exact diff: mechanical-001.patch.

Resolved Django fields.E304 reverse-accessor collisions by adding unique related_name values to approved_by, cancelled_by and extension_approved_by. Foreign-key targets, field names and workflow logic were preserved. Diff: mechanical-002.patch.

Created empty Python package __init__.py files for services, selectors, api and migrations as mechanical package scaffolding. Application logic remains model-generated.

Prompt 010: corrected services-relative model import to modules.leave_elm.models; adapted nonexistent fusion_auth.client.exceptions.PermissionDeniedError to the supplied core.api.exceptions.PermissionDeniedError. Query scopes and permission choices unchanged. Prompt 011: model replaced misplaced duplicate ORM declarations with pure-domain constants, preserving defaults.

Prompt 012: corrected model import and missing PermissionDeniedError import; mapped application:create to the registered leave_elm.application.create interface; adapted async function declaration to the synchronous Django ORM/DRF service calling convention. Submission body, history/task fields and exception handling unchanged.

Prompt 013: corrected relative model import; added existing timezone, timedelta and PermissionDeniedError imports; adapted Principal.user_type to supplied Principal.kind. All action branches, model writes, helper calls and decisions preserved. No functional execution or logic repairs.

Prompt 014: corrected api-relative model import to modules.leave_elm.models. Serializer fields and read-only choices retained.

Prompt 015: corrected api-relative service imports to modules.leave_elm.services. View methods, authentication checks, service choices and response handling retained exactly.

Registered generated backend URL include at /api/v1/leave/ and frontend static module import at /leave in existing platform registries. No service or workflow changes.

Prompt 017: remapped invented URL import locations to the generated .views/.configuration modules and aligned path trailing slashes to Fusion API convention. Prompt 018 did not fix indentation/decorator misuse: removed invalid module-function decorator indentation and adapted class decorators to supplied DRF permission_classes interface, using registered names. Preserved queryset filters, save arguments and function bodies. Missing serializer interfaces requested separately from Qwen.

Prompt 019: corrected service model import; added missing imports for existing timezone, models and generated domain constants; changed malformed multiline f-string delimiters to triple quotes and task escalated token to task.escalated. Event calculations, notification channel, field assumptions and branches unchanged. Tasks were not executed.

Prompt 020: added missing shared_task registration to existing annual wrapper. Schedule response was syntactically incomplete; requesting configuration-only retry with fully qualified worker names.

Prompt 021: corrected api-relative record serializer model import after observed ModuleNotFoundError.

Registered the generated ELM Celery schedule/task routes in config/celery.py via existing merge convention. No tasks invoked.

Prompt 023: corrected frontend http import depth, exported existing client interfaces/functions for generated page imports, and aligned configuration/records URL prefix with registered /api/v1/leave routes. Payload bodies and HTTP method choices retained.

Registered ELM in existing import-linter domain/module/layer structural configuration. This checks imports only.

Prompt 030: remapped missing Mine page import to generated MyLeavePage; type-only RouteObject import; relative route paths for Fusion mounting. Prompt 031: wired model-generated response types into api.ts instead of empty placeholder interfaces, resolving missing type references. Installing react-hook-form@7 dependency used by Qwen employee page; package and lockfile changes are mechanical dependency adjustment.

Prompt 032 corrected http import but retained incompatible tuple/function useMutation and Stack spacing. Host mapped each existing callback to ReactQuery5 {mutate:name}=useMutation({mutationFn:...}) with id type; added missing listTasks/PageHeader imports and Mantine Stack gap. URLs, nested payloads and task.id/title/description assumptions unchanged.

Prompt 033 introduced object JSON editor state/changed parsing and still did not resolve library errors. Restored its saved before-file (original prompt029) and applied compiler interface fixes only: missing imports, ReactQuery5 object calls/result aliases/mutation argument type, React state declaration for existing setter names, Mantine7 component/property names, unused imports. Kept original JSON parsing, payloads, actions, dialogs, record field assumptions and rendering. Record arrays have permissive type annotations only; backend fields not changed.

Prompt 034 corrected dependency/component import names and Select callback but retained invalid useForm destructuring/missing imports. Host adapted useForm object result, imported existing API functions, added type aliases matching generated interfaces and a compile-only request type assertion. Existing string leave_type values, static choices, rendering, cache usage and HTTP request data unchanged.

```


END OF REFERENCES

CURRENT TASK

Write a concise factual TRIAL_RECORD.md in Markdown with sections Configuration, Method, Observed generation results, Build checks, Limits, Reproduce. Use supplied observed-results.json and mechanical-corrections.md exactly. This was one real local Ollama qwen2.5-coder:3b trial, not a simulation; user chose one candidate. Record model size/quant/version, hardware, official Fusion base SHA, API Python runner with streamed prompts and periodic output checks, token-limit/repetition failures and raw-source format switch. Parameters changed across attempts: do not present as controlled comparative benchmark or prove general efficiency. State original raw responses and payloads retained in responses/, exact prompts separately in prompts.md, host mechanical changes in mechanical-corrections.md; no deliberate bugs inserted, functional bugs left, no BR correctness/missing requirement/security/optimization tests. Include actual passing/failing checks, particularly pre-existing PlacementSQLite failure separate from isolated ELM migration. Do not invent functional success, tests, PRs, commits or PostgreSQL runs. Reproduce a request with python devtools/qwen_elm_trial.py generate docs/08-delivery/elm-qwen-trial/jobs/02h-queries-small.json (appends a new log and rewrites that generated file, not identical-run guarantee). Point exact per-call payloads/options/statistics/checks. No broad claims model inefficient. Max150 lines.

Output file: docs/08-delivery/elm-qwen-trial/TRIAL_RECORD.md
Return only complete raw source code, without JSON, explanation or Markdown fences.

