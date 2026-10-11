# Employee Leave Management (ELM) 

### **Workflow Specifications — Final Synchronized v1.6** 

Corrected Basis-Workflow completeness • 17 complete Basis Workflows • 4 Composite Workflows • authoritative STTs 

## **1. Revision Scope and Authority** 

Version 1.6 corrects a Basis-Workflow derivation defect in v1.5: reusable substitute-consent/recovery prefixes were incorrectly counted as Basis Workflows, leaving some complete valid UC sequences (for example EL-UC-001 → EL-UC-002 → EL-UC-003 for substitute-required CL/RH) without a corresponding Basis Workflow. No PS, CFR/AFR, UC, or BR semantics are changed. 

The Composite Workflows remain semantically unchanged. Their constituent Basis-Workflow references are updated to the corrected complete-path set. The State-Transition Table (STT) remains authoritative and each diagram is a corresponding visual view. 

## **2. Workflow Derivation Decisions** 

1. Derive workflows only from validated state-changing UCs and applicable BRs. 

2. A Basis Workflow shall be a complete finite valid progression from a meaningful process start/context to a meaningful business outcome; a reusable prefix, suffix, or recovery fragment is not by itself a Basis Workflow unless it independently constitutes such a progression. 

3. A sequence such as Apply → Substitute Response → Unit Head Review must therefore appear as a complete Basis Workflow when it is a valid business path. 

4. When terminal outcomes differ only in the outcome of the same final decision UC and all preceding steps are identical, they may be represented as alternative terminal rows in one Basis Workflow to avoid duplicate path specifications. 

5. A purely configuration-controlled optional/bypass step (for example the Establishment routing step) may remain within the same Basis Workflow when it does not create a different business outcome. 

6. For a meaningful loop, represent zero traversal and exactly one traversal; do not enumerate further equivalent repetitions. 

7. Composite Workflows integrate complete Basis Workflows and may additionally represent cross-cutting transitions such as pending withdrawal and routing-changing SLA escalation. 

8. ELM is not its own UC actor. System may appear in an STT only as the performer of a meaningful automatic transition; time/external events remain triggers/guards. 

9. Pending requests are not modified in place. Change before final approval is handled through withdrawal and, if needed, a fresh application. 

10. Year-end processing and reminder/notification-only SLA handling remain event-triggered UC+BR behavior, not standalone workflows. 

11. The STT is authoritative; diagrams must correspond to it exactly. 

## **3. Workflow Registry** 

|**Workflow ID**|**Workflow Name**|**Type**|**Purpose / Scope**|**Constituent / Related Workflows**|**Primary Related UCs**|
|---|---|---|---|---|---|
|BW-EL-01|New CL/RH — No Substitute Gate|Basis|CL/RH: no substitute → Unit Head decision|CW-EL-01|EL-UC-001, EL-UC-003|
|BW-EL-02|New CL/RH — Substitute Accepted (No<br>Loop)|Basis|CL/RH: substitute accept → Unit Head<br>decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-003|
|BW-EL-03|New CL/RH — Substitute Declined,<br>Replacement Accepted (One Loop<br>Traversal)|Basis|CL/RH: one decline/replacement loop →<br>Unit Head decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-019, EL-<br>UC-003|



|BW-EL-04|New Higher-Sanction Leave — No<br>Substitute Gate|Basis|Higher-sanction: no substitute → final<br>decision|CW-EL-01|EL-UC-001, EL-UC-003, EL-UC-004, EL-<br>UC-005|
|---|---|---|---|---|---|
|BW-EL-05|New Higher-Sanction Leave — Substitute<br>Accepted (No Loop)|Basis|Higher-sanction: substitute accept → final<br>decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-003, EL-<br>UC-004, EL-UC-005|
|BW-EL-06|New Higher-Sanction Leave — Substitute<br>Declined, Replacement Accepted (One<br>Loop Traversal)|Basis|Higher-sanction: one decline/replacement<br>loop → final decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-019, EL-<br>UC-003, EL-UC-004, EL-UC-005|
|BW-EL-07|Director Self-Sanction — No Substitute<br>Gate|Basis|Director: no substitute → self-sanction<br>decision|CW-EL-01|EL-UC-001, EL-UC-005|
|BW-EL-08|Director Self-Sanction — Substitute<br>Accepted (No Loop)|Basis|Director: substitute accept → self-sanction<br>decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-005|
|BW-EL-09|Director Self-Sanction — Substitute<br>Declined, Replacement Accepted (One<br>Loop Traversal)|Basis|Director: one decline/replacement loop →<br>self-sanction decision|CW-EL-01|EL-UC-001, EL-UC-002, EL-UC-019, EL-<br>UC-005|
|BW-EL-10|CL/RH Approved-Leave Cancellation|Basis|CL/RH cancellation → Unit Head decision|CW-EL-02|EL-UC-008, EL-UC-003|
|BW-EL-11|Higher-Sanction Approved-Leave<br>Cancellation|Basis|Higher-sanction cancellation → final<br>decision|CW-EL-02|EL-UC-008, EL-UC-003, EL-UC-004, EL-<br>UC-005|
|BW-EL-12|Ongoing Leave Extension — No Substitute<br>Gate|Basis|Extension: no substitute → final decision|CW-EL-03|EL-UC-009, EL-UC-003, EL-UC-004, EL-<br>UC-005|
|BW-EL-13|Ongoing Leave Extension — Substitute<br>Accepted (No Loop)|Basis|Extension: substitute accept → final decision|CW-EL-03|EL-UC-009, EL-UC-002, EL-UC-003, EL-<br>UC-004, EL-UC-005|
|BW-EL-14|Ongoing Leave Extension — Substitute<br>Declined, Replacement Accepted (One<br>Loop Traversal)|Basis|Extension: one decline/replacement loop →<br>final decision|CW-EL-03|EL-UC-009, EL-UC-002, EL-UC-019, EL-<br>UC-003, EL-UC-004, EL-UC-005|
|BW-EL-15|Normal Resumption Review|Basis|Normal resumption → review|CW-EL-04|EL-UC-010, EL-UC-011|
|BW-EL-16|Early Resumption Review|Basis|Early resumption → review and synchronize|CW-EL-04|EL-UC-010, EL-UC-011|
|BW-EL-17|Late Resumption Review|Basis|Late resumption → review and synchronize|CW-EL-04|EL-UC-010, EL-UC-011|
|CW-EL-01|New Leave Processing and Pending<br>Withdrawal|Composite|Integrated new-leave progression + pending<br>withdrawal|BW-EL-01–09|EL-UC-001–005, EL-UC-007, EL-UC-019|
|CW-EL-02|Approved Leave Cancellation|Composite|Integrated approved-leave cancellation|BW-EL-10–11|EL-UC-008, EL-UC-003–005|
|CW-EL-03|Ongoing Leave Extension|Composite|Integrated ongoing-leave extension +<br>withdrawal|BW-EL-12–14|EL-UC-009, EL-UC-002–005, EL-UC-007, EL-<br>UC-019|
|CW-EL-04|Resumption Review|Composite|Integrated normal/early/late resumption<br>review|BW-EL-15–17|EL-UC-010, EL-UC-011|



