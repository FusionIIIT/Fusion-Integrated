# Patent Management System — blueprint

Module code `pms` (folder `modules/pms`, URL `/api/v1/pms/`, client `/pms`, permission prefix `pms.`).
Built from the specification set *Fusion ERP – Patent Management System*, v1.3 DIRECT_FINAL
(problem statement v1.2). Environment: `module-only`.

**Status: approved.** Student 2 (Assignment 9: no mentor) approved, in writing on 21 Nov 2026,
the Phase 1 answers and this blueprint, including proposals Q-1..Q-13, H-1, H-2, H-3, S-1 and
S-2. The quality report records both approvals.

---

## 0. Inputs this blueprint rests on

### 0.1 Spec inventory

| Artefact | Live ids | Notes |
|---|---|---|
| Grouped requirements | 30 (CFR-PMS-001..030) | Each rolls up from its detailed requirements |
| Detailed requirements | 203 (PMS-AFR-nnn) | Same numbers as the old PMS-FR-nnn ids. 36 numbers absent; the spec calls them historical and lists no replacements |
| Business rules | 84 (BR-PMS-003..146) | 62 numbers absent; the spec does not enumerate them |
| Use cases | 33 (UC-PMS-001..033) | none retired |
| Workflows | 21 (BW-PMS-01..16, CW-PMS-01..05) | none retired |
| Open spec issue | ISS-PMS-020 | settled by ruling A15 below |

Absent numbers are treated as non-existent: nothing in the module cites them. The traceability
matrix's mapping columns are empty on every row, so coverage below was worked out by reading
each rule, not copied from the matrix.

### 0.2 Rulings received (Phase 1)

The pair's answers to the 22 Phase 1 questions, relayed into the build session. **The date on
the relayed text was blank; Student 2 confirmed in writing that the answers were approved on
21 Nov 2026.** Short form; the numbering matches `phase1_questions.md`.

| # | Ruling | Where it lands |
|---|---|---|
| A1 | Real uploads in PMS; 50 MB as the spec says; submission refused while no scanner is configured; report the 5 MB baseline as a conflict rather than lower the limit | §3.2 documents, §3.8 H-1, H-2, H-3 |
| A2 | Roles are assigned only by the IAM; UC-025 covers PMS settings; the role-assignment half of PMS-AFR-027 is an accepted gap | §3.8 G-1 |
| A3 | BR-PMS-131 / PMS-AFR-221 accepted gap; name the IAM endpoint needed | §3.8 G-2 |
| A4 | Applicant = `student`, `faculty`, `staff`. New designations `pms_director`, `pms_pcc_admin`, `pms_attorney`; display names Director / PCC_ADMIN / Attorney | §3.4 |
| B5 | Budget is its own record with its own states. "Approved" in BR-PMS-052 = {Approved, Pending Review, Attorney Assigned}; in BR-PMS-040 = {Approved, Pending Review} | §3.3 |
| B6 | BR-PMS-034 wins: a Rejected application may be revised, documents included. BR-PMS-087 read as "documents editable only in a revisable state (Needs Revision or Rejected)" | §3.3, `domain/documents.py` |
| B7 | 60-day expiry applies to Rejected; an open appeal stops the clock; appeal period configurable, default 30 days; no revision while an appeal is open | §3.3 |
| C8 | Remanded → Needs Revision with a new 60-day clock; Decision Modified → Director picks Approve or Needs Revision; Rejection Upheld is final | §3.3 |
| C9 | Grant recorded as a patent-office communication (Filed → Granted). Patent-office refusal → final status **Refused** | §3.3 |
| C10 | Business days = Mon–Fri minus a PCC_ADMIN holiday list. A late decision is refused; PCC_ADMIN reassigns, which restarts the clock; the miss also escalates | §3.3, §3.7 |
| C11 | Inventors are institute users or outside people; shares each > 0 and total exactly 100; the Applicant records agreements and consents; e-signatures off | §3.2 |
| C12 | A resubmission answers each piece of feedback (≥ 50 characters) and changes at least one field or document | `domain/validation.py` |
| C13 | PCC_ADMIN keeps technical areas; Applicant picks one; PCC_ADMIN maps Directors and panel attorneys to areas; Director sees assigned applications plus their areas for oversight and reports; workload = open assignments | §3.2, §3.5 |
| C14 | Attorney enters costs and requests review; the reviewing Director decides; no threshold → refuse; after Escalated, PCC_ADMIN records the outside decision | §3.3 |
| C15 | PCC_ADMIN picks which of CW-PMS-05's seven statuses allow withdrawal, none to start; co-inventor consent only when a setting says so, off by default | §3.2 policy |
| C16 | Sensitivity: Public-internal, Confidential, Restricted. Applicant sets on upload; PCC_ADMIN may change. Restricted readable only by the Applicant, institute-user inventors, the assigned Director, the assigned Attorney and PCC_ADMIN | `domain/documents.py`; §3.8 Q-3 |
| C17 | Prior art: sessions logged, references entered by hand, ranking against recorded references, outside sources shown "not connected"; outside search is a known gap | §3.8 G-3 |
| C18 | Attorney sets, per office action, whether Applicant review is required and the deadline | §3.3 |
| C19 | Renewal decided by the reviewing Director; PCC_ADMIN reassigns if that Director is no longer active | §3.3 |
| C20 | Licensing routes to a configured committee or named Director; Director and PCC_ADMIN record negotiation and agreement; visible to the applicant, routed Director and PCC_ADMIN only | §3.2, `selectors/scoping.py` |
| C21 | Escalation chain configurable, PCC_ADMIN by default; Directors view audit logs for their own areas | §3.2 policy, `selectors/scoping.py` |
| C22 | Saved report definitions, weekly or monthly, CSV export | §3.5; one change for security in §3.8 S-1 |

---

## 3.1 (a) Traceability

Layer key: **domain** = pure rule in `modules/pms/domain/`; **service** = transactional write
in `services/`; **selector** = row visibility or read in `selectors/`; **db** = a database
constraint; **task** = scheduled work; **registry** = permission grant published to the IAM;
**platform** = outside PMS. Paths are relative to `modules/pms/`. Nothing lands in `api/`.

