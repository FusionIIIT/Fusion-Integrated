# **Employee Leave Management (ELM)** 

#### **Business Rule Specifications — Final Synchronized v1.4** 

Fusion ERP • Employee Leave Management • Synchronized baseline v1.4 

Rule discipline 

Business Rules externalize material policy, eligibility, authorization, calculation, routing, lifecycle, and threshold constraints. They constrain actor-triggered or event-triggered Use Cases and workflow transitions; they are not workflow activities. BREL-021 and BR-EL-026 remain retired identifiers for traceability. BR-EL-030 uses current configured policy/hierarchy values; holiday/RH calendar publication semantics remain under BR-EL-031. 

## **1. Business Rule Index** 

|**BR ID**<br>BR-EL-001|**Rule Name**<br>Supported leave-<br>category eligibility|**Type**<br>Eligibility|**Status**<br>Active|**Related CFRs**<br>CFR-EL-002–003|
|---|---|---|---|---|
|BR-EL-002|Casual Leave<br>entitlement and lapse|Entitlement|Active|CFR-EL-004, CFR-<br>EL-028|
|BR-EL-003|Restricted Holiday<br>entitlement and<br>applicability|Entitlement / Calendar|Active|CFR-EL-005, CFR-<br>EL-025, CFR-EL-028|
|BR-EL-004|Special Casual Leave<br>entitlement and<br>admissibility|Entitlement / Authority|Active|CFR-EL-006, CFR-<br>EL-028|
|BR-EL-005|Non-faculty Earned<br>Leave credit and carry-<br>forward|Entitlement|Active|CFR-EL-007, CFR-<br>EL-028|
|BR-EL-006|Faculty Vacation Leave<br>entitlement and<br>vacation-period<br>applicability|Entitlement / Calendar|Active|CFR-EL-008|
|BR-EL-007|VL-to-EL year-end<br>conversion|Calculation / Year-end|Active|CFR-EL-008, CFR-<br>EL-028|
|BR-EL-008|Treatment of EL created<br>by VL conversion|Account|Active|CFR-EL-008, CFR-<br>EL-028|
|BR-EL-009|Commuted Leave<br>entitlement and<br>treatment|Entitlement / Evidence|Active|CFR-EL-009, CFR-<br>EL-028|
|BR-EL-010|Half-day CL treatment|Calculation|Active|CFR-EL-004|
|BR-EL-011|Continuous-day<br>counting|Counting|Active|CFR-EL-003, CFR-<br>EL-010|
|BR-EL-012|Applicant non-overlap<br>with half-day CL<br>exception|Validation|Active|CFR-EL-003|
|BR-EL-013|Station Leave coupling|Scope / Information|Active|CFR-EL-002|



ELM synchronized specification • Final baseline v1.4 

|**BR ID**|**Rule Name**|**Type**|**Status**|**Related CFRs**|
|---|---|---|---|---|
|BR-EL-014|Substitute eligibility|Eligibility|Active|CFR-EL-011–012|
|BR-EL-015|Substitute consent gate<br>and decline recovery|Routing / Eligibility|Active|CFR-EL-012|
|BR-EL-016|Unit Head final scope<br>for CL/RH|Authority|Active|CFR-EL-013, CFR-<br>EL-019|
|BR-EL-017|Unit Head<br>recommendation for<br>higher-sanction leave|Authority / Routing|Active|CFR-EL-014, CFR-<br>EL-019–020|
|BR-EL-018|Higher-sanction routing|Routing|Active|CFR-EL-014, CFR-<br>EL-019–020|
|BR-EL-019|Authority resolution and<br>optional Establishment<br>step|Routing / Authority|Active|CFR-EL-014, CFR-<br>EL-019–020|
|BR-EL-020|Director self-sanction|Authority / Exception|Active|CFR-EL-015|
|BR-EL-021|RETIRED — Modify<br>Pending Request|Retired|RETIRED|—|
|BR-EL-022|Immediate withdrawal<br>of pending request|Lifecycle|Active|CFR-EL-018|
|BR-EL-023|Cancellation of<br>approved leave before<br>start|Lifecycle / Routing|Active|CFR-EL-019|
|BR-EL-024|Fresh application after<br>cancellation|Lifecycle|Active|CFR-EL-019|
|BR-EL-025|Extension of ongoing<br>EL/COL/VL|Lifecycle / Calculation|Active|CFR-EL-020|
|BR-EL-026|RETIRED IDENTIFIER|Retired|RETIRED|—|
|BR-EL-027|Resumption<br>applicability and review<br>authority|Lifecycle / Authority|Active|CFR-EL-021|
|BR-EL-028|Normal, early, and late<br>resumption outcome|Lifecycle / Account|Active|CFR-EL-021|
|BR-EL-029|Offline-sanctioned<br>leave synchronization|Record integrity|Active|CFR-EL-027|
|BR-EL-030|Current configured<br>policy and hierarchy|Configuration|Active|CFR-EL-003, CFR-<br>EL-014, CFR-EL-024|
|BR-EL-031|Effective published<br>holiday/RH calendar|Calendar|Active|CFR-EL-003, CFR-<br>EL-005, CFR-EL-025|
|BR-EL-032|SLA reminder on still-<br>pending task|Threshold / Notification|Active|CFR-EL-031|
|BR-EL-033|SLA escalation on still-<br>pending task|Threshold / Escalation|Active|CFR-EL-032|
|BR-EL-034|No post-submission<br>modification|Lifecycle constraint|Active|CFR-EL-017|
|BR-EL-035|Actionable task<br>assignment notification|Notification|Active|CFR-EL-030|
|BR-EL-036<br>BR-EL-037|Role-based<br>authorization<br>Administrative|Authorization<br>Authorization / Record|Active<br>Active|CFR-EL-001<br>CFR-EL-026–027|



