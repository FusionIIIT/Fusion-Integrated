
## Prompt 001 Backend foundation

UTC: 2026-10-12T16:11:34.568159+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 8192}`

REFERENCE MATERIAL ONLY

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


END OF REFERENCES

CURRENT TASK

Implement the Employee Leave Management module inside the supplied Fusion ERP base. This is the first implementation stage, not a code review. Use the provided specification context to generate backend data models, the pure-Python domain definitions/calculations, app configuration, module permissions/navigation/role grants and batched public contracts. Reuse Fusion identity; employee references must be integer IAM user IDs, not Django user foreign keys. Models must contain all data needed by the provided leave workflows, policy/calendar/hierarchy configuration, balances, audit, notifications, SLA and year-end processing. Code package is modules.leave_elm, module code is leave_elm, frontend base is /leave and backend prefix is /api/v1/leave/. Plan three nav paths /leave/mine, /leave/queue, /leave/admin. registry.py is plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label), ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list. Use names from the supplied actor registry. Include faculty and staff grants for employee actions. Do not create login/user models or tests. Return only the foundational files requested; later stages will implement services/API/UI against your definitions. Use only installed Django/standard-library dependencies. Domain must not import Django/DRF/Celery. contracts.py getters must accept sequences. AppConfig name modules.leave_elm, label leave_elm, default_auto_field django.db.models.BigAutoField. All fields should be syntactically valid Django fields. Keep the output compact enough to return all files.

Required output paths:
modules/leave_elm/__init__.py
modules/leave_elm/apps.py
modules/leave_elm/models.py
modules/leave_elm/domain/__init__.py
modules/leave_elm/domain/policy.py
modules/leave_elm/registry.py
modules/leave_elm/contracts.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 002 Complete missing public contracts

UTC: 2026-10-12T16:23:16.358481+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 1800}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
"""Leave Management data models.

All fields are syntactically valid Django fields. Models contain all data needed
by the provided leave workflows, policy/calendar/hierarchy configuration,
balances, audit, notifications, SLA and year-end processing.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel

LeaveCategory = Literal[
    "CL",  # Casual Leave
    "RH",  # Restricted Holiday
    "SCL", # Special Casual Leave
    "EL",  # Earned Leave
    "COL", # Commuted Leave
    "VL",  # Vacation Leave
]

LeaveStatus = Literal[
    "DRAFT",
    "AWAITING_SUBSTITUTE",
    "AWAITING_UNIT_HEAD",
    "AWAITING_ESTABLISHMENT",
    "AWAITING_FINAL_SANCTION",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "EXTENSION_PENDING",
    "EXTENDED",
    "RESUMPTION_PENDING",
    "RESUMPTION_REVIEWED",
    "WITHDRAWN",
]

ResumptionType = Literal["NORMAL", "EARLY", "LATE"]


class LeavePolicy(TimeStampedModel):
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    CL_DAYS = models.IntegerField(default=8, verbose_name="Casual Leave days")
    RH_DAYS = models.IntegerField(default=2, verbose_name="Restricted Holiday days")
    SCL_MAX_DAYS = models.IntegerField(default=15, verbose_name="Special Casual Leave max days")
    EL_DAYS = models.IntegerField(default=30, verbose_name="Earned Leave days (non-faculty)")
    COL_DAYS = models.IntegerField(default=20, verbose_name="Commuted Leave days")
    VL_DAYS = models.IntegerField(default=60, verbose_name="Vacation Leave days (faculty)")
    VL_TO_EL_RATIO = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal("0.5"), verbose_name="VL to EL conversion ratio (2:1)")

    class Meta:
        verbose_name = "Leave Policy"
        verbose_name_plural = "Leave Policies"


class HolidayCalendar(TimeStampedModel):
    """Currently effective published holiday/RH calendar."""
    year = models.IntegerField(unique=True, verbose_name="Year")
    is_effective = models.BooleanField(default=False, verbose_name="Is currently effective")
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")

    class Meta:
        verbose_name = "Holiday Calendar"
        ordering = ["-year"]


class Holiday(TimeStampedModel):
    """Individual holiday or Restricted Holiday entry."""
    calendar = models.ForeignKey(
        "HolidayCalendar",
        on_delete=models.CASCADE,
        related_name="holidays",
        verbose_name="Calendar",
    )
    date = models.DateField(unique=True, verbose_name="Date")
    type = models.CharField(max_length=20, choices=[("HOLIDAY", "Holiday"), ("RH", "Restricted Holiday")], verbose_name="Type")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    class Meta:
        verbose_name = "Holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_calendar_date")
        ]


class VacationPeriod(TimeStampedModel):
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year = models.IntegerField(verbose_name="Year")
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    name = models.CharField(max_length=100, verbose_name="Name")

    class Meta:
        verbose_name = "Vacation Period"
        ordering = ["year", "start_date"]


class OrganizationalUnit(TimeStampedModel):
    """Department, Section, or Office."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    name = models.CharField(max_length=200, verbose_name="Name")
    parent_unit_id = models.IntegerField(null=True, blank=True, verbose_name="Parent unit ID", db_index=True)
    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")

    class Meta:
        verbose_name = "Organizational Unit"
        ordering = ["code"]


class LeaveHierarchy(TimeStampedModel):
    """Configured hierarchy for leave sanctioning paths."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        verbose_name = "Leave Hierarchy"
        ordering = ["name"]


class LeaveHierarchyStep(TimeStampedModel):
    """Step in a leave sanctioning hierarchy."""
    hierarchy = models.ForeignKey(
        "LeaveHierarchy",
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Hierarchy",
    )
    order = models.IntegerField(verbose_name="Order")
    role_code = models.CharField(max_length=50, verbose_name="Role code")
    is_establishment_step = models.BooleanField(default=False, verbose_name="Is establishment step")

    class Meta:
        verbose_name = "Hierarchy Step"
        ordering = ["hierarchy", "order"]
        constraints = [
            models.UniqueConstraint(fields=["hierarchy", "order"], name="unique_hierarchy_order")
        ]


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave application record.

Not modified in place after submission. Changes require withdrawal and new application.
"""
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_FINAL_SANCTION", "Awaiting Final Sanction Decision"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("EXTENSION_PENDING", "Extension Pending"),
        ("EXTENDED", "Extended"),
        ("RESUMPTION_PENDING", "Resumption Pending"),
        ("RESUMPTION_REVIEWED", "Resumption Reviewed"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    category = models.CharField(max_length=2, choices=[
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ], verbose_name="Leave Category")

    user_id = models.IntegerField(db_index=True, verbose_name="Applicant user ID")

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    purpose = models.TextField(verbose_name="Purpose/Reason")
    station_leave_required = models.BooleanField(default=False, verbose_name="Station Leave Required")
    station_leave_details = models.JSONField(blank=True, default=dict, verbose_name="Station Leave Details")

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Substitute user ID")
    substitute_consent_given = models.BooleanField(default=False, verbose_name="Substitute Consent Given")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT", verbose_name="Status")

    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")
    hierarchy_step_order = models.IntegerField(verbose_name="Hierarchy Step Order")

    final_decision_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Final Decision User ID")
    final_decision_date = models.DateField(null=True, blank=True, verbose_name="Final Decision Date")
    final_decision_type = models.CharField(max_length=20, choices=[
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ], null=True, blank=True, verbose_name="Final Decision Type")

    # Extension fields
    original_application_id = models.IntegerField(null=True, blank=True, verbose_name="Original Application ID")
    extension_incremental_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Extension Incremental Days")

    # Resumption fields
    actual_resumption_date = models.DateField(null=True, blank=True, verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], null=True, blank=True, verbose_name="Resumption Type")

    # Audit fields
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")
    updated_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Updated by user ID")
    submitted_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Submitted by user ID")
    withdrawn_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Withdrawn by user ID")
    cancelled_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Cancelled by user ID")

    class Meta:
        verbose_name = "Leave Application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="idx_leave_user_status"),
            models.Index(fields=["start_date", "end_date"], name="idx_leave_dates"),
        ]

    def __str__(self):
        return f"{self.category} {self.start_date} to {self.end_date} ({self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Employee leave balance snapshot.

Maintained per employee. Updated on approval, cancellation, year-end processing,
and VL-to-EL conversion.
"""
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")
    effective_date = models.DateField(verbose_name="Effective Date", db_index=True)

    cl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="CL Balance")
    rh_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="RH Balance")
    scl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="SCL Balance")
    el_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="EL Balance")
    col_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="COL Balance")
    vl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="VL Balance (faculty only)")

    class Meta:
        verbose_name = "Leave Balance"
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["user_id", "effective_date"], name="idx_balance_user_date"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.effective_date}: CL={self.cl_balance}, EL={self.el_balance}, COL={self.col_balance}, VL={self.vl_balance}"


class LeaveTransaction(TimeStampedModel, UserScopedModel):
    """Leave account transaction record.

Records all balance changes: approvals, cancellations, year-end lapses/conversions,
extensions, and resumption adjustments.
"""
    TRANSACTION_TYPE_CHOICES = [
        ("APPROVAL", "Approval"),
        ("CANCELLATION", "Cancellation"),
        ("YEAR_END_LAPSE", "Year End Lapse"),
        ("YEAR_END_CONVERSION", "Year End Conversion"),
        ("EXTENSION_APPROVAL", "Extension Approval"),
        ("RESUMPTION_ADJUSTMENT", "Resumption Adjustment"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Related Application",
        null=True,
        blank=True,
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Transaction Type")
    category = models.CharField(max_length=2, verbose_name="Leave Category")
    quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Quantity")
    balance_before = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance Before")
    balance_after = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance After")

    reference_application_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Application ID")
    reference_transaction_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Transaction ID")

    processed_by_user_id = models.IntegerField(db_index=True, verbose_name="Processed by user ID")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="Processed At")

    class Meta:
        verbose_name = "Leave Transaction"
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["user_id", "transaction_type"], name="idx_txn_user_type"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.transaction_type} {self.category}: {self.quantity}"


class WorkflowTask(TimeStampedModel, UserScopedModel):
    """Actionable workflow task with SLA tracking.

Used for Unit Head review, Establishment routing, Final Sanction, and SLA reminders/escalations.
"""
    TASK_TYPE_CHOICES = [
        ("UNIT_HEAD_REVIEW", "Unit Head Review"),
        ("ESTABLISHMENT_ROUTING", "Establishment Routing"),
        ("FINAL_SANCTION", "Final Sanction"),
        ("RESUMPTION_REVIEW", "Resumption Review"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Related Application",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="Task Type")

    assigned_to_user_id = models.IntegerField(db_index=True, verbose_name="Assigned to user ID")
    role_code = models.CharField(max_length=50, verbose_name="Role Code")

    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("COMPLETED", "Completed")], default="PENDING", verbose_name="Status")

    reminder_threshold_seconds = models.IntegerField(default=3600, verbose_name="Reminder Threshold (seconds)")
    escalation_threshold_seconds = models.IntegerField(default=7200, verbose_name="Escalation Threshold (seconds)")

    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Reminder Sent")
    last_escalation_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Escalation Sent")

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    completed_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Completed by user ID")

    class Meta:
        verbose_name = "Workflow Task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to_user_id", "status"], name="idx_task_assigned_status"),
            models.Index(fields=["application", "status"], name="idx_task_app_status"),
        ]

    def __str__(self):
        return f"{self.application} {self.task_type} for {self.assigned_to_user_id}"


class SLAEventLog(TimeStampedModel, UserScopedModel):
    """SLA reminder and escalation event log."""
    EVENT_TYPE_CHOICES = [
        ("REMINDER", "Reminder"),
        ("ESCALATION", "Escalation"),
    ]

    task = models.ForeignKey(
        "WorkflowTask",
        on_delete=models.CASCADE,
        related_name="sla_events",
        verbose_name="Related Task",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name="Event Type")

    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Triggered At")
    threshold_seconds = models.IntegerField(verbose_name="Threshold (seconds)")
    message = models.TextField(verbose_name="Message")

    class Meta:
        verbose_name = "SLA Event Log"
        ordering = ["-triggered_at"]


class ResumptionRecord(TimeStampedModel, UserScopedModel):
    """Resumption record for EL/COL/VL.

Captures actual return date and details reviewed by Sanctioning Authority.
"""
    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="resumptions",
        verbose_name="Related Application",
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    actual_resumption_date = models.DateField(verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], verbose_name="Resumption Type")

    reviewed_by_user_id = models.IntegerField(db_index=True, verbose_name="Reviewed by user ID")
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name="Reviewed At")

    balance_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Balance Adjustment")

    class Meta:
        verbose_name = "Resumption Record"
        ordering = ["-reviewed_at"]

```


END OF REFERENCES

CURRENT TASK

Generate only contracts.py for the existing new ELM foundation. Maximum75 lines. Provide plural module-level getters get_leave_applications(user_ids:Sequence[int]) and get_leave_balances(user_ids:Sequence[int]) using the exact existing Django model names and owner fields. Return dictionaries or grouped values appropriate for batched IAM-user lookup. Import own models; use collections.abc.Sequence. Do not change models/domain/registry or add workflow algorithms. Keep it concise and complete. The prior output truncated before completing this file.

Output file: modules/leave_elm/contracts.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 003 Backend services and selectors

UTC: 2026-10-12T16:25:04.985480+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128, "num_predict": 6500}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen35-9b-trial/specification-context-compact.md
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
"""Leave Management data models.

All fields are syntactically valid Django fields. Models contain all data needed
by the provided leave workflows, policy/calendar/hierarchy configuration,
balances, audit, notifications, SLA and year-end processing.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel

LeaveCategory = Literal[
    "CL",  # Casual Leave
    "RH",  # Restricted Holiday
    "SCL", # Special Casual Leave
    "EL",  # Earned Leave
    "COL", # Commuted Leave
    "VL",  # Vacation Leave
]

LeaveStatus = Literal[
    "DRAFT",
    "AWAITING_SUBSTITUTE",
    "AWAITING_UNIT_HEAD",
    "AWAITING_ESTABLISHMENT",
    "AWAITING_FINAL_SANCTION",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "EXTENSION_PENDING",
    "EXTENDED",
    "RESUMPTION_PENDING",
    "RESUMPTION_REVIEWED",
    "WITHDRAWN",
]

ResumptionType = Literal["NORMAL", "EARLY", "LATE"]


class LeavePolicy(TimeStampedModel):
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    CL_DAYS = models.IntegerField(default=8, verbose_name="Casual Leave days")
    RH_DAYS = models.IntegerField(default=2, verbose_name="Restricted Holiday days")
    SCL_MAX_DAYS = models.IntegerField(default=15, verbose_name="Special Casual Leave max days")
    EL_DAYS = models.IntegerField(default=30, verbose_name="Earned Leave days (non-faculty)")
    COL_DAYS = models.IntegerField(default=20, verbose_name="Commuted Leave days")
    VL_DAYS = models.IntegerField(default=60, verbose_name="Vacation Leave days (faculty)")
    VL_TO_EL_RATIO = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal("0.5"), verbose_name="VL to EL conversion ratio (2:1)")

    class Meta:
        verbose_name = "Leave Policy"
        verbose_name_plural = "Leave Policies"


class HolidayCalendar(TimeStampedModel):
    """Currently effective published holiday/RH calendar."""
    year = models.IntegerField(unique=True, verbose_name="Year")
    is_effective = models.BooleanField(default=False, verbose_name="Is currently effective")
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")

    class Meta:
        verbose_name = "Holiday Calendar"
        ordering = ["-year"]


class Holiday(TimeStampedModel):
    """Individual holiday or Restricted Holiday entry."""
    calendar = models.ForeignKey(
        "HolidayCalendar",
        on_delete=models.CASCADE,
        related_name="holidays",
        verbose_name="Calendar",
    )
    date = models.DateField(unique=True, verbose_name="Date")
    type = models.CharField(max_length=20, choices=[("HOLIDAY", "Holiday"), ("RH", "Restricted Holiday")], verbose_name="Type")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    class Meta:
        verbose_name = "Holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_calendar_date")
        ]


class VacationPeriod(TimeStampedModel):
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year = models.IntegerField(verbose_name="Year")
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    name = models.CharField(max_length=100, verbose_name="Name")

    class Meta:
        verbose_name = "Vacation Period"
        ordering = ["year", "start_date"]


class OrganizationalUnit(TimeStampedModel):
    """Department, Section, or Office."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    name = models.CharField(max_length=200, verbose_name="Name")
    parent_unit_id = models.IntegerField(null=True, blank=True, verbose_name="Parent unit ID", db_index=True)
    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")

    class Meta:
        verbose_name = "Organizational Unit"
        ordering = ["code"]


