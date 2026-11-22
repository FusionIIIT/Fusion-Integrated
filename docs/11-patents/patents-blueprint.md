# Patent Management System (PMS) — Module Blueprint

**Module Code:** `patents`  
**Base Path:** `/patents`  
**API Prefix:** `/api/v1/patents/`  
**Governing Method:** Problem Statement v1.2 → Requirement Registry v1.3 → UC + BR v1.3 → Workflows v1.3 → Architecture Baseline

---

## Revision Change Log

| Revision Item | Description of Change | Governing Spec Reference |
|---|---|---|
| **A1** | Updated Attorney decline transition: `ASSIGNMENT_OFFERED` + `decline_assignment` transitions to `PENDING_REVIEW` (instead of `APPROVED`), representing declined assignments awaiting reassignment by `PCC_ADMIN`. | `BW-PMS-07` (rows 2 and 3) |
| **A2** | Disambiguated `PENDING_REVIEW`: reserved `PENDING_REVIEW` exclusively for declined attorney assignments awaiting reassignment. Added `ASSESSMENT_IN_PROGRESS` as the distinct assessment substate after `ATTORNEY_ASSIGNED` acceptance. | `BW-PMS-06`, `BW-PMS-07`, `UC-PMS-012` |
| **A3** | Corrected withdrawal rule citations to `BR-PMS-067`, `BR-PMS-068`, `BR-PMS-069`, and `BR-PMS-070` (replacing `BR-PMS-082..086`, which govern document versioning). Made the eligible pre-filing status list configurable in `PatentPolicy` with no hard-coded default. | `BR-PMS-067..070`, `BW-PMS-16`, `ISS-PMS-020` |
| **A4.1** | Re-cited Attorney assignment guard in §3.3 to `BR-PMS-040..045` and `BR-PMS-127` (replacing `038..042`). | `BW-PMS-06`, `BW-PMS-07`, `BR-PMS-040..045`, `BR-PMS-127` |
| **A4.2** | Re-cited Attorney accept/decline transitions to `UC-PMS-011` and `PMS-AFR-080..081` (no governing BR). | `BW-PMS-06` (row 2), `BW-PMS-07` (row 2), `UC-PMS-011`, `PMS-AFR-080..081` |
| **A4.3** | Mapped assessment start to `UC-PMS-012`; noted that no BR governs start, while `BR-PMS-046` governs finalized opinion recommendation validation. | `UC-PMS-012`, `BR-PMS-046`, `PMS-AFR-082..087` |
| **A4.4** | Re-cited appeal filing in §3.3 and §3.5 to `BR-PMS-092..094` (replacing `088..091`, which govern licensing). | `BR-PMS-092..094`, `UC-PMS-022`, `BW-PMS-03..05` |
| **B1** | Corrected all endpoint and transition rule citations in §3.3 and §3.5 against the authoritative v1.3 rule registry. | `04_PMS_Business_Rule_Specifications_v1.3_DIRECT_FINAL.md` |
| **B2** | Corrected cost escalation citation in §3.8 Open Item 4 to `BR-PMS-051` (replacing `BR-PMS-050`, which specifies administrative cost inclusion). | `BR-PMS-051` |
| **B3.1** | Added explicit architectural note in §3.3 clarifying that `BW-PMS-08..10` (budgets) and `BW-PMS-12..13` (office actions) represent subordinate entity lifecycles tracked in `PatentBudgetLedger` and `OfficeActionRecord`, not in `PatentApplication.status`. | `BW-PMS-08..10`, `BW-PMS-12..13`, `CW-PMS-02`, `CW-PMS-03` |
| **B3.2** | Added revision/resubmission path from `REJECTED` in §3.3 state machine table, validating that `REJECTED` applications may be revised within 60 days to transition to `RESUBMITTED` or expire to `EXPIRED`. | `BR-PMS-034`, `BR-PMS-035`, `BR-PMS-036`, `BR-PMS-038`, `UC-PMS-005` |
| **S2.1** | Removed citations to non-existent rules `BR-PMS-062`, `063`, `064`, `071`, `072`. Corrected post-grant maintenance citations to `BR-PMS-059`, `060`, `061`, `100` in §3.3 and §3.5. Added external patent office boundary rules `BR-PMS-138` and `BR-PMS-142` to filing and office-action endpoints in §3.5. | `BR-PMS-059..061`, `BR-PMS-100`, `BR-PMS-138`, `BR-PMS-142` |
| **S2.2** | Aligned `modify_decision` transition resulting state from `APPEAL_SUBMITTED` to `DECISION_MODIFIED` (instead of `APPROVED`), directly mirroring authoritative transition row 3 without inventing downstream assumptions. | `BW-PMS-05` (row 3), `UC-PMS-023` |
| **S2.3** | Re-confirmed and highlighted subordinate lifecycle tracking in `PatentBudgetLedger` / `OfficeActionRecord` and `REJECTED` resubmission eligibility under `BR-PMS-034`. | `BW-PMS-08..10`, `BW-PMS-12..13`, `BR-PMS-034`, `UC-PMS-005` |

---

## 3.1 (a) — Traceability Table

