# Mess Management System blueprint

| Assignment input | Value |
| --- | --- |
| Module and code | Mess Management System, mms |
| Environment | module-only |
| Development branch | module/mms from upstream main at 5595be6628b4cdc6f8b47cf74bac267a2470f780 |
| Docs directory | docs/10-mms |
| Source IDs | MMS-UC, BR-MMS, BW-MMS, CW-MMS, CFR-MMS and AFR-MMS |
| Review status | Draft for review. Section H records decisions that still need a ruling. |

The source set is the synchronized MMS Problem Statement v1.0, the v1.4 Requirements Registry, Use Case Specifications, Business Rule Specifications and Workflow Specifications, and the v1.4 Traceability Matrix. These are the reference documents supplied for the assignment. The verified local baseline uses the public development fixture with IAM revision 9eef142b6eda23972e156538083713ff9f7d3ad6.

## A. Traceability

Each live specification ID has its own row. The enforcement names are proposed responsibilities, independent of the final Python symbol names. Tests will cite the complete source ID and cover its applicable outcomes. The 41 active rules exclude retired BR-MMS-037, and the requirements list uses the live CFR and AFR identifiers.

### Business rules

| ID | What it requires | Layer | Planned enforcement | Notes |
| --- | --- | --- | --- | --- |
| BR-MMS-001 | Remain limited to the mess-management functions and explicit integrations/notification triggers defined in the frozen problem statement | Boundary | MMS model, route and integration inventory | — |
| BR-MMS-002 | MMS may use institutional employee identity data needed for Mess Caretaker and Mess Warden assignment, but MMS shall not own employee master-data management | Service | Verify employee identity with the directory contract | — |
| BR-MMS-003 | Enforce exactly one active Mess Caretaker at a time | Model and service | Caretaker duty range constraint and transactional handoff | — |
| BR-MMS-004 | Enforce exactly one active Mess Warden at a time | Model and service | Warden duty range constraint and transactional handoff | — |
| BR-MMS-005 | Prevent Mess Admin from accessing operational mess data, student requests, billing, or feedback | Registry and selector | Deny Admin operational data and filter visible rows | — |
| BR-MMS-006 | A mid-cycle Caretaker or Warden reassignment takes effect immediately in MMS from the recorded reassignment time | Service | Immediately close prior duty and record successor at the same instant | — |
| BR-MMS-007 | After Caretaker reassignment, MMS shall make pending operational requests visible and actionable by the newly assigned Caretaker | Selector and service | Authorize pending work against its current Caretaker | — |
| BR-MMS-008 | Only the active Mess Caretaker opens the registration window for a mess cycle or designated period | Service | Create a cycle registration window with valid boundaries | — |
| BR-MMS-009 | Allow Student registration requests only while the registration window is open | Service | Check window at the time of student submission | — |
| BR-MMS-010 | Only the active Mess Caretaker may approve or reject registration and deregistration requests. The Mess Warden has oversight-only access | Service | Check active Caretaker and apply a valid request transition | — |
| BR-MMS-011 | The Mess Warden may view operational student requests for oversight but may not approve, reject, register, deregister, or otherwise decide those requests | Registry and selector | Grant oversight reads and withhold all decision verbs | — |
| BR-MMS-012 | Allow Students to submit deregistration requests at any time | Service | Accept deregistration from a registered student independently of the window | — |
| BR-MMS-013 | Make an approved deregistration effective from the next calendar day after Caretaker approval | Domain and scheduler | Calculate next institute calendar date and apply due change | — |
| BR-MMS-014 | Store weekly menu information day-wise and meal-wise for breakfast, lunch, and dinner | Model | Validate menu date, weekday and meal category | — |
| BR-MMS-015 | Trigger system-generated email notifications to Students when weekly menu updates are published | Service | Persist update event with the menu transaction | — |
| BR-MMS-016 | Generate mess bills using the monthly calendar-month cycle | Domain and scheduler | Use institute-local calendar-month boundaries | — |
| BR-MMS-017 | MMS monthly billing shall include daily-rate multiplied by number of served days, charges for approved special meals, and automatic deductions for approved rebates | Domain and ledger | Compute served-day charges, special meals and rebate deductions | — |
| BR-MMS-018 | Require Caretaker review and finalization before monthly bills are published to Students | Service | Require Caretaker finalization before publication | — |
| BR-MMS-019 | Apply rebate deductions to monthly bills only for approved rebate requests | Domain and ledger | Include only approved rebate amounts | — |
| BR-MMS-020 | Store Student text feedback and make feedback visible to Caretaker and Warden for monitoring and reporting | Model and selector | Persist feedback and restrict staff review | — |
| BR-MMS-021 | Reject rebate requests with a requested duration of fewer than three days | Domain | Require at least three inclusive calendar days | — |
| BR-MMS-022 | Reject rebate requests not submitted at least one calendar day before the rebate start date | Domain | Require submission before the start date by at least one local day | — |
| BR-MMS-023 | Prevent overlapping rebate requests | Model and service | Serialize conflicting rebate intervals for each student | Resolve overlap after rejection. |
| BR-MMS-024 | Require Student rebate requests to specify a reason and shall require explanation when the reason is Other | Domain | Validate reason category and explanation for Other | — |
| BR-MMS-025 | The Caretaker may modify rebate dates before approval only where permitted by the external mess policy. Approved dates become the dates used by MMS for billing adjustment | Service and ledger | Check external policy and calculate from approved dates | — |
| BR-MMS-026 | Send vacation food continuity surveys only to currently registered Students | Selector and service | Restrict survey distribution to currently registered students | — |
| BR-MMS-027 | Record No as the default response for registered Students who do not respond before the response deadline | Scheduler and service | Default to No for due eligible nonresponses | — |
| BR-MMS-028 | Allow special food requests only when submitted at least one calendar day before the requested date | Domain | Require at least one local calendar day of lead time | — |
| BR-MMS-029 | Mark a special food request as Rejected if the Caretaker does not decide within the institution-defined decision period of receiving the request | Scheduler and service | Reject overdue requests still in Requested | ISS-MMS-013 |
| BR-MMS-030 | Approved special-food requests are chargeable and their charges are added to the Student monthly bill | Ledger | Charge an approved request from its source identity | ISS-MMS-015 |
| BR-MMS-031 | Track special food requests using Requested, Approved, Rejected, Served, and Cancelled states; Served and Cancelled shall occur only after Approved | Domain and service | Apply a declared special-food transition and record history | ISS-MMS-014 and ISS-MMS-015 |
| BR-MMS-032 | Only the active Mess Caretaker or Mess Warden may publish mess-related announcements | Registry and service | Authorize Caretaker and Warden publication for mess-relevant announcements | — |
| BR-MMS-033 | Maintain mess-relevant announcement history and allow MMS actors to view it according to access rights | Model and selector | Keep announcement history within actor access rights | — |
| BR-MMS-034 | Restrict supervisory reports to Warden and operational reports to Caretaker as stated in the frozen problem statement | Registry and selector | Filter supervisory and operational report shapes by role | — |
| BR-MMS-035 | MMS triggers system-generated email notifications only for the MMS events explicitly listed in the frozen problem statement. External email delivery infrastructure remains outside MMS | Service and adapter | Use an allowlist of spec events and publish to external transport | — |
| BR-MMS-036 | Not define institutional mess policies such as rates, vacation periods, or employee appointment policy. It may only use explicitly provided values as inputs where the frozen problem statement states system behavior | Boundary and service | Consume effective-dated supplied policy inputs | — |
| BR-MMS-038 | Students, the Mess Caretaker, and the Mess Warden may view the weekly menu. Mess Admin menu access remains unresolved because the frozen PS contains conflicting statements | Registry and selector | Grant known menu readers and hold the disputed Admin grant | ISS-MMS-012 |
| BR-MMS-039 | Permit only the Mess Caretaker to add, delete, or modify weekly mess menu items | Service | Authorize Caretaker menu maintenance | — |
| BR-MMS-040 | Allow Students to view only actor-visible monthly mess bills and outstanding balances maintained within MMS | Selector and ledger | Expose only own published bills and actor-visible outstanding amounts | — |
| BR-MMS-041 | Restrict Student vacation food continuity responses to Yes or No | Domain and model | Accept only Yes or No | — |
| BR-MMS-042 | Allow a Student to view status and history only for the Student’s own submitted MMS requests | Selector | Filter request status and history to the Student owner | — |

