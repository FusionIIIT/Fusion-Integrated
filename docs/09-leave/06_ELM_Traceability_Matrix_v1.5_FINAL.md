# Sheet: Summary

| ELM Traceability Matrix — Final Synchronized v1.5 |
| Authority: final PS v1.4 + CFR/AFR RR v1.5 + UC/BR v1.4 + WF v1.5. The 107 SRS-EL items remain the immutable as-administered student baseline and are preserved through the RR/crosswalk. |
| Measure | Value |  | Convention |
| Consolidated CFRs | 32 |  | UC mapping | Actor-triggered or event-triggered use case; N/A is valid |
| Active actor-triggered UCs | 18 |  | BR mapping | Material policy/constraint; N/A is valid |
| Active event-triggered UCs | 2 |  | WF mapping | Connected state-changing progression; automatic System transitions may appear where applicable; N/A is valid |
| Retired UCs | 1 |  | Minimum satisfaction | Smallest representation set sufficient for the CFR meaning; broader traceability is listed separately |
| Active BRs | 36 |  | Student continuity | Do not rewrite SRS-EL-001…107 history; use companion crosswalk |
| Retired BR identifiers | 2 |  | Workflow authority | State-Transition Tables in Workflow Specifications v1.5 are authoritative. |
| Composite Workflows | 4 |  | Cross-cutting automatic transition | XTP-EL-01 is used only when SLA escalation changes routing/responsibility. |
| Basis Workflows | 19 |  | Formal mapping vocabulary | UC, BR, WF, UC+BR, UC+WF, BR+WF, UC+BR+WF only. |
| Coverage | Full for all 32 CFRs |

# Sheet: CFR_to_UC_BR_WF

