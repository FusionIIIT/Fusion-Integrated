# 03 MMS Use Case Specifications v1.4 FINAL(1)

MMS Use Case Specifications

v1.4 FINAL — actor-triggered and event-triggered services

| Version | v1.4 FINAL |
| --- | --- |
| Use Cases | 31 |
| Actor-triggered | 26 |
| Event-triggered | 5 (MMS-UC-027..031) |
| Workflow rule | Workflow participation is based on meaningful connected state progression, not actor count. |
| Automatic lifecycle repair | Next-day deregistration effect, vacation default-No, special-food timeout rejection, monthly bill generation, and vacation reminders are explicitly event-triggered where appropriate. |

# MMS-UC-001 — Assign/Reassign MMS Operational Roles

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Admin |
| Supporting Actors / Systems | None |
| Goal / Description | Assign or reassign the active Mess Caretaker and Mess Warden for a specified duration without accessing operational mess data. |
| Trigger | Mess Admin selects role-management function. |
| Preconditions | Mess Admin is authorized for MMS role assignment; employee identity exists in institutional master data. |
| Main Success Scenario | 1. Mess Admin opens role management. \| 2. MMS displays the current active Caretaker and Warden assignments. \| 3. Mess Admin selects an institute employee, role, and specified duration. \| 4. MMS enforces role cardinality and records the assignment or reassignment. \| 5. For a mid-cycle reassignment, MMS makes the change immediately effective from the recorded reassignment time and transfers pending Caretaker-owned request visibility/actionability to the newly assigned Caretaker. |
| Alternative Flows | A1: If the requested assignment would violate the exactly-one-active-role constraint for its effective period, MMS prevents the conflicting assignment. \| A2: If required employee identity data is unavailable from institutional master data, MMS does not record the assignment. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Exactly one active Caretaker and one active Warden remain active; Mess Admin remains blocked from operational data. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-002 to BR-MMS-007 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | No workflow mapping: role assignment/reassignment is a single isolated service; the PS does not define a connected multi-UC state progression for it. |

# MMS-UC-002 — Open Registration Window

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | None |
| Goal / Description | Open a registration window for a mess cycle or designated period. |
| Trigger | Caretaker starts registration setup. |
| Preconditions | Caretaker is active for the period. |
| Main Success Scenario | 1. Caretaker opens registration-window setup. \| 2. Caretaker identifies the mess cycle or designated period and the registration window. \| 3. MMS records the window as open. \| 4. MMS permits Student registration submissions for the open window. |
| Alternative Flows | A1: If required window information is missing, MMS does not open the window and requests correction. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Registration window is open for the configured period. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-008 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Notes / TODO | None. |

# MMS-UC-003 — Submit Registration Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit a mess registration request during an open registration window. |
| Trigger | Student selects mess registration. |
| Preconditions | Student is authenticated; registration window is open. |
| Main Success Scenario | 1. Student opens mess registration.<br>2. System displays the active registration window.<br>3. Student enters required registration details.<br>4. Student submits the request.<br>5. System validates that the window is open.<br>6. System records the request as Pending.<br>7. System sends submission notification to the Student. |
| Alternative Flows | A1: If no window is open, system prevents submission.<br>A2: If required details are missing, system asks for correction. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Registration request is pending Caretaker decision; Student can track status/history. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-009, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Notes / TODO | None. |

# MMS-UC-004 — Review Registration Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Student |
| Goal / Description | Approve or reject a submitted registration request. |
| Trigger | Caretaker opens pending registration requests. |
| Preconditions | A registration request exists in Pending status. |
| Main Success Scenario | 1. Caretaker views pending registration requests.<br>2. Caretaker selects a request.<br>3. System displays submitted details and request history.<br>4. Caretaker approves or rejects the request.<br>5. System records the decision and updates status.<br>6. System sends decision notification to the Student. |
| Alternative Flows | A1: If request is no longer pending, system prevents duplicate decision. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Request is Approved or Rejected; decision is visible to Student and available for Warden oversight. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-010, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Notes / TODO | None. |

# MMS-UC-005 — Submit Deregistration Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit a mess deregistration request at any time. |
| Trigger | Student selects deregistration. |
| Preconditions | Student is currently registered for mess service. |
| Main Success Scenario | 1. Student opens deregistration request.<br>2. System displays current registration status.<br>3. Student confirms deregistration request.<br>4. System records the request as Pending.<br>5. System sends submission notification to the Student. |
| Alternative Flows | A1: If Student is not currently registered, system prevents request submission. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Deregistration request is pending Caretaker decision. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-012, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-03, BW-MMS-04, CW-MMS-02 |
| Notes / TODO | None. |

