# 04 MMS Business Rule Specifications v1.4 FINAL(1)

MMS Business Rule Specifications

v1.4 FINAL — synchronized to CFR/AFR and event-triggered UCs

| Version | v1.4 FINAL |
| --- | --- |
| Active BRs | 41 |
| Retired historical BR | BR-MMS-037 remains retired; “System is not a primary actor” is a modeling convention, not a business rule. |
| Rule semantics | No new domain policy introduced in this pass; only references/representation affected by DIRECT_FINAL_v2 were updated. |

# BR-MMS-001 — MMS Functional Scope Boundary

| Rule Type | Scope Boundary |
| --- | --- |
| Rule Statement | MMS shall remain limited to the mess-management functions and explicit integrations/notification triggers defined in the frozen problem statement. |
| Applies To | All MMS artifacts and screens |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall remain limited to the mess-management functions and explicit integrations/notification triggers defined in the frozen problem statement. |
| Exceptions / Exclusions | None inside MMS; external modules may own excluded functions. |
| Source / Rationale | Frozen PS overview and scope clarifications |
| Related CFRs / AFRs |  |
| Related UCs | N/A |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-002 — Employee Identity Boundary for Role Assignment

| Rule Type | Scope Boundary |
| --- | --- |
| Rule Statement | MMS may use institutional employee identity data needed for Mess Caretaker and Mess Warden assignment, but MMS shall not own employee master-data management. |
| Applies To | Role management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS may use institutional employee identity data needed for Mess Caretaker and Mess Warden assignment, but MMS shall not own employee master-data management. |
| Exceptions / Exclusions | If employee identity is unavailable, role assignment is not recorded. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-003 — Single Active Caretaker Rule

| Rule Type | Cardinality |
| --- | --- |
| Rule Statement | MMS shall enforce exactly one active Mess Caretaker at a time. |
| Applies To | Role management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall enforce exactly one active Mess Caretaker at a time. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-004 — Single Active Warden Rule

| Rule Type | Cardinality |
| --- | --- |
| Rule Statement | MMS shall enforce exactly one active Mess Warden at a time. |
| Applies To | Role management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall enforce exactly one active Mess Warden at a time. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-005 — Mess Admin Operational Data Restriction

| Rule Type | Access Control |
| --- | --- |
| Rule Statement | MMS shall prevent Mess Admin from accessing operational mess data, student requests, billing, or feedback. |
| Applies To | Role management and access |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall prevent Mess Admin from accessing operational mess data, student requests, billing, or feedback. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-006 — Immediate Mid-cycle Role Reassignment

| Rule Type | Workflow Rule |
| --- | --- |
| Rule Statement | A mid-cycle Caretaker or Warden reassignment takes effect immediately in MMS from the recorded reassignment time. |
| Applies To | Role management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | A mid-cycle Caretaker or Warden reassignment takes effect immediately in MMS from the recorded reassignment time. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-007 — Pending Request Handoff After Caretaker Reassignment

| Rule Type | Workflow Rule |
| --- | --- |
| Rule Statement | After Caretaker reassignment, MMS shall make pending operational requests visible and actionable by the newly assigned Caretaker. |
| Applies To | Role management and operational requests |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | After Caretaker reassignment, MMS shall make pending operational requests visible and actionable by the newly assigned Caretaker. |
| Exceptions / Exclusions | Applies only to requests owned by Caretaker role. |
| Source / Rationale | Frozen role-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-001 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-008 — Registration Window Creation

| Rule Type | Authorization / Trigger |
| --- | --- |
| Rule Statement | Only the active Mess Caretaker opens the registration window for a mess cycle or designated period. |
| Applies To | Registration management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | Only the active Mess Caretaker opens the registration window for a mess cycle or designated period. |
| Exceptions / Exclusions | Cycle/designated-period policy is external context. |
| Source / Rationale | Frozen registration scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-002 |
| Related WFs | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Status / Notes / TODO | Active. |