| CFR ID | Requirement / Short Name | UC Trace | BR Trace | Workflow Trace | Minimum Satisfaction Set | Coverage | Mapping Rationale |
| CFR-EL-001 | Role-based ELM access | N/A | BR-EL-036 | N/A | BR | Full | Cross-cutting authorization rule; no standalone UC/WF required. |
| CFR-EL-002 | Create and submit leave application | EL-UC-001 | BR-EL-001, BR-EL-013, BR-EL-036 | CW-EL-01 | UC+BR | Full | UC provides actor goal; BRs provide supported-category/Station Leave/access constraints. |
| CFR-EL-003 | Validate a leave request before progression | EL-UC-001 | BR-EL-001–012, BR-EL-030–031 | CW-EL-01 | UC+BR | Full | Validation is interaction-bound and policy governed; WF is broad traceability, not needed for minimum satisfaction. |
| CFR-EL-004 | CL entitlement and treatment | EL-UC-001; EL-UC-020 | BR-EL-002, BR-EL-010 | CW-EL-01 | BR | Full | Policy is sufficient for semantic satisfaction; execution points trace broadly. |
| CFR-EL-005 | RH entitlement and treatment | EL-UC-001, EL-UC-015; EL-UC-020 | BR-EL-003, BR-EL-031 | CW-EL-01 | BR | Full | Pure policy/calendar constraint. |
| CFR-EL-006 | SCL entitlement and treatment | EL-UC-001, EL-UC-005; EL-UC-020 | BR-EL-004 | CW-EL-01 | BR | Full | Policy/authority constraint. |
| CFR-EL-007 | EL entitlement and carry-forward | EL-UC-001; EL-UC-020 | BR-EL-005 | N/A | BR | Full | Policy obligation; scheduled execution is traced separately. |
| CFR-EL-008 | Faculty VL and VL-to-EL conversion | EL-UC-001; EL-UC-020 | BR-EL-006–008 | N/A | UC+BR | Full | Faculty VL policy and event-triggered year-end execution are both required; no workflow is implied solely by the time trigger. |
| CFR-EL-009 | COL entitlement and treatment | EL-UC-001; EL-UC-020 | BR-EL-009 | N/A | BR | Full | Policy/evidence/carry-forward semantics. |
| CFR-EL-010 | Continuous-day counting | EL-UC-001, EL-UC-009 | BR-EL-011 | CW-EL-01; CW-EL-03 | BR | Full | Counting policy is sufficient. |
| CFR-EL-011 | Nominate an eligible substitute | EL-UC-001, EL-UC-019 | BR-EL-014, BR-EL-036 | CW-EL-01; CW-EL-03 | UC+BR | Full | Actor nomination plus eligibility constraints. |
| CFR-EL-012 | Obtain substitute response and enforce consent gate | EL-UC-002, EL-UC-019 | BR-EL-014–015 | CW-EL-01; CW-EL-03 | UC+BR+WF | Full | Interaction, consent policy, and decline/accept progression all material. |
| CFR-EL-013 | CL/RH Unit Head final decision | EL-UC-003 | BR-EL-016 | CW-EL-01 | UC+BR+WF | Full | Unit Head interaction, authority rule, and lifecycle branch are all needed. |
| CFR-EL-014 | Higher-sanction progression to final decision | EL-UC-003–005 | BR-EL-017–019, BR-EL-030 | CW-EL-01 | UC+BR+WF | Full | Multiple actor goals + routing policy + explicit progression. |
| CFR-EL-015 | Director self-sanction | EL-UC-005 | BR-EL-020 | CW-EL-01 | BR+WF | Full | The distinguishing requirement is the exception policy plus altered progression; EL-UC-005 is broad traceability. |
| CFR-EL-016 | Record and communicate final leave decision | EL-UC-003, EL-UC-005, EL-UC-012 | BR-EL-035–036 | CW-EL-01 | UC+WF | Full | Final-decision actor interaction and terminal progression/effects; no independent domain policy is required for the core obligation. |
| CFR-EL-017 | No post-submission modification | EL-UC-007, EL-UC-001 | BR-EL-034 | CW-EL-01 | BR | Full | Constraint prohibits the former capability and directs change via withdrawal/new application. |
| CFR-EL-018 | Immediate withdrawal of pending request | EL-UC-007 | BR-EL-022 | CW-EL-01; CW-EL-03 where a pending extension request is withdrawn | UC+WF | Full | Actor goal + immediate terminal lifecycle effect; withdrawal is cross-cutting in new-leave processing and, where applicable, in a pending extension request. |
| CFR-EL-019 | Cancel approved leave before start | EL-UC-008, EL-UC-003–005 | BR-EL-016–019, BR-EL-023–024, BR-EL-030 | CW-EL-02 | UC+BR+WF | Full | Pre-start policy, multi-actor decision, and state/account outcomes. |
| CFR-EL-020 | Extend ongoing EL/COL/VL | EL-UC-009, EL-UC-002–005, EL-UC-019 | BR-EL-011, BR-EL-014–019, BR-EL-025, BR-EL-030–031 | CW-EL-03 | UC+BR+WF | Full | Interaction, eligibility/routing policy and extension progression. |
| CFR-EL-021 | Review resumption and adjust actual leave where required | EL-UC-010–011 | BR-EL-027–028 | CW-EL-04 | UC+BR+WF | Full | Employee submission, authority review policy, and outcome-dependent progression/synchronization. |
| CFR-EL-022 | View leave balances and history | EL-UC-012 | BR-EL-036 | N/A | UC | Full | Simple information-access actor goal. |
| CFR-EL-023 | Obtain printable/exportable leave application | EL-UC-013 | BR-EL-036 | N/A | UC | Full | Simple actor capability; access rule is cross-cutting. |
| CFR-EL-024 | Maintain policy parameters and hierarchy configuration | EL-UC-014 | BR-EL-030, BR-EL-036 | N/A | UC+BR | Full | Admin interaction + current-config/no-publication policy. |
| CFR-EL-025 | Maintain and publish holiday/RH calendar | EL-UC-015 | BR-EL-003, BR-EL-031, BR-EL-036 | N/A | UC+BR | Full | Admin interaction + effective-published-calendar semantics. |
| CFR-EL-026 | Maintain authorized leave records | EL-UC-017 | BR-EL-036–037 | N/A | UC+BR | Full | Admin interaction + authorization/non-sanction boundary. |
| CFR-EL-027 | Record already-sanctioned offline leave | EL-UC-016 | BR-EL-029, BR-EL-036–037 | N/A | UC+BR | Full | Single-actor synchronization governed by record-integrity policy; no second workflow. |
| CFR-EL-028 | Execute and record year-end leave-account processing | EL-UC-020 | BR-EL-002–010 | N/A | UC+BR | Full | Event-triggered year-end execution is represented by EL-UC-020 and governed by the applicable year-end BRs; no separate workflow is required. |
| CFR-EL-029 | Configure workflow-task SLA thresholds | EL-UC-018 | BR-EL-038, BR-EL-036 | N/A | UC+BR | Full | Admin configuration actor goal + threshold policy. |
| CFR-EL-030 | Notify a user when an actionable task is assigned | Affected task-generating UCs | BR-EL-035 | CW-EL-01–04 (broad) | BR | Full | Event/notification rule is the minimum sufficient representation. |
| CFR-EL-031 | Remind on a still-pending SLA task | EL-UC-021 | BR-EL-032, BR-EL-038 | N/A | UC+BR | Full | EL-UC-021 expresses the event-triggered reminder behavior; BRs provide threshold and still-pending constraints. Reminder alone is not a workflow progression. |
| CFR-EL-032 | Escalate a still-pending SLA task | EL-UC-021 | BR-EL-033, BR-EL-038 | XTP-EL-01 within the applicable CW-EL-01–04 only when configured escalation changes task routing/responsibility; otherwise N/A | UC+BR | Full | EL-UC-021 + BR-EL-033/038 are sufficient for the generic escalation obligation. Where configuration changes routing/responsibility, the automatic System transition is represented by XTP-EL-01 within the affected composite workflow. |