ELM synchronized specification • Final baseline v1.4 

|**BR ID**|**Rule Name**|**Type**|**Status**|**Related CFRs**|
|---|---|---|---|---|
||maintenance is not<br>sanctioning|integrity|||
|BR-EL-038|Configurable SLA<br>thresholds|Configuration|Active|CFR-EL-029|



## **2. Rule Specifications** 

### **BR-EL-001 — Supported leave-category eligibility** 

|**Rule Type**|Eligibility|
|---|---|
|**Rule Statement**|A new leave request shall use only CL, RH, SCL, EL, COL, or VL<br>and shall satisfy the category-applicability conditions in the<br>current configured ELM policy.|
|**Applies To**|New leave validation|
|**Condition / Trigger**|Requested category/application context|
|**Required Outcome / Constraint**|Reject/prevent progression when category applicability is not<br>satisfied.|
|**Related CFRs**|CFR-EL-002–003|
|**Related Use Cases**|EL-UC-001, EL-UC-009|
|**Related Workflow(s)**|CW-EL-01; CW-EL-03|
|**Status / Revision Note**|Revised to remove published-policy-version semantics.|



### **BR-EL-002 — Casual Leave entitlement and lapse** 

|**Rule Type**|Entitlement|
|---|---|
|**Rule Statement**|Each employee has 8 CL days per year; unused CL lapses at<br>year end and does not carry forward.|
|**Applies To**|CL validation/year-end|
|**Condition / Trigger**|CL account/request|
|**Required Outcome / Constraint**|Enforce 8-day annual entitlement and no carry-forward.|
|**Related CFRs**|CFR-EL-004, CFR-EL-028|
|**Related Use Cases**|EL-UC-001; EL-UC-020|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Active.|



### **BR-EL-003 — Restricted Holiday entitlement and applicability** 

|**Rule Type**|Entitlement / Calendar|
|---|---|
|**Rule Statement**|Each employee has 2 RH days per year; an RH request must<br>correspond to an applicable Restricted Holiday in the currently<br>effective published holiday/RH calendar; unused RH lapses at<br>year end.|
|**Applies To**|RH validation/year-end|
|**Condition / Trigger**|RH request/account|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|Enforce entitlement, calendar applicability, and lapse.|
|---|---|
|**Related CFRs**|CFR-EL-005, CFR-EL-025, CFR-EL-028|
|**Related Use Cases**|EL-UC-001, EL-UC-015; EL-UC-020|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Expanded/confirmed after adjudication.|



### **BR-EL-004 — Special Casual Leave entitlement and admissibility** 