class LeaveHierarchy(TimeStampedModel):
    """Configured hierarchy for leave sanctioning paths."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        verbose_name = "Leave Hierarchy"
        ordering = ["name"]


class LeaveHierarchyStep(TimeStampedModel):
    """Step in a leave sanctioning hierarchy."""
    hierarchy = models.ForeignKey(
        "LeaveHierarchy",
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Hierarchy",
    )
    order = models.IntegerField(verbose_name="Order")
    role_code = models.CharField(max_length=50, verbose_name="Role code")
    is_establishment_step = models.BooleanField(default=False, verbose_name="Is establishment step")

    class Meta:
        verbose_name = "Hierarchy Step"
        ordering = ["hierarchy", "order"]
        constraints = [
            models.UniqueConstraint(fields=["hierarchy", "order"], name="unique_hierarchy_order")
        ]


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave application record.

Not modified in place after submission. Changes require withdrawal and new application.
"""
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_FINAL_SANCTION", "Awaiting Final Sanction Decision"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("EXTENSION_PENDING", "Extension Pending"),
        ("EXTENDED", "Extended"),
        ("RESUMPTION_PENDING", "Resumption Pending"),
        ("RESUMPTION_REVIEWED", "Resumption Reviewed"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    category = models.CharField(max_length=3, choices=[
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ], verbose_name="Leave Category")

    user_id = models.IntegerField(db_index=True, verbose_name="Applicant user ID")

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    purpose = models.TextField(verbose_name="Purpose/Reason")
    station_leave_required = models.BooleanField(default=False, verbose_name="Station Leave Required")
    station_leave_details = models.JSONField(blank=True, default=dict, verbose_name="Station Leave Details")

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Substitute user ID")
    substitute_consent_given = models.BooleanField(default=False, verbose_name="Substitute Consent Given")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT", verbose_name="Status")

    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")
    hierarchy_step_order = models.IntegerField(verbose_name="Hierarchy Step Order")

    final_decision_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Final Decision User ID")
    final_decision_date = models.DateField(null=True, blank=True, verbose_name="Final Decision Date")
    final_decision_type = models.CharField(max_length=20, choices=[
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ], null=True, blank=True, verbose_name="Final Decision Type")

    # Extension fields
    original_application_id = models.IntegerField(null=True, blank=True, verbose_name="Original Application ID")
    extension_incremental_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Extension Incremental Days")

    # Resumption fields
    actual_resumption_date = models.DateField(null=True, blank=True, verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], null=True, blank=True, verbose_name="Resumption Type")

    # Audit fields
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")
    updated_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Updated by user ID")
    submitted_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Submitted by user ID")
    withdrawn_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Withdrawn by user ID")
    cancelled_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Cancelled by user ID")

    class Meta:
        verbose_name = "Leave Application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="idx_leave_user_status"),
            models.Index(fields=["start_date", "end_date"], name="idx_leave_dates"),
        ]

    def __str__(self):
        return f"{self.category} {self.start_date} to {self.end_date} ({self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Employee leave balance snapshot.

Maintained per employee. Updated on approval, cancellation, year-end processing,
and VL-to-EL conversion.
"""
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")
    effective_date = models.DateField(verbose_name="Effective Date", db_index=True)

    cl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="CL Balance")
    rh_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="RH Balance")
    scl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="SCL Balance")
    el_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="EL Balance")
    col_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="COL Balance")
    vl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="VL Balance (faculty only)")

    class Meta:
        verbose_name = "Leave Balance"
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["user_id", "effective_date"], name="idx_balance_user_date"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.effective_date}: CL={self.cl_balance}, EL={self.el_balance}, COL={self.col_balance}, VL={self.vl_balance}"


class LeaveTransaction(TimeStampedModel, UserScopedModel):
    """Leave account transaction record.

Records all balance changes: approvals, cancellations, year-end lapses/conversions,
extensions, and resumption adjustments.
"""
    TRANSACTION_TYPE_CHOICES = [
        ("APPROVAL", "Approval"),
        ("CANCELLATION", "Cancellation"),
        ("YEAR_END_LAPSE", "Year End Lapse"),
        ("YEAR_END_CONVERSION", "Year End Conversion"),
        ("EXTENSION_APPROVAL", "Extension Approval"),
        ("RESUMPTION_ADJUSTMENT", "Resumption Adjustment"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Related Application",
        null=True,
        blank=True,
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Transaction Type")
    category = models.CharField(max_length=2, verbose_name="Leave Category")
    quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Quantity")
    balance_before = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance Before")
    balance_after = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance After")

    reference_application_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Application ID")
    reference_transaction_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Transaction ID")

    processed_by_user_id = models.IntegerField(db_index=True, verbose_name="Processed by user ID")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="Processed At")

    class Meta:
        verbose_name = "Leave Transaction"
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["user_id", "transaction_type"], name="idx_txn_user_type"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.transaction_type} {self.category}: {self.quantity}"


class WorkflowTask(TimeStampedModel, UserScopedModel):
    """Actionable workflow task with SLA tracking.

Used for Unit Head review, Establishment routing, Final Sanction, and SLA reminders/escalations.
"""
    TASK_TYPE_CHOICES = [
        ("UNIT_HEAD_REVIEW", "Unit Head Review"),
        ("ESTABLISHMENT_ROUTING", "Establishment Routing"),
        ("FINAL_SANCTION", "Final Sanction"),
        ("RESUMPTION_REVIEW", "Resumption Review"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Related Application",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="Task Type")

    assigned_to_user_id = models.IntegerField(db_index=True, verbose_name="Assigned to user ID")
    role_code = models.CharField(max_length=50, verbose_name="Role Code")

    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("COMPLETED", "Completed")], default="PENDING", verbose_name="Status")

    reminder_threshold_seconds = models.IntegerField(default=3600, verbose_name="Reminder Threshold (seconds)")
    escalation_threshold_seconds = models.IntegerField(default=7200, verbose_name="Escalation Threshold (seconds)")

    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Reminder Sent")
    last_escalation_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Escalation Sent")

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    completed_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Completed by user ID")

    class Meta:
        verbose_name = "Workflow Task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to_user_id", "status"], name="idx_task_assigned_status"),
            models.Index(fields=["application", "status"], name="idx_task_app_status"),
        ]

    def __str__(self):
        return f"{self.application} {self.task_type} for {self.assigned_to_user_id}"


class SLAEventLog(TimeStampedModel, UserScopedModel):
    """SLA reminder and escalation event log."""
    EVENT_TYPE_CHOICES = [
        ("REMINDER", "Reminder"),
        ("ESCALATION", "Escalation"),
    ]

    task = models.ForeignKey(
        "WorkflowTask",
        on_delete=models.CASCADE,
        related_name="sla_events",
        verbose_name="Related Task",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name="Event Type")

    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Triggered At")
    threshold_seconds = models.IntegerField(verbose_name="Threshold (seconds)")
    message = models.TextField(verbose_name="Message")

    class Meta:
        verbose_name = "SLA Event Log"
        ordering = ["-triggered_at"]


class ResumptionRecord(TimeStampedModel, UserScopedModel):
    """Resumption record for EL/COL/VL.

Captures actual return date and details reviewed by Sanctioning Authority.
"""
    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="resumptions",
        verbose_name="Related Application",
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    actual_resumption_date = models.DateField(verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], verbose_name="Resumption Type")

    reviewed_by_user_id = models.IntegerField(db_index=True, verbose_name="Reviewed by user ID")
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name="Reviewed At")

    balance_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Balance Adjustment")

    class Meta:
        verbose_name = "Resumption Record"
        ordering = ["-reviewed_at"]

```


### Repository file modules/leave_elm/domain/policy.py
```
"""Policy domain definitions.

Pure-Python. No Django imports.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

LeaveCategory = Literal["CL", "RH", "SCL", "EL", "COL", "VL"]


@dataclass(frozen=True)
class LeavePolicy:
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    cl_days: int = 8
    rh_days: int = 2
    scl_max_days: int = 15
    el_days: int = 30
    col_days: int = 20
    vl_days: int = 60
    vl_to_el_ratio: Decimal = Decimal("0.5")  # 2 VL : 1 EL

    def get_entitlement(self, category: LeaveCategory) -> Optional[Decimal]:
        """Get entitlement for a leave category."""
        if category == "CL":
            return Decimal(self.cl_days)
        elif category == "RH":
            return Decimal(self.rh_days)
        elif category == "SCL":
            return Decimal(self.scl_max_days)
        elif category == "EL":
            return Decimal(self.el_days)
        elif category == "COL":
            return Decimal(self.col_days)
        elif category == "VL":
            return Decimal(self.vl_days)
        return None

    def get_year_end_outcome(self, category: LeaveCategory) -> Literal["LAPSE", "CARRY_FORWARD", "CONVERT"]:
        """Get year-end outcome for a leave category."""
        if category in ("CL", "RH", "SCL"):
            return "LAPSE"
        elif category == "VL":
            return "CONVERT"
        else:  # EL, COL
            return "CARRY_FORWARD"

    def is_faculty_vl_applicable(self, user_kind: str) -> bool:
        """Check if VL is applicable for faculty."""
        return user_kind == "faculty"


@dataclass(frozen=True)
class HolidayCalendar:
    """Currently effective published holiday/RH calendar."""
    year: int
    holidays: list[date]
    restricted_holidays: list[date]
    is_effective: bool = True

    def is_date_a_holiday(self, d: date) -> bool:
        """Check if a date is a holiday."""
        return d in self.holidays

    def is_restricted_holiday(self, d: date) -> bool:
        """Check if a date is a Restricted Holiday."""
        return d in self.restricted_holidays


@dataclass(frozen=True)
class VacationPeriod:
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year: int
    start_date: date
    end_date: date
    name: str

    def contains_date(self, d: date) -> bool:
        """Check if a date falls within this vacation period."""
        return self.start_date <= d <= self.end_date


@dataclass(frozen=True)
class OrganizationalUnit:
    """Department, Section, or Office."""
    code: str
    name: str
    parent_unit_id: Optional[int] = None
    unit_head_user_id: int = 0

    def is_parent_of(self, other: "OrganizationalUnit") -> bool:
        """Check if this unit is a parent of another unit."""
        return self.code == other.parent_unit_id


@dataclass(frozen=True)
class LeaveHierarchy:
    """Configured hierarchy for leave sanctioning paths."""
    name: str
    description: str = ""
    steps: list["LeaveHierarchyStep"] = None

    def __post_init__(self):
        if self.steps is None:
            object.__setattr__(self, "steps", [])


@dataclass(frozen=True)
class LeaveHierarchyStep:
    """Step in a leave sanctioning hierarchy."""
    order: int
    role_code: str
    is_establishment_step: bool = False

```


### Repository file modules/leave_elm/registry.py
```
"""Leave Management module registry.

Plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label),
ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list.
"""
MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "HR & Admin",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee: My Leave (view balances, history, apply, cancel, extend, resumption) ---
    {
        "code": "leave_elm.mine",
        "label": "My Leave",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave_elm.leave.view_self",
        "sort_order": 10,
    },

    # -- Unit Head / Sanctioning Authority: Queue (review, approve/reject) ---
    {
        "code": "leave_elm.queue",
        "label": "Leave Queue",
        "icon": "ClipboardList",
        "to": "/leave/queue",
        "required_permission": "leave_elm.leave.review",
        "sort_order": 20,
    },

    # -- Admin: Configuration (policy, hierarchy, calendar) ---
    {
        "code": "leave_elm.admin",
        "label": "Admin",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.leave.view_self", "View own leave applications and balances"),
    ("leave_elm.leave.apply", "Create and submit new leave application"),
    ("leave_elm.leave.withdraw", "Withdraw pending leave application"),
    ("leave_elm.leave.cancel", "Request cancellation of approved leave"),
    ("leave_elm.leave.extend", "Request extension of ongoing leave"),
    ("leave_elm.leave.resumption", "Submit resumption of duty"),
    ("leave_elm.leave.view", "View all leave applications"),
    ("leave_elm.leave.review", "Review and approve/reject leave requests"),
    ("leave_elm.leave.approve", "Approve leave request"),
    ("leave_elm.leave.reject", "Reject leave request"),
    ("leave_elm.substitute.accept", "Accept substitute responsibility assignment"),
    ("leave_elm.substitute.decline", "Decline substitute responsibility assignment"),
    ("leave_elm.policy.manage", "Manage leave policy parameters and hierarchy configuration"),
    ("leave_elm.calendar.manage", "Manage holiday/RH calendar"),
    ("leave_elm.hierarchy.manage", "Manage leave sanctioning hierarchy"),
    ("leave_elm.record.maintain", "Maintain or correct leave records within authorized scope"),
]

SYSTEM_PERMISSIONS = [
    "leave_elm.year_end.process",
    "leave_elm.sla.reminder",
    "leave_elm.sla.escalate",
]

# Role grants mapping role names to permission codes
ROLE_GRANTS = {
    # Employee roles (Faculty, Staff)
    "faculty": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],
    "staff": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Unit Head role
    "unit_head": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Establishment processing role (Deputy Registrar Estt.)
    "deputy_registrar_estt": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Dean role
    "dean": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Registrar role
    "registrar": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Director role (self-sanction)
    "director": [
        "leave_elm.leave.view",
        "leave_elm.leave.approve",  # Self-sanction only
    ],

    # Leave Administrator role
    "leave_administrator": [
        "leave_elm.policy.manage",
        "leave_elm.calendar.manage",
        "leave_elm.hierarchy.manage",
        "leave_elm.record.maintain",
    ],
}

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


END OF REFERENCES

CURRENT TASK

Continue the same ELM implementation trial. Generate the service layer and selectors against YOUR supplied foundation files, without renaming or redefining their models/fields. Implement the ELM operations described in the supplied specification: applications, balance inquiries, substitutes and response/replacement, approval routing and decisions, withdrawal, cancellation, extensions, resumption, offline-sanctioned entry, record maintenance, notifications, configuration helpers, year-end and SLA processing. Reuse request.principal / actor.user_id and actor.has_permission(code); use the exact leave_elm permission codes in your registry. All user identities are from modules.directory.contracts; only contracts may be imported across module boundaries. Do not import DRF into services. Use core.api.exceptions domain errors, transaction.atomic for writes, and functions with clear parameters that a later API stage can call. Getters/selectors return QuerySets or simple serializable data. Do not create tests or run functional correctness checks. This is initial implementation generation, not a business-rule review or hardening pass. Return complete compact service code, no placeholders, and only the requested files. The services/__init__.py and selectors/__init__.py may be empty. Do not create login/authentication/database connection infrastructure. Do not invent observed results. Keep this initial output compact, with no repeated methods or placeholder functions. Limit the TOTAL batch to about 280 source lines and at most twelve public service functions; use compact action dispatch rather than generating repetitive per-field methods. Leave unrelated getters to contracts.py. Do not include placeholder pass methods. Keep it small enough to finish the output.

Required output paths:
modules/leave_elm/services/__init__.py
modules/leave_elm/services/leave.py
modules/leave_elm/selectors/__init__.py
modules/leave_elm/selectors/leave.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 004 Complete missing selectors