## **4. Basis Workflow Specifications** 

All Basis Workflows below are complete finite valid paths; no prefix/recovery fragment is counted as a Basis Workflow. 

#### **BW-EL-01 — New CL/RH — No Substitute Gate** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid CL/RH application that does not require substitute consent from submission through the Unit<br>Head final decision.|
|**Trigger**|Employee submits a valid CL/RH request for which substitute coverage is not required.|
|**Participants**|Employee; Unit Head|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-013, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-003|
|**Related BRs**|BR-EL-001–013, BR-EL-016, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; no substitute<br>required; applicant is not Director|Awaiting Unit Head Review|BR-EL-001–013, BR-EL-030–031|
|2|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Approve|Approved|BR-EL-016|
|3|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Reject|Rejected|BR-EL-016|



###### **_Specification Notes_** 

- The two terminal outcomes share the same complete UC sequence; they are retained as alternative terminal rows rather than duplicated as separate Basis Workflows. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Unit Head<br>EL-UC-003<br>Employee CL/RH; outcome = Approve Approved<br>EL-UC-001<br>Draft / Not Submitted. |Submission valid; no substitute required; applicant is not Director Awaiting Unit Head Review (ytHead,<br>CLIRH; outcome = Reject<br>Rejected<br><!-- End of picture text -->

#### **BW-EL-02 — New CL/RH — Substitute Accepted (No Loop)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid CL/RH application requiring substitute coverage through accepted<br>substitute consent and the Unit Head final decision.|
|**Trigger**|Employee submits a valid CL/RH request for which substitute coverage is required.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–013, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-003|
|**Related BRs**|BR-EL-001–016, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not<br>Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute<br>Response|BR-EL-001–015, BR-<br>EL-030–031|
|2|Awaiting Substitute<br>Response|Substitute /<br>Responsibility|EL-UC-002 / Respond to<br>Substitute Request|Outcome = Accept; applicant<br>is not Director|Awaiting Unit Head<br>Review|BR-EL-014–015|
|3|Awaiting Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-<br>Related Request at Unit Head|CL/RH; outcome = Approve|Approved|BR-EL-016|
|4|Awaiting Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-<br>Related Request at Unit Head|CL/RH; outcome = Reject|Rejected|BR-EL-016|



###### **_Specification Notes_** 

- This is the previously missing complete Basis path EL-UC-001 → EL-UC-002 → EL-UC-003 for CL/RH. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Unit Head<br>Employee CURH; EL-UC-003outcome = Approve Approved<br>EL-UC-002<br>EL-UC-001 ‘Substitute / Responsibility Holder<br>Draft / Not Submitted Sthriiesion Waki sbees required ‘Awaiting Substitute Response Outcome = Accept; applicantis not Director Awaiting Unit Head Review nkttead<br>CURH; outcome = Reject<br><!-- End of picture text -->

#### **BW-EL-03 — New CL/RH — Substitute Declined, Replacement Accepted (One Loop Traversal)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid CL/RH application through one substitute-decline recovery traversal, replacement acceptance,<br>and the Unit Head final decision.|
|**Trigger**|Employee submits a valid CL/RH request requiring substitute coverage; the first nominee declines.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–013, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-019, EL-UC-003|
|**Related BRs**|BR-EL-001–016, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Applicant Action Required|BR-EL-014–015|
|3|Applicant Action Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Substitute Response|BR-EL-014–015|
|4|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>not Director|Awaiting Unit Head Review|BR-EL-014–015|
|5|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Approve|Approved|BR-EL-016|
|6|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Reject|Rejected|BR-EL-016|



**_Specification Notes_** 

- Exactly one decline → replacement → accept traversal is shown, per the loop rule. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
‘Substitute / Responsibiity Holder<br>EL-UC-002<br>Outcome = Decline<br>Applicant Action Required<br>Employee<br>Draft / Not Submitted Submission valid; substtute requred Awaiting Substitute Response Eipile replacement nominated<br>Unit Head<br>ete ogy eatin<br>sine eee EL-UC-003<br>Outcome = Accept; applicant is not Director<br>Awaiting Unit Head Review Unit Head<br>EL-UC-003<br>CURH; outcome = Reject<br>Rejected<br><!-- End of picture text -->

#### **BW-EL-04 — New Higher-Sanction Leave — No Substitute Gate** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid SCL/EL/COL/VL application not requiring substitute consent from submission through Unit Head<br>recommendation and final sanction.|
|**Trigger**|Employee submits a valid higher-sanction leave request for which substitute coverage is not required.|
|**Participants**|Employee; Unit Head; Establishment where configured; final Sanctioning Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-014, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001–013, BR-EL-017–019, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; no substitute<br>required; applicant is not Director|Awaiting Unit Head Review|BR-EL-001–013, BR-EL-030–031|
|2|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended;<br>Establishment configured|Awaiting Establishment Routing|BR-EL-017–019, BR-EL-030|
|3|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended; no<br>Establishment step|Awaiting Final Sanction Decision|BR-EL-017–019, BR-EL-030|
|4|Awaiting Establishment Routing|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Awaiting Final Sanction Decision|BR-EL-018–019, BR-EL-030|
|5|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-004, BR-EL-017–019|
|6|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-004, BR-EL-017–019|



###### **_Specification Notes_** 

- The Establishment step is configuration-controlled; its bypass does not create a distinct business outcome and therefore remains within the same Basis Workflow. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
aus, __, [oon tte tr) a a<br>- foot CT — sowie<br>a sapere<br>VC esre weaaitg )—oseame—Reet<br>Rect<br><!-- End of picture text -->