# Sheet: UC_Registry

| UC ID | Name | Primary Actor | Related CFRs | Related BRs | Workflow | Status | UC Type |
| EL-UC-001 | Apply for Leave | Employee | CFR-EL-002–003, CFR-EL-011, CFR-EL-015 | BR-EL-001–015, BR-EL-020, BR-EL-030–031, BR-EL-036 | CW-EL-01 | Active | Actor-triggered |
| EL-UC-002 | Respond to Substitute Request | Substitute / Responsibility Holder | CFR-EL-012, CFR-EL-030 | BR-EL-014–015, BR-EL-035–036 | CW-EL-01; CW-EL-03 | Active | Actor-triggered |
| EL-UC-003 | Review Leave-Related Request at Unit Head | Unit Head | CFR-EL-013–016, CFR-EL-019–020 | BR-EL-016–020, BR-EL-023, BR-EL-025, BR-EL-030, BR-EL-036 | CW-EL-01; CW-EL-02; CW-EL-03 | Active | Actor-triggered |
| EL-UC-004 | Verify and Route Higher-Sanction Request | Deputy Registrar (Estt.) / Establishment Processing Role | CFR-EL-014, CFR-EL-019–020 | BR-EL-018–019, BR-EL-023, BR-EL-025, BR-EL-030, BR-EL-036 | CW-EL-01; CW-EL-02; CW-EL-03 | Active | Actor-triggered |
| EL-UC-005 | Make Final Sanctioning Decision | Sanctioning Authority (Deputy Registrar (Estt.), Dean, Registrar, Director, or other configured competent authority) | CFR-EL-006, CFR-EL-014–016, CFR-EL-019–020 | BR-EL-004, BR-EL-017–020, BR-EL-023–025, BR-EL-030, BR-EL-036 | CW-EL-01; CW-EL-02; CW-EL-03 | Active | Actor-triggered |
| EL-UC-007 | Withdraw Pending Request | Employee | CFR-EL-017–018 | BR-EL-022, BR-EL-034, BR-EL-036 | CW-EL-01; CW-EL-03 (only when the extension request itself is pending and withdrawal is applicable) | Active | Actor-triggered |
| EL-UC-008 | Request Cancellation of Approved Leave | Employee | CFR-EL-019 | BR-EL-023–024, BR-EL-030, BR-EL-036 | CW-EL-02 | Active | Actor-triggered |
| EL-UC-009 | Request Extension of Ongoing Leave | Employee | CFR-EL-020 | BR-EL-001, BR-EL-005–015, BR-EL-017–019, BR-EL-025, BR-EL-030–031, BR-EL-036 | CW-EL-03 | Active | Actor-triggered |
| EL-UC-010 | Submit Resumption of Duty | Employee | CFR-EL-021 | BR-EL-027, BR-EL-036 | CW-EL-04 | Active | Actor-triggered |
| EL-UC-011 | Review Resumption | Applicable Sanctioning Authority | CFR-EL-021 | BR-EL-027–028, BR-EL-036 | CW-EL-04 | Active | Actor-triggered |
| EL-UC-012 | View Leave Balances and History | Employee | CFR-EL-016, CFR-EL-022 | BR-EL-036 | N/A | Active | Actor-triggered |
| EL-UC-013 | Obtain Printable/Exportable Leave Application | Employee | CFR-EL-023 | BR-EL-036 | N/A | Active | Actor-triggered |
| EL-UC-014 | Maintain Policy and Hierarchy Configuration | Authorized administrative role | CFR-EL-024 | BR-EL-030, BR-EL-036 | N/A | Active | Actor-triggered |
| EL-UC-015 | Maintain and Publish Holiday/RH Calendar | Authorized administrative role | CFR-EL-005, CFR-EL-025 | BR-EL-003, BR-EL-031, BR-EL-036 | N/A | Active | Actor-triggered |
| EL-UC-016 | Record Already-Sanctioned Offline Leave | Leave Administrator | CFR-EL-027 | BR-EL-029, BR-EL-036–037 | N/A | Active | Actor-triggered |
| EL-UC-017 | Maintain Authorized Leave Records | Authorized administrative role | CFR-EL-026 | BR-EL-036–037 | N/A | Active | Actor-triggered |
| EL-UC-018 | Configure Workflow SLA Thresholds | Authorized administrative role | CFR-EL-029 | BR-EL-038, BR-EL-036 | N/A | Active | Actor-triggered |
| EL-UC-019 | Nominate Replacement Substitute After Decline | Employee | CFR-EL-011–012, CFR-EL-018 | BR-EL-014–015, BR-EL-022, BR-EL-036 | CW-EL-01; CW-EL-03 | Active | Actor-triggered |
| EL-UC-006 | Modify Pending Request | Employee | — | BR-EL-021 (retired); replacement BR-EL-034 | — | RETIRED | Retired |
| EL-UC-020 | Execute Year-End Leave Processing | N.A. — Event-triggered | CFR-EL-004–009, CFR-EL-028 | BR-EL-002–009 | N/A — isolated event-triggered year-end operation, not a connected multi-step progression. | Active | Event-triggered |
| EL-UC-021 | Process SLA Threshold Event | N.A. — Event-triggered | CFR-EL-031–032 | BR-EL-032–033, BR-EL-038 | Conditional cross-cutting trace to CW-EL-01–04 only when escalation changes routing/responsibility; otherwise N/A. | Active | Event-triggered |