|**Rule Type**|Entitlement / Authority|
|---|---|
|**Rule Statement**|Each employee may use up to 15 SCL days per calendar year for<br>a special purpose considered admissible by the applicable<br>Sanctioning Authority; no separate encoded admissibility<br>criterion is required; unused SCL lapses at year end.|
|**Applies To**|SCL validation/decision/year-end|
|**Condition / Trigger**|SCL request/account|
|**Required Outcome / Constraint**|Enforce annual limit; leave purpose is judged by authority; lapse<br>unused SCL.|
|**Related CFRs**|CFR-EL-006, CFR-EL-028|
|**Related Use Cases**|EL-UC-001, EL-UC-005; EL-UC-020|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Clarified: admissibility is authority judgment, not separate<br>encoded rule.|



### **BR-EL-005 — Non-faculty Earned Leave credit and carry-forward** 

|**Rule Type**|Entitlement|
|---|---|
|**Rule Statement**|Each non-faculty employee shall receive 30 EL days per year<br>and unused EL shall carry forward according to policy.|
|**Applies To**|EL account/year-end|
|**Condition / Trigger**|Non-faculty EL|
|**Required Outcome / Constraint**|Credit 30/year and preserve unused EL across year boundary.|
|**Related CFRs**|CFR-EL-007, CFR-EL-028|
|**Related Use Cases**|EL-UC-001; EL-UC-020|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Active.|



### **BR-EL-006 — Faculty Vacation Leave entitlement and vacation-period applicability** 

|**Rule Type**|Entitlement / Calendar|
|---|---|
|**Rule Statement**|Each faculty member shall have 60 VL associated with vacation<br>periods supplied by the institute Academic Calendar, and VL<br>may be availed only during an applicable vacation period.|
|**Applies To**|VL validation|
|**Condition / Trigger**|Faculty VL request|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|Enforce 60 VL and external Academic Calendar vacation-period<br>applicability.|
|---|---|
|**Related CFRs**|CFR-EL-008|
|**Related Use Cases**|EL-UC-001|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Clarified external vacation-period source.|



### **BR-EL-007 — VL-to-EL year-end conversion** 

|**Rule Type**|Calculation / Year-end|
|---|---|
|**Rule Statement**|At year end, all unused faculty VL shall convert to EL at 2 VL : 1<br>EL including fractional conversion, and VL itself shall not carry<br>forward.|
|**Applies To**|Year-end processing|
|**Condition / Trigger**|Unused faculty VL|
|**Required Outcome / Constraint**|Convert at 2:1 including fractions; leave no unused VL balance<br>as VL.|
|**Related CFRs**|CFR-EL-008, CFR-EL-028|
|**Related Use Cases**|EL-UC-020|
|**Related Workflow(s)**|N/A|
|**Status / Revision Note**|Active, consolidated statement.|



### **BR-EL-008 — Treatment of EL created by VL conversion** 

|**Rule Type**|Account|
|---|---|
|**Rule Statement**|EL created by VL conversion shall be credited to the faculty<br>member's EL balance, may carry forward, and may<br>subsequently be availed.|
|**Applies To**|Year-end/account use|
|**Condition / Trigger**|Converted EL|
|**Required Outcome / Constraint**|Credit and retain converted EL as usable EL.|
|**Related CFRs**|CFR-EL-008, CFR-EL-028|
|**Related Use Cases**|EL-UC-020; EL-UC-001|
|**Related Workflow(s)**|N/A|
|**Status / Revision Note**|Active.|



### **BR-EL-009 — Commuted Leave entitlement and treatment** 

|**Rule Type**|Entitlement / Evidence|
|---|---|
|**Rule Statement**|Eligible employees have 20 COL days/year in this baseline; COL<br>is medical/balance-controlled, supporting medical evidence<br>may be required where applicable, and unused COL carries<br>forward.|
|**Applies To**|COL validation/year-end|
|**Condition / Trigger**|COL request/account|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|Enforce annual entitlement, balance/evidence conditions, and<br>carry-forward.|
|---|---|
|**Related CFRs**|CFR-EL-009, CFR-EL-028|
|**Related Use Cases**|EL-UC-001; EL-UC-020|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Consolidated.|



### **BR-EL-010 — Half-day CL treatment** 

|**Rule Type**|Calculation|
|---|---|
|**Rule Statement**|CL shall support first-half and second-half requests; an<br>approved half day consumes 0.5 CL day.|
|**Applies To**|CL validation/accounting|
|**Condition / Trigger**|Half-day CL|
|**Required Outcome / Constraint**|Recognize halves and deduct 0.5 day when approved.|
|**Related CFRs**|CFR-EL-004|
|**Related Use Cases**|EL-UC-001|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Active.|