### Business rules (84)

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-PMS-003 | Applicants see report data only for their own applications | selector | `selectors/scoping.py::applications_for`, `selectors/reports.py::report_rows` | Out-of-scope rows simply absent |
| BR-PMS-005 | Directors see reports only within their scope | selector | `selectors/reports.py::report_rows` via `scoping.applications_for` | Scope = assigned + own areas (C13) |
| BR-PMS-006 | Director oversight limited to their domain | selector | `selectors/scoping.py::applications_for`, `selectors/oversight.py::workflow_summary` | |
| BR-PMS-014 | Accepted documents must be PDF | domain | `domain/documents.py::check_pdf` (magic bytes `%PDF-` and `.pdf` name), called by `services/documents.py::upload` | Content sniffed, not trusted from the name |
| BR-PMS-015 | Document must be under 50 MB | domain | `domain/documents.py::check_size` (< 52,428,800 bytes) | nginx cap conflicts — §3.8 H-1 |
| BR-PMS-016 | Document must pass malware validation before acceptance | service | `services/scanning.py::scan` inside `services/documents.py::upload`; no stored version without a clean result | Refused when no scanner is configured (A1) |
| BR-PMS-017 | Required fields complete before submission | domain | `domain/validation.py::missing_fields`, called by `services/applications.py::submit` | Names each missing field |
| BR-PMS-020 | Inventor agreements complete before external filing | domain | `domain/filing.py::filing_blockers` → `services/filing.py::record_filing` | Same check as BR-PMS-078 |
| BR-PMS-022 | Automatic Director assignment only when rules are configured, using the same criteria | service | `services/routing.py::auto_route` (only when `policy.auto_routing_enabled`), reusing `domain/assignment.py::eligible_directors` | |
| BR-PMS-023 | Director expertise matches application domain | domain | `domain/assignment.py::eligible_directors` | Strict reading: a match is required — §3.8 Q-8 |
| BR-PMS-024 | Director workload balance is a criterion | domain + selector | `domain/assignment.py::rank_attorneys`; counts from `selectors/candidates.py::director_workloads` | Auto-routing picks the least loaded |
| BR-PMS-025 | Conflict-of-interest check before Director assignment | domain | `domain/assignment.py::conflicts` (applicant or inventor) | |
| BR-PMS-026 | A Director never reviews an application listing them as inventor | domain + service | `domain/assignment.py::conflicts` at assignment; re-checked in `services/review.py::decide` | Checked again at decision time because inventors can change |
| BR-PMS-027 | PCC_ADMIN never acts as reviewer where they are an inventor | service | `services/review.py::refuse_conflicted_admin` on every PCC_ADMIN act on that application | §3.8 Q-6 |
| BR-PMS-029 | Review decision is exactly one of Approve / Reject / Needs Revision | domain | `domain/state_machine.py` APPLICATION table (three decide events only) | Anything else is inexpressible |
| BR-PMS-030 | Review justification ≥ 50 characters | domain | `domain/validation.py::check_justification` | Counted after trimming |
| BR-PMS-031 | Review completed within 15 business days of assignment | domain + service | `domain/calendar.py::review_due`; guard in `services/review.py::decide` | Late decision refused (C10) |
| BR-PMS-033 | Revision permitted in Needs Revision | domain | `domain/state_machine.py::APPLICATION`; `resubmit` from NEEDS_REVISION | |
| BR-PMS-034 | Revision permitted in Rejected | domain | `domain/state_machine.py::APPLICATION`; `resubmit` from REJECTED | B6 |
| BR-PMS-035 | Resubmit within 60 days of the decision | domain | `domain/calendar.py::revision_due`; guard in `services/revision.py::resubmit` | Clock stops while an appeal is open (B7) |
| BR-PMS-036 | Resubmission must address recorded feedback | domain | `domain/validation.py::check_revision_responses` | C12 |
| BR-PMS-038 | Missed resubmission period → Expired | task | `tasks.py::process_deadlines` → `services/deadlines.py::sweep` | SYSTEM edge in the table |
| BR-PMS-040 | Only PCC_ADMIN assigns an Attorney, to an Approved application | registry + domain | `pms.attorney.assign` held only by `pms_pcc_admin`; APPLICATION/ASSIGNMENT guards in `services/attorneys.py::assign_attorney` | Approved = {Approved, Pending Review} (B5) |
| BR-PMS-041 | Attorney from the approved panel unless an exception is recorded | domain | `domain/assignment.py::check_attorney` | Exception needs a recorded reason |
| BR-PMS-042 | Attorney expertise matches the domain | domain | `domain/assignment.py::check_attorney` | Waived only by a recorded exception |
| BR-PMS-043 | Attorney workload is a criterion | domain + selector | `domain/assignment.py::rank_attorneys`, `selectors/candidates.py::attorney_workloads` | |
| BR-PMS-044 | Conflict-of-interest check before Attorney assignment | domain | `domain/assignment.py::conflicts` | |
| BR-PMS-045 | Applicant preference counts only for a panel attorney | domain | `domain/assignment.py::rank_attorneys` (preferred panel attorney first); `services/applications.py::update_draft` refuses a non-panel preference | |
| BR-PMS-046 | Final opinion carries exactly one of File Patent / Do Not File / Needs Amendment | domain + db | `domain/validation.py::check_opinion`; CheckConstraint `pms_assessment_final_has_recommendation` in `models/legal.py` | |
| BR-PMS-048 | Budget includes filing fees | domain + db | `domain/budget.py::check_components`; NOT NULL ≥ 0 | |
| BR-PMS-049 | Budget includes attorney fees | domain + db | as above | |
| BR-PMS-050 | Budget includes administrative costs | domain + db | as above | |
| BR-PMS-051 | Total over the configured threshold → escalate | domain | `domain/budget.py::exceeds_threshold` → BUDGET table `escalate` edge | No threshold → decision refused (C14) |
| BR-PMS-052 | Budget approval only while the application is Approved | domain | `domain/budget.py::application_allows_budget` with B5's set | |
| BR-PMS-053 | Validate budget availability where data exists | domain | `domain/budget.py::availability` → `NOT_AVAILABLE` (no source) recorded on the financial record | Conditional rule; the unavailable branch is what runs |
| BR-PMS-055 | Filing package meets format rules where rules exist | domain | `domain/filing.py::filing_blockers` → `NO_RULES` recorded on the filing | Conditional rule |
| BR-PMS-056 | International filing needs a recorded justification | domain + db | `domain/validation.py::check_international_justification`; CheckConstraint `pms_filing_international_justified` in `models/filing.py` | |
| BR-PMS-059 | Post-grant tracking only for Granted | domain | `domain/post_grant.py::may_track` in `services/maintenance.py` | |
| BR-PMS-060 | Maintenance schedule from grant date and jurisdiction where rules exist | domain | `domain/post_grant.py::schedule` | No rule → no schedule; attorney may enter a due date (§3.8 Q-12) |
| BR-PMS-061 | Explicit Renew / Do Not Renew before each deadline | domain | MAINTENANCE table; guard `before_due_date` in `services/maintenance.py::decide` | |
| BR-PMS-065 | Response recorded submitted within the deadline unless extended | domain | `domain/office_actions.py::current_deadline`, guard in `services/office_actions.py::record_submission` | |
| BR-PMS-066 | Response deadline tracking only where deadline data exists | domain + task | `domain/office_actions.py::tracked`; `services/deadlines.py` skips actions with no deadline | |
| BR-PMS-067 | Withdrawal only before filing | domain | `domain/withdrawal.py::check_allowed` (post-filing statuses never eligible) | |
| BR-PMS-068 | Withdrawal only from a configured eligible status | domain | `domain/withdrawal.py::check_allowed` with policy withdrawal_statuses | Empty by default (C15) |
| BR-PMS-069 | Withdrawal needs a reason | domain | `domain/validation.py::check_withdrawal_reason` | |
| BR-PMS-070 | Co-inventor consent recorded when required | domain | `domain/withdrawal.py::check_consent` | Required only when the policy flag is on |
| BR-PMS-073 | Inventor information validated | domain | `domain/validation.py::check_inventors` | Name required; institute user or outside person |
| BR-PMS-074 | Ownership percentages validated | domain + db | `domain/validation.py::check_inventors` (each > 0, total = 100.00); CheckConstraint `pms_inventor_share_range` in `models/applications.py` | Total checked under the application lock |
| BR-PMS-075 | Required consent obtained before filing | domain | `domain/filing.py::filing_blockers` | |
| BR-PMS-076 | E-signatures only where permitted and configured | domain | `domain/policy.py` has no e-signature setting, so `services/inventors.py` never collects one | Conditional rule |
| BR-PMS-077 | E-signature validation only where permitted and configured | domain | as BR-PMS-076 | |
| BR-PMS-078 | Inventor agreements complete before filing | domain | `domain/filing.py::filing_blockers` | Same check as BR-PMS-020 |
| BR-PMS-082 | Automatic version numbers | service + db | `services/documents.py::upload` (`next_version` under lock); UniqueConstraint `pms_docversion_number_unique` in `models/documents.py` | |
| BR-PMS-084 | Previous versions readable only per role and status | domain + selector | `domain/documents.py::may_read`; `selectors/scoping.py::documents_for` | |
| BR-PMS-086 | Document access controlled by role and status | domain + selector | `domain/documents.py::may_upload`, `may_read` | |
| BR-PMS-087 | Applicants edit documents only in a revisable state | domain | `domain/documents.py::may_upload` (Draft, Needs Revision, Rejected) | B6 |
| BR-PMS-088 | Licensing requests routed per the configured process | domain + service | `domain/licensing.py::route_target`, `services/licensing.py::submit` | Unconfigured → stays Submitted, no invented decision |
| BR-PMS-091 | License records under confidentiality controls | selector | `selectors/scoping.py::licensing_for` | C20 |
| BR-PMS-092 | Only Rejected applications may be appealed | domain | `domain/state_machine.py::APPLICATION`; `appeal` from REJECTED only | |
| BR-PMS-093 | Appeal within the configured period | domain | `domain/appeals.py::check_open` | Default 30 days (B7) |
| BR-PMS-094 | Appeal needs grounds and justification | domain | `domain/validation.py::check_appeal_grounds` | |
| BR-PMS-095 | Appeal outcome is exactly one of three | domain | APPEAL table (three decide events) | |
| BR-PMS-097 | Review deadline calculated and monitored | domain + task | `domain/calendar.py::review_due`; `services/deadlines.py::sweep` | |
| BR-PMS-098 | Revision deadline calculated and monitored | domain + task | `domain/calendar.py::revision_due`; `services/deadlines.py::sweep` | |
| BR-PMS-099 | Office-action deadlines monitored only where data exists | task | `services/deadlines.py::sweep` → `domain/office_actions.py::tracked` | |
| BR-PMS-100 | Maintenance deadlines monitored only where rules or data exist | task | `services/deadlines.py::sweep` over cycles with a due date | |
| BR-PMS-101 | Alert 30 days before a tracked deadline | domain + task | `domain/deadlines.py::alerts_due`; UniqueConstraint `pms_alert_once` | Offsets configurable, default 30/15/5 |
| BR-PMS-102 | Alert 15 days before | domain + task | as above | |
| BR-PMS-103 | Alert 5 days before | domain + task | as above | |
| BR-PMS-104 | Missed deadline escalates along the configured chain | domain + task | `domain/deadlines.py::missed`; `services/escalations.py::raise_case`; UniqueConstraint `pms_escalation_open_once` | Chain defaults to PCC_ADMIN (C21) |
| BR-PMS-116 | PMS only triggers email; delivery is outside | service | `services/notifications.py::deliver_pending` hands messages to Django's mail backend | |
| BR-PMS-121 | Audit records carry user, action, time, application, from and to state | service + db | `services/audit.py::record`; `AuditEntry` columns | |
| BR-PMS-122 | Critical operations create immutable audit records | db | `AuditEntry` refuses update and delete in Python **and** a trigger `pms_auditentry_immutable` in the initial migration | |
| BR-PMS-126 | A valid PMS role is needed to use PMS | registry + api gate | `HasModuleGrant("pms")` then `HasPermission(...)` on every view | Gate classes only; policy stays out of `api/` |
| BR-PMS-127 | No attorney assignment before Director approval | domain | ASSIGNMENT guard `application_approved` (B5 set) | |
| BR-PMS-128 | No external filing before approvals and budget | domain | `domain/filing.py::filing_blockers` (approved budget, accepted attorney) | |
| BR-PMS-130 | Confidential information under role-based access | selector + domain | `selectors/scoping.py` for every read; `domain/documents.py::may_read` for sensitivity | |
| BR-PMS-131 | Exactly one active PCC_ADMIN | platform | **Accepted gap G-2** (A3) | PMS cannot see designation holders |
| BR-PMS-138 | Patent offices are external; PMS records only | service | `services/communications.py` records; no outbound call exists | |
| BR-PMS-139 | Financial systems are external | service | `services/licensing.py::record_agreement` and `services/budget.py` record `financial_sync = NOT_AVAILABLE` | |
| BR-PMS-140 | Document-management systems are external | service | `services/documents.py` stores PMS's own versions only | |
| BR-PMS-141 | Prior-art databases are query sources, not PMS data | domain | `domain/prior_art.py::SOURCES` all "not connected"; references stored only when a person attaches them | Gap G-3 |
| BR-PMS-142 | Filing success not treated as internal | domain + db | `domain/filing.py::filing_blockers` needs an external filing id and confirmation; NOT NULL columns | |
| BR-PMS-146 | Applicant approval only when the process requires it | domain | OFFICE_ACTION table: the `requires_applicant_review` flag selects the path | C18 |

### Use cases (33)

Every use case is enforced by its service entry point, behind the module gate and one
permission (§3.5), with rows narrowed by `selectors/scoping.py`.

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| UC-PMS-001 | Submit an application | service | `services/applications.py::create_draft`, `submit` | Fails closed without a scanner |
| UC-PMS-002 | Track own status and history | selector | `selectors/applications.py::detail`, `history` | |
| UC-PMS-003 | Manage co-inventors and agreements | service | `services/inventors.py::replace_inventors`, `record_agreement` | |
| UC-PMS-004 | Search and attach prior art | service | `services/prior_art.py::search`, `attach` | |
| UC-PMS-005 | Revise and resubmit | service | `services/revision.py::save_revision`, `resubmit` | |
| UC-PMS-006 | Withdraw | service | `services/withdrawal.py::withdraw` | |
| UC-PMS-007 | Assign to a Director | service | `services/review.py::assign_director`; `services/routing.py::auto_route` | |
| UC-PMS-008 | Review an application | service | `services/review.py::decide` | |
| UC-PMS-009 | Review and decide a budget | service | `services/budget.py::propose`, `decide` | |
| UC-PMS-010 | Assign an Attorney | service | `services/attorneys.py::assign_attorney` | |
| UC-PMS-011 | Accept or decline an assignment | service | `services/attorneys.py::respond` | |
| UC-PMS-012 | Patentability assessment | service | `services/assessments.py::save`, `finalize`; `services/legal.py::request` | |
| UC-PMS-013 | Prepare and record external filing | service | `services/filing.py::record_filing` | |
| UC-PMS-014 | Record patent-office communication | service | `services/communications.py::record` | Includes grant and refusal (C9) |
| UC-PMS-015 | Respond to an office action | service | `services/office_actions.py::prepare_response`, `record_submission`, `record_extension` | |
| UC-PMS-016 | Monitor deadlines and escalations | selector + task | `selectors/deadlines.py::upcoming`, `missed`; `tasks.py::process_deadlines` | |
| UC-PMS-017 | Post-grant tracking and maintenance | service | `services/maintenance.py::activate`, `request_decision`, `record_action` | |
| UC-PMS-018 | Renewal decision | service | `services/maintenance.py::decide` | |
| UC-PMS-019 | Manage document versions | service | `services/documents.py::upload`, `set_sensitivity`; `selectors/scoping.py::document_versions_for` | |
| UC-PMS-020 | Submit a licensing request | service | `services/licensing.py::submit` | |
| UC-PMS-021 | Review a licensing request | service | `services/licensing.py::route`, `add_note`, `record_agreement` | |
| UC-PMS-022 | File an appeal | service | `services/appeals.py::file_appeal` | |
| UC-PMS-023 | Review an appeal | service | `services/appeals.py::decide_appeal` | |
| UC-PMS-024 | System-wide reports | selector + service | `selectors/reports.py::report_rows`; `services/reports.py::save_definition`, `export` | |
| UC-PMS-025 | Manage PMS configuration | service | `services/policy.py::publish` | Role assignment is the IAM's (G-1) |
| UC-PMS-026 | Maintain the attorney panel | service | `services/rosters.py::add_panel_attorney`, `end_panel_attorney` | |
| UC-PMS-027 | Monitor workflow and handle exceptions | service | `services/escalations.py::handle`; `services/budget.py::route_escalation`, `record_external_decision` | |
| UC-PMS-028 | View audit logs | selector | `selectors/audit.py::entries_for` | Directors: own areas (C21) |
| UC-PMS-029 | Applicant approves an office-action response | service | `services/office_actions.py::approve_response` | |
| UC-PMS-030 | Own application reports | selector | `selectors/reports.py::report_rows` (applicant scope) | |
| UC-PMS-031 | Director reports | selector | `selectors/reports.py::report_rows` (director scope) | |
| UC-PMS-032 | Director workflow oversight | selector | `selectors/oversight.py::workflow_summary` | |
| UC-PMS-033 | Record legal advice | service | `services/legal.py::record_advice` | No status change |

### Workflows (21)