# BR-MMS-009 — Registration Submission Window Restriction

| Rule Type | Eligibility Rule |
| --- | --- |
| Rule Statement | MMS shall allow Student registration requests only while the registration window is open. |
| Applies To | Registration management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall allow Student registration requests only while the registration window is open. |
| Exceptions / Exclusions | No exception stated. |
| Source / Rationale | Frozen registration scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-003 |
| Related WFs | BW-MMS-01, BW-MMS-02, CW-MMS-01 |
| Status / Notes / TODO | Active. |

# BR-MMS-010 — Caretaker Request Decision Authority

| Rule Type | Authorization |
| --- | --- |
| Rule Statement | Only the active Mess Caretaker may approve or reject registration and deregistration requests; the Mess Warden has oversight-only access. |
| Applies To | Registration and deregistration management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | Only the active Mess Caretaker may approve or reject registration and deregistration requests; the Mess Warden has oversight-only access. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen actor ownership |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-004, MMS-UC-006 |
| Related WFs | BW-MMS-01, BW-MMS-04, CW-MMS-01, CW-MMS-02, BW-MMS-02, BW-MMS-03 |
| Status / Notes / TODO | Active. |

# BR-MMS-011 — Warden Operational Request Oversight-only Rule

| Rule Type | Access Control |
| --- | --- |
| Rule Statement | The Mess Warden may view operational student requests for oversight but may not approve, reject, register, deregister, or otherwise decide those requests. |
| Applies To | Operational student requests |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | The Mess Warden may view operational student requests for oversight but may not approve, reject, register, deregister, or otherwise decide those requests. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen actor ownership |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-007 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-012 — Deregistration Anytime Submission

| Rule Type | Availability Rule |
| --- | --- |
| Rule Statement | MMS shall allow Students to submit deregistration requests at any time. |
| Applies To | Deregistration management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall allow Students to submit deregistration requests at any time. |
| Exceptions / Exclusions | Student must be registered to submit a meaningful deregistration request. |
| Source / Rationale | Frozen deregistration scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-005 |
| Related WFs | BW-MMS-03, BW-MMS-04, CW-MMS-02 |
| Status / Notes / TODO | Active. |

# BR-MMS-013 — Deregistration Effective Date Rule

| Rule Type | Lifecycle Rule |
| --- | --- |
| Rule Statement | MMS shall make an approved deregistration effective from the next calendar day after Caretaker approval. |
| Applies To | Deregistration management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall make an approved deregistration effective from the next calendar day after Caretaker approval. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen deregistration scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-027 |
| Related WFs | BW-MMS-03, CW-MMS-02 |
| Status / Notes / TODO | Active. |

# BR-MMS-014 — Weekly Menu Structure Rule

| Rule Type | Data Structure |
| --- | --- |
| Rule Statement | MMS shall store weekly menu information day-wise and meal-wise for breakfast, lunch, and dinner. |
| Applies To | Menu management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall store weekly menu information day-wise and meal-wise for breakfast, lunch, and dinner. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen menu scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-008, MMS-UC-009 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-015 — Menu Update Notification Rule

| Rule Type | Notification Rule |
| --- | --- |
| Rule Statement | MMS shall trigger system-generated email notifications to Students when weekly menu updates are published. |
| Applies To | Menu management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall trigger system-generated email notifications to Students when weekly menu updates are published. |
| Exceptions / Exclusions | MMS triggers email events but does not own email infrastructure. |
| Source / Rationale | Frozen notification scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-008 |
| Related WFs | N/A |
| Status / Notes / TODO | Not workflow-grounded under the new convention; enforced in MMS-UC-008. |

# BR-MMS-016 — Monthly Calendar Billing Cycle

| Rule Type | Computation Rule |
| --- | --- |
| Rule Statement | MMS shall generate mess bills using the monthly calendar-month cycle. |
| Applies To | Billing management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall generate mess bills using the monthly calendar-month cycle. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen billing scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-030 |
| Related WFs | BW-MMS-16 |
| Status / Notes / TODO | Active; represented in BW-MMS-16 under DIRECT_FINAL_v2. |