### **BR-EL-011 — Continuous-day counting** 

|**Rule Type**|Counting|
|---|---|
|**Rule Statement**|For EL, COL, and VL, intervening weekends and closed holidays<br>inside the continuous approved interval count as leave days;<br>this rule does not apply to CL, SCL, or RH.|
|**Applies To**|Leave-day calculation|
|**Condition / Trigger**|EL/COL/VL and excluded categories|
|**Required Outcome / Constraint**|Apply category-specific counting boundary exactly.|
|**Related CFRs**|CFR-EL-003, CFR-EL-010|
|**Related Use Cases**|EL-UC-001, EL-UC-009|
|**Related Workflow(s)**|CW-EL-01; CW-EL-03|
|**Status / Revision Note**|Active.|



### **BR-EL-012 — Applicant non-overlap with half-day CL exception** 

|**Rule Type**|Validation|
|---|---|
|**Rule Statement**|A new request shall not impermissibly overlap the employee's<br>active pending or approved leave; first-half and second-half CL<br>on the same date are non-overlapping when they occupy<br>different halves.|
|**Applies To**|New-request validation|
|**Condition / Trigger**|Employee leave intervals|
|**Required Outcome / Constraint**|Block impermissible overlap; permit different CL halves on|



ELM synchronized specification • Final baseline v1.4 

||same date.|
|---|---|
|**Related CFRs**|CFR-EL-003|
|**Related Use Cases**|EL-UC-001|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Confirmed PS gap.|



### **BR-EL-013 — Station Leave coupling** 

|**Rule Type**|Scope / Information|
|---|---|
|**Rule Statement**|Station Leave permission/details, when applicable, shall be<br>captured within the same leave application and shall not create<br>a separate leave-request process.|
|**Applies To**|Leave application|
|**Condition / Trigger**|Outside-Jabalpur context|
|**Required Outcome / Constraint**|Keep Station Leave inside associated leave application.|
|**Related CFRs**|CFR-EL-002|
|**Related Use Cases**|EL-UC-001|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Active.|



### **BR-EL-014 — Substitute eligibility** 

|**Rule Type**|Eligibility|
|---|---|
|**Rule Statement**|When responsibility coverage is required, exactly one substitute<br>is nominated; the substitute must be another employee, must<br>not be the applicant, and must have no overlapping pending or<br>approved leave during the responsibility period.|
|**Applies To**|Substitute nomination|
|**Condition / Trigger**|Nominated employee and responsibility period|
|**Required Outcome / Constraint**|Reject an ineligible nominee.|
|**Related CFRs**|CFR-EL-011–012|
|**Related Use Cases**|EL-UC-001, EL-UC-002, EL-UC-009, EL-UC-019|
|**Related Workflow(s)**|CW-EL-01; CW-EL-03|
|**Status / Revision Note**|Expanded to include not-the-applicant condition.|



### **BR-EL-015 — Substitute consent gate and decline recovery** 

|**Rule Type**|Routing / Eligibility|
|---|---|
|**Rule Statement**|Required approval routing shall not proceed until the<br>nominated substitute accepts. A decline leaves the consent<br>gate closed; the applicant may nominate another eligible<br>substitute or withdraw the pending request where applicable.|
|**Applies To**|Substitute response|
|**Condition / Trigger**|Pending request requiring responsibility coverage|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|Accept releases routing gate; decline does not.|
|---|---|
|**Related CFRs**|CFR-EL-012|
|**Related Use Cases**|EL-UC-002, EL-UC-019|
|**Related Workflow(s)**|CW-EL-01; CW-EL-03|
|**Status / Revision Note**|Expanded with adjudicated recovery path.|



### **BR-EL-016 — Unit Head final scope for CL/RH** 

|**Rule Type**|Authority|
|---|---|
|**Rule Statement**|For CL and RH, including associated Station Leave, the<br>applicant's Unit Head is the final approve/reject authority<br>except for the Director-specific self-sanction case.|
|**Applies To**|New leave / same-hierarchy cancellation|
|**Condition / Trigger**|CL/RH request|
|**Required Outcome / Constraint**|Final decision is made at Unit Head unless Director exception<br>applies.|
|**Related CFRs**|CFR-EL-013, CFR-EL-019|
|**Related Use Cases**|EL-UC-003, EL-UC-008|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02|
|**Status / Revision Note**|Active.|