UTC: 2026-10-12T17:17:33.784444+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1600}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen35-9b-trial/model-field-interfaces.md
```
LeavePolicy: CL_DAYS, RH_DAYS, SCL_MAX_DAYS, EL_DAYS, COL_DAYS, VL_DAYS, VL_TO_EL_RATIO
HolidayCalendar: year, is_effective, created_by_user_id
Holiday: calendar, date, type, name
VacationPeriod: year, start_date, end_date, name
OrganizationalUnit: code, name, parent_unit_id, unit_head_user_id
LeaveHierarchy: name, description
LeaveHierarchyStep: hierarchy, order, role_code, is_establishment_step
LeaveApplication: STATUS_CHOICES, category, user_id, start_date, end_date, purpose, station_leave_required, station_leave_details, substitute_user_id, substitute_consent_given, status, unit_head_user_id, hierarchy_step_order, final_decision_user_id, final_decision_date, final_decision_type, original_application_id, extension_incremental_days, actual_resumption_date, resumption_type, created_by_user_id, updated_by_user_id, submitted_by_user_id, withdrawn_by_user_id, cancelled_by_user_id
LeaveBalance: user_id, effective_date, cl_balance, rh_balance, scl_balance, el_balance, col_balance, vl_balance
LeaveTransaction: TRANSACTION_TYPE_CHOICES, application, user_id, transaction_type, category, quantity, balance_before, balance_after, reference_application_id, reference_transaction_id, processed_by_user_id, processed_at
WorkflowTask: TASK_TYPE_CHOICES, application, task_type, assigned_to_user_id, role_code, status, reminder_threshold_seconds, escalation_threshold_seconds, last_reminder_sent_at, last_escalation_sent_at, completed_at, completed_by_user_id
SLAEventLog: EVENT_TYPE_CHOICES, task, event_type, triggered_at, threshold_seconds, message
ResumptionRecord: application, user_id, actual_resumption_date, resumption_type, reviewed_by_user_id, reviewed_at, balance_adjustment

```


END OF REFERENCES

CURRENT TASK

Generate selectors/leave.py only, maximum60 lines. Reuse the exact current model names/fields. Provide get_application_by_id(application_id:int,user_id:Optional[int]=None), get_own_applications(user_id:int), get_own_balances(user_id:int), get_assigned_tasks(user_id:int), get_current_policy(), and get_notifications(user_id:int) using whatever actual event-log model is available. Return ORM querysets/model instances, imports own models from modules.leave_elm.models. Initial selector generation only; no model or service changes, workflow checks or business-rule repairs. Keep concise and complete.

Output file: modules/leave_elm/selectors/leave.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 005 Backend API and scheduled work

UTC: 2026-10-12T17:21:32.871967+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 7000}`

REFERENCE MATERIAL ONLY


### Repository file modules/leave_elm/models.py
```
"""Leave Management data models.

All fields are syntactically valid Django fields. Models contain all data needed
by the provided leave workflows, policy/calendar/hierarchy configuration,
balances, audit, notifications, SLA and year-end processing.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel

LeaveCategory = Literal[
    "CL",  # Casual Leave
    "RH",  # Restricted Holiday
    "SCL", # Special Casual Leave
    "EL",  # Earned Leave
    "COL", # Commuted Leave
    "VL",  # Vacation Leave
]

LeaveStatus = Literal[
    "DRAFT",
    "AWAITING_SUBSTITUTE",
    "AWAITING_UNIT_HEAD",
    "AWAITING_ESTABLISHMENT",
    "AWAITING_FINAL_SANCTION",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "EXTENSION_PENDING",
    "EXTENDED",
    "RESUMPTION_PENDING",
    "RESUMPTION_REVIEWED",
    "WITHDRAWN",
]

ResumptionType = Literal["NORMAL", "EARLY", "LATE"]


class LeavePolicy(TimeStampedModel):
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    CL_DAYS = models.IntegerField(default=8, verbose_name="Casual Leave days")
    RH_DAYS = models.IntegerField(default=2, verbose_name="Restricted Holiday days")
    SCL_MAX_DAYS = models.IntegerField(default=15, verbose_name="Special Casual Leave max days")
    EL_DAYS = models.IntegerField(default=30, verbose_name="Earned Leave days (non-faculty)")
    COL_DAYS = models.IntegerField(default=20, verbose_name="Commuted Leave days")
    VL_DAYS = models.IntegerField(default=60, verbose_name="Vacation Leave days (faculty)")
    VL_TO_EL_RATIO = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal("0.5"), verbose_name="VL to EL conversion ratio (2:1)")

    class Meta:
        verbose_name = "Leave Policy"
        verbose_name_plural = "Leave Policies"


class HolidayCalendar(TimeStampedModel):
    """Currently effective published holiday/RH calendar."""
    year = models.IntegerField(unique=True, verbose_name="Year")
    is_effective = models.BooleanField(default=False, verbose_name="Is currently effective")
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")

    class Meta:
        verbose_name = "Holiday Calendar"
        ordering = ["-year"]


class Holiday(TimeStampedModel):
    """Individual holiday or Restricted Holiday entry."""
    calendar = models.ForeignKey(
        "HolidayCalendar",
        on_delete=models.CASCADE,
        related_name="holidays",
        verbose_name="Calendar",
    )
    date = models.DateField(unique=True, verbose_name="Date")
    type = models.CharField(max_length=20, choices=[("HOLIDAY", "Holiday"), ("RH", "Restricted Holiday")], verbose_name="Type")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    class Meta:
        verbose_name = "Holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_calendar_date")
        ]


class VacationPeriod(TimeStampedModel):
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year = models.IntegerField(verbose_name="Year")
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    name = models.CharField(max_length=100, verbose_name="Name")

    class Meta:
        verbose_name = "Vacation Period"
        ordering = ["year", "start_date"]


class OrganizationalUnit(TimeStampedModel):
    """Department, Section, or Office."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    name = models.CharField(max_length=200, verbose_name="Name")
    parent_unit_id = models.IntegerField(null=True, blank=True, verbose_name="Parent unit ID", db_index=True)
    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")

    class Meta:
        verbose_name = "Organizational Unit"
        ordering = ["code"]


class LeaveHierarchy(TimeStampedModel):
    """Configured hierarchy for leave sanctioning paths."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        verbose_name = "Leave Hierarchy"
        ordering = ["name"]


class LeaveHierarchyStep(TimeStampedModel):
    """Step in a leave sanctioning hierarchy."""
    hierarchy = models.ForeignKey(
        "LeaveHierarchy",
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Hierarchy",
    )
    order = models.IntegerField(verbose_name="Order")
    role_code = models.CharField(max_length=50, verbose_name="Role code")
    is_establishment_step = models.BooleanField(default=False, verbose_name="Is establishment step")

    class Meta:
        verbose_name = "Hierarchy Step"
        ordering = ["hierarchy", "order"]
        constraints = [
            models.UniqueConstraint(fields=["hierarchy", "order"], name="unique_hierarchy_order")
        ]


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave application record.

Not modified in place after submission. Changes require withdrawal and new application.
"""
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_FINAL_SANCTION", "Awaiting Final Sanction Decision"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("EXTENSION_PENDING", "Extension Pending"),
        ("EXTENDED", "Extended"),
        ("RESUMPTION_PENDING", "Resumption Pending"),
        ("RESUMPTION_REVIEWED", "Resumption Reviewed"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    category = models.CharField(max_length=3, choices=[
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ], verbose_name="Leave Category")

    user_id = models.IntegerField(db_index=True, verbose_name="Applicant user ID")

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    purpose = models.TextField(verbose_name="Purpose/Reason")
    station_leave_required = models.BooleanField(default=False, verbose_name="Station Leave Required")
    station_leave_details = models.JSONField(blank=True, default=dict, verbose_name="Station Leave Details")

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Substitute user ID")
    substitute_consent_given = models.BooleanField(default=False, verbose_name="Substitute Consent Given")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT", verbose_name="Status")

    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")
    hierarchy_step_order = models.IntegerField(verbose_name="Hierarchy Step Order")

    final_decision_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Final Decision User ID")
    final_decision_date = models.DateField(null=True, blank=True, verbose_name="Final Decision Date")
    final_decision_type = models.CharField(max_length=20, choices=[
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ], null=True, blank=True, verbose_name="Final Decision Type")

    # Extension fields
    original_application_id = models.IntegerField(null=True, blank=True, verbose_name="Original Application ID")
    extension_incremental_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Extension Incremental Days")

    # Resumption fields
    actual_resumption_date = models.DateField(null=True, blank=True, verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], null=True, blank=True, verbose_name="Resumption Type")

    # Audit fields
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")
    updated_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Updated by user ID")
    submitted_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Submitted by user ID")
    withdrawn_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Withdrawn by user ID")
    cancelled_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Cancelled by user ID")

    class Meta:
        verbose_name = "Leave Application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="idx_leave_user_status"),
            models.Index(fields=["start_date", "end_date"], name="idx_leave_dates"),
        ]

    def __str__(self):
        return f"{self.category} {self.start_date} to {self.end_date} ({self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Employee leave balance snapshot.

Maintained per employee. Updated on approval, cancellation, year-end processing,
and VL-to-EL conversion.
"""
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")
    effective_date = models.DateField(verbose_name="Effective Date", db_index=True)

    cl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="CL Balance")
    rh_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="RH Balance")
    scl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="SCL Balance")
    el_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="EL Balance")
    col_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="COL Balance")
    vl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="VL Balance (faculty only)")

    class Meta:
        verbose_name = "Leave Balance"
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["user_id", "effective_date"], name="idx_balance_user_date"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.effective_date}: CL={self.cl_balance}, EL={self.el_balance}, COL={self.col_balance}, VL={self.vl_balance}"


class LeaveTransaction(TimeStampedModel, UserScopedModel):
    """Leave account transaction record.

Records all balance changes: approvals, cancellations, year-end lapses/conversions,
extensions, and resumption adjustments.
"""
    TRANSACTION_TYPE_CHOICES = [
        ("APPROVAL", "Approval"),
        ("CANCELLATION", "Cancellation"),
        ("YEAR_END_LAPSE", "Year End Lapse"),
        ("YEAR_END_CONVERSION", "Year End Conversion"),
        ("EXTENSION_APPROVAL", "Extension Approval"),
        ("RESUMPTION_ADJUSTMENT", "Resumption Adjustment"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Related Application",
        null=True,
        blank=True,
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Transaction Type")
    category = models.CharField(max_length=2, verbose_name="Leave Category")
    quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Quantity")
    balance_before = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance Before")
    balance_after = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance After")

    reference_application_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Application ID")
    reference_transaction_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Transaction ID")

    processed_by_user_id = models.IntegerField(db_index=True, verbose_name="Processed by user ID")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="Processed At")

    class Meta:
        verbose_name = "Leave Transaction"
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["user_id", "transaction_type"], name="idx_txn_user_type"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.transaction_type} {self.category}: {self.quantity}"


class WorkflowTask(TimeStampedModel, UserScopedModel):
    """Actionable workflow task with SLA tracking.

Used for Unit Head review, Establishment routing, Final Sanction, and SLA reminders/escalations.
"""
    TASK_TYPE_CHOICES = [
        ("UNIT_HEAD_REVIEW", "Unit Head Review"),
        ("ESTABLISHMENT_ROUTING", "Establishment Routing"),
        ("FINAL_SANCTION", "Final Sanction"),
        ("RESUMPTION_REVIEW", "Resumption Review"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Related Application",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="Task Type")

    assigned_to_user_id = models.IntegerField(db_index=True, verbose_name="Assigned to user ID")
    role_code = models.CharField(max_length=50, verbose_name="Role Code")

    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("COMPLETED", "Completed")], default="PENDING", verbose_name="Status")

    reminder_threshold_seconds = models.IntegerField(default=3600, verbose_name="Reminder Threshold (seconds)")
    escalation_threshold_seconds = models.IntegerField(default=7200, verbose_name="Escalation Threshold (seconds)")

    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Reminder Sent")
    last_escalation_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Escalation Sent")

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    completed_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Completed by user ID")

    class Meta:
        verbose_name = "Workflow Task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to_user_id", "status"], name="idx_task_assigned_status"),
            models.Index(fields=["application", "status"], name="idx_task_app_status"),
        ]

    def __str__(self):
        return f"{self.application} {self.task_type} for {self.assigned_to_user_id}"


class SLAEventLog(TimeStampedModel, UserScopedModel):
    """SLA reminder and escalation event log."""
    EVENT_TYPE_CHOICES = [
        ("REMINDER", "Reminder"),
        ("ESCALATION", "Escalation"),
    ]

    task = models.ForeignKey(
        "WorkflowTask",
        on_delete=models.CASCADE,
        related_name="sla_events",
        verbose_name="Related Task",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name="Event Type")

    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Triggered At")
    threshold_seconds = models.IntegerField(verbose_name="Threshold (seconds)")
    message = models.TextField(verbose_name="Message")

    class Meta:
        verbose_name = "SLA Event Log"
        ordering = ["-triggered_at"]


class ResumptionRecord(TimeStampedModel, UserScopedModel):
    """Resumption record for EL/COL/VL.