### Business Rules (84 live rules)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
| --- | --- | --- | --- | --- |
| BR-PMS-003 | Applicants may access report information only for their own patent applications. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to Applicant (Authorization / Access Constraint) |
| BR-PMS-005 | Directors may access PMS reports and analytics only within their authorized PMS scope. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to Director (Authorization / Access Constraint) |
| BR-PMS-006 | Director workflow-oversight access is limited to application workflows in the Director's domain. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to Director (Authorization / Access Constraint) |
| BR-PMS-014 | Application supporting documents accepted for submission must be PDF files. | `domain/validation.py` | `domain/validation.py & api/serializers.py` | Applies to Applicant (Validation) |
| BR-PMS-015 | An application document must be under 50 MB to be accepted. | `domain/validation.py` | `domain/validation.py & api/serializers.py` | Applies to Applicant (Validation) |
| BR-PMS-016 | A submitted application document must pass malware validation before it is accepted. | `domain/validation.py` | `domain/validation.py & services/` | Applies to PMS (Validation) |
| BR-PMS-017 | Required application fields must be complete before PMS accepts the application submission. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Applicant (Validation) |
| BR-PMS-020 | Inventor agreements must be completed before external filing. | `services/` | `services/applications.py` | Applies to Applicant / Attorney (Constraint) |
| BR-PMS-022 | Automatic Director assignment may be used only when configured assignment rules are available, and it must apply the same governing assignment criteria. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN / Director (Routing / Assignment) |
| BR-PMS-023 | Director expertise matching with the application domain is an assignment criterion. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-024 | Director workload balance is an assignment criterion. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-025 | PMS must perform a conflict-of-interest check before Director assignment. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN / Director (Routing / Assignment) |
| BR-PMS-026 | A Director must not review an application in which that Director is listed as an inventor. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Director (Routing / Assignment) |
| BR-PMS-027 | PCC_ADMIN must not act as reviewer for an application in which PCC_ADMIN is listed as an inventor. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-029 | A Director review decision must be exactly one of: Approve, Reject, or Needs Revision. | `services/` | `services/applications.py` | Applies to Director (Decision Constraint) |
| BR-PMS-030 | Every Director review decision must include a justification of at least 50 characters. | `services/` | `services/applications.py` | Applies to Director (Constraint) |
| BR-PMS-031 | Director review must be completed within 15 business days of assignment. | `services/` | `services/applications.py` | Applies to Director (Trigger / Time) |
| BR-PMS-033 | Application revision is permitted when the application status is Needs Revision. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-034 | Application revision is permitted when the application status is Rejected. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-035 | A revised application must be resubmitted within 60 days from the relevant rejection or revision-request decision date. | `services/` | `services/applications.py` | Applies to Applicant (Trigger / Time) |
| BR-PMS-036 | A resubmitted revision must address the recorded Director feedback. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Applicant / Director (Validation) |
| BR-PMS-038 | When the applicable 60-day resubmission period expires without valid resubmission, PMS changes the application status to Expired. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-040 | Only PCC_ADMIN may assign an Attorney to an Approved application. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-041 | An assigned Attorney must be selected from the approved panel unless an institutional exception is recorded or allowed. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-042 | Attorney expertise matching the application domain is an assignment criterion. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-043 | Attorney current workload is an assignment criterion. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN (Routing / Assignment) |
| BR-PMS-044 | PMS must perform a conflict-of-interest check before Attorney assignment. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN / Attorney (Routing / Assignment) |
| BR-PMS-045 | Applicant Attorney preference may be considered only when the preferred Attorney is in the approved panel. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant / PCC_ADMIN (Routing / Assignment) |
| BR-PMS-046 | A finalized Attorney patentability opinion must contain exactly one recommendation: File Patent, Do Not File, or Needs Amendment. | `services/` | `services/applications.py` | Applies to Attorney (Decision Constraint) |
| BR-PMS-048 | Budget information must include filing fees. | `domain/` | `domain/calculations.py & models/` | Applies to Director (Calculation / Data Rule) |
| BR-PMS-049 | Budget information must include attorney fees. | `domain/` | `domain/calculations.py & models/` | Applies to Director (Calculation / Data Rule) |
| BR-PMS-050 | Budget information must include administrative costs. | `domain/` | `domain/calculations.py & models/` | Applies to Director (Calculation / Data Rule) |
| BR-PMS-051 | When total patent cost exceeds the configured threshold, PMS must route/escalate the case to the applicable higher authority. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Director / PCC_ADMIN (Routing / Assignment) |
| BR-PMS-052 | Budget approval is permitted only when the application status is Approved. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Director (Eligibility / Lifecycle) |
| BR-PMS-053 | Where budget-availability information is available to PMS, budget availability must be validated before approval. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Director (Validation) |
| BR-PMS-055 | Where corresponding validation rules are available, the filing package must satisfy the applicable patent-office format standards before PMS records compliant readiness. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Attorney (Validation) |
| BR-PMS-056 | An international filing must include additional justification recorded in PMS. | `services/` | `services/applications.py` | Applies to Attorney (Constraint) |
| BR-PMS-059 | Post-grant tracking is activated only when patent status is Granted. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Attorney / Director (Eligibility / Lifecycle) |
| BR-PMS-060 | Where applicable schedule rules are available, the maintenance-fee schedule is determined from grant date and jurisdiction. | `domain/` | `domain/calculations.py & models/` | Applies to Attorney / Director (Calculation / Data Rule) |
| BR-PMS-061 | An explicit Renew or Do Not Renew decision is required before each maintenance deadline. | `services/` | `services/applications.py` | Applies to Director (Trigger / Time) |
| BR-PMS-065 | An office-action response must be recorded as submitted within the applicable deadline unless a permitted extension applies. | `services/` | `services/applications.py` | Applies to Attorney (Trigger / Time) |
| BR-PMS-066 | Office-action response deadline tracking is automated only where applicable deadline data/rules are available to PMS. | `services/` | `services/applications.py` | Applies to Attorney / Applicant (Trigger / Time) |
| BR-PMS-067 | Withdrawal is permitted only before the filing stage. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-068 | Withdrawal is permitted only when the current application status is withdrawal-eligible under the applicable PMS rule/configuration. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-069 | A withdrawal request must include an Applicant-provided reason. | `services/` | `services/applications.py` | Applies to Applicant (Constraint) |
| BR-PMS-070 | Co-inventor consent for withdrawal must be recorded when the applicable process requires such consent. | `services/` | `services/applications.py` | Applies to Applicant / Co-inventor (Constraint) |
| BR-PMS-073 | Inventor information must pass PMS validation before the change is accepted. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Applicant (Validation) |
| BR-PMS-074 | Inventor ownership percentages must pass PMS validation before the change is accepted. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Applicant (Validation) |
| BR-PMS-075 | Required inventor consent must be obtained before filing. | `services/` | `services/applications.py` | Applies to Applicant / Co-inventor (Constraint) |
| BR-PMS-076 | Electronic signatures for inventor consent/agreement may be collected only where legally permitted and configured. | `services/` | `services/applications.py` | Applies to Applicant / Co-inventor (Constraint) |
| BR-PMS-077 | Electronic-signature validation applies only where legally permitted and configured. | `domain/validation.py` | `domain/validation.py & services/` | Applies to Applicant / Co-inventor (Validation) |
| BR-PMS-078 | Inventor agreements must be complete before filing. | `services/` | `services/applications.py` | Applies to Applicant / Attorney (Constraint) |
| BR-PMS-082 | PMS assigns automatic version numbers to new document versions. | `domain/` | `domain/calculations.py & models/` | Applies to Applicant / Attorney (Calculation / Data Rule) |
| BR-PMS-084 | Access to previous document versions is limited by applicable role and application-status access rules. | `services/` | `services/applications.py` | Applies to Applicant / Director / Attorney (Constraint) |
| BR-PMS-086 | Document access is controlled by user role and application status. | `services/` | `services/applications.py` | Applies to Applicant / Director / Attorney / PCC_ADMIN (Constraint) |
| BR-PMS-087 | Applicants may edit application documents only while the application status is Needs Revision. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-088 | Licensing/technology-transfer requests are routed to the appropriate committee or Director according to the applicable institutional process. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant / Director (Routing / Assignment) |
| BR-PMS-091 | License records are subject to confidentiality controls. | `services/` | `services/applications.py` | Applies to Director / PCC_ADMIN (Constraint) |
| BR-PMS-092 | Only an application in Rejected status is eligible for an Applicant appeal. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Applicant (Eligibility / Lifecycle) |
| BR-PMS-093 | An appeal must be filed within the applicable configured or institutionally defined allowed period. | `services/` | `services/applications.py` | Applies to Applicant (Trigger / Time) |
| BR-PMS-094 | An appeal must include Applicant-provided grounds and justification. | `services/` | `services/applications.py` | Applies to Applicant (Constraint) |
| BR-PMS-095 | A Director appeal outcome must be exactly one of: Uphold Rejection, Remand for Amendment, or Modify Decision. | `services/` | `services/applications.py` | Applies to Director (Decision Constraint) |
| BR-PMS-097 | PMS calculates/monitors the Director review deadline using the applicable review-deadline rule. | `services/` | `services/applications.py` | Applies to Director / PCC_ADMIN (Trigger / Time) |
| BR-PMS-098 | PMS calculates/monitors the revision deadline using the applicable revision-deadline rule. | `services/` | `services/applications.py` | Applies to Applicant / Director (Trigger / Time) |
| BR-PMS-099 | PMS calculates/monitors office-action response deadlines only where applicable deadline rules/data are available. | `services/` | `services/applications.py` | Applies to Attorney / Applicant (Trigger / Time) |
| BR-PMS-100 | PMS calculates/monitors maintenance-fee deadlines only where applicable jurisdictional schedule rules/data are available. | `services/` | `services/applications.py` | Applies to Attorney / Director (Trigger / Time) |
| BR-PMS-101 | Where applicable, PMS generates an alert 30 days before a tracked deadline. | `services/` | `services/applications.py` | Applies to Relevant stakeholder (Trigger / Time) |
| BR-PMS-102 | Where applicable, PMS generates an alert 15 days before a tracked deadline. | `services/` | `services/applications.py` | Applies to Relevant stakeholder (Trigger / Time) |
| BR-PMS-103 | Where applicable, PMS generates an alert 5 days before a tracked deadline. | `services/` | `services/applications.py` | Applies to Relevant stakeholder (Trigger / Time) |
| BR-PMS-104 | A missed tracked deadline triggers escalation according to the configured escalation chain. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN / relevant stakeholder (Routing / Assignment) |
| BR-PMS-116 | PMS responsibility for email notifications is limited to triggering system-generated emails; external delivery infrastructure is outside PMS. | `services/` | `services/applications.py` | Applies to PMS / external email service (Constraint) |
| BR-PMS-121 | Where applicable, audit records include user ID, action type, timestamp, application ID, previous state, and new state. | `domain/` | `domain/calculations.py & models/` | Applies to PCC_ADMIN / compliance reviewer (Calculation / Data Rule) |
| BR-PMS-122 | Critical PMS operations create immutable audit records. | `services/` | `services/applications.py` | Applies to PCC_ADMIN / compliance reviewer (Constraint) |
| BR-PMS-126 | A valid PMS role assignment is required before a user may access patent-management functions. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to Applicant / Director / PCC_ADMIN / Attorney (Authorization / Access Constraint) |
| BR-PMS-127 | Attorney assignment must not occur before Director approval is recorded. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to PCC_ADMIN / Attorney (Eligibility / Lifecycle) |
| BR-PMS-128 | External filing must not occur until required approvals and budget allocation are complete. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Attorney / Director (Eligibility / Lifecycle) |
| BR-PMS-130 | Confidential patent information is protected by role-based access control. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to Applicant / Director / PCC_ADMIN / Attorney (Authorization / Access Constraint) |
| BR-PMS-131 | PMS maintains exactly one active PCC_ADMIN oversight role. | `selectors/scoping.py` | `selectors/scoping.py (queryset narrowing)` | Applies to PCC_ADMIN (Authorization / Access Constraint) |
| BR-PMS-138 | Patent-office systems are external; PMS may validate, record, track, notify, log, or report based on filing/status/communication data but does not control patent-office processing or decisions. | `services/` | `services/ (external boundary encapsulation)` | Applies to Patent office systems (Scope / Integration Boundary) |
| BR-PMS-139 | Financial systems and payment/accounting execution are external; PMS may record, validate, approve, track, log, or exchange financial metadata where integration is available. | `services/` | `services/ (external boundary encapsulation)` | Applies to Financial systems (Scope / Integration Boundary) |
| BR-PMS-140 | Document-management systems are external; PMS owns only the document/version/access/audit behavior explicitly represented within PMS or an available integration. | `services/` | `services/ (external boundary encapsulation)` | Applies to Document management system (Scope / Integration Boundary) |
| BR-PMS-141 | External prior-art databases are query sources and are not PMS-owned repositories. | `services/` | `services/ (external boundary encapsulation)` | Applies to Prior-art databases (Scope / Integration Boundary) |
| BR-PMS-142 | PMS must not treat external patent-office filing success as internally controlled beyond recording submitted filing details and confirmations. | `services/` | `services/ (external boundary encapsulation)` | Applies to Attorney / patent office systems (Scope / Integration Boundary) |
| BR-PMS-146 | Applicant review and approval of an office-action response is required only when the applicable process requires Applicant review. | `domain/state_machine.py` | `domain/state_machine.py & services/applications.py` | Applies to Office-action response handling (Eligibility / Routing) |