**BR-EL-017 — Unit Head recommendation for higher-sanction leave** 

|**Rule Type**|Authority / Routing|
|---|---|
|**Rule Statement**|For SCL, EL, COL, and VL, the Unit Head records<br>Recommended or Not Recommended; Not Recommended is<br>not a final rejection and both outcomes continue through the<br>applicable higher-sanction path.|
|**Applies To**|Higher-sanction new leave/extension/cancellation|
|**Condition / Trigger**|Higher-sanction request|
|**Required Outcome / Constraint**|Record recommendation and continue routing.|
|**Related CFRs**|CFR-EL-014, CFR-EL-019–020|
|**Related Use Cases**|EL-UC-003|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02; CW-EL-03|
|**Status / Revision Note**|Clarified after adjudication.|



### **BR-EL-018 — Higher-sanction routing** 

|**Rule Type**|Routing|
|---|---|
|**Rule Statement**|SCL, EL, COL, and VL requests requiring higher sanction shall<br>proceed through the current configured hierarchy to the<br>resolved final Sanctioning Authority.|
|**Applies To**|Higher-sanction contexts|
|**Condition / Trigger**|Routed request|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|Route to competent final authority using current configuration.|
|---|---|
|**Related CFRs**|CFR-EL-014, CFR-EL-019–020|
|**Related Use Cases**|EL-UC-003–005|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02; CW-EL-03|
|**Status / Revision Note**|Revised to current configuration terminology.|



### **BR-EL-019 — Authority resolution and optional Establishment step** 

|**Rule Type**|Routing / Authority|
|---|---|
|**Rule Statement**|The processing/sanctioning path shall be resolved from<br>applicant, organizational unit, designation/role, leave category,<br>and current hierarchy configuration; an Establishment step and<br>the roles Deputy Registrar (Estt.), Dean, Registrar, and Director<br>occur only where configured.|
|**Applies To**|Routing resolution|
|**Condition / Trigger**|Higher-sanction request|
|**Required Outcome / Constraint**|Resolve and use only configured processing/authority steps.|
|**Related CFRs**|CFR-EL-014, CFR-EL-019–020|
|**Related Use Cases**|EL-UC-003–005|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02; CW-EL-03|
|**Status / Revision Note**|Revised to remove effective-published-policy wording.|



### **BR-EL-020 — Director self-sanction** 

|**Rule Type**|Authority / Exception|
|---|---|
|**Rule Statement**|When the Director is the applicant, the Director-specific self-<br>sanction path replaces the normal Unit Head/higher-authority<br>route.|
|**Applies To**|Director-applicant leave|
|**Condition / Trigger**|Applicant role = Director|
|**Required Outcome / Constraint**|Use Director self-sanction path.|
|**Related CFRs**|CFR-EL-015|
|**Related Use Cases**|EL-UC-001, EL-UC-005|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Active.|



### **BR-EL-021 — RETIRED — Modify Pending Request** 

|**Rule Type**|Retired|
|---|---|
|**Rule Statement**|The former rule permitting pending-request modification is<br>retired. Post-submission modification is not part of the<br>synchronized baseline.|
|**Applies To**|N/A|
|**Condition / Trigger**|N/A|



ELM synchronized specification • Final baseline v1.4 

|**Required Outcome / Constraint**|N/A|
|---|---|
|**Related CFRs**|—|
|**Related Use Cases**|—|
|**Related Workflow(s)**|—|
|**Status / Revision Note**|Retired because G-09 reversed the former semantics;<br>replacement is BR-EL-034.|



### **BR-EL-022 — Immediate withdrawal of pending request** 

|**Rule Type**|Lifecycle|
|---|---|
|**Rule Statement**|A pending request may be withdrawn at any time before final<br>approval; withdrawal is immediate, terminates remaining<br>approval processing, blocks later approve/reject actions, and<br>informs concerned roles. After final approval, withdrawal is<br>unavailable.|
|**Applies To**|Pending request lifecycle|
|**Condition / Trigger**|Pending before final approval|
|**Required Outcome / Constraint**|Apply immediate terminal withdrawal effects.|
|**Related CFRs**|CFR-EL-018|
|**Related Use Cases**|EL-UC-007|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Consolidated and strengthened.|



