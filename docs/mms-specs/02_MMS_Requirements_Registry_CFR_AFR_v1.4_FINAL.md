# 02 MMS Requirements Registry CFR AFR v1.4 FINAL(1)

MMS Two-Level Requirement Registry

CFR + AFR — v1.4 FINAL | historical MMS-FR continuity preserved

| Governing rule | DIRECT_FINAL_v2 |
| --- | --- |
| CFR count | 22 |
| AFR count | 101 |
| Historical continuity | AFR-MMS-001..101 preserve the exact v1.3 atomic requirement statements and map one-to-one to MMS-FR-001..101. MMS-FR-102 remains retired as a modeling convention. |
| Semantic profile | I = interaction/service; C = constraint/rule; B = business-state progression/behavior. Profiles describe dominant semantics, not artifact types. |
| Traceability | AFR-level mappings are authoritative; CFR mappings roll up from constituent AFRs. |

# CFR-MMS-001 — Module Scope and Policy Boundary

| CFR Statement | MMS shall provide only the mess-management capabilities and explicit integration/notification responsibilities defined by the frozen Problem Statement, while excluding payment/accounting/payroll/procurement/inventory functions and institutional policy definition beyond explicitly stated behavior. |
| --- | --- |
| Semantic Profile | C |
| Constituent AFRs | AFR-MMS-001, AFR-MMS-100, AFR-MMS-101 |
| Rolled-up UC(s) | N/A |
| Rolled-up BR(s) | BR-MMS-001, BR-MMS-036 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-001 | MMS shall provide only the mess-management functionality explicitly defined in the frozen problem statement. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.1, §3.4 |
| AFR-MMS-100 | MMS shall not perform payment collection, accounting settlement, payroll processing, procurement, stock management, or inventory management. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.4 |
| AFR-MMS-101 | MMS shall not define institutional mess policies such as rates, vacation periods, eligibility policy, or approval authority beyond behavior explicitly stated in the frozen problem statement. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.4 |

# CFR-MMS-002 — Operational Role Assignment and Handoff

| CFR Statement | MMS shall allow the Mess Admin to assign or reassign exactly one active Mess Caretaker and one active Mess Warden for specified durations using institutional employee identities; mid-cycle changes take immediate effect and pending Caretaker-owned work becomes actionable by the newly active Caretaker. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-002, AFR-MMS-003, AFR-MMS-004, AFR-MMS-005, AFR-MMS-006, AFR-MMS-096, AFR-MMS-097, AFR-MMS-098, AFR-MMS-099 |
| Rolled-up UC(s) | MMS-UC-001 |
| Rolled-up BR(s) | BR-MMS-002, BR-MMS-006, BR-MMS-003, BR-MMS-004, BR-MMS-007 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-002 | MMS shall allow the Mess Admin to assign the Mess Caretaker role to a specific institute employee. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.2.1, §3.3.11 |
| AFR-MMS-003 | MMS shall allow the Mess Admin to assign the Mess Warden role to a specific institute employee. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.2.1, §3.3.11 |
| AFR-MMS-004 | MMS shall allow the Mess Admin to reassign the active Mess Caretaker or Mess Warden when required, including during an active mess cycle. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.2.1, §3.3.11 |
| AFR-MMS-005 | MMS shall maintain exactly one active Mess Caretaker at a time. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.2.1, §3.3.11 |
| AFR-MMS-006 | MMS shall maintain exactly one active Mess Warden at a time. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.2.1, §3.3.11 |
| AFR-MMS-096 | MMS Caretaker and Warden role assignments shall be time-bound for specified durations. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.11 |
| AFR-MMS-097 | A mid-cycle Caretaker or Warden reassignment shall take effect immediately in MMS from the recorded reassignment time. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Drive the triggering state/event and verify the required automatic resulting state/effect and history. |  |  |  |  | PS §3.3.11 |
| AFR-MMS-098 | From the effective time of a Caretaker reassignment, pending operational requests shall become visible to and actionable by the newly assigned active Mess Caretaker. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.11 |
| AFR-MMS-099 | MMS shall consume institute employee identities needed for Mess Admin, Caretaker, and Warden role assignment without owning employee master-data management. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.4 |