# MMS-UC-006 — Review Deregistration Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Student |
| Goal / Description | Approve or reject a submitted deregistration request. |
| Trigger | Caretaker opens pending deregistration requests. |
| Preconditions | A deregistration request exists in Pending status. |
| Main Success Scenario | 1. Caretaker views pending deregistration requests.<br>2. Caretaker selects a request.<br>3. MMS displays request details and history.<br>4. Caretaker approves or rejects the request.<br>5. MMS records the decision immediately and triggers the decision notification to the Student.<br>6. If approved, the request enters an Approved — Awaiting Effective Date state; the next-calendar-day service effect is handled by MMS-UC-027. |
| Alternative Flows | A1: If request is no longer pending, system prevents duplicate decision. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Request is Approved — Awaiting Effective Date or Rejected; a rejected Student remains registered, while an approved request awaits the next-calendar-day system transition. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-010, BR-MMS-013, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-03, BW-MMS-04, CW-MMS-02 |
| Notes / TODO | Approved deregistration service effect is separated into event-triggered MMS-UC-027 under DIRECT_FINAL_v2. |

# MMS-UC-007 — View Operational Student Requests for Oversight

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Warden |
| Supporting Actors / Systems | None |
| Goal / Description | View operational student requests for supervisory oversight without decision authority. |
| Trigger | Warden opens registration oversight view. |
| Preconditions | One or more operational student requests exist in MMS. |
| Main Success Scenario | 1. Warden opens the operational-request oversight view. \| 2. MMS displays request records permitted for supervisory oversight, including registration and deregistration requests and other operational student requests where represented. \| 3. Warden views or filters request details. \| 4. MMS does not expose approval, rejection, registration, deregistration, or other operational decision actions to the Warden. |
| Alternative Flows | A1: If the Warden attempts a decision action through any exposed path, MMS blocks the action. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Warden obtains oversight information; no operational request state is changed. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-011 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Broadened from registration/deregistration-only wording to match PS §3.2.4. Informational UC; not workflow-grounded. |

# MMS-UC-008 — Publish or Update Weekly Menu

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Students and other menu viewers |
| Goal / Description | Create, modify, delete, publish, or update day-wise and meal-wise weekly menu information. |
| Trigger | Caretaker opens menu management. |
| Preconditions | Caretaker is active. |
| Main Success Scenario | 1. Caretaker opens weekly menu.<br>2. System displays day-wise and meal-wise structure.<br>3. Caretaker adds, modifies, or deletes menu items.<br>4. System validates menu structure.<br>5. Caretaker publishes or updates the menu.<br>6. System sends menu-update notifications to Students. |
| Alternative Flows | A1: If structure is incomplete or invalid, system asks for correction. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Weekly menu is published/updated and visible to authorized viewers. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-014, BR-MMS-015, BR-MMS-039 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | No workflow mapping: weekly menu maintenance is a single isolated publication/update service; notification and viewing do not form additional state-changing transitions. |

# MMS-UC-009 — View Weekly Menu

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student / Mess Caretaker / Mess Warden |
| Supporting Actors / Systems | None |
| Goal / Description | View the day-wise and meal-wise weekly menu according to actor access rights. |
| Trigger | Actor opens menu view. |
| Preconditions | Weekly menu exists or view is available. |
| Main Success Scenario | 1. Authorized actor opens the weekly menu. \| 2. MMS displays the day-wise breakfast, lunch, and dinner menu. \| 3. Actor views menu details. |
| Alternative Flows | A1: Mess Admin menu visibility is not fixed here because the frozen PS is internally inconsistent on that point; see ISS-MMS-012. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Actor views the available weekly menu. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-038 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Mess Admin menu access remains Needs Clarification because PS §3.3.2 conflicts with PS §3.2.1/§3.3.11. |

