---
purpose: ELM source inventory, design, traceability, verification and blockers.
---

# Employee Leave Management (ELM)

**Status: draft, not production-ready.** This document uses the six original files in `assignment-evidence/Reference_Documents/` as the source of truth. The repository's new-module instructions require ambiguity and architecture conflicts to be surfaced, not guessed away.

## 1. Source inventory

| Artefact | Inventory | Notes |
|---|---:|---|
| Functional requirements | 107 (`SRS-EL-001`–`SRS-EL-107`) | See grouped traceability below |
| Use cases | 16 (`EL-UC-001`–`EL-UC-016`) | Employee, Substitute/Responsibility Holder, Unit Head, Establishment, Sanctioning Authority, Leave Administrator |
| Business rules | 32 indexed rules | `BR-EL-001`–`025`, then `027`–`033`; **`BR-EL-026` is absent** from the provided index/body and is not reconstructed |
| Scheduled functions | 2 | `SF-EL-001` year-end; `SF-EL-002` SLA |
| Workflows | 8 | `WF-EL-01`–`WF-EL-08` |

## 2. Use-case index

| ID | Use case | Primary actor |
|---|---|---|
| `EL-UC-001` | Apply for Leave | Employee |
| `EL-UC-002` | Respond to Substitute Request | Substitute / Responsibility Holder |
| `EL-UC-003` | Unit Head Review | Unit Head |
| `EL-UC-004` | Establishment Review / Routing | Deputy Registrar (Estt.) / configured Establishment role |
| `EL-UC-005` | Final Sanctioning Decision | Dean / Registrar / Director / other configured authority |
| `EL-UC-006` | Modify Pending Request | Employee |
| `EL-UC-007` | Withdraw Pending Request | Employee |
| `EL-UC-008` | Request Cancellation of Approved Leave | Employee |
| `EL-UC-009` | Submit Leave Extension | Employee |
| `EL-UC-010` | Submit Resumption of Duty | Employee |
| `EL-UC-011` | Verify Resumption | Unit Head / authorized Establishment role |
| `EL-UC-012` | View Leave Balance and History | Employee |
| `EL-UC-013` | Obtain Printable Leave Application | Employee |
| `EL-UC-014` | Maintain Leave Policy Parameters | Leave Administrator |
| `EL-UC-015` | Maintain Holiday and RH Calendar | Leave Administrator |
| `EL-UC-016` | Record Offline-Sanctioned Leave | Leave Administrator |

## 3. Requirement traceability

| Requirement IDs | Capability in source | Current implementation status |
|---|---|---|
| `SRS-EL-001`–`005` | Request submission, categories, required details, coupled Station Leave | Request model/create API exists; responsibility coverage and Station Leave semantics incomplete |
| `SRS-EL-006`–`008`, `035` | Effective policy eligibility, balance, counting and calendar | Basic published policy/calendar lookup and calculation; full policy model needs confirmation |
| `SRS-EL-009`–`018` | CL/RH/SCL entitlement, half-day CL and lapse | Baseline values/counting exist; annual year-end lapse is not implemented |
| `SRS-EL-019`–`026` | EL credit/carry-forward, faculty VL and VL→EL conversion | Partial balance only; annual credits and conversion not implemented |
| `SRS-EL-027`–`030` | COL balance/carry-forward and medical evidence | Evidence reference and configurable check exist; safe file handling/carry-forward incomplete |
| `SRS-EL-031`–`034` | Continuous counting, overlap, CL half-day distinction | Core counting and overlap check exist; edge-case tests incomplete |
| `SRS-EL-036`–`041` | Substitute eligibility, overlap, consent gate and replacement after decline | Nomination/response partial; directory-backed eligibility and replacement flow incomplete |
| `SRS-EL-042`–`054` | Unit Head, Establishment, competent authority, Director exception, ledger posting, notifications | Basic transitions/ledger exist; hierarchy, recommendation semantics, Director rule and notifications incomplete |
| `SRS-EL-055`–`058` | Pending modification, revalidation and superseded tasks | Not implemented |
| `SRS-EL-059`–`063` | Immediate pending withdrawal, task closure and notifications | Withdrawal/task closure partial; notifications and race tests incomplete |
| `SRS-EL-064`–`069` | Pre-start cancellation, same hierarchy, reversal, fresh application | Linked cancellation request partial; full routing/reversal tests incomplete |
| `SRS-EL-070`–`076` | Separate ongoing EL/COL/VL extension | Linked extension request partial; full workflow tests incomplete |
| `SRS-EL-077`–`081` | Resumption and early return, actual date and verification | Linked resumption and unused-day restoration partial; verification rules incomplete |
| `SRS-EL-082`–`087` | Balance/history and printable representation | Balance and history endpoints exist; printable/exportable application missing |
| `SRS-EL-088`–`093` | Printable application, policy/calendar administration and publication | Policy/calendar CRUD/publish endpoints exist; immutable publication validation incomplete |
| `SRS-EL-094`–`097` | Offline-sanctioned leave and evidence | Not implemented |
| `SRS-EL-098`–`101` | Year-end lapse/conversion/carry-forward and exceptions | Scheduled placeholder reports blocker; actual processing not implemented |
| `SRS-EL-102`–`107` | SLA reminders/escalation and audit | Escalation timestamp only; reminder delivery, configured thresholds and audit incomplete |