### **BR-EL-023 — Cancellation of approved leave before start** 

|**Rule Type**|Lifecycle / Routing|
|---|---|
|**Rule Statement**|An approved leave may be cancelled only before its start date;<br>cancellation uses the same applicable hierarchy, does not edit<br>the approved leave in place, approval marks the leave<br>Cancelled and restores/adjusts already deducted balance,<br>while rejection leaves the original approval unchanged.|
|**Applies To**|Approved-leave cancellation|
|**Condition / Trigger**|Approved and not started|
|**Required Outcome / Constraint**|Enforce pre-start boundary and context-specific final effects.|
|**Related CFRs**|CFR-EL-019|
|**Related Use Cases**|EL-UC-008, EL-UC-003–005|
|**Related Workflow(s)**|CW-EL-02|
|**Status / Revision Note**|Expanded with adjudicated outcome effects.|



### **BR-EL-024 — Fresh application after cancellation** 

|**Rule Type**|Lifecycle|
|---|---|
|**Rule Statement**|If revised leave is still required after cancellation, a fresh leave|
||application shall be submitted rather than editing the approved|
||leave in place.|
|**Applies To**|Approved-leave change|



ELM synchronized specification • Final baseline v1.4 

|**Condition / Trigger**|Successful cancellation followed by revised need|
|---|---|
|**Required Outcome / Constraint**|Require fresh application.|
|**Related CFRs**|CFR-EL-019|
|**Related Use Cases**|EL-UC-008, EL-UC-001|
|**Related Workflow(s)**|CW-EL-02|
|**Status / Revision Note**|Active.|



### **BR-EL-025 — Extension of ongoing EL/COL/VL** 

|**Rule Type**|Lifecycle / Calculation|
|---|---|
|**Rule Statement**|Extension is available only for ongoing EL/COL/VL; it uses<br>applicable eligibility, balance, substitute, calendar and<br>sanction rules; approval posts only the incremental additional<br>period while rejection preserves the original approved leave.|
|**Applies To**|Ongoing leave extension|
|**Condition / Trigger**|Ongoing EL/COL/VL|
|**Required Outcome / Constraint**|Validate/rout appropriately and apply incremental-only<br>approval effect.|
|**Related CFRs**|CFR-EL-020|
|**Related Use Cases**|EL-UC-009, EL-UC-002–005, EL-UC-019|
|**Related Workflow(s)**|CW-EL-03|
|**Status / Revision Note**|Expanded with adjudicated incremental-posting rule.|



### **BR-EL-026 — RETIRED IDENTIFIER** 

|**Rule Type**|Retired|
|---|---|
|**Rule Statement**|No active rule is assigned to this identifier.|
|**Applies To**|N/A|
|**Condition / Trigger**|N/A|
|**Required Outcome / Constraint**|N/A|
|**Related CFRs**|—|
|**Related Use Cases**|—|
|**Related Workflow(s)**|—|
|**Status / Revision Note**|Remains retired.|



### **BR-EL-027 — Resumption applicability and review authority** 

|**Rule Type**|Lifecycle / Authority|
|---|---|
|**Rule Statement**|Formal resumption review applies to EL, COL, and VL; the<br>employee submits actual resumption information and the<br>applicable Sanctioning Authority reviews it.|
|**Applies To**|Resumption|
|**Condition / Trigger**|Return from EL/COL/VL|
|**Required Outcome / Constraint**|Route submitted resumption to applicable Sanctioning|



ELM synchronized specification • Final baseline v1.4 

||Authority.|
|---|---|
|**Related CFRs**|CFR-EL-021|
|**Related Use Cases**|EL-UC-010–011|
|**Related Workflow(s)**|CW-EL-04|
|**Status / Revision Note**|Revised verifier identity.|



### **BR-EL-028 — Normal, early, and late resumption outcome** 

