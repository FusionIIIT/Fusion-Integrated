# 05 MMS Workflow Specifications v1.4 FINAL(1)

MMS Workflow Specifications

v1.4 FINAL — Basis/Composite workflows; STT authoritative

| Version | v1.4 FINAL |
| --- | --- |
| Basis Workflows | 16 |
| Composite Workflows | 5 |
| Complete Workflow | Not forced; the five composites plus one standalone billing basis workflow communicate the supported behavior clearly. |
| System transitions | System appears only for meaningful autonomous state changes grounded in event-triggered UCs. |
| Excluded topics | Role assignment, menu publication, announcement publication, feedback, and reporting remain outside workflows because the PS does not define connected state-changing progressions for them. |

# BW-MMS-01 — Registration — Approved

| Workflow ID | BW-MMS-01 |
| --- | --- |
| Workflow Name | Registration — Approved |
| Type | Basis |
| Purpose / Scope | One valid path from opening a registration window through Student submission to Caretaker approval. |
| Trigger | Caretaker opens a registration window; Student then submits during the open window. |
| Participants | Mess Caretaker; Student |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-02; CW-MMS-01; CW-MMS-02 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-002, MMS-UC-003, MMS-UC-004 |
| Related BRs | BR-MMS-008, BR-MMS-009, BR-MMS-035, BR-MMS-010 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Registration Window Not Open | Mess Caretaker | MMS-UC-002 — Open Registration Window | Window information is sufficient; outcome: Open | Registration Window Open | BR-MMS-008 |
| 2 | Registration Window Open | Student | MMS-UC-003 — Submit Registration Request | Window is open; valid submission | Registration Request Pending | BR-MMS-009; BR-MMS-035 |
| 3 | Registration Request Pending | Mess Caretaker | MMS-UC-004 — Review Registration Request | Outcome: Approve | Registration Request Approved / Student Registered | BR-MMS-010; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-01.

# BW-MMS-02 — Registration — Rejected

| Workflow ID | BW-MMS-02 |
| --- | --- |
| Workflow Name | Registration — Rejected |
| Type | Basis |
| Purpose / Scope | One valid path from opening a registration window through Student submission to Caretaker rejection. |
| Trigger | Caretaker opens a registration window; Student then submits during the open window. |
| Participants | Mess Caretaker; Student |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-01; CW-MMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-002, MMS-UC-003, MMS-UC-004 |
| Related BRs | BR-MMS-008, BR-MMS-009, BR-MMS-035, BR-MMS-010 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Registration Window Not Open | Mess Caretaker | MMS-UC-002 — Open Registration Window | Window information is sufficient; outcome: Open | Registration Window Open | BR-MMS-008 |
| 2 | Registration Window Open | Student | MMS-UC-003 — Submit Registration Request | Window is open; valid submission | Registration Request Pending | BR-MMS-009; BR-MMS-035 |
| 3 | Registration Request Pending | Mess Caretaker | MMS-UC-004 — Review Registration Request | Outcome: Reject | Registration Request Rejected | BR-MMS-010; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-02.

# CW-MMS-01 — Registration Request Lifecycle

| Workflow ID | CW-MMS-01 |
| --- | --- |
| Workflow Name | Registration Request Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine the approved and rejected registration basis paths while preserving the common opening/submission prefix. |
| Trigger | Caretaker opens registration window; Student submits during open window. |
| Participants | Mess Caretaker; Student |
| Constituent Workflows | BW-MMS-01; BW-MMS-02 |
| Related Workflows | CW-MMS-02 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-002, MMS-UC-003, MMS-UC-004 |
| Related BRs | BR-MMS-008, BR-MMS-009, BR-MMS-035, BR-MMS-010 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Registration Window Not Open | Mess Caretaker | MMS-UC-002 — Open Registration Window | Outcome: Open | Registration Window Open | BR-MMS-008 |
| 2 | Registration Window Open | Student | MMS-UC-003 — Submit Registration Request | Guard: registration window open; valid submission | Registration Request Pending | BR-MMS-009; BR-MMS-035 |
| 3 | Registration Request Pending | Mess Caretaker | MMS-UC-004 — Review Registration Request | Outcome: Approve | Registration Request Approved / Student Registered | BR-MMS-010; BR-MMS-035 |
| 4 | Registration Request Pending | Mess Caretaker | MMS-UC-004 — Review Registration Request | Outcome: Reject | Registration Request Rejected | BR-MMS-010; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page CW-MMS-01.