## 4. Business-rule inventory

`BR-EL-001` eligibility; `002` CL entitlement/lapse; `003` RH entitlement/calendar/lapse; `004` SCL entitlement/admissibility/lapse; `005` staff EL credit/carry-forward; `006` faculty VL entitlement/vacation; `007` VL-to-EL conversion; `008` faculty EL use/carry-forward; `009` COL credit/carry-forward; `010` half-day CL; `011` continuing leave counting; `012` non-overlap; `013` Station Leave coupling; `014` substitute eligibility; `015` substitute consent gate; `016` Unit Head final scope; `017` Unit Head recommendation for higher-sanction leave; `018` higher sanction; `019` authority resolution; `020` Director self-sanction; `021` pending modification; `022` immediate withdrawal; `023` approved-leave cancellation; `024` fresh application after cancellation; `025` ongoing leave extension; `027` resumption requirement; `028` early resumption; `029` offline-sanctioned leave recording; `030` effective policy version; `031` effective holiday/RH calendar; `032` SLA reminder; `033` SLA escalation.

## 5. Workflow inventory

| Workflow | Purpose | Status |
|---|---|---|
| `WF-EL-01` | Apply and decide leave | Partial state machine/API |
| `WF-EL-02` | Modify or withdraw pending request | Withdrawal partial; modification missing |
| `WF-EL-03` | Cancel approved leave before start | Linked cancellation partial |
| `WF-EL-04` | Extend ongoing leave | Linked extension partial |
| `WF-EL-05` | Resume duty / early return | Linked resumption partial |
| `WF-EL-06` | Record offline-sanctioned leave | Missing |
| `WF-EL-07` | Scheduled year-end processing | Blocked pending entitlement and directory integration |
| `WF-EL-08` | SLA reminder and escalation | Escalation placeholder; reminder delivery incomplete |

## 6. Architecture

- Django REST Framework API under `/api/v1/elm/`; React routes under `/elm`.
- ELM owns request, policy, calendar, task, ledger, audit and year-end-run tables.
- Institute identities are plain integer `user_id` references. The only foreign key outside a simple user id is `LeaveRequest.parent_request`, which points to the same ELM model.
- Pure-Python domain code handles date counting and state transitions. Selectors scope reads; services own transactional writes.
- Requests snapshot policy/calendar version IDs. Ledger writes use unique idempotency keys.
- Celery schedule declares both source scheduled functions, but year-end processing explicitly reports a blocker rather than pretending it completed.

## 7. Draft API surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/elm/requests` | GET/POST | List visible requests / submit leave |
| `/api/v1/elm/requests/{id}` | GET/PATCH | Scoped request detail / pending request modification |
| `/api/v1/elm/requests/{id}/transition` | POST | Permission-gated transition |
| `/api/v1/elm/requests/{id}/related` | POST | Linked cancellation/extension/resumption |
| `/api/v1/elm/requests/{id}/substitute-response` | POST | Accept/decline substitute task |
| `/api/v1/elm/requests/{id}/history` | GET | Audit history |
| `/api/v1/elm/balances/me` | GET | Own balance projection |
| `/api/v1/elm/tasks/me` | GET | Tasks assigned to user/role |
| `/api/v1/elm/policies` | GET/POST | Policy versions |
| `/api/v1/elm/policies/{id}/publish` | POST | Publish policy version |
| `/api/v1/elm/calendars` | GET/POST | Calendar versions |
| `/api/v1/elm/calendars/{id}/publish` | POST | Publish calendar version |