Captures actual return date and details reviewed by Sanctioning Authority.
"""
    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="resumptions",
        verbose_name="Related Application",
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    actual_resumption_date = models.DateField(verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], verbose_name="Resumption Type")

    reviewed_by_user_id = models.IntegerField(db_index=True, verbose_name="Reviewed by user ID")
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name="Reviewed At")

    balance_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Balance Adjustment")

    class Meta:
        verbose_name = "Resumption Record"
        ordering = ["-reviewed_at"]

```


### Repository file modules/leave_elm/services/leave.py
```
from __future__ import annotations
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.directory.contracts import get_users, UserDTO
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, LeaveTransaction,
    WorkflowTask, SLAEventLog, ResumptionRecord, OrganizationalUnit,
    HolidayCalendar, VacationPeriod, LeaveHierarchy, LeaveHierarchyStep,
    LeavePolicy
)
from modules.leave_elm.domain.policy import (
    LeaveCategory, HolidayCalendar as PolicyCalendar,
    VacationPeriod as PolicyVacationPeriod, LeavePolicy as DomainPolicy
)

def _get_policy() -> DomainPolicy:
    db_policy = LeavePolicy.objects.first()
    if not db_policy:
        return DomainPolicy()
    return DomainPolicy(
        cl_days=db_policy.CL_DAYS, rh_days=db_policy.RH_DAYS,
        scl_max_days=db_policy.SCL_MAX_DAYS, el_days=db_policy.EL_DAYS,
        col_days=db_policy.COL_DAYS, vl_days=db_policy.VL_DAYS,
        vl_to_el_ratio=db_policy.VL_TO_EL_RATIO
    )

def _get_calendar() -> PolicyCalendar:
    effective = HolidayCalendar.objects.filter(is_effective=True).first()
    if not effective:
        return PolicyCalendar(year=2025, holidays=[], restricted_holidays=[], is_effective=False)
    hols = list(effective.holidays.all().values_list('date', flat=True))
    rh = list(effective.holidays.filter(type='RH').values_list('date', flat=True))
    return PolicyCalendar(
        year=effective.year, holidays=hols, restricted_holidays=rh,
        is_effective=effective.is_effective
    )

def _get_vacation_periods() -> list[PolicyVacationPeriod]:
    periods = VacationPeriod.objects.filter(year=date.today().year)
    return [PolicyVacationPeriod(
        year=p.year, start_date=p.start_date, end_date=p.end_date, name=p.name
    ) for p in periods]

def _get_unit_head(user_id: int) -> Optional[int]:
    unit = OrganizationalUnit.objects.filter(unit_head_user_id=user_id).first()
    return unit.unit_head_user_id if unit else None

def _is_director(user_id: int) -> bool:
    return user_id == 1000  # Assumed Director ID

def _get_sanctioning_path(category: str, user_id: int) -> list[int]:
    """Return ordered list of user IDs for sanctioning path."""
    policy = _get_policy()
    if category in ('CL', 'RH'):
        unit_head = _get_unit_head(user_id)
        return [unit_head] if unit_head else []
    # Higher sanction
    steps = LeaveHierarchy.objects.first()
    if not steps:
        return []
    path = []
    for step in steps.steps.all():
        if step.is_establishment_step:
            continue
        role_users = OrganizationalUnit.objects.filter(
            unit_head_user_id__in=[step.role_code] if step.role_code.isdigit() else []
        ).values_list('unit_head_user_id', flat=True)
        path.extend(role_users)
    return path

def _validate_leave_request(
    user_id: int, category: str, start_date: date, end_date: date,
    substitute_user_id: Optional[int] = None
) -> tuple[bool, list[str]]:
    errors = []
    policy = _get_policy()
    calendar = _get_calendar()
    periods = _get_vacation_periods()
    
    if category not in ('CL', 'RH', 'SCL', 'EL', 'COL', 'VL'):
        errors.append(f"Invalid category: {category}")
        return False, errors
    
    # Check entitlement
    if category == 'RH':
        if start_date not in calendar.restricted_holidays:
            errors.append("Restricted Holiday must match published RH calendar")
            return False, errors
    elif category == 'VL':
        if not any(p.contains_date(start_date) for p in periods):
            errors.append("VL must be within a vacation period")
            return False, errors
    
    # Check balance
    balances = LeaveBalance.objects.filter(user_id=user_id).order_by('-effective_date')
    latest = balances.first()
    if not latest:
        errors.append("No leave balance record found")
        return False, errors
    
    if category == 'CL':
        if latest.cl_balance < Decimal('0.5'):
            errors.append("Insufficient CL balance")
    elif category == 'RH':
        if latest.rh_balance < Decimal('1'):
            errors.append("Insufficient RH balance")
    elif category == 'SCL':
        if latest.scl_balance < Decimal('1'):
            errors.append("Insufficient SCL balance")
    elif category == 'EL':
        if latest.el_balance < Decimal('1'):
            errors.append("Insufficient EL balance")
    elif category == 'COL':
        if latest.col_balance < Decimal('1'):
            errors.append("Insufficient COL balance")
    elif category == 'VL':
        if latest.vl_balance < Decimal('2'):  # 2 VL = 1 EL
            errors.append("Insufficient VL balance")
    
    # Check overlap
    existing = LeaveApplication.objects.filter(
        user_id=user_id, status__in=('APPROVED', 'AWAITING_SUBSTITUTE', 'AWAITING_UNIT_HEAD',
                                     'AWAITING_ESTABLISHMENT', 'AWAITING_FINAL_SANCTION'),
        start_date__lte=end_date, end_date__gte=start_date
    ).exclude(
        id__in=LeaveApplication.objects.filter(
            user_id=user_id, status='DRAFT'
        ).values_list('id', flat=True)
    )
    
    if existing.exists():
        errors.append("Overlaps with active pending or approved leave")
        return False, errors
    
    # Check substitute overlap
    if substitute_user_id:
        sub_exists = LeaveApplication.objects.filter(
            user_id=substitute_user_id, status__in=('APPROVED', 'AWAITING_SUBSTITUTE',
                                                     'AWAITING_UNIT_HEAD', 'AWAITING_ESTABLISHMENT',
                                                     'AWAITING_FINAL_SANCTION'),
            start_date__lte=end_date, end_date__gte=start_date
        ).exists()
        if sub_exists:
            errors.append("Substitute has overlapping leave")
    
    return len(errors) == 0, errors

def _check_substitute_consent(substitute_user_id: int) -> bool:
    """Check if substitute has accepted."""
    # In real impl, this would check a consent table or workflow task state
    # For now, assume we need to create the task and wait for response
    return True  # Placeholder - actual implementation needs consent tracking

def _create_application(
    user_id: int, category: str, start_date: date, end_date: date,
    purpose: str, station_leave_required: bool = False,
    substitute_user_id: Optional[int] = None
) -> LeaveApplication:
    """Create a new leave application."""
    policy = _get_policy()
    
    # Determine category-specific entitlement
    if category == 'CL':
        days = Decimal('0.5') if (start_date.day % 2 != 0 and end_date.day % 2 != 0) else Decimal('1')
    elif category == 'RH':
        days = Decimal('1')
    elif category == 'SCL':
        days = Decimal('1')
    elif category == 'EL':
        days = Decimal('1')
    elif category == 'COL':
        days = Decimal('1')
    elif category == 'VL':
        days = Decimal('2')  # 2 VL per day
    
    app = LeaveApplication.objects.create(
        user_id=user_id, category=category, start_date=start_date,
        end_date=end_date, purpose=purpose,
        station_leave_required=station_leave_required,
        substitute_user_id=substitute_user_id,
        created_by_user_id=user_id
    )
    
    # Determine initial status
    if substitute_user_id:
        app.status = 'AWAITING_SUBSTITUTE'
    elif _is_director(user_id):
        app.status = 'AWAITING_UNIT_HEAD'  # Director self-sanction starts at Unit Head
    else:
        app.status = 'AWAITING_UNIT_HEAD'
    
    app.save()
    return app

def _process_substitute_response(
    application_id: int, substitute_user_id: int, accepted: bool,
    new_substitute_user_id: Optional[int] = None
) -> tuple[bool, str]:
    """Process substitute response. Returns (success, message)."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if not app.substitute_user_id:
        return False, "No substitute nominated"
    
    if accepted:
        app.status = 'AWAITING_UNIT_HEAD'
        app.save()
        return True, "Substitute accepted"
    else:
        # Decline - allow replacement or withdrawal
        if new_substitute_user_id:
            app.substitute_user_id = new_substitute_user_id
            app.status = 'AWAITING_SUBSTITUTE'
            app.save()
            return True, "New substitute nominated"
        return False, "Substitute declined - must nominate replacement or withdraw"

def _route_to_sanctioning(app: LeaveApplication) -> WorkflowTask:
    """Route application to appropriate sanctioning authority."""
    policy = _get_policy()
    
    if app.category in ('CL', 'RH'):
        # Unit Head final decision
        unit_head_id = _get_unit_head(app.user_id)
        if not unit_head_id:
            raise ConflictError("No Unit Head configured")
        
        task = WorkflowTask.objects.create(
            application=app, task_type='UNIT_HEAD_REVIEW',
            assigned_to_user_id=unit_head_id, role_code='unit_head'
        )
        return task
    else:
        # Higher sanction path
        steps = _get_sanctioning_path(app.category, app.user_id)
        if not steps:
            raise ConflictError("No sanctioning path configured")
        
        task = WorkflowTask.objects.create(
            application=app, task_type='FINAL_SANCTION',
            assigned_to_user_id=steps[0], role_code='sanctioning_authority'
        )
        return task

def _make_final_decision(
    application_id: int, decision: Literal['APPROVED', 'REJECTED'],
    user_id: int
) -> tuple[bool, str]:
    """Make final sanctioning decision."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status not in ('AWAITING_FINAL_SANCTION', 'AWAITING_UNIT_HEAD'):
        return False, "Application not in sanctionable state"
    
    with transaction.atomic():
        # Update application
        app.final_decision_user_id = user_id
        app.final_decision_date = date.today()
        app.final_decision_type = decision
        
        if decision == 'APPROVED':
            app.status = 'APPROVED'
            
            # Deduct balance
            balances = LeaveBalance.objects.filter(user_id=app.user_id).order_by('-effective_date')
            latest = balances.first()
            
            if app.category == 'CL':
                days = Decimal('0.5') if (app.start_date.day % 2 != 0 and app.end_date.day % 2 != 0) else Decimal('1')
            elif app.category == 'RH':
                days = Decimal('1')
            elif app.category == 'SCL':
                days = Decimal('1')
            elif app.category == 'EL':
                days = Decimal('1')
            elif app.category == 'COL':
                days = Decimal('1')
            elif app.category == 'VL':
                days = Decimal('2')
            
            new_balance = getattr(latest, f'{app.category.lower()}_balance', Decimal('0')) - days
            
            # Create transaction record
            LeaveTransaction.objects.create(
                application=app, user_id=app.user_id,
                transaction_type='APPROVAL', category=app.category,
                quantity=days, balance_before=new_balance + days,
                balance_after=new_balance, processed_by_user_id=user_id
            )
            
            # Update balance
            latest.__setattr__(f'{app.category.lower()}_balance', new_balance)
            latest.save()
        else:
            app.status = 'REJECTED'
        
        app.save()
    
    return True, "Decision recorded"

def _withdraw_application(application_id: int, user_id: int) -> tuple[bool, str]:
    """Withdraw a pending application."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status == 'WITHDRAWN':
        return False, "Already withdrawn"
    
    if app.status in ('APPROVED', 'REJECTED'):
        return False, "Cannot withdraw approved/rejected application"
    
    with transaction.atomic():
        app.status = 'WITHDRAWN'
        app.withdrawn_by_user_id = user_id
        app.save()
    
    # Cancel associated tasks
    WorkflowTask.objects.filter(application=app).update(status='COMPLETED')
    
    return True, "Application withdrawn"

def _cancel_approved_leave(
    application_id: int, decision: Literal['APPROVED', 'REJECTED'],
    user_id: int
) -> tuple[bool, str]:
    """Cancel an approved leave before start."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can be cancelled"
    
    if app.start_date <= date.today():
        return False, "Cannot cancel leave that has already started"
    
    with transaction.atomic():
        # Process through hierarchy
        if app.category in ('CL', 'RH'):
            unit_head_id = _get_unit_head(app.user_id)
            if not unit_head_id:
                raise ConflictError("No Unit Head configured")
            task = WorkflowTask.objects.create(
                application=app, task_type='UNIT_HEAD_REVIEW',
                assigned_to_user_id=unit_head_id, role_code='unit_head'
            )
        else:
            steps = _get_sanctioning_path(app.category, app.user_id)
            if not steps:
                raise ConflictError("No sanctioning path configured")
            task = WorkflowTask.objects.create(
                application=app, task_type='FINAL_SANCTION',
                assigned_to_user_id=steps[0], role_code='sanctioning_authority'
            )
        
        # Make final decision
        success, msg = _make_final_decision(app.id, decision, user_id)
        if not success:
            return False, msg
    
    return True, "Cancellation processed"

def _extend_ongoing_leave(
    application_id: int, additional_days: Decimal, user_id: int,
    substitute_user_id: Optional[int] = None
) -> tuple[bool, str]:
    """Extend an ongoing leave."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.category not in ('EL', 'COL', 'VL'):
        return False, "Extension only available for EL, COL, VL"
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can be extended"
    
    # Validate extension
    valid, errors = _validate_leave_request(
        user_id, app.category, app.end_date + timedelta(days=1),
        app.end_date + timedelta(days=int(additional_days)),
        substitute_user_id
    )
    if not valid:
        return False, "; ".join(errors)
    
    with transaction.atomic():
        # Create extension application linked to original
        ext_app = LeaveApplication.objects.create(
            user_id=app.user_id, category=app.category,
            start_date=app.end_date + timedelta(days=1),
            end_date=app.end_date + timedelta(days=int(additional_days)),
            purpose=f"Extension of {app.category} leave",
            station_leave_required=app.station_leave_required,
            substitute_user_id=substitute_user_id,
            created_by_user_id=user_id,
            original_application_id=app.id
        )
        
        ext_app.status = 'AWAITING_SUBSTITUTE' if substitute_user_id else 'AWAITING_UNIT_HEAD'
        ext_app.extension_incremental_days = additional_days
        ext_app.save()
    
    return True, "Extension request created"

def _submit_resumption(
    application_id: int, actual_date: date, user_id: int
) -> tuple[bool, str]:
    """Submit resumption of duty."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.category not in ('EL', 'COL', 'VL'):
        return False, "Resumption only for EL, COL, VL"
    
    if app.status != 'APPROVED':
        return False, "Only approved leaves can have resumption submitted"
    
    with transaction.atomic():
        record = ResumptionRecord.objects.create(
            application=app, user_id=user_id,
            actual_resumption_date=actual_date,
            reviewed_by_user_id=user_id
        )
        
        # Calculate adjustment
        approved_days = (app.end_date - app.start_date).days + 1
        actual_days = (actual_date - app.start_date).days + 1
        adjustment = Decimal(actual_days) - Decimal(approved_days)
        
        record.balance_adjustment = adjustment
        record.save()
    
    return True, "Resumption submitted"

def _record_offline_sanction(
    user_id: int, category: str, start_date: date, end_date: date,
    reference_number: str, evidence: str
) -> tuple[bool, str]:
    """Record offline-sanctioned leave."""
    with transaction.atomic():
        app = LeaveApplication.objects.create(
            user_id=user_id, category=category, start_date=start_date,
            end_date=end_date, purpose="Offline sanctioned",
            station_leave_required=False,
            created_by_user_id=user_id
        )
        
        # Calculate days
        if category == 'CL':
            days = Decimal('0.5') if (start_date.day % 2 != 0 and end_date.day % 2 != 0) else Decimal('1')
        elif category in ('RH', 'SCL', 'EL', 'COL', 'VL'):
            days = Decimal('1') if category != 'VL' else Decimal('2')
        
        # Create transaction
        LeaveTransaction.objects.create(
            application=app, user_id=user_id,
            transaction_type='APPROVAL', category=category,
            quantity=days, balance_before=Decimal('0'),
            balance_after=-days, processed_by_user_id=user_id
        )
    
    return True, "Offline sanction recorded"

def _maintain_leave_record(
    user_id: int, application_id: int, field: str, value
) -> tuple[bool, str]:
    """Maintain or correct a leave record within authorized scope."""
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status in ('APPROVED', 'REJECTED'):
        return False, "Cannot modify approved/rejected applications"
    
    allowed_fields = ['purpose', 'station_leave_required']
    if field not in allowed_fields:
        return False, f"Field {field} not allowed for maintenance"
    
    with transaction.atomic():
        setattr(app, field, value)
        app.save()
    
    return True, "Record maintained"

def _get_leave_balances(user_id: int) -> dict:
    """Get current leave balances."""
    balances = LeaveBalance.objects.filter(user_id=user_id).order_by('-effective_date')
    latest = balances.first()
    
    if not latest:
        return {
            'cl_balance': Decimal('0'), 'rh_balance': Decimal('0'),
            'scl_balance': Decimal('0'), 'el_balance': Decimal('0'),
            'col_balance': Decimal('0'), 'vl_balance': Decimal('0')
        }
    
    return {
        'cl_balance': latest.cl_balance, 'rh_balance': latest.rh_balance,
        'scl_balance': latest.scl_balance, 'el_balance': latest.el_balance,
        'col_balance': latest.col_balance, 'vl_balance': latest.vl_balance
    }

def _get_leave_history(user_id: int) -> list:
    """Get leave application history."""
    apps = LeaveApplication.objects.filter(user_id=user_id).order_by('-created_at')
    
    history = []
    for app in apps:
        entry = {
            'id': app.id, 'category': app.category,
            'start_date': app.start_date, 'end_date': app.end_date,
            'purpose': app.purpose, 'status': app.status,
            'created_at': app.created_at
        }
        
        if app.final_decision_type:
            entry['final_decision'] = app.final_decision_type
            entry['decision_date'] = app.final_decision_date
        
        history.append(entry)
    
    return history

def _process_year_end(user_id: int) -> dict:
    """Process year-end leave account."""
    policy = _get_policy()
    today = date.today()
    year_end = date(today.year, 12, 31)
    
    results = {
        'processed': False, 'exceptions': [],
        'lapses': [], 'conversions': [], 'carry_forwards': []
    }
    
    balances = LeaveBalance.objects.filter(user_id=user_id, effective_date__lte=year_end)
    latest = balances.first()
    
    if not latest:
        return results
    
    # Process CL, RH, SCL - lapse
    for cat in ['cl', 'rh', 'scl']:
        balance = getattr(latest, f'{cat}_balance', Decimal('0'))
        if balance > Decimal('0'):
            LeaveTransaction.objects.create(
                user_id=user_id, transaction_type='YEAR_END_LAPSE',
                category=cat.upper(), quantity=balance,
                balance_before=balance, balance_after=Decimal('0'),
                processed_by_user_id=user_id
            )
            results['lapses'].append({
                'category': cat.upper(), 'quantity': balance,
                'reason': 'Year end lapse'
            })
    
    # Process VL - convert to EL
    vl_balance = latest.vl_balance
    if vl_balance > Decimal('0'):
        el_converted = vl_balance / policy.vl_to_el_ratio
        LeaveTransaction.objects.create(
            user_id=user_id, transaction_type='YEAR_END_CONVERSION',
            category='VL', quantity=vl_balance,
            balance_before=vl_balance, balance_after=Decimal('0'),
            processed_by_user_id=user_id
        )
        LeaveTransaction.objects.create(
            user_id=user_id, transaction_type='YEAR_END_CONVERSION',
            category='EL', quantity=el_converted,
            balance_before=latest.el_balance, balance_after=latest.el_balance + el_converted,
            processed_by_user_id=user_id
        )
        results['conversions'].append({
            'from': 'VL', 'to': 'EL', 'quantity': vl_balance,
            'converted_quantity': el_converted
        })
    
    # Process EL, COL - carry forward (no transaction needed, balance persists)
    results['carry_forwards'].append({
        'category': 'EL', 'balance': latest.el_balance,
        'reason': 'Year end carry forward'
    })
    results['carry_forwards'].append({
        'category': 'COL', 'balance': latest.col_balance,
        'reason': 'Year end carry forward'
    })
    
    results['processed'] = True
    return results

def _process_sla_task(task_id: int, threshold_type: Literal['REMINDER', 'ESCALATION']) -> dict:
    """Process SLA threshold event."""
    task = WorkflowTask.objects.get(id=task_id)
    
    if task.status != 'PENDING':
        return {'processed': False, 'reason': 'Task not pending'}
    
    with transaction.atomic():
        if threshold_type == 'REMINDER':
            if task.reminder_threshold_seconds > 0:
                # Check if threshold reached
                elapsed = (timezone.now() - task.created_at).total_seconds()
                if elapsed >= task.reminder_threshold_seconds:
                    if not task.last_reminder_sent_at or \
                       (timezone.now() - task.last_reminder_sent_at).total_seconds() > task.reminder_threshold_seconds:
                        SLAEventLog.objects.create(
                            task=task, event_type='REMINDER',
                            threshold_seconds=task.reminder_threshold_seconds,
                            message=f"Reminder sent for {task.task_type}"
                        )
                        task.last_reminder_sent_at = timezone.now()
                        task.save()
        
        elif threshold_type == 'ESCALATION':
            if task.escalation_threshold_seconds > 0:
                elapsed = (timezone.now() - task.created_at).total_seconds()
                if elapsed >= task.escalation_threshold_seconds:
                    if not task.last_escalation_sent_at or \
                       (timezone.now() - task.last_escalation_sent_at).total_seconds() > task.escalation_threshold_seconds:
                        SLAEventLog.objects.create(
                            task=task, event_type='ESCALATION',
                            threshold_seconds=task.escalation_threshold_seconds,
                            message=f"Escalation sent for {task.task_type}"
                        )
                        task.last_escalation_sent_at = timezone.now()
                        task.save()
    
    return {'processed': True, 'event_type': threshold_type}

```


### Repository file modules/leave_elm/selectors/leave.py
```
from typing import Optional, List
from django.db.models import QuerySet
from modules.leave_elm.models import LeaveApplication, LeaveBalance, WorkflowTask, SLAEventLog, LeavePolicy, HolidayCalendar, VacationPeriod, OrganizationalUnit


def get_application_by_id(application_id: int, user_id: Optional[int] = None) -> Optional[LeaveApplication]:
    if user_id is not None:
        return LeaveApplication.objects.filter(id=application_id, user_id=user_id).first()
    return LeaveApplication.objects.filter(id=application_id).first()


def get_own_applications(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(user_id=user_id)


def get_own_balances(user_id: int) -> List[LeaveBalance]:
    return list(LeaveBalance.objects.filter(user_id=user_id))


def get_assigned_tasks(user_id: int) -> QuerySet[WorkflowTask]:
    return WorkflowTask.objects.filter(assigned_to_user_id=user_id, status__in=['PENDING', 'IN_PROGRESS'])


def get_current_policy() -> LeavePolicy:
    return LeavePolicy.objects.first()


def get_notifications(user_id: int) -> List[SLAEventLog]:
    tasks = WorkflowTask.objects.filter(assigned_to_user_id=user_id, status='PENDING')
    return list(SLAEventLog.objects.filter(task__in=tasks, event_type__in=['ESCALATION', 'REMINDER']))

```


### Repository file modules/leave_elm/registry.py
```
"""Leave Management module registry.

Plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label),
ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list.
"""
MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "HR & Admin",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee: My Leave (view balances, history, apply, cancel, extend, resumption) ---
    {
        "code": "leave_elm.mine",
        "label": "My Leave",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave_elm.leave.view_self",
        "sort_order": 10,
    },

    # -- Unit Head / Sanctioning Authority: Queue (review, approve/reject) ---
    {
        "code": "leave_elm.queue",
        "label": "Leave Queue",
        "icon": "ClipboardList",
        "to": "/leave/queue",
        "required_permission": "leave_elm.leave.review",
        "sort_order": 20,
    },

    # -- Admin: Configuration (policy, hierarchy, calendar) ---
    {
        "code": "leave_elm.admin",
        "label": "Admin",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.leave.view_self", "View own leave applications and balances"),
    ("leave_elm.leave.apply", "Create and submit new leave application"),
    ("leave_elm.leave.withdraw", "Withdraw pending leave application"),
    ("leave_elm.leave.cancel", "Request cancellation of approved leave"),
    ("leave_elm.leave.extend", "Request extension of ongoing leave"),
    ("leave_elm.leave.resumption", "Submit resumption of duty"),
    ("leave_elm.leave.view", "View all leave applications"),
    ("leave_elm.leave.review", "Review and approve/reject leave requests"),
    ("leave_elm.leave.approve", "Approve leave request"),
    ("leave_elm.leave.reject", "Reject leave request"),
    ("leave_elm.substitute.accept", "Accept substitute responsibility assignment"),
    ("leave_elm.substitute.decline", "Decline substitute responsibility assignment"),
    ("leave_elm.policy.manage", "Manage leave policy parameters and hierarchy configuration"),
    ("leave_elm.calendar.manage", "Manage holiday/RH calendar"),
    ("leave_elm.hierarchy.manage", "Manage leave sanctioning hierarchy"),
    ("leave_elm.record.maintain", "Maintain or correct leave records within authorized scope"),
]

SYSTEM_PERMISSIONS = [
    "leave_elm.year_end.process",
    "leave_elm.sla.reminder",
    "leave_elm.sla.escalate",
]

# Role grants mapping role names to permission codes
ROLE_GRANTS = {
    # Employee roles (Faculty, Staff)
    "faculty": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],
    "staff": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Unit Head role
    "unit_head": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Establishment processing role (Deputy Registrar Estt.)
    "deputy_registrar_estt": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Dean role
    "dean": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Registrar role
    "registrar": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Director role (self-sanction)
    "director": [
        "leave_elm.leave.view",
        "leave_elm.leave.approve",  # Self-sanction only
    ],

    # Leave Administrator role
    "leave_administrator": [
        "leave_elm.policy.manage",
        "leave_elm.calendar.manage",
        "leave_elm.hierarchy.manage",
        "leave_elm.record.maintain",
    ],
}

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


END OF REFERENCES

CURRENT TASK

Continue the local Qwen ELM implementation. Generate DRF serializers, APIViews and urls using YOUR existing models and service functions supplied below, without redesigning business rules or changing model/service logic. Mount-relative URL paths must have no trailing slash, because the existing Axios client uses /api/v1. APIs must expose the operations already implemented by your service layer to the frontend: own leave list/create, details, balances, assigned task queue, substitute responses and replacement, review/final decisions, withdrawal/cancellation/extension/resumption, admin configuration/calendars/offline-record entry and history/notifications as available. Reuse request.principal, HasModuleGrant("leave_elm"), and the exact HasPermission codes declared in your registry. Never use request.user.pk or Django User. Use modules.directory.contracts for employee selection. Annotate every APIView method with drf_spectacular extend_schema request/response serializers or OpenApiTypes so schema generation works. Give action endpoints unique operation_id on the METHOD decorator, never the class decorator. Return React-compatible simple response JSON. Scheduled tasks may call existing service operations only: no copied logic or new rules. Use Celery shared_task string names and expose BEAT_SCHEDULE and TASK_ROUTES from schedule.py. Do not write tests. Only generate requested new files. Keep this initial output compact, with no repeated methods or placeholder functions. Keep the batch under approximately 300 source lines. Use a small set of APIViews with action dispatch, rather than dozens of duplicate classes. Every imported service function and model name must actually exist in the supplied code. Do not invent a new method just to complete a URL. Group operations using existing service methods and preserve their behavior.

Required output paths:
modules/leave_elm/api/__init__.py
modules/leave_elm/api/serializers.py
modules/leave_elm/api/views.py
modules/leave_elm/api/urls.py
modules/leave_elm/tasks.py
modules/leave_elm/schedule.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 006 Frontend types, queries and route table

UTC: 2026-10-12T17:29:18.096044+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 6000}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen35-9b-trial/problem-statement-context.md
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


### Repository file modules/leave_elm/api/urls.py
```
"""Leave Management API URLs."""
from django.urls import path
from .views import LeaveAPI

app_name = 'leave_elm'

urlpatterns = [
    path('', LeaveAPI.as_view({'get': 'mine'}), name='root'),
    path('mine/', LeaveAPI.as_view({'get': 'mine'}), name='mine'),
    path('apply/', LeaveAPI.as_view({'post': 'apply'}), name='apply'),
    path('<int:id>/', LeaveAPI.as_view({'get': 'details'}), name='detail'),
    path('<int:id>/withdraw/', LeaveAPI.as_view({'post': 'withdraw'}), name='withdraw'),
    path('<int:id>/cancel/', LeaveAPI.as_view({'post': 'cancel'}), name='cancel'),
    path('<int:id>/extend/', LeaveAPI.as_view({'post': 'extend'}), name='extend'),
    path('<int:id>/resumption/', LeaveAPI.as_view({'post': 'resumption'}), name='resumption'),
    path('balances/', LeaveAPI.as_view({'get': 'balances'}), name='balances'),
    path('history/', LeaveAPI.as_view({'get': 'history'}), name='history'),
    path('queue/', LeaveAPI.as_view({'get': 'queue'}), name='queue'),
    path('<int:id>/substitute/accept/', LeaveAPI.as_view({'post': 'substitute_accept'}), name='substitute_accept'),
    path('<int:id>/substitute/decline/', LeaveAPI.as_view({'post': 'substitute_decline'}), name='substitute_decline'),
    path('<int:id>/review/', LeaveAPI.as_view({'post': 'review'}), name='review'),
    path('policy/', LeaveAPI.as_view({'get': 'policy'}), name='policy'),
    path('calendar/', LeaveAPI.as_view({'get': 'calendar'}), name='calendar'),
    path('offline-record/', LeaveAPI.as_view({'post': 'offline_record'}), name='offline_record'),
    path('notifications/', LeaveAPI.as_view({'get': 'notifications'}), name='notifications'),
]

```


### Repository file modules/leave_elm/api/views.py
```
"""Leave Management API views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date
from decimal import Decimal
from typing import Optional

from .serializers import LeaveApplicationSerializer, WorkflowTaskSerializer
from fusion_auth.principal import Principal
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, WorkflowTask, SLAEventLog,
    HolidayCalendar, VacationPeriod, OrganizationalUnit,
    LeaveHierarchy, LeaveHierarchyStep, LeavePolicy
)
from modules.leave_elm.services.leave import (
    _validate_leave_request, _create_application, _process_substitute_response,
    _route_to_sanctioning, _make_final_decision, _withdraw_application,
    _cancel_approved_leave, _extend_ongoing_leave, _submit_resumption,
    _record_offline_sanction, _get_leave_balances, _get_leave_history,
    _process_year_end, _process_sla_task
)
from modules.directory.contracts import get_users

class LeaveAPI(viewsets.GenericViewSet):
    permission_classes = []  # Handled by HasPermission decorators
    
    def get_serializer_class(self):
        return LeaveApplicationSerializer
    
    @action(detail=False, methods=['get'])
    def mine(self, request: dict) -> Response:
        """Get own leave applications."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        apps = LeaveApplication.objects.filter(user_id=user_id).order_by('-created_at')
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def apply(self, request: dict) -> Response:
        """Create new leave application."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = request.data
        category = data.get('category')
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])
        purpose = data.get('purpose', '')
        substitute_user_id = data.get('substitute_user_id')
        
        valid, errors = _validate_leave_request(
            user_id, category, start_date, end_date, substitute_user_id
        )
        if not valid:
            return Response({'errors': errors}, status=400)
        
        app = _create_application(
            user_id=user_id, category=category, start_date=start_date,
            end_date=end_date, purpose=purpose, substitute_user_id=substitute_user_id
        )
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data, status=201)
    
    @action(detail=True, methods=['get'])
    def details(self, request: dict) -> Response:
        """Get application details."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        app = LeaveApplication.objects.filter(id=app_id, user_id=user_id).first()
        if not app:
            return Response({'error': 'Not found'}, status=404)
        
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request: dict) -> Response:
        """Withdraw pending application."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _withdraw_application(app_id, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request: dict) -> Response:
        """Cancel approved leave."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _cancel_approved_leave(app_id, 'CANCELLED', user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def extend(self, request: dict) -> Response:
        """Extend ongoing leave."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        additional_days = Decimal(request.data.get('additional_days', '0'))
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _extend_ongoing_leave(app_id, additional_days, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resumption(self, request: dict) -> Response:
        """Submit resumption of duty."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        actual_date = date.fromisoformat(request.data.get('actual_date'))
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _submit_resumption(app_id, actual_date, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balances(self, request: dict) -> Response:
        """Get leave balances."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = _get_leave_balances(user_id)
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def history(self, request: dict) -> Response:
        """Get leave history."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        history = _get_leave_history(user_id)
        return Response(history)
    
    @action(detail=False, methods=['get'])
    def queue(self, request: dict) -> Response:
        """Get assigned tasks."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        tasks = WorkflowTask.objects.filter(assigned_to_user_id=user_id, status='PENDING')
        serializer = WorkflowTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def substitute_accept(self, request: dict) -> Response:
        """Accept substitute responsibility."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _process_substitute_response(app_id, user_id, accepted=True)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def substitute_decline(self, request: dict) -> Response:
        """Decline substitute responsibility."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        new_substitute_user_id = request.data.get('new_substitute_user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _process_substitute_response(app_id, user_id, accepted=False, new_substitute_user_id=new_substitute_user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def review(self, request: dict) -> Response:
        """Review and make final decision."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        decision = request.data.get('decision')
        
        if not app_id or not user_id or not decision:
            return Response({'error': 'ID, User ID and decision required'}, status=400)
        
        success, msg = _make_final_decision(app_id, decision, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def policy(self, request: dict) -> Response:
        """Get current leave policy."""
        policy = _get_policy()
        return Response({
            'CL_DAYS': policy.cl_days,
            'RH_DAYS': policy.rh_days,
            'SCL_MAX_DAYS': policy.scl_max_days,
            'EL_DAYS': policy.el_days,
            'COL_DAYS': policy.col_days,
            'VL_DAYS': policy.vl_days,
            'VL_TO_EL_RATIO': float(policy.vl_to_el_ratio)
        })
    
    @action(detail=False, methods=['get'])
    def calendar(self, request: dict) -> Response:
        """Get holiday calendar."""
        cal = _get_calendar()
        return Response({
            'year': cal.year,
            'holidays': list(cal.holidays),
            'restricted_holidays': list(cal.restricted_holidays),
            'is_effective': cal.is_effective
        })
    
    @action(detail=False, methods=['post'])
    def offline_record(self, request: dict) -> Response:
        """Record offline-sanctioned leave."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = request.data
        category = data.get('category')
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])
        reference_number = data.get('reference_number', '')
        evidence = data.get('evidence', '')
        
        success, msg = _record_offline_sanction(
            user_id, category, start_date, end_date, reference_number, evidence
        )
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.filter(user_id=user_id).last()
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def notifications(self, request: dict) -> Response:
        """Get SLA notifications."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        notifications = get_notifications(user_id)
        serializer = WorkflowTaskSerializer(notifications, many=True)
        return Response(serializer.data)

```


### Repository file modules/leave_elm/api/serializers.py
```
"""Leave Management serializers."""
from rest_framework import serializers
from datetime import date
from decimal import Decimal
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, WorkflowTask,
    SLAEventLog, HolidayCalendar, VacationPeriod,
    OrganizationalUnit, LeaveHierarchy, LeaveHierarchyStep, LeavePolicy
)

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'category', 'start_date', 'end_date', 'purpose', 
                  'station_leave_required', 'substitute_user_id', 'status',
                  'final_decision_type', 'final_decision_date', 'created_at']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['effective_date', 'cl_balance', 'rh_balance', 'scl_balance',
                  'el_balance', 'col_balance', 'vl_balance']

class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = ['id', 'task_type', 'assigned_to_user_id', 'status',
                  'reminder_threshold_seconds', 'escalation_threshold_seconds',
                  'last_reminder_sent_at', 'last_escalation_sent_at']

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ['year', 'is_effective', 'created_by_user_id']

class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ['year', 'start_date', 'end_date', 'name']

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ['CL_DAYS', 'RH_DAYS', 'SCL_MAX_DAYS', 'EL_DAYS', 
                  'COL_DAYS', 'VL_DAYS', 'VL_TO_EL_RATIO']

```


### Repository file modules/leave_elm/registry.py
```
"""Leave Management module registry.