#### **BW-EL-05 — New Higher-Sanction Leave — Substitute Accepted (No Loop)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid SCL/EL/COL/VL application requiring substitute coverage through accepted consent, Unit Head<br>recommendation, and final sanction.|
|**Trigger**|Employee submits a valid higher-sanction leave request for which substitute coverage is required.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head; Establishment where configured; final Sanctioning<br>Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–012, CFR-EL-014, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001–019, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>not Director|Awaiting Unit Head Review|BR-EL-014–015|
|3|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended;<br>Establishment configured|Awaiting Establishment Routing|BR-EL-017–019, BR-EL-030|
|4|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended; no<br>Establishment step|Awaiting Final Sanction Decision|BR-EL-017–019, BR-EL-030|
|5|Awaiting Establishment Routing|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Awaiting Final Sanction Decision|BR-EL-018–019, BR-EL-030|
|6|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-004, BR-EL-017–019|
|7|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-004, BR-EL-017–019|



##### **Workflow Diagram** 



<!-- Start of picture text -->
june Head J Awaiting EstablishmentRout |<br>(onsitea fai ORM ty Yaa Renen[itera Renmei oats | mingFinew) =a<br>— — a)<br><!-- End of picture text -->

#### **BW-EL-06 — New Higher-Sanction Leave — Substitute Declined, Replacement Accepted (One Loop Traversal)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid SCL/EL/COL/VL application through one substitute-decline recovery traversal, Unit Head<br>recommendation, and final sanction.|
|**Trigger**|Employee submits a valid higher-sanction leave request requiring substitute coverage; the first nominee<br>declines.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head; Establishment where configured; final Sanctioning<br>Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–012, CFR-EL-014, CFR-EL-016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-019, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001–019, BR-EL-030–031|



**Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Applicant Action Required|BR-EL-014–015|
|3|Applicant Action Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Substitute Response|BR-EL-014–015|
|4|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>not Director|Awaiting Unit Head Review|BR-EL-014–015|
|5|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended;<br>Establishment configured|Awaiting Establishment Routing|BR-EL-017–019, BR-EL-030|
|6|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended; no<br>Establishment step|Awaiting Final Sanction Decision|BR-EL-017–019, BR-EL-030|
|7|Awaiting Establishment Routing|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Awaiting Final Sanction Decision|BR-EL-018–019, BR-EL-030|
|8|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-004, BR-EL-017–019|
|9<br>**_i_**|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-004, BR-EL-017–019|
|**_Specification Notes_**|||||||



- Exactly one decline → replacement → accept traversal is shown, per the loop rule. 



<!-- Start of picture text -->
somepatoe<br>_ ta re)<br>—_ _Senneroromesaie aae ‘nang tense ag ‘eee anes<br>conn eee sa san emma tnt sgt Jaa ae<br>———_Qucome = Accept. appear8 ot Decor ‘atingUntHead Review | nn— — san teem sucattestmentstoning— ‘wating Frat Sarcion Decsin )al _ Se2omphunortyei<br>ef tes<br><!-- End of picture text -->

**Workflow Diagram** 

#### **BW-EL-07 — Director Self-Sanction — No Substitute Gate** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid Director-applicant new leave request not requiring substitute consent from submission through<br>the Director self-sanction decision.|
|**Trigger**|Director, acting as employee applicant, submits a valid request for which substitute coverage is not required.|
|**Participants**|Director as Employee; Director as Sanctioning Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-015–016|
|**Related UCs**|EL-UC-001, EL-UC-005|
|**Related BRs**|BR-EL-001–013, BR-EL-020, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee (Director as applicant)|EL-UC-001 / Apply for Leave|Submission valid; no substitute<br>required; applicant is Director|Awaiting Director Self-Sanction|BR-EL-001–013, BR-EL-020, BR-<br>EL-030–031|
|2|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-020|
|3|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-020|



##### **Workflow Diagram** 



<!-- Start of picture text -->
Director (Sanctioning Authority role)<br>EL-UC-005<br>Outcome = Approve Approved<br>Employee (Director as applicant)<br>EL-UC-001<br>Draft / Not Submitted Subrission veld, no subetnute required: appicent ls Director Awaiting Director Self-Sanction Director (Sanctioning Authority role)<br>EL-UC-005<br>Outcome = Reject<br>Rejected<br><!-- End of picture text -->

#### **BW-EL-08 — Director Self-Sanction — Substitute Accepted (No Loop)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid Director-applicant new leave request requiring substitute coverage through accepted consent<br>and the Director self-sanction decision.|
|**Trigger**|Director, acting as employee applicant, submits a valid request requiring substitute coverage.|
|**Participants**|Director as Employee; Substitute / Responsibility Holder; Director as Sanctioning Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–012, CFR-EL-015–016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-005|
|**Related BRs**|BR-EL-001–015, BR-EL-020, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>Director|Awaiting Director Self-Sanction|BR-EL-014–015, BR-EL-020|
|3|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-020|
|4|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-020|



##### **Workflow Diagram** 