### Use cases

| ID | What it requires | Layer | Planned enforcement | Notes |
| --- | --- | --- | --- | --- |
| MMS-UC-001 | Assign/Reassign MMS Operational Roles | Service | Assign operational duty | Mess Admin |
| MMS-UC-002 | Open Registration Window | Service | Open registration window | Mess Caretaker |
| MMS-UC-003 | Submit Registration Request | Service | Submit registration request | Student |
| MMS-UC-004 | Review Registration Request | Service | Decide registration request | Mess Caretaker |
| MMS-UC-005 | Submit Deregistration Request | Service | Submit deregistration request | Student |
| MMS-UC-006 | Review Deregistration Request | Service | Decide deregistration request and save effective date | Mess Caretaker |
| MMS-UC-007 | View Operational Student Requests for Oversight | Registry and selector | List operational requests for Warden oversight | Mess Warden |
| MMS-UC-008 | Publish or Update Weekly Menu | Service | Publish or update weekly menu | Mess Caretaker |
| MMS-UC-009 | View Weekly Menu | Registry and selector | Read weekly menu | Student / Mess Caretaker / Mess Warden. ISS-MMS-012 |
| MMS-UC-010 | Review, Finalize, and Publish Monthly Bills | Service | Review, finalize and publish monthly bill | Mess Caretaker |
| MMS-UC-011 | View Monthly Bills and Outstanding Balances | Selector | Read student's published bills and outstanding balance | Student |
| MMS-UC-012 | Submit Feedback | Service | Submit feedback | Student |
| MMS-UC-013 | View Feedback | Registry and selector | List feedback | Mess Caretaker / Mess Warden |
| MMS-UC-014 | Submit Rebate Request | Domain and service | Validate and submit rebate request | Student |
| MMS-UC-015 | Review Rebate Request | Service and ledger | Decide rebate and record approved dates | Mess Caretaker |
| MMS-UC-016 | Create Vacation Food Continuity Survey | Service | Create vacation survey and determine eligible recipients | Mess Caretaker |
| MMS-UC-017 | Respond to Vacation Food Continuity Survey | Domain and service | Record eligible student's Yes or No | Student |
| MMS-UC-018 | View Vacation Survey Response Summary | Selector | Show Caretaker's vacation survey summary | Mess Caretaker |
| MMS-UC-019 | Submit Special Food Request | Domain and service | Validate and submit special-food request | Student |
| MMS-UC-020 | Review Special Food Request | Service | Decide special-food request before decision cutoff | Mess Caretaker. ISS-MMS-013 |
| MMS-UC-021 | Update Special Food Fulfillment Status | Domain and service | Transition approved special food to Served or Cancelled | Mess Caretaker. ISS-MMS-014 and ISS-MMS-015 |
| MMS-UC-022 | Publish Announcement | Service | Publish and record announcement | Mess Caretaker / Mess Warden |
| MMS-UC-023 | View Announcement History | Selector | Read actor-visible announcement history | All MMS actors, subject to access rights |
| MMS-UC-024 | View and Search Supervisory Reports | Registry and selector | Search Warden supervisory reports | Mess Warden |
| MMS-UC-025 | Generate Operational Reports | Registry and selector | Generate Caretaker operational reports | Mess Caretaker |
| MMS-UC-026 | Track Submitted Request Status and History | Selector | Read student-owned status and history | Student |
| MMS-UC-027 | Activate Approved Deregistration | Scheduler and service | Apply approved next-day deregistration | N.A. — Event-triggered |
| MMS-UC-028 | Apply Default Vacation Response at Deadline | Scheduler and service | Default a missing vacation response to No | N.A. — Event-triggered |
| MMS-UC-029 | Default-Reject Undecided Special Food Request | Scheduler and service | Reject an overdue undecided special-food request | N.A. — Event-triggered. ISS-MMS-013 |
| MMS-UC-030 | Generate Monthly Mess Bills | Scheduler and service | Generate bills for a due calendar month | N.A. — Event-triggered |
| MMS-UC-031 | Send Vacation Survey Reminder | Scheduler and service | Emit a reminder for an open vacation survey | N.A. — Event-triggered. ISS-MMS-019 |

### Workflows