### Use Cases (33 live use cases)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
| --- | --- | --- | --- | --- |
| UC-PMS-001 | Submit Patent Application: Create and submit a complete patent application for institutional processing. | `services/` | `services/ & domain/state_machine.py (Submit Patent Application)` | Primary Actor: Applicant |
| UC-PMS-002 | Track Application Status and History: View the current status, progress, and recorded history of the Applicant's own applications. | `selectors/` | `selectors/ & api/views.py (Track Application Status and History)` | Primary Actor: Applicant |
| UC-PMS-003 | Manage Co-Inventors and Agreements: Maintain inventor identities, ownership shares, consents, and agreements for an application. | `services/` | `services/ & domain/state_machine.py (Manage Co-Inventors and Agreements)` | Primary Actor: Applicant |
| UC-PMS-004 | Search and Attach Prior Art: Search prior-art sources and attach selected references to an application. | `selectors/` | `selectors/ & api/views.py (Search and Attach Prior Art)` | Primary Actor: Applicant or Attorney |
| UC-PMS-005 | Revise and Resubmit Application: Revise an application after a Needs Revision or Rejected decision and resubmit it for a new review cycle. | `services/` | `services/ & domain/state_machine.py (Revise and Resubmit Application)` | Primary Actor: Applicant |
| UC-PMS-006 | Withdraw Patent Application: Withdraw an application when the applicable pre-filing status permits withdrawal. | `services/` | `services/ & domain/state_machine.py (Withdraw Patent Application)` | Primary Actor: Applicant |
| UC-PMS-007 | Assign Application to Director: Assign a Submitted application to an eligible Director and start the review timeline. | `services/` | `services/ & domain/state_machine.py (Assign Application to Director)` | Primary Actor: PCC_ADMIN |
| UC-PMS-008 | Review Patent Application: Review an assigned application and record one supported technical-merit decision. | `services/` | `services/ & domain/state_machine.py (Review Patent Application)` | Primary Actor: Director |
| UC-PMS-009 | Review and Decide Patent Budget: Review filing/prosecution costs and record a budget decision or escalation. | `services/` | `services/ & domain/state_machine.py (Review and Decide Patent Budget)` | Primary Actor: Director |
| UC-PMS-010 | Assign Attorney to Approved Application: Select and assign an eligible Attorney to an Approved application. | `services/` | `services/ & domain/state_machine.py (Assign Attorney to Approved Application)` | Primary Actor: PCC_ADMIN |
| UC-PMS-011 | Accept or Decline Attorney Assignment: Record the assigned Attorney's acceptance or decline decision. | `services/` | `services/ & domain/state_machine.py (Accept or Decline Attorney Assignment)` | Primary Actor: Attorney |
| UC-PMS-012 | Conduct Patentability Assessment: Record legal/patentability analysis and a supported filing recommendation. | `services/` | `services/ & domain/state_machine.py (Conduct Patentability Assessment)` | Primary Actor: Attorney |
| UC-PMS-013 | Prepare and Record External Patent Filing: Prepare a filing package, perform supported validation, submit externally, and record filing confirmation in PMS. | `services/` | `services/ & domain/state_machine.py (Prepare and Record External Patent Filing)` | Primary Actor: Attorney |
| UC-PMS-014 | Record Patent Office Communication: Record official patent-office communication, including an office action, for lifecycle tracking. | `services/` | `services/ & domain/state_machine.py (Record Patent Office Communication)` | Primary Actor: Attorney |
| UC-PMS-015 | Respond to Office Action: Prepare, finalize, and record submission of an office-action response within applicable timing rules. | `services/` | `services/ & domain/state_machine.py (Respond to Office Action)` | Primary Actor: Attorney |
| UC-PMS-016 | Monitor Deadlines and Escalations: Monitor calculated deadlines, reminders, missed-deadline escalations, and pending actions. | `selectors/` | `selectors/ & api/views.py (Monitor Deadlines and Escalations)` | Primary Actor: PCC_ADMIN |
| UC-PMS-017 | Manage Post-Grant Tracking and Maintenance: Track granted patents, maintenance schedules, renewal decisions, and recorded maintenance actions. | `selectors/` | `selectors/ & api/views.py (Manage Post-Grant Tracking and Maintenance)` | Primary Actor: Attorney |
| UC-PMS-018 | Make Maintenance Renewal Decision: Record the required Renew or Do Not Renew decision for an upcoming maintenance deadline. | `services/` | `services/ & domain/state_machine.py (Make Maintenance Renewal Decision)` | Primary Actor: Director |
| UC-PMS-019 | Manage Document Versions: Upload, version, archive, and access application documents under role/status controls. | `services/` | `services/ & domain/state_machine.py (Manage Document Versions)` | Primary Actor: Applicant (also Attorney/Director/PCC_ADMIN when authorized) |
| UC-PMS-020 | Submit Licensing or Technology-Transfer Request: Submit a licensing or technology-transfer request linked to patent/IP records. | `services/` | `services/ & domain/state_machine.py (Submit Licensing or Technology-Transfer Request)` | Primary Actor: Applicant |
| UC-PMS-021 | Review Licensing or Technology-Transfer Request: Review a request routed to the Director and record negotiation/final-agreement information within PMS authority. | `services/` | `services/ & domain/state_machine.py (Review Licensing or Technology-Transfer Request)` | Primary Actor: Director |
| UC-PMS-022 | File Appeal Against Rejection: Submit a supported appeal against a Rejected application within the applicable appeal period. | `services/` | `services/ & domain/state_machine.py (File Appeal Against Rejection)` | Primary Actor: Applicant |
| UC-PMS-023 | Review Appeal: Review an appeal and record one permitted appeal outcome. | `services/` | `services/ & domain/state_machine.py (Review Appeal)` | Primary Actor: Director |
| UC-PMS-024 | Generate System-Wide PMS Reports and Analytics: Generate authorized system-wide PMS reports, dashboards, analytics, schedules, and exports. | `services/` | `services/ & domain/state_machine.py (Generate System-Wide PMS Reports and Analytics)` | Primary Actor: PCC_ADMIN |
| UC-PMS-025 | Manage PMS Roles and Configuration: Manage PMS-specific configuration and role assignments within module scope. | `services/` | `services/ & domain/state_machine.py (Manage PMS Roles and Configuration)` | Primary Actor: PCC_ADMIN |
| UC-PMS-026 | Maintain Attorney Panel and Expertise Mappings: Maintain approved attorney-panel membership and expertise mappings used by assignment. | `services/` | `services/ & domain/state_machine.py (Maintain Attorney Panel and Expertise Mappings)` | Primary Actor: PCC_ADMIN |
| UC-PMS-027 | Monitor Workflow and Handle Exceptional Cases: Monitor PMS workflows and handle/route conflicts, delayed actions, escalations, and exceptional cases within PMS scope. | `selectors/` | `selectors/ & api/views.py (Monitor Workflow and Handle Exceptional Cases)` | Primary Actor: PCC_ADMIN |
| UC-PMS-028 | View Audit Trail and Compliance Logs: View audit/compliance records for authorized verification or forensic analysis. | `selectors/` | `selectors/ & api/views.py (View Audit Trail and Compliance Logs)` | Primary Actor: PCC_ADMIN |
| UC-PMS-029 | Review Office-Action Response: Review and approve an Attorney-prepared office-action response when the applicable process requires Applicant review. | `services/` | `services/ & domain/state_machine.py (Review Office-Action Response)` | Primary Actor: Applicant |
| UC-PMS-030 | View Own Application Reports: View report information for the Applicant's own patent applications. | `selectors/` | `selectors/ & api/views.py (View Own Application Reports)` | Primary Actor: Applicant |
| UC-PMS-031 | View PMS Reports and Analytics: Generate/view PMS reports and analytics within the Director's authorized scope. | `selectors/` | `selectors/ & api/views.py (View PMS Reports and Analytics)` | Primary Actor: Director |
| UC-PMS-032 | View Application Workflow Oversight: View workflow oversight information for applications in the Director's domain. | `selectors/` | `selectors/ & api/views.py (View Application Workflow Oversight)` | Primary Actor: Director |
| UC-PMS-033 | Record Patent Legal Advice: Record legal advice associated with a patent application throughout its lifecycle. | `services/` | `services/ & domain/state_machine.py (Record Patent Legal Advice)` | Primary Actor: Attorney |