# Sheet: BR_Registry

| BR ID | Rule Name | Type | Related CFRs | Related UC/Function | Related WF | Status/Note |
| BR-EL-001 | Supported leave-category eligibility | Eligibility | CFR-EL-002–003 | EL-UC-001, EL-UC-009 | CW-EL-01; CW-EL-03 | Revised to remove published-policy-version semantics. |
| BR-EL-002 | Casual Leave entitlement and lapse | Entitlement | CFR-EL-004, CFR-EL-028 | EL-UC-001; EL-UC-020 | CW-EL-01 | Active. |
| BR-EL-003 | Restricted Holiday entitlement and applicability | Entitlement / Calendar | CFR-EL-005, CFR-EL-025, CFR-EL-028 | EL-UC-001, EL-UC-015; EL-UC-020 | CW-EL-01 | Expanded/confirmed after adjudication. |
| BR-EL-004 | Special Casual Leave entitlement and admissibility | Entitlement / Authority | CFR-EL-006, CFR-EL-028 | EL-UC-001, EL-UC-005; EL-UC-020 | CW-EL-01 | Clarified: admissibility is authority judgment, not separate encoded rule. |
| BR-EL-005 | Non-faculty Earned Leave credit and carry-forward | Entitlement | CFR-EL-007, CFR-EL-028 | EL-UC-001; EL-UC-020 | CW-EL-01 | Active. |
| BR-EL-006 | Faculty Vacation Leave entitlement and vacation-period applicability | Entitlement / Calendar | CFR-EL-008 | EL-UC-001 | CW-EL-01 | Clarified external vacation-period source. |
| BR-EL-007 | VL-to-EL year-end conversion | Calculation / Year-end | CFR-EL-008, CFR-EL-028 | EL-UC-020 | N/A | Active, consolidated statement. |
| BR-EL-008 | Treatment of EL created by VL conversion | Account | CFR-EL-008, CFR-EL-028 | EL-UC-020; EL-UC-001 | N/A | Active. |
| BR-EL-009 | Commuted Leave entitlement and treatment | Entitlement / Evidence | CFR-EL-009, CFR-EL-028 | EL-UC-001; EL-UC-020 | CW-EL-01 | Consolidated. |
| BR-EL-010 | Half-day CL treatment | Calculation | CFR-EL-004 | EL-UC-001 | CW-EL-01 | Active. |
| BR-EL-011 | Continuous-day counting | Counting | CFR-EL-003, CFR-EL-010 | EL-UC-001, EL-UC-009 | CW-EL-01; CW-EL-03 | Active. |
| BR-EL-012 | Applicant non-overlap with half-day CL exception | Validation | CFR-EL-003 | EL-UC-001 | CW-EL-01 | Confirmed PS gap. |
| BR-EL-013 | Station Leave coupling | Scope / Information | CFR-EL-002 | EL-UC-001 | CW-EL-01 | Active. |
| BR-EL-014 | Substitute eligibility | Eligibility | CFR-EL-011–012 | EL-UC-001, EL-UC-002, EL-UC-009, EL-UC-019 | CW-EL-01; CW-EL-03 | Expanded to include not-the-applicant condition. |
| BR-EL-015 | Substitute consent gate and decline recovery | Routing / Eligibility | CFR-EL-012 | EL-UC-002, EL-UC-019 | CW-EL-01; CW-EL-03 | Expanded with adjudicated recovery path. |
| BR-EL-016 | Unit Head final scope for CL/RH | Authority | CFR-EL-013, CFR-EL-019 | EL-UC-003, EL-UC-008 | CW-EL-01; CW-EL-02 | Active. |
| BR-EL-017 | Unit Head recommendation for higher-sanction leave | Authority / Routing | CFR-EL-014, CFR-EL-019–020 | EL-UC-003 | CW-EL-01; CW-EL-02; CW-EL-03 | Clarified after adjudication. |
| BR-EL-018 | Higher-sanction routing | Routing | CFR-EL-014, CFR-EL-019–020 | EL-UC-003–005 | CW-EL-01; CW-EL-02; CW-EL-03 | Revised to current configuration terminology. |
| BR-EL-019 | Authority resolution and optional Establishment step | Routing / Authority | CFR-EL-014, CFR-EL-019–020 | EL-UC-003–005 | CW-EL-01; CW-EL-02; CW-EL-03 | Revised to remove effective-published-policy wording. |
| BR-EL-020 | Director self-sanction | Authority / Exception | CFR-EL-015 | EL-UC-001, EL-UC-005 | CW-EL-01 | Active. |
| BR-EL-021 | RETIRED — Modify Pending Request | Retired | — | — | — | Retired because G-09 reversed the former semantics; replacement is BR-EL-034. |
| BR-EL-022 | Immediate withdrawal of pending request | Lifecycle | CFR-EL-018 | EL-UC-007 | CW-EL-01 | Consolidated and strengthened. |
| BR-EL-023 | Cancellation of approved leave before start | Lifecycle / Routing | CFR-EL-019 | EL-UC-008, EL-UC-003–005 | CW-EL-02 | Expanded with adjudicated outcome effects. |
| BR-EL-024 | Fresh application after cancellation | Lifecycle | CFR-EL-019 | EL-UC-008, EL-UC-001 | CW-EL-02 | Active. |
| BR-EL-025 | Extension of ongoing EL/COL/VL | Lifecycle / Calculation | CFR-EL-020 | EL-UC-009, EL-UC-002–005, EL-UC-019 | CW-EL-03 | Expanded with adjudicated incremental-posting rule. |
| BR-EL-026 | RETIRED IDENTIFIER | Retired | — | — | — | Remains retired. |
| BR-EL-027 | Resumption applicability and review authority | Lifecycle / Authority | CFR-EL-021 | EL-UC-010–011 | CW-EL-04 | Revised verifier identity. |
| BR-EL-028 | Normal, early, and late resumption outcome | Lifecycle / Account | CFR-EL-021 | EL-UC-011 | CW-EL-04 | Major revision: no generic closure state; late resumption explicitly supported. |
| BR-EL-029 | Offline-sanctioned leave synchronization | Record integrity | CFR-EL-027 | EL-UC-016 | N/A | Expanded with evidence and consistency requirements. |
| BR-EL-030 | Current configured policy and hierarchy | Configuration | CFR-EL-003, CFR-EL-014, CFR-EL-024 | EL-UC-001, EL-UC-003–005, EL-UC-014 | CW-EL-01; CW-EL-02; CW-EL-03 | Materially revised from former 'Effective Policy Version' rule. |
| BR-EL-031 | Effective published holiday/RH calendar | Calendar | CFR-EL-003, CFR-EL-005, CFR-EL-025 | EL-UC-001, EL-UC-015 | CW-EL-01 | Confirmed after adjudication. |
| BR-EL-032 | SLA reminder on still-pending task | Threshold / Notification | CFR-EL-031 | EL-UC-021 | N/A | Strengthened with pending-only guard. |
| BR-EL-033 | SLA escalation on still-pending task | Threshold / Escalation | CFR-EL-032 | EL-UC-021 | Conditional: applicable CW-EL-01–04 only when configured escalation changes task routing/responsibility; otherwise N/A | Strengthened with pending-only guard. |
| BR-EL-034 | No post-submission modification | Lifecycle constraint | CFR-EL-017 | EL-UC-007, EL-UC-001 | CW-EL-01 | New replacement rule for retired BR-EL-021. |
| BR-EL-035 | Actionable task assignment notification | Notification | CFR-EL-030 | EL-UC-002–005, EL-UC-011 | CW-EL-01; CW-EL-02; CW-EL-03; CW-EL-04 | New explicit rule from adjudicated PS. |
| BR-EL-036 | Role-based authorization | Authorization | CFR-EL-001 | All actor UCs | All composite workflows | New explicit cross-cutting rule from PS. |
| BR-EL-037 | Administrative maintenance is not sanctioning | Authorization / Record integrity | CFR-EL-026–027 | EL-UC-016–017 | N/A | New explicit cross-cutting distinction. |
| BR-EL-038 | Configurable SLA thresholds | Configuration | CFR-EL-029 | EL-UC-018; EL-UC-021 | N/A | New explicit configuration rule. |