# MMS-UC-010 — Review, Finalize, and Publish Monthly Bills

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Students |
| Goal / Description | Review system-generated monthly bills, finalize them, and publish finalized bills to Students. |
| Trigger | Generated monthly bills are available for Caretaker review. |
| Preconditions | MMS-UC-030 has generated the monthly bills for the applicable calendar-month billing cycle. |
| Main Success Scenario | 1. Caretaker opens the generated monthly bills.<br>2. MMS displays the generated bill details and computation results.<br>3. Caretaker reviews the bills.<br>4. Caretaker finalizes the bills.<br>5. Caretaker publishes the finalized bills.<br>6. MMS makes published bills available to Students and triggers the bill-publication notification. |
| Alternative Flows | A1: If the Caretaker does not finalize a generated bill, MMS does not publish that bill. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Finalized monthly bills are visible to Students. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-018, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-16 |
| Notes / TODO | Monthly computation is separated into event-triggered MMS-UC-030; this UC owns Caretaker review, finalization, and publication. |

# MMS-UC-011 — View Monthly Bills and Outstanding Balances

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | View monthly mess bills and outstanding balances. |
| Trigger | Student opens bill view. |
| Preconditions | Student has bill or balance information in MMS. |
| Main Success Scenario | 1. Student opens billing section.<br>2. System displays monthly bills.<br>3. System displays outstanding balance.<br>4. Student views bill details. |
| Alternative Flows | A1: If no bill exists for a month, system displays no bill for that month. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Student obtains actor-visible billing information. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-040 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | None. |

# MMS-UC-012 — Submit Feedback

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit text feedback related to mess services. |
| Trigger | Student opens feedback form. |
| Preconditions | Student is authenticated. |
| Main Success Scenario | 1. Student opens feedback form.<br>2. Student enters text feedback.<br>3. Student submits feedback.<br>4. System stores the feedback entry. |
| Alternative Flows | A1: If feedback text is empty, system asks for text input. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Feedback is stored for Caretaker and Warden monitoring/reporting. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-020 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | None. |

# MMS-UC-013 — View Feedback

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker / Mess Warden |
| Supporting Actors / Systems | None |
| Goal / Description | View stored feedback entries for monitoring and reporting. |
| Trigger | Caretaker or Warden opens feedback view. |
| Preconditions | Feedback entries exist. |
| Main Success Scenario | 1. Actor opens feedback list.<br>2. System displays feedback entries according to role access.<br>3. Actor reviews entries. |
| Alternative Flows | A1: If no feedback exists, system displays empty feedback list. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Actor views stored feedback. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-020 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | No formal feedback-resolution process is introduced; viewing is informational. |

# MMS-UC-014 — Submit Rebate Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit a rebate request with reason and date range. |
| Trigger | Student opens rebate request. |
| Preconditions | Student is registered for mess service. |
| Main Success Scenario | 1. Student opens rebate request form.<br>2. System displays required fields: reason, explanation where applicable, start date, and end date.<br>3. Student enters request details.<br>4. System validates minimum duration, lead time, and non-overlap.<br>5. System records valid request as Pending.<br>6. System sends submission notification to Student. |
| Alternative Flows | A1: If duration is below three days, system rejects submission.<br>A2: If start date is less than one calendar day ahead, system rejects submission.<br>A3: If request overlaps another rebate request, system rejects submission. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Rebate request is pending Caretaker decision and trackable by Student. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-021 to BR-MMS-024, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03 |
| Notes / TODO | None. |

# MMS-UC-015 — Review Rebate Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Student |
| Goal / Description | Approve, reject, or modify dates before approving a rebate request. |
| Trigger | Caretaker opens pending rebate requests. |
| Preconditions | A rebate request exists in Pending status. |
| Main Success Scenario | 1. Caretaker opens a Pending rebate request. \| 2. MMS displays the submitted reason and requested dates. \| 3. Caretaker may modify the dates before approval where permitted by external mess policy. \| 4. Caretaker approves or rejects the request. \| 5. MMS records Approved or Rejected status. \| 6. For approval, MMS uses the approved dates for automatic billing adjustment. \| 7. MMS triggers the decision notification to the Student. |
| Alternative Flows | A1: If request is no longer pending, system prevents duplicate decision. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Rebate is Approved or Rejected; approved rebates adjust monthly billing. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-019, BR-MMS-025, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03 |
| Notes / TODO | Permitted date modifications are constrained by external policy; limits are not invented here. |