# CFR-MMS-003 — Mess Admin Operational Data Access Boundary

| CFR Statement | MMS shall restrict the Mess Admin to role-management responsibilities and prevent access to operational mess data. |
| --- | --- |
| Semantic Profile | C |
| Constituent AFRs | AFR-MMS-007 |
| Rolled-up UC(s) | MMS-UC-001 |
| Rolled-up BR(s) | BR-MMS-005 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-007 | MMS shall prevent the Mess Admin from accessing operational mess data, including student requests, billing details, rebate details, special-food requests, vacation responses, and feedback entries. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.2.1, §3.3.11 |

# CFR-MMS-004 — Mess Registration Request Lifecycle

| CFR Statement | MMS shall support Caretaker-controlled registration windows in which Students may submit registration requests only while a window is open and the active Mess Caretaker may approve or reject submitted requests. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-012, AFR-MMS-013, AFR-MMS-015 |
| Rolled-up UC(s) | MMS-UC-002, MMS-UC-003, MMS-UC-004 |
| Rolled-up BR(s) | BR-MMS-008, BR-MMS-009, BR-MMS-010 |
| Rolled-up WF(s) | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-012 | MMS shall allow the Mess Caretaker to open a registration window for a mess cycle or other designated period. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-013 | MMS shall accept a Student registration request only while the registration window is open. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-015 | MMS shall allow the Mess Caretaker to approve or reject each submitted registration request. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.1 |

# CFR-MMS-005 — Mess Deregistration Request Lifecycle

| CFR Statement | MMS shall allow a registered Student to submit a deregistration request at any time, allow the active Mess Caretaker to approve or reject it, record the decision immediately, and make an approved deregistration effective from the next calendar day. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-014, AFR-MMS-016, AFR-MMS-017, AFR-MMS-018 |
| Rolled-up UC(s) | MMS-UC-005, MMS-UC-006, MMS-UC-027 |
| Rolled-up BR(s) | BR-MMS-012, BR-MMS-010, BR-MMS-013 |
| Rolled-up WF(s) | BW-MMS-03, BW-MMS-04, CW-MMS-02 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-014 | MMS shall allow a Student to submit a deregistration request at any time while registered for mess service. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-016 | MMS shall allow the Mess Caretaker to approve or reject each submitted deregistration request. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-017 | MMS shall record the Caretaker’s decision on a deregistration request when the decision is made. | Retained as a distinct data/computation obligation with an independently testable outcome. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-018 | For an approved deregistration request, MMS shall make the mess-service effect start from the next calendar day. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Drive the triggering state/event and verify the required automatic resulting state/effect and history. |  |  |  |  | PS §3.3.1 |

# CFR-MMS-006 — Warden Operational Request Oversight

| CFR Statement | MMS shall allow the Mess Warden to view operational Student requests for supervisory oversight while preventing the Warden from deciding or otherwise acting on those requests. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-019, AFR-MMS-020 |
| Rolled-up UC(s) | MMS-UC-007 |
| Rolled-up BR(s) | BR-MMS-011 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-019 | MMS shall allow the Mess Warden to view operational student requests for supervisory oversight, including registration and deregistration requests. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.4, §3.3.1 |
| AFR-MMS-020 | MMS shall prevent the Mess Warden from approving, rejecting, registering, deregistering, or otherwise deciding operational student requests. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.2.4, §3.3.1 |

# CFR-MMS-007 — Student Request Tracking and Registration/Deregistration Notifications