| ID | What it requires | Layer | Planned enforcement | Notes |
| --- | --- | --- | --- | --- |
| BW-MMS-01 | Registration — Approved | Workflow service | Open window, submit and approve | Basis workflow |
| BW-MMS-02 | Registration — Rejected | Workflow service | Open window, submit and reject | Basis workflow |
| CW-MMS-01 | Registration Request Lifecycle | Workflow service | Registration review with approval and rejection paths | Composite workflow |
| BW-MMS-03 | Deregistration — Approved | Workflow service | Submit deregistration, approve and apply next-day effect | Basis workflow |
| BW-MMS-04 | Deregistration — Rejected | Workflow service | Submit and reject deregistration | Basis workflow |
| CW-MMS-02 | Deregistration Request Lifecycle | Workflow service | Deregistration review with dated effect after approval | Composite workflow |
| BW-MMS-05 | Rebate — Approved as Submitted | Workflow service | Submit and approve rebate dates as requested | Basis workflow |
| BW-MMS-06 | Rebate — Dates Modified then Approved | Workflow service | Submit, apply permitted date modification, and approve rebate | Basis workflow |
| BW-MMS-07 | Rebate — Rejected | Workflow service | Submit and reject rebate | Basis workflow |
| CW-MMS-03 | Rebate Request Lifecycle | Workflow service | Rebate decisions including permitted date modification | Composite workflow |
| BW-MMS-08 | Vacation Survey — Yes Response | Workflow service | Create survey and record Yes | Basis workflow |
| BW-MMS-09 | Vacation Survey — No Response | Workflow service | Create survey and record a voluntary No | Basis workflow |
| BW-MMS-10 | Vacation Survey — Default No | Scheduler and workflow service | Create survey and default nonresponse to No | Basis workflow |
| CW-MMS-04 | Vacation Food Continuity Response Lifecycle | Workflow service | Vacation survey responses and deadline default | Composite workflow |
| BW-MMS-11 | Special Food — Rejected by Caretaker | Workflow service | Submit special food and reject manually | Basis workflow |
| BW-MMS-12 | Special Food — Default Rejected | Scheduler and workflow service | Submit special food and reject on timeout | Basis workflow |
| BW-MMS-13 | Special Food — Approved, Awaiting Fulfillment | Workflow service | Submit and approve special food pending fulfillment | Basis workflow |
| BW-MMS-14 | Special Food — Served | Workflow service | Approve special food and record Served | Basis workflow |
| BW-MMS-15 | Special Food — Cancelled | Workflow service | Approve special food and record Cancelled | Basis workflow |
| CW-MMS-05 | Special Food Request Lifecycle | Workflow service | Special-food review, timeout and fulfillment | Composite workflow |
| BW-MMS-16 | Monthly Billing — Generated to Published | Scheduler and workflow service | Generate, review, finalize and publish monthly bills | Basis workflow |

### Coherent functional requirements

| ID | What it requires | Layer | Planned enforcement | Notes |
| --- | --- | --- | --- | --- |
| CFR-MMS-001 | Module Scope and Policy Boundary | Boundary | MMS model, route and integration inventory | — |
| CFR-MMS-002 | Operational Role Assignment and Handoff | Service and model | Assign effective-dated operational duty with immediate handoff | — |
| CFR-MMS-003 | Mess Admin Operational Data Access Boundary | Registry and selector | Administrator operational-data boundary | — |
| CFR-MMS-004 | Mess Registration Request Lifecycle | Service | Registration window, submission and Caretaker decision | — |
| CFR-MMS-005 | Mess Deregistration Request Lifecycle | Service and scheduler | Deregistration submission, decision and next-day effect | — |
| CFR-MMS-006 | Warden Operational Request Oversight | Registry and selector | Read-only Warden oversight | — |
| CFR-MMS-007 | Student Request Tracking and Registration/Deregistration Notifications | Selector and service | Own history and registration notification events | — |
| CFR-MMS-008 | Weekly Menu Management and Access | Model and service | Weekly menu structure, visibility and publication | ISS-MMS-012 |
| CFR-MMS-009 | Monthly Billing Management and Student Billing Access | Service and ledger | Calendar-month charging, finalization and own published view | — |
| CFR-MMS-010 | Feedback Recording and Review | Service and selector | Student feedback capture and staff review | — |
| CFR-MMS-011 | Rebate Submission and Validation | Domain and model | Rebate submission, eligibility and overlap checks | — |
| CFR-MMS-012 | Rebate Decision, Status, Billing Effect and Notifications | Service and ledger | Rebate decision, approved dates, billing and notifications | — |
| CFR-MMS-013 | Vacation Food Continuity Survey Setup and Notifications | Service and scheduler | Create registered-student survey and dispatch due events | ISS-MMS-019 |
| CFR-MMS-014 | Vacation Survey Response, Default and Summary | Model and service | Yes/No response, deadline default and summary | — |
| CFR-MMS-015 | Special Food Request Submission | Domain and service | Special-food submission and lead time | — |
| CFR-MMS-016 | Special Food Decision and Default Rejection | Service and scheduler | Special-food manual decision or timeout | ISS-MMS-013 |
| CFR-MMS-017 | Special Food Status, Fulfillment and Billing Link | Domain and ledger | Special-food history, fulfillment, charge and event | ISS-MMS-015 and ISS-MMS-014 and ISS-MMS-015 |
| CFR-MMS-018 | Mess Announcements and History | Service and selector | Publish relevant announcements and retain scoped history | — |
| CFR-MMS-019 | Warden Supervisory Reporting | Registry and selector | Warden supervisory reports | — |
| CFR-MMS-020 | Caretaker Operational Reporting | Registry and selector | Caretaker operational reports | — |
| CFR-MMS-021 | MMS Report Scope Boundary | Boundary and selector | MMS-only report inventory | — |
| CFR-MMS-022 | Notification Governance and Email Boundary | Service and adapter | Emit named events into configured email transport | — |

### Atomic functional requirements