# BW-MMS-03 — Deregistration — Approved

| Workflow ID | BW-MMS-03 |
| --- | --- |
| Workflow Name | Deregistration — Approved |
| Type | Basis |
| Purpose / Scope | Registered Student submission, Caretaker approval, and the next-calendar-day System transition that makes deregistration effective. |
| Trigger | Registered Student submits deregistration request. |
| Participants | Student; Mess Caretaker; System |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-04; CW-MMS-02; CW-MMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-005, MMS-UC-006, MMS-UC-027 |
| Related BRs | BR-MMS-012, BR-MMS-035, BR-MMS-010, BR-MMS-013 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Student Registered | Student | MMS-UC-005 — Submit Deregistration Request | Valid submission | Deregistration Request Pending | BR-MMS-012; BR-MMS-035 |
| 2 | Deregistration Request Pending | Mess Caretaker | MMS-UC-006 — Review Deregistration Request | Outcome: Approve | Deregistration Approved — Awaiting Effective Date | BR-MMS-010; BR-MMS-035 |
| 3 | Deregistration Approved — Awaiting Effective Date | System | MMS-UC-027 — Activate Approved Deregistration | Trigger: next calendar day begins after approval | Student Deregistered / Mess Service Inactive | BR-MMS-013 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-03.

# BW-MMS-04 — Deregistration — Rejected

| Workflow ID | BW-MMS-04 |
| --- | --- |
| Workflow Name | Deregistration — Rejected |
| Type | Basis |
| Purpose / Scope | One path from registered Student submission through Caretaker rejection. |
| Trigger | Registered Student submits deregistration request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-03; CW-MMS-02 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-005, MMS-UC-006 |
| Related BRs | BR-MMS-012, BR-MMS-035, BR-MMS-010 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Student Registered | Student | MMS-UC-005 — Submit Deregistration Request | Valid submission | Deregistration Request Pending | BR-MMS-012; BR-MMS-035 |
| 2 | Deregistration Request Pending | Mess Caretaker | MMS-UC-006 — Review Deregistration Request | Outcome: Reject | Deregistration Request Rejected / Student remains Registered | BR-MMS-010; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-04.

# CW-MMS-02 — Deregistration Request Lifecycle

| Workflow ID | CW-MMS-02 |
| --- | --- |
| Workflow Name | Deregistration Request Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine the approved and rejected deregistration paths. |
| Trigger | Registered Student submits deregistration request. |
| Participants | Student; Mess Caretaker; System |
| Constituent Workflows | BW-MMS-03; BW-MMS-04 |
| Related Workflows | CW-MMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-005, MMS-UC-006, MMS-UC-027 |
| Related BRs | BR-MMS-012, BR-MMS-035, BR-MMS-010, BR-MMS-013 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Student Registered | Student | MMS-UC-005 — Submit Deregistration Request | Valid submission | Deregistration Request Pending | BR-MMS-012; BR-MMS-035 |
| 2 | Deregistration Request Pending | Mess Caretaker | MMS-UC-006 — Review Deregistration Request | Outcome: Approve | Deregistration Approved — Awaiting Effective Date | BR-MMS-010; BR-MMS-035 |
| 3 | Deregistration Approved — Awaiting Effective Date | System | MMS-UC-027 — Activate Approved Deregistration | Trigger: next calendar day begins after approval | Student Deregistered / Mess Service Inactive | BR-MMS-013 |
| 4 | Deregistration Request Pending | Mess Caretaker | MMS-UC-006 — Review Deregistration Request | Outcome: Reject | Deregistration Request Rejected / Student remains Registered | BR-MMS-010; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page CW-MMS-02.

