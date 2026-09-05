---
owner: leave-lead
status: generated
last-reviewed: 2026-09-02
---

# Employee Leave Management — the rules, and where each one lives

Every business rule and use case from the ELM specification, what it means in a
sentence, and a link straight to the line of code that decides it.

Built for teaching. Read a rule, click the arrow, land on the function that
enforces it.

> **This page is generated.** Run `python ops/docs/build_elm_reference.py` after
> moving code. The rule statements are read from the `.docx` specifications and
> the line numbers from the source tree, so neither can drift by hand — and
> a line number edited by hand is how a reference stops being trustworthy.

**Source documents** — the six files this is drawn from live in
[`ELM/`](../../../ELM/README.md). This page is the reading order; those are the
contract.

| | |
|---|---|
| Business rules | **32** defined, **31** implemented |
| Use cases | **16** defined, **15** implemented |
| Scheduled functions | **2** |
| Workflows | 12 basis + 5 composite |
| States / transitions | 23 states, 46 transitions, 4 terminal |
| Tables | 12, with 12 database check constraints |

---

## The journey of one request


```
                      ┌─ substitute declines ─→ renominate (EL-UC-006)
                      │                         or withdraw  (EL-UC-007)
   apply              ▼
 EL-UC-001 ──→ substitute consent ──→ unit head ──┬─→ APPROVED   (CL, RH)
               EL-UC-002              EL-UC-003   │   BR-EL-016
               BR-EL-014/015          BR-EL-017   │
                                                  └─→ establishment ──→ sanction
                                                      EL-UC-004         EL-UC-005
                                                      BR-EL-018         BR-EL-019/020
                                                                             │
   ┌─────────────────────────────────────────────────────────────────────────┘
   ▼         (the only point a balance moves)
 APPROVED ──[clock]──→ ONGOING ──[clock]──→ resumption ──→ verified ──→ CLOSED
                          │                  EL-UC-010     EL-UC-011
                          │                                BR-EL-027/028
                          ├─→ cancel  EL-UC-008  BR-EL-023
                          └─→ extend  EL-UC-009  BR-EL-025
```


Two things on that diagram are worth pausing on when teaching:

- **The balance moves once**, at final sanction. Nothing is held while a request
  is pending, which is why a withdrawal needs no reversal — and why two
  separately affordable requests have to be re-checked against each other at
  approval.
- **`[clock]` is not a person.** Leave starting, and reaching its end, are the
  passage of time. If nothing runs that clock, approved leave never becomes
  ongoing, stays cancellable after the employee has gone, and can never be
  extended or closed.

---

## Use cases

Who does what, and why it exists.