|**Rule Type**|Lifecycle / Account|
|---|---|
|**Rule Statement**|If actual resumption equals the approved end date, review<br>causes no adjustment to approved leave period or balance. If<br>actual resumption is earlier or later, after review ELM records<br>the actual leave period, adjusts leave balance accordingly, and<br>synchronizes relevant leave/attendance records.|
|**Applies To**|Resumption review|
|**Condition / Trigger**|Compare actual vs approved end date|
|**Required Outcome / Constraint**|Apply no-adjustment or adjusted synchronization branch.|
|**Related CFRs**|CFR-EL-021|
|**Related Use Cases**|EL-UC-011|
|**Related Workflow(s)**|CW-EL-04|
|**Status / Revision Note**|Major revision: no generic closure state; late resumption<br>explicitly supported.|



### **BR-EL-029 — Offline-sanctioned leave synchronization** 

|**Rule Type**|Record integrity|
|---|---|
|**Rule Statement**|Only leave already sanctioned through an authorized<br>offline/paper process may be retrospectively recorded;<br>sanction/reference evidence shall be captured, record<br>consistency validated, relevant balance/history synchronized,<br>and no second approval workflow initiated.|
|**Applies To**|Offline leave entry|
|**Condition / Trigger**|Already-sanctioned leave + acceptable ELM-unavailable<br>context|
|**Required Outcome / Constraint**|Synchronize records without new sanction.|
|**Related CFRs**|CFR-EL-027|
|**Related Use Cases**|EL-UC-016|
|**Related Workflow(s)**|N/A|
|**Status / Revision Note**|Expanded with evidence and consistency requirements.|



### **BR-EL-030 — Current configured policy and hierarchy** 

|**Rule Type**|Configuration|
|---|---|
|**Rule Statement**|ELM validation and routing shall use the current configured<br>i|
||leave-policy parameters and hierarchy configuration. No<br>f|
||draft/publish/effective-version lifecycle applies to leave-policy|



ELM synchronized specification • Final baseline v1.4 

||parameters in this baseline.|
|---|---|
|**Applies To**|Validation/routing/admin config|
|**Condition / Trigger**|Current configured values|
|**Required Outcome / Constraint**|Use current configuration directly; do not depend on policy<br>publication state.|
|**Related CFRs**|CFR-EL-003, CFR-EL-014, CFR-EL-024|
|**Related Use Cases**|EL-UC-001, EL-UC-003–005, EL-UC-014|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02; CW-EL-03|
|**Status / Revision Note**|Materially revised from former 'Effective Policy Version' rule.|



### **BR-EL-031 — Effective published holiday/RH calendar** 

|**Rule Type**|Calendar|
|---|---|
|**Rule Statement**|Date and RH validation shall use the currently effective<br>published holiday/RH calendar until a replacement calendar is<br>published.|
|**Applies To**|Date/RH validation|
|**Condition / Trigger**|Published calendar state|
|**Required Outcome / Constraint**|Use current published calendar; activate replacement only<br>when published.|
|**Related CFRs**|CFR-EL-003, CFR-EL-005, CFR-EL-025|
|**Related Use Cases**|EL-UC-001, EL-UC-015|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|Confirmed after adjudication.|



**BR-EL-032 — SLA reminder on still-pending task** 

|**Rule Type**|Threshold / Notification|
|---|---|
|**Rule Statement**|When an SLA-controlled actionable task reaches its configured<br>reminder threshold, issue a reminder to the responsible user<br>and log it only if the task is still pending; otherwise issue no<br>reminder.|
|**Applies To**|EL-UC-021 / SLA reminder-threshold processing|
|**Condition / Trigger**|Task at reminder threshold|
|**Required Outcome / Constraint**|Pending -> remind+log; non-pending -> no reminder.|
|**Related CFRs**|CFR-EL-031|
|**Related Use Cases**|EL-UC-021|
|**Related Workflow(s)**|N/A — reminder alone does not create a workflow transition.|
|**Status / Revision Note**|Strengthened with pending-only guard.|



### **BR-EL-033 — SLA escalation on still-pending task** 

|**Rule Type**|Threshold / Escalation|
|---|---|
|**Rule Statement**|When an SLA-controlled actionable task remains pending past|



ELM synchronized specification • Final baseline v1.4 