| CFR Statement | MMS shall maintain Student-visible request status/history and trigger the defined submission and decision email notifications for registration and deregistration requests. |
| --- | --- |
| Semantic Profile | I+B |
| Constituent AFRs | AFR-MMS-011, AFR-MMS-021, AFR-MMS-022, AFR-MMS-023 |
| Rolled-up UC(s) | MMS-UC-026, MMS-UC-003, MMS-UC-004, MMS-UC-005, MMS-UC-006, MMS-UC-027 |
| Rolled-up BR(s) | BR-MMS-042, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-01, BW-MMS-02, CW-MMS-01, BW-MMS-03, BW-MMS-04, CW-MMS-02 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-011 | MMS shall allow a Student to track the status and history of the Student’s submitted MMS requests. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.2.2 |
| AFR-MMS-021 | MMS shall maintain request status and request history for registration and deregistration requests. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.1 |
| AFR-MMS-022 | MMS shall trigger a system-generated email notification to the Student when a registration or deregistration request is submitted. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.1, §3.3.10 |
| AFR-MMS-023 | MMS shall trigger a system-generated email notification to the Student when a registration or deregistration request is approved or rejected. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.1, §3.3.10 |

# CFR-MMS-008 — Weekly Menu Management and Access

| CFR Statement | MMS shall store a day-wise and meal-wise weekly menu, allow authorized actors to view it, allow the Mess Caretaker to maintain menu items, and notify Students when the menu is updated; Mess Admin menu visibility remains subject to the unresolved frozen-PS conflict. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-008, AFR-MMS-024, AFR-MMS-025, AFR-MMS-026, AFR-MMS-027, AFR-MMS-028, AFR-MMS-029, AFR-MMS-030, AFR-MMS-031, AFR-MMS-032 |
| Rolled-up UC(s) | MMS-UC-009, MMS-UC-008 |
| Rolled-up BR(s) | BR-MMS-014, BR-MMS-038, BR-MMS-039, BR-MMS-015, BR-MMS-035 |
| Rolled-up WF(s) | N/A |
| Coverage | Partial |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-008 | MMS shall allow a Student to view the weekly mess menu. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.2, §3.3.2 |
| AFR-MMS-024 | MMS shall store the weekly mess menu in a day-wise and meal-wise structure covering breakfast, lunch, and dinner. | Retained as a distinct data/computation obligation with an independently testable outcome. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-025 | MMS shall allow Students to view the weekly mess menu according to their access rights. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-026 | MMS shall allow the Mess Caretaker to view the weekly mess menu. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-027 | MMS shall allow the Mess Warden to view the weekly mess menu. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-028 | MMS shall represent the Mess Admin weekly-menu visibility consistently with the frozen PS; the PS simultaneously states that Mess Admin may view the menu according to access rights and that Mess Admin has no operational-data access. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.2.1 vs §3.3.2 |
| AFR-MMS-029 | MMS shall allow the Mess Caretaker to add weekly mess menu items. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-030 | MMS shall allow the Mess Caretaker to delete weekly mess menu items. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-031 | MMS shall allow the Mess Caretaker to modify weekly mess menu items. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.2 |
| AFR-MMS-032 | MMS shall trigger system-generated email notifications to Students when the weekly menu is updated. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.2, §3.3.10 |

# CFR-MMS-009 — Monthly Billing Management and Student Billing Access

| CFR Statement | MMS shall generate monthly mess bills on the calendar-month cycle from served-day charges, approved special-meal/add-on charges, and approved rebate deductions; require Caretaker review/finalization before publication; allow Students to view published bills and MMS balances; and notify Students on publication, while excluding payment/accounting settlement functions. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-009, AFR-MMS-033, AFR-MMS-034, AFR-MMS-035, AFR-MMS-036, AFR-MMS-037, AFR-MMS-038, AFR-MMS-039, AFR-MMS-040, AFR-MMS-041, AFR-MMS-042, AFR-MMS-043 |
| Rolled-up UC(s) | MMS-UC-011, MMS-UC-030, MMS-UC-015, MMS-UC-010 |
| Rolled-up BR(s) | BR-MMS-040, BR-MMS-016, BR-MMS-017, BR-MMS-030, BR-MMS-019, BR-MMS-018, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-16, CW-MMS-05, CW-MMS-03 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-009 | MMS shall allow a Student to view the Student’s monthly mess bills. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.2, §3.3.3 |
| AFR-MMS-033 | MMS shall generate mess bills using a calendar-month billing cycle. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-034 | MMS shall include daily-rate charges for served days in monthly bill computation. | Retained as a distinct data/computation obligation with an independently testable outcome. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-035 | MMS shall include charges for approved special meals or add-ons in monthly bill computation. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-036 | MMS shall deduct approved rebates in monthly bill computation. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-037 | MMS shall allow the Mess Caretaker to review system-generated monthly mess bills before publication. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-038 | MMS shall require the Mess Caretaker to finalize monthly mess bills before publication. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-039 | MMS shall allow the Mess Caretaker to publish finalized monthly mess bills. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-040 | MMS shall allow a Student to view the Student’s published monthly mess bill. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-041 | MMS shall allow a Student to view the Student’s outstanding mess balance maintained within MMS. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.3 |
| AFR-MMS-042 | MMS shall not perform payment collection, accounting settlement, or payroll/account integration as part of billing management. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.3.3, §3.4 |
| AFR-MMS-043 | MMS shall trigger a system-generated email notification to Students when monthly bills are published. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |

# CFR-MMS-010 — Feedback Recording and Review

| CFR Statement | MMS shall accept and store Student text feedback and allow the Mess Caretaker and Mess Warden to view it for their stated purposes, without implying a formal feedback-resolution workflow. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-044, AFR-MMS-045, AFR-MMS-046, AFR-MMS-047, AFR-MMS-048 |
| Rolled-up UC(s) | MMS-UC-012, MMS-UC-013 |
| Rolled-up BR(s) | BR-MMS-020 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-044 | MMS shall allow a Student to submit text feedback related to mess services. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.4 |
| AFR-MMS-045 | MMS shall allow the Mess Caretaker to view Student feedback entries for operational review, record keeping, and analysis. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.3, §3.3.4 |
| AFR-MMS-046 | MMS shall allow the Mess Warden to view Student feedback entries for supervisory oversight, record keeping, and analysis. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.4, §3.3.4 |
| AFR-MMS-047 | MMS shall store Student feedback entries with relevant record information. | Retained as a distinct data/computation obligation with an independently testable outcome. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.4 |
| AFR-MMS-048 | MMS shall not assume a formal feedback-resolution workflow because none is defined in the frozen problem statement. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.3.4 |

# CFR-MMS-011 — Rebate Submission and Validation

| CFR Statement | MMS shall allow a Student to submit a rebate request containing the required reason and dates only when the supported reason rules, minimum duration, lead-time, and non-overlap constraints are satisfied. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-049, AFR-MMS-050, AFR-MMS-051, AFR-MMS-052, AFR-MMS-053, AFR-MMS-054 |
| Rolled-up UC(s) | MMS-UC-014 |
| Rolled-up BR(s) | BR-MMS-024, BR-MMS-021, BR-MMS-022, BR-MMS-023 |
| Rolled-up WF(s) | BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-049 | MMS shall allow a Student to submit a mess rebate request. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-050 | A rebate request shall capture a reason, start date, and end date. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-051 | MMS shall restrict rebate reasons to medical, institute leave, family function, and other, and shall require an explanation when other is selected. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-052 | MMS shall accept a rebate request only when the requested rebate duration is at least 3 days. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-053 | MMS shall accept a rebate request only when it is submitted at least 1 calendar day before the requested rebate start date. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-054 | MMS shall prevent overlapping rebate requests for the same Student. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.3.5 |

# CFR-MMS-012 — Rebate Decision, Status, Billing Effect and Notifications