# BW-MMS-05 — Rebate — Approved as Submitted

| Workflow ID | BW-MMS-05 |
| --- | --- |
| Workflow Name | Rebate — Approved as Submitted |
| Type | Basis |
| Purpose / Scope | Valid rebate submission followed by approval without changing dates. |
| Trigger | Student submits a valid rebate request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-06; BW-MMS-07; CW-MMS-03 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-014, MMS-UC-015 |
| Related BRs | BR-MMS-021, BR-MMS-024, BR-MMS-035, BR-MMS-019, BR-MMS-025 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Current Rebate Request | Student | MMS-UC-014 — Submit Rebate Request | Guards: reason/date data complete; duration >=3 days; >=1-day lead time; no overlap | Rebate Request Pending | BR-MMS-021 to BR-MMS-024; BR-MMS-035 |
| 2 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Approve without date modification | Rebate Approved; approved dates used for billing adjustment | BR-MMS-019; BR-MMS-025; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-05.

# BW-MMS-06 — Rebate — Dates Modified then Approved

| Workflow ID | BW-MMS-06 |
| --- | --- |
| Workflow Name | Rebate — Dates Modified then Approved |
| Type | Basis |
| Purpose / Scope | Valid rebate submission followed by policy-permitted date modification and approval. |
| Trigger | Student submits a valid rebate request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-05; BW-MMS-07; CW-MMS-03 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-014, MMS-UC-015 |
| Related BRs | BR-MMS-021, BR-MMS-024, BR-MMS-035, BR-MMS-019, BR-MMS-025 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Current Rebate Request | Student | MMS-UC-014 — Submit Rebate Request | Guards: reason/date data complete; duration >=3 days; >=1-day lead time; no overlap | Rebate Request Pending | BR-MMS-021 to BR-MMS-024; BR-MMS-035 |
| 2 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Modify dates where external policy permits, then Approve | Rebate Approved with Modified Dates; approved dates used for billing adjustment | BR-MMS-019; BR-MMS-025; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-06.

# BW-MMS-07 — Rebate — Rejected

| Workflow ID | BW-MMS-07 |
| --- | --- |
| Workflow Name | Rebate — Rejected |
| Type | Basis |
| Purpose / Scope | Valid rebate submission followed by Caretaker rejection. |
| Trigger | Student submits a valid rebate request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-05; BW-MMS-06; CW-MMS-03 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-014, MMS-UC-015 |
| Related BRs | BR-MMS-021, BR-MMS-024, BR-MMS-035 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Current Rebate Request | Student | MMS-UC-014 — Submit Rebate Request | Guards: reason/date data complete; duration >=3 days; >=1-day lead time; no overlap | Rebate Request Pending | BR-MMS-021 to BR-MMS-024; BR-MMS-035 |
| 2 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Reject | Rebate Rejected | BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-07.

# CW-MMS-03 — Rebate Request Lifecycle