| Use case | Actor | What it is | Code |
|---|---|---|---|
| **EL-UC-001**<br>Apply for Leave | Employee | The entry point. Everything the policy has to say about eligibility, counting and overlap is checked here, once, before anything is written. | [`services/requests.py:199`](../../modules/leave/services/requests.py#L199) [↗](../../modules/leave/services/requests.py#L199)<br>[`domain/state_machine.py:96`](../../modules/leave/domain/state_machine.py#L96)<br>[`domain/state_machine.py:100`](../../modules/leave/domain/state_machine.py#L100)<br><sub>4 citations in all</sub> |
| **EL-UC-002**<br>Respond to Substitute Request | Substitute | The nominated substitute accepts or declines. Routing waits on this. | [`services/decisions.py:109`](../../modules/leave/services/decisions.py#L109) [↗](../../modules/leave/services/decisions.py#L109)<br>[`domain/state_machine.py:108`](../../modules/leave/domain/state_machine.py#L108)<br>[`domain/state_machine.py:112`](../../modules/leave/domain/state_machine.py#L112)<br><sub>5 citations in all</sub> |
| **EL-UC-003**<br>Unit Head Review | Unit Head | The unit head's step: a decision for CL and RH, a recommendation for everything else. | [`services/decisions.py:140`](../../modules/leave/services/decisions.py#L140) [↗](../../modules/leave/services/decisions.py#L140)<br>[`domain/state_machine.py:126`](../../modules/leave/domain/state_machine.py#L126)<br>[`domain/state_machine.py:130`](../../modules/leave/domain/state_machine.py#L130)<br><sub>7 citations in all</sub> |
| **EL-UC-004**<br>Establishment Review / Routing | Deputy Registrar (Estt.) / configured Establishment role | The establishment section forwards a recommended request to the competent authority. It routes; it does not decide. | [`services/decisions.py:182`](../../modules/leave/services/decisions.py#L182) [↗](../../modules/leave/services/decisions.py#L182)<br>[`domain/state_machine.py:142`](../../modules/leave/domain/state_machine.py#L142)<br>[`domain/state_machine.py:207`](../../modules/leave/domain/state_machine.py#L207)<br><sub>4 citations in all</sub> |
| **EL-UC-005**<br>Final Sanctioning Decision | Dean / Registrar / Director / other configured competent authority | The final decision, and the only point at which a balance moves. | [`services/decisions.py:200`](../../modules/leave/services/decisions.py#L200) [↗](../../modules/leave/services/decisions.py#L200)<br>[`domain/state_machine.py:146`](../../modules/leave/domain/state_machine.py#L146)<br>[`domain/state_machine.py:150`](../../modules/leave/domain/state_machine.py#L150)<br><sub>9 citations in all</sub> |
| **EL-UC-006**<br>Modify Pending Request | Employee | A fresh substitute after the first declined, so a request is not lost to one person's unavailability. | [`services/decisions.py:262`](../../modules/leave/services/decisions.py#L262) [↗](../../modules/leave/services/decisions.py#L262)<br>[`api/views.py:160`](../../modules/leave/api/views.py#L160)<br>[`domain/state_machine.py:116`](../../modules/leave/domain/state_machine.py#L116)<br><sub>4 citations in all</sub> |
| **EL-UC-007**<br>Withdraw Pending Request | Employee | Withdrawing a request that has not yet been approved. | [`services/decisions.py:251`](../../modules/leave/services/decisions.py#L251) [↗](../../modules/leave/services/decisions.py#L251)<br>[`domain/state_machine.py:120`](../../modules/leave/domain/state_machine.py#L120)<br>[`domain/state_machine.py:165`](../../modules/leave/domain/state_machine.py#L165)<br><sub>8 citations in all</sub> |
| **EL-UC-008**<br>Request Cancellation of Approved Leave | Employee | Asking to cancel leave that has already been granted — a request, not an action. | [`domain/state_machine.py:187`](../../modules/leave/domain/state_machine.py#L187) [↗](../../modules/leave/domain/state_machine.py#L187)<br>[`domain/state_machine.py:191`](../../modules/leave/domain/state_machine.py#L191)<br>[`domain/state_machine.py:195`](../../modules/leave/domain/state_machine.py#L195)<br><sub>5 citations in all</sub> |
| **EL-UC-009**<br>Submit Leave Extension | Employee | Extending leave while it runs. Only the incremental days are charged. | [`domain/state_machine.py:225`](../../modules/leave/domain/state_machine.py#L225) [↗](../../modules/leave/domain/state_machine.py#L225)<br>[`domain/state_machine.py:229`](../../modules/leave/domain/state_machine.py#L229) |
| **EL-UC-010**<br>Submit Resumption of Duty | Employee | Reporting the return to duty. The date is the first day back, not the last day of leave. | [`services/lifecycle.py:336`](../../modules/leave/services/lifecycle.py#L336) [↗](../../modules/leave/services/lifecycle.py#L336)<br>[`domain/state_machine.py:221`](../../modules/leave/domain/state_machine.py#L221)<br>[`domain/state_machine.py:279`](../../modules/leave/domain/state_machine.py#L279)<br><sub>5 citations in all</sub> |
| **EL-UC-011**<br>Verify Resumption | Unit Head / authorized Establishment role according to hierarchy | The establishment verifies the reported resumption, which is what closes the request and restores any unused days. | [`domain/state_machine.py:291`](../../modules/leave/domain/state_machine.py#L291) [↗](../../modules/leave/domain/state_machine.py#L291)<br>[`domain/state_machine.py:295`](../../modules/leave/domain/state_machine.py#L295) |
| **EL-UC-012**<br>View Leave Balance and History | Employee | Seeing your own balance and history — and the entries behind the figure, not just the figure. | [`selectors/balances.py:78`](../../modules/leave/selectors/balances.py#L78) [↗](../../modules/leave/selectors/balances.py#L78) |
| **EL-UC-013**<br>Obtain Printable Leave Application | Employee | A printable application. **Not implemented** — see the gaps section. | *not in code* — |
| **EL-UC-014**<br>Maintain Leave Policy Parameters | Leave Administrator | Maintaining the entitlement figures and the counting rules, as a new policy version. | [`services/administration.py:42`](../../modules/leave/services/administration.py#L42) [↗](../../modules/leave/services/administration.py#L42) |
| **EL-UC-015**<br>Maintain Holiday and RH Calendar | Leave Administrator | Maintaining the holidays, restricted holidays and vacation periods. | [`services/administration.py:160`](../../modules/leave/services/administration.py#L160) [↗](../../modules/leave/services/administration.py#L160) |
| **EL-UC-016**<br>Record Offline-Sanctioned Leave | Leave Administrator | Recording leave sanctioned outside the system. Deliberately not a workflow — it is bookkeeping, not approval. | [`services/administration.py:312`](../../modules/leave/services/administration.py#L312) [↗](../../modules/leave/services/administration.py#L312)<br>[`domain/state_machine.py:76`](../../modules/leave/domain/state_machine.py#L76)<br>[`models/policy.py:35`](../../modules/leave/models/policy.py#L35) |

### Scheduled functions

Not use cases: nobody triggers these. They are what the system does because
time passed.

| Function | What it does | Rules | Code |
|---|---|---|---|
| **SF-EL-001**<br>Scheduled Year-End Leave Processing | Closes a leave year: lapse what does not carry, convert unused vacation leave, carry the rest forward. Idempotent per employee and year, and --dry-run rehearses it inside a rolled-back transaction. | BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005 … | [`services/yearend.py:3`](../../modules/leave/services/yearend.py#L3) [↗](../../modules/leave/services/yearend.py#L3)<br>[`domain/entitlement.py:100`](../../modules/leave/domain/entitlement.py#L100)<br>[`management/commands/leave_year_end.py:1`](../../modules/leave/management/commands/leave_year_end.py#L1) |
| **SF-EL-002**<br>Scheduled SLA Processing | Reminds, then escalates, whoever a request is waiting on. A clock already reminded is not reminded again. | BR-EL-032, BR-EL-033 | [`services/sla.py:1`](../../modules/leave/services/sla.py#L1) [↗](../../modules/leave/services/sla.py#L1)<br>[`management/commands/leave_sla.py:1`](../../modules/leave/management/commands/leave_sla.py#L1) |

---

## Business rules

### Entitlement — how many days exist

What each category grants, whether it survives the year, and how vacation leave becomes earned leave. Every figure here is a database row, not a constant.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-001**<br>Leave Category Eligibility | Employees may request only leave categories for which they are eligible under the effective ELM policy. | The policy, not the code, decides which categories reach which employee. A staff member cannot request faculty-only vacation leave even holding a balance. | [`domain/entitlement.py:61`](../../modules/leave/domain/entitlement.py#L61) [↗](../../modules/leave/domain/entitlement.py#L61)<br>[`services/requests.py:121`](../../modules/leave/services/requests.py#L121)<br>[`models/request.py:25`](../../modules/leave/models/request.py#L25)<br><sub>6 citations in all</sub> |
| **BR-EL-002**<br>CL Entitlement | Each employee receives 8 CL per calendar year. Unused CL lapses at year end. | Casual leave is a flat 8 a year and does not survive December. Nothing carries, so the year-end simply lapses whatever is left. | [`domain/entitlement.py:66`](../../modules/leave/domain/entitlement.py#L66) [↗](../../modules/leave/domain/entitlement.py#L66)<br>[`management/commands/seed_leave_policy.py:5`](../../modules/leave/management/commands/seed_leave_policy.py#L5)<br>[`management/commands/seed_leave_policy.py:27`](../../modules/leave/management/commands/seed_leave_policy.py#L27)<br><sub>5 citations in all</sub> |
| **BR-EL-003**<br>RH Entitlement | Each employee receives 2 RH per calendar year. Unused RH lapses at year end. RH must correspond to an applicable published Restricted Holiday. | Restricted holidays are 2 a year and must name a date the calendar published. Choosing an arbitrary day is refused at submission. | [`domain/categories.py:34`](../../modules/leave/domain/categories.py#L34) [↗](../../modules/leave/domain/categories.py#L34)<br>[`models/calendar.py:40`](../../modules/leave/models/calendar.py#L40)<br>[`selectors/policy.py:71`](../../modules/leave/selectors/policy.py#L71)<br><sub>4 citations in all</sub> |
| **BR-EL-004**<br>SCL Entitlement | Each employee may receive up to 15 SCL days per calendar year for an admissible special purpose. Unused SCL does not carry forward. Admissibility is decided by the competent authority. | Up to 15 special casual leave a year for an admissible purpose. Admissibility is a human judgement, so the module enforces the ceiling and leaves the decision to the authority. | [`management/commands/seed_leave_policy.py:27`](../../modules/leave/management/commands/seed_leave_policy.py#L27) [↗](../../modules/leave/management/commands/seed_leave_policy.py#L27) |
| **BR-EL-005**<br>Staff EL Credit | Each non-faculty employee receives 30 EL per year. Unused EL carries forward. | Non-faculty earn 30 a year and unused days carry forward, which is why EL is the category the year-end has to think hardest about. | [`management/commands/seed_leave_policy.py:27`](../../modules/leave/management/commands/seed_leave_policy.py#L27) [↗](../../modules/leave/management/commands/seed_leave_policy.py#L27) |
| **BR-EL-006**<br>Faculty Vacation Leave | Each faculty member receives 60 VL associated with published vacation periods in the academic calendar. VL may be availed only during an applicable vacation period. | Faculty get vacation leave instead of earned leave, and it must fall inside a published vacation period. | [`domain/categories.py:37`](../../modules/leave/domain/categories.py#L37) [↗](../../modules/leave/domain/categories.py#L37)<br>[`models/calendar.py:59`](../../modules/leave/models/calendar.py#L59)<br>[`management/commands/seed_leave_policy.py:28`](../../modules/leave/management/commands/seed_leave_policy.py#L28) |
| **BR-EL-007**<br>VL to EL Conversion | At year end, all unused faculty VL is converted to EL at 2 VL : 1 EL. Fractional conversion is permitted. VL does not carry forward after conversion. | Unused vacation leave converts to earned leave at the policy's ratio. Neither the ratio nor the rounding is hardcoded — a test passes 3:1 to prove it. | [`domain/entitlement.py:9`](../../modules/leave/domain/entitlement.py#L9) [↗](../../modules/leave/domain/entitlement.py#L9)<br>[`domain/entitlement.py:81`](../../modules/leave/domain/entitlement.py#L81)<br>[`domain/entitlement.py:100`](../../modules/leave/domain/entitlement.py#L100)<br><sub>7 citations in all</sub> |
| **BR-EL-008**<br>Faculty EL Use | EL generated through VL conversion is credited to the faculty member's EL balance, carries forward, and may subsequently be availed. | Converted days are ordinary earned leave: same balance, carries forward, available to take. | [`domain/entitlement.py:74`](../../modules/leave/domain/entitlement.py#L74) [↗](../../modules/leave/domain/entitlement.py#L74) |
| **BR-EL-009**<br>COL Credit and Carry-Forward | Each eligible employee receives 20 COL days per year in the canonical case. Unused COL carries forward. COL is treated as medical/balance-controlled leave and may require supporting medical evidence. | Commuted leave is 20 a year and carries forward. | [`domain/entitlement.py:66`](../../modules/leave/domain/entitlement.py#L66) [↗](../../modules/leave/domain/entitlement.py#L66)<br>[`management/commands/seed_leave_policy.py:5`](../../modules/leave/management/commands/seed_leave_policy.py#L5)<br>[`management/commands/seed_leave_policy.py:28`](../../modules/leave/management/commands/seed_leave_policy.py#L28)<br><sub>5 citations in all</sub> |

### Counting — how many days a request costs

The arithmetic. Read this group before answering a disputed balance.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-010**<br>Half-Day CL | CL may be taken for the first or second half of a day. A half-day CL consumes 0.5 CL day. | Only casual leave may be taken as a half day, and only on a single date. The database enforces the single date, not just the form. | [`domain/categories.py:25`](../../modules/leave/domain/categories.py#L25) [↗](../../modules/leave/domain/categories.py#L25)<br>[`models/request.py:22`](../../modules/leave/models/request.py#L22)<br>[`client/src/pages/ApplyPage.tsx:24`](../../client/src/modules/leave/pages/ApplyPage.tsx#L24)<br><sub>5 citations in all</sub> |
| **BR-EL-011**<br>Continuing Leave Counting | For EL, COL and VL, intervening weekends and closed holidays inside a continuous approved leave interval count as leave days. This rule does not apply to CL, SCL or RH. | The counting rule that is most often got wrong. For EL, COL and VL a weekend inside the leave is charged; for CL, RH and SCL it is not. Monday to Monday is 8 days of EL and 6 of CL. | [`domain/categories.py:22`](../../modules/leave/domain/categories.py#L22) [↗](../../modules/leave/domain/categories.py#L22)<br>[`domain/counting.py:3`](../../modules/leave/domain/counting.py#L3)<br>[`tests/test_counting.py:26`](../../modules/leave/tests/test_counting.py#L26)<br><sub>4 citations in all</sub> |
| **BR-EL-012**<br>Non-Overlap | A new or modified leave request must not overlap impermissibly with another active pending or approved leave for the same employee. Two half-day CL requests on the same date do not overlap if they occupy different halves. | A new request may not overlap leave already held, pending or approved. The one exception is two opposite half days on the same date. | [`domain/overlap.py:3`](../../modules/leave/domain/overlap.py#L3) [↗](../../modules/leave/domain/overlap.py#L3)<br>[`services/requests.py:70`](../../modules/leave/services/requests.py#L70)<br>[`tests/test_overlap.py:13`](../../modules/leave/tests/test_overlap.py#L13)<br><sub>4 citations in all</sub> |
| **BR-EL-013**<br>Station Leave Coupling | Station Leave is captured within the same leave application whenever the employee will be outside Jabalpur. It is not a separate leave-request workflow. | Being away from headquarters travels inside the application rather than beside it, so a request carries its own station details. | [`models/request.py:58`](../../modules/leave/models/request.py#L58) [↗](../../modules/leave/models/request.py#L58)<br>[`models/request.py:96`](../../modules/leave/models/request.py#L96) |

### Substitution — who holds the work

A substitute is required for some leave, and their consent gates the whole route.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-014**<br>Substitute Eligibility | A substitute must be an employee other than the applicant and must not have an overlapping pending or approved leave during the responsibility period. | Where a substitute is required, nothing moves until they answer. The request waits rather than proceeding on an assumption. | [`models/request.py:113`](../../modules/leave/models/request.py#L113) [↗](../../modules/leave/models/request.py#L113) |
| **BR-EL-015**<br>Substitute Consent Gate | Where substitute assignment is required, the request must not proceed to approval routing until the nominated substitute accepts. | A declined nomination returns the request to the applicant, who nominates somebody else or withdraws. | [`services/decisions.py:109`](../../modules/leave/services/decisions.py#L109) [↗](../../modules/leave/services/decisions.py#L109)<br>[`models/request.py:113`](../../modules/leave/models/request.py#L113)<br>[`tests/test_decisions.py:115`](../../modules/leave/tests/test_decisions.py#L115) |

### Authority — who decides

The rules that make the approval path configuration rather than code.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-016**<br>Unit Head Final Scope | For CL and RH, including associated Station Leave, the Unit Head is the final sanctioning authority in the canonical case. | Casual and restricted leave end with the unit head. They are the competent authority for those categories. | [`domain/authority.py:3`](../../modules/leave/domain/authority.py#L3) [↗](../../modules/leave/domain/authority.py#L3)<br>[`domain/categories.py:31`](../../modules/leave/domain/categories.py#L31)<br>[`management/commands/seed_leave_policy.py:40`](../../modules/leave/management/commands/seed_leave_policy.py#L40)<br><sub>6 citations in all</sub> |
| **BR-EL-017**<br>Unit Head Recommendation for Higher-Sanction Leave | For SCL, EL, COL and VL, the Unit Head reviews the request and records Recommended or Not Recommended. The Unit Head does not make the final rejection decision for these leave categories. | For SCL, EL, COL and VL the unit head records Recommended or Not Recommended and routes onward. **They do not make the final rejection.** | [`services/decisions.py:140`](../../modules/leave/services/decisions.py#L140) [↗](../../modules/leave/services/decisions.py#L140)<br>[`services/decisions.py:154`](../../modules/leave/services/decisions.py#L154)<br>[`models/request.py:74`](../../modules/leave/models/request.py#L74)<br><sub>5 citations in all</sub> |
| **BR-EL-018**<br>Higher Sanction | SCL, EL, COL and VL proceed after Unit Head review through the configured hierarchy to the appropriate final Sanctioning Authority. | Those four categories go above the unit head. The category sets the floor; the configuration decides who. | [`domain/authority.py:116`](../../modules/leave/domain/authority.py#L116) [↗](../../modules/leave/domain/authority.py#L116) |
| **BR-EL-019**<br>Authority Resolution | The system resolves the processing/sanctioning path from applicant, organizational unit, designation/role, leave category and the currently effective hierarchy configuration. Named roles may include Deputy Registrar (Estt.), Dean, Registrar and Director; an Establishment processing step occurs where configured. | Who reviews and who sanctions is configuration, not code. A reorganisation is a row, not a deployment. | [`services/administration.py:106`](../../modules/leave/services/administration.py#L106) [↗](../../modules/leave/services/administration.py#L106)<br>[`services/decisions.py:33`](../../modules/leave/services/decisions.py#L33)<br>[`models/request.py:44`](../../modules/leave/models/request.py#L44)<br><sub>8 citations in all</sub> |
| **BR-EL-020**<br>Director Self-Sanction | When the Director is the applicant, the Director-specific self-sanction rule governs the sanctioning path. | When the Director applies, their own leave takes the self-sanction route — the one case where deciding your own request is correct. | [`domain/authority.py:3`](../../modules/leave/domain/authority.py#L3) [↗](../../modules/leave/domain/authority.py#L3)<br>[`domain/state_machine.py:152`](../../modules/leave/domain/state_machine.py#L152)<br>[`services/decisions.py:33`](../../modules/leave/services/decisions.py#L33)<br><sub>12 citations in all</sub> |

### Lifecycle — changing a request after it exists

Withdrawal, cancellation, extension and resumption. The distinction that matters: before approval it is yours to withdraw; after approval it is the authority's to cancel.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-021**<br>Modify Pending Request | A pending request may be modified only before final approval and while its current status permits modification. Modified data must be revalidated and invalidated substitute/approval tasks must be superseded. | A pending request may be modified before final approval, with revalidation and superseded tasks. **Not implemented** — see the gaps section. | *not in code* — |
| **BR-EL-022**<br>Immediate Withdrawal of Pending Request | An employee may withdraw a request at any time before final approval. Withdrawal becomes effective immediately, pending tasks are closed/cancelled, and concerned users/roles are informed. | A pending request may be withdrawn at any point before approval, by the applicant. | [`domain/categories.py:37`](../../modules/leave/domain/categories.py#L37) [↗](../../modules/leave/domain/categories.py#L37)<br>[`domain/state_machine.py:162`](../../modules/leave/domain/state_machine.py#L162)<br>[`services/decisions.py:251`](../../modules/leave/services/decisions.py#L251)<br><sub>4 citations in all</sub> |
| **BR-EL-023**<br>Cancellation of Approved Leave | An approved leave may be cancelled only before the approved leave begins. Cancellation follows the same review/recommendation/sanction hierarchy applicable to the original leave. | Approved leave is cancelled by the authority that granted it, not unilaterally by the applicant. | [`services/lifecycle.py:4`](../../modules/leave/services/lifecycle.py#L4) [↗](../../modules/leave/services/lifecycle.py#L4)<br>[`services/lifecycle.py:69`](../../modules/leave/services/lifecycle.py#L69)<br>[`tests/test_lifecycle.py:45`](../../modules/leave/tests/test_lifecycle.py#L45) |
| **BR-EL-024**<br>Fresh Application after Approved-Leave Cancellation | If revised leave is required after cancellation of an approved leave, the employee submits a fresh leave application. The approved leave is not edited in place. | Revised leave after a cancellation is a fresh application. An approved leave is never edited in place, which is why cancellation is terminal. | [`domain/state_machine.py:299`](../../modules/leave/domain/state_machine.py#L299) [↗](../../modules/leave/domain/state_machine.py#L299) |
| **BR-EL-025**<br>Extension of Ongoing Leave | An ongoing EL, COL or VL may be extended through a separate extension request subject to eligibility, balance, substitute and routing rules. | Extension applies to leave already running, and only the additional days are charged. | [`domain/categories.py:28`](../../modules/leave/domain/categories.py#L28) [↗](../../modules/leave/domain/categories.py#L28)<br>[`services/lifecycle.py:167`](../../modules/leave/services/lifecycle.py#L167)<br>[`tests/test_lifecycle.py:79`](../../modules/leave/tests/test_lifecycle.py#L79) |
| **BR-EL-027**<br>Resumption Requirement | After EL, COL or VL, the employee submits resumption of duty through ELM for verification and closure. | Resumption is reported by the employee and verified by the establishment before anything is settled. | [`domain/categories.py:28`](../../modules/leave/domain/categories.py#L28) [↗](../../modules/leave/domain/categories.py#L28)<br>[`services/lifecycle.py:370`](../../modules/leave/services/lifecycle.py#L370)<br>[`tests/test_lifecycle.py:128`](../../modules/leave/tests/test_lifecycle.py#L128) |
| **BR-EL-028**<br>Early Resumption | An employee on EL, COL or VL may resume before the approved end date. After verification, unused approved leave is restored to the corresponding leave balance and the actual leave period is recorded. | Returning early does not automatically return every unused day — what happens to the tail is a policy choice, because two readings are defensible. | [`domain/categories.py:28`](../../modules/leave/domain/categories.py#L28) [↗](../../modules/leave/domain/categories.py#L28)<br>[`domain/counting.py:10`](../../modules/leave/domain/counting.py#L10)<br>[`domain/counting.py:99`](../../modules/leave/domain/counting.py#L99)<br><sub>8 citations in all</sub> |
| **BR-EL-029**<br>Offline-Sanctioned Leave Recording | A Leave Administrator may retrospectively record leave already sanctioned through an authorized offline/paper process. This keeps ELM records synchronized and does not constitute a second approval. | Leave sanctioned on paper is brought onto the record as synchronisation, explicitly not a second approval. | [`services/administration.py:312`](../../modules/leave/services/administration.py#L312) [↗](../../modules/leave/services/administration.py#L312) |

### Policy and calendar — what governs a decision

Effective dating. A decision is judged against what was in force when it was taken.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-030**<br>Effective Policy Version | Validation and routing use the currently effective published policy and hierarchy parameters. | A decision is judged against the policy in force when it was taken. Policy is never edited; a revision is a new version with its own effective date. | [`services/administration.py:42`](../../modules/leave/services/administration.py#L42) [↗](../../modules/leave/services/administration.py#L42)<br>[`models/policy.py:3`](../../modules/leave/models/policy.py#L3)<br>[`selectors/policy.py:3`](../../modules/leave/selectors/policy.py#L3) |
| **BR-EL-031**<br>Effective Holiday/RH Calendar | Date and RH validations use the currently effective published holiday/RH calendar. | The same for the calendar: the published version in force governs, and a replacement supersedes rather than overwrites. | [`domain/counting.py:48`](../../modules/leave/domain/counting.py#L48) [↗](../../modules/leave/domain/counting.py#L48)<br>[`services/administration.py:160`](../../modules/leave/services/administration.py#L160)<br>[`models/calendar.py:3`](../../modules/leave/models/calendar.py#L3)<br><sub>4 citations in all</sub> |

### Service levels — what happens when nobody acts

Reminders and escalation for a task left pending.

| Rule | Statement | What it means | Code |
|---|---|---|---|
| **BR-EL-032**<br>SLA Reminder | Each SLA-controlled actionable task has a configurable reminder threshold. If still pending at that threshold, the responsible user is reminded. | An SLA-controlled task that is still pending at its reminder threshold gets the responsible user reminded. | [`services/administration.py:134`](../../modules/leave/services/administration.py#L134) [↗](../../modules/leave/services/administration.py#L134)<br>[`services/sla.py:3`](../../modules/leave/services/sla.py#L3)<br>[`models/workflow.py:89`](../../modules/leave/models/workflow.py#L89)<br><sub>5 citations in all</sub> |
| **BR-EL-033**<br>SLA Escalation | Each SLA-controlled actionable task has a configurable escalation threshold. If still pending at that threshold, the configured higher/responsible authority is notified or the task is escalated according to policy. The action is logged. | Still pending at the escalation threshold, and it goes to the configured authority, logged. | [`services/administration.py:134`](../../modules/leave/services/administration.py#L134) [↗](../../modules/leave/services/administration.py#L134)<br>[`services/sla.py:3`](../../modules/leave/services/sla.py#L3)<br>[`models/workflow.py:89`](../../modules/leave/models/workflow.py#L89)<br><sub>5 citations in all</sub> |


---

## Workflows

The specification derives small **basis** workflows for finite paths, then
composes them. The transition table cites the basis rows, because those are what
a single state change belongs to.

| Workflow | Name | Code |
|---|---|---|
| `BW-EL-01` | Substitute-Required New Leave — Consent Accepted | [`domain/state_machine.py:3`](../../modules/leave/domain/state_machine.py#L3) [↗](../../modules/leave/domain/state_machine.py#L3)<br>[`domain/state_machine.py:93`](../../modules/leave/domain/state_machine.py#L93)<br>[`domain/state_machine.py:96`](../../modules/leave/domain/state_machine.py#L96)<br><sub>5 citations in all</sub> |
| `BW-EL-02` | Substitute-Required New Leave — Consent Declined | [`domain/state_machine.py:93`](../../modules/leave/domain/state_machine.py#L93) [↗](../../modules/leave/domain/state_machine.py#L93)<br>[`domain/state_machine.py:112`](../../modules/leave/domain/state_machine.py#L112)<br>[`domain/state_machine.py:116`](../../modules/leave/domain/state_machine.py#L116)<br><sub>5 citations in all</sub> |
| `BW-EL-03` | Higher-Sanction Leave — Approved | [`domain/authority.py:142`](../../modules/leave/domain/authority.py#L142) [↗](../../modules/leave/domain/authority.py#L142)<br>[`domain/state_machine.py:100`](../../modules/leave/domain/state_machine.py#L100)<br>[`domain/state_machine.py:104`](../../modules/leave/domain/state_machine.py#L104)<br><sub>17 citations in all</sub> |
| `BW-EL-04` | Higher-Sanction Leave — Rejected | [`domain/state_machine.py:123`](../../modules/leave/domain/state_machine.py#L123) [↗](../../modules/leave/domain/state_machine.py#L123)<br>[`domain/state_machine.py:138`](../../modules/leave/domain/state_machine.py#L138)<br>[`domain/state_machine.py:150`](../../modules/leave/domain/state_machine.py#L150)<br><sub>4 citations in all</sub> |
| `BW-EL-05` | Higher-Sanction Cancellation — Approved | [`domain/authority.py:151`](../../modules/leave/domain/authority.py#L151) [↗](../../modules/leave/domain/authority.py#L151)<br>[`domain/state_machine.py:184`](../../modules/leave/domain/state_machine.py#L184)<br>[`domain/state_machine.py:187`](../../modules/leave/domain/state_machine.py#L187)<br><sub>8 citations in all</sub> |
| `BW-EL-06` | Higher-Sanction Cancellation — Rejected | [`domain/state_machine.py:184`](../../modules/leave/domain/state_machine.py#L184) [↗](../../modules/leave/domain/state_machine.py#L184)<br>[`domain/state_machine.py:203`](../../modules/leave/domain/state_machine.py#L203)<br>[`domain/state_machine.py:215`](../../modules/leave/domain/state_machine.py#L215)<br><sub>4 citations in all</sub> |
| `BW-EL-07` | Ongoing Leave Extension — Approved | [`domain/state_machine.py:218`](../../modules/leave/domain/state_machine.py#L218) [↗](../../modules/leave/domain/state_machine.py#L218)<br>[`domain/state_machine.py:225`](../../modules/leave/domain/state_machine.py#L225)<br>[`domain/state_machine.py:229`](../../modules/leave/domain/state_machine.py#L229)<br><sub>14 citations in all</sub> |
| `BW-EL-08` | Ongoing Leave Extension — Rejected | [`domain/state_machine.py:218`](../../modules/leave/domain/state_machine.py#L218) [↗](../../modules/leave/domain/state_machine.py#L218)<br>[`domain/state_machine.py:273`](../../modules/leave/domain/state_machine.py#L273)<br>[`services/lifecycle.py:252`](../../modules/leave/services/lifecycle.py#L252)<br><sub>4 citations in all</sub> |
| `BW-EL-09` | Normal Resumption and Closure | [`domain/state_machine.py:221`](../../modules/leave/domain/state_machine.py#L221) [↗](../../modules/leave/domain/state_machine.py#L221)<br>[`domain/state_machine.py:276`](../../modules/leave/domain/state_machine.py#L276)<br>[`domain/state_machine.py:279`](../../modules/leave/domain/state_machine.py#L279)<br><sub>9 citations in all</sub> |
| `BW-EL-10` | Early Resumption and Closure | [`domain/state_machine.py:276`](../../modules/leave/domain/state_machine.py#L276) [↗](../../modules/leave/domain/state_machine.py#L276)<br>[`domain/state_machine.py:283`](../../modules/leave/domain/state_machine.py#L283) |
| `BW-EL-11` | Modified Request — Fresh Substitute Accepted | [`domain/state_machine.py:242`](../../modules/leave/domain/state_machine.py#L242) [↗](../../modules/leave/domain/state_machine.py#L242) |
| `BW-EL-12` | Modified Request — Fresh Substitute Declined | [`domain/state_machine.py:3`](../../modules/leave/domain/state_machine.py#L3) [↗](../../modules/leave/domain/state_machine.py#L3) |
| `CW-EL-01` | New Leave Processing | [`domain/state_machine.py:300`](../../modules/leave/domain/state_machine.py#L300) [↗](../../modules/leave/domain/state_machine.py#L300) |
| `CW-EL-02` | Pending Request Change | *not in code* — |
| `CW-EL-03` | Approved Leave Cancellation | *not in code* — |
| `CW-EL-04` | Ongoing Leave Extension | *not in code* — |
| `CW-EL-05` | Resumption and Leave Closure | *not in code* — |

---

## What is deliberately absent, and what is simply missing

The distinction matters when teaching: most of these are decisions, one is a gap.

**BR-EL-021** — Modify a pending request

Not implemented. There is no edit path: a pending request is withdrawn and re-applied for. That satisfies the intent (revalidation, superseded tasks) by construction, but it is not the same as the rule, and it costs the applicant a resubmission. Worth building before a real season.

**EL-UC-013** — Obtain a printable leave application

Not implemented. No PDF or print view exists. The data is all present, so this is presentation work rather than domain work.

**BR-EL-026** — —

**This rule does not exist.** The specification numbers 32 rules and skips 026. All 32 are defined and all 32 are cited; there is no orphan. The gap in the numbering is upstream and was left alone deliberately rather than renumbered, so the ids in this repository match the documents you were given.

**CW-EL-02 … CW-EL-05** — Composite workflows

Not cited directly, by design. A composite is a composition of basis workflows, and the code cites the basis rows (`BW-EL-nn`) it actually implements. `CW-EL-01` appears once, where the specification names it as the related workflow for a fresh application after cancellation.

**WF-EL-06 / 07 / 08** — Retired as workflows

The specification retires these on purpose. Offline recording is record synchronisation (EL-UC-016 + BR-EL-029), and year-end and SLA are scheduled functions (SF-EL-001, SF-EL-002). None of them is a multi-actor collaboration, so none is modelled as one.

---

## Where to look for what

One shape, five layers, and the layer tells you what a file is allowed to do.

### `domain/`

Framework-free. The rules, as pure Python — no Django import, which is what keeps them testable without a database.

- `categories.py` — which category behaves how
- `counting.py` — chargeable days, early return
- `entitlement.py` — credits, lapse, carry-forward, conversion
- `overlap.py` — clashes, and the half-day exception
- `state_machine.py` — 23 states, 46 transitions, every row cited
- `authority.py` — which rule applies and what route it implies

### `models/`

The tables. 12 of them, 12 database check constraints.

- `policy.py` — LeavePolicy, CategoryRule
- `calendar.py` — HolidayCalendar, Holiday, VacationPeriod
- `ledger.py` — LedgerEntry — append-only, no balance column anywhere
- `request.py` — LeaveRequest, SubstituteNomination
- `workflow.py` — RequestTransition, AuthorityRule, SlaRule, SlaClock

### `selectors/`

Every read. Scope lives here, as queryset narrowing.

- `balances.py` — a balance is a sum of the ledger
- `policy.py` — which policy and calendar govern a date
- `scoping.py` — who may see what

### `services/`

Every write. Transaction boundaries.

- `requests.py` — validate and submit
- `workflow.py` — apply_event — the single choke point
- `decisions.py` — review, routing, sanction, withdrawal
- `lifecycle.py` — cancellation, extension, resumption
- `yearend.py` — close and credit a year
- `scheduler.py` — what the calendar does on its own
- `sla.py` — reminders and escalation
- `administration.py` — policy, calendar and offline recording

### `api/`

Thin. Two gates on every endpoint, then straight to a service.

- `views.py` — every endpoint
- `serializers.py` — the wire shapes
- `urls.py` — the routes

### `tests/`

Where a rule's behaviour is pinned.

- `test_counting.py` — the arithmetic
- `test_authority.py` — BR-EL-017, 019, 020
- `test_loopholes.py` — what the module must refuse
- `test_ledger_integrity.py` — running the accounting twice
- `test_concurrency.py` — two transactions at once

---

## The five ideas behind all of it

If somebody remembers only five things from a session on this module:

1. **The balance is a ledger, not a column.** There is no stored total anywhere.
   A balance is the sum of append-only entries, so it can always be re-derived
   and always explained row by row. A wrong entry is corrected by a reversing
   entry, so the mistake survives the correction.
2. **Policy is effective-dated and never edited.** A revised ordinance is a new
   version. Last year's approvals still explain themselves, because they cite
   the version they were decided under.
3. **Transitions are a table.** An illegal state change is *inexpressible*
   rather than rejected by a check somebody can forget to write.
4. **Authority is configuration.** Naming offices in code turns a reorganisation
   into a deployment.
5. **Scope is a queryset.** Somebody else's request is not found, rather than
   refused — because a refusal confirms it exists.

---

## Further reading

- [Domain model](leave-domain-model.md) — tables, categories, bring-up order
- [Counting and entitlement](leave-counting-and-entitlement.md) — the arithmetic
- [State machine](leave-state-machine.md) — all 46 transitions
- [Authority, routing and scope](leave-authority-and-routing.md) — who decides, who sees