# MMS-UC-016 — Create Vacation Food Continuity Survey

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Registered Students |
| Goal / Description | Create a vacation food continuity survey for upcoming institute vacation. |
| Trigger | Caretaker creates survey. |
| Preconditions | Upcoming institute vacation exists as institutional context. |
| Main Success Scenario | 1. Caretaker opens vacation-survey creation.<br>2. Caretaker identifies the upcoming vacation and sets the response deadline.<br>3. MMS creates the survey for currently registered Students only.<br>4. MMS triggers the survey-creation notification. |
| Alternative Flows | A1: If no response deadline is supplied, MMS does not create the survey.<br>A2: Reminder timing/cadence is not specified by the frozen PS; reminder delivery is represented separately by event-triggered MMS-UC-031 without inventing a schedule. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Survey is available only to currently registered Students until deadline. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-026, BR-MMS-027, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-08, BW-MMS-09, BW-MMS-10, CW-MMS-04 |
| Notes / TODO | Automatic default-No handling is MMS-UC-028. Autonomous reminder sending is MMS-UC-031. |

# MMS-UC-017 — Respond to Vacation Food Continuity Survey

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit Yes or No response to a vacation food continuity survey. |
| Trigger | Registered Student receives or opens survey. |
| Preconditions | Student is currently registered; survey is open. |
| Main Success Scenario | 1. Student opens survey.<br>2. System displays Yes/No response options.<br>3. Student selects Yes or No.<br>4. Student submits response.<br>5. System records response. |
| Alternative Flows | A1: If the Student is not currently registered or the survey is not open, MMS prevents response submission. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | An explicit Yes or No response is recorded before the deadline. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-041 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-08, BW-MMS-09, CW-MMS-04 |
| Notes / TODO | Non-response at deadline is not a Student alternative flow; it is handled by event-triggered MMS-UC-028. |

# MMS-UC-018 — View Vacation Survey Response Summary

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | None |
| Goal / Description | View the vacation food continuity response list and summary for operational planning. |
| Trigger | Caretaker opens survey response view. |
| Preconditions | Survey exists. |
| Main Success Scenario | 1. Caretaker opens a vacation survey response view. \| 2. MMS displays recorded Yes, No, and default-No responses and the summary. \| 3. Caretaker reviews the information for planning. |
| Alternative Flows | A1: If no responses exist, MMS displays the available empty/zero response summary. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Caretaker obtains response information; no survey or response state is changed. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-026, BR-MMS-027 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Renamed to remove unsupported “Manage” behavior. Informational UC; not workflow-grounded. |

# MMS-UC-019 — Submit Special Food Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | Submit special food request due to illness or personal event at least one calendar day before requested date. |
| Trigger | Student opens special food request. |
| Preconditions | Student is authenticated. |
| Main Success Scenario | 1. Student opens the special-food request form. \| 2. Student enters the request reason/context and requested date. \| 3. MMS validates the one-calendar-day lead-time rule. \| 4. MMS records a valid request as Requested and maintains request history. \| 5. MMS triggers the submission notification to the Student. |
| Alternative Flows | A1: If lead time is not met, system rejects submission. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Special food request is Requested and awaiting Caretaker decision. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-028, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Notes / TODO | None. |

# MMS-UC-020 — Review Special Food Request

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Student |
| Goal / Description | Approve or reject a Requested special-food request within the institution-defined decision period. |
| Trigger | Caretaker opens special food requests. |
| Preconditions | Special food request exists in Requested state. |
| Main Success Scenario | 1. Caretaker opens a Requested special-food request.<br>2. MMS displays request details and request time.<br>3. Caretaker approves or rejects the request within the institution-defined decision period.<br>4. MMS records Approved or Rejected status and triggers the applicable decision notification. |
| Alternative Flows | A1: If the request is no longer in Requested state, MMS prevents a second decision.<br>A2: The frozen PS mentions 12 hours as an intended period but does not freeze the value; this specification leaves the parameter institution-defined. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Request becomes Approved or explicitly Rejected; an Approved request may proceed to fulfillment. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-029, BR-MMS-031, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Notes / TODO | If no Caretaker decision occurs within the stipulated period, event-triggered MMS-UC-029 performs the default rejection. Exact period remains ISS-MMS-013. |

# MMS-UC-021 — Update Special Food Fulfillment Status

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | Student |
| Goal / Description | Record a post-approval fulfillment status of Served or Cancelled for a special-food request. |
| Trigger | Caretaker updates fulfillment. |
| Preconditions | Special food request is Approved. |
| Main Success Scenario | 1. Caretaker opens an Approved special-food request. \| 2. Caretaker selects Served or Cancelled. \| 3. MMS validates that the current state is Approved. \| 4. MMS records the new fulfillment state. \| 5. MMS triggers the applicable fulfillment-status notification to the Student. |
| Alternative Flows | A1: If the request is not Approved, MMS prevents a Served or Cancelled transition. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Request is Served or Cancelled; the billing treatment of a later Cancelled state is not resolved by the frozen PS. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-030, BR-MMS-031, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Notes / TODO | Caretaker ownership of Served/Cancelled updates is retained from the prior UC but is not explicit in the PS; see ISS-MMS-014. Billing treatment after Cancelled is also unclear; see ISS-MMS-015. |