| Workflow ID | CW-MMS-03 |
| --- | --- |
| Workflow Name | Rebate Request Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine valid rebate submission with the three materially different Caretaker outcomes. |
| Trigger | Student submits a valid rebate request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | BW-MMS-05; BW-MMS-06; BW-MMS-07 |
| Related Workflows | N/A |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-014, MMS-UC-015 |
| Related BRs | BR-MMS-021, BR-MMS-024, BR-MMS-035, BR-MMS-019, BR-MMS-025 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Current Rebate Request | Student | MMS-UC-014 — Submit Rebate Request | Guards: reason/date data complete; duration >=3 days; >=1-day lead time; no overlap | Rebate Request Pending | BR-MMS-021 to BR-MMS-024; BR-MMS-035 |
| 2 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Approve without date modification | Rebate Approved; billing adjustment uses approved dates | BR-MMS-019; BR-MMS-035 |
| 3 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Modify dates where permitted, then Approve | Rebate Approved with Modified Dates; billing adjustment uses modified approved dates | BR-MMS-019; BR-MMS-025; BR-MMS-035 |
| 4 | Rebate Request Pending | Mess Caretaker | MMS-UC-015 — Review Rebate Request | Outcome: Reject | Rebate Rejected | BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page CW-MMS-03.

# BW-MMS-08 — Vacation Survey — Yes Response

| Workflow ID | BW-MMS-08 |
| --- | --- |
| Workflow Name | Vacation Survey — Yes Response |
| Type | Basis |
| Purpose / Scope | Create survey and record an explicit Yes response. |
| Trigger | Caretaker creates survey. |
| Participants | Mess Caretaker; Student |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-09; BW-MMS-10; CW-MMS-04 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-016, MMS-UC-017 |
| Related BRs | BR-MMS-026, BR-MMS-035, BR-MMS-041 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Vacation Survey Not Created | Mess Caretaker | MMS-UC-016 — Create Vacation Food Continuity Survey | Upcoming vacation identified; response deadline set; only currently registered Students included | Vacation Survey Open | BR-MMS-026; BR-MMS-035 |
| 2 | Vacation Survey Open | Student | MMS-UC-017 — Respond to Vacation Food Continuity Survey | Outcome: Yes before deadline | Vacation Response = Yes | BR-MMS-041 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-08.

# BW-MMS-09 — Vacation Survey — No Response

| Workflow ID | BW-MMS-09 |
| --- | --- |
| Workflow Name | Vacation Survey — No Response |
| Type | Basis |
| Purpose / Scope | Create survey and record an explicit No response. |
| Trigger | Caretaker creates survey. |
| Participants | Mess Caretaker; Student |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-08; BW-MMS-10; CW-MMS-04 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-016, MMS-UC-017 |
| Related BRs | BR-MMS-026, BR-MMS-035, BR-MMS-041 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Vacation Survey Not Created | Mess Caretaker | MMS-UC-016 — Create Vacation Food Continuity Survey | Upcoming vacation identified; response deadline set; only currently registered Students included | Vacation Survey Open | BR-MMS-026; BR-MMS-035 |
| 2 | Vacation Survey Open | Student | MMS-UC-017 — Respond to Vacation Food Continuity Survey | Outcome: No before deadline | Vacation Response = No | BR-MMS-041 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-09.

# BW-MMS-10 — Vacation Survey — Default No

| Workflow ID | BW-MMS-10 |
| --- | --- |
| Workflow Name | Vacation Survey — Default No |
| Type | Basis |
| Purpose / Scope | Create a vacation survey and apply the source-defined default No when the response deadline is reached for a non-responding registered Student. |
| Trigger | Caretaker creates survey; Student does not respond by deadline. |
| Participants | Mess Caretaker; System |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-08; BW-MMS-09; CW-MMS-04 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-016, MMS-UC-028 |
| Related BRs | BR-MMS-026, BR-MMS-035, BR-MMS-027 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Vacation Survey Not Created | Mess Caretaker | MMS-UC-016 — Create Vacation Food Continuity Survey | Upcoming vacation identified; response deadline set; only currently registered Students included | Vacation Survey Open | BR-MMS-026; BR-MMS-035 |
| 2 | Vacation Survey Open | System | MMS-UC-028 — Apply Default Vacation Response at Deadline | Trigger: response deadline reached; applicable Student has no recorded response | Vacation Response = Default No | BR-MMS-027 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-10.

# CW-MMS-04 — Vacation Food Continuity Response Lifecycle