<!-- Start of picture text -->
Director (Sanctioning Authorty role)<br>EL-UC-005<br>EL-UC-001Employee ‘Substitute /EL-UC-002Responsibility Holder (Outcome = Approve Approved<br>Draft / Not Submitted Submission vakd; substtute required ‘Awaiting Substitute Response Outcome = Accept, appicants Drector Awaiting Director Self-Sanction Director (Sanctioning Authority role)<br>EL-UC-005<br>Outcome = Reject<br>Rejected<br><!-- End of picture text -->

#### **BW-EL-09 — Director Self-Sanction — Substitute Declined, Replacement Accepted (One Loop Traversal)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process a valid Director-applicant new leave request through one substitute-decline recovery traversal and the<br>Director self-sanction decision.|
|**Trigger**|Director, acting as employee applicant, submits a valid request requiring substitute coverage; the first nominee<br>declines.|
|**Participants**|Director as Employee; Substitute / Responsibility Holder; Director as Sanctioning Authority|
|**Related Workflows**|CW-EL-01|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–012, CFR-EL-015–016|
|**Related UCs**|EL-UC-001, EL-UC-002, EL-UC-019, EL-UC-005|
|**Related BRs**|BR-EL-001–015, BR-EL-020, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Applicant Action Required|BR-EL-014–015|
|3|Applicant Action Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Substitute Response|BR-EL-014–015|
|4|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>Director|Awaiting Director Self-Sanction|BR-EL-014–015, BR-EL-020|
|5|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-020|
|6|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-020|



**_Specification Notes_** 

- Exactly one decline → replacement → accept traversal is shown, per the loop rule. 

**Workflow Diagram** 



<!-- Start of picture text -->
‘Substtute / Responsibilty Holder<br>EL-UC-002,<br>Outcome = Decline.<br>Applicant Action Required<br>Employee<br>ee evucars<br>Draft / Not Submitted | Submission vakd, substtute requted _5.! awaiting Substitute Response Eigble replacement nominated Director (Sanctioning Authority role)<br>Substitute / Responsbilty Holder EL-UC-005<br>Outcome = Accept;EL-UC-002applicant is Director ‘Outcome =Approve Approved<br>‘Awaiting Director Self-Sanction | Director (SanctioningEL-UC-005 Authorty role)<br>Outcome = Reject<br>Rejected<br><!-- End of picture text -->

#### **BW-EL-10 — CL/RH Approved-Leave Cancellation** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process cancellation of an approved CL/RH before its start from employee request through the Unit Head final<br>cancellation decision.|
|**Trigger**|Employee requests cancellation of approved CL/RH before its start.|
|**Participants**|Employee; Unit Head|
|**Related Workflows**|CW-EL-02|
|**Related CFRs**|CFR-EL-019|
|**Related UCs**|EL-UC-008, EL-UC-003|
|**Related BRs**|BR-EL-016, BR-EL-023–024|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Approved / Not Started|Employee|EL-UC-008 / Request Cancellation<br>of Approved Leave|Cancellation eligible|Cancellation Pending — Unit Head<br>Review|BR-EL-023|
|2|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Original leave Unit-Head-final;<br>outcome = Approve cancellation|Cancelled; deducted balance<br>restored/adjusted|BR-EL-016, BR-EL-023–024|
|3|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Original leave Unit-Head-final;<br>outcome = Reject cancellation|Approved / Unchanged|BR-EL-016, BR-EL-023|



##### **Workflow Diagram** 



<!-- Start of picture text -->
Unit Head<br>Employee Original leave Unit-Head-final,EL-UC-003outcome = Approve cancellation Cancelled, deducted balance restored/adjusted<br>EL-UC-008<br>Approved / Not Started | Cancellation elible_.| Cancellation Pending — Unit Head Review unmuees<br>EL-UC-003<br>(Original leave Unit-Head: tna, outcome = Reject cancellation<br>Approved / Unchanged<br><!-- End of picture text -->

#### **BW-EL-11 — Higher-Sanction Approved-Leave Cancellation** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process cancellation of an approved higher-sanction leave before its start through the applicable<br>recommendation/routing hierarchy and final cancellation decision.|
|**Trigger**|Employee requests cancellation of approved SCL/EL/COL/VL before its start.|
|**Participants**|Employee; Unit Head; Establishment where configured; final Sanctioning Authority|
|**Related Workflows**|CW-EL-02|
|**Related CFRs**|CFR-EL-019|
|**Related UCs**|EL-UC-008, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-017–019, BR-EL-023–024, BR-EL-030|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Approved / Not Started|Employee|EL-UC-008 / Request Cancellation<br>of Approved Leave|Cancellation eligible|Cancellation Pending — Unit Head<br>Review|BR-EL-023|
|2|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction cancellation;<br>recommendation recorded;<br>Establishment configured|Cancellation Pending —<br>Establishment|BR-EL-017–019, BR-EL-023, BR-<br>EL-030|
|3|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction cancellation;<br>recommendation recorded; no<br>Establishment step|Cancellation Pending — Final<br>Decision|BR-EL-017–019, BR-EL-023, BR-<br>EL-030|
|4|Cancellation Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Cancellation Pending — Final<br>Decision|BR-EL-018–019, BR-EL-023, BR-<br>EL-030|
|5|Cancellation Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve cancellation|Cancelled; deducted balance<br>restored/adjusted|BR-EL-023–024|
|6|Cancellation Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject cancellation|Approved / Unchanged|BR-EL-023|



##### **Workflow Diagram** 



<!-- Start of picture text -->
oe =)<br>. So ste cane es hoe raged PX. " J eae Seonghaorty >)<br>a ees ome comer ener) ae ou ERAT (comes snes renentane<br>( ‘} es(<aa st ncn tnsrates tanning netimM ( Perf——__._.non grap —<br>of aerovea Unchanged<br><!-- End of picture text -->

#### **BW-EL-12 — Ongoing Leave Extension — No Substitute Gate** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process an admissible EL/COL/VL extension not requiring substitute consent from submission through Unit<br>Head recommendation and final sanction.|
|**Trigger**|Employee on ongoing EL/COL/VL requests additional leave time; substitute coverage is not required.|
|**Participants**|Employee; Unit Head; Establishment where configured; final Sanctioning Authority|
|**Related Workflows**|CW-EL-03|
|**Related CFRs**|CFR-EL-020|
|**Related UCs**|EL-UC-009, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001, BR-EL-005–013, BR-EL-017–019, BR-EL-025, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Ongoing EL/COL/VL|Employee|EL-UC-009 / Request Extension of<br>Ongoing Leave|Valid extension; no substitute<br>required|Awaiting Extension Unit Head<br>Review|BR-EL-001, BR-EL-005–013, BR-<br>EL-025, BR-EL-030–031|
|2|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded;<br>Establishment configured|Extension Pending —<br>Establishment|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|3|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded; no<br>Establishment step|Extension Pending — Final<br>Decision|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|4|Extension Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Extension Pending — Final<br>Decision|BR-EL-018–019, BR-EL-025, BR-<br>EL-030|
|5|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Extended Leave in Effect —<br>Incremental Period Posted|BR-EL-025|
|6|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Original Ongoing Leave<br>Unchanged|BR-EL-025|



##### **Workflow Diagram** 



<!-- Start of picture text -->
ayn >)<br>> ‘comentoesaoe ‘tension Perang—Estabestmere) ) nisaber ETRE (rman neha rn Pa<br>‘Ongong EuCOUM,_|"ates — owsreas reaes_5(ayanng> Extension Unt Head Review E_ saconmanston eSvs cannaep —, Exiension Pending — Fina Decisionoo | SenaenraAsherty ~)<br>Ate fee (<br>—— — — arse<br>of origna ongoing Leave Unchanged<br>X oe<br><!-- End of picture text -->

#### **BW-EL-13 — Ongoing Leave Extension — Substitute Accepted (No Loop)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process an admissible EL/COL/VL extension requiring substitute coverage through accepted consent, Unit Head<br>recommendation, and final sanction.|
|**Trigger**|Employee on ongoing EL/COL/VL requests additional leave time; substitute coverage is required.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head; Establishment where configured; final Sanctioning<br>Authority|
|**Related Workflows**|CW-EL-03|
|**Related CFRs**|CFR-EL-011–012, CFR-EL-020|
|**Related UCs**|EL-UC-009, EL-UC-002, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001, BR-EL-005–019, BR-EL-025, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Ongoing EL/COL/VL|Employee|EL-UC-009 / Request Extension of<br>Ongoing Leave|Valid extension; substitute<br>required|Awaiting Extension Substitute<br>Response|BR-EL-001, BR-EL-005–015, BR-<br>EL-025, BR-EL-030–031|
|2|Awaiting Extension Substitute<br>Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept|Awaiting Extension Unit Head<br>Review|BR-EL-014–015, BR-EL-025|
|3|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded;<br>Establishment configured|Extension Pending —<br>Establishment|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|4|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded; no<br>Establishment step|Extension Pending — Final<br>Decision|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|5|Extension Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Extension Pending — Final<br>Decision|BR-EL-018–019, BR-EL-025, BR-<br>EL-030|
|6|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Extended Leave in Effect —<br>Incremental Period Posted|BR-EL-025|
|7|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Original Ongoing Leave<br>Unchanged|BR-EL-025|



##### **Workflow Diagram** 



<!-- Start of picture text -->
a OO OO — -+( curt rea ane tr<br><!-- End of picture text -->

#### **BW-EL-14 — Ongoing Leave Extension — Substitute Declined, Replacement Accepted (One Loop Traversal)** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Process an admissible EL/COL/VL extension through one substitute-decline recovery traversal, Unit Head<br>recommendation, and final sanction.|
|**Trigger**|Employee on ongoing EL/COL/VL requests additional leave time requiring substitute coverage; the first nominee<br>declines.|
|**Participants**|Employee; Substitute / Responsibility Holder; Unit Head; Establishment where configured; final Sanctioning<br>Authority|
|**Related Workflows**|CW-EL-03|
|**Related CFRs**|CFR-EL-011–012, CFR-EL-020|
|**Related UCs**|EL-UC-009, EL-UC-002, EL-UC-019, EL-UC-003, EL-UC-004, EL-UC-005|
|**Related BRs**|BR-EL-001, BR-EL-005–019, BR-EL-025, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Ongoing EL/COL/VL|Employee|EL-UC-009 / Request Extension of<br>Ongoing Leave|Valid extension; substitute<br>required|Awaiting Extension Substitute<br>Response|BR-EL-001, BR-EL-005–015, BR-<br>EL-025, BR-EL-030–031|
|2|Awaiting Extension Substitute<br>Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Extension Applicant Action<br>Required|BR-EL-014–015, BR-EL-025|
|3|Extension Applicant Action<br>Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Extension Substitute<br>Response|BR-EL-014–015|
|4|Awaiting Extension Substitute<br>Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept|Awaiting Extension Unit Head<br>Review|BR-EL-014–015, BR-EL-025|
|5|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded;<br>Establishment configured|Extension Pending —<br>Establishment|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|6|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded; no<br>Establishment step|Extension Pending — Final<br>Decision|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|7|Extension Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Extension Pending — Final<br>Decision|BR-EL-018–019, BR-EL-025, BR-<br>EL-030|
|8|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Extended Leave in Effect —<br>Incremental Period Posted|BR-EL-025|
|9<br>**_i_**|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Original Ongoing Leave<br>Unchanged|BR-EL-025|
|**_Specification Notes_**|||||||



- Exactly one decline → replacement → accept traversal is shown, per the loop rule. 



<!-- Start of picture text -->
_. SE (aman)<br>a en _— a<br>a ee<br>ee |CORE]<br><!-- End of picture text -->

**Workflow Diagram** 

#### **BW-EL-15 — Normal Resumption Review** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Record employee resumption and review a normal return from EL/COL/VL without changing the approved period<br>or balance.|
|**Trigger**|Employee returns on the approved end date and submits actual resumption information.|
|**Participants**|Employee; applicable Sanctioning Authority|
|**Related Workflows**|CW-EL-04|
|**Related CFRs**|CFR-EL-021|
|**Related UCs**|EL-UC-010, EL-UC-011|
|**Related BRs**|BR-EL-027–028|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Returned from EL/COL/VL|Employee|EL-UC-010 / Submit Resumption<br>of Duty|Actual resumption details<br>submitted|Resumption Review Pending|BR-EL-027|
|2|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date = approved end date|Resumption Reviewed — No<br>Adjustment|BR-EL-027–028|



**_Specification Notes_** 

- No generic Closed leave state is introduced. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Employee Applicable Sanctioning Authority<br>EL-UC-010 EL-UC-O11<br>Returned from EL/COL/VL Actual resumption details submitted Resumption Review Pending Actual date = approved end date Resumption Reviewed — No Adjustment<br><!-- End of picture text -->

#### **BW-EL-16 — Early Resumption Review** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Record employee resumption and review an early return from EL/COL/VL, then synchronize the actual period,<br>balance, leave record, and attendance.|
|**Trigger**|Employee returns before the approved end date and submits actual resumption information.|
|**Participants**|Employee; applicable Sanctioning Authority|
|**Related Workflows**|CW-EL-04|
|**Related CFRs**|CFR-EL-021|
|**Related UCs**|EL-UC-010, EL-UC-011|
|**Related BRs**|BR-EL-027–028|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Returned from EL/COL/VL|Employee|EL-UC-010 / Submit Resumption<br>of Duty|Actual resumption details<br>submitted|Resumption Review Pending|BR-EL-027|
|2|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date < approved end date|Resumption Reviewed — Early<br>Return Synchronized|BR-EL-028|



**_Specification Notes_** 

- No generic Closed leave state is introduced. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Employee Applicable Sanctioning Authority<br>EL-UC-010 EL-UC-011<br>Returned from EUCOL/VL_ | Actual resumption details submitted Resumption Review Pending Actual date < approved end date. Resumption Reviewed — Early Return Synchronized<br><!-- End of picture text -->

#### **BW-EL-17 — Late Resumption Review** 

|**Type**|Basis|
|---|---|
|**Purpose / Scope**|Record employee resumption and review a late return from EL/COL/VL, then synchronize the actual period,<br>balance, leave record, and attendance.|
|**Trigger**|Employee returns after the approved end date and submits actual resumption information.|
|**Participants**|Employee; applicable Sanctioning Authority|
|**Related Workflows**|CW-EL-04|
|**Related CFRs**|CFR-EL-021|
|**Related UCs**|EL-UC-010, EL-UC-011|
|**Related BRs**|BR-EL-027–028|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Returned from EL/COL/VL|Employee|EL-UC-010 / Submit Resumption<br>of Duty|Actual resumption details<br>submitted|Resumption Review Pending|BR-EL-027|
|2|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date > approved end date|Resumption Reviewed — Late<br>Return Synchronized|BR-EL-028|



**_Specification Notes_** 

- No generic Closed leave state is introduced. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Employee Applicable Sanctioning Authority<br>EL-UC-010 EL-UC-011<br>Retumed from EL/COLU/VL Actual resumption details submitted Resumption Review Pending Actual date > approved end date Resumption Reviewed — Late Return Synchronized<br><!-- End of picture text -->

## **5. Composite Workflow Specifications** 

#### **CW-EL-01 — New Leave Processing and Pending Withdrawal** 

|**Type**|Composite|
|---|---|
|**Purpose / Scope**|Provide the end-to-end progression for a new leave request, including substitute consent/recovery, Unit-Head-<br>final CL/RH decisions, higher-sanction routing, the Director-specific self-sanction route, and immediate<br>withdrawal from every valid pending pre-final state.|
|**Trigger**|Employee submits a valid new leave request.|
|**Participants**|Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final<br>Sanctioning Authority; Director in self-sanction case|
|**Constituent Workflows**|BW-EL-01–09|
|**Related Workflows**|CW-EL-02; CW-EL-03; CW-EL-04|
|**Related CFRs**|CFR-EL-002–003, CFR-EL-011–018|
|**Related UCs**|EL-UC-001–005, EL-UC-007, EL-UC-019|
|**Related BRs**|BR-EL-001–020, BR-EL-022, BR-EL-030–035|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; substitute<br>required|Awaiting Substitute Response|BR-EL-001–015, BR-EL-030–031|
|2|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; no substitute<br>required; applicant is Director|Awaiting Director Self-Sanction|BR-EL-001–013, BR-EL-020, BR-<br>EL-030–031|
|3|Draft / Not Submitted|Employee|EL-UC-001 / Apply for Leave|Submission valid; no substitute<br>required; applicant is not Director|Awaiting Unit Head Review|BR-EL-001–013, BR-EL-030–031|
|4|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>Director|Awaiting Director Self-Sanction|BR-EL-014–015, BR-EL-020|
|5|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept; applicant is<br>not Director|Awaiting Unit Head Review|BR-EL-014–015|
|6|Awaiting Substitute Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Applicant Action Required|BR-EL-014–015|
|7|Applicant Action Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Substitute Response|BR-EL-014–015|
|8|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Approve|Approved|BR-EL-016|
|9|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|CL/RH; outcome = Reject|Rejected|BR-EL-016|
|10|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended;<br>Establishment configured|Awaiting Establishment Routing|BR-EL-017–019, BR-EL-030|
|11|Awaiting Unit Head Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction; Recommended<br>or Not Recommended; no<br>Establishment step|Awaiting Final Sanction Decision|BR-EL-017–019, BR-EL-030|



|12|Awaiting Establishment Routing|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Awaiting Final Sanction Decision|BR-EL-018–019, BR-EL-030|
|---|---|---|---|---|---|---|
|13|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-004, BR-EL-017–019|
|14|Awaiting Final Sanction Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-004, BR-EL-017–019|
|15|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Approved|BR-EL-020|
|16|Awaiting Director Self-Sanction|Director (Sanctioning Authority<br>role)|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Rejected|BR-EL-020|
|17|Awaiting Substitute Response;<br>Applicant Action Required;<br>Awaiting Unit Head Review;<br>Awaiting Establishment Routing;<br>Awaiting Final Sanction Decision;<br>Awaiting Director Self-Sanction|Employee|EL-UC-007 / Withdraw Pending<br>Request|Withdrawal succeeds before final<br>approval|Withdrawn|BR-EL-022, BR-EL-034|



###### **_Specification Notes_** 

- Pending in-place modification is not supported. Change before final approval is handled by withdrawal and, if needed, a fresh application. 

- Pending withdrawal is cross-cutting across every valid pending pre-final state. 

- Conditional routing/responsibility-changing SLA escalation uses XTP-EL-01 where applicable. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
ee<br>‘Awaiting Director Selt-Sanction ELUC D0 |<br>/<br>iher-sancton; no Establishment v a)|<br>cs<br><!-- End of picture text -->