||its configured escalation threshold, the system shall perform<br>the configured escalation action: notify the configured<br>higher/responsible authority and, where the escalation<br>configuration changes routing/responsibility, apply that<br>routing/responsibility change; the escalation action shall be<br>logged. If the task is no longer pending, no escalation shall be<br>issued.|
|---|---|
|**Applies To**|EL-UC-021 / SLA escalation-threshold processing|
|**Condition / Trigger**|Task past escalation threshold|
|**Required Outcome / Constraint**|Pending -> configured notify/escalate action + log; non-pending<br>-> no escalation.|
|**Related CFRs**|CFR-EL-032|
|**Related Use Cases**|EL-UC-021|
|**Related Workflow(s)**|Conditional cross-cutting trace to the applicable CW-EL-01–04<br>only when escalation changes routing/responsibility;<br>notification-only escalation = N/A.|
|**Status / Revision Note**|Pending-only guard retained; notification-only and<br>routing/responsibility-changing escalation are distinguished<br>formally.|



### **BR-EL-034 — No post-submission modification** 

|**Rule Type**|Lifecycle constraint|
|---|---|
|**Rule Statement**|A submitted pending leave request shall not be modified in<br>place. If change is needed before final approval, the employee<br>may withdraw and submit a new application if needed.|
|**Applies To**|Pending request|
|**Condition / Trigger**|Submitted and pending|
|**Required Outcome / Constraint**|Block in-place modification; preserve withdrawal/new-<br>application route.|
|**Related CFRs**|CFR-EL-017|
|**Related Use Cases**|EL-UC-007, EL-UC-001|
|**Related Workflow(s)**|CW-EL-01|
|**Status / Revision Note**|New replacement rule for retired BR-EL-021.|



### **BR-EL-035 — Actionable task assignment notification** 

|**Rule Type**|Notification|
|---|---|
|**Rule Statement**|When an actionable workflow task is assigned to a user, ELM<br>shall notify the assigned user.|
|**Applies To**|Task assignment|
|**Condition / Trigger**|New actionable assignment|
|**Required Outcome / Constraint**|Generate assignment notification.|
|**Related CFRs**|CFR-EL-030|
|**Related Use Cases**|EL-UC-002–005, EL-UC-011; EL-UC-021|
|**Related Workflow(s)**|CW-EL-01; CW-EL-02; CW-EL-03; CW-EL-04|



ELM synchronized specification • Final baseline v1.4 

New explicit rule from adjudicated PS. 

**Status / Revision Note** 

### **BR-EL-036 — Role-based authorization** 

|**Rule Type**|Authorization|
|---|---|
|**Rule Statement**|ELM capabilities shall be available only to users authorized for<br>the corresponding employee, processing, sanctioning, or<br>administrative role.|
|**Applies To**|All protected ELM actions|
|**Condition / Trigger**|Attempted protected action|
|**Required Outcome / Constraint**|Permit only role-authorized action.|
|**Related CFRs**|CFR-EL-001|
|**Related Use Cases**|All actor UCs|
|**Related Workflow(s)**|All composite workflows|
|**Status / Revision Note**|New explicit cross-cutting rule from PS.|



### **BR-EL-037 — Administrative maintenance is not sanctioning** 

|**Rule Type**|Authorization / Record integrity|
|---|---|
|**Rule Statement**|Authorized leave-record maintenance/correction shall not itself<br>create a new sanctioning decision; retrospective offline entry is<br>also synchronization rather than a second approval.|
|**Applies To**|Administrative record maintenance|
|**Condition / Trigger**|Admin maintenance action|
|**Required Outcome / Constraint**|Preserve separation between record maintenance and<br>sanctioning.|
|**Related CFRs**|CFR-EL-026–027|
|**Related Use Cases**|EL-UC-016–017|
|**Related Workflow(s)**|N/A|
|**Status / Revision Note**|New explicit cross-cutting distinction.|



### **BR-EL-038 — Configurable SLA thresholds** 

|**Rule Type**|Configuration|
|---|---|
|**Rule Statement**|Reminder and escalation thresholds for SLA-controlled<br>actionable workflow tasks shall be configurable by an<br>authorized administrative role and shall govern EL-UC-021<br>event-triggered SLA processing.|
|**Applies To**|SLA configuration|
|**Condition / Trigger**|Authorized threshold change|
|**Required Outcome / Constraint**|Store valid thresholds and use them in EL-UC-021.|
|**Related CFRs**|CFR-EL-029|
|**Related Use Cases**|EL-UC-018; EL-UC-021|
|**Related Workflow(s)**|N/A|



ELM synchronized specification • Final baseline v1.4 

New explicit configuration rule. 

**Status / Revision Note** 

ELM synchronized specification • Final baseline v1.4 