| CFR Statement | MMS shall allow the Mess Caretaker to approve or reject a rebate request and, where external policy permits, modify dates before approval; approved dates shall drive billing adjustment, Students shall be able to track status, and defined submission/decision notifications shall be triggered. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-055, AFR-MMS-056, AFR-MMS-057, AFR-MMS-058, AFR-MMS-059, AFR-MMS-060, AFR-MMS-061 |
| Rolled-up UC(s) | MMS-UC-015, MMS-UC-026, MMS-UC-030, MMS-UC-014 |
| Rolled-up BR(s) | BR-MMS-025, BR-MMS-019, BR-MMS-042, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03, BW-MMS-16 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-055 | MMS shall allow the Mess Caretaker to approve or reject a rebate request. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-056 | MMS shall allow the Mess Caretaker to modify rebate dates before approval where permitted by the stated external mess policy. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-057 | When rebate dates are modified before approval, MMS shall use the approved dates as the rebate dates for billing adjustment. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-058 | MMS shall allow Students to track rebate request status as Pending, Approved, or Rejected. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-059 | MMS shall automatically apply approved rebate adjustments to the corresponding monthly mess bill. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Drive the triggering state/event and verify the required automatic resulting state/effect and history. |  |  |  |  | PS §3.3.5 |
| AFR-MMS-060 | MMS shall trigger a system-generated email notification to the Student when a rebate request is submitted. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |
| AFR-MMS-061 | MMS shall trigger a system-generated email notification to the Student when a rebate request is approved or rejected. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |

# CFR-MMS-013 — Vacation Food Continuity Survey Setup and Notifications

| CFR Statement | MMS shall allow the Mess Caretaker to create an upcoming-vacation food-continuity survey for currently registered Students, set its response deadline, trigger the survey-creation notification, and issue reminders without inventing an unspecified reminder cadence. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-062, AFR-MMS-063, AFR-MMS-065, AFR-MMS-068, AFR-MMS-069 |
| Rolled-up UC(s) | MMS-UC-016, MMS-UC-031 |
| Rolled-up BR(s) | BR-MMS-026, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-08, BW-MMS-09, BW-MMS-10, CW-MMS-04 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-062 | MMS shall allow the Mess Caretaker to create a vacation food continuity survey for an upcoming institute vacation. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.6 |
| AFR-MMS-063 | MMS shall make a vacation food continuity survey available only to currently registered Students. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.6 |
| AFR-MMS-065 | MMS shall allow the Mess Caretaker to set a response deadline for each vacation food continuity survey. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.6 |
| AFR-MMS-068 | MMS shall trigger system-generated email notification when a vacation food continuity survey is created. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |
| AFR-MMS-069 | MMS shall trigger system-generated email reminders for vacation food continuity surveys; reminder timing is not specified by the frozen PS. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |

# CFR-MMS-014 — Vacation Survey Response, Default and Summary

| CFR Statement | MMS shall accept only Yes/No Student vacation-food responses, record No automatically for registered Students who do not respond by the deadline, and allow the Mess Caretaker to view the resulting response summary. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-064, AFR-MMS-066, AFR-MMS-067 |
| Rolled-up UC(s) | MMS-UC-017, MMS-UC-028, MMS-UC-018 |
| Rolled-up BR(s) | BR-MMS-041, BR-MMS-027 |
| Rolled-up WF(s) | BW-MMS-08, BW-MMS-09, CW-MMS-04, BW-MMS-10 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-064 | MMS shall restrict a Student’s vacation food continuity response to Yes or No. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.3.6 |
| AFR-MMS-066 | For each currently registered Student who has not responded by the survey deadline, MMS shall record the response as No. | Retained as a distinct data/computation obligation with an independently testable outcome. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.6 |
| AFR-MMS-067 | MMS shall allow the Mess Caretaker to view the vacation survey response summary for operational planning. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.6 |

# CFR-MMS-015 — Special Food Request Submission

| CFR Statement | MMS shall allow a Student to submit a special-food request for illness or a personal event only with the required lead time and shall trigger the submission notification. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-070, AFR-MMS-071, AFR-MMS-075 |
| Rolled-up UC(s) | MMS-UC-019 |
| Rolled-up BR(s) | BR-MMS-028, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-070 | MMS shall allow a Student to submit a special food request due to illness or a personal event. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-071 | MMS shall accept a special food request only when submitted at least 1 calendar day before the requested date. | Retained separately because the constraint can fail independently and requires focused validation. | Test boundary-valid and boundary-invalid cases and verify the stated rule is enforced. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-075 | MMS shall trigger a system-generated email notification to the Student when a special food request is submitted. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.7, §3.3.10 |

# CFR-MMS-016 — Special Food Decision and Default Rejection