| ID | What it requires | Layer | Planned enforcement | Notes |
| --- | --- | --- | --- | --- |
| AFR-MMS-001 | Provide only the mess-management functionality explicitly defined in the frozen problem statement | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-002 | Allow the Mess Admin to assign the Mess Caretaker role to a specific institute employee | Service | assign operational duty | — |
| AFR-MMS-003 | Allow the Mess Admin to assign the Mess Warden role to a specific institute employee | Service | assign operational duty | — |
| AFR-MMS-004 | Allow the Mess Admin to reassign the active Mess Caretaker or Mess Warden when required, including during an active mess cycle | Service | assign operational duty | — |
| AFR-MMS-005 | Maintain exactly one active Mess Caretaker at a time | Model | non-overlapping duty intervals | — |
| AFR-MMS-006 | Maintain exactly one active Mess Warden at a time | Model | non-overlapping duty intervals | — |
| AFR-MMS-007 | Prevent the Mess Admin from accessing operational mess data, including student requests, billing details, rebate details, special-food requests, vacation responses, and feedback entries | Registry and selector | administrator data boundary | — |
| AFR-MMS-008 | Allow a Student to view the weekly mess menu | Selector | weekly menu visibility | — |
| AFR-MMS-009 | Allow a Student to view the Student’s monthly mess bills | Selector | own published billing view | — |
| AFR-MMS-010 | Allow a Student to view mess-service announcements relevant to the Student | Selector | scoped announcement history | — |
| AFR-MMS-011 | Allow a Student to track the status and history of the Student’s submitted MMS requests | Selector | own request and history | — |
| AFR-MMS-012 | Allow the Mess Caretaker to open a registration window for a mess cycle or other designated period | Service | open a registration window | — |
| AFR-MMS-013 | Accept a Student registration request only while the registration window is open | Service | submit a registration request | — |
| AFR-MMS-014 | Allow a Student to submit a deregistration request at any time while registered for mess service | Service | submit a deregistration request | — |
| AFR-MMS-015 | Allow the Mess Caretaker to approve or reject each submitted registration request | Service | decide a pending registration or deregistration request | — |
| AFR-MMS-016 | Allow the Mess Caretaker to approve or reject each submitted deregistration request | Service | decide a pending registration or deregistration request | — |
| AFR-MMS-017 | Record the Caretaker’s decision on a deregistration request when the decision is made | Service | decide a pending registration or deregistration request | — |
| AFR-MMS-018 | For an approved deregistration request, MMS shall make the mess-service effect start from the next calendar day | Service and scheduler | apply dated deregistration | — |
| AFR-MMS-019 | Allow the Mess Warden to view operational student requests for supervisory oversight, including registration and deregistration requests | Registry and selector | supervisory request access | — |
| AFR-MMS-020 | Prevent the Mess Warden from approving, rejecting, registering, deregistering, or otherwise deciding operational student requests | Registry and selector | supervisory request access | — |
| AFR-MMS-021 | Maintain request status and request history for registration and deregistration requests | Model and service | append request history | — |
| AFR-MMS-022 | Trigger a system-generated email notification to the Student when a registration or deregistration request is submitted | Service | emit permitted notification event on commit | — |
| AFR-MMS-023 | Trigger a system-generated email notification to the Student when a registration or deregistration request is approved or rejected | Service | emit permitted notification event on commit | — |
| AFR-MMS-024 | Store the weekly mess menu in a day-wise and meal-wise structure covering breakfast, lunch, and dinner | Model | day and meal menu item | — |
| AFR-MMS-025 | Allow Students to view the weekly mess menu according to their access rights | Selector | weekly menu visibility | — |
| AFR-MMS-026 | Allow the Mess Caretaker to view the weekly mess menu | Selector | weekly menu visibility | — |
| AFR-MMS-027 | Allow the Mess Warden to view the weekly mess menu | Selector | weekly menu visibility | — |
| AFR-MMS-028 | Represent the Mess Admin weekly-menu visibility consistently with the frozen PS. The PS simultaneously states that Mess Admin may view the menu according to access rights and that Mess Admin has no operational-data access | Selector | weekly menu visibility | ISS-MMS-012 |
| AFR-MMS-029 | Allow the Mess Caretaker to add weekly mess menu items | Service | maintain and publish menu items | — |
| AFR-MMS-030 | Allow the Mess Caretaker to delete weekly mess menu items | Service | maintain and publish menu items | — |
| AFR-MMS-031 | Allow the Mess Caretaker to modify weekly mess menu items | Service | maintain and publish menu items | — |
| AFR-MMS-032 | Trigger system-generated email notifications to Students when the weekly menu is updated | Service | emit permitted notification event on commit | — |
| AFR-MMS-033 | Generate mess bills using a calendar-month billing cycle | Service and scheduler | generate a calendar-month bill | — |
| AFR-MMS-034 | Include daily-rate charges for served days in monthly bill computation | Domain and ledger | calculate charge and deduction lines | — |
| AFR-MMS-035 | Include charges for approved special meals or add-ons in monthly bill computation | Domain and ledger | calculate charge and deduction lines | — |
| AFR-MMS-036 | Deduct approved rebates in monthly bill computation | Domain and ledger | calculate charge and deduction lines | — |
| AFR-MMS-037 | Allow the Mess Caretaker to review system-generated monthly mess bills before publication | Selector | Caretaker bill review | — |
| AFR-MMS-038 | Require the Mess Caretaker to finalize monthly mess bills before publication | Service | finalize and publish a bill | — |
| AFR-MMS-039 | Allow the Mess Caretaker to publish finalized monthly mess bills | Service | finalize and publish a bill | — |
| AFR-MMS-040 | Allow a Student to view the Student’s published monthly mess bill | Selector | own published billing view | — |
| AFR-MMS-041 | Allow a Student to view the Student’s outstanding mess balance maintained within MMS | Selector | own published billing view | — |
| AFR-MMS-042 | Not perform payment collection, accounting settlement, or payroll/account integration as part of billing management | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-043 | Trigger a system-generated email notification to Students when monthly bills are published | Service | emit permitted notification event on commit | — |
| AFR-MMS-044 | Allow a Student to submit text feedback related to mess services | Service and model | record student feedback | — |
| AFR-MMS-045 | Allow the Mess Caretaker to view Student feedback entries for operational review, record keeping, and analysis | Registry and selector | read feedback | — |
| AFR-MMS-046 | Allow the Mess Warden to view Student feedback entries for supervisory oversight, record keeping, and analysis | Registry and selector | read feedback | — |
| AFR-MMS-047 | Store Student feedback entries with relevant record information | Service and model | record student feedback | — |
| AFR-MMS-048 | Not assume a formal feedback-resolution workflow because none is defined in the frozen problem statement | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-049 | Allow a Student to submit a mess rebate request | Service | submit a rebate request | — |
| AFR-MMS-050 | A rebate request shall capture a reason, start date, and end date | Service | submit a rebate request | — |
| AFR-MMS-051 | Restrict rebate reasons to medical, institute leave, family function, and other, and shall require an explanation when other is selected | Domain | validate rebate reason, duration and lead time | — |
| AFR-MMS-052 | Accept a rebate request only when the requested rebate duration is at least 3 days | Domain | validate rebate reason, duration and lead time | — |
| AFR-MMS-053 | Accept a rebate request only when it is submitted at least 1 calendar day before the requested rebate start date | Domain | validate rebate reason, duration and lead time | — |
| AFR-MMS-054 | Prevent overlapping rebate requests for the same Student | Model and service | reject overlapping rebate intervals | — |
| AFR-MMS-055 | Allow the Mess Caretaker to approve or reject a rebate request | Service | decide a rebate with external policy | — |
| AFR-MMS-056 | Allow the Mess Caretaker to modify rebate dates before approval where permitted by the stated external mess policy | Service | decide a rebate with external policy | — |
| AFR-MMS-057 | When rebate dates are modified before approval, MMS shall use the approved dates as the rebate dates for billing adjustment | Domain and ledger | calculate charge and deduction lines | — |
| AFR-MMS-058 | Allow Students to track rebate request status as Pending, Approved, or Rejected | Model and service | append request history | — |
| AFR-MMS-059 | Automatically apply approved rebate adjustments to the corresponding monthly mess bill | Domain and ledger | calculate charge and deduction lines | — |
| AFR-MMS-060 | Trigger a system-generated email notification to the Student when a rebate request is submitted | Service | emit permitted notification event on commit | — |
| AFR-MMS-061 | Trigger a system-generated email notification to the Student when a rebate request is approved or rejected | Service | emit permitted notification event on commit | — |
| AFR-MMS-062 | Allow the Mess Caretaker to create a vacation food continuity survey for an upcoming institute vacation | Service | configure and open a vacation survey | — |
| AFR-MMS-063 | Make a vacation food continuity survey available only to currently registered Students | Selector and service | restrict survey eligibility | — |
| AFR-MMS-064 | Restrict a Student’s vacation food continuity response to Yes or No | Domain and model | record Yes or No once | — |
| AFR-MMS-065 | Allow the Mess Caretaker to set a response deadline for each vacation food continuity survey | Service | configure and open a vacation survey | — |
| AFR-MMS-066 | For each currently registered Student who has not responded by the survey deadline, MMS shall record the response as No | Scheduler and service | record default No | — |
| AFR-MMS-067 | Allow the Mess Caretaker to view the vacation survey response summary for operational planning | Selector | operational vacation survey summary | — |
| AFR-MMS-068 | Trigger system-generated email notification when a vacation food continuity survey is created | Service | emit permitted notification event on commit | — |
| AFR-MMS-069 | Trigger system-generated email reminders for vacation food continuity surveys. Reminder timing is not specified by the frozen PS | Scheduler and service | emit due survey reminders | ISS-MMS-019 |
| AFR-MMS-070 | Allow a Student to submit a special food request due to illness or a personal event | Service | submit a special-food request | — |
| AFR-MMS-071 | Accept a special food request only when submitted at least 1 calendar day before the requested date | Domain | validate special-food lead time | — |
| AFR-MMS-072 | Allow the Mess Caretaker to approve or reject a special food request within the institution-defined stipulated decision period | Service | decide special food before cutoff | ISS-MMS-013 |
| AFR-MMS-073 | If a special food request is not decided within the institution-defined stipulated decision period, MMS shall mark the request Rejected by default | Scheduler and service | expire an undecided special-food request | ISS-MMS-013 |
| AFR-MMS-074 | Maintain special food request history and status so the Student can track the request | Model and service | append request history | — |
| AFR-MMS-075 | Trigger a system-generated email notification to the Student when a special food request is submitted | Service | emit permitted notification event on commit | — |
| AFR-MMS-076 | Trigger a system-generated email notification to the Student when a special food request is approved or rejected | Service | emit permitted notification event on commit | — |
| AFR-MMS-077 | Add charges for approved special food requests to the Student’s monthly mess bill | Domain and ledger | calculate charge and deduction lines | ISS-MMS-015 |
| AFR-MMS-078 | Track special food requests using the states Requested, Approved, Rejected, Served, and Cancelled | Model and service | append request history | — |
| AFR-MMS-079 | Permit Served and Cancelled statuses only after a special food request has reached Approved status | Domain and service | fulfill approved special-food request | ISS-MMS-014 and ISS-MMS-015 |
| AFR-MMS-080 | Trigger system-generated email notifications for special-food fulfillment-related updates where applicable | Service | emit permitted notification event on commit | — |
| AFR-MMS-081 | Allow the Mess Caretaker to publish mess-related announcements | Service | publish a relevant announcement | — |
| AFR-MMS-082 | Allow the Mess Warden to publish mess-related announcements | Service | publish a relevant announcement | — |
| AFR-MMS-083 | Trigger a system-generated email notification to Students when a new announcement is published | Service | emit permitted notification event on commit | — |
| AFR-MMS-084 | Maintain announcement history relevant to mess services | Selector | scoped announcement history | — |
| AFR-MMS-085 | Allow MMS actors to view announcement history according to their access rights | Selector | scoped announcement history | — |
| AFR-MMS-086 | Allow the Mess Warden to view and search registered Student lists | Registry and selector | Warden supervisory reports | — |
| AFR-MMS-087 | Allow the Mess Warden to view and search rebate summaries | Registry and selector | Warden supervisory reports | — |
| AFR-MMS-088 | Allow the Mess Warden to view and search vacation survey response summaries | Registry and selector | Warden supervisory reports | — |
| AFR-MMS-089 | Allow the Mess Caretaker to generate registration trend reports | Registry and selector | Caretaker operational reports | — |
| AFR-MMS-090 | Allow the Mess Caretaker to generate special meal logs | Registry and selector | Caretaker operational reports | — |
| AFR-MMS-091 | Allow the Mess Caretaker to generate billing summary reports | Registry and selector | Caretaker operational reports | — |
| AFR-MMS-092 | MMS reports shall be limited to MMS operational and supervisory information | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-093 | Not provide external financial, payroll, procurement, or inventory reports | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-094 | Trigger system-generated email notifications only for MMS events explicitly identified in the frozen problem statement | Service | emit permitted notification event on commit | — |
| AFR-MMS-095 | Not own the external email delivery infrastructure used to deliver system-generated email notifications | Service | emit permitted notification event on commit | — |
| AFR-MMS-096 | MMS Caretaker and Warden role assignments shall be time-bound for specified durations | Service | assign operational duty | — |
| AFR-MMS-097 | A mid-cycle Caretaker or Warden reassignment shall take effect immediately in MMS from the recorded reassignment time | Service | assign operational duty | — |
| AFR-MMS-098 | From the effective time of a Caretaker reassignment, pending operational requests shall become visible to and actionable by the newly assigned active Mess Caretaker | Selector and service | current duty holder and pending queue | — |
| AFR-MMS-099 | Consume institute employee identities needed for Mess Admin, Caretaker, and Warden role assignment without owning employee master-data management | Service | assign operational duty | — |
| AFR-MMS-100 | Not perform payment collection, accounting settlement, payroll processing, procurement, stock management, or inventory management | Boundary | MMS model, route and integration inventory | — |
| AFR-MMS-101 | Not define institutional mess policies such as rates, vacation periods, eligibility policy, or approval authority beyond behavior explicitly stated in the frozen problem statement | Boundary | MMS model, route and integration inventory | — |