## 8. Blocking questions

1. **IAM role mapping:** exact `globals_designation` names for Employee, Substitute/Responsibility Holder, Unit Head, Deputy Registrar (Estt.), Dean, Registrar, Director and Leave Administrator are not established by the checked-in registry evidence. `ROLE_GRANTS` is therefore empty and module status remains `draft`. Do not activate ELM until this is resolved.
2. **Directory contract:** approved contract to validate active employees/substitutes and resolve Unit Head, unit, designation and faculty/staff kind is missing. No cross-module table join or FK may be added.
3. **Authority hierarchy:** exact routing schema, Director self-sanction path, Establishment checks, and distinction between recommendation and final sanction need confirmation.
4. **Entitlements:** annual credit timing, faculty EL opening balance, COL carry-forward limits and VL→EL fractional rounding need exact policy confirmation.
5. **Calendar semantics:** expected JSON representation for holidays, RH dates and vacation periods, and exact SCL non-continuous counting need confirmation from source rules.
6. **Notifications/SLA:** delivery mechanism, recipients, thresholds, escalation authority and idempotency need confirmation.
7. **Evidence:** approved secure upload/storage/scanning contract for medical evidence and offline sanction documents is not wired in.
8. **Offline processing:** sanction evidence fields, backdating, duplicate detection and reconciliation behavior remain unspecified in implementation.

## 9. Verification status

- Pure-domain tests have been added for date counting and workflow transitions.
- Full repository checks have **not** run in this build environment: Django and project dependencies are absent, and package-index access failed.
- On the user's Mac, run `make check`, `make check-client`, migration consistency, `make schema`, permission-manifest checks, navigation parity, import-linter, no-cross-module-FK checks, and end-to-end tests.
- Static permission coverage has been added, but the actual IAM designation labels are not verified in the environment. The proposed role grants must be checked against `globals_designation`; other unimplemented use cases also prevent production readiness.
- Do not commit/push/submit as production-ready until all requirements and the repository Definition of Done pass.


## Appendix A — Complete functional-requirement register

Statements below are transcribed from `01_Source_Functional_Requirements.docx`; status is an implementation assessment, not a source requirement.