| CFR Statement | MMS shall allow the Mess Caretaker to approve or reject a special-food request within the institution-defined decision period, automatically reject an undecided request when that period expires, and trigger the applicable decision notification. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-072, AFR-MMS-073, AFR-MMS-076 |
| Rolled-up UC(s) | MMS-UC-020, MMS-UC-029 |
| Rolled-up BR(s) | BR-MMS-029, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-11, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05, BW-MMS-12 |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-072 | MMS shall allow the Mess Caretaker to approve or reject a special food request within the institution-defined stipulated decision period. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-073 | If a special food request is not decided within the institution-defined stipulated decision period, MMS shall mark the request Rejected by default. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Drive the triggering state/event and verify the required automatic resulting state/effect and history. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-076 | MMS shall trigger a system-generated email notification to the Student when a special food request is approved or rejected. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.7, §3.3.10 |

# CFR-MMS-017 — Special Food Status, Fulfillment and Billing Link

| CFR Statement | MMS shall maintain special-food request status/history through Requested, Approved, Rejected, Served, and Cancelled; allow Served/Cancelled only after Approved; trigger fulfillment-related notifications; and add approved special-food charges to monthly billing, while preserving unresolved fulfillment-actor and cancellation-billing questions. |
| --- | --- |
| Semantic Profile | I+C+B |
| Constituent AFRs | AFR-MMS-074, AFR-MMS-077, AFR-MMS-078, AFR-MMS-079, AFR-MMS-080 |
| Rolled-up UC(s) | MMS-UC-019, MMS-UC-026, MMS-UC-020, MMS-UC-030, MMS-UC-021, MMS-UC-029 |
| Rolled-up BR(s) | BR-MMS-042, BR-MMS-030, BR-MMS-031, BR-MMS-035 |
| Rolled-up WF(s) | BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05, BW-MMS-16 |
| Coverage | Partial |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-074 | MMS shall maintain special food request history and status so the Student can track the request. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-077 | MMS shall add charges for approved special food requests to the Student’s monthly mess bill. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-078 | MMS shall track special food requests using the states Requested, Approved, Rejected, Served, and Cancelled. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-079 | MMS shall permit Served and Cancelled statuses only after a special food request has reached Approved status. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.7 |
| AFR-MMS-080 | MMS shall trigger system-generated email notifications for special-food fulfillment-related updates where applicable. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |

# CFR-MMS-018 — Mess Announcements and History

| CFR Statement | MMS shall allow the Mess Caretaker or Mess Warden to publish mess-related announcements, notify Students of new announcements, maintain announcement history, and allow MMS actors to view that history according to access rights. |
| --- | --- |
| Semantic Profile | I+C |
| Constituent AFRs | AFR-MMS-010, AFR-MMS-081, AFR-MMS-082, AFR-MMS-083, AFR-MMS-084, AFR-MMS-085 |
| Rolled-up UC(s) | MMS-UC-023, MMS-UC-022 |
| Rolled-up BR(s) | BR-MMS-033, BR-MMS-032, BR-MMS-035 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-010 | MMS shall allow a Student to view mess-service announcements relevant to the Student. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.2.2, §3.3.8 |
| AFR-MMS-081 | MMS shall allow the Mess Caretaker to publish mess-related announcements. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.2.3, §3.3.8 |
| AFR-MMS-082 | MMS shall allow the Mess Warden to publish mess-related announcements. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Execute the stated actor goal under valid preconditions and verify the recorded outcome/postcondition. |  |  |  |  | PS §3.2.4, §3.3.8 |
| AFR-MMS-083 | MMS shall trigger a system-generated email notification to Students when a new announcement is published. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.8, §3.3.10 |
| AFR-MMS-084 | MMS shall maintain announcement history relevant to mess services. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.8 |
| AFR-MMS-085 | MMS shall allow MMS actors to view announcement history according to their access rights. | Retained separately because the lifecycle/state effect is independently verifiable and workflow-relevant. | Exercise relevant lifecycle paths and verify allowed states, ordering, and persisted history/status. |  |  |  |  | PS §3.3.8 |

# CFR-MMS-019 — Warden Supervisory Reporting