---

## 3.2 (b) — Domain Model

### Entities, Fields, and Invariants

#### 1. `PatentApplication` (Aggregate Root)
* **Fields:**
  * `id`: BigAutoField
  * `application_number`: CharField(32, unique=True, db_index=True) — e.g. `PMS-2026-0001`
  * `applicant_user_id`: IntegerField(db_index=True) — plain integer user id (`UserScopedModel`)
  * `title`: CharField(500) — application title
  * `abstract`: TextField — application abstract
  * `description`: TextField — detailed technical description
  * `claims`: TextField — patent claims definition
  * `status`: CharField(32, db_index=True) — lifecycle status enum
  * `domain_category`: CharField(100) — technology domain/category for expertise matching
  * `assigned_director_id`: IntegerField(null=True, blank=True, db_index=True)
  * `assigned_attorney_id`: IntegerField(null=True, blank=True, db_index=True)
  * `external_filing_id`: CharField(100, blank=True, default="")
  * `filing_date`: DateField(null=True, blank=True)
  * `grant_date`: DateField(null=True, blank=True)
  * `jurisdiction`: CharField(50, default="IN") — "IN" (Indian Patent Office) or "PCT" / international
  * `decision_date`: DateTimeField(null=True, blank=True) — timestamp of review rejection/revision request for 60-day window
  * `version`: PositiveIntegerField(default=1) — optimistic locking & version tracking
  * `created_at`, `updated_at`: DateTimeField (`TimeStampedModel`)
* **Invariants & Database Constraints:**
  * Unique constraint on `application_number`.
  * Check constraint: `status` in defined lifecycle states.
  * Check constraint: `version >= 1`.
  * Check constraint: `assigned_director_id != applicant_user_id` when director is assigned (COI rule).

#### 2. `CoInventor`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="co_inventors")
  * `user_id`: IntegerField(null=True, blank=True) — optional for external co-inventors
  * `name`: CharField(255)
  * `email`: EmailField
  * `share_percentage`: DecimalField(max_digits=5, decimal_places=2) — ownership share
  * `consent_granted`: BooleanField(default=False) — in-app consent flag
  * `consent_timestamp`: DateTimeField(null=True, blank=True)
* **Invariants & Database Constraints:**
  * Check constraint: `share_percentage > 0 AND share_percentage <= 100`.
  * Sum of shares across inventors must equal 100% (validated at pre-filing gate).