Plain MODULE dictionary, NAV_ITEMS dictionaries, PERMISSIONS list of (code,label),
ROLE_GRANTS dict of role names to permission-code lists, SYSTEM_PERMISSIONS list.
"""
MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "HR & Admin",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee: My Leave (view balances, history, apply, cancel, extend, resumption) ---
    {
        "code": "leave_elm.mine",
        "label": "My Leave",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave_elm.leave.view_self",
        "sort_order": 10,
    },

    # -- Unit Head / Sanctioning Authority: Queue (review, approve/reject) ---
    {
        "code": "leave_elm.queue",
        "label": "Leave Queue",
        "icon": "ClipboardList",
        "to": "/leave/queue",
        "required_permission": "leave_elm.leave.review",
        "sort_order": 20,
    },

    # -- Admin: Configuration (policy, hierarchy, calendar) ---
    {
        "code": "leave_elm.admin",
        "label": "Admin",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.leave.view_self", "View own leave applications and balances"),
    ("leave_elm.leave.apply", "Create and submit new leave application"),
    ("leave_elm.leave.withdraw", "Withdraw pending leave application"),
    ("leave_elm.leave.cancel", "Request cancellation of approved leave"),
    ("leave_elm.leave.extend", "Request extension of ongoing leave"),
    ("leave_elm.leave.resumption", "Submit resumption of duty"),
    ("leave_elm.leave.view", "View all leave applications"),
    ("leave_elm.leave.review", "Review and approve/reject leave requests"),
    ("leave_elm.leave.approve", "Approve leave request"),
    ("leave_elm.leave.reject", "Reject leave request"),
    ("leave_elm.substitute.accept", "Accept substitute responsibility assignment"),
    ("leave_elm.substitute.decline", "Decline substitute responsibility assignment"),
    ("leave_elm.policy.manage", "Manage leave policy parameters and hierarchy configuration"),
    ("leave_elm.calendar.manage", "Manage holiday/RH calendar"),
    ("leave_elm.hierarchy.manage", "Manage leave sanctioning hierarchy"),
    ("leave_elm.record.maintain", "Maintain or correct leave records within authorized scope"),
]

SYSTEM_PERMISSIONS = [
    "leave_elm.year_end.process",
    "leave_elm.sla.reminder",
    "leave_elm.sla.escalate",
]

# Role grants mapping role names to permission codes
ROLE_GRANTS = {
    # Employee roles (Faculty, Staff)
    "faculty": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],
    "staff": [
        "leave_elm.leave.view_self",
        "leave_elm.leave.apply",
        "leave_elm.leave.withdraw",
        "leave_elm.leave.cancel",
        "leave_elm.leave.extend",
        "leave_elm.leave.resumption",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Unit Head role
    "unit_head": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
        "leave_elm.substitute.accept",
        "leave_elm.substitute.decline",
    ],

    # Establishment processing role (Deputy Registrar Estt.)
    "deputy_registrar_estt": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Dean role
    "dean": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Registrar role
    "registrar": [
        "leave_elm.leave.view",
        "leave_elm.leave.review",
        "leave_elm.leave.approve",
        "leave_elm.leave.reject",
    ],

    # Director role (self-sanction)
    "director": [
        "leave_elm.leave.view",
        "leave_elm.leave.approve",  # Self-sanction only
    ],

    # Leave Administrator role
    "leave_administrator": [
        "leave_elm.policy.manage",
        "leave_elm.calendar.manage",
        "leave_elm.hierarchy.manage",
        "leave_elm.record.maintain",
    ],
}

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


### Repository file client/src/auth/types.ts
```
import type { NavGroup } from "../ui/layout/AppShellLayout";

export interface Session {
  user: {
    id: number;
    username: string;
    display_name: string;
    kind: string;
    email: string;
  };
  active_role: string | null;
  roles: string[];
  permissions: string[];
  modules: string[];
  navigation: NavGroup[];
  /** Paired with the session cookie. Echoed in X-CSRF-Token on every write. */
  csrf_token: string;
}

```


### Repository file client/src/app/registry.ts
```
/** Frontend module registry.
 *
 *  `code` MUST match accesscontrol_module.code on the server. An ungranted
 *  module gets no route at all, so deep-linking it 404s rather than rendering
 *  blank. `load` must be a STATIC import() literal or Vite cannot split it. */
import type { RouteObject } from "react-router-dom";

export interface ModuleManifest {
  code: string;
  basePath: string;
  load: () => Promise<{ routes: RouteObject[] }>;
}

export const MODULE_REGISTRY: Record<string, ModuleManifest> = {
  leave_elm: {
    code: "leave_elm",
    basePath: "/leave",
    load: () => import("../modules/leave_elm/routes"),
  },
  placement_cell: {
    code: "placement_cell",
    basePath: "/placement",
    load: () => import("../modules/placement/routes"),
  },
};

```


### Repository file client/src/modules/placement/routes.tsx
```
import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const PostingsPage = lazy(() => import("./pages/PostingsPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const OffersPage = lazy(() => import("./pages/OffersPage"));
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"));
const InterviewsPage = lazy(() => import("./pages/InterviewsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const StudentCpiPage = lazy(() => import("./pages/StudentCpiPage"));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage"));
const RegistrationApprovalsPage = lazy(
  () => import("./pages/RegistrationApprovalsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="postings" replace /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "registration-approvals", element: <RegistrationApprovalsPage /> },
  { path: "postings", element: <PostingsPage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "offers", element: <OffersPage /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "companies", element: <CompaniesPage /> },
  { path: "interviews", element: <InterviewsPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "students-cpi", element: <StudentCpiPage /> },
  { path: "reports", element: <ReportsPage /> },
];

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

Generate the frontend API types, React Query hooks and route table for the actual ELM backend supplied below. This is initial frontend implementation; do not review or repair business rules. Use the exact URL paths, input field names and output JSON shapes exposed by YOUR API code. Reuse Fusion http and errorMessage from client/src/lib/http, useAuth from client/src/auth/AuthProvider, installed @tanstack/react-query and @mantine/notifications. The existing http baseURL is /api/v1; all hooks must use paths under /leave and no trailing slash unless your server uses one. Define clear typed functions/hooks for the pages to call; avoid external packages or custom clients. A later request will create the page components against these hooks. routes.tsx must export const routes: RouteObject[] and contain index redirect plus three relative paths mine, queue, admin, lazy-loading MyLeavePage, LeaveTasksPage, LeaveAdminPage under ./pages. Use only installed React 18/react-router-dom 6/Mantine 7/React Query 5 interfaces. Keep this batch under about 230 lines and return exactly the required files. Do not create tests.

Required output paths:
client/src/modules/leave_elm/api/types.ts
client/src/modules/leave_elm/api/hooks.ts
client/src/modules/leave_elm/routes.tsx

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 007 Frontend MyLeavePage

UTC: 2026-10-12T17:32:46.623601+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 4200}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api/types.ts
```
import type { LeaveApplication, LeaveBalance, WorkflowTask } from '../models';

export interface LeaveRequest {
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  substitute_user_id?: number;
}

export interface LeaveResponse extends LeaveApplication {}

export type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

export interface Policy {
  CL_DAYS: number;
  RH_DAYS: number;
  SCL_MAX_DAYS: number;
  EL_DAYS: number;
  COL_DAYS: number;
  VL_DAYS: number;
  VL_TO_EL_RATIO: number;
}

export interface Calendar {
  year: number;
  holidays: Date[];
  restricted_holidays: Date[];
  is_effective: boolean;
}

export interface Notification {
  id: number;
  task_type: string;
  assigned_to_user_id: number;
  status: string;
  reminder_threshold_seconds: number;
  escalation_threshold_seconds: number;
  last_reminder_sent_at?: string;
  last_escalation_sent_at?: string;
}
```


### Repository file client/src/modules/leave_elm/api/hooks.ts
```
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { http, errorMessage } from '../../lib/http';

const BASE = '/leave';

export function useMyLeave() {
  return useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => http.get(`${BASE}/mine`),
  });
}

export function useApplyLeave(data: LeaveRequest) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/apply`, d),
  });
}

export function useLeaveDetails(id: number) {
  return useQuery({
    queryKey: ['leave', 'detail', id],
    queryFn: () => http.get(`${BASE}/${id}`),
    enabled: !!id,
  });
}

export function useWithdrawLeave(id: number) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/${id}/withdraw`, d),
  });
}

export function useCancelLeave(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/cancel`),
  });
}

export function useExtendLeave(id: number) {
  return useMutation({
    mutationFn: (d: { additional_days: number }) => 
      http.post(`${BASE}/${id}/extend`, d),
  });
}

export function useResumption(id: number) {
  return useMutation({
    mutationFn: (d: { actual_date: string }) => 
      http.post(`${BASE}/${id}/resumption`, d),
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ['leave', 'balances'],
    queryFn: () => http.get(`${BASE}/balances`),
  });
}

export function useLeaveHistory() {
  return useQuery({
    queryKey: ['leave', 'history'],
    queryFn: () => http.get(`${BASE}/history`),
  });
}

export function useLeaveQueue(userId: number) {
  return useQuery({
    queryKey: ['leave', 'queue', userId],
    queryFn: () => http.get(`${BASE}/queue`),
  });
}

export function useSubstituteAccept(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/substitute/accept`),
  });
}

export function useSubstituteDecline(id: number) {
  return useMutation({
    mutationFn: (d: { new_substitute_user_id?: number }) => 
      http.post(`${BASE}/${id}/substitute/decline`, d),
  });
}

export function useReviewLeave(id: number) {
  return useMutation({
    mutationFn: (d: { decision: string }) => 
      http.post(`${BASE}/${id}/review`, d),
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: ['leave', 'policy'],
    queryFn: () => http.get(`${BASE}/policy`),
  });
}

export function useCalendar() {
  return useQuery({
    queryKey: ['leave', 'calendar'],
    queryFn: () => http.get(`${BASE}/calendar`),
  });
}

export function useNotifications(userId: number) {
  return useQuery({
    queryKey: ['leave', 'notifications', userId],
    queryFn: () => http.get(`${BASE}/notifications`),
  });
}

export function useOfflineRecord() {
  return useMutation({
    mutationFn: (d: { category: string; start_date: string; end_date: string; reference_number?: string; evidence?: string }) => 
      http.post(`${BASE}/offline-record`, d),
  });
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

Generate the initial MyLeavePage React18/Mantine7 page as a default export. Provide own applications and balances and an application form. Use supplied API types/hooks/functions exactly. Include available employee action buttons by calling existing API exports; do not add backend rules. Show loading and error states. Use React Query5 object syntax if needed, shared errorMessage from ../../../lib/http, named PageHeader from ../../../ui/components/PageHeader. No new authentication, database connections, dependencies or tests. Return concise complete TSX, maximum160 lines; no repeated placeholder methods. This is initial generation against the new model's own API, not a correctness review.

Output file: client/src/modules/leave_elm/pages/MyLeavePage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 008 Frontend LeaveTasksPage

UTC: 2026-10-12T17:35:27.855458+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 4200}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api/types.ts
```
import type { LeaveApplication } from '../models';

export interface LeaveRequest {
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  substitute_user_id?: number;
}

export interface LeaveResponse extends LeaveApplication {}

export type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

export interface Policy {
  CL_DAYS: number;
  RH_DAYS: number;
  SCL_MAX_DAYS: number;
  EL_DAYS: number;
  COL_DAYS: number;
  VL_DAYS: number;
  VL_TO_EL_RATIO: number;
}

export interface Calendar {
  year: number;
  holidays: Date[];
  restricted_holidays: Date[];
  is_effective: boolean;
}

export interface Notification {
  id: number;
  task_type: string;
  assigned_to_user_id: number;
  status: string;
  reminder_threshold_seconds: number;
  escalation_threshold_seconds: number;
  last_reminder_sent_at?: string;
  last_escalation_sent_at?: string;
}
```


### Repository file client/src/modules/leave_elm/api/hooks.ts
```
import { useQuery, useMutation } from '@tanstack/react-query';
import { http } from '../../../lib/http';
import type { LeaveRequest } from './types';

const BASE = '/leave';

export function useMyLeave() {
  return useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => http.get(`${BASE}/mine`),
  });
}

export function useApplyLeave(_data: LeaveRequest) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/apply`, d),
  });
}

export function useLeaveDetails(id: number) {
  return useQuery({
    queryKey: ['leave', 'detail', id],
    queryFn: () => http.get(`${BASE}/${id}`),
    enabled: !!id,
  });
}

export function useWithdrawLeave(id: number) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/${id}/withdraw`, d),
  });
}

export function useCancelLeave(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/cancel`),
  });
}

export function useExtendLeave(id: number) {
  return useMutation({
    mutationFn: (d: { additional_days: number }) => 
      http.post(`${BASE}/${id}/extend`, d),
  });
}

export function useResumption(id: number) {
  return useMutation({
    mutationFn: (d: { actual_date: string }) => 
      http.post(`${BASE}/${id}/resumption`, d),
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ['leave', 'balances'],
    queryFn: () => http.get(`${BASE}/balances`),
  });
}

export function useLeaveHistory() {
  return useQuery({
    queryKey: ['leave', 'history'],
    queryFn: () => http.get(`${BASE}/history`),
  });
}

export function useLeaveQueue(userId: number) {
  return useQuery({
    queryKey: ['leave', 'queue', userId],
    queryFn: () => http.get(`${BASE}/queue`),
  });
}

export function useSubstituteAccept(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/substitute/accept`),
  });
}

export function useSubstituteDecline(id: number) {
  return useMutation({
    mutationFn: (d: { new_substitute_user_id?: number }) => 
      http.post(`${BASE}/${id}/substitute/decline`, d),
  });
}

export function useReviewLeave(id: number) {
  return useMutation({
    mutationFn: (d: { decision: string }) => 
      http.post(`${BASE}/${id}/review`, d),
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: ['leave', 'policy'],
    queryFn: () => http.get(`${BASE}/policy`),
  });
}

export function useCalendar() {
  return useQuery({
    queryKey: ['leave', 'calendar'],
    queryFn: () => http.get(`${BASE}/calendar`),
  });
}

export function useNotifications(userId: number) {
  return useQuery({
    queryKey: ['leave', 'notifications', userId],
    queryFn: () => http.get(`${BASE}/notifications`),
  });
}

export function useOfflineRecord() {
  return useMutation({
    mutationFn: (d: { category: string; start_date: string; end_date: string; reference_number?: string; evidence?: string }) => 
      http.post(`${BASE}/offline-record`, d),
  });
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

Generate the initial LeaveTasksPage React18/Mantine7 page as a default export. Provide the work queue using supplied task/application query hooks and available decision/substitute response API mutations. Use exact supplied types and names, with decision comments and simple controls. Do not add backend rules. Use React Query5 object syntax if needed, shared errorMessage from ../../../lib/http, named PageHeader from ../../../ui/components/PageHeader. No new authentication, database connections, dependencies or tests. Return concise complete TSX, maximum160 lines; no repeated placeholder methods. This is initial generation against the new model's own API, not a correctness review.

Output file: client/src/modules/leave_elm/pages/LeaveTasksPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 009 Frontend LeaveAdminPage

UTC: 2026-10-12T17:37:12.844741+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 4200}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/api/types.ts
```
import type { LeaveApplication } from '../models';

export interface LeaveRequest {
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  substitute_user_id?: number;
}

export interface LeaveResponse extends LeaveApplication {}

export type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

export interface Policy {
  CL_DAYS: number;
  RH_DAYS: number;
  SCL_MAX_DAYS: number;
  EL_DAYS: number;
  COL_DAYS: number;
  VL_DAYS: number;
  VL_TO_EL_RATIO: number;
}

export interface Calendar {
  year: number;
  holidays: Date[];
  restricted_holidays: Date[];
  is_effective: boolean;
}

export interface Notification {
  id: number;
  task_type: string;
  assigned_to_user_id: number;
  status: string;
  reminder_threshold_seconds: number;
  escalation_threshold_seconds: number;
  last_reminder_sent_at?: string;
  last_escalation_sent_at?: string;
}
```


### Repository file client/src/modules/leave_elm/api/hooks.ts
```
import { useQuery, useMutation } from '@tanstack/react-query';
import { http } from '../../../lib/http';
import type { LeaveRequest } from './types';

const BASE = '/leave';

export function useMyLeave() {
  return useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => http.get(`${BASE}/mine`),
  });
}

export function useApplyLeave(_data: LeaveRequest) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/apply`, d),
  });
}

export function useLeaveDetails(id: number) {
  return useQuery({
    queryKey: ['leave', 'detail', id],
    queryFn: () => http.get(`${BASE}/${id}`),
    enabled: !!id,
  });
}

export function useWithdrawLeave(id: number) {
  return useMutation({
    mutationFn: (d: LeaveRequest) => http.post(`${BASE}/${id}/withdraw`, d),
  });
}

export function useCancelLeave(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/cancel`),
  });
}

export function useExtendLeave(id: number) {
  return useMutation({
    mutationFn: (d: { additional_days: number }) => 
      http.post(`${BASE}/${id}/extend`, d),
  });
}

export function useResumption(id: number) {
  return useMutation({
    mutationFn: (d: { actual_date: string }) => 
      http.post(`${BASE}/${id}/resumption`, d),
  });
}

export function useLeaveBalances() {
  return useQuery({
    queryKey: ['leave', 'balances'],
    queryFn: () => http.get(`${BASE}/balances`),
  });
}

export function useLeaveHistory() {
  return useQuery({
    queryKey: ['leave', 'history'],
    queryFn: () => http.get(`${BASE}/history`),
  });
}

export function useLeaveQueue(userId: number) {
  return useQuery({
    queryKey: ['leave', 'queue', userId],
    queryFn: () => http.get(`${BASE}/queue`),
  });
}

export function useSubstituteAccept(id: number) {
  return useMutation({
    mutationFn: () => http.post(`${BASE}/${id}/substitute/accept`),
  });
}

export function useSubstituteDecline(id: number) {
  return useMutation({
    mutationFn: (d: { new_substitute_user_id?: number }) => 
      http.post(`${BASE}/${id}/substitute/decline`, d),
  });
}

export function useReviewLeave(id: number) {
  return useMutation({
    mutationFn: (d: { decision: string }) => 
      http.post(`${BASE}/${id}/review`, d),
  });
}

export function usePolicy() {
  return useQuery({
    queryKey: ['leave', 'policy'],
    queryFn: () => http.get(`${BASE}/policy`),
  });
}

export function useCalendar() {
  return useQuery({
    queryKey: ['leave', 'calendar'],
    queryFn: () => http.get(`${BASE}/calendar`),
  });
}

export function useNotifications(userId: number) {
  return useQuery({
    queryKey: ['leave', 'notifications', userId],
    queryFn: () => http.get(`${BASE}/notifications`),
  });
}

export function useOfflineRecord() {
  return useMutation({
    mutationFn: (d: { category: string; start_date: string; end_date: string; reference_number?: string; evidence?: string }) => 
      http.post(`${BASE}/offline-record`, d),
  });
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
    "@mantine/form": "7.13.4",
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

Generate the initial LeaveAdminPage React18/Mantine7 page as a default export. Provide administration configuration/calendar/record controls exposed by the supplied API, using exact supplied hook/function/type exports. Use simple JSON editors if needed. Do not add backend rules. Use React Query5 object syntax if needed, shared errorMessage from ../../../lib/http, named PageHeader from ../../../ui/components/PageHeader. No new authentication, database connections, dependencies or tests. Return concise complete TSX, maximum160 lines; no repeated placeholder methods. This is initial generation against the new model's own API, not a correctness review.

Output file: client/src/modules/leave_elm/pages/LeaveAdminPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 010 Frontend imported model type interfaces

UTC: 2026-10-12T17:40:11.007637+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen35-9b-trial/model-field-interfaces.md
```
LeavePolicy: CL_DAYS, RH_DAYS, SCL_MAX_DAYS, EL_DAYS, COL_DAYS, VL_DAYS, VL_TO_EL_RATIO
HolidayCalendar: year, is_effective, created_by_user_id
Holiday: calendar, date, type, name
VacationPeriod: year, start_date, end_date, name
OrganizationalUnit: code, name, parent_unit_id, unit_head_user_id
LeaveHierarchy: name, description
LeaveHierarchyStep: hierarchy, order, role_code, is_establishment_step
LeaveApplication: STATUS_CHOICES, category, user_id, start_date, end_date, purpose, station_leave_required, station_leave_details, substitute_user_id, substitute_consent_given, status, unit_head_user_id, hierarchy_step_order, final_decision_user_id, final_decision_date, final_decision_type, original_application_id, extension_incremental_days, actual_resumption_date, resumption_type, created_by_user_id, updated_by_user_id, submitted_by_user_id, withdrawn_by_user_id, cancelled_by_user_id
LeaveBalance: user_id, effective_date, cl_balance, rh_balance, scl_balance, el_balance, col_balance, vl_balance
LeaveTransaction: TRANSACTION_TYPE_CHOICES, application, user_id, transaction_type, category, quantity, balance_before, balance_after, reference_application_id, reference_transaction_id, processed_by_user_id, processed_at
WorkflowTask: TASK_TYPE_CHOICES, application, task_type, assigned_to_user_id, role_code, status, reminder_threshold_seconds, escalation_threshold_seconds, last_reminder_sent_at, last_escalation_sent_at, completed_at, completed_by_user_id
SLAEventLog: EVENT_TYPE_CHOICES, task, event_type, triggered_at, threshold_seconds, message
ResumptionRecord: application, user_id, actual_resumption_date, resumption_type, reviewed_by_user_id, reviewed_at, balance_adjustment

```


### Repository file modules/leave_elm/api/serializers.py
```
"""Leave Management serializers."""
from rest_framework import serializers
from datetime import date
from decimal import Decimal
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, WorkflowTask,
    SLAEventLog, HolidayCalendar, VacationPeriod,
    OrganizationalUnit, LeaveHierarchy, LeaveHierarchyStep, LeavePolicy
)

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'category', 'start_date', 'end_date', 'purpose', 
                  'station_leave_required', 'substitute_user_id', 'status',
                  'final_decision_type', 'final_decision_date', 'created_at']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['effective_date', 'cl_balance', 'rh_balance', 'scl_balance',
                  'el_balance', 'col_balance', 'vl_balance']

class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = ['id', 'task_type', 'assigned_to_user_id', 'status',
                  'reminder_threshold_seconds', 'escalation_threshold_seconds',
                  'last_reminder_sent_at', 'last_escalation_sent_at']

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ['year', 'is_effective', 'created_by_user_id']

class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ['year', 'start_date', 'end_date', 'name']

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ['CL_DAYS', 'RH_DAYS', 'SCL_MAX_DAYS', 'EL_DAYS', 
                  'COL_DAYS', 'VL_DAYS', 'VL_TO_EL_RATIO']

```


### Repository file client/src/modules/leave_elm/api/types.ts
```
import type { LeaveApplication } from '../models';

export interface LeaveRequest {
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  substitute_user_id?: number;
}

export interface LeaveResponse extends LeaveApplication {}

export type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

export interface Policy {
  CL_DAYS: number;
  RH_DAYS: number;
  SCL_MAX_DAYS: number;
  EL_DAYS: number;
  COL_DAYS: number;
  VL_DAYS: number;
  VL_TO_EL_RATIO: number;
}

export interface Calendar {
  year: number;
  holidays: Date[];
  restricted_holidays: Date[];
  is_effective: boolean;
}

export interface Notification {
  id: number;
  task_type: string;
  assigned_to_user_id: number;
  status: string;
  reminder_threshold_seconds: number;
  escalation_threshold_seconds: number;
  last_reminder_sent_at?: string;
  last_escalation_sent_at?: string;
}
```


END OF REFERENCES

CURRENT TASK

Provide the missing frontend models.ts type interfaces referenced by your earlier api/types.ts. Generate only TypeScript type/interface declarations LeaveApplication, LeaveBalance and WorkflowTask using the exact fields in the supplied backend model field list and serializers. No runtime functions, API operations, tests, business rules or dependencies. Maximum80 lines. Existing hooks and page logic must remain unchanged. This is completing the initial missing imported source file.

Output file: client/src/modules/leave_elm/models.ts
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 011 Frontend missing imported JSON editor helper

UTC: 2026-10-12T17:41:09.973278+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1600}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/leave_elm/pages/LeaveAdminPage.tsx
```
import { useState } from 'react';
import { Group, Stack, Text, Title, Paper, Button, TextInput, NumberInput, Select, ActionIcon, Divider, SimpleGrid } from '@mantine/core';
import { useJsonEditor } from '../../../lib/json-editor';
import { http } from '../../../lib/http';
import { PageHeader } from '../../../ui/components/PageHeader';
import { usePolicy, useCalendar, useLeaveBalances, useNotifications, useOfflineRecord } from '../api/hooks';

export default function LeaveAdminPage() {
  const [activeTab, setActiveTab] = useState<'policy' | 'calendar' | 'records'>('policy');
  
  const policyQuery = usePolicy();
  const calendarQuery = useCalendar();
  const balancesQuery = useLeaveBalances();
  const notificationsQuery = useNotifications(1); // Admin user ID placeholder
  const offlineMutation = useOfflineRecord();

  if (policyQuery.isLoading || calendarQuery.isLoading) return <Text>Loading...</Text>;
  if (!policyQuery.data || !calendarQuery.data) return <Text>Error loading data</Text>;

  const policy: any = policyQuery.data;
  const calendar: any = calendarQuery.data;

  const handlePolicyUpdate = (newPolicy: any) => {
    // In a real scenario, this would be an API call. Here we just log or show feedback.
    console.log('Updating policy:', newPolicy);
    offlineMutation.mutate({ category: 'CL', start_date: new Date().toISOString(), end_date: new Date().toISOString(), reference_number: 'POLICY_UPDATE' });
  };

  const handleCalendarUpdate = (newCalendar: any) => {
    console.log('Updating calendar:', newCalendar);
    offlineMutation.mutate({ category: 'CL', start_date: new Date().toISOString(), end_date: new Date().toISOString(), reference_number: 'CALENDAR_UPDATE' });
  };

  return (
    <>
      <PageHeader title="Leave Administration" subtitle="Manage policies, calendars, and records">
        <Group gap="sm">
          <Button variant="outline" onClick={() => setActiveTab('policy')}>Policy</Button>
          <Button variant={activeTab === 'calendar' ? 'filled' : 'outline'} onClick={() => setActiveTab('calendar')}>Calendar</Button>
          <Button variant={activeTab === 'records' ? 'filled' : 'outline'} onClick={() => setActiveTab('records')}>Records</Button>
        </Group>
      </PageHeader>

      {activeTab === 'policy' && (
        <Paper p="md" withBorder shadow="sm">
          <Title order={3} mb="md">Leave Policy Configuration</Title>
          <Stack gap="md">
            <Text c="dimmed">Current Policy Data:</Text>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              {Object.entries(policy).map(([key, value]) => (
                <Paper key={key} p="sm" withBorder radius="md">
                  <Text size="xs" c="dimmed">{key}</Text>
                  <Text fw={500}>{typeof value === 'number' ? value : JSON.stringify(value)}</Text>
                </Paper>
              ))}
            </SimpleGrid>
            
            <Divider my="md" />
            
            <Group justify="space-between">
              <Text c="dimmed">Edit Policy (Simulation):</Text>
              <Stack gap="sm">
                {useJsonEditor(policy, handlePolicyUpdate)}
              </Stack>
            </Group>
          </Stack>
        </Paper>
      )}

      {activeTab === 'calendar' && (
        <Paper p="md" withBorder shadow="sm">
          <Title order={3} mb="md">Calendar Configuration</Title>
          <Stack gap="md">
            <Text c="dimmed">Current Calendar Data:</Text>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <Paper p="sm" withBorder radius="md">
                <Text size="xs" c="dimmed">Year</Text>
                <Text fw={500}>{calendar.year}</Text>
              </Paper>
              <Paper p="sm" withBorder radius="md">
                <Text size="xs" c="dimmed">Effective</Text>
                <Text fw={500}>{calendar.is_effective ? 'Yes' : 'No'}</Text>
              </Paper>
            </SimpleGrid>

            <Divider my="md" />

            <Group justify="space-between">
              <Text c="dimmed">Edit Calendar (Simulation):</Text>
              <Stack gap="sm">
                {useJsonEditor(calendar, handleCalendarUpdate)}
              </Stack>
            </Group>
          </Stack>
        </Paper>
      )}

      {activeTab === 'records' && (
        <Paper p="md" withBorder shadow="sm">
          <Title order={3} mb="md">Offline Records & Notifications</Title>
          
          <Stack gap="md">
            <Group justify="space-between">
              <Text c="dimmed">Create Offline Record:</Text>
              <SimpleGrid cols={{ base: 1, md: 4 }} spacing="xs">
                <TextInput label="Category" placeholder="CL" />
                <TextInput label="Start Date" type="date" />
                <TextInput label="End Date" type="date" />
                <Button onClick={() => offlineMutation.mutate({ category: 'CL', start_date: new Date().toISOString(), end_date: new Date().toISOString() })}>
                  Submit Record
                </Button>
              </SimpleGrid>
            </Group>

            <Divider my="md" />

            <Text c="dimmed">Notifications:</Text>
            {notificationsQuery.data ? (
              notificationsQuery.data.map((notif: any) => (
                <Paper key={notif.id} p="sm" withBorder radius="md">
                  <Group justify="space-between">
                    <Stack gap={1}>
                      <Text fw={500}>{notif.task_type}</Text>
                      <Text size="xs" c="dimmed">User: {notif.assigned_to_user_id}</Text>
                    </Stack>
                    <Text size="xs" c="dimmed">{new Date(notif.last_reminder_sent_at).toLocaleString()}</Text>
                  </Group>
                </Paper>
              ))
            ) : (
              <Text c="dimmed">No notifications available.</Text>
            )}

            {offlineMutation.isPending && (
              <Text c="yellow" size="sm">Submitting offline record...</Text>
            )}
            
            {offlineMutation.error && (
              <Text c="red" size="sm">Error: {offlineMutation.error.message}</Text>
            )}
          </Stack>
        </Paper>
      )}
    </>
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
    "@mantine/form": "7.13.4",
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

Complete the missing local JSON editor helper imported by your generated LeaveAdminPage. Generate a single TSX file exporting useJsonEditor(value: any, onChange: (value: any) => void), returning the editor UI as a React node. Keep compatible with the supplied existing calls and Mantine7. No network requests, workflow logic changes, additional dependencies or tests. Do not change the admin page behavior. Maximum50 lines. This completes your initial frontend implementation rather than reviewing its functional correctness.

Output file: client/src/modules/leave_elm/json-editor.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 012 Documentation trial README, record and comparison

UTC: 2026-10-12T17:44:20.479989+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP ELM pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 16384, "num_batch": 128, "num_predict": 4200}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/elm-qwen35-9b-trial/documentation-context.md
```
# Verified observations for documentation

{
  "model": "qwen3.5:9b",
  "details": {
    "parent_model": "",
    "format": "safetensors",
    "family": "qwen3_5",
    "families": null,
    "parameter_size": "9.7B",
    "quantization_level": "nvfp4",
    "runner": "mlx"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "generation_requests": 11,
  "code_request_wall_seconds": 2504.01,
  "output_limit_requests": [
    "001",
    "003"
  ],
  "requests": [
    {
      "prompt": "001",
      "label": "Backend foundation",
      "wall_seconds": 604.65,
      "prompt_eval_count": 19787,
      "eval_count": 8192,
      "done_reason": "length"
    },
    {
      "prompt": "002",
      "label": "Complete missing public contracts",
      "wall_seconds": 64.58,
      "prompt_eval_count": 4231,
      "eval_count": 1173,
      "done_reason": "stop"
    },
    {
      "prompt": "003",
      "label": "Backend services and selectors",
      "wall_seconds": 826.37,
      "prompt_eval_count": 20865,
      "eval_count": 6500,
      "done_reason": "length"
    },
    {
      "prompt": "004",
      "label": "Complete missing selectors",
      "wall_seconds": 16.53,
      "prompt_eval_count": 623,
      "eval_count": 302,
      "done_reason": "stop"
    },
    {
      "prompt": "005",
      "label": "Backend API and scheduled work",
      "wall_seconds": 381.51,
      "prompt_eval_count": 13607,
      "eval_count": 4426,
      "done_reason": "stop"
    },
    {
      "prompt": "006",
      "label": "Frontend types, queries and route table",
      "wall_seconds": 178.53,
      "prompt_eval_count": 10290,
      "eval_count": 1443,
      "done_reason": "stop"
    },
    {
      "prompt": "007",
      "label": "Frontend MyLeavePage",
      "wall_seconds": 112.72,
      "prompt_eval_count": 2080,
      "eval_count": 1246,
      "done_reason": "stop"
    },
    {
      "prompt": "008",
      "label": "Frontend LeaveTasksPage",
      "wall_seconds": 88.45,
      "prompt_eval_count": 2078,
      "eval_count": 1240,
      "done_reason": "stop"
    },
    {
      "prompt": "009",
      "label": "Frontend LeaveAdminPage",
      "wall_seconds": 152.31,
      "prompt_eval_count": 2088,
      "eval_count": 1562,
      "done_reason": "stop"
    },
    {
      "prompt": "010",
      "label": "Frontend imported model type interfaces",
      "wall_seconds": 23.02,
      "prompt_eval_count": 1278,
      "eval_count": 220,
      "done_reason": "stop"
    },
    {
      "prompt": "011",
      "label": "Frontend missing imported JSON editor helper",
      "wall_seconds": 55.34,
      "prompt_eval_count": 2290,
      "eval_count": 691,
      "done_reason": "stop"
    }
  ],
  "checks": [
    {
      "label": "foundation-python-compilation",
      "returncode": 0,
      "wall_seconds": 0.05
    },
    {
      "label": "foundation-django-registration",
      "returncode": 1,
      "wall_seconds": 0.65
    },
    {
      "label": "foundation-registration-corrected",
      "returncode": 0,
      "wall_seconds": 0.57
    },
    {
      "label": "generate-elm-schema",
      "returncode": 0,
      "wall_seconds": 0.48
    },
    {
      "label": "isolated-foundation-schema-install",
      "returncode": 0,
      "wall_seconds": 0.21
    },
    {
      "label": "foundation-contract-compilation",
      "returncode": 0,
      "wall_seconds": 0.04
    },
    {
      "label": "plural-contract-interface-check",
      "returncode": 1,
      "wall_seconds": 0.03
    },
    {
      "label": "plural-contract-interface-corrected",
      "returncode": 0,
      "wall_seconds": 0.03
    },
    {
      "label": "service-syntax-check",
      "returncode": 0,
      "wall_seconds": 0.04
    },
    {
      "label": "service-selector-import-check",
      "returncode": 1,
      "wall_seconds": 0.54
    },
    {
      "label": "service-selector-import-corrected",
      "returncode": 0,
      "wall_seconds": 0.4
    },
    {
      "label": "backend-api-registration",
      "returncode": 1,
      "wall_seconds": 0.55
    },
    {
      "label": "backend-api-registration-corrected",
      "returncode": 0,
      "wall_seconds": 0.44
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0,
      "wall_seconds": 0.03
    },
    {
      "label": "schema-model-drift",
      "returncode": 0,
      "wall_seconds": 0.56
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0,
      "wall_seconds": 0.82
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1,
      "wall_seconds": 1.36
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0,
      "wall_seconds": 0.21
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0,
      "wall_seconds": 0.42
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0,
      "wall_seconds": 0.23
    },
    {
      "label": "backend-task-imports",
      "returncode": 0,
      "wall_seconds": 1.04
    },
    {
      "label": "api-schema-generation",
      "returncode": 0,
      "wall_seconds": 0.79
    },
    {
      "label": "permission-manifest-registration",
      "returncode": 1,
      "wall_seconds": 0.58
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2,
      "wall_seconds": 2.88
    },
    {
      "label": "frontend-after-interface-corrections",
      "returncode": 2,
      "wall_seconds": 1.95
    },
    {
      "label": "frontend-complete-typecheck",
      "returncode": 2,
      "wall_seconds": 1.59
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0,
      "wall_seconds": 1.52
    },
    {
      "label": "backend-final-registration",
      "returncode": 0,
      "wall_seconds": 0.62
    },
    {
      "label": "frontend-production-build",
      "returncode": 0,
      "wall_seconds": 4.4
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0,
      "wall_seconds": 0.03
    }
  ],
  "hardware_record": "Recorded in trial-metadata.json; exported identifiers redacted. Target reproduction PC is not measured trial hardware.",
  "functional_correctness": "Not evaluated; model logic preserved.",
  "full_baseline_migration": "Failed in pre-existing Placement0009 on disposable SQLite",
  "permission_manifest_registration": "Failed; no permission behavior repairs performed",
  "comparison_limits": "Same official base/specification exercise; prompt ordering, settings, runtime and quantization differ. Exploratory comparison only."
}

# First-model summary

{
  "model": "qwen2.5-coder:3b",
  "details": {
    "parameter_size": "3.1B",
    "quantization_level": "Q4_K_M",
    "format": "gguf",
    "runner": "ggml"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "generation_requests": 34,
  "code_request_wall_seconds": 1734.58,
  "output_limit_requests": [
    1,
    3,
    5,
    7,
    9
  ],
  "final_build_status": "Compilation, frontend production build, Django system checks, isolated ELM schema and import boundaries passed after mechanical integration corrections; full temporary SQLite migration failed in pre-existing Placement0009; workflow correctness unverified",
  "checks": [
    {
      "label": "Foundation Python compilation",
      "returncode": 0
    },
    {
      "label": "Foundation Python compilation after batch recovery",
      "returncode": 0
    },
    {
      "label": "Django foundation import and registration",
      "returncode": 1
    },
    {
      "label": "Django registration after mixin inheritance correction",
      "returncode": 1
    },
    {
      "label": "Generate schema migration from Qwen models",
      "returncode": 1
    },
    {
      "label": "Django model registration after related-name correction",
      "returncode": 0
    },
    {
      "label": "Generate schema migration from registered Qwen models",
      "returncode": 0
    },
    {
      "label": "backend-import-registration",
      "returncode": 1
    },
    {
      "label": "backend-api-imports",
      "returncode": 1
    },
    {
      "label": "backend-api-imports-corrected",
      "returncode": 0
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0
    },
    {
      "label": "schema-model-drift",
      "returncode": 0
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2
    },
    {
      "label": "frontend-after-interface-retries",
      "returncode": 2
    },
    {
      "label": "frontend-current-typecheck",
      "returncode": 2
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0
    },
    {
      "label": "frontend-production-build",
      "returncode": 0
    },
    {
      "label": "final-harness-compilation",
      "returncode": 0
    }
  ],
  "comparison_limits": "Same official base and specification exercise. Prompt ordering, configurations, quantization and runtimes differ; this is exploratory, not a controlled performance benchmark."
}


# Method and limits

# Qwen 3.5 9B ELM trial

Independent clean worktree from official latest main 02b01fea4a67b257ea7000009f06a1561699550e, identical to the first trial base. No first-model ELM application output was copied. Shared trial harness, specification extracts and initial task plans were reused.

The installed model supports thinking; requests explicitly set think=false to generate code without a separate thinking phase. Actual per-call settings and outputs will be recorded. Build/integration checks only; workflow bugs are to remain. This is an exploratory comparison, not a controlled performance benchmark.

During prompt001, ollama ps reported qwen3.5:9b using 7.7 GB, 100% GPU, context4096 and runnermlx despite requested num_ctx32768. Requested settings do not by themselves establish the runtime context actually used. This discrepancy is preserved rather than assuming identical effective settings across models.

Comparison limits: stage instructions and specification inputs are reused, but this trial uses the final evolved harness (references before CURRENT TASK), while early first-trial prompts used the older ordering. Model/runtime/quantization and thinking capability differ. This is the same implementation exercise, not byte-identical prompting or a controlled model-efficiency benchmark.

For API generation, removed repeated specification text from input because this stage wraps existing generated service/model interfaces, without changing their logic. Full specifications were provided to foundation/service stages. API request uses shorter interface-only context and requested context16384; exact payload will be logged.

Frontend interface generation uses requested context16384 and temperature0.2, with exact options saved in each request. First-model build/timing summary copied for later comparison only; its ELM application source was not used as second-model input.

Backend Django checks, syntax compilation, isolated schema/module seeding, import boundaries, migration drift, task imports and API schema generation passed. API schema emitted one operation-ID collision warning. Full temporary SQLite migration failed in baseline Placement0009. The repository permission-manifest registration command failed validation; its full output is retained in checks.log. No permission enforcement or application behavior was changed to pass that gate, in accordance with the mechanical-correction-only scope. This is partial integration success, not a claim that every repository gate passes.


# Mechanical corrections

# Mechanical integration corrections

Prompt001 truncated contracts.py; six complete preceding JSON file values were recovered unchanged. See 001.recovery.json for hashes. Registered modules.leave_elm in DOMAIN_MODULES and added empty package initializers. No model/domain/registry logic changed.

Django fields.E009: adapted LeaveApplication.category max_length2 to3 to fit existing declared choices. Choice values, other fields and logic unchanged. See mechanical-001.patch.

Plural-contract interface check rejected two extra scalar helpers generated by prompt002. Renamed get_holidays and get_vacation_periods to module-private _get_holidays/_get_vacation_periods; retained their signatures and bodies exactly. The requested plural getters are unchanged. No workflow logic repaired.

Prompt003 hit its output limit in selectors/leave.py. Recovered complete service and initializer strings unchanged; incomplete selector not applied.

Selector import corrected from .models (nonexistent selectors.models) to modules.leave_elm.models. No selector bodies changed. See mechanical-003.patch.

Import check found domain package exports referencing files the model did not generate. Removed only the nonexistent imports and matching __all__ names; retained exports from existing policy.py unchanged. No domain calculations or services changed. See mechanical-004.patch.

Registered ELM root API URLs, frontend static route import, Celery schedule/routes and import-boundary configuration. See integration-registration.patch.

API import/registration check failed because ViewSet.as_view lacked HTTP-to-action dictionaries. Adapted existing URL declarations to their existing action names, imported serializers and their LeavePolicy model, and converted the generated list schedule to Fusion/Celery mapping configuration with actual registered task names. Preserved paths, schedule intervals, action bodies and task logic. See mechanical-005.patch.

Normalized registered ELM API URL suffixes to Fusion/client paths without a trailing slash. Preserved endpoint/action mapping and all view bodies. See mechanical-006.patch. The preceding frontend prompt retains the exact earlier route excerpt it received.

Adapted frontend shared-http import placement, imported the already declared LeaveRequest type, removed unused imports and prefixed an unused parameter for existing strict compiler settings. Exported hook names, argument positions, request bodies and request operations unchanged. See mechanical-007.patch.

Added @mantine/form7.13.4 to package.json/package-lock.json to satisfy the model-generated employee-page import, matching the repository Mantine version. Replaced only the worktree dependency symlink with independent npm-installed dependencies; original checkout files remain untouched. No application behavior changed.

First TypeScript check recorded import/library-interface errors. Corrected Textarea/errorMessage imports, unused imports, Axios response-envelope access, explicit callback typings and non-null date-index typing. Changed unsupported button active prop to data-active. Preserved the model's unsupported form schema object using spread (no validation rules were implemented), and adapted the existing substitute-mutation argument transport to React Query5's single variables object with the same supplied values/request body. The unused apply-hook argument now accepts Partial<LeaveRequest>. No action buttons were connected or business logic repaired. See mechanical-008.patch.

Admin-page compiler adaptations: removed unused imports/binding while retaining the balance-hook call; adjusted shared PageHeader children to its actual action prop; corrected Axios notification envelope access; placed the missing model-generated JSON editor helper within the ELM module and adapted the import. No admin handler or request logic repaired. See mechanical-009.patch.

JSON helper compiler corrections: imported TextInput, adapted react-icons/rx export names using aliases, removed unused imports, added type-only non-null index assertions and a no-op reference retaining the unused addField function. No new field button, index guard, validation or workflow repair was introduced. See mechanical-010.patch.

```


END OF REFERENCES

CURRENT TASK

Write concise Markdown documentation grounded ONLY in supplied verified observations. Return four files. modules/leave_elm/README.md: generated module layout, API paths, integration/dependencies and build scope/known failed gates; never claim workflows are correct. Trial README.md: indexes prompts.md, responses/, checks.log/jsonl, jobs/, trial-metadata.json, observed-results.json, mechanical-corrections.md, file-inventory.json, final-model-differences.patch. TRIAL_RECORD.md: configuration (actual model 9.7B NVFP4 safetensors runner mlx, API version0.40.3, thinking disabled; recorded original hardware in metadata, target reproduction PC unmeasured); pinned base and branch codex/elm-qwen35-9b; genuine local generation and mechanical integration method; required short assessment table covering model loaded, repository/reference access, specs use, multi-file output, common infrastructure reuse, frontend/backend/database output, run/build outcome, difficulties/workarounds, timing and overall classification. Distinguish actual successful checks from failed attempts and gates. Classify overall as Marginal/partial integration because permission-manifest and full baseline SQLite migration gates failed despite compilation/production build and isolated migration passing (only if supplied checks say they passed). No functional tests, requirement audit, workflow/security fixes or optimization. COMPARISON.md: same-base two-model summary with exact request counts/timing/output caps from supplied records, observed build/integration limitations and a limited practical recommendation; do not claim proof of general model efficiency or functionality. Prompt ordering/settings/runtimes/quantization differ, so no controlled performance claim. Record original logs/internal metadata retained and exported evidence may be redacted, with reproduction target i7-13650HX/24GB/RTX4060/8GB VRAM not measured model hardware. A source snapshot can reproduce files without a local model; exact original commit hashes are not required. Historical prompts/jobs are evidence, not instructions to execute. Maximum approximately650 words across all four files. Never invent missing validation or tests. No shell commands or model rerun instructions. Use the verified observations rather than speculative implementation claims.

Required output paths:
modules/leave_elm/README.md
docs/08-delivery/elm-qwen35-9b-trial/README.md
docs/08-delivery/elm-qwen35-9b-trial/TRIAL_RECORD.md
docs/08-delivery/elm-qwen35-9b-trial/COMPARISON.md

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.