# BR-MMS-017 — Bill Computation Components

| Rule Type | Computation Rule |
| --- | --- |
| Rule Statement | MMS monthly billing shall include daily-rate multiplied by number of served days, charges for approved special meals, and automatic deductions for approved rebates. |
| Applies To | Billing management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS monthly billing shall include daily-rate multiplied by number of served days, charges for approved special meals, and automatic deductions for approved rebates. |
| Exceptions / Exclusions | Rate values are external policy inputs; payment collection is outside MMS scope. |
| Source / Rationale | Frozen billing scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-030, MMS-UC-015 |
| Related WFs | BW-MMS-16, CW-MMS-05, CW-MMS-03 |
| Status / Notes / TODO | Active; represented in BW-MMS-16 under DIRECT_FINAL_v2. |

# BR-MMS-018 — Caretaker Bill Finalization Rule

| Rule Type | Authorization |
| --- | --- |
| Rule Statement | MMS shall require Caretaker review and finalization before monthly bills are published to Students. |
| Applies To | Billing management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall require Caretaker review and finalization before monthly bills are published to Students. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen billing scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-010 |
| Related WFs | BW-MMS-16 |
| Status / Notes / TODO | Active; represented in BW-MMS-16 under DIRECT_FINAL_v2. |

# BR-MMS-019 — Approved Rebate Billing Effect

| Rule Type | Computation Rule |
| --- | --- |
| Rule Statement | MMS shall apply rebate deductions to monthly bills only for approved rebate requests. |
| Applies To | Billing and rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall apply rebate deductions to monthly bills only for approved rebate requests. |
| Exceptions / Exclusions | Rejected or pending rebates do not adjust bills. |
| Source / Rationale | Frozen rebate/billing scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-015, MMS-UC-030 |
| Related WFs | BW-MMS-05, BW-MMS-06, CW-MMS-03, BW-MMS-16 |
| Status / Notes / TODO | Active. |

# BR-MMS-020 — Feedback Storage and Visibility Rule

| Rule Type | Information Rule |
| --- | --- |
| Rule Statement | MMS shall store Student text feedback and make feedback visible to Caretaker and Warden for monitoring and reporting. |
| Applies To | Feedback management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall store Student text feedback and make feedback visible to Caretaker and Warden for monitoring and reporting. |
| Exceptions / Exclusions | No complaint-resolution workflow is introduced. |
| Source / Rationale | Frozen feedback scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-012, MMS-UC-013 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-021 — Minimum Rebate Duration Rule

| Rule Type | Validation |
| --- | --- |
| Rule Statement | MMS shall reject rebate requests with a requested duration of fewer than three days. |
| Applies To | Rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall reject rebate requests with a requested duration of fewer than three days. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen rebate rules |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-014 |
| Related WFs | BW-MMS-05, BW-MMS-07, CW-MMS-03, BW-MMS-06 |
| Status / Notes / TODO | Active. |

# BR-MMS-022 — Rebate Lead-time Rule

| Rule Type | Validation |
| --- | --- |
| Rule Statement | MMS shall reject rebate requests not submitted at least one calendar day before the rebate start date. |
| Applies To | Rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall reject rebate requests not submitted at least one calendar day before the rebate start date. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen rebate rules |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-014 |
| Related WFs | BW-MMS-05, BW-MMS-07, CW-MMS-03, BW-MMS-06 |
| Status / Notes / TODO | Active. |

# BR-MMS-023 — Rebate Non-overlap Rule

| Rule Type | Validation |
| --- | --- |
| Rule Statement | MMS shall prevent overlapping rebate requests. |
| Applies To | Rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall prevent overlapping rebate requests. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen rebate rules |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-014 |
| Related WFs | BW-MMS-05, BW-MMS-07, CW-MMS-03, BW-MMS-06 |
| Status / Notes / TODO | Active. |