# Sheet: WF_Registry

| Workflow / Pattern ID | Name | Type | Status / Purpose | Constituent / Applies To |
| BW-EL-01 | New Leave — Substitute Consent Accepted (No Loop) | Basis | Substitute-consent prefix; accepted response routes to applicant-appropriate next approval state. | CW-EL-01 |
| BW-EL-02 | New Leave — Substitute Declined, Replacement Accepted (One Loop Traversal) | Basis | Exactly one substitute-decline recovery traversal ending in accepted replacement. | CW-EL-01 |
| BW-EL-03 | New CL/RH — Approved | Basis | Direct Unit-Head-final approval path for CL/RH without substitute gate. | CW-EL-01 |
| BW-EL-04 | New CL/RH — Rejected | Basis | Direct Unit-Head-final rejection path for CL/RH without substitute gate. | CW-EL-01 |
| BW-EL-05 | New Higher-Sanction Leave — Approved | Basis | Higher-sanction approval path with optional configured Establishment step. | CW-EL-01 |
| BW-EL-06 | New Higher-Sanction Leave — Rejected | Basis | Higher-sanction rejection path with optional configured Establishment step. | CW-EL-01 |
| BW-EL-07 | Director Self-Sanction — Approved | Basis | Director-applicant new-leave self-sanction approval after any required substitute gate. | CW-EL-01 |
| BW-EL-08 | Director Self-Sanction — Rejected | Basis | Director-applicant new-leave self-sanction rejection after any required substitute gate. | CW-EL-01 |
| BW-EL-09 | CL/RH Approved-Leave Cancellation — Approved | Basis | Unit-Head-final pre-start cancellation approval. | CW-EL-02 |
| BW-EL-10 | CL/RH Approved-Leave Cancellation — Rejected | Basis | Unit-Head-final pre-start cancellation rejection; original approval preserved. | CW-EL-02 |
| BW-EL-11 | Higher-Sanction Approved-Leave Cancellation — Approved | Basis | Higher-sanction cancellation approval through the same applicable hierarchy. | CW-EL-02 |
| BW-EL-12 | Higher-Sanction Approved-Leave Cancellation — Rejected | Basis | Higher-sanction cancellation rejection; original approval preserved. | CW-EL-02 |
| BW-EL-13 | Extension — Substitute Consent Accepted (No Loop) | Basis | Substitute-consent prefix for an admissible EL/COL/VL extension. | CW-EL-03 |
| BW-EL-14 | Extension — Substitute Declined, Replacement Accepted (One Loop Traversal) | Basis | Exactly one extension substitute-decline recovery traversal. | CW-EL-03 |
| BW-EL-15 | Ongoing Leave Extension — Approved | Basis | Higher-sanction extension approval; only incremental additional period posted. | CW-EL-03 |
| BW-EL-16 | Ongoing Leave Extension — Rejected | Basis | Higher-sanction extension rejection; original ongoing leave preserved. | CW-EL-03 |
| BW-EL-17 | Normal Resumption Review | Basis | Sanctioning Authority review; no leave-period/balance adjustment. | CW-EL-04 |
| BW-EL-18 | Early Resumption Review | Basis | Early return review; actual period/balance and records synchronized. | CW-EL-04 |
| BW-EL-19 | Late Resumption Review | Basis | Late return review; actual period/balance and records synchronized. | CW-EL-04 |
| CW-EL-01 | New Leave Processing and Pending Withdrawal | Composite | End-to-end new-leave progression including substitute recovery, CL/RH and higher-sanction decisions, Director self-sanction, and cross-cutting pending withdrawal. | BW-EL-01–08 |
| CW-EL-02 | Approved Leave Cancellation | Composite | Pre-start cancellation through the same applicable decision hierarchy, with approved/rejected effects. | BW-EL-09–12 |
| CW-EL-03 | Ongoing Leave Extension | Composite | EL/COL/VL extension with validation, substitute recovery, higher-sanction decision, and pending-extension withdrawal. | BW-EL-13–16 |
| CW-EL-04 | Resumption Review | Composite | Normal/early/late resumption review by applicable Sanctioning Authority without generic closure state. | BW-EL-17–19 |
| XTP-EL-01 | Cross-Cutting SLA Routing / Responsibility Escalation | Transition Pattern | Automatic System transition used only when configured SLA escalation changes routing/responsibility; notification-only escalation is not a WF transition. | Applicable CW-EL-01–04 |