# MMS-UC-022 — Publish Announcement

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker / Mess Warden |
| Supporting Actors / Systems | Students |
| Goal / Description | Publish mess-related announcements. |
| Trigger | Caretaker or Warden opens announcement publication. |
| Preconditions | Actor is authorized to publish announcements. |
| Main Success Scenario | 1. Authorized Caretaker or Warden opens announcement publication. \| 2. Actor enters a mess-related announcement. \| 3. Actor publishes the announcement. \| 4. MMS records it in announcement history and triggers the new-announcement notification to Students. |
| Alternative Flows | A1: MMS prevents publication by an actor other than the active Caretaker or Warden. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Announcement is published and visible in history. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-032, BR-MMS-033, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | No workflow mapping: announcement publication is a single isolated state-changing service; notification/history viewing are not state-changing workflow steps. |

# MMS-UC-023 — View Announcement History

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | All MMS actors, subject to access rights |
| Supporting Actors / Systems | None |
| Goal / Description | View announcement history relevant to mess services according to access rights. |
| Trigger | Actor opens announcements. |
| Preconditions | Announcement history exists or view is available. |
| Main Success Scenario | 1. Actor opens announcement history.<br>2. System displays mess-relevant announcements according to access rights.<br>3. Actor views announcement details. |
| Alternative Flows | A1: If no announcement exists, system displays empty history. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Actor views announcement history. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-033 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Mess Admin announcement-history access is interpreted through stated access rights; no operational-data privilege is added. |

# MMS-UC-024 — View and Search Supervisory Reports

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Warden |
| Supporting Actors / Systems | None |
| Goal / Description | View and search registered student lists, rebate summaries, and vacation survey response summaries. |
| Trigger | Warden opens reports. |
| Preconditions | Report data exists in MMS. |
| Main Success Scenario | 1. Warden opens reports.<br>2. System displays available supervisory report types.<br>3. Warden selects registered student list, rebate summary, or vacation response summary.<br>4. Warden searches or views report data. |
| Alternative Flows | A1: If requested report data is unavailable, system displays no data. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Warden obtains supervisory report information within MMS scope. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Informational/reporting UC; not workflow-grounded. |

# MMS-UC-025 — Generate Operational Reports

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Mess Caretaker |
| Supporting Actors / Systems | None |
| Goal / Description | Generate registration trend, special meal log, and billing summary reports. |
| Trigger | Caretaker opens operational reports. |
| Preconditions | Operational report data exists in MMS. |
| Main Success Scenario | 1. Caretaker opens operational reports.<br>2. System displays available operational report types.<br>3. Caretaker selects report type.<br>4. System generates the selected report. |
| Alternative Flows | A1: If report data is unavailable, system displays no data. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Caretaker obtains operational report within MMS scope. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Operational report generation is a bounded reporting service rather than a connected business-state progression. |

# MMS-UC-026 — Track Submitted Request Status and History

| UC Type | Actor-triggered |
| --- | --- |
| Primary Actor | Student |
| Supporting Actors / Systems | None |
| Goal / Description | View the status and history of the Student’s own submitted MMS requests. |
| Trigger | Student opens request status/history view. |
| Preconditions | Student has submitted one or more MMS requests, or the status/history view is available. |
| Main Success Scenario | 1. Student opens the request status/history view.<br>2. MMS displays the Student’s submitted MMS requests.<br>3. MMS displays current status and recorded history for each listed request.<br>4. Student views request details. |
| Alternative Flows | A1: If the Student has no submitted requests, MMS displays an empty request history.<br>A2: If the Student attempts to access another Student’s request history, MMS prevents access. |
| Exception Flows | Invalid or unauthorized actions are rejected without committing an invalid business-state change; specific exceptions are listed in Alternative Flows where source-supported. |
| Success Postcondition | Student views actor-visible request status/history for the Student’s own submitted requests. |
| Failure / Minimal Guarantee | No unauthorized or invalid business-state change is committed; existing valid records and previously recorded history remain intact. |
| Related Business Rules | BR-MMS-042 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Informational UC; not workflow-grounded. |

