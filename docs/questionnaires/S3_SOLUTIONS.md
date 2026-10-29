# ELM Requirements Comprehension Exercise — Section S3 Solutions

**Student:** Sumit Kumar (Roll No: `24BCS245`, Batch: `B`)  
**Assigned Questionnaire Section:** **S3** (30 Questions)  
**File Updated:** [`docs/questionnaires/S3.xlsx`](file:///c:/Users/sumit/fusion-assignment/Fusion-Integrated/docs/questionnaires/S3.xlsx)

---

## Solutions & Traceability Matrix

| Q# | Question Summary | Answer | Confidence | Main Source Used | Specification Reference & Rationale |
|:---|:---|:---:|:---:|:---:|:---|
| **1** | If the institute changes COL so unused COL no longer carries forward, which rule is directly changed? | **A** | 100% | UC (v2)+BR | **BR-EL-009**: Commuted Leave credit and carry-forward rule. |
| **2** | Resumption reaches verifier but return cannot be verified. What should verifier do? | **B** | 100% | UC (v2)+BR+WF | **CW-EL-04 / UC-EL-07**: Resumption remains awaiting verification; do not proceed with closure/restoration until verified. |
| **3** | Extension goes from Ongoing directly to sanction omitting required substitute. What is missing? | **D** | 100% | UC (v2)+BR+WF | **CW-EL-03**: Substitute-response gate and subsequent Unit Head review before higher-sanction processing. |
| **4** | Replacement holiday/RH calendar edited but not published. Which obligation applies? | **A** | 100% | UC (v2)+BR | **BR-EL-031**: Continue using the currently effective published calendar until a replacement is published. |
| **5** | What must ELM do before accepting a requested leave category? | **A** | 100% | UC (v2)+BR | **BR-EL-001**: Validate that the employee is eligible for the requested category under currently effective published policy. |
| **6** | How do cancellation and extension differ in the leave lifecycle? | **D** | 100% | UC (v2)+BR+WF | **BR-EL-023 / BR-EL-025 / CW-EL-02 / CW-EL-03**: Cancellation applies to approved leave before it begins; extension applies to ongoing EL/COL/VL. |
| **7** | Higher-sanction leave actor-goal chain with no substitute and Establishment configured. | **B** | 100% | UC (v2)+BR+WF | **CW-EL-01**: Employee applies → Unit Head reviews/recommends → Establishment verifies/routes → Sanctioning Authority decides. |
| **8** | EL interval running across a closed holiday. How is the holiday treated? | **C** | 100% | UC (v2)+BR | **BR-EL-011**: Continuous-count categories (EL, COL, VL) count intervening weekends and closed holidays as leave days. |
| **9** | Required system effects after verified early resumption. | **A** | 100% | UC (v2)+BR+WF | **BR-EL-028 / CW-EL-04**: Record actual leave period, restore unused approved EL/COL/VL, synchronize records, and close leave. |
| **10** | What is employee accomplishing in Obtain Printable Leave Application? | **B** | 100% | UC (v1) | **UC-EL-04**: Produce a printable/exportable representation of the leave application. |
| **11** | How many characters may an employee enter in leave-purpose/reason field? | **E** | 100% | FR | Cannot be determined from the supplied specification (no character length constraint is specified). |
| **12** | Colleague nominee with overlapping pending leave. Eligible as substitute? | **C** | 100% | UC (v2)+BR | **BR-EL-014**: Overlapping pending or approved leave makes the nominee ineligible. |
| **13** | Higher-sanction cancellation rejected by final Sanctioning Authority. Original leave state? | **D** | 100% | UC (v2)+BR+WF | **BR-EL-023 / CW-EL-02**: It remains Approved — Unchanged. |
| **14** | Contrast staff EL credit with faculty VL in canonical case. | **C** | 100% | UC (v2)+BR | **BR-EL-005–008**: Non-faculty receive 30 EL directly; faculty receive 60 VL tied to vacation periods, with unused VL converting 2:1 to EL at year end. |
| **15** | Valid path for CL requiring substitute, substitute accepts, Unit Head rejects. | **D** | 100% | UC (v2)+BR+WF | **CW-EL-01 / BR-EL-016**: Draft → Awaiting Substitute Response → Awaiting Unit Head Review → Rejected. |
| **16** | Interaction boundary of Record Offline-Sanctioned Leave. | **B** | 100% | UC (v2)+BR | **BR-EL-029 / UC-EL-010**: Administrator records leave already validly sanctioned offline; does not obtain a second approval. |
| **17** | Exact notification channel ELM uses to inform employee of final decision. | **E** | 100% | FR | Cannot be determined from the supplied specification (specific channel like email/SMS/push/memo is unspecified). |
| **18** | Year-end leave balance treatment for unused RH. | **C** | 100% | UC (v2)+BR | **BR-EL-003**: Unused RH lapses and does not carry forward. |
| **19** | Employee wants additional time while currently on approved COL. Actor goal? | **B** | 100% | UC (v2)+BR+WF | **CW-EL-03 / UC-EL-009**: Submit Leave Extension. |
| **20** | Categories expressly excluded from continuous-day counting rule. | **C** | 100% | UC (v2)+BR | **BR-EL-010 / BR-EL-011**: CL, SCL, and RH (they exclude weekends and holidays). |
| **21** | Substitute declines twice in succession. How many additional replacement loops before auto-rejection? | **E** | 100% | UC (v2)+BR | **BR-EL-015**: Cannot be determined from the supplied specification (no fixed decline loop limit or auto-rejection is specified). |
| **22** | Institute publishes new hierarchy. Which rule ensures later routing uses it? | **C** | 95% | UC (v2)+BR | **BR-EL-030**: Validation and routing use the currently effective published policy and hierarchy parameters. |
| **23** | Extension in Extension Awaiting Final Sanction rejected. Resulting state? | **D** | 100% | UC (v2)+BR+WF | **CW-EL-03**: Ongoing Leave — Original Unchanged. |
| **24** | Higher-sanction leave without substitute, Establishment configured. Progression? | **D** | 100% | UC (v2)+BR+WF | **CW-EL-01**: Employee submission → Unit Head review → Establishment routing → final Sanctioning Authority. |
| **25** | System allows two full-day requests overlapping on same dates. Violation? | **A** | 100% | UC (v2)+BR | **BR-EL-012**: ELM must detect and prevent impermissible overlap with active pending or approved leave. |
| **26** | Exact medical certificate format mandatory when COL evidence is required. | **E** | 100% | UC (v2)+BR | **BR-EL-009**: Cannot be determined from the supplied specification (exact certificate form/template is unspecified). |
| **27** | Requirement making SLA reminder and escalation thresholds configurable. | **B** | 100% | UC (v2)+BR | **BR-EL-037 / CFR-EL-023**: Support configurable reminder and escalation thresholds for SLA-controlled tasks. |
| **28** | Apply for Leave validation fails before submission. Interaction outcome? | **B** | 100% | UC (v2)+BR | **UC-EL-001**: The request does not progress until the validation problem is corrected. |
| **29** | Fresh substitute response no longer required when substitute data changes. What is removed? | **A** | 100% | UC (v2)+BR+WF | **CW-EL-01 / UC-EL-006**: Branch from modified pending request to Awaiting Fresh Substitute Response and accept/decline transitions. |
| **30** | Approved extension changes only newly requested period rather than reposting whole leave. | **A** | 100% | UC (v2)+BR+WF | **BR-EL-025 / CW-EL-03**: Post only the incremental additional leave period when an extension is approved. |