#### 3. `ApplicationDocument`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="documents")
  * `document_type`: CharField(50) — `specification`, `claims`, `prior_art`, `agreement`, `office_action_response`
  * `file_name`: CharField(255)
  * `file_format`: CharField(10) — must be `pdf` (`BR-PMS-014`)
  * `file_size_bytes`: BigIntegerField — max 50 MB = 52,428,800 bytes (`BR-PMS-015`)
  * `storage_path`: CharField(500)
  * `sensitivity_level`: CharField(30, default="confidential") — `normal`, `confidential`, `highly_confidential`
  * `version`: PositiveIntegerField(default=1)
  * `uploaded_by_user_id`: IntegerField()
  * `created_at`: DateTimeField(auto_now_add=True)
* **Invariants & Database Constraints:**
  * Check constraint: `file_size_bytes > 0 AND file_size_bytes <= 52428800`.
  * Check constraint: `file_format = 'pdf'`.

#### 4. `ReviewDecision`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="reviews")
  * `director_user_id`: IntegerField()
  * `decision`: CharField(20) — `Approve`, `Reject`, `Needs Revision`
  * `justification`: TextField — minimum 50 characters (`BR-PMS-030`)
  * `assigned_at`: DateTimeField()
  * `decided_at`: DateTimeField(auto_now_add=True)
* **Invariants & Database Constraints:**
  * Check constraint: `LENGTH(justification) >= 50`.
  * Check constraint: `decision IN ('Approve', 'Reject', 'Needs Revision')`.

#### 5. `AppealRecord`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="appeals")
  * `applicant_user_id`: IntegerField()
  * `grounds`: TextField
  * `status`: CharField(30) — `SUBMITTED`, `REMANDED`, `UPHELD`, `MODIFIED`
  * `director_user_id`: IntegerField(null=True, blank=True)
  * `decision_notes`: TextField(blank=True, default="")
  * `submitted_at`: DateTimeField(auto_now_add=True)
  * `decided_at`: DateTimeField(null=True, blank=True)

#### 6. `AttorneyPanelMember`
* **Fields:**
  * `id`: BigAutoField
  * `user_id`: IntegerField(unique=True) — IAM user id of attorney
  * `firm_name`: CharField(255)
  * `expertise_domains`: JSONField(default=list) — list of domain strings
  * `active_workload`: PositiveIntegerField(default=0)
  * `is_approved_panel`: BooleanField(default=True)
  * `created_at`: DateTimeField(auto_now_add=True)

#### 7. `PatentBudgetLedger` (Append-Only Financial Metadata)
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="budget_entries")
  * `entry_type`: CharField(30) — `ESTIMATE`, `APPROVAL`, `EXPENDITURE`, `REVERSAL`
  * `amount`: DecimalField(max_digits=12, decimal_places=2)
  * `currency`: CharField(3, default="INR")
  * `category`: CharField(50) — `filing_fee`, `attorney_fee`, `maintenance_fee`, `admin_cost`
  * `status`: CharField(30, default="PENDING") — `PENDING`, `APPROVED`, `REJECTED`, `ESCALATED`
  * `authorized_by_user_id`: IntegerField()
  * `notes`: TextField(blank=True, default="")
  * `created_at`: DateTimeField(auto_now_add=True)
* **Invariants & Database Constraints:**
  * Append-only: updates and deletes forbidden in service layer.

#### 8. `OfficeActionRecord`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="office_actions")
  * `action_code`: CharField(100) — official reference number
  * `issuing_authority`: CharField(100)
  * `issued_date`: DateField()
  * `response_deadline`: DateField()
  * `status`: CharField(30, default="RECORDED") — `RECORDED`, `DRAFTING`, `AWAITING_APPLICANT`, `APPLICANT_APPROVED`, `RESPONSE_READY`, `SUBMITTED`
  * `requires_applicant_review`: BooleanField(default=False) (`BR-PMS-146`)
  * `response_summary`: TextField(blank=True, default="")
  * `submitted_at`: DateTimeField(null=True, blank=True)

#### 9. `TechnologyTransferRecord`
* **Fields:**
  * `id`: BigAutoField
  * `application`: ForeignKey(`PatentApplication`, on_delete=CASCADE, related_name="licensing_records")
  * `applicant_user_id`: IntegerField()
  * `request_type`: CharField(50) — `Licensing`, `Assignment`, `Commercialization`
  * `partner_name`: CharField(255)
  * `status`: CharField(30, default="SUBMITTED") — `SUBMITTED`, `UNDER_REVIEW`, `NEGOTIATING`, `AGREEMENT_RECORDED`, `REJECTED`
  * `confidentiality_level`: CharField(30, default="confidential")
  * `terms_summary`: TextField(blank=True, default="")
  * `created_at`: DateTimeField(auto_now_add=True)

#### 10. `PatentPolicy` (Effective-Dated Configuration)
* **Fields:**
  * `id`: BigAutoField
  * `director_review_days`: PositiveIntegerField(default=15)
  * `revision_resubmission_days`: PositiveIntegerField(default=60)
  * `cost_escalation_threshold`: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
  * `max_document_size_bytes`: BigIntegerField(default=52428800)
  * `withdrawal_eligible_states`: JSONField(default=list) — list of configurable pre-filing statuses
  * `effective_from`: DateTimeField(auto_now_add=True)
  * `is_active`: BooleanField(default=True)

---

## 3.3 (c) — State Machine

### Declarative Transition Table

All lifecycle progression is mediated by a single transactional choke-point in `services/applications.py::transition_application()`. It evaluates `(current_state, event, acting_role)` against this table under `select_for_update()`. Any transition not defined here is strictly inexpressible.

> [!NOTE]
> **Subordinate Entity Lifecycles:** Workflows `BW-PMS-08..10` (budget approval, rejection, escalation) and `BW-PMS-12..13` (office-action response cycles with or without applicant review) govern subordinate records and are tracked inside `PatentBudgetLedger.status` (`PENDING`, `APPROVED`, `REJECTED`, `ESCALATED`) and `OfficeActionRecord.status` (`RECORDED`, `DRAFTING`, `AWAITING_APPLICANT`, `APPLICANT_APPROVED`, `RESPONSE_READY`, `SUBMITTED`), respectively, rather than in `PatentApplication.status`.