# Sheet: Legacy_Disposition

| Previous Workflow | Disposition | Replacement | Rationale |
| WF-EL-01 Apply and Decide Leave | Reconstructed | CW-EL-01 + BW-EL-01–08 | Full Basis/Composite decomposition; substitute recovery, Director ordering, and cross-cutting withdrawal synchronized. |
| WF-EL-02 Modify or Withdraw Pending Request | Retired / redistributed | Withdrawal in CW-EL-01 and CW-EL-03; no Modify workflow | Pending in-place modification removed; withdrawal retained where semantically valid. |
| WF-EL-03 Cancel Approved Leave | Reconstructed | CW-EL-02 + BW-EL-09–12 | Unit-Head-final and higher-sanction cancellation outcomes; fresh application outside cancellation. |
| WF-EL-04 Extend Ongoing Leave | Reconstructed | CW-EL-03 + BW-EL-13–16 | Substitute recovery, hierarchy, incremental-only approval, rejection preservation, and extension withdrawal synchronized. |
| WF-EL-05 Resume Duty and Close Leave | Reconstructed | CW-EL-04 + BW-EL-17–19 | Generic closure/verifier semantics replaced by Sanctioning Authority review and normal/early/late outcomes. |
| WF-EL-06 Record Offline-Sanctioned Leave | Retired as workflow | EL-UC-016 + BR-EL-029 | Record synchronization, not a second approval progression. |
| WF-EL-07 Year-End Leave Processing | Retired as workflow | EL-UC-020 + BR-EL-002–009 | Event-triggered isolated system operation; no SF representation type. |
| WF-EL-08 SLA Reminder / Escalation | Retired as standalone workflow | EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing changes | Reminder/notification-only behavior is UC+BR; routing-changing escalation is a cross-cutting System transition only. |