| CFR Statement | MMS shall allow the Mess Warden to view and search registered-Student lists, rebate summaries, and vacation-survey response summaries. |
| --- | --- |
| Semantic Profile | I |
| Constituent AFRs | AFR-MMS-086, AFR-MMS-087, AFR-MMS-088 |
| Rolled-up UC(s) | MMS-UC-024 |
| Rolled-up BR(s) | BR-MMS-034 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-086 | MMS shall allow the Mess Warden to view and search registered Student lists. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.9 |
| AFR-MMS-087 | MMS shall allow the Mess Warden to view and search rebate summaries. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.9 |
| AFR-MMS-088 | MMS shall allow the Mess Warden to view and search vacation survey response summaries. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Authenticate as the stated actor and verify the permitted information is visible and unauthorized information/actions are absent. |  |  |  |  | PS §3.3.9 |

# CFR-MMS-020 — Caretaker Operational Reporting

| CFR Statement | MMS shall allow the Mess Caretaker to generate registration-trend reports, special-meal logs, and billing-summary reports. |
| --- | --- |
| Semantic Profile | I |
| Constituent AFRs | AFR-MMS-089, AFR-MMS-090, AFR-MMS-091 |
| Rolled-up UC(s) | MMS-UC-025 |
| Rolled-up BR(s) | BR-MMS-034 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-089 | MMS shall allow the Mess Caretaker to generate registration trend reports. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.2.3, §3.3.9 |
| AFR-MMS-090 | MMS shall allow the Mess Caretaker to generate special meal logs. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.2.3, §3.3.9 |
| AFR-MMS-091 | MMS shall allow the Mess Caretaker to generate billing summary reports. | Retained as a distinct actor/system service outcome that can be accepted and traced independently. | Prepare controlled billing inputs and verify generated values/state include the required charge/deduction semantics. |  |  |  |  | PS §3.2.3, §3.3.9 |

# CFR-MMS-021 — MMS Report Scope Boundary

| CFR Statement | MMS reporting shall remain limited to MMS operational and supervisory information and shall exclude external financial, payroll, procurement, and inventory reporting. |
| --- | --- |
| Semantic Profile | C |
| Constituent AFRs | AFR-MMS-092, AFR-MMS-093 |
| Rolled-up UC(s) | MMS-UC-024, MMS-UC-025 |
| Rolled-up BR(s) | BR-MMS-034 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-092 | MMS reports shall be limited to MMS operational and supervisory information. | Retained because it expresses a distinct verifiable obligation within the parent coherent requirement. | Verify the stated obligation directly against its condition and expected observable outcome. |  |  |  |  | PS §3.3.9 |
| AFR-MMS-093 | MMS shall not provide external financial, payroll, procurement, or inventory reports. | Retained separately because the constraint can fail independently and requires focused validation. | Attempt the prohibited action/scope and verify MMS blocks or excludes it without invalid state change. |  |  |  |  | PS §3.3.9 |

# CFR-MMS-022 — Notification Governance and Email Boundary

| CFR Statement | MMS shall trigger system-generated email notifications only for events explicitly identified in the frozen Problem Statement and shall not own the external email-delivery infrastructure. |
| --- | --- |
| Semantic Profile | C |
| Constituent AFRs | AFR-MMS-094, AFR-MMS-095 |
| Rolled-up UC(s) | N/A |
| Rolled-up BR(s) | BR-MMS-035 |
| Rolled-up WF(s) | N/A |
| Coverage | Full |

| AFR ID | AFR Statement | Atomicity / Decomposition Rationale | Verification / Acceptance Focus | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Min. Rep. | PS Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AFR-MMS-094 | MMS shall trigger system-generated email notifications only for MMS events explicitly identified in the frozen problem statement. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.3.10 |
| AFR-MMS-095 | MMS shall not own the external email delivery infrastructure used to deliver system-generated email notifications. | Retained as a distinct observable notification obligation with its own trigger/outcome. | Trigger the stated event and verify the MMS notification event is issued to the stated recipient(s); do not test external delivery infrastructure. |  |  |  |  | PS §3.1, §3.3.10 |