# MMS-UC-027 — Activate Approved Deregistration

| UC Type | Event-triggered |
| --- | --- |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | Student (affected service recipient) |
| Goal / Description | Apply the next-calendar-day service effect for a previously approved deregistration request. |
| Trigger | The next calendar day begins after Caretaker approval of a deregistration request. |
| Preconditions | A deregistration request is in Approved — Awaiting Effective Date state. |
| Main Success Scenario | 1. The next calendar day after approval begins.<br>2. MMS identifies approved deregistration requests whose service effect is due.<br>3. MMS makes the deregistration effective for mess service.<br>4. MMS records the resulting lifecycle state/history. |
| Alternative Flows | A1: If the request is no longer eligible for the transition because its state has validly changed, MMS does not apply the transition. |
| Exception Flows | A processing failure shall not create a partial or contradictory registration state; the previously recorded approval remains available for recovery. |
| Success Postcondition | The Student is deregistered for mess service from the next calendar day, as required by the frozen PS. |
| Failure / Minimal Guarantee | The approved request and prior registration state remain recorded consistently until the event-triggered transition can be completed. |
| Related Business Rules | BR-MMS-013 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-03, CW-MMS-02 |
| Notes / TODO | Event-triggered UC introduced by DIRECT_FINAL_v2; no new timing policy is invented. |

# MMS-UC-028 — Apply Default Vacation Response at Deadline

| UC Type | Event-triggered |
| --- | --- |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | Registered Students with no recorded response |
| Goal / Description | Record No for each currently registered Student who has not responded to an open vacation food-continuity survey by its response deadline. |
| Trigger | The configured response deadline for a vacation food-continuity survey is reached. |
| Preconditions | The survey exists; a response deadline was set; one or more currently registered Students have no recorded response. |
| Main Success Scenario | 1. The survey response deadline is reached.<br>2. MMS identifies currently registered Students with no recorded response.<br>3. MMS records No as the default response for each such Student.<br>4. MMS makes the defaulted responses available in the survey response summary. |
| Alternative Flows | A1: Students with an explicit Yes or No response are left unchanged.<br>A2: If no registered Student lacks a response, no default response record is created. |
| Exception Flows | A processing failure shall not overwrite explicit responses or create duplicate response records. |
| Success Postcondition | Each applicable non-responding registered Student has a recorded default No response. |
| Failure / Minimal Guarantee | Existing explicit responses remain unchanged and valid. |
| Related Business Rules | BR-MMS-027 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-10, CW-MMS-04 |
| Notes / TODO | Event-triggered UC introduced by DIRECT_FINAL_v2; the deadline itself is configured by the Caretaker in MMS-UC-016. |

# MMS-UC-029 — Default-Reject Undecided Special Food Request

| UC Type | Event-triggered |
| --- | --- |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | Student (notification recipient) |
| Goal / Description | Reject a special-food request automatically when it remains undecided after the institution-defined stipulated decision period. |
| Trigger | The institution-defined stipulated decision period expires for a special-food request still in Requested state. |
| Preconditions | A special-food request exists in Requested state and no Caretaker decision has been recorded within the stipulated period. |
| Main Success Scenario | 1. The stipulated decision period expires.<br>2. MMS verifies that the request remains Requested and undecided.<br>3. MMS changes the request state to Rejected (Default).<br>4. MMS records the lifecycle/history update.<br>5. MMS triggers the rejection-outcome notification to the Student. |
| Alternative Flows | A1: If the Caretaker has already approved or rejected the request, MMS does not perform the default rejection. |
| Exception Flows | A processing failure shall not create both an explicit and a default decision for the same request. |
| Success Postcondition | The undecided request is Rejected (Default) and the rejection outcome is recorded/notified. |
| Failure / Minimal Guarantee | The request remains in its last valid state with no duplicate decision. |
| Related Business Rules | BR-MMS-029, BR-MMS-031, BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-12, CW-MMS-05 |
| Notes / TODO | The exact decision-period value remains institution-defined per ISS-MMS-013. |

# MMS-UC-030 — Generate Monthly Mess Bills