# BR-MMS-024 — Rebate Reason Capture Rule

| Rule Type | Data Requirement |
| --- | --- |
| Rule Statement | MMS shall require Student rebate requests to specify a reason and shall require explanation when the reason is Other. |
| Applies To | Rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall require Student rebate requests to specify a reason and shall require explanation when the reason is Other. |
| Exceptions / Exclusions | Allowed reasons are medical, institute leave, family function, and other. |
| Source / Rationale | Frozen rebate scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-014 |
| Related WFs | BW-MMS-05, BW-MMS-07, CW-MMS-03, BW-MMS-06 |
| Status / Notes / TODO | Active. |

# BR-MMS-025 — Caretaker Rebate Date Modification Rule

| Rule Type | Decision Rule |
| --- | --- |
| Rule Statement | The Caretaker may modify rebate dates before approval only where permitted by the external mess policy; approved dates become the dates used by MMS for billing adjustment. |
| Applies To | Rebate management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | The Caretaker may modify rebate dates before approval only where permitted by the external mess policy; approved dates become the dates used by MMS for billing adjustment. |
| Exceptions / Exclusions | The frozen PS does not define the permitted range or limits of date modification. |
| Source / Rationale | Frozen rebate scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-015 |
| Related WFs | BW-MMS-06, CW-MMS-03, BW-MMS-05 |
| Status / Notes / TODO | Active. |

# BR-MMS-026 — Vacation Survey Registered-student Restriction

| Rule Type | Eligibility Rule |
| --- | --- |
| Rule Statement | MMS shall send vacation food continuity surveys only to currently registered Students. |
| Applies To | Vacation food continuity management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall send vacation food continuity surveys only to currently registered Students. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen vacation survey scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-016, MMS-UC-017 |
| Related WFs | BW-MMS-08, BW-MMS-10, CW-MMS-04, BW-MMS-09 |
| Status / Notes / TODO | Active. |

# BR-MMS-027 — Vacation Survey Default No Rule

| Rule Type | Deadline Rule |
| --- | --- |
| Rule Statement | MMS shall record No as the default response for registered Students who do not respond before the response deadline. |
| Applies To | Vacation food continuity management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall record No as the default response for registered Students who do not respond before the response deadline. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen vacation survey scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-028 |
| Related WFs | BW-MMS-10, CW-MMS-04 |
| Status / Notes / TODO | Active. |

# BR-MMS-028 — Special Food Lead-time Rule

| Rule Type | Validation |
| --- | --- |
| Rule Statement | MMS shall allow special food requests only when submitted at least one calendar day before the requested date. |
| Applies To | Special food arrangement |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall allow special food requests only when submitted at least one calendar day before the requested date. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen special food scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-019 |
| Related WFs | BW-MMS-11, BW-MMS-15, CW-MMS-05, BW-MMS-12, BW-MMS-13, BW-MMS-14 |
| Status / Notes / TODO | Active. |

# BR-MMS-029 — Special Food Default Rejection Rule

| Rule Type | Deadline Rule |
| --- | --- |
| Rule Statement | MMS shall mark a special food request as Rejected if the Caretaker does not decide within the institution-defined decision period of receiving the request. |
| Applies To | Special food arrangement |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall mark a special food request as Rejected if the Caretaker does not decide within the institution-defined decision period of receiving the request. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen special food scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-029 |
| Related WFs | BW-MMS-12, CW-MMS-05 |
| Status / Notes / TODO | The source mentions 12 hours as intended but explicitly leaves the exact value institution-defined; see ISS-MMS-013. |

# BR-MMS-030 — Special Food Charge Rule