#### **CW-EL-02 — Approved Leave Cancellation** 

|**Type**|Composite|
|---|---|
|**Purpose / Scope**|Represent cancellation of approved leave before its start through the same applicable decision hierarchy, with<br>distinct cancellation-approved and cancellation-rejected effects. A later revised leave request is a fresh New<br>Leave instance, not part of this workflow.|
|**Trigger**|Employee requests cancellation of an approved leave before its start date.|
|**Participants**|Employee; Unit Head; Establishment where configured; final Sanctioning Authority|
|**Constituent Workflows**|BW-EL-10–11|
|**Related Workflows**|CW-EL-01; CW-EL-03; CW-EL-04|
|**Related CFRs**|CFR-EL-019|
|**Related UCs**|EL-UC-008, EL-UC-003–005|
|**Related BRs**|BR-EL-016–019, BR-EL-023–024, BR-EL-030|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Approved / Not Started|Employee|EL-UC-008 / Request Cancellation<br>of Approved Leave|Cancellation eligible|Cancellation Pending — Unit Head<br>Review|BR-EL-023|
|2|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Original leave Unit-Head-final;<br>outcome = Approve cancellation|Cancelled; deducted balance<br>restored/adjusted|BR-EL-016, BR-EL-023|
|3|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Original leave Unit-Head-final;<br>outcome = Reject cancellation|Approved / Unchanged|BR-EL-016, BR-EL-023|
|4|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction cancellation;<br>recommendation recorded;<br>Establishment configured|Cancellation Pending —<br>Establishment|BR-EL-017–019, BR-EL-023, BR-<br>EL-030|
|5|Cancellation Pending — Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Higher-sanction cancellation;<br>recommendation recorded; no<br>Establishment step|Cancellation Pending — Final<br>Decision|BR-EL-017–019, BR-EL-023, BR-<br>EL-030|
|6|Cancellation Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Cancellation Pending — Final<br>Decision|BR-EL-018–019, BR-EL-023, BR-<br>EL-030|
|7|Cancellation Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve cancellation|Cancelled; deducted balance<br>restored/adjusted|BR-EL-023|
|8|Cancellation Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject cancellation|Approved / Unchanged|BR-EL-023|