| ID | Source requirement statement | Draft status |
|---|---|---|
| `SRS-EL-001` | The system shall allow an eligible employee to create and submit a leave request. | Partial: request schema/API; coupled behavior incomplete |
| `SRS-EL-002` | The system shall support CL, RH, SCL, EL, COL and VL within the study scope. | Partial: request schema/API; coupled behavior incomplete |
| `SRS-EL-003` | The system shall capture leave category, requested period, purpose/reason and other required information in a leave application. | Partial: request schema/API; coupled behavior incomplete |
| `SRS-EL-004` | The system shall capture Station Leave details within the same leave application when applicable. | Partial: request schema/API; coupled behavior incomplete |
| `SRS-EL-005` | The system shall treat Station Leave for outside-Jabalpur absence as information coupled to the associated leave application rather than as a separate leave-request process. | Partial: request schema/API; coupled behavior incomplete |
| `SRS-EL-006` | The system shall validate requested leave-category eligibility using the currently effective published policy. | Partial: effective config/validation exists; policy completeness pending |
| `SRS-EL-007` | The system shall validate available leave entitlement/balance before a request is submitted or modified. | Partial: effective config/validation exists; policy completeness pending |
| `SRS-EL-008` | The system shall calculate chargeable leave days using the applicable leave-counting rule and effective calendar. | Partial: effective config/validation exists; policy completeness pending |
| `SRS-EL-009` | The system shall maintain an annual CL entitlement of 8 days for each employee. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-010` | The system shall lapse unused CL at year end and shall not carry it forward. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-011` | The system shall support first-half and second-half CL. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-012` | The system shall deduct 0.5 CL day for an approved half-day CL. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-013` | The system shall maintain an annual RH entitlement of 2 days for each employee. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-014` | The system shall validate an RH request against the applicable published Restricted Holiday calendar. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-015` | The system shall lapse unused RH at year end and shall not carry it forward. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-016` | The system shall support up to 15 SCL days per calendar year for each employee for an admissible special purpose. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-017` | The system shall use the competent authority’s admissibility decision when processing SCL. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-018` | The system shall lapse unused SCL at year end and shall not carry it forward. | Partial: counting/baseline only; year-end lapse pending |
| `SRS-EL-019` | The system shall maintain an annual EL credit of 30 days for each non-faculty employee. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-020` | The system shall carry forward unused EL according to policy. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-021` | The system shall maintain 60 VL for each faculty member associated with published vacation periods. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-022` | The system shall allow VL to be availed only during an applicable published vacation period. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-023` | The system shall convert all unused faculty VL to EL at year end at a ratio of 2 VL to 1 EL. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-024` | The system shall support fractional VL-to-EL conversion at year end. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-025` | The system shall not carry forward VL after the year-end VL-to-EL conversion. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-026` | The system shall credit EL generated by VL conversion to the faculty member’s EL balance, carry it forward, and permit subsequent use. | Incomplete: annual credit/carry-forward/conversion |
| `SRS-EL-027` | The system shall maintain an annual COL entitlement of 20 days for each eligible employee in the study baseline. | Partial: evidence reference only; storage/carry-forward pending |
| `SRS-EL-028` | The system shall carry forward unused COL according to policy. | Partial: evidence reference only; storage/carry-forward pending |
| `SRS-EL-029` | The system shall treat COL as medical/balance-controlled leave. | Partial: evidence reference only; storage/carry-forward pending |
| `SRS-EL-030` | The system shall support a requirement for supporting medical evidence for COL where applicable. | Partial: evidence reference only; storage/carry-forward pending |
| `SRS-EL-031` | The system shall count intervening weekends and closed holidays inside a continuous EL, COL or VL interval as leave days. | Partial: counting/overlap; edge tests pending |
| `SRS-EL-032` | The system shall not apply the continuous-day counting rule to CL, SCL or RH. | Partial: counting/overlap; edge tests pending |
| `SRS-EL-033` | The system shall detect and prevent impermissible overlap between a new or modified request and the employee’s active pending or approved leave. | Partial: counting/overlap; edge tests pending |
| `SRS-EL-034` | The system shall treat first-half and second-half CL on the same date as non-overlapping when they occupy different halves. | Partial: counting/overlap; edge tests pending |
| `SRS-EL-035` | The system shall use the currently effective published holiday/RH calendar for date and RH validations. | Partial: effective config/validation exists; policy completeness pending |
| `SRS-EL-036` | The system shall allow an employee to nominate one substitute when responsibility coverage is required. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-037` | The system shall reject a substitute nomination if the nominee is not another employee or is the applicant. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-038` | The system shall reject a substitute nomination when the nominee has overlapping pending or approved leave during the responsibility period. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-039` | The system shall allow the nominated substitute to accept or decline the assignment. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-040` | The system shall prevent approval routing until required substitute consent is accepted. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-041` | The system shall allow the applicant to nominate another eligible substitute or withdraw after a required substitute declines. | Partial: substitute gate; directory validation/replacement pending |
| `SRS-EL-042` | The system shall route a submitted request to the applicant’s Unit Head except where the Director-specific self-sanction rule governs the request. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-043` | The system shall treat the Unit Head as final sanctioning authority for CL and RH, including associated Station Leave. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-044` | The system shall allow the Unit Head to approve or reject CL and RH within Unit Head authority. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-045` | The system shall allow the Unit Head to record Recommended or Not Recommended for SCL, EL, COL and VL. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-046` | The system shall not treat the Unit Head’s Not Recommended decision as the final rejection of SCL, EL, COL or VL. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-047` | The system shall route SCL, EL, COL and VL after Unit Head review through the configured hierarchy to the appropriate final Sanctioning Authority. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-048` | The system shall resolve the processing/sanctioning path from the applicant, organizational unit, designation/role, leave category and effective hierarchy configuration. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-049` | The system shall support configured processing/sanctioning paths that may include Deputy Registrar (Estt.), Dean, Registrar and Director. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-050` | The system shall support configured Establishment-level verification/routing before forwarding higher-sanction leave to the resolved competent authority. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-051` | The system shall allow the final Sanctioning Authority to approve or reject a routed higher-sanction request. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-052` | The system shall apply the Director-specific self-sanction rule when the Director is the applicant. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-053` | The system shall update the employee’s leave record/account after final approval. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-054` | The system shall notify concerned participants about relevant leave-request status changes and decisions. | Partial: transition/ledger; hierarchy and notifications pending |
| `SRS-EL-055` | The system shall allow a pending request to be modified only before final approval and while its current status permits modification. | Partial: modification endpoint exists; complete workflow/task semantics pending |
| `SRS-EL-056` | The system shall revalidate an eligible pending request after modification. | Partial: modification endpoint exists; complete workflow/task semantics pending |
| `SRS-EL-057` | The system shall supersede obsolete substitute, review or sanction tasks when a pending request is materially modified. | Partial: modification endpoint exists; complete workflow/task semantics pending |
| `SRS-EL-058` | The system shall obtain any newly required substitute consent and reroute a modified request from the appropriate point in the effective approval path. | Partial: modification endpoint exists; complete workflow/task semantics pending |
| `SRS-EL-059` | The system shall allow an employee to withdraw a pending request at any time before final approval and shall make the withdrawal effective immediately. | Partial: withdrawal/task closure; notifications/race tests pending |
| `SRS-EL-060` | The system shall close or cancel pending workflow tasks when a request is withdrawn. | Partial: withdrawal/task closure; notifications/race tests pending |
| `SRS-EL-061` | The system shall inform concerned users/roles when a pending request is withdrawn. | Partial: withdrawal/task closure; notifications/race tests pending |
| `SRS-EL-062` | The system shall prevent later approval or rejection actions on a withdrawn request. | Partial: withdrawal/task closure; notifications/race tests pending |
| `SRS-EL-063` | The system shall disallow withdrawal after final approval and shall use the approved-leave cancellation process where applicable. | Partial: withdrawal/task closure; notifications/race tests pending |
| `SRS-EL-064` | The system shall allow cancellation of an approved leave only before the approved leave begins. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-065` | The system shall route an approved-leave cancellation through the same hierarchy applicable to the original leave. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-066` | The system shall reverse or adjust the original approved leave effect and mark the leave cancelled when cancellation is finally approved. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-067` | The system shall preserve the original approved leave when a cancellation request is rejected. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-068` | The system shall require a fresh leave application when revised leave is needed after cancellation and shall not edit the approved leave in place. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-069` | The system shall direct post-start leave changes to the applicable extension or resumption process rather than pre-start cancellation. | Partial: linked cancellation request; full routing/reversal pending |
| `SRS-EL-070` | The system shall allow an employee on ongoing EL, COL or VL to submit a separate extension request for additional leave time. | Partial: linked extension request; full workflow pending |
| `SRS-EL-071` | The system shall limit the defined extension capability in the study baseline to ongoing EL, COL and VL. | Partial: linked extension request; full workflow pending |
| `SRS-EL-072` | The system shall validate and route an extension using the applicable eligibility, balance, substitute, calendar and approval rules. | Partial: linked extension request; full workflow pending |
| `SRS-EL-073` | The system shall obtain required substitute consent for an extension before approval routing proceeds. | Partial: linked extension request; full workflow pending |
| `SRS-EL-074` | The system shall route a valid extension through the applicable Unit Head and configured higher-sanction path. | Partial: linked extension request; full workflow pending |
| `SRS-EL-075` | The system shall post only the incremental additional leave period when an extension is approved. | Partial: linked extension request; full workflow pending |
| `SRS-EL-076` | The system shall leave the original approved leave unchanged when an extension request is rejected. | Partial: linked extension request; full workflow pending |
| `SRS-EL-077` | The system shall allow an employee to submit resumption of duty after EL, COL or VL. | Partial: linked resumption/early restoration; verification pending |
| `SRS-EL-078` | The system shall support early resumption before the approved end date for EL, COL and VL. | Partial: linked resumption/early restoration; verification pending |
| `SRS-EL-079` | The system shall capture the employee’s actual resumption date and required resumption details. | Partial: linked resumption/early restoration; verification pending |
| `SRS-EL-080` | The system shall route submitted resumption information through the configured verification path. | Partial: linked resumption/early restoration; verification pending |
| `SRS-EL-081` | The system shall allow the authorized verifier to verify actual return to duty. | Partial: linked resumption/early restoration; verification pending |
| `SRS-EL-082` | The system shall record the actual leave period after resumption is verified. | Partial: balance/history exists; printable output pending |
| `SRS-EL-083` | The system shall restore unused approved EL/COL/VL after verified early resumption. | Partial: balance/history exists; printable output pending |
| `SRS-EL-084` | The system shall synchronize leave and attendance records after verified resumption. | Partial: balance/history exists; printable output pending |
| `SRS-EL-085` | The system shall close the leave after verified resumption and record synchronization. | Partial: balance/history exists; printable output pending |
| `SRS-EL-086` | The system shall not restore unused approved leave for early resumption until the return is verified. | Partial: balance/history exists; printable output pending |
| `SRS-EL-087` | The system shall display an employee’s current leave balances and leave-account history. | Partial: balance/history exists; printable output pending |
| `SRS-EL-088` | The system shall provide a printable/exportable representation of a leave application accessible to the employee. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-089` | The system shall allow authorized administrators to create, revise and publish leave-policy parameters. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-090` | The system shall use the currently effective published policy/hierarchy parameters for validation and routing. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-091` | The system shall continue using the currently effective published policy until a replacement is validly published. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-092` | The system shall allow authorized administrators to create, revise and publish the holiday/RH calendar. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-093` | The system shall continue using the currently effective published holiday/RH calendar until a replacement is published. | Partial: policy/calendar CRUD exists; publication/version controls pending |
| `SRS-EL-094` | The system shall allow an authorized Leave Administrator to retrospectively record leave already sanctioned through an authorized offline/paper process. | Not implemented: offline-sanctioned record synchronization |
| `SRS-EL-095` | The system shall treat retrospective offline-sanctioned leave entry as record synchronization rather than a second approval. | Not implemented: offline-sanctioned record synchronization |
| `SRS-EL-096` | The system shall record sanction/reference evidence for each offline-sanctioned leave entry. | Not implemented: offline-sanctioned record synchronization |
| `SRS-EL-097` | The system shall validate an offline-sanctioned leave entry for record consistency and update the relevant leave balance/history. | Not implemented: offline-sanctioned record synchronization |
| `SRS-EL-098` | The system shall perform year-end lapse of unused CL, RH and SCL. | Blocked: year-end processing not implemented |
| `SRS-EL-099` | The system shall perform the defined year-end faculty VL-to-EL conversion. | Blocked: year-end processing not implemented |
| `SRS-EL-100` | The system shall carry forward EL and COL according to policy at year end. | Blocked: year-end processing not implemented |
| `SRS-EL-101` | The system shall record resulting leave-account transactions and report exceptions during year-end processing. | Blocked: year-end processing not implemented |
| `SRS-EL-102` | The system shall support configurable reminder and escalation thresholds for SLA-controlled actionable workflow tasks. | Partial: escalation timestamp only; reminder delivery/audit pending |
| `SRS-EL-103` | The system shall identify SLA-controlled pending tasks at configured reminder thresholds. | Partial: escalation timestamp only; reminder delivery/audit pending |
| `SRS-EL-104` | The system shall remind the responsible user when an SLA-controlled task remains pending at its reminder threshold. | Partial: escalation timestamp only; reminder delivery/audit pending |
| `SRS-EL-105` | The system shall notify or escalate to the configured higher/responsible authority when an SLA-controlled task remains pending past its escalation threshold. | Partial: escalation timestamp only; reminder delivery/audit pending |
| `SRS-EL-106` | The system shall log SLA reminder and escalation actions. | Partial: escalation timestamp only; reminder delivery/audit pending |
| `SRS-EL-107` | The system shall not issue the corresponding SLA reminder or escalation for a task that is no longer pending when the threshold is reached. | Partial: escalation timestamp only; reminder delivery/audit pending |