| Rule Type | Computation Rule |
| --- | --- |
| Rule Statement | Approved special-food requests are chargeable and their charges are added to the Student monthly bill. |
| Applies To | Special food and billing link |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | Approved special-food requests are chargeable and their charges are added to the Student monthly bill. |
| Exceptions / Exclusions | The frozen PS does not state whether a later Cancelled status reverses or suppresses the charge; see ISS-MMS-015. |
| Source / Rationale | Frozen special food/billing scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-020, MMS-UC-030 |
| Related WFs | BW-MMS-13, BW-MMS-15, CW-MMS-05, BW-MMS-16, BW-MMS-14 |
| Status / Notes / TODO | Active. |

# BR-MMS-031 — Special Food State-transition Rule

| Rule Type | Lifecycle Rule |
| --- | --- |
| Rule Statement | MMS shall track special food requests using Requested, Approved, Rejected, Served, and Cancelled states; Served and Cancelled shall occur only after Approved. |
| Applies To | Special food arrangement |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall track special food requests using Requested, Approved, Rejected, Served, and Cancelled states; Served and Cancelled shall occur only after Approved. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen special food state scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-019, MMS-UC-020, MMS-UC-021, MMS-UC-029 |
| Related WFs | BW-MMS-11, BW-MMS-15, CW-MMS-05, BW-MMS-12, BW-MMS-13, BW-MMS-14 |
| Status / Notes / TODO | The PS does not explicitly assign the actor who records Served/Cancelled; see ISS-MMS-014. |

# BR-MMS-032 — Announcement Publisher and Relevance Rule

| Rule Type | Authorization |
| --- | --- |
| Rule Statement | Only the active Mess Caretaker or Mess Warden may publish mess-related announcements. |
| Applies To | Announcements |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | Only the active Mess Caretaker or Mess Warden may publish mess-related announcements. |
| Exceptions / Exclusions | No automated content-relevance validation is specified by the frozen PS. |
| Source / Rationale | Frozen announcement scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-022 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-033 — Announcement History Access Rule

| Rule Type | Information Rule |
| --- | --- |
| Rule Statement | MMS shall maintain mess-relevant announcement history and allow MMS actors to view it according to access rights. |
| Applies To | Announcements |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall maintain mess-relevant announcement history and allow MMS actors to view it according to access rights. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen announcement scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-023, MMS-UC-022 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-034 — Report Role-access Rule

| Rule Type | Access Control |
| --- | --- |
| Rule Statement | MMS shall restrict supervisory reports to Warden and operational reports to Caretaker as stated in the frozen problem statement. |
| Applies To | Reports |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall restrict supervisory reports to Warden and operational reports to Caretaker as stated in the frozen problem statement. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen report scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-024, MMS-UC-025 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-035 — MMS Notification Trigger Scope

| Rule Type | Notification Rule |
| --- | --- |
| Rule Statement | MMS triggers system-generated email notifications only for the MMS events explicitly listed in the frozen problem statement; external email delivery infrastructure remains outside MMS. |
| Applies To | Notifications |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS triggers system-generated email notifications only for the MMS events explicitly listed in the frozen problem statement; external email delivery infrastructure remains outside MMS. |
| Exceptions / Exclusions | Delivery failure handling is outside MMS unless otherwise specified. |
| Source / Rationale | Frozen notification scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-003, MMS-UC-004, MMS-UC-005, MMS-UC-006, MMS-UC-008, MMS-UC-010, MMS-UC-014, MMS-UC-015, MMS-UC-016, MMS-UC-019, MMS-UC-020, MMS-UC-021, MMS-UC-022, MMS-UC-029, MMS-UC-031 |
| Related WFs | BW-MMS-01, BW-MMS-02, CW-MMS-01, BW-MMS-03, BW-MMS-04, CW-MMS-02, BW-MMS-16, BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03, BW-MMS-08, BW-MMS-09, BW-MMS-10, CW-MMS-04, BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Status / Notes / TODO | Active. |

# BR-MMS-036 — External Policy Ownership Boundary