| Workflow ID | CW-MMS-04 |
| --- | --- |
| Workflow Name | Vacation Food Continuity Response Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine the explicit Yes, explicit No, and default-No paths after survey creation. |
| Trigger | Caretaker creates survey. |
| Participants | Mess Caretaker; Student; System |
| Constituent Workflows | BW-MMS-08; BW-MMS-09; BW-MMS-10 |
| Related Workflows | N/A |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-016, MMS-UC-017, MMS-UC-028 |
| Related BRs | BR-MMS-026, BR-MMS-035, BR-MMS-041, BR-MMS-027 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Vacation Survey Not Created | Mess Caretaker | MMS-UC-016 — Create Vacation Food Continuity Survey | Upcoming vacation identified; response deadline set; only currently registered Students included | Vacation Survey Open | BR-MMS-026; BR-MMS-035 |
| 2 | Vacation Survey Open | Student | MMS-UC-017 — Respond to Vacation Food Continuity Survey | Outcome: Yes before deadline | Vacation Response = Yes | BR-MMS-041 |
| 3 | Vacation Survey Open | Student | MMS-UC-017 — Respond to Vacation Food Continuity Survey | Outcome: No before deadline | Vacation Response = No | BR-MMS-041 |
| 4 | Vacation Survey Open | System | MMS-UC-028 — Apply Default Vacation Response at Deadline | Trigger: response deadline reached; no explicit response | Vacation Response = Default No | BR-MMS-027 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page CW-MMS-04.

# BW-MMS-11 — Special Food — Rejected by Caretaker

| Workflow ID | BW-MMS-11 |
| --- | --- |
| Workflow Name | Special Food — Rejected by Caretaker |
| Type | Basis |
| Purpose / Scope | Valid special-food submission followed by explicit Caretaker rejection. |
| Trigger | Student submits valid request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-12 to BW-MMS-15; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-029, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Reject within stipulated decision period | Rejected | BR-MMS-029; BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-11.

# BW-MMS-12 — Special Food — Default Rejected

| Workflow ID | BW-MMS-12 |
| --- | --- |
| Workflow Name | Special Food — Default Rejected |
| Type | Basis |
| Purpose / Scope | Valid special-food submission followed by source-defined default rejection when no decision occurs in time. |
| Trigger | Student submits valid request; no Caretaker decision occurs within the stipulated period. |
| Participants | Student; System |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-11; BW-MMS-13 to BW-MMS-15; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-029 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-029, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | System | MMS-UC-029 — Default-Reject Undecided Special Food Request | Trigger: institution-defined decision period expires with request still Requested | Rejected (Default) | BR-MMS-029; BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-12.

# BW-MMS-13 — Special Food — Approved, Awaiting Fulfillment

| Workflow ID | BW-MMS-13 |
| --- | --- |
| Workflow Name | Special Food — Approved, Awaiting Fulfillment |
| Type | Basis |
| Purpose / Scope | Valid special-food submission followed by approval, ending in the meaningful Approved state. |
| Trigger | Student submits valid request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-14; BW-MMS-15; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Approve within stipulated decision period | Approved | BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-13.

# BW-MMS-14 — Special Food — Served

| Workflow ID | BW-MMS-14 |
| --- | --- |
| Workflow Name | Special Food — Served |
| Type | Basis |
| Purpose / Scope | Valid special-food submission, approval, then post-approval transition to Served. |
| Trigger | Student submits valid request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-13; BW-MMS-15; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020, MMS-UC-021 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Approve | Approved | BR-MMS-031; BR-MMS-035 |
| 3 | Approved | Mess Caretaker | MMS-UC-021 — Update Special Food Fulfillment Status | Outcome: Served | Served | BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-14.

# BW-MMS-15 — Special Food — Cancelled