## B. Domain model

MMS is one bounded context for student mess services. It owns its operational records in Fusion-Integrated. IAM owns identities, designations and permissions. MMS stores identity references as scalar ERP user IDs. Dependency candidates remain the upstream access-control framework and the directory's public contract. Financial data and rates are external policy inputs. The shared directory contract provides display data and verifies employee identities for assignments. Each mutation derives its acting user and active role from the authenticated principal.

| Proposed record | Principal fields | Database guarantees |
| --- | --- | --- |
| OperationalDutySlot and OperationalAssignment | Slot kind, employee ID, effective interval, actor ID and assignment time | Unique slot per duty kind. Positive effective interval. A PostgreSQL exclusion constraint prevents overlapping intervals for a duty kind. A transaction locks the slot, ends the prior interval and creates the successor at the same instant. Bootstrap and gaps at expiry are addressed in Section H. |
| RegistrationWindow | Cycle reference, opening and closing instants, creator ID | Closing instant strictly after opening instant. The service validates which window applies to the request. |
| Membership and MembershipRequest | Student ID, membership dates, submission kind, cycle, current request state, decision and effective date | Valid membership date ranges and no overlapping active service intervals for one student. The decision, membership update or dated transition, and history write are atomic. |
| MenuItem | Week start, day, meal category, display order, details and publishing actor | Day and category constrained to valid values. A successful publish or update records the notification intent in the same transaction. |
| FeedbackEntry | Authenticated student ID, text and submitted time | Required nonempty text and immutable submission time. |
| RebateRequest | Student ID, requested and approved date ranges, reason, conditional explanation, decision metadata and state | Ordered date ranges, valid reason and required explanation for Other. The concurrency-safe overlap check uses a database range exclusion for the set of requests covered by the policy. Section H records the unresolved state scope. |
| VacationSurvey, SurveyRecipient and SurveyResponse | Vacation range, response deadline, caretaker identity, recipient ID, answer source and timestamp | One recipient and one response per survey and student. A supplied answer is Yes or No. Deadline processing uses a conditional insert, preserving any recorded response. |
| SpecialFoodRequest | Student ID, requested service date, reason, decision cutoff and the policy revision used, decision and fulfillment metadata | Known states and valid dates. Atomic updates prevent a timeout and Caretaker decision from both winning. A request references its captured cutoff so a later policy edit cannot change its decision period. |
| Announcement | Publication time, author and acting role, content and allowed audience | Published record and its audience are kept for history. Selectors apply the approved visibility rules. |
| BillingPolicyVersion, Bill and BillLedgerEntry | Effective range, source and monetary policy inputs, student, month, status, component, decimal amount and source reference | One bill per student and month. A stable entry key prevents duplicate charge or deduction for the same source and service period. Finalization locks the bill. If corrections are authorized, ledger entries use explicit reversals. |
| RequestEvent and NotificationIntent | Request type and record reference, previous and new state, timestamp and acting identity or service, event kind and recipient | History is appended in the same transaction as the state change. A unique event and recipient key prevents duplicate intents. The module records dispatch attempts and reuses the platform transport. |