| Rule Type | Scope Boundary |
| --- | --- |
| Rule Statement | MMS shall not define institutional mess policies such as rates, vacation periods, or employee appointment policy; it may only use explicitly provided values as inputs where the frozen problem statement states system behavior. |
| Applies To | All MMS areas |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall not define institutional mess policies such as rates, vacation periods, or employee appointment policy; it may only use explicitly provided values as inputs where the frozen problem statement states system behavior. |
| Exceptions / Exclusions | Policy definition remains outside MMS. |
| Source / Rationale | Frozen scope clarification |
| Related CFRs / AFRs |  |
| Related UCs | N/A |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-038 — Weekly Menu Visibility and Access Rule

| Rule Type | Access Rule |
| --- | --- |
| Rule Statement | Students, the Mess Caretaker, and the Mess Warden may view the weekly menu. Mess Admin menu access remains unresolved because the frozen PS contains conflicting statements. |
| Applies To | Menu management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | Students, the Mess Caretaker, and the Mess Warden may view the weekly menu. Mess Admin menu access remains unresolved because the frozen PS contains conflicting statements. |
| Exceptions / Exclusions | Mess Admin visibility requires clarification; see ISS-MMS-012. |
| Source / Rationale | Frozen menu visibility scope and Mess Admin boundary |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-009 |
| Related WFs | N/A |
| Status / Notes / TODO | Needs Clarification. |

# BR-MMS-039 — Weekly Menu Maintenance Authority Rule

| Rule Type | Permission Rule |
| --- | --- |
| Rule Statement | MMS shall permit only the Mess Caretaker to add, delete, or modify weekly mess menu items. |
| Applies To | Menu management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall permit only the Mess Caretaker to add, delete, or modify weekly mess menu items. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen Caretaker menu-management scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-008 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-040 — Student Billing Information Access Rule

| Rule Type | Information Access Rule |
| --- | --- |
| Rule Statement | MMS shall allow Students to view only actor-visible monthly mess bills and outstanding balances maintained within MMS. |
| Applies To | Billing management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall allow Students to view only actor-visible monthly mess bills and outstanding balances maintained within MMS. |
| Exceptions / Exclusions | External payment collection, accounting settlement, and payroll/accounting operations remain outside MMS. |
| Source / Rationale | Frozen billing viewing scope and external finance boundary |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-011 |
| Related WFs | N/A |
| Status / Notes / TODO | Active. |

# BR-MMS-041 — Vacation Survey Response Option Rule

| Rule Type | Validation Rule |
| --- | --- |
| Rule Statement | MMS shall restrict Student vacation food continuity responses to Yes or No. |
| Applies To | Vacation food continuity management |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall restrict Student vacation food continuity responses to Yes or No. |
| Exceptions / Exclusions | Non-response is handled separately by the default-No rule. |
| Source / Rationale | Frozen vacation response scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-017 |
| Related WFs | BW-MMS-08, BW-MMS-09, CW-MMS-04 |
| Status / Notes / TODO | Active. |

# BR-MMS-042 — Student Request Status and History Access Rule

| Rule Type | Information Access Rule |
| --- | --- |
| Rule Statement | MMS shall allow a Student to view status and history only for the Student’s own submitted MMS requests. |
| Applies To | Request status/history access |
| Condition / Trigger | Applies whenever the stated applicability/trigger is reached. |
| Required Outcome / Constraint | MMS shall allow a Student to view status and history only for the Student’s own submitted MMS requests. |
| Exceptions / Exclusions | None stated. |
| Source / Rationale | Frozen Student status/history tracking scope |
| Related CFRs / AFRs |  |
| Related UCs | MMS-UC-026, MMS-UC-003, MMS-UC-004, MMS-UC-005, MMS-UC-006, MMS-UC-027, MMS-UC-015, MMS-UC-019 |
| Related WFs | BW-MMS-01, BW-MMS-02, CW-MMS-01, BW-MMS-03, BW-MMS-04, CW-MMS-02, BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03, BW-MMS-11, BW-MMS-12, BW-MMS-13, BW-MMS-14, BW-MMS-15, CW-MMS-05 |
| Status / Notes / TODO | Active. |