**_Specification Notes_** 

- A successful cancellation marks the leave Cancelled and restores/adjusts deducted balance; it does not edit the approved leave in place. 

- A revised leave request after cancellation is a fresh instance of CW-EL-01. 

**Workflow Diagram** 



<!-- Start of picture text -->
‘Approved / Not Started<br>Employee<br>EL-UC-008<br>igble cancelation<br>Cancellation Pending — Unit Head Review<br>Unit Head<br>Ligher sanction;ELUC-003Establishment configured<br>Unit Head<br>igher-sanction,EL-UC-003no Establishment Cancellation Pending — Establishment<br>Unit Head Stablishment Unit Head<br>LRH approveELUC-003cancellation routeELUC-004resolved CCURH ELUC-003reject cancellation<br>Cancellation Pending — Final Decision<br>fanetioning Authority \\ Sanctioning Authority<br>ELUC-005. EL-UC-O05<br>Approve cancelation \\ Reject cancellation<br>Cancelled Approved / Unchanged<br><!-- End of picture text -->

**CW-EL-03 — Ongoing Leave Extension** 

|**Type**|Composite|
|---|---|
|**Purpose / Scope**|Represent an extension of ongoing EL/COL/VL through applicable validation, substitute consent/recovery where<br>required, Unit Head recommendation, configured higher-sanction decision, and immediate withdrawal of the<br>pending extension request where applicable.|
|**Trigger**|Employee on ongoing EL/COL/VL requests additional leave time.|
|**Participants**|Employee; Substitute / Responsibility Holder where required; Unit Head; Establishment where configured; final<br>Sanctioning Authority|
|**Constituent Workflows**|BW-EL-12–14|
|**Related Workflows**|CW-EL-01; CW-EL-02; CW-EL-04|
|**Related CFRs**|CFR-EL-020, CFR-EL-018 where pending-extension withdrawal applies|
|**Related UCs**|EL-UC-009, EL-UC-002–005, EL-UC-007, EL-UC-019|
|**Related BRs**|BR-EL-001, BR-EL-005–019, BR-EL-022, BR-EL-025, BR-EL-030–031|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Ongoing EL/COL/VL|Employee|EL-UC-009 / Request Extension of<br>Ongoing Leave|Valid extension; substitute<br>required|Awaiting Extension Substitute<br>Response|BR-EL-001, BR-EL-005–015, BR-<br>EL-025, BR-EL-030–031|
|2|Ongoing EL/COL/VL|Employee|EL-UC-009 / Request Extension of<br>Ongoing Leave|Valid extension; no substitute<br>required|Awaiting Extension Unit Head<br>Review|BR-EL-001, BR-EL-005–013, BR-<br>EL-025, BR-EL-030–031|
|3|Awaiting Extension Substitute<br>Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Accept|Awaiting Extension Unit Head<br>Review|BR-EL-014–015, BR-EL-025|
|4|Awaiting Extension Substitute<br>Response|Substitute / Responsibility Holder|EL-UC-002 / Respond to Substitute<br>Request|Outcome = Decline|Extension Applicant Action<br>Required|BR-EL-014–015, BR-EL-025|
|5|Extension Applicant Action<br>Required|Employee|EL-UC-019 / Nominate<br>Replacement Substitute After<br>Decline|Eligible replacement nominated|Awaiting Extension Substitute<br>Response|BR-EL-014–015|
|6|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded;<br>Establishment configured|Extension Pending —<br>Establishment|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|7|Awaiting Extension Unit Head<br>Review|Unit Head|EL-UC-003 / Review Leave-Related<br>Request at Unit Head|Recommendation recorded; no<br>Establishment step|Extension Pending — Final<br>Decision|BR-EL-017–019, BR-EL-025, BR-<br>EL-030|
|8|Extension Pending —<br>Establishment|Establishment|EL-UC-004 / Verify and Route<br>Higher-Sanction Request|Routing context valid|Extension Pending — Final<br>Decision|BR-EL-018–019, BR-EL-025, BR-<br>EL-030|
|9|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Approve|Extended Leave in Effect —<br>Incremental Period Posted|BR-EL-025|
|10|Extension Pending — Final<br>Decision|Sanctioning Authority|EL-UC-005 / Make Final<br>Sanctioning Decision|Outcome = Reject|Original Ongoing Leave<br>Unchanged|BR-EL-025|
|11|Awaiting Extension Substitute<br>Response; Extension Applicant<br>Action Required; Awaiting<br>Extension Unit Head Review;<br>Extension Pending —<br>Establishment; Extension Pending<br>— Final Decision|Employee|EL-UC-007 / Withdraw Pending<br>Request|Withdrawal succeeds while<br>extension request remains<br>pending|Extension Request Withdrawn —<br>Original Leave Unchanged|BR-EL-022|



