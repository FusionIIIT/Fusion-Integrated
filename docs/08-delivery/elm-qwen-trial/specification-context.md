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