Time intervals use half-open bounds for effective instants. Local service dates, lead times and billing months use the platform's Asia/Kolkata timezone. Rebate date ranges are inclusive to the student. Database ranges normalize those dates to an exclusive end for overlap checks.

The proposed range constraints use PostgreSQL GiST with btree_gist for scalar equality. Confirm the extension can be provisioned before writing those migrations. Services enforce actor, eligibility and time-dependent rules while holding the relevant slot or record lock. API serializers validate request shape and delegate business transitions to services.

Each policy revision is effective-dated and tied to its supplied institutional source. A missing required input produces an actionable business refusal or a pending scheduled obligation visible to operators. Generated bill totals use decimal arithmetic. MMS shows its own published ledger amounts. Payment collection and settlement stay with the institutional systems that own them.

## C. State transitions

The domain layer declares permitted combinations of current state, event and acting authority. A service locks the relevant record or uses a guarded update, commits the state and history together, and emits a notification intent only where the specification requires one.

| Lifecycle | From | Event and authority | To and effect |
| --- | --- | --- | --- |
| Registration window | Configured | Opening instant reached, by clock | Open |
| Registration window | Open | Closing instant reached, by clock | Closed. Student submission checks the stored clock boundaries directly. |
| Registration request | New | Submit, Student in open window | Pending |
| Registration request | Pending | Approve, active Caretaker | Approved and membership is recorded |
| Registration request | Pending | Reject, active Caretaker | Rejected |
| Deregistration request | New | Submit, Student with valid membership | Pending, independent of registration window |
| Deregistration request | Pending | Approve, active Caretaker | Approved, with next local calendar day stored as the effective date |
| Deregistration request | Pending | Reject, active Caretaker | Rejected |
| Membership | Active | Apply due approved deregistration, system | Ended with the recorded effective date. The request retains its Approved decision. |
| Rebate request | New | Submit valid dates and reason, Student | Pending |
| Rebate request | Pending | Approve original or policy-permitted revised dates, active Caretaker | Approved, with the approved dates recorded for billing |
| Rebate request | Pending | Reject, active Caretaker | Rejected |
| Survey response | No response | Respond Yes or No before cutoff, eligible Student | Yes or No with Student response source |
| Survey response | No response | Apply deadline, system | No with deadline-default source |
| Special-food request | New | Submit with valid lead time, Student | Requested |
| Special-food request | Requested | Approve or reject within configured cutoff, active Caretaker | Approved or Rejected |
| Special-food request | Requested | Decision cutoff reached, system | Rejected with timeout reason |
| Special-food request | Approved | Record fulfillment, proposed active Caretaker | Served or Cancelled. See ISS-MMS-014 and ISS-MMS-015. |
| Monthly bill | Absent | Generate after the calendar month closes, system | Generated |
| Monthly bill | Generated | Finalize, active Caretaker | Finalized with locked bill components |
| Monthly bill | Finalized | Publish, active Caretaker | Published and visible to its Student |

Repeat delivery of a system event is a no-op once its transition has happened. A scheduling delay never makes a closed registration window or an expired decision window accept an action. Reports, menus, announcements and feedback use explicit permissions and selectors. They do not gain extra workflow states.

## D. Permissions and row scope

The synthetic fixture contains the exact designation codes mess_manager for Mess Caretaker and mess_warden for Mess Warden. Student uses the platform's student basic role. The Mess Admin designation remains open. The proposed Admin permissions are listed below, pending the exact ERP designation. The final registry can be validated and seeded only after that mapping is known.

An endpoint requires both the MMS module grant and its action permission. A current operational assignment is an additional business check for Caretaker and Warden actions. It does not create or replace an IAM designation. Student reads are scoped to the authenticated identity and to actor-visible menu, survey or announcement data. Admin sees assignments, the employee lookup used for assignment, and announcement history within its approved audience. Warden has read-only operational oversight and can publish relevant announcements. The Warden's report views and the Caretaker's operational report views use separate resource permissions.

Proposed registry declarations for module and permission inventory:

~~~python
MODULE = {
    "code": "mms",
    "label": "Mess Management System",
    "icon": "FaClipboardList",
    "base_path": "/mess",
    "nav_section": "Mess",
    "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("mms.assignment.view", "View mess duty assignments and eligible employees"),
    ("mms.assignment.assign", "Assign or replace a mess duty holder"),
    ("mms.registration_window.view", "View applicable registration windows"),
    ("mms.registration_window.create", "Open a registration window"),
    ("mms.request.view", "View scoped registration requests and own request history"),
    ("mms.request.create", "Submit a registration or deregistration request"),
    ("mms.request.approve", "Decide a registration or deregistration request"),
    ("mms.menu.view", "View the weekly menu"),
    ("mms.menu.create", "Add a weekly menu item"),
    ("mms.menu.update", "Update a weekly menu item"),
    ("mms.menu.delete", "Remove a weekly menu item"),
    ("mms.menu.publish", "Publish a weekly menu update"),
    ("mms.bill.view", "View scoped bills and outstanding amounts"),
    ("mms.bill.approve", "Finalize a generated bill"),
    ("mms.bill.publish", "Publish a finalized bill"),
    ("mms.feedback.view", "View feedback for oversight or operational review"),
    ("mms.feedback.create", "Submit text feedback"),
    ("mms.rebate.view", "View scoped rebate requests"),
    ("mms.rebate.create", "Submit a rebate request"),
    ("mms.rebate.approve", "Decide a rebate request"),
    ("mms.survey.view", "View scoped vacation surveys and response summaries"),
    ("mms.survey.create", "Open a vacation survey"),
    ("mms.survey_response.create", "Answer an eligible vacation survey"),
    ("mms.special_food.view", "View scoped special-food requests"),
    ("mms.special_food.create", "Submit a special-food request"),
    ("mms.special_food.approve", "Decide a special-food request"),
    ("mms.special_food.update", "Record approved special-food fulfillment"),
    ("mms.announcement.view", "View actor-visible mess announcement history"),
    ("mms.announcement.publish", "Publish a mess announcement"),
    ("mms.operational_report.view", "View Caretaker operational reports"),
    ("mms.supervisory_report.view", "View Warden supervisory reports"),
    ("mms.membership.update", "Apply due deregistration"),
    ("mms.survey_response.update", "Apply the deadline default"),
    ("mms.special_food_expiry.update", "Reject an overdue special-food request"),
    ("mms.bill.create", "Generate a monthly bill"),
    ("mms.survey_reminder.create", "Queue a due vacation survey reminder"),
    ("mms.notification.publish", "Dispatch a named MMS notification event"),
]