| Current State | Event / Action | Permitted Actor | Resulting State | Guard Conditions & Citations |
|---|---|---|---|---|
| `DRAFT` | `submit` | `Applicant` | `SUBMITTED` | Completeness check passed, PDF format & <=50MB docs (`BR-PMS-014`, `015`, `016`, `017`) |
| `SUBMITTED` | `assign_director` | `PCC_ADMIN` | `UNDER_REVIEW` | Director selected != Applicant (`BR-PMS-022..027`) |
| `UNDER_REVIEW` | `approve_review` | `Director` | `APPROVED` | Justification >= 50 chars (`BR-PMS-029`, `030`, `031`) |
| `UNDER_REVIEW` | `request_revision` | `Director` | `NEEDS_REVISION` | Justification >= 50 chars, sets `decision_date` (`BR-PMS-029`, `030`, `031`) |
| `UNDER_REVIEW` | `reject_review` | `Director` | `REJECTED` | Justification >= 50 chars, sets `decision_date` (`BR-PMS-029`, `030`, `031`) |
| `NEEDS_REVISION` | `resubmit` | `Applicant` | `RESUBMITTED` | Resubmitted within 60 days of decision date; addresses feedback (`BR-PMS-033`, `035`, `036`, `UC-PMS-005`) |
| `REJECTED` | `resubmit` | `Applicant` | `RESUBMITTED` | Resubmitted within 60 days of rejection; addresses feedback (`BR-PMS-034`, `035`, `036`, `UC-PMS-005`) |
| `NEEDS_REVISION` | `expire_revision` | `SYSTEM` (Beat) | `EXPIRED` | Elapsed days > 60 days from decision date (`BR-PMS-035`, `038`) |
| `REJECTED` | `expire_revision` | `SYSTEM` (Beat) | `EXPIRED` | Elapsed days > 60 days from decision date with no appeal/resubmission (`BR-PMS-035`, `038`) |
| `RESUBMITTED` | `assign_director` | `PCC_ADMIN` | `UNDER_REVIEW` | Review cycle restarted (`BR-PMS-035`, `PMS-AFR-070`) |
| `REJECTED` | `file_appeal` | `Applicant` | `APPEAL_SUBMITTED` | Appeal filed within allowed period with grounds/justification (`BR-PMS-092`, `093`, `094`, `UC-PMS-022`) |
| `APPEAL_SUBMITTED`| `remand_appeal` | `Director` | `REMANDED` | Remanded for amendment (`BR-PMS-095`, `BW-PMS-03`) |
| `APPEAL_SUBMITTED`| `uphold_rejection` | `Director` | `REJECTION_UPHELD`| Rejection confirmed (`BR-PMS-095`, `BW-PMS-04`) |
| `APPEAL_SUBMITTED`| `modify_decision` | `Director` | `DECISION_MODIFIED`| Appeal outcome = Modify Decision; recorded per `BW-PMS-05` row 3 without downstream extrapolation (`BR-PMS-095`, `BW-PMS-05`) |
| `REMANDED` | `resubmit` | `Applicant` | `RESUBMITTED` | Resubmission within amendment timeframe (`BW-PMS-03`) |
| `APPROVED` | `assign_attorney` | `PCC_ADMIN` | `ASSIGNMENT_OFFERED` | Attorney on approved panel, expertise matched, no COI, sequential gate (`BR-PMS-040..045`, `BR-PMS-127`) |
| `ASSIGNMENT_OFFERED` | `accept_assignment`| `Attorney` | `ATTORNEY_ASSIGNED` | Attorney accepts assignment (`UC-PMS-011`, `PMS-AFR-080`, `BW-PMS-06` row 2) |
| `ASSIGNMENT_OFFERED` | `decline_assignment`| `Attorney` | `PENDING_REVIEW` | Attorney declines assignment; moves to `PENDING_REVIEW` awaiting PCC_ADMIN reassignment (`UC-PMS-011`, `PMS-AFR-081`, `BW-PMS-07` row 2) |
| `PENDING_REVIEW` | `reassign_attorney`| `PCC_ADMIN` | `ASSIGNMENT_OFFERED` | PCC_ADMIN reassigns to new panel attorney (`UC-PMS-010`, `BW-PMS-07` row 3) |
| `ATTORNEY_ASSIGNED` | `start_assessment` | `Attorney` | `ASSESSMENT_IN_PROGRESS` | Patentability evaluation initiated (`UC-PMS-012`; opinion recommendations governed by `BR-PMS-046`) |
| `ASSESSMENT_IN_PROGRESS`| `record_filing` | `Attorney` | `FILED` | Inventor agreements completed (`BR-PMS-020`, `078`), budget recorded (`BR-PMS-128`), format valid (`BR-PMS-055`, `056`) |
| `FILED` | `record_grant` | `Attorney` / `PCC_ADMIN` | `GRANTED` | Official patent grant details recorded (`BR-PMS-059`) |
| `GRANTED` | `schedule_renewal` | `SYSTEM` (Beat) | `MAINTENANCE_PENDING` | Maintenance fee deadline tracking active (`BR-PMS-059`, `060`, `061`, `100`) |
| `MAINTENANCE_PENDING` | `approve_renewal` | `Director` | `RENEWED` | Renewal approved; next cycle scheduled (`BR-PMS-059`, `060`, `061`, `100`, `BW-PMS-14`) |
| `MAINTENANCE_PENDING` | `decline_renewal` | `Director` | `LAPSED` | Do Not Renew decision recorded (`BR-PMS-059`, `061`, `100`, `BW-PMS-15`) |
| `DRAFT` | `withdraw` | `Applicant` | `WITHDRAWN` | Pre-filing withdrawal with reason (`BR-PMS-067`, `068`, `069`, `070`, `BW-PMS-16`) |
| `SUBMITTED` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `SUBMITTED` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `UNDER_REVIEW` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `UNDER_REVIEW` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `NEEDS_REVISION` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `NEEDS_REVISION` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `APPROVED` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `APPROVED` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `ATTORNEY_ASSIGNED` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `ATTORNEY_ASSIGNED` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `PENDING_REVIEW` | `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `PENDING_REVIEW` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |
| `ASSESSMENT_IN_PROGRESS`| `withdraw` | `Applicant` | `WITHDRAWN` | Permitted if `ASSESSMENT_IN_PROGRESS` is in configured withdrawal-eligible states (`BR-PMS-067`, `068`, `069`, `070`) |

*Terminal states:* `WITHDRAWN`, `EXPIRED`, `REJECTION_UPHELD`, `DECISION_MODIFIED`, `LAPSED`.

---

## 3.4 (d) — Permission List

### Exact `registry.py` Content

```python
"""What the server tells the shell about the patents module (ADR-0010)."""

MODULE = {
    "code": "patents",
    "label": "Patent Management",
    "icon": "Certificate",
    "base_path": "/patents",
    "nav_section": "Research",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- applicant (faculty, student, staff) ---------------------------------
    {
        "code": "patents.mine",
        "label": "My Applications",
        "icon": "Files",
        "to": "/patents/mine",
        "required_permission": "patents.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "patents.new",
        "label": "New Application",
        "icon": "FilePlus",
        "to": "/patents/new",
        "required_permission": "patents.application.create",
        "sort_order": 20,
    },
    {
        "code": "patents.prior_art",
        "label": "Prior Art Search",
        "icon": "MagnifyingGlass",
        "to": "/patents/prior-art",
        "required_permission": "patents.prior_art.search",
        "sort_order": 30,
    },

    # -- director (evaluator & authority) ------------------------------------
    {
        "code": "patents.director_reviews",
        "label": "Review Queue",
        "icon": "ClipboardText",
        "to": "/patents/reviews",
        "required_permission": "patents.application.review",
        "sort_order": 40,
    },
    {
        "code": "patents.director_budgets",
        "label": "Budget Approvals",
        "icon": "CurrencyInr",
        "to": "/patents/budget-approvals",
        "required_permission": "patents.budget.approve",
        "sort_order": 50,
    },
    {
        "code": "patents.director_renewals",
        "label": "Maintenance Renewals",
        "icon": "ClockCounterClockwise",
        "to": "/patents/maintenance-decisions",
        "required_permission": "patents.maintenance.decide",
        "sort_order": 55,
    },

    # -- attorney ------------------------------------------------------------
    {
        "code": "patents.attorney_assignments",
        "label": "Attorney Docket",
        "icon": "Briefcase",
        "to": "/patents/docket",
        "required_permission": "patents.assessment.perform",
        "sort_order": 60,
    },
    {
        "code": "patents.office_actions",
        "label": "Office Actions",
        "icon": "WarningCircle",
        "to": "/patents/office-actions",
        "required_permission": "patents.office_action.respond",
        "sort_order": 70,
    },

    # -- coordinator / admin -------------------------------------------------
    {
        "code": "patents.admin_queue",
        "label": "All Applications",
        "icon": "Folders",
        "to": "/patents/all",
        "required_permission": "patents.application.view",
        "sort_order": 80,
    },
    {
        "code": "patents.attorney_panel",
        "label": "Attorney Panel",
        "icon": "Scales",
        "to": "/patents/attorney-panel",
        "required_permission": "patents.panel.manage",
        "sort_order": 90,
    },
    {
        "code": "patents.reports",
        "label": "Reports & Analytics",
        "icon": "ChartBar",
        "to": "/patents/reports",
        "required_permission": "patents.report.view",
        "sort_order": 100,
    },
]