| Workflow ID | BW-MMS-15 |
| --- | --- |
| Workflow Name | Special Food — Cancelled |
| Type | Basis |
| Purpose / Scope | Valid special-food submission, approval, then post-approval transition to Cancelled. |
| Trigger | Student submits valid request. |
| Participants | Student; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | BW-MMS-13; BW-MMS-14; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020, MMS-UC-021 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Approve | Approved | BR-MMS-031; BR-MMS-035 |
| 3 | Approved | Mess Caretaker | MMS-UC-021 — Update Special Food Fulfillment Status | Outcome: Cancelled | Cancelled | BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-15.

# CW-MMS-05 — Special Food Request Lifecycle

| Workflow ID | CW-MMS-05 |
| --- | --- |
| Workflow Name | Special Food Request Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine the explicit rejection, default rejection, approval, Served, and Cancelled paths. |
| Trigger | Student submits a valid special-food request. |
| Participants | Student; Mess Caretaker; System |
| Constituent Workflows | BW-MMS-11; BW-MMS-12; BW-MMS-13; BW-MMS-14; BW-MMS-15 |
| Related Workflows | N/A |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020, MMS-UC-029, MMS-UC-021 |
| Related BRs | BR-MMS-028, BR-MMS-035, BR-MMS-029, BR-MMS-031 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Special Food Request | Student | MMS-UC-019 — Submit Special Food Request | Guard: submitted at least 1 calendar day before requested date | Special Food Request = Requested | BR-MMS-028; BR-MMS-035 |
| 2 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Reject within stipulated period | Rejected | BR-MMS-029; BR-MMS-031; BR-MMS-035 |
| 3 | Requested | System | MMS-UC-029 — Default-Reject Undecided Special Food Request | Trigger: stipulated decision period expires with no Caretaker decision | Rejected (Default) | BR-MMS-029; BR-MMS-031; BR-MMS-035 |
| 4 | Requested | Mess Caretaker | MMS-UC-020 — Review Special Food Request | Outcome: Approve within stipulated period | Approved | BR-MMS-031; BR-MMS-035 |
| 5 | Approved | Mess Caretaker | MMS-UC-021 — Update Special Food Fulfillment Status | Outcome: Served | Served | BR-MMS-031; BR-MMS-035 |
| 6 | Approved | Mess Caretaker | MMS-UC-021 — Update Special Food Fulfillment Status | Outcome: Cancelled | Cancelled | BR-MMS-031; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page CW-MMS-05.

# BW-MMS-16 — Monthly Billing — Generated to Published

| Workflow ID | BW-MMS-16 |
| --- | --- |
| Workflow Name | Monthly Billing — Generated to Published |
| Type | Basis |
| Purpose / Scope | Generate monthly bill records on the calendar-month billing event and progress them through Caretaker review/finalization to publication. |
| Trigger | Calendar-month billing cycle becomes due for bill generation. |
| Participants | System; Mess Caretaker |
| Constituent Workflows | N/A |
| Related Workflows | CW-MMS-03; CW-MMS-05 |
| Related CFRs / key AFRs |  |
| Related UCs | MMS-UC-030, MMS-UC-010 |
| Related BRs | BR-MMS-016, BR-MMS-017, BR-MMS-019, BR-MMS-030, BR-MMS-018, BR-MMS-035 |

Authoritative State-Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Monthly Bill Not Generated | System | MMS-UC-030 — Generate Monthly Mess Bills | Calendar-month billing event; required billing inputs available | Monthly Bill Generated | BR-MMS-016; BR-MMS-017; BR-MMS-019; BR-MMS-030 |
| 2 | Monthly Bill Generated | Mess Caretaker | MMS-UC-010 — Review, Finalize, and Publish Monthly Bills | Outcome: reviewed and finalized before publication | Monthly Bill Published | BR-MMS-018; BR-MMS-035 |

Corresponding editable diagram: see 05A_MMS_Workflow_Diagrams_v1.4_FINAL.drawio, page BW-MMS-16.