SYSTEM_PERMISSIONS = [
    "mms.membership.update",
    "mms.survey_response.update",
    "mms.special_food_expiry.update",
    "mms.bill.create",
    "mms.survey_reminder.create",
    "mms.notification.publish",
]

SCOPE_PERMISSIONS = []

ROLE_GRANTS = {
    "student": [
        "mms.registration_window.view", "mms.request.view", "mms.request.create",
        "mms.menu.view", "mms.bill.view", "mms.feedback.create",
        "mms.rebate.view", "mms.rebate.create", "mms.survey.view",
        "mms.survey_response.create", "mms.special_food.view",
        "mms.special_food.create", "mms.announcement.view",
    ],
    "mess_manager": [
        "mms.registration_window.view", "mms.registration_window.create",
        "mms.request.view", "mms.request.approve", "mms.menu.view", "mms.menu.create",
        "mms.menu.update", "mms.menu.delete", "mms.menu.publish", "mms.bill.view",
        "mms.bill.approve", "mms.bill.publish", "mms.feedback.view", "mms.rebate.view",
        "mms.rebate.approve", "mms.survey.view", "mms.survey.create",
        "mms.special_food.view", "mms.special_food.approve", "mms.special_food.update",
        "mms.announcement.view", "mms.announcement.publish",
        "mms.operational_report.view",
    ],
    "mess_warden": [
        "mms.request.view", "mms.menu.view", "mms.feedback.view",
        "mms.announcement.view", "mms.announcement.publish",
        "mms.supervisory_report.view",
    ],
}
~~~

Confirmed Admin designation to receive: mms.assignment.view, mms.assignment.assign, and mms.announcement.view subject to announcement visibility. Assignment and bill publication are sensitive operations and need audit coverage. Selectors scope rows by principal identity and current operational duty.

## E. API and frontend entry points

Paths are relative to /api/v1/mms/. Every row includes the common MMS module grant plus the operation permission listed. Action services also check ownership, current duty or cohort eligibility. List responses use cursor pagination. Creates return the resource with a Location header. Detail and history lookups use scoped selectors. A record outside the caller's visibility returns 404. A missing action permission returns 403. Semantic validation returns 422. A conflicting transition returns 409.

| Method and resource | Operation permission | Response and visibility | Main rules |
| --- | --- | --- | --- |
| GET employees/ and assignments/ | mms.assignment.view | Eligible directory candidates or current and historical duty assignments | BR-MMS-002–007 |
| POST assignments/ | mms.assignment.assign | New assignment and effective interval | BR-MMS-002–007 |
| GET registration-windows/ | mms.registration_window.view | Applicable cycle windows | BR-MMS-008–009 |
| POST registration-windows/ | mms.registration_window.create | New cycle registration window | BR-MMS-008 |
| GET requests/ and requests/{id}/ | mms.request.view | Student's own request history, Caretaker queue, or Warden's oversight rows | BR-MMS-005, BR-MMS-007, BR-MMS-011, BR-MMS-042 |
| POST requests/ | mms.request.create | Pending registration or deregistration request | BR-MMS-009, BR-MMS-012, BR-MMS-035 |
| POST requests/{id}/decision/ | mms.request.approve | Decision, history and any effective date | BR-MMS-010, BR-MMS-013, BR-MMS-035 |
| GET menus/ | mms.menu.view | Visible week, day and meal groups | BR-MMS-014, BR-MMS-038 |
| POST menu-items/ | mms.menu.create | Added weekly menu item | BR-MMS-014, BR-MMS-015, BR-MMS-039 |
| PATCH or DELETE menu-items/{id}/ | mms.menu.update or mms.menu.delete | Updated item or empty deletion response | BR-MMS-014, BR-MMS-015, BR-MMS-039 |
| POST menus/{week}/publication/ | mms.menu.publish | Published weekly menu | BR-MMS-014, BR-MMS-015, BR-MMS-039 |
| GET bills/, bills/{id}/ and balances/ | mms.bill.view | Own published bills and own balance for Students, or bill review rows for the Caretaker | BR-MMS-016–019, BR-MMS-040 |
| POST bills/{id}/finalization/ | mms.bill.approve | Finalized bill | BR-MMS-018 |
| POST bills/{id}/publication/ | mms.bill.publish | Published bill | BR-MMS-018, BR-MMS-035 |
| GET feedback/ | mms.feedback.view | Authorized staff feedback list | BR-MMS-020 |
| POST feedback/ | mms.feedback.create | Stored text feedback | BR-MMS-020 |
| GET rebates/ and rebates/{id}/ | mms.rebate.view | Own rebate or Caretaker review detail | BR-MMS-019, BR-MMS-042 |
| POST rebates/ | mms.rebate.create | Pending rebate | BR-MMS-021–024, BR-MMS-035 |
| POST rebates/{id}/decision/ | mms.rebate.approve | Decision and any policy-permitted approved dates | BR-MMS-019, BR-MMS-025, BR-MMS-035 |
| GET surveys/ and surveys/{id}/ | mms.survey.view | Eligible student's survey or Caretaker response summary | BR-MMS-026–027, BR-MMS-041 |
| POST surveys/ | mms.survey.create | Survey with deadline and eligible recipient set | BR-MMS-026, BR-MMS-035 |
| POST surveys/{id}/responses/ | mms.survey_response.create | Accepted Yes or No response | BR-MMS-026–027, BR-MMS-041 |
| GET special-food-requests/ and special-food-requests/{id}/ | mms.special_food.view | Own requests or Caretaker queue and history | BR-MMS-031, BR-MMS-042 |
| POST special-food-requests/ | mms.special_food.create | Requested special food with its configured cutoff | BR-MMS-028, BR-MMS-035 |
| POST special-food-requests/{id}/decision/ | mms.special_food.approve | Approved or Rejected request | BR-MMS-029–031, BR-MMS-035 |
| POST special-food-requests/{id}/fulfillment/ | mms.special_food.update | Served or Cancelled request | BR-MMS-030–031, BR-MMS-035 |
| GET announcements/ | mms.announcement.view | Actor-visible news and history | BR-MMS-032–033 |
| POST announcements/ | mms.announcement.publish | Published mess announcement | BR-MMS-032, BR-MMS-035 |
| GET operational-reports/{kind}/ | mms.operational_report.view | Registration trends, special meal logs, or billing summaries | BR-MMS-034 |
| GET supervisory-reports/{kind}/ | mms.supervisory_report.view | Searchable student lists, rebate summaries, or vacation survey summaries | BR-MMS-011, BR-MMS-034 |