PERMISSIONS = [
    # Application lifecycle
    ("patents.application.create", "Submit a new patent application"),
    ("patents.application.view_self", "View one's own patent applications and reports"),
    ("patents.application.view", "View patent applications within authorized scope"),
    ("patents.application.update", "Revise and update an application"),
    ("patents.application.withdraw", "Withdraw an application before filing"),
    ("patents.application.assign_director", "Assign submitted application to Director"),
    ("patents.application.review", "Review technical merit and decide application"),
    ("patents.application.appeal", "File an appeal against a rejection"),
    ("patents.application.decide_appeal", "Adjudicate an appeal"),

    # Attorney & Assessment
    ("patents.attorney.assign", "Assign attorney to approved application"),
    ("patents.attorney.respond_assignment", "Accept or decline attorney assignment"),
    ("patents.assessment.perform", "Conduct patentability and prior-art assessment"),
    ("patents.filing.record", "Record external patent office filing details"),
    ("patents.office_action.record", "Record external office actions"),
    ("patents.office_action.respond", "Prepare and submit office action responses"),
    ("patents.office_action.approve", "Review and approve office action response"),

    # Budget & Financial
    ("patents.budget.approve", "Review and approve patent filing and prosecution budgets"),
    ("patents.budget.view", "View patent budget and expenditure records"),

    # Post-grant Maintenance
    ("patents.maintenance.track", "Track post-grant maintenance schedules and fees"),
    ("patents.maintenance.decide", "Make patent maintenance renewal decisions"),

    # Technology Transfer & Prior Art
    ("patents.tech_transfer.create", "Submit technology transfer or licensing request"),
    ("patents.tech_transfer.review", "Review technology transfer agreements"),
    ("patents.prior_art.search", "Search and attach prior-art references"),

    # Administration & Oversight
    ("patents.panel.manage", "Manage attorney panel roster and expertise mappings"),
    ("patents.audit.view", "View audit trail and compliance logs"),
    ("patents.report.view", "Generate and view reports and analytics"),

    # System permissions
    ("patents.application.expire", "System revision expiration"),
    ("patents.maintenance.sweep", "System maintenance deadline sweep"),
]

SYSTEM_PERMISSIONS = [
    "patents.application.expire",
    "patents.maintenance.sweep",
]

SCOPE_PERMISSIONS = [
    "patents.application.view",
    "patents.application.review",
    "patents.report.view",
]

_APPLICANT = [
    "patents.application.create",
    "patents.application.view_self",
    "patents.application.update",
    "patents.application.withdraw",
    "patents.application.appeal",
    "patents.prior_art.search",
    "patents.office_action.approve",
    "patents.tech_transfer.create",
]

_DIRECTOR = [
    "patents.application.view",
    "patents.application.review",
    "patents.application.decide_appeal",
    "patents.budget.approve",
    "patents.budget.view",
    "patents.maintenance.decide",
    "patents.tech_transfer.review",
    "patents.report.view",
]

_ATTORNEY = [
    "patents.application.view",
    "patents.attorney.respond_assignment",
    "patents.assessment.perform",
    "patents.filing.record",
    "patents.office_action.record",
    "patents.office_action.respond",
    "patents.maintenance.track",
    "patents.prior_art.search",
]

_PCC_ADMIN = [
    "patents.application.view",
    "patents.application.assign_director",
    "patents.attorney.assign",
    "patents.panel.manage",
    "patents.budget.view",
    "patents.report.view",
    "patents.audit.view",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "Director": _DIRECTOR,
    "attorney": _ATTORNEY,
    "pcc_admin": _PCC_ADMIN,
}
```

---

## 3.5 (e) — Endpoint List

All endpoints live under `/api/v1/patents/` and sit behind two gates:
1. `ModuleAccessGate`: Principal holds grant for module `patents`.
2. `PermissionGate`: Principal holds the declared `required_permission`.

| Method | Path | Required Permission | Scoping / Behavior | Return Type | Enforced Rule IDs |
|---|---|---|---|---|---|
| `GET` | `applications/` | `patents.application.view_self` OR `patents.application.view` | Filtered by `scoping.py` (own if applicant, assigned if director/attorney, all if admin) | `Paginated[ApplicationSummaryDTO]` | `BR-PMS-003`, `005`, `006`, `126`, `130` |
| `POST` | `applications/` | `patents.application.create` | Creates draft/submitted application; validates fields & docs | `ApplicationDetailDTO` | `BR-PMS-014`, `015`, `016`, `017` |
| `GET` | `applications/{id}/` | `patents.application.view_self` OR `patents.application.view` | Scoped lookup (404 if out of scope) | `ApplicationDetailDTO` | `BR-PMS-003`, `005`, `006`, `126`, `130` |
| `PUT` | `applications/{id}/` | `patents.application.update` | Replaces/edits application in `DRAFT`, `NEEDS_REVISION`, or `REJECTED` | `ApplicationDetailDTO` | `BR-PMS-033`, `034`, `035`, `036` |
| `POST` | `applications/{id}/withdraw/` | `patents.application.withdraw` | Pre-filing withdrawal with mandatory reason | `ApplicationDetailDTO` | `BR-PMS-067`, `068`, `069`, `070` |
| `POST` | `applications/{id}/documents/` | `patents.application.update` | Uploads document (PDF, <= 50MB, malware check) | `DocumentDTO` | `BR-PMS-014`, `015`, `016`, `082`, `084`, `086` |
| `POST` | `applications/{id}/consent/` | `patents.application.view_self` | Co-inventor in-app consent recording | `ConsentResultDTO` | `BR-PMS-020`, `073`, `074`, `075`, `078` |
| `POST` | `applications/{id}/assign-director/` | `patents.application.assign_director` | Assigns Director (enforces COI check) | `ApplicationDetailDTO` | `BR-PMS-022..027` |
| `POST` | `applications/{id}/review-decision/` | `patents.application.review` | Records review (Approve/Reject/Revision, $\ge 50$ chars) | `ReviewDecisionDTO` | `BR-PMS-029`, `030`, `031` |
| `POST` | `applications/{id}/appeal/` | `patents.application.appeal` | Files appeal against rejection with grounds | `AppealRecordDTO` | `BR-PMS-092`, `093`, `094` |
| `POST` | `applications/{id}/appeal-decision/`| `patents.application.decide_appeal` | Remand / Uphold / Modify appeal decision | `AppealRecordDTO` | `BR-PMS-095` |
| `POST` | `applications/{id}/assign-attorney/`| `patents.attorney.assign` | Assigns approved panel attorney | `ApplicationDetailDTO` | `BR-PMS-040..045`, `127` |
| `POST` | `applications/{id}/respond-assignment/`| `patents.attorney.respond_assignment` | Attorney accepts or declines assignment | `ApplicationDetailDTO` | `UC-PMS-011`, `PMS-AFR-080..081` |
| `POST` | `applications/{id}/assessment/` | `patents.assessment.perform` | Records patentability opinion | `AssessmentOpinionDTO` | `UC-PMS-012`, `BR-PMS-046` |
| `POST` | `applications/{id}/budget-decision/`| `patents.budget.approve` | Director approves/rejects budget; checks threshold | `BudgetLedgerEntryDTO` | `BR-PMS-048..053`, `128` |
| `POST` | `applications/{id}/filing/` | `patents.filing.record` | Records external filing confirmation | `ApplicationDetailDTO` | `BR-PMS-020`, `055`, `056`, `078`, `128`, `138`, `142` |
| `POST` | `applications/{id}/office-actions/`| `patents.office_action.record` | Logs official office action received | `OfficeActionDTO` | `BR-PMS-065`, `066`, `138` |
| `POST` | `office-actions/{id}/response/`| `patents.office_action.respond` | Submits draft response to office action | `OfficeActionDTO` | `BR-PMS-065`, `138`, `142`, `146` |
| `POST` | `office-actions/{id}/approve/` | `patents.office_action.approve` | Applicant approves response (when required) | `OfficeActionDTO` | `BR-PMS-146` |
| `POST` | `applications/{id}/renewal-decision/`| `patents.maintenance.decide` | Director approves/declines post-grant renewal | `MaintenanceRecordDTO`| `BR-PMS-059`, `060`, `061`, `100` |
| `GET` | `attorney-panel/` | `patents.panel.manage` | List attorney panel members & workloads | `List[AttorneyPanelDTO]` | `BR-PMS-041`, `042`, `043` |
| `POST` | `prior-art/search/` | `patents.prior_art.search` | Queries patent/literature references | `PriorArtResultDTO` | `UC-PMS-004`, `UC-PMS-012`, `BR-PMS-141` |
| `POST` | `tech-transfer/` | `patents.tech_transfer.create` | Submits licensing/tech-transfer request | `TechTransferDTO` | `BR-PMS-088`, `091`, `UC-PMS-020` |
| `GET` | `reports/` | `patents.report.view` | Generates operational metrics & summaries | `ReportDataDTO` | `BR-PMS-003`, `005`, `121` |
| `GET` | `audit-logs/` | `patents.audit.view` | Immutable system audit log lookup | `Paginated[AuditLogDTO]` | `BR-PMS-121`, `122` |

### `Fusion-client` Navigation Entry Handover
For inclusion in `Fusion-client/src/ui/nav/navigation.js` under `INTEGRATED_MODULES`:
```javascript
{
  id: "patents",
  label: "Patents",
  icon: "Certificate",
  to: "/patents",
  section: "Research",
}
```

---

## 3.6 (f) — Contracts

### 1. What `modules/patents/contracts.py` Exposes (All getters plural)
```python
from typing import Sequence
from dataclasses import dataclass