Each workflow is a set of rows in a declarative table in `domain/state_machine.py` (§3.3). Each
row is executed by `services/workflow.py::transition` (application) or `transition_record`
(other records).

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BW-PMS-01 | Draft → Submitted → Under Review → Approved | domain | APPLICATION rows `submit`, `assign_director`, `approve` | |
| BW-PMS-02 | Under Review → Needs Revision → Resubmitted → Under Review → Approved | domain | APPLICATION rows `request_revision`, `resubmit`, `assign_director`, `approve` | |
| BW-PMS-03 | Rejected → Appeal Submitted → Remanded for Amendment | domain | APPLICATION `reject`, `appeal`; APPEAL `remand` → application `remanded` (to Needs Revision) | C8 |
| BW-PMS-04 | … → Rejection Upheld | domain | APPEAL `uphold` → application `appeal_upheld` | Final |
| BW-PMS-05 | … → Decision Modified | domain | APPEAL `modify` → application `appeal_modified_approve` / `appeal_modified_revise` | C8 |
| BW-PMS-06 | Approved → Assignment Offered → Attorney Assigned | domain | ASSIGNMENT `offer`, `accept`; APPLICATION `attorney_accepted` | Offered is an assignment state, not an application status |
| BW-PMS-07 | Decline → Pending Review → reassign → accept | domain | ASSIGNMENT `decline`; APPLICATION `attorney_declined`; then BW-PMS-06 again | |
| BW-PMS-08 | Budget Approved | domain | BUDGET `approve` | |
| BW-PMS-09 | Budget Rejected | domain | BUDGET `reject` | |
| BW-PMS-10 | Escalated → Escalation Tracked | domain | BUDGET `escalate`, `route` (plus C14's `record_external_*`) | |
| BW-PMS-11 | Pre-filing preconditions → Filed | domain | APPLICATION `file`, guarded by `domain/filing.py::filing_blockers` | "Preconditions satisfied" is computed, never stored |
| BW-PMS-12 | Office action with Applicant review | domain | OFFICE_ACTION `prepare_for_applicant`, `applicant_approve`, `submit` | |
| BW-PMS-13 | Office action without Applicant review | domain | OFFICE_ACTION `prepare_ready`, `submit` | |
| BW-PMS-14 | Renewal → renewed, next cycle scheduled | domain | MAINTENANCE `request`, `renew`, `record_action` | |
| BW-PMS-15 | Do Not Renew | domain | MAINTENANCE `request`, `do_not_renew` | |
| BW-PMS-16 | Withdrawal from an eligible pre-filing status | domain | APPLICATION `withdraw` rows, guarded by `domain/withdrawal.py` | |
| CW-PMS-01 | Review and disposition (BW-01..05) | domain | APPLICATION table rows of BW-01..05 | |
| CW-PMS-02 | Pre-filing governance (BW-06..11) | domain | ASSIGNMENT, BUDGET, APPLICATION `file` | Budget and attorney run in parallel (B5) |
| CW-PMS-03 | Office-action handling (BW-12, 13) | domain | OFFICE_ACTION table | |
| CW-PMS-04 | Maintenance cycle (BW-14, 15) | domain | MAINTENANCE table | |
| CW-PMS-05 | Withdrawal from the seven candidate statuses | domain | APPLICATION `withdraw` rows from exactly those seven | Each also needs the policy to list it |

### Grouped requirements (30)

Each one is satisfied when all of its detailed requirements below are.

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| CFR-PMS-001 | Applicant tracking and reports | selector | AFR-010, 016 | |
| CFR-PMS-002 | Director oversight | selector | AFR-023 | |
| CFR-PMS-003 | PCC_ADMIN administration | service | AFR-026, 027, 029, 030 | AFR-027 partly gap G-1 |
| CFR-PMS-004 | Attorney legal advice | service | AFR-037 | |
| CFR-PMS-005 | Submission | domain + service | AFR-038..048 | |
| CFR-PMS-006 | Director routing | domain + service | AFR-049..057 | |
| CFR-PMS-007 | Director review | domain + service | AFR-058..065 | |
| CFR-PMS-008 | Revision and resubmission | domain + service + task | AFR-066..072 | |
| CFR-PMS-009 | Attorney assignment | domain + service | AFR-074..081 | |
| CFR-PMS-010 | Patentability assessment | domain + service | AFR-082..089 | |
| CFR-PMS-011 | Budget | domain + service | AFR-090..098 | |
| CFR-PMS-012 | Filing and communication | domain + service | AFR-099..106 | |
| CFR-PMS-013 | Post-grant maintenance | domain + service | AFR-107..115 | |
| CFR-PMS-014 | Office actions | domain + service | AFR-116..124 | |
| CFR-PMS-015 | Withdrawal | domain + service | AFR-125..131 | |
| CFR-PMS-016 | Inventors and agreements | domain + service | AFR-132..138, 140 | |
| CFR-PMS-017 | Prior art | domain + service | AFR-141..149 | AFR-143/144 gap G-3 |
| CFR-PMS-018 | Documents | domain + service | AFR-150..157 | |
| CFR-PMS-019 | Licensing | service + selector | AFR-158..164 | |
| CFR-PMS-020 | Appeals | domain + service | AFR-165..171 | |
| CFR-PMS-021 | Deadlines and escalation | domain + task | AFR-172..181 | |
| CFR-PMS-022 | Reports | selector + service | AFR-182..191, 237..239 | |
| CFR-PMS-023 | Email notifications | service + task | AFR-192..204, 206 | |
| CFR-PMS-024 | Audit and security | service + db + platform | AFR-207..215 | |
| CFR-PMS-025 | Role required | registry | AFR-216 | |
| CFR-PMS-026 | Lifecycle gates | domain | AFR-217, 218 | |
| CFR-PMS-027 | Confidential access | selector | AFR-220 | |
| CFR-PMS-028 | Role and workflow governance | domain + registry | AFR-221..227 | AFR-221 gap G-2 |
| CFR-PMS-029 | External-system boundary | service | AFR-228..232 | |
| CFR-PMS-030 | Budget rejection outcome | domain + service | AFR-236 | |

### Detailed requirements (203)

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| PMS-AFR-010 | Applicants track status and progress | selector | `selectors/applications.py::list_for`, `detail` | |
| PMS-AFR-016 | Applicants view reports on their own applications | selector | `selectors/reports.py::report_rows` | BR-PMS-003 |
| PMS-AFR-023 | Directors get oversight of their domain | selector | `selectors/oversight.py::workflow_summary` | |
| PMS-AFR-026 | PCC_ADMIN monitors workflows and resolves conflicts | service | `selectors/oversight.py`; `services/escalations.py::handle` | |
| PMS-AFR-027 | PCC_ADMIN manages configuration and role assignments | service | `services/policy.py::publish` | Role-assignment half: gap G-1 |
| PMS-AFR-029 | PCC_ADMIN handles escalations and exceptions | service | `services/escalations.py::handle` | |
| PMS-AFR-030 | PCC_ADMIN maintains panels and expertise | service | `services/rosters.py` | |
| PMS-AFR-037 | Attorneys record legal advice | service | `services/legal.py::record_advice` | |
| PMS-AFR-038 | Submit with title, abstract, description, claims, inventors, documents | domain | `domain/validation.py::missing_fields` | ≥ 1 document and ≥ 1 inventor |
| PMS-AFR-039 | Documents must be PDF | domain | `domain/documents.py::check_pdf` | |
| PMS-AFR-040 | Reject documents over 50 MB | domain | `domain/documents.py::check_size` | |
| PMS-AFR-041 | Malware-free before acceptance | service | `services/scanning.py::scan` | |
| PMS-AFR-042 | Validate completeness | domain | `domain/validation.py::missing_fields` | |
| PMS-AFR-043 | Classify documents by sensitivity | domain + db | `Document.sensitivity` with a CheckConstraint; set at upload (C16) | |
| PMS-AFR-044 | Unique application id | service + db | `services/applications.py::submit` → `PMS-<year>-<00001>` from a locked yearly counter; UniqueConstraint `pms_application_reference_unique` | |
| PMS-AFR-045 | Status Submitted after submission | domain | APPLICATION `submit` | |
| PMS-AFR-046 | Inventor agreements before filing | domain | `domain/filing.py::filing_blockers` | |
| PMS-AFR-047 | Application history | service | `services/audit.py::record` on every transition | |
| PMS-AFR-048 | Notify on submission and status updates | service | `services/notifications.py::enqueue` from `services/workflow.py::transition` | |
| PMS-AFR-049 | PCC_ADMIN assigns to Directors | service | `services/review.py::assign_director` | |
| PMS-AFR-050 | Optional automatic assignment | task | `services/routing.py::auto_route` | |
| PMS-AFR-051 | Expertise matching | domain | `domain/assignment.py::eligible_directors` | |
| PMS-AFR-052 | Workload balance | domain | `domain/assignment.py::rank_candidates` | |
| PMS-AFR-053 | Conflict check before assignment | domain | `domain/assignment.py::conflicts` | |
| PMS-AFR-054 | Directors never review own inventions | domain | `domain/assignment.py::conflicts` | |
| PMS-AFR-055 | PCC_ADMIN never reviews own inventions | service | `services/authz.py::refuse_if_conflicted` | |
| PMS-AFR-056 | Under Review on assignment | domain | APPLICATION `assign_director` | |
| PMS-AFR-057 | Notify the Director and start the timeline | service | `services/review.py::assign_director` sets `due_on`, enqueues notice | |
| PMS-AFR-058 | Directors view assigned application and documents | selector | `selectors/scoping.py::applications_for`, `document_versions_for` | |
| PMS-AFR-059 | Exactly one decision | domain | APPLICATION decide rows | |
| PMS-AFR-060 | Justification ≥ 50 | domain | `domain/validation.py::check_justification` | |
| PMS-AFR-061 | Review within 15 business days | domain | `domain/calendar.py::review_due` | |
| PMS-AFR-062 | Feedback notice on Reject | service | `services/review.py::decide` enqueues with the justification | |
| PMS-AFR-063 | Feedback notice on Needs Revision | service | as above | |
| PMS-AFR-064 | Approved routes to attorney assignment | selector | `selectors/oversight.py::awaiting_attorney` (PCC_ADMIN queue) | |
| PMS-AFR-065 | Audit trail of review | service | `services/audit.py::record` | |
| PMS-AFR-066 | Revise in Needs Revision | domain | APPLICATION `resubmit` | |
| PMS-AFR-067 | Revise in Rejected | domain | APPLICATION `resubmit` | |
| PMS-AFR-068 | Resubmit within 60 days | domain | `domain/calendar.py::revision_due` | |
| PMS-AFR-069 | Revision addresses feedback | domain | `domain/validation.py::check_revision_responses` | |
| PMS-AFR-070 | New review cycle after resubmission | service | `services/review.py::assign_director` opens cycle n+1 | |
| PMS-AFR-071 | Version control of revisions | service + db | `ApplicationVersion` snapshot per submission; UniqueConstraint `pms_appversion_unique` | |
| PMS-AFR-072 | Expired on missed deadline | task | `services/deadlines.py::expire_revisions` | |
| PMS-AFR-074 | Only PCC_ADMIN assigns attorneys | registry | `pms.attorney.assign` | |
| PMS-AFR-075 | Panel unless exception | domain | `domain/assignment.py::eligible_attorney` | |
| PMS-AFR-076 | Attorney expertise | domain | as above | |
| PMS-AFR-077 | Attorney workload | domain | `domain/assignment.py::rank_candidates` | |
| PMS-AFR-078 | Conflict check | domain | `domain/assignment.py::conflicts` | |
| PMS-AFR-079 | Preference only within the panel | domain | `domain/assignment.py::rank_candidates` | |
| PMS-AFR-080 | Attorney accepts or declines | domain | ASSIGNMENT `accept`, `decline` | |
| PMS-AFR-081 | Outcome: Attorney Assigned or Pending Review | domain | APPLICATION `attorney_accepted`, `attorney_declined` | |
| PMS-AFR-082 | Record legal and patentability analysis | service | `services/assessments.py::save` | |
| PMS-AFR-083 | Record prior-art searches | service | `services/prior_art.py::search` | |
| PMS-AFR-084 | Record novelty, non-obviousness, utility | service + db | `Assessment` fields; required to finalize (`domain/validation.py::check_opinion`) | |
| PMS-AFR-085 | Exactly one recommendation | domain + db | `check_opinion`; CheckConstraint | |
| PMS-AFR-086 | Request additional information | service | `services/legal.py::request(kind=info)` | Notifies the Applicant |
| PMS-AFR-087 | Request extensions | service | `services/legal.py::request(kind=extension)` | Recorded and notified; no clock exists to extend |
| PMS-AFR-088 | Record the opinion | service | `services/assessments.py::finalize` | Final opinions are immutable |
| PMS-AFR-089 | Notify after the opinion | service | `finalize` enqueues to the Applicant and reviewing Director | |
| PMS-AFR-090 | Directors review costs | selector | `selectors/scoping.py::budgets_for` | |
| PMS-AFR-091 | Directors approve costs | domain | BUDGET `approve` | |
| PMS-AFR-092 | Filing fees | domain + db | `Budget.filing_fee` | |
| PMS-AFR-093 | Attorney fees | domain + db | `Budget.attorney_fee` | |
| PMS-AFR-094 | Administrative costs | domain + db | `Budget.admin_cost` | |
| PMS-AFR-095 | Escalate above threshold | domain | `domain/budget.py::classify` | |
| PMS-AFR-096 | Approval only for Approved | domain | `domain/budget.py::application_allows_budget` | B5 |
| PMS-AFR-097 | Availability check where data exists | domain | `domain/budget.py::availability` | Conditional |
| PMS-AFR-098 | Log financial transactions with authorization level | service + db | `FinancialRecord` (append-only) written by `services/budget.py`, `services/maintenance.py` | |
| PMS-AFR-099 | Attorney prepares the filing package | service | `services/documents.py::upload(kind=filing_package)` by the assigned Attorney | |
| PMS-AFR-100 | Format validation where rules exist | domain | `domain/filing.py::format_validation` | Conditional |
| PMS-AFR-101 | Record Indian Patent Office filing | service | `services/filing.py::record_filing(office=IN)` | |
| PMS-AFR-102 | Record international filing | service | `services/filing.py::record_filing(office=INTL)` | |
| PMS-AFR-103 | Justify international filings | domain + db | `check_international_justification`; CheckConstraint | |
| PMS-AFR-104 | Capture filing id, date, confirmation for each filing | db | `Filing` NOT NULL columns; several filings per application (§3.8 Q-11) | |
| PMS-AFR-105 | Filed after recording | domain | APPLICATION `file` | |
| PMS-AFR-106 | Log official communications | service | `services/communications.py::record` | |
| PMS-AFR-107 | Post-grant tracking only when Granted | domain | `domain/post_grant.py::may_track` | |
| PMS-AFR-108 | Maintenance schedule where rules exist | domain | `domain/post_grant.py::schedule` | |
| PMS-AFR-109 | Attorneys manage reminders and deadlines | service | `services/maintenance.py::add_cycle` (manual due date) | Reminders via deadline alerts |
| PMS-AFR-110 | Explicit decision before each deadline | domain | MAINTENANCE guard `before_due_date` | |
| PMS-AFR-111 | Attorneys request the decision | domain | MAINTENANCE `request` | |
| PMS-AFR-112 | Directors decide Renew / Do Not Renew | domain | MAINTENANCE `renew`, `do_not_renew` | |
| PMS-AFR-113 | Record action, transaction and status | service | `services/maintenance.py::record_action` + `FinancialRecord` | |
| PMS-AFR-114 | Renewal history | db | `MaintenanceCycle` rows are never deleted | |
| PMS-AFR-115 | Schedule the next cycle | service | `record_action` creates cycle n+1 from the schedule | |
| PMS-AFR-116 | Record office actions | service | `services/communications.py::record(kind=office_action)` | |
| PMS-AFR-117 | Attorneys review office actions | selector | `selectors/scoping.py::office_actions_for` | |
| PMS-AFR-118 | Draft responses | domain | OFFICE_ACTION `prepare_*` | |
| PMS-AFR-119 | Applicant approves when needed | domain | OFFICE_ACTION `applicant_approve` | |
| PMS-AFR-120 | Finalize responses | domain | OFFICE_ACTION `prepare_ready`, or `submit` from Applicant Approved | |
| PMS-AFR-121 | Record submission within deadline | domain | `domain/office_actions.py::current_deadline` | |
| PMS-AFR-122 | Record extension requests | service | `services/office_actions.py::record_extension` | |
| PMS-AFR-123 | Track submission status | db | `OfficeAction.status` | |
| PMS-AFR-124 | Automate deadline tracking where data exists | task | `services/deadlines.py::sweep` | |
| PMS-AFR-125 | Withdraw before filing | domain | `domain/withdrawal.py::withdrawal_allowed` | |
| PMS-AFR-126 | Validate eligibility by status | domain | as above | |
| PMS-AFR-127 | Reason required | domain | `check_withdrawal_reason` | |
| PMS-AFR-128 | Co-inventor consent when required | domain | `domain/withdrawal.py::consent_complete` | |
| PMS-AFR-129 | Status Withdrawn | domain | APPLICATION `withdraw` | |
| PMS-AFR-130 | Remove from active queues | selector | queue selectors exclude terminal statuses (`domain/state_machine.py::TERMINAL`) | |
| PMS-AFR-131 | Withdrawal history | db | `Withdrawal` row + audit entry | |
| PMS-AFR-132 | Manage multiple inventors | service | `services/inventors.py::replace_inventors` | |
| PMS-AFR-133 | Manage ownership shares | service | as above | |
| PMS-AFR-134 | Validate inventor information | domain | `check_inventors` | |
| PMS-AFR-135 | Validate percentages | domain | `check_inventors` | |
| PMS-AFR-136 | Consent before filing | domain | `filing_blockers` | |
| PMS-AFR-137 | E-signature collection where configured | domain | not configured → never collected | Conditional |
| PMS-AFR-138 | E-signature validation where configured | domain | as above | Conditional |
| PMS-AFR-140 | Notify on inventor changes | service | `replace_inventors` enqueues to affected inventors who have an email | |
| PMS-AFR-141 | Applicants search prior art | service | `services/prior_art.py::search` | |
| PMS-AFR-142 | Attorneys search prior art | service | as above | |
| PMS-AFR-143 | Query patent databases where integrated | — | **Accepted gap G-3** | Sources shown "not connected" |
| PMS-AFR-144 | Query publication databases where integrated | — | **Accepted gap G-3** | |
| PMS-AFR-145 | Ranked results | domain | `domain/prior_art.py::rank` over references in the caller's scope | §3.8 S-2 |
| PMS-AFR-146 | Attach references | service | `services/prior_art.py::attach` | |
| PMS-AFR-147 | Log search sessions | service + db | `PriorArtSearch` row + audit entry | |
| PMS-AFR-148 | Keyword optimization | domain | `domain/prior_art.py::optimise_keywords` | |
| PMS-AFR-149 | Classification mapping | domain | `domain/prior_art.py::classification_suggestions` (IPC codes per area from the policy) + IPC format check | |
| PMS-AFR-150 | Version history | db | `DocumentVersion` rows | |
| PMS-AFR-151 | Upload per role and status | domain | `domain/documents.py::may_upload` | |
| PMS-AFR-152 | Automatic version numbers | service + db | `next_version` + unique constraint | |
| PMS-AFR-153 | Archive previous versions | db | `is_current` partial unique; old versions kept | |
| PMS-AFR-154 | Access previous versions per rules | domain | `domain/documents.py::may_read` | |
| PMS-AFR-155 | Log modifications with user and time | service | `DocumentVersion.uploaded_by_user_id/at` + audit entry | |
| PMS-AFR-156 | Access by role and status | domain | `may_read`, `may_upload` | |
| PMS-AFR-157 | Applicants edit only in Needs Revision | domain | `may_upload` (Needs Revision or Rejected, per B6) | B6 reading, recorded in the quality report |
| PMS-AFR-158 | Submit licensing requests | service | `services/licensing.py::submit(kind=licensing)` | |
| PMS-AFR-159 | Submit technology-transfer requests | service | `submit(kind=technology_transfer)` | |
| PMS-AFR-160 | Route to committee or Director | domain | `domain/licensing.py::route_target` | |
| PMS-AFR-161 | Track negotiation | service | `services/licensing.py::add_note` (append-only) | |
| PMS-AFR-162 | Document final agreements | service | `services/licensing.py::record_agreement` | |
| PMS-AFR-163 | Share with finance where integrated | service | records `financial_sync = NOT_AVAILABLE` | Conditional |
| PMS-AFR-164 | Confidential license records | selector | `selectors/scoping.py::licensing_for` | |
| PMS-AFR-165 | Appeal rejected applications | domain | APPLICATION `appeal` | |
| PMS-AFR-166 | Within the configured period | domain | `domain/appeals.py::appeal_open` | |
| PMS-AFR-167 | Grounds and justification | domain | `check_appeal_grounds` | |
| PMS-AFR-168 | Directors review appeals | selector + domain | `selectors/scoping.py`; APPEAL table actor DIRECTOR | Which Director: §3.8 Q-1 |
| PMS-AFR-169 | Three outcomes | domain | APPEAL table | |
| PMS-AFR-170 | Record outcomes | service + db | `Appeal.outcome`, audit | |
| PMS-AFR-171 | Initiate next steps | domain | APPEAL outcome → APPLICATION row (C8) | |
| PMS-AFR-172 | Monitor review deadlines | task | `services/deadlines.py::sweep` | |
| PMS-AFR-173 | Monitor revision deadlines | task | as above | |
| PMS-AFR-174 | Monitor office-action deadlines | task | as above | |
| PMS-AFR-175 | Monitor maintenance deadlines | task | as above | |
| PMS-AFR-176 | 30-day alerts | domain + task | `alerts_due` | |
| PMS-AFR-177 | 15-day alerts | domain + task | `alerts_due` | |
| PMS-AFR-178 | 5-day alerts | domain + task | `alerts_due` | |
| PMS-AFR-179 | Deadline notices to stakeholders | service | `services/deadlines.py` → `notifications.enqueue` | |
| PMS-AFR-180 | Escalate missed deadlines | service | `services/escalations.py::raise_case` | |
| PMS-AFR-181 | Log deadline tracking | db | `DeadlineAlert`, `Escalation` rows + audit | |
| PMS-AFR-182 | Status and progress reports | selector | `selectors/reports.py` type `status` | |
| PMS-AFR-183 | Financial and budget reports | selector | type `financial` | |
| PMS-AFR-184 | Deadline and pending-action reports | selector | type `deadlines` | |
| PMS-AFR-185 | Inventor reports | selector | type `inventors` | |
| PMS-AFR-186 | Portfolio analysis | selector | type `portfolio` | |
| PMS-AFR-187 | Workload and assignment reports | selector | type `workload` | |
| PMS-AFR-188 | Schedule reports | task + service | `services/reports.py::run_scheduled` | §3.8 S-1 |
| PMS-AFR-189 | Export reports | service | `services/reports.py::export` via `core/api/csv.py` | |
| PMS-AFR-190 | Customize reports | service | `ReportDefinition` filters and columns | |
| PMS-AFR-191 | Log report access | service | `services/audit.py::record(action=report.viewed)` | |
| PMS-AFR-192 | Email on submission | service | `notifications.enqueue` topic `application.submitted` | |
| PMS-AFR-193 | Email on status change | service | `workflow.transition` | |
| PMS-AFR-194 | Email on Director assignment | service | `review.assign_director` | |
| PMS-AFR-195 | Email on Attorney assignment | service | `attorneys.assign_attorney` | |
| PMS-AFR-196 | Email on review decisions | service | `review.decide` | |
| PMS-AFR-197 | Email on budget decisions | service | `budget.decide` | |
| PMS-AFR-198 | Email on filing confirmation | service | `filing.record_filing` | |
| PMS-AFR-199 | Email on office actions | service | `communications.record` | |
| PMS-AFR-200 | Email deadline reminders | task | `deadlines.sweep` | |
| PMS-AFR-201 | Email escalations | task | `escalations.raise_case` | |
| PMS-AFR-202 | Email maintenance reminders | task | `deadlines.sweep` for cycles | |
| PMS-AFR-203 | Email on document updates | service | `documents.upload` | |
| PMS-AFR-204 | Email on version changes | service | `documents.upload` (version > 1) | |
| PMS-AFR-206 | PMS only triggers email | service | `notifications.deliver_pending` | |
| PMS-AFR-207 | Audit trail of actions | service | `services/audit.py::record` | |
| PMS-AFR-208 | Log all user actions | service | every service write calls `audit.record` | Reads logged for reports and audit views |
| PMS-AFR-209 | Log all status changes | service | `workflow.transition`, `transition_record` | |
| PMS-AFR-210 | Log document modifications | service | `documents.upload`, `set_sensitivity` | |
| PMS-AFR-211 | Required audit attributes | db | `AuditEntry` columns | |
| PMS-AFR-212 | Immutable records for critical operations | db | trigger + model guards | |
| PMS-AFR-213 | Audit logs for compliance | selector | `selectors/audit.py` + export | |
| PMS-AFR-214 | Encryption at rest | platform | database and disk encryption are the deployment's | Nothing in PMS to enforce |
| PMS-AFR-215 | Encryption in transit | platform | TLS at nginx | Nothing in PMS to enforce |
| PMS-AFR-216 | Valid role required | registry | `HasModuleGrant("pms")` + permission on every view | |
| PMS-AFR-217 | No attorney assignment before approval | domain | ASSIGNMENT guard | |
| PMS-AFR-218 | No filing before approvals and budget | domain | `filing_blockers` | |
| PMS-AFR-220 | Role-based access to confidential data | selector | `selectors/scoping.py` | |
| PMS-AFR-221 | Exactly one active PCC_ADMIN | platform | **Accepted gap G-2** | |
| PMS-AFR-222 | Multiple Directors by expertise | db | `DirectorProfile` roster, one active row per person | |
| PMS-AFR-223 | Multiple panel attorneys | db | `PanelAttorney` roster | |
| PMS-AFR-224 | Multiple Applicants | registry | `student`, `faculty`, `staff` hold the applicant grant | |
| PMS-AFR-225 | Status-driven transitions | domain | `domain/state_machine.py` tables + `services/workflow.py` | |
| PMS-AFR-226 | Escalation for delayed actions | task | `services/escalations.py` | |
| PMS-AFR-227 | Parallel processing only where defined | domain | only the budget and attorney tracks run in parallel (CW-PMS-02, B5) | |
| PMS-AFR-228 | Patent office external | service | no outbound integration; records only | |
| PMS-AFR-229 | Finance external | service | `NOT_AVAILABLE` recorded | |
| PMS-AFR-230 | Document management external | service | PMS stores its own versions only | |
| PMS-AFR-231 | Prior-art databases are query sources | domain | `domain/prior_art.py::SOURCES` | |
| PMS-AFR-232 | Filing success not internally controlled | domain | `filing_blockers` needs external confirmation | |
| PMS-AFR-236 | Directors reject budgets | domain | BUDGET `reject` | |
| PMS-AFR-237 | Dashboards | selector | report type `dashboard` | |
| PMS-AFR-238 | Historical analysis | selector | report type `history` (counts by month) | |
| PMS-AFR-239 | Trend reporting | selector | report type `trend` (month-on-month change) | |

---

## 3.2 (b) Domain model

Every person is a plain integer `user_id` (`core.db.mixins.UserScopedModel` where the row
belongs to one person). No foreign key leaves the module. Money is `Decimal(12,2)` in rupees. All
models carry `created_at`/`updated_at` from `TimeStampedModel` unless marked append-only.

| Model (file) | Key fields | Invariants in the database |
|---|---|---|
| `Application` (`models/applications.py`) | `reference`, `applicant_user_id`, `title`, `abstract`, `description`, `claims`, `domain_code`, `preferred_attorney_user_id`, `status`, `version`, `submitted_at`, `decided_at`, `revision_due_on`, `appeal_due_on`, `grant_date`, `patent_number` | CheckConstraint `pms_application_status_valid`; `pms_application_reference_when_submitted` (reference NULL only in Draft); UniqueConstraint `pms_application_reference_unique` (partial, reference not null); `pms_application_granted_has_grant` |
| `ReferenceCounter` | `year`, `last` | PK on `year`; row locked with `select_for_update` to number submissions |
| `ApplicationVersion` (append-only) | `application`, `version`, content snapshot, `created_by_user_id` | UniqueConstraint `pms_appversion_unique (application, version)` |
| `Inventor` | `application`, `user_id` (nullable), `name`, `email`, `affiliation`, `share_percent`, `agreement_completed_at`, `consent_recorded_at`, `agreement_reference` | `pms_inventor_share_range` (0 < share ≤ 100); partial unique `pms_inventor_user_once (application, user_id)` |
| `ReviewCycle` | `application`, `cycle_no`, `director_user_id`, `assigned_by_user_id` (NULL = automatic), `assigned_at`, `due_on`, `status` (open, decided, reassigned, closed), `decision`, `justification`, `decided_at` | partial unique `pms_review_one_open (application) WHERE status='open'`; unique `(application, cycle_no)`; `pms_review_decided_complete` |
| `RevisionResponse` (append-only) | `application`, `review_cycle`, `version`, `response` | `response` length ≥ 50 is checked in the domain |
| `Appeal` | `application`, `rejected_cycle`, `director_user_id`, `grounds`, `justification`, `status`, `outcome`, `modified_decision`, `outcome_note`, `decided_at` | partial unique `pms_appeal_one_open`; `pms_appeal_modify_has_decision` |
| `Withdrawal` + `WithdrawalConsent` (append-only) | `application` (one-to-one), `from_status`, `reason`, consents per inventor | one per application |
| `DirectorProfile` (roster, effective-dated) | `user_id`, `domain_codes`, `valid_from`, `valid_to`, `added_by_user_id` | partial unique `pms_director_one_active (user_id) WHERE valid_to IS NULL`. Changing a profile ends the row and adds a new one |
| `PanelAttorney` (roster, effective-dated) | same shape | partial unique `pms_panel_one_active` |
| `AttorneyAssignment` | `application`, `attorney_user_id`, `assigned_by_user_id`, `is_exception`, `exception_reason`, `status` (offered, accepted, declined, cancelled), `responded_at`, `decline_reason` | partial unique `pms_assignment_one_live (application) WHERE status IN ('offered','accepted')`; `pms_assignment_exception_has_reason` |
| `Assessment` | `application`, `attorney_user_id`, `analysis`, `novelty`, `non_obviousness`, `utility`, `recommendation`, `status` (draft, final), `finalized_at` | `pms_assessment_final_has_recommendation` |
| `LegalRequest`, `LegalAdvice` (append-only) | `application`, `attorney_user_id`, `kind` / `stage`, text | — |
| `Budget` | `application`, `proposed_by_user_id`, `filing_fee`, `attorney_fee`, `admin_cost`, `total`, `status`, `decided_by_user_id`, `threshold_at_decision`, `availability`, `routed_to`, `external_reference`, `external_decided_on` | `pms_budget_components_nonnegative`; `pms_budget_total_is_sum`; partial unique `pms_budget_one_open`; partial unique `pms_budget_one_approved` |
| `FinancialRecord` (append-only) | `application`, `budget`/`maintenance_cycle`, `kind`, `amount`, `authorization_level`, `recorded_by_user_id`, `reference` | — |
| `Filing` | `application`, `office` (IN, INTL), `office_name`, `international_justification`, `external_filing_id`, `filing_date`, `confirmation_reference`, `format_validation`, `filed_by_user_id` | `pms_filing_international_justified`; unique `pms_filing_external_id (office_name, external_filing_id)` |
| `Communication` | `application`, `kind` (office_action, grant, refusal, other), `received_on`, `reference`, `details`, `recorded_by_user_id` | — |
| `OfficeAction` + `OfficeActionExtension` | `communication` (one-to-one), `response_due_on`, `requires_applicant_review`, `status`, `draft_response`, `approved_by_user_id`, `submitted_on`, `submission_reference` | `pms_oa_submitted_complete` |
| `MaintenanceCycle` | `application`, `seq`, `due_on`, `source` (schedule, manual), `status`, `deciding_director_user_id`, `decided_at`, `action_reference`, `amount`, `actioned_on` | unique `(application, seq)`; partial unique `pms_maintenance_one_live` |
| `LicensingRequest`, `NegotiationNote` (append-only), `LicenseAgreement` | `application`, `applicant_user_id`, `kind`, `summary`, `status`, `route_kind`, `routed_director_user_id`, `committee_name`; agreement `counterparty`, `signed_on`, `terms_summary`, `financial_sync` | one agreement per request |
| `Document`, `DocumentVersion` | `application`, `kind`, `title`, `sensitivity`; version `number`, `storage_key`, `original_name`, `size_bytes`, `sha256`, `scanner`, `uploaded_by_user_id`, `is_current` | `pms_document_sensitivity_valid`; `pms_docversion_size_range`; unique `pms_docversion_number_unique`; partial unique `pms_docversion_one_current`; unique `storage_key` |
| `PriorArtSearch` (append-only), `PriorArtReference` | search: `actor_user_id`, `application`, `query`, `keywords`, `classification_codes`, `result_reference_ids`; reference: `application`, `kind`, `title`, `identifier`, `url`, `notes` | partial unique `pms_reference_once (application, identifier)` |
| `PmsPolicy` (effective-dated, never edited) | `version`, `effective_from`, `published_by_user_id`, `cost_threshold`, `appeal_period_days`, `alert_offsets_days`, `withdrawal_statuses`, `withdrawal_consent_required`, `holidays`, `domains` (code, label, IPC classes), `maintenance_rules` (jurisdiction → months after grant), `escalation_chain` (user ids), `pcc_contact_user_id`, `auto_routing_enabled`, `licensing_route` | unique `version`; save refuses an update; publishing requires `based_on_version` = current, else 409 |
| `Escalation` | `kind` (missed_review, missed_revision, missed_office_action, missed_maintenance, no_eligible_director, no_eligible_attorney, conflicted_admin, budget_threshold), `application`, `subject_id`, `deadline`, `status` (open, routed, resolved), `note`, `handled_by_user_id` | partial unique `pms_escalation_open_once (kind, subject_id) WHERE status='open'` |
| `DeadlineAlert` (append-only) | `kind`, `subject_id`, `deadline`, `offset_days` | unique `pms_alert_once (kind, subject_id, deadline, offset_days)` |
| `AuditEntry` (append-only, immutable) | `at`, `actor_user_id` (NULL = system), `actor_role`, `action`, `application`, `object_type`, `object_id`, `from_state`, `to_state`, `details` (ids and codes only) | trigger `pms_auditentry_immutable` refuses UPDATE and DELETE |
| `Notification` (outbox) | `topic`, `dedupe_key`, `recipient_user_id`, `subject`, `body`, `status`, `attempts`, `next_attempt_at` | unique `dedupe_key` |
| `ReportDefinition`, `ReportRun` | owner, `owner_role`, `report_type`, `filters`, `columns`, `schedule` (none, weekly, monthly), `active`; run: CSV text, `generated_at` | — |

**Policy with nothing published.** `domain/policy.py::DEFAULTS` applies: appeal period 30 days
(B7), alert offsets 30/15/5, every other value empty. Each action that needs an empty value is
refused with a sentence naming the setting (for example: *"No budget threshold is configured.
Ask the PCC_ADMIN to set one under Settings before a budget can be decided."*). The setup
checklist (§3.5, `GET /setup`) and the readiness command list the same gaps.

**Indexes.** Each one serves a named query:

- `pms_app_applicant_idx (applicant_user_id, -created_at)`: My Applications
- `pms_app_status_idx (status, -updated_at)`: PCC_ADMIN queues
- `pms_app_domain_status_idx (domain_code, status)`: Director oversight
- `pms_review_director_open_idx (director_user_id) WHERE status='open'`: Director queue and workload
- `pms_review_due_idx (due_on) WHERE status='open'`: deadline sweep
- `pms_app_revision_due_idx (revision_due_on) WHERE status IN ('needs_revision','rejected')`: expiry sweep
- `pms_assignment_attorney_live_idx (attorney_user_id) WHERE status IN ('offered','accepted')`: Attorney queue and workload
- `pms_oa_due_idx (response_due_on) WHERE status <> 'submitted'`: office-action deadlines
- `pms_cycle_due_idx (due_on) WHERE status IN ('scheduled','decision_requested','renew_approved')`: maintenance deadlines
- `pms_audit_app_idx (application, -at)`, `pms_audit_actor_idx (actor_user_id, -at)`, `pms_audit_action_idx (action, -at)`: audit views
- `pms_notification_pending_idx (status, next_attempt_at)`: delivery
- `pms_escalation_open_idx (status, -created_at)`: monitoring

**Files.** Stored under a new `PMS_UPLOAD_ROOT` (outside the repository; checked at startup by a
PMS system check), named by a random key, mode 0600. Served only by
`GET /documents/versions/{id}/download` after scope and sensitivity checks, as an attachment
with `nosniff`. Original names pass through `core.files.validators.sanitise_filename`.

**Malware scanning.** `services/scanning.py` speaks ClamAV's `INSTREAM` protocol over a socket,
using only the standard library, so no Python dependency is added. It reads `PMS_CLAMD_SOCKET`
(or host and port). No setting → `ScannerUnavailable` → the upload and the submission are
refused (A1, UC-001 exception flow). A development scanner for local and CI use is proposed in
§3.8 H-2.

---

## 3.3 (c) State machines

All tables live in `domain/state_machine.py` as tuples of `Transition(frm, event, actor, to,
guards)`. A pair (state, event) that is not in a table cannot be executed. `resolve()` raises
`InvalidTransition`, which the service layer maps to 409. Actors: `APPLICANT`, `DIRECTOR`,
`PCC_ADMIN`, `ATTORNEY`, `SYSTEM`. The actor is derived in `services/authz.py::actor_kind` from
the acting role's permissions **and** the person's relation to the record. A Director acting on
an application they are not assigned to is not a DIRECTOR for that row.

### APPLICATION

| From | Event | Actor | To | Guards |
|---|---|---|---|---|
| draft | submit | APPLICANT | submitted | owner; `missing_fields` empty; every document scanned clean |
| submitted, resubmitted | assign_director | PCC_ADMIN, SYSTEM | under_review | eligible, unconflicted Director (BR-023..027); not a conflicted PCC_ADMIN |
| under_review | reassign_director | PCC_ADMIN | under_review | open cycle is past its due date or the Director's profile has ended |
| under_review | approve | DIRECTOR | approved | assigned; unconflicted; justification ≥ 50; within the review deadline |
| under_review | request_revision | DIRECTOR | needs_revision | same; sets `revision_due_on` = decision date + 60 days |
| under_review | reject | DIRECTOR | rejected | same; sets `revision_due_on` and `appeal_due_on` |
| needs_revision, rejected | resubmit | APPLICANT | resubmitted | owner; before `revision_due_on`; feedback answered; at least one change |
| rejected | appeal | APPLICANT | appeal_submitted | before `appeal_due_on` and `revision_due_on`; grounds; clears the revision clock |
| appeal_submitted | appeal_remanded | SYSTEM (from APPEAL) | needs_revision | new 60-day clock |
| appeal_submitted | appeal_modified_approve | SYSTEM (from APPEAL) | approved | |
| appeal_submitted | appeal_modified_revise | SYSTEM (from APPEAL) | needs_revision | new 60-day clock |
| appeal_submitted | appeal_upheld | SYSTEM (from APPEAL) | rejection_upheld | |
| approved, pending_review | attorney_accepted | SYSTEM (from ASSIGNMENT) | attorney_assigned | |
| approved | attorney_declined | SYSTEM (from ASSIGNMENT) | pending_review | |
| pending_review | attorney_declined | SYSTEM (from ASSIGNMENT) | pending_review | another decline |
| attorney_assigned | file | ATTORNEY | filed | assigned, accepted Attorney; `filing_blockers` empty |
| filed | grant | ATTORNEY | granted | grant communication with date and patent number |
| filed | refuse | ATTORNEY | refused | refusal communication with date and reference |
| needs_revision, rejected | expire | SYSTEM | expired | `revision_due_on` passed |
| submitted, under_review, needs_revision, rejected, approved, attorney_assigned, pending_review | withdraw | APPLICANT | withdrawn | status in `policy.withdrawal_statuses`; reason; consent if required |

Final statuses: `withdrawn`, `expired`, `rejection_upheld`, `refused`. `granted` stays open for
maintenance. No row leaves a final status. Withdrawal closes the open review cycle, cancels an
offered assignment and closes an open budget in the same transaction.

### ASSIGNMENT (attorney)

| From | Event | Actor | To | Guards |
|---|---|---|---|---|
| — | offer | PCC_ADMIN | offered | application in {approved, pending_review}; eligible attorney or recorded exception; unconflicted; no live assignment |
| offered | accept | ATTORNEY | accepted | the offered attorney |
| offered | decline | ATTORNEY | declined | the offered attorney; reason; notifies PCC_ADMIN |
| offered | cancel | SYSTEM | cancelled | application withdrawn |

### BUDGET

| From | Event | Actor | To | Guards |
|---|---|---|---|---|
| — | propose | ATTORNEY | proposed | the accepted attorney; application in B5's set; components ≥ 0; no open budget; no approved budget |
| proposed | approve | DIRECTOR | approved | the reviewing Director; threshold configured; total ≤ threshold; availability checked where data exists |
| proposed | reject | DIRECTOR | rejected | same Director; threshold configured |
| proposed | escalate | DIRECTOR | escalated | same Director; total > threshold (the Director's decision request lands here automatically) |
| escalated | route | PCC_ADMIN | escalation_tracked | `routed_to` named |
| escalation_tracked | record_external_approval | PCC_ADMIN | external_approved | reference and date (C14) |
| escalation_tracked | record_external_rejection | PCC_ADMIN | external_rejected | reference and date |
| proposed, escalated, escalation_tracked | close | SYSTEM | closed | application withdrawn |

### OFFICE_ACTION

| From | Event | Actor | To | Guards |
|---|---|---|---|---|
| recorded | prepare_for_applicant | ATTORNEY | awaiting_applicant_approval | `requires_applicant_review`; draft text |
| recorded | prepare_ready | ATTORNEY | response_ready | not `requires_applicant_review`; draft text |
| awaiting_applicant_approval | applicant_approve | APPLICANT | applicant_approved | the application's Applicant |
| applicant_approved, response_ready | submit | ATTORNEY | submitted | submitted on or before the current deadline (after extensions); reference |

Extensions add an `OfficeActionExtension` row and move the deadline without a status change.

### MAINTENANCE

| From | Event | Actor | To | Guards |
|---|---|---|---|---|
| scheduled | request | ATTORNEY | decision_requested | application granted |
| decision_requested | renew | DIRECTOR | renew_approved | the deciding Director; on or before `due_on` |
| decision_requested | do_not_renew | DIRECTOR | do_not_renew | same |
| renew_approved | record_action | ATTORNEY | renewed | reference and amount; schedules cycle n+1 when the schedule has one |
| decision_requested | reassign_decider | PCC_ADMIN | decision_requested | the deciding Director's profile has ended (C19) |

### APPEAL

| From | Event | Actor | To |
|---|---|---|---|
| open | uphold / remand / modify | DIRECTOR | decided (outcome recorded; drives the APPLICATION row) |

### LICENSING

| From | Event | Actor | To |
|---|---|---|---|
| submitted | route | SYSTEM at submission, or PCC_ADMIN later | routed |
| routed | add_note | DIRECTOR (routed), PCC_ADMIN | negotiating |
| negotiating | record_agreement | DIRECTOR (routed), PCC_ADMIN | agreement_recorded |

**Choke points.** `services/workflow.py::transition(application_id, event, actor, **ctx)` is the
only code that writes `Application.status`. In one transaction it:

1. takes `select_for_update` on the application
2. refuses a final status
3. resolves the table row for the actor
4. runs the guards in a fixed order, most useful message first (state, then actor, then deadline, then content)
5. writes the status
6. writes the audit entry
7. enqueues the notifications

`transition_record(model, pk, event, actor, **ctx)` does the same for the other tables. A change
that touches both (an appeal decision, an attorney accepting) runs inside one atomic block,
locking the record first and then the application.

---

## 3.4 (d) Registry

```python
MODULE = {
    "code": "pms", "label": "Patent Management", "icon": "Lightbulb",
    "base_path": "/pms", "nav_section": "Research", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "pms.applications", "label": "My Applications", "icon": "FileText",
     "to": "/pms/applications", "required_permission": "pms.application.create",
     "sort_order": 10},
    {"code": "pms.reviews", "label": "Reviews", "icon": "Gavel",
     "to": "/pms/reviews", "required_permission": "pms.review.approve", "sort_order": 20},
    {"code": "pms.cases", "label": "Assigned Cases", "icon": "Briefcase",
     "to": "/pms/cases", "required_permission": "pms.attorney_assignment.review",
     "sort_order": 30},
    {"code": "pms.assignments", "label": "Assignments", "icon": "UserSwitch",
     "to": "/pms/assignments", "required_permission": "pms.review.assign", "sort_order": 40},
    {"code": "pms.monitoring", "label": "Deadlines & Escalations", "icon": "Alarm",
     "to": "/pms/monitoring", "required_permission": "pms.escalation.review",
     "sort_order": 50},
    {"code": "pms.oversight", "label": "Oversight", "icon": "Binoculars",
     "to": "/pms/oversight", "required_permission": "pms.workflow.view", "sort_order": 60},
    {"code": "pms.prior_art", "label": "Prior Art Search", "icon": "MagnifyingGlass",
     "to": "/pms/prior-art", "required_permission": "pms.prior_art.create", "sort_order": 70},
    {"code": "pms.licensing", "label": "Licensing", "icon": "Handshake",
     "to": "/pms/licensing", "required_permission": "pms.licensing_request.view",
     "sort_order": 80},
    {"code": "pms.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/pms/reports", "required_permission": "pms.report.view", "sort_order": 90},
    {"code": "pms.audit", "label": "Audit Log", "icon": "ListMagnifyingGlass",
     "to": "/pms/audit", "required_permission": "pms.audit_log.view", "sort_order": 100},
    {"code": "pms.directors", "label": "Directors", "icon": "UsersThree",
     "to": "/pms/directors", "required_permission": "pms.director_profile.update",
     "sort_order": 110},
    {"code": "pms.attorney_panel", "label": "Attorney Panel", "icon": "Scales",
     "to": "/pms/attorney-panel", "required_permission": "pms.attorney_panel.update",
     "sort_order": 120},
    {"code": "pms.settings", "label": "Settings", "icon": "GearSix",
     "to": "/pms/settings", "required_permission": "pms.policy.publish", "sort_order": 130},
]

PERMISSIONS = [
    ("pms.application.view", "See applications within one's scope"),
    ("pms.application.create", "Draft and submit a patent application"),
    ("pms.application.update", "Edit and resubmit one's own application"),
    ("pms.inventor.update", "Maintain an application's inventors and agreements"),
    ("pms.withdrawal.create", "Withdraw one's own application"),
    ("pms.appeal.create", "Appeal a rejection"),
    ("pms.appeal.review", "Decide an appeal"),
    ("pms.review.assign", "Assign or reassign an application to a Director"),
    ("pms.review.approve", "Record a review decision on an assigned application"),
    ("pms.director_profile.update", "Maintain Directors' expertise areas"),
    ("pms.attorney_panel.update", "Maintain the approved attorney panel"),
    ("pms.attorney.assign", "Assign an attorney to an approved application"),
    ("pms.attorney_assignment.review", "Accept or decline an attorney assignment"),
    ("pms.assessment.create", "Record a patentability assessment"),
    ("pms.legal_request.create", "Ask the applicant for information or an extension"),
    ("pms.legal_advice.create", "Record legal advice"),
    ("pms.budget.create", "Propose a filing and prosecution budget"),
    ("pms.budget.approve", "Approve or reject a budget"),
    ("pms.filing.create", "Record an external patent filing"),
    ("pms.communication.create", "Record a patent-office communication"),
    ("pms.office_action_response.create", "Prepare an office-action response"),
    ("pms.office_action_response.update", "Record a response's submission or extension"),
    ("pms.office_action_response.approve", "Approve a response as the applicant"),
    ("pms.maintenance.update", "Track maintenance and record maintenance actions"),
    ("pms.renewal.approve", "Decide Renew or Do Not Renew"),
    ("pms.renewal.assign", "Reassign a renewal decision to another Director"),
    ("pms.document.view", "Read application documents within one's scope"),
    ("pms.document.create", "Upload a document or a new version"),
    ("pms.document.update", "Change a document's sensitivity level"),
    ("pms.prior_art.view", "See prior-art references within one's scope"),
    ("pms.prior_art.create", "Search prior art and attach references"),
    ("pms.licensing_request.view", "See licensing requests within one's scope"),
    ("pms.licensing_request.create", "Submit a licensing or technology-transfer request"),
    ("pms.licensing_request.review", "Route, negotiate and record licensing agreements"),
    ("pms.escalation.review", "Monitor deadlines and handle escalations"),
    ("pms.workflow.view", "See workflow oversight"),
    ("pms.report.view", "See reports within one's scope"),
    ("pms.report.export", "Export reports"),
    ("pms.report_definition.create", "Save and schedule report definitions"),
    ("pms.audit_log.view", "See audit logs within one's scope"),
    ("pms.audit_log.export", "Export audit logs"),
    ("pms.policy.publish", "Publish a new PMS settings version"),
]

#: Performed only by scheduled work.
SYSTEM_PERMISSIONS = [
    "pms.deadline.manage",      # expiry, alerts and escalations in one sweep
    "pms.routing.assign",       # automatic Director assignment
]
# `manage` because one sweep expires, alerts and escalates; no single verb names it.

#: Read only in selectors to narrow rows; none — every scope here follows an enforced permission.
SCOPE_PERMISSIONS: list[str] = []

_APPLICANT = [
    "pms.application.view", "pms.application.create", "pms.application.update",
    "pms.inventor.update", "pms.withdrawal.create", "pms.appeal.create",
    "pms.document.view", "pms.document.create",
    "pms.prior_art.view", "pms.prior_art.create",
    "pms.office_action_response.approve",
    "pms.licensing_request.view", "pms.licensing_request.create",
    "pms.report.view",
]
_DIRECTOR = [
    "pms.application.view", "pms.review.approve", "pms.appeal.review",
    "pms.budget.approve", "pms.renewal.approve",
    "pms.document.view", "pms.prior_art.view",
    "pms.licensing_request.view", "pms.licensing_request.review",
    "pms.workflow.view", "pms.report.view", "pms.report.export",
    "pms.report_definition.create", "pms.audit_log.view",
]
_PCC_ADMIN = [
    "pms.application.view", "pms.review.assign", "pms.attorney.assign",
    "pms.director_profile.update", "pms.attorney_panel.update",
    "pms.renewal.assign", "pms.escalation.review", "pms.workflow.view",
    "pms.document.view", "pms.document.create", "pms.document.update",
    "pms.prior_art.view",
    "pms.licensing_request.view", "pms.licensing_request.review",
    "pms.report.view", "pms.report.export", "pms.report_definition.create",
    "pms.audit_log.view", "pms.audit_log.export", "pms.policy.publish",
]
_ATTORNEY = [
    "pms.application.view", "pms.attorney_assignment.review",
    "pms.assessment.create", "pms.legal_request.create", "pms.legal_advice.create",
    "pms.budget.create", "pms.filing.create", "pms.communication.create",
    "pms.office_action_response.create", "pms.office_action_response.update",
    "pms.maintenance.update", "pms.document.view", "pms.document.create",
    "pms.prior_art.view", "pms.prior_art.create",
]

#: Keyed by designation name; the three pms_* names are new (ruling A4).
ROLE_GRANTS = {
    "student": _APPLICANT,      # PS 2.2.1, UC-PMS-001; ruling A4
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "pms_director": _DIRECTOR,      # PS 2.2.2; UC-PMS-008, 009, 018, 023, 031, 032
    "pms_pcc_admin": _PCC_ADMIN,    # PS 2.2.3; UC-PMS-007, 010, 016, 024–028
    "pms_attorney": _ATTORNEY,      # PS 2.2.4; UC-PMS-011–015, 017, 033
}
```

Every verb is from `rbac-model.md`'s closed list. All four roles use the same codes; what
differs between them is the rows each sees (`selectors/scoping.py`).

The display names Director, PCC_ADMIN and Attorney appear in PMS's own screens. The role
switcher shows the IAM designation name. The designation `full_name` is set by the IAM when
`assign_role` creates it, which this module does not control.

**Scope (`selectors/scoping.py`, out of scope → 404):**

- **PCC_ADMIN** (holds `pms.review.assign`): every application except other people's drafts.
- **Director** (holds `pms.review.approve`): applications where they hold any review cycle, the
  appeal, the renewal decision or the budget decision; plus, read-only, non-draft applications
  in their active profile's areas.
- **Attorney** (holds `pms.attorney_assignment.review`): applications with an offered or accepted
  assignment to them.
- **Applicant**: own applications; read-only, those listing them as an institute-user inventor
  (§3.8 Q-10).
- **Licensing**: applicant, routed Director, PCC_ADMIN.
- **Audit**: PCC_ADMIN all; Director within the Director application scope above.

---

## 3.5 (e) Endpoints

All paths sit under `/api/v1/pms/`. Every view carries the module gate
`HasModuleGrant("pms")` first, then `HasPermission(<code>)`, then narrows rows through
`selectors/scoping.py`. Writes carry a `throttle_scope`. Every view has `@extend_schema` with
request and response examples.

| # | Method and path | Permission | Returns | Ids |
|---|---|---|---|---|
| 1 | GET `applications` | application.view | page of scoped applications (filters: status, domain, `q`) | UC-002, UC-032, AFR-010 |
| 2 | POST `applications` | application.create | 201 draft | UC-001 |
| 3 | GET `applications/{id}` | application.view | detail with inventors, cycles, feedback, budget, filings, cycles | UC-002, AFR-058 |
| 4 | PATCH `applications/{id}` | application.update | updated draft or revision | UC-001, UC-005, BR-045 |
| 5 | POST `applications/{id}/submit` | application.create | submitted application | BR-014..017, AFR-044, 045 |
| 6 | GET `applications/{id}/history` | application.view | audit entries for the application | AFR-047 |
| 7 | PUT `applications/{id}/inventors` | inventor.update | the inventor set | UC-003, BR-073, 074 |
| 8 | POST `applications/{id}/inventors/{inv}/agreement` | inventor.update | inventor | BR-075, 078 |
| 9 | POST `applications/{id}/resubmit` | application.update | resubmitted application | UC-005, BR-033..036 |
| 10 | POST `applications/{id}/withdraw` | withdrawal.create | withdrawn application | UC-006, BR-067..070 |
| 11 | POST `applications/{id}/appeal` | appeal.create | appeal | UC-022, BR-092..094 |
| 12 | GET `applications/{id}/director-candidates` | review.assign | ranked eligible Directors | BR-023..025 |
| 13 | POST `applications/{id}/assign-director` | review.assign | review cycle | UC-007 |
| 14 | POST `applications/{id}/review` | review.approve | decided cycle | UC-008, BR-029..031 |
| 15 | POST `appeals/{id}/decision` | appeal.review | appeal | UC-023, BR-095 |
| 16 | GET `attorney-panel` | attorney_panel.update or attorney.assign | panel with areas and workload | UC-026 |
| 17 | GET `attorney-panel/options` | application.create | panel names and areas only (for preference) | BR-045 |
| 18 | POST `attorney-panel` | attorney_panel.update | member | UC-026 |
| 19 | POST `attorney-panel/{id}/end` | attorney_panel.update | ended member | UC-026 |
| 20 | GET `applications/{id}/attorney-candidates` | attorney.assign | ranked attorneys | BR-041..045 |
| 21 | POST `applications/{id}/assign-attorney` | attorney.assign | assignment | UC-010, BR-040, 127 |
| 22 | POST `attorney-assignments/{id}/respond` | attorney_assignment.review | assignment | UC-011 |
| 23 | GET `directors` | director_profile.update | roster | AFR-222 |
| 24 | POST `directors` | director_profile.update | profile | C13 |
| 25 | POST `directors/{id}/end` | director_profile.update | ended profile | C13 |
| 26 | POST `applications/{id}/assessments` | assessment.create | draft assessment | UC-012 |
| 27 | POST `assessments/{id}/finalize` | assessment.create | final assessment | BR-046 |
| 28 | POST `applications/{id}/legal-requests` | legal_request.create | request | AFR-086, 087 |
| 29 | POST `applications/{id}/legal-advice` | legal_advice.create | advice | UC-033 |
| 30 | POST `applications/{id}/budgets` | budget.create | budget | UC-009, BR-048..050 |
| 31 | POST `budgets/{id}/decision` | budget.approve | budget (approved, rejected or escalated) | BR-051..053 |
| 32 | POST `budgets/{id}/route` | escalation.review | budget | BW-PMS-10 |
| 33 | POST `budgets/{id}/external-decision` | escalation.review | budget | C14 |
| 34 | POST `applications/{id}/filings` | filing.create | filing | UC-013, BR-020, 055, 056, 128 |
| 35 | POST `applications/{id}/communications` | communication.create | communication (plus office action) | UC-014, C9 |
| 36 | POST `office-actions/{id}/response` | office_action_response.create | office action | UC-015 |
| 37 | POST `office-actions/{id}/approve` | office_action_response.approve | office action | UC-029, BR-146 |
| 38 | POST `office-actions/{id}/submission` | office_action_response.update | office action | BR-065 |
| 39 | POST `office-actions/{id}/extension` | office_action_response.update | office action | AFR-122 |
| 40 | POST `applications/{id}/maintenance-cycles` | maintenance.update | cycle (manual due date) | AFR-109 |
| 41 | POST `maintenance-cycles/{id}/request-decision` | maintenance.update | cycle | UC-017 |
| 42 | POST `maintenance-cycles/{id}/decision` | renewal.approve | cycle | UC-018, BR-061 |
| 43 | POST `maintenance-cycles/{id}/action` | maintenance.update | cycle (+ next) | AFR-113, 115 |
| 44 | POST `maintenance-cycles/{id}/reassign` | renewal.assign | cycle | C19 |
| 45 | GET `applications/{id}/documents` | document.view | documents with readable versions | UC-019 |
| 46 | POST `applications/{id}/documents` | document.create | version (multipart) | BR-014..016, 082, 087 |
| 47 | GET `documents/versions/{id}/download` | document.view | file stream | BR-084, 086, 130 |
| 48 | PATCH `documents/{id}` | document.update | document (sensitivity) | C16 |
| 49 | POST `prior-art/searches` | prior_art.create | ranked references, keyword and class suggestions, sources "not connected" | UC-004 |
| 50 | GET `applications/{id}/prior-art` | prior_art.view | references | AFR-146 |
| 51 | POST `applications/{id}/prior-art` | prior_art.create | reference | AFR-146 |
| 52 | GET `licensing-requests` | licensing_request.view | scoped requests | UC-020, 021 |
| 53 | POST `licensing-requests` | licensing_request.create | request | UC-020 |
| 54 | POST `licensing-requests/{id}/route` | licensing_request.review | request | BR-088 |
| 55 | POST `licensing-requests/{id}/notes` | licensing_request.review | note | AFR-161 |
| 56 | POST `licensing-requests/{id}/agreement` | licensing_request.review | agreement | AFR-162, 163 |
| 57 | GET `my-work` | application.view | the caller's pending items | AFR-057, 064 |
| 58 | GET `deadlines` | escalation.review | upcoming and missed deadlines | UC-016 |
| 59 | GET `escalations` | escalation.review | escalations | UC-016, 027 |
| 60 | POST `escalations/{id}/handle` | escalation.review | escalation | UC-027 |
| 61 | GET `oversight` | workflow.view | counts by status and pending actions, scoped | UC-032 |
| 62 | GET `reports/{type}` | report.view | report rows, scoped; access logged | UC-024, 030, 031 |
| 63 | GET `reports/{type}/export` | report.export | CSV | AFR-189 |
| 64 | GET, POST `report-definitions` | report_definition.create | definitions | AFR-188, 190 |
| 65 | POST `report-definitions/{id}/deactivate` | report_definition.create | definition | AFR-188 |
| 66 | GET `report-runs/{id}/download` | report.view | CSV, owner only, scope rebuilt at download | S-1 |
| 67 | GET `audit` | audit_log.view | scoped entries | UC-028 |
| 68 | GET `audit/export` | audit_log.export | CSV | UC-028 |
| 69 | GET `reference-data` | application.view | areas, sensitivity levels, IPC suggestions, alert offsets | C13, C16 |
| 70 | GET `policy` | policy.publish | current version and history | UC-025 |
| 71 | POST `policy` | policy.publish | new version (409 if `based_on_version` is stale) | UC-025 |
| 72 | GET `setup` | policy.publish | configuration still missing | Step 2.8 |

Throttle scopes, added to `DEFAULT_THROTTLE_RATES` (pre-approved): `pms_write` 240/hour,
`pms_submit` 30/hour, `pms_upload` 60/hour, `pms_search` 120/hour, `pms_export` 10/hour.

Query parameters are parsed by serializers. A malformed value answers 400. Unknown body keys
are refused.

### Client routes

Paths are relative to `/pms`. Each one has exactly one nav item above. Detail opens in a drawer
or a modal on its list page.

| Route | Page | Guard |
|---|---|---|
| `applications` | My Applications: list, new-application modal, detail drawer (history, inventors, documents, prior art, revise, withdraw, appeal, office-action approval) | `RequirePermission("pms.application.create")` |
| `reviews` | Reviews: assigned reviews, appeals, budget decisions, renewal decisions | `RequirePermission("pms.review.approve")` |
| `cases` | Assigned Cases: offers to accept or decline, assessments, budgets, filing, communications, office actions, maintenance, legal advice | `RequirePermission("pms.attorney_assignment.review")` |
| `assignments` | Assignments: Director and Attorney assignment queues | `RequirePermission("pms.review.assign")` |
| `monitoring` | Deadlines & Escalations | `RequirePermission("pms.escalation.review")` |
| `oversight` | Oversight (Director and PCC_ADMIN) | `RequirePermission("pms.workflow.view")` |
| `prior-art` | Prior Art Search (Applicant and Attorney) | `RequirePermission("pms.prior_art.create")` |
| `licensing` | Licensing: shared; controls gated with `can("pms.licensing_request.create")` and `can("pms.licensing_request.review")` | `RequirePermission("pms.licensing_request.view")` |
| `reports` | Reports: shared; export and schedule controls gated with `can()` | `RequirePermission("pms.report.view")` |
| `audit` | Audit Log; export gated with `can("pms.audit_log.export")` | `RequirePermission("pms.audit_log.view")` |
| `directors` | Directors roster | `RequirePermission("pms.director_profile.update")` |
| `attorney-panel` | Attorney Panel | `RequirePermission("pms.attorney_panel.update")` |
| `settings` | Settings and setup checklist | `RequirePermission("pms.policy.publish")` |

Every route is guarded by its nav item's own permission; a test like
`test_client_route_guards.py` pins them.

### `Fusion-client` sidebar entry (to paste into `INTEGRATED_MODULES`)

```js
{ id: "pms", label: "Patent Management", icon: "Lightbulb", to: "/pms", section: "Research" }
```

`icon` is a Phosphor name. `section` must match a section that `navigation.js` already renders.
If `Research` is not one, whoever adds the entry picks the nearest existing section. This repo
cannot check that (`module-only`).

---

## 3.6 (f) Contracts

`modules/pms/contracts.py` exposes one read-only, plural getter:

```python
def get_patent_summaries(user_ids: Sequence[int]) -> dict[int, PatentSummaryDTO]:
    """Filed and granted counts per person, as applicant or institute-user inventor."""
```

It returns counts only of filed and granted applications, which are already public records,
and never titles or content. No other module consumes it yet.

PMS needs from others only what already exists: `modules.directory.contracts.get_users`
(names and emails for display and notifications) and `modules.directory.contracts.search`
(picking an inventor, a Director or an attorney). Nothing is added to another module, to
`IamClient` or to `FakeIam`.

The one IAM capability PMS lacks — who holds a designation — is gap G-2, not a dependency to
build.

---

## 3.7 (g) Scheduled work

| Beat entry | Task | Cadence | Queue | If it does not run |
|---|---|---|---|---|
| `pms.deliver-notifications` | `pms.deliver_notifications` | 60 s, expires 55 s | notifications | No email leaves PMS; every notice the spec requires is silently queued |
| `pms.process-deadlines` | `pms.process_deadlines` | hourly at :05, expires 50 min | default | Overdue revisions never expire (BR-PMS-038); no 30/15/5-day alerts; missed review, office-action and maintenance deadlines never escalate — a patent can lapse unnoticed |
| `pms.auto-route` | `pms.auto_route_submissions` | every 10 min, expires 9 min | default | With automatic routing switched on, submissions sit in Submitted until PCC_ADMIN assigns them by hand |
| `pms.run-scheduled-reports` | `pms.run_scheduled_reports` | daily 06:00 IST | reports | Saved weekly or monthly reports are not produced |

Each task is idempotent:

- Alerts and escalations are unique by constraint.
- Expiry runs under `select_for_update` and re-checks the status.
- Delivery claims rows with `skip_locked`.
- Report runs are unique per (definition, period).

`pms_run_task --task <name>` runs any of them by hand.

**Management commands:** `pms_readiness`, `pms_run_task`. There is no policy-seeding command:
the built-in defaults (§3.2) apply until PCC_ADMIN publishes a version.

**Deployment order:** `migrate` → `seed_modules` → `seed_iam_permissions` (from the IAM) → grant
designations → `pms_readiness`.

`registry.readiness()` returns hard prerequisites only:

- the upload root exists, sits outside the repository and is not world-readable
- a scanner is configured and answers

Each is a sentence saying what to set. The configuration checklist (no areas, no Directors, no
panel, no threshold, no withdrawal statuses, no PCC_ADMIN contact) is printed by
`pms_readiness` as information and shown on the Settings page. It does not block `seed_modules`.

---

## 3.8 (h) Open questions, known gaps and approvals needed

### Accepted gaps (rulings A2, A3, C17; record dated approval)

- **G-1** PMS-AFR-027 (role-assignment half), UC-PMS-025: roles are assigned in the IAM with
  `assign_role`; PMS has no role table.
- **G-2** BR-PMS-131, PMS-AFR-221: PMS cannot see who holds `pms_pcc_admin`. Closing it needs an
  IAM endpoint such as `GET /api/iam/v1/designations/<name>/holders` (service-token
  authenticated, returning user ids). No IAM change in this assignment.
- **G-3** PMS-AFR-143, PMS-AFR-144: no outside patent or publication database is connected.
  Searches run over references recorded in PMS, and every outside source is shown as
  "not connected".

**Follows from G-2, for approval:** PCC_ADMIN adds Directors and panel attorneys to PMS's
rosters by picking people from the directory. PMS cannot check that the person holds
`pms_director` or `pms_attorney`. Someone without the designation can be listed but can never
act, because every action needs the permission. Readiness lists roster entries whose holders
have never signed in to PMS as a hint.

### Conditional rules implemented as their "not available" branch

BR-PMS-053 / PMS-AFR-097, BR-PMS-055 / PMS-AFR-100, BR-PMS-076, BR-PMS-077 / PMS-AFR-137, 138,
BR-PMS-139 / PMS-AFR-163. Each records that the source or rule is not available, and none
fabricates a result. PMS-AFR-214 and 215 are the platform's (TLS, storage encryption).

### Conflicts to rule on (raised as ruling A1 asked)

- **H-1 50 MB uploads vs the platform's limits.** The production nginx config
  (`ops/nginx/fusion-platform.conf:38`) caps every request at `client_max_body_size 2m`.
  `docs/06-crosscutting/security-baseline.md` items 4.5 and 4.12 cap documents at 5 MB and
  multipart bodies at 6 MB. BR-PMS-015 allows up to 50 MB.
  - Without a change, production refuses any PMS document over 2 MB at nginx, before the module
    sees it.
  - **Proposal:** one nginx `location` for `/api/v1/pms/applications/*/documents` with
    `client_max_body_size 51m`, and a recorded exception to baseline 4.5 and 4.12 for PMS
    documents.
  - Both are shared-file changes outside the module and need approval. If refused, 50 MB stays
    in PMS's own check (A1 says do not lower it) and the nginx cap is a documented production
    limitation.
- **H-2 Malware scanner in development and CI.** No ClamAV exists on this machine or in CI
  (`.github/workflows/e2e.yml` runs `config.settings.dev` with no scanner). Since A1 says
  submission is refused without a scanner, UC-PMS-001's Playwright journey cannot pass in CI.
  - **Proposal:** a `development` scanner backend that accepts everything except the EICAR test
    string.
  - It is selected by `PMS_MALWARE_SCANNER = "development"` in `config/settings/dev.py`, a
    shared-file change.
  - It refuses to run, and fails a system check, whenever `DEBUG` is false, so it cannot reach
    production.
  - Alternatives: install ClamAV locally (`brew install clamav`, a system tool, not a project
    dependency) and accept that the CI journey fails, or change CI, which this assignment may
    not do.
- **H-3 New settings** in `config/settings/base.py` (shared file, not pre-approved):
  - `PMS_UPLOAD_ROOT`, defaulting outside the repository like `PLACEMENT_UPLOAD_ROOT`
  - `PMS_CLAMD_SOCKET`, `PMS_CLAMD_HOST`, `PMS_CLAMD_PORT`, empty by default
  - `PMS_MALWARE_SCANNER`, `clamd` by default

  None needs a value in production for the deploy check to pass, so CI's deploy-check line does
  not change. Production must run `clamd` and set the socket. That is an operations item for
  the deployment notes.
- **No new Python or npm dependency** is proposed. PDF sniffing and the ClamAV protocol use the
  standard library.

### Questions the answers did not settle (each has a proposal; approving the blueprint approves the proposal)

- **Q-1** Which Director reviews an appeal (UC-PMS-023 says only "assigned/available")? *Proposal:
  PCC_ADMIN assigns an eligible Director other than the one who rejected it, using the same
  eligibility as BR-PMS-023..026.*
- **Q-2** After Budget Rejected or an outside rejection, may the Attorney propose a new budget?
  Without one, filing is impossible for good (BR-PMS-128). *Proposal: yes, as a new budget record;
  the rejected one stays.*
- **Q-3** Ruling C16 defines who reads Restricted, not how Confidential differs from
  Public-internal. *Proposal: Public-internal = anyone who can see the application, including a
  Director reading through area oversight; Confidential = only the people acting on it
  (applicant, institute-user inventors, current and past reviewing Directors, the assigned
  Attorney, PCC_ADMIN); Restricted = ruling C16's list.*
- **Q-4** BR-PMS-030's 50-character justification names "every Director review decision". Does
  it apply to appeal decisions? *Proposal: yes.*
- **Q-5** Who may see a licensing request's linked application status? *Proposal: no limit on
  which status may be licensed, beyond not being a draft; the spec states none.*
- **Q-6** If the only PCC_ADMIN is an inventor on an application (BR-PMS-027), nobody may assign
  it. *Proposal: the action is refused with that reason and an escalation of kind
  `conflicted_admin` is opened. Automatic routing, if enabled, still assigns a Director. Attorney
  assignment for that application waits for a different PCC_ADMIN. That second holder is
  possible because of G-2, but is something the institute arranges.*
- **Q-7** Notices addressed to "PCC_ADMIN" need a person: PMS cannot find the holder (G-2).
  *Proposal: Settings carries a PCC_ADMIN contact user id; until set, those notices are only
  in-app (escalation list) and the setup checklist says so.*
- **Q-8** BR-PMS-023 and 042 call expertise "a criterion". *Proposal: a Director or panel
  attorney is eligible only with a matching area; no match → the UC-PMS-007 exception flow (stays
  Submitted, escalation `no_eligible_director`). For attorneys a recorded institutional exception
  may waive the match, as it does the panel.*
- **Q-9** When the inventor set changes, are earlier agreements still valid? *Proposal: an
  inventor whose identity and share are unchanged keeps their agreement and consent; a new or
  changed inventor needs fresh ones.*
- **Q-10** Ruling C16 lets institute-user inventors read Restricted documents. *Proposal: such
  inventors see the application read-only; only the Applicant acts on it.*
- **Q-11** PMS-AFR-104 says "for each filing". *Proposal: several filings per application; the
  first moves it to Filed, later ones (for example an international filing after an Indian one)
  are recorded while Filed or Granted.*
- **Q-12** With no maintenance schedule rule for a jurisdiction, may the Attorney enter a due date
  by hand (PMS-AFR-109)? *Proposal: yes; that is data entered by a person, not a fabricated
  schedule.*
- **Q-13** Policy versions are published whole. Two PCC_ADMIN sessions publishing at once would
  lose one change. *Proposal: publishing names the version it was based on and is refused with
  409 if that is no longer current.*

### Changes made for security, not open to waiver (§0 rule)

- **S-1** Ruling C22 approved emailing scheduled reports as CSV. An emailed file leaves the
  platform's access control, and PMS cannot recheck offline whether the owner still holds their
  role (G-2). Scheduled runs are therefore stored and the email carries a link. The download
  rebuilds the scope from the owner's live session and permissions, so a revoked role sees
  nothing.
- **S-2** Ruling C17 ranks against "recorded references". Ranking over every application's
  references would reveal what other applicants are working on. The ranking covers only
  references on applications in the searcher's own scope.

### Shared-file changes requested (beyond Step 4.0's pre-approved lines)

| File | Change | Why |
|---|---|---|
| `config/settings/base.py` | `PMS_UPLOAD_ROOT`, `PMS_CLAMD_*`, `PMS_MALWARE_SCANNER` | H-3 |
| `config/settings/dev.py` | `PMS_MALWARE_SCANNER = "development"` | H-2 |
| `ops/nginx/fusion-platform.conf` | 51 MB location for PMS uploads | H-1 |

The pre-approved Step 4.0 lines (DOMAIN_MODULES, throttle rates, URL include, Celery merge,
`client/src/app/registry.ts`, `.importlinter`, `client/e2e/accounts.ts` entries for an applicant,
a Director, a PCC_ADMIN and an Attorney, `ops/docs/pms_reference.py`, regenerated files) are made
without further approval.

### Approvals (all given in writing by Student 2 on 21 Nov 2026)

1. The blueprint as a whole, including the proposals Q-1..Q-13.
2. Gaps G-1, G-2, G-3 (already ruled; the record needs a date).
3. H-1 (nginx and the baseline exception), H-2 (development scanner), H-3 (settings).
4. The Phase 1 answers themselves.