**_Specification Notes_** 

- Extension approval posts only the incremental additional period; rejection preserves the original approved leave. 

- Pending extension withdrawal is cross-cutting across all valid pending extension states. 

##### **Workflow Diagram** 



<!-- Start of picture text -->
Ongoing EUCOLVL ‘Any eligible pending extension state<br>ali: peers)Sti eed thearerepring exes<br>Emoyee<br>‘Awaiting Extension Substitute Response ioetcbee Extension Request Withdrawn<br>Sirmnteue a peice)Emooyee ewesubstase<br>Decine / retcenent roma ‘econ<br>Extension Applicant Acton Required ‘Awaiting Extension Unit Head Review<br>ne Head<br>evueon<br>ecommentaion. Estabhnert cored<br>Hoe<br>Extension Pending — Establishment seconmansitonecuconro Establahnet<br>sate<br>eLveoo<br>Extension Peni — Final Decision<br>SetgnngEitan Autorly > SarctonngetueonAuthority<br>-Aeprove; ert peed Reet<br>Extended Leave in Effect Original Ongoing Leave Unchanged<br><!-- End of picture text -->

#### **CW-EL-04 — Resumption Review** 

|**Type**|Composite|
|---|---|
|**Purpose / Scope**|Coordinate employee submission of actual resumption information with review by the applicable Sanctioning<br>Authority, distinguishing normal, early, and late return without inventing a generic leave-closure state.|
|**Trigger**|Employee returns from EL/COL/VL and submits actual resumption information.|
|**Participants**|Employee; applicable Sanctioning Authority|
|**Constituent Workflows**|BW-EL-15–17|
|**Related Workflows**|CW-EL-02; CW-EL-03|
|**Related CFRs**|CFR-EL-021|
|**Related UCs**|EL-UC-010, EL-UC-011|
|**Related BRs**|BR-EL-027–028|