| UC Type | Event-triggered |
| --- | --- |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | Mess Caretaker (subsequent reviewer) |
| Goal / Description | Generate the monthly mess bills for a calendar-month billing cycle from the source-defined charge and deduction components. |
| Trigger | A calendar-month billing cycle becomes due for bill generation. |
| Preconditions | Served-day data, approved special-meal/add-on charges, and approved rebate deductions applicable to the billing month are available in MMS. |
| Main Success Scenario | 1. The monthly billing event occurs for the applicable calendar month.<br>2. MMS determines served-day charges using the applicable daily-rate input.<br>3. MMS includes approved special-meal/add-on charges.<br>4. MMS applies approved rebate deductions.<br>5. MMS generates the monthly bill records in Generated state for Caretaker review. |
| Alternative Flows | A1: If required bill-input data is unavailable, MMS does not mark the affected bill as ready for Caretaker finalization. |
| Exception Flows | A computation or data-access failure shall not publish an incomplete or unfinalized bill. |
| Success Postcondition | Monthly bill records exist in Generated state and are available to the Caretaker for review/finalization/publication through MMS-UC-010. |
| Failure / Minimal Guarantee | No incomplete bill is published; source billing data remains unchanged. |
| Related Business Rules | BR-MMS-016, BR-MMS-017, BR-MMS-019, BR-MMS-030 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-MMS-16 |
| Notes / TODO | Event-triggered UC introduced because DIRECT_FINAL_v2 permits automatic system services as UCs; no specific day/time within the calendar month is invented. |

# MMS-UC-031 — Send Vacation Survey Reminder

| UC Type | Event-triggered |
| --- | --- |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | Registered Students with an open survey |
| Goal / Description | Trigger the required vacation food-continuity survey reminder email for applicable registered Students. |
| Trigger | An institution-defined reminder event occurs while the vacation survey remains open. |
| Preconditions | A vacation food-continuity survey exists and is open for currently registered Students. |
| Main Success Scenario | 1. A reminder event occurs for the open survey.<br>2. MMS identifies the applicable currently registered Students.<br>3. MMS triggers the system-generated survey reminder email through the external email infrastructure. |
| Alternative Flows | A1: If the survey is no longer open, MMS does not trigger an open-survey reminder. |
| Exception Flows | External email-delivery failure handling is outside MMS scope unless separately specified. |
| Success Postcondition | The MMS reminder event has been triggered for the applicable survey recipients. |
| Failure / Minimal Guarantee | Survey and response records remain unchanged. |
| Related Business Rules | BR-MMS-035 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Reminder timing/cadence remains unspecified by the frozen PS (ISS-MMS-019); this UC models the service without inventing a schedule. |

MMS Use Case Specifications

v1.4 FINAL — actor-triggered and event-triggered services

# MMS-UC-001 — Assign/Reassign MMS Operational Roles

# MMS-UC-002 — Open Registration Window

# MMS-UC-003 — Submit Registration Request

# MMS-UC-004 — Review Registration Request

# MMS-UC-005 — Submit Deregistration Request

# MMS-UC-006 — Review Deregistration Request

# MMS-UC-007 — View Operational Student Requests for Oversight

# MMS-UC-008 — Publish or Update Weekly Menu

# MMS-UC-009 — View Weekly Menu

# MMS-UC-010 — Review, Finalize, and Publish Monthly Bills

# MMS-UC-011 — View Monthly Bills and Outstanding Balances

# MMS-UC-012 — Submit Feedback

# MMS-UC-013 — View Feedback

# MMS-UC-014 — Submit Rebate Request

# MMS-UC-015 — Review Rebate Request

# MMS-UC-016 — Create Vacation Food Continuity Survey

# MMS-UC-017 — Respond to Vacation Food Continuity Survey

# MMS-UC-018 — View Vacation Survey Response Summary

# MMS-UC-019 — Submit Special Food Request

# MMS-UC-020 — Review Special Food Request

# MMS-UC-021 — Update Special Food Fulfillment Status

# MMS-UC-022 — Publish Announcement

# MMS-UC-023 — View Announcement History

# MMS-UC-024 — View and Search Supervisory Reports

# MMS-UC-025 — Generate Operational Reports

# MMS-UC-026 — Track Submitted Request Status and History

# MMS-UC-027 — Activate Approved Deregistration

# MMS-UC-028 — Apply Default Vacation Response at Deadline

# MMS-UC-029 — Default-Reject Undecided Special Food Request

# MMS-UC-030 — Generate Monthly Mess Bills

# MMS-UC-031 — Send Vacation Survey Reminder