The Caretaker owns the separate pending rebate and special-food queues. The Warden's supervisory reports carry only the information specified for each report. Students can find their own rebate and special-food status through the student history selector. Time-driven actions use their reserved system permissions in the scheduled services.

The module-only handoff for the external Fusion client is id mms, label Mess Management System, icon FaClipboardList, to /mess, section Mess. The local shell registers the same base path. Each child route receives a nav item with the same permission. Use drawers or dialogs for detail pages.

| Route | Navigation label | Guard |
| --- | --- | --- |
| /mess | Mess Management System | MMS module grant. The index lists only permitted child links, using the module header as its entry. |
| /mess/assignments | Duty Assignments | mms.assignment.view |
| /mess/requests | Requests | mms.request.view |
| /mess/menu | Weekly Menu | mms.menu.view |
| /mess/bills | Bills and Balances | mms.bill.view |
| /mess/feedback | Feedback Review | mms.feedback.view |
| /mess/submit-feedback | Submit Feedback | mms.feedback.create |
| /mess/rebates | Rebates | mms.rebate.view |
| /mess/surveys | Vacation Surveys | mms.survey.view |
| /mess/special-food | Special Food | mms.special_food.view |
| /mess/announcements | Announcements | mms.announcement.view |
| /mess/operational-reports | Operational Reports | mms.operational_report.view |
| /mess/supervisory-reports | Supervisory Reports | mms.supervisory_report.view |

Show write actions only when the matching permission and the row's current state allow them. Registration-window management fits into the Requests page for the Caretaker.

## F. Integration contracts

- Identity and employee selection use IAM's authenticated principal and the existing batched directory contracts. Resolve the authenticated student server-side. Use the employee directory for assignment eligibility and request display labels in batches. A directory miss must refuse a new assignment without saving a partial record.
- Operational assignment is an MMS duty record. Fusion IAM remains responsible for designation membership and grants. Confirm how the institution aligns eligible duty holders with their IAM roles before granting live access.
- External email transport receives an allowlisted MMS event, stable deduplication key, appropriate template data and recipient reference. The outbox records the MMS trigger. Email delivery infrastructure remains owned by the platform through the configured adapter.
- The source for served days, rates, approved supplemental charges and other institutional policy needs an approved input contract. The module operates on supplied billing inputs. IAM owns access to the ERP identity data. The supplied spec calls for internal MMS services. Any future public getter uses the repository's plural, typed contract convention.

## G. Scheduled work

The processing cadences below are technical proposals. Business effectiveness is derived from the stored date or timestamp even when a worker runs late. Tasks are repeatable, work from indexed due-state queries and record each applied transition once.

| Task | Proposed cadence | Consequence if unavailable |
| --- | --- | --- |
| Apply due deregistrations | Every minute, using the next local calendar date | Pending service effects need catch-up. Access checks use the effective date rather than waiting for the worker. |
| Apply vacation deadline defaults | Every minute, filtered by due surveys | Response summaries may lack default No entries until the queue catches up. Deadline restrictions on Student submissions still apply. |
| Reject undecided special food | Every minute, filtered by the captured deadline | Requested rows may show a delayed timeout transition. A manual decision after the cutoff remains disallowed. |
| Generate due calendar-month bills | Daily after local midnight, catch up missed months with configured inputs | Generated bills are delayed until the worker resumes and the inputs are available. |
| Discover due vacation reminders | Every minute once approved offsets or events are configured | Open surveys may miss a reminder. The task rechecks that the survey is open before recording any event. |
| Dispatch notification intents | Every minute on the platform notification queue, subject to bounded batches and retry | Issued notifications are delayed. Previously dispatched events retain their deduplication keys. |

## H. Open decisions and verification

| Decision | Evidence and proposed treatment |
| --- | --- |
| Mess Admin IAM designation and power to assign existing employees | Confirm the exact ERP designation. The fixture verifies mess_manager and mess_warden, but no Mess Admin designation was identified. Confirm whether a nominated employee already holds the relevant IAM designation and what Admin may do when an assignment expires without a successor. |
| ISS-MMS-012 — Mess Admin weekly-menu access | Problem Statement §3.3.2 mentions Admin menu viewing. §3.2.1 and §3.3.11 restrict Admin operational access. The draft grants menu access only to Student, Caretaker and Warden, pending a ruling. |
| ISS-MMS-013 — Special-food decision period | Use a supplied, effective-dated period. The problem statement gives 12 hours as intended and treats the exact policy as institution-defined. |
| ISS-MMS-014 — Special-food fulfillment authority | UC-021 names Caretaker. Confirm that the active Caretaker is the authorized actor for Served and Cancelled before granting the update capability. |
| ISS-MMS-015 — Charge after cancellation | Confirm whether a Cancelled request keeps, removes or reverses the approved add-on charge and how already-published bills are handled. |
| ISS-MMS-019 — Vacation reminder cadence | Obtain the allowed reminder times and recipient policy. A polling interval does not establish a reminder schedule. |
| Billing inputs and opening balance | Confirm the authoritative served-day source, daily and special-food rates, how an approved rebate is valued, rounding, and how any balance adjustments are supplied without adding payment collection to MMS. |
| Rebate overlap and date revision | Confirm whether a rejected request's interval blocks a new request and supply the external date modification policy. Approved revisions are checked for consistency and retained as the billing source. |
| Survey cohort changes and announcement audience | Confirm whether students who become registered after a survey opens join that survey. Confirm the default and role-specific visibility settings for announcement history and the recipient source for menu notices. |
| Database extension and integration changes | Confirm the availability and deploy ownership of btree_gist. Module registration, Celery schedule, OpenAPI and permission manifest changes will be reviewed as explicit shared-file edits. |

During implementation, add source-linked domain, API and workflow tests. Check that closed windows, unauthorized decisions, cross-student reads and out-of-order transitions leave no unauthorized state changes. Exercise concurrent assignment, rebate overlap, survey default and response, special-food timeout and decision, and bill generation. Run the backend and client gates and exercise each role and access boundary in Chromium with synthetic identities. The spec-only Assignment 9 test design remains a separate stage after the builder review.