##### **Authoritative State-Transition Table** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Returned from EL/COL/VL|Employee|EL-UC-010 / Submit Resumption<br>of Duty|Actual resumption details<br>submitted|Resumption Review Pending|BR-EL-027|
|2|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date = approved end date|Resumption Reviewed — No<br>Adjustment|BR-EL-027–028|
|3|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date < approved end date|Resumption Reviewed — Early<br>Return Synchronized|BR-EL-028|
|4|Resumption Review Pending|Applicable Sanctioning Authority|EL-UC-011 / Review Resumption|Actual date > approved end date|Resumption Reviewed — Late<br>Return Synchronized|BR-EL-028|



**_Specification Notes_** 

- No generic Closed leave state is introduced. 

- Normal, early, and late return are distinguished by review outcome and synchronization effect. 

**Workflow Diagram** 



<!-- Start of picture text -->
Returned from EL/COL/VL<br>Employee<br>EL-UC-010<br>submit actual retum<br>Resumption Review Pending<br>janctioning Authority Sanctioning Authority Sanctioning Authority<br>EL-UC-011 EL-UC-011 EL-UC-011<br>normal; no adjustment learly; restore + sync late; adjust + sync<br>Resumption Reviewed — No Adjustment Resumption Reviewed — Early Return Synchronized Resumption Reviewed — Late Return Synchronized<br><!-- End of picture text -->

## **6. Cross-Cutting Automatic SLA Routing / Responsibility Escalation Pattern** 

|**Pattern ID**|XTP-EL-01|
|---|---|
|**Applies To**|Any SLA-controlled actionable task state in CW-EL-01–04 where the configured escalation changes<br>routing/responsibility.|
|**Trigger**|Configured escalation threshold reached.|
|**Performer**|System (workflow transition performer; not a UC actor).|
|**Related UC**|EL-UC-021 / Process SLA Threshold Event|
|**Related BRs**|BR-EL-033, BR-EL-038|



##### **Authoritative State-Transition Pattern** 

|**S. No.**|**From State**|**Actor**|**Use Case ID / Name**|**Guard / Outcome**|**Resulting State**|**BR Reference(s)**|
|---|---|---|---|---|---|---|
|1|Any SLA-controlled actionable<br>task state that remains pending|System|EL-UC-021 / Process SLA<br>Threshold Event|Escalation threshold reached;<br>task still pending; configured<br>action changes<br>routing/responsibility|Same business process state;<br>actionable task<br>responsibility/routing updated<br>to configured higher/responsible<br>authority|i<br>BR-EL-033, BR-EL-038|



##### **Transition Diagram** 



<!-- Start of picture text -->
System<br>EL-UC-021<br>Any SLA-Controlled Pending Actionable State escalation threshold; stil pending; routing/responsibilty changes Same Pending Business State — Escalated Responsibility<br><!-- End of picture text -->

## **7. Functions Intentionally Outside the Workflow Registry** 

|**Artifact**|**Reason outside Workflow Registry**|**Retained Representation**|
|---|---|---|
|EL-UC-006|Retired. Pending in-place modification is not part of the synchronized baseline.|Retired identifier + BR-EL-034 no-modification rule|
|EL-UC-012 / EL-UC-013|Informational inquiry/export capabilities; no connected persistent business-<br>state progression.|Use Cases|
|EL-UC-014 / EL-UC-015 / EL-UC-017 / EL-UC-018|Administrative configuration/maintenance interactions; isolated actor-goal<br>functions rather than connected process progression.|Use Cases + applicable BRs|
|EL-UC-016|Retrospective synchronization of already-sanctioned offline leave; explicitly<br>not a second approval progression.|Use Case + BR-EL-029|
|EL-UC-020|Event-triggered year-end leave-account processing; an isolated timed<br>operation applying year-end BRs, not by itself a connected workflow<br>progression.|Event-triggered Use Case + BR-EL-002–009|
|EL-UC-021 reminder / notification-only escalation|Event-triggered threshold behavior that does not change process<br>routing/responsibility.|Event-triggered Use Case + BR-EL-032/033/038|
|BR-EL-035 task-assignment notification|Notification effect attached to actionable task assignment; not a standalone<br>workflow.|Business Rule / UC effect|



## **Appendix A — Legacy Workflow Migration / Disposition** 

|**Previous Workflow**|**Disposition**|**Replacement**|**Rationale**|
|---|---|---|---|
|WF-EL-01 Apply and Decide Leave|Reconstructed|CW-EL-01 + BW-EL-01–09|Uses complete new-leave Basis paths; substitute<br>consent/recovery fragments are embedded within the<br>applicable CL/RH, higher-sanction, and Director paths.|
|WF-EL-02 Modify or Withdraw Pending Request|Retired / redistributed|Withdrawal in CW-EL-01 and CW-EL-03; no Modify<br>workflow|Pending in-place modification is removed. Withdrawal is<br>represented where it is actually valid.|
|WF-EL-03 Cancel Approved Leave|Reconstructed|CW-EL-02 + BW-EL-10–11|Uses complete cancellation paths with terminal<br>approve/reject alternatives; fresh application remains<br>outside cancellation.|
|WF-EL-04 Extend Ongoing Leave|Reconstructed|CW-EL-03 + BW-EL-12–14|Uses complete extension paths for no-substitute,<br>accepted-consent, and one decline/replacement traversal<br>variants.|
|WF-EL-05 Resume Duty and Close Leave|Reconstructed|CW-EL-04 + BW-EL-15–17|Replaces “closure” and verifier semantics with<br>Sanctioning Authority review and normal/early/late<br>outcomes.|
|WF-EL-06 Record Offline-Sanctioned Leave|Retired as workflow|EL-UC-016 + BR-EL-029|Record synchronization, not a second approval<br>progression.|
|WF-EL-07 Year-End Leave Processing|Retired as workflow|EL-UC-020 + BR-EL-002–009|Event-triggered isolated system operation; no SF<br>representation type.|
|WF-EL-08 SLA Reminder / Escalation|Retired as standalone workflow|EL-UC-021 + BR-EL-032/033/038; XTP-EL-01 where routing<br>changes|Reminder/notification-only behavior is UC+BR; routing-<br>changing escalation is cross-cutting System transition<br>only.|