@dataclass(frozen=True)
class PatentSummaryContract:
    application_id: int
    application_number: str
    applicant_user_id: int
    status: str
    title: str

def get_patents_for_users(user_ids: Sequence[int]) -> dict[int, list[PatentSummaryContract]]:
    """Returns active patent applications authored by the requested users."""
    ...

def get_patent_filing_statuses(application_ids: Sequence[int]) -> dict[int, str]:
    """Returns current filing status for requested patent IDs."""
    ...
```

### 2. What PMS Consumes from Other Modules
* **From `modules/directory/contracts.py`:**
  * `get_users(user_ids: Sequence[int]) -> dict[int, UserSnapshot]` for person display names, kinds, and email lookups.
  * No direct queries to `auth_user`, `globals_extrainfo`, or `fusionlab` tables.

---

## 3.7 (g) — Scheduled Work

### Registered in `modules/patents/schedule.py`
```python
from celery.schedules import crontab

BEAT_SCHEDULE = {
    "patents-sweep-deadlines-daily": {
        "task": "modules.patents.tasks.pms_sweep_deadlines",
        "schedule": crontab(hour=0, minute=30),  # Daily at 00:30 UTC
        "options": {"queue": "patents_periodic"},
    },
}

TASK_ROUTES = {
    "modules.patents.tasks.*": {"queue": "patents"},
}
```

### Failure Impact
* **Task:** `pms_sweep_deadlines`
* **Real-world consequence if not running:**
  * Applications in `NEEDS_REVISION` or `REJECTED` whose 60-day resubmission deadline has elapsed will fail to advance to `EXPIRED`, remaining indefinitely in the active review pool.
  * Upcoming office action deadlines and post-grant maintenance renewal deadlines will not trigger warning notifications, potentially causing institutional patent abandonments.

---

## 3.8 (h) — Open Items and Design Choices

### Open Items (Awaiting Institute / Administrative Decisions)
1. **`PCC_ADMIN` Official Designation Name:** The specification does not define the designation name. To be determined by the institute. (For dev/testing in `module-only`, `pcc_admin` will be provisioned in the IAM).
2. **Director Review Scope Expansion:** The spec maps technical review strictly to `"Director"` (PS 2.3.21). Inclusion of `"Dean (R&D)"` and department heads (`"HOD (CSE)"`, etc.) is recorded as an open question for administrative decision.
3. **Applicant Eligibility Policy:** Whether applicants are restricted to faculty/researchers or open to all `student`, `faculty`, and `staff` is pending administrative clarification.
4. **Cost Escalation Numerical Threshold (`BR-PMS-051`):** `BR-PMS-051` mandates escalation for costs exceeding a threshold limit, but the spec deliberately leaves the value undefined. Left configurable in `PatentPolicy` with no seeded default value.

### Design Choices (Architectural Proposals)
1. **IAM Attorney Modeling:** Attorneys are modeled as IAM users holding an `"attorney"` designation; attorney panel approval status and workload are tracked in `AttorneyPanelMember` in `patents`.
2. **Append-Only Budget Ledger:** Implemented as `PatentBudgetLedger` recording individual allocation, expenditure, and reversal events with full user and timestamp metadata.
3. **In-App Co-Inventor Consent:** Provided via an authenticated in-app confirmation action (`POST /applications/{id}/consent/`). E-signatures are treated as optional metadata without assuming legal binding.
4. **Daily Deadline Sweep Cadence:** A daily scheduled Celery beat task (`pms_sweep_deadlines` at 00:30 UTC) is chosen as a design choice to evaluate expirations and dispatch deadline alerts.
5. **Lightweight Technology Transfer:** Implemented strictly as records and status trackers for licensing requests and agreements without payment or royalty pipelines.
6. **Configurable Withdrawal Eligible Statuses:** In accordance with `BR-PMS-068` and `ISS-PMS-020`, pre-filing statuses eligible for withdrawal are maintained as a configurable list in `PatentPolicy` rather than hard-coded.
7. **Strict Alignment to `DECISION_MODIFIED` on Appeal Modification:** `BW-PMS-05` (row 3) specifies `Resulting State: Decision Modified` with note *"No downstream state beyond the recorded appeal outcome is invented where the PS is silent"*. Rather than extrapolating `DECISION_MODIFIED` to `APPROVED`, the state machine directly records `DECISION_MODIFIED` as the resulting terminal appeal state.
