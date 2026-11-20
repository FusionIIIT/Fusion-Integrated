# Placement Cell: blueprint

Module code `placement`, docs folder `docs/04-placement/`, environment `module-only`.
Specification set: PC Problem Statement v1.2, Requirement Registry v1.3 FINAL, Use Cases v1.3 FINAL, Business Rules v1.3 FINAL, Workflows v1.3 FINAL and the v1.3 traceability matrix.
This blueprint rebuilds the existing Placement module in place against that set.
Every approval this document needs is recorded in the quality report.

## Phase 0 inventory

The spec has 26 live business rules: PC-BR-001 to PC-BR-007, PC-BR-009 to PC-BR-017, PC-BR-019 to PC-BR-026, PC-BR-029 and PC-BR-030.
Four rules are retired.
PC-BR-008 and PC-BR-018 moved to requirements PC-AFR-009 and PC-AFR-043.
PC-BR-027 is a modelling convention, and PC-BR-028 moved to the record-maintenance requirement.
The spec has 22 live use cases: PC-UC-001 to PC-UC-017 and PC-UC-020 to PC-UC-024.
PC-UC-018 and PC-UC-019 are retired, and role scope is now the cross-cutting rule PC-BR-022.
The spec has 8 basis workflows (BW-PC-01 to BW-PC-08) and 4 composite workflows (CW-PC-01 to CW-PC-04).
The legacy ids PC-WF-001 to PC-WF-008 are not live.
The spec has 19 consolidated requirements (PC-CFR-001 to PC-CFR-019) and 64 atomic requirements (PC-AFR-001 to PC-AFR-064).
The traceability matrix leaves its AFR mapping columns empty, so coverage was derived by reading each requirement.
No two spec documents contradict each other.
The spec keeps two issues open: ISS-PC-025 and ISS-PC-026 (section h).

## (a) Traceability

The generated [placement-reference.md](placement-reference.md) links each id below to the line that enforces it, and maps every PC-AFR and PC-CFR id to the rule or use case that enforces it.

| Id | What it requires | Layer | Enforcement point |
|---|---|---|---|
| PC-BR-001 | Profile completeness before applying | domain, services | `_guard`, `TRANSITIONS` |
| PC-BR-002 | Eligibility enforced before applying | domain, services | `evaluate`, `evaluate_for` |
| PC-BR-003 | Posting needs description, criteria and deadline | services | `_require_publishable` |
| PC-BR-004 | Criteria use the recorded vocabulary only | domain | `FIELDS`, `validate` |
| PC-BR-005 | TPO posting authority | registry, services | `create`, `_OFFICER` |
| PC-BR-006 | Company posting authority within scope | selectors, services | `create`, `postings_for` |
| PC-BR-007 | Company functions only once approved | models, services | `can_operate`, `approve` |
| PC-BR-009 | Company sees only its own applications | selectors | `applications_for` |
| PC-BR-010 | TPO manages applications | domain, services | `_review`, `transition` |
| PC-BR-011 | Interview needs date, slot and mode | services | `schedule_round` |
| PC-BR-012 | Interview notification | services | `add_candidates` |
| PC-BR-013 | Offer response within the deadline | services | `respond`, `expire_overdue` |
| PC-BR-014 | Acceptance updates the placement record | services | `_record_acceptance` |
| PC-BR-015 | Multiple offers only by represented policy | domain | `can_accept` |
| PC-BR-016 | Students see anonymised statistics | services | `student_view` |
| PC-BR-017 | Announcement topics bounded | models, services | `Announcement`, `publish` |
| PC-BR-019 | Alumni read-only access | registry | `_ALUMNI` |
| PC-BR-020 | Alumni kept out of active workflows | registry, selectors | `applications_for`, `_ALUMNI` |
| PC-BR-021 | Notifications handed off as email | services | `deliver_pending` |
| PC-BR-022 | Access by role and scope | selectors, services | `is_staff`, `require` |
| PC-BR-023 | Sensitive data view restricted | selectors | `may_read_candidate` |
| PC-BR-024 | Sensitive data modify restricted | services | `require` |
| PC-BR-025 | Academic data stays external | services | `academic_facts` |
| PC-BR-026 | Platform auth and RBAC stay external | authentication, registry | `RecruiterAuthentication`, `ROLE_GRANTS` |
| PC-BR-029 | TPO updates student and alumni records | services | `correct` |
| PC-BR-030 | No external recruitment decision made here | domain | `TRANSITIONS` |
| PC-UC-001 | Student placement profile | api, services | `MyResumeView`, `attach_link` |
| PC-UC-002 | Browse opportunities | selectors | `postings_for` |
| PC-UC-003 | Apply for an eligible posting | services | `apply_to` |
| PC-UC-004 | Track status | api, selectors | `ApplicationHistoryView`, `applications_for` |
| PC-UC-005 | Respond to an offer | services | `respond` |
| PC-UC-006 | TPO manages postings | services | `publish` |
| PC-UC-007 | Automated notifications | services | `enqueue` |
| PC-UC-008 | TPO reviews and filters applications | selectors, services | `applications_for`, `transition` |
| PC-UC-009 | TPO schedules interviews | services | `add_candidates` |
| PC-UC-010 | TPO maintains placement records | services | `correct` |
| PC-UC-011 | TPO reports | services | `staff_view`, `trends` |
| PC-UC-012 | Chairman oversight | registry, services | `staff_view`, `_CHAIRMAN` |
| PC-UC-013 | Chairman announcements | services | `publish` |
| PC-UC-014 | Company registers | api, services | `CompanySelfRegisterView`, `register` |
| PC-UC-015 | Company publishes or submits | services | `submit` |
| PC-UC-016 | Company shortlists or rejects | services | `transition` |
| PC-UC-017 | Alumni restricted access | registry | `_ALUMNI` |
| PC-UC-020 | TPO announcements | services | `publish` |
| PC-UC-021 | Company schedules an interview | services | `schedule_round` |
| PC-UC-022 | Company extends an offer | services | `issue` |
| PC-UC-023 | Resume from the profile | services | `candidate_record` |
| PC-UC-024 | Student statistics | services | `student_view` |
| BW-PC-01 | TPO publishes, student applies | services | `publish`, `apply_to` |
| BW-PC-02 | Company publishes, student applies | services | `publish` |
| BW-PC-03 | Company submits, TPO publishes | services | `submit` |
| BW-PC-04 | Applied to shortlisted | domain | `TRANSITIONS` |
| BW-PC-05 | Shortlisted to TPO interview | services | `add_candidates` |
| BW-PC-06 | Shortlisted to company interview | services | `add_candidates` |
| BW-PC-07 | Offer accepted, record updated | services | `_record_acceptance` |
| BW-PC-08 | Offer rejected | services | `respond` |
| CW-PC-01 | Publication paths to application | services | `publish` |
| CW-PC-02 | Selection and scheduling | domain | `TRANSITIONS` |
| CW-PC-03 | Offer outcome | services | `respond` |
| CW-PC-04 | End-to-end lifecycle | domain | `TRANSITIONS` |

## (b) Domain model

Every person reference is a plain integer `user_id`.
No foreign key crosses a module boundary.

- `PlacementPolicy` is one season, unique on `season`. It holds the response-deadline default and the discipline groups. `PolicyCategory` holds that season's signed offer bands, with a check that `ctc_max >= ctc_min`.
- `Company` carries `approval_status`. A check constraint requires an approver on every approved company. A unique index on the lowercased name allows one record per company (decision 10). `can_operate` is true only for an approved company that is not blacklisted (PC-BR-007).
- `RecruiterAccount`, `RecruiterSession` and `RecruiterLoginAttempt` are the company's own sign-in lane. Session tokens are stored only as hashes.
- `JobPosting` has a check that a published posting has a locked eligibility rule (PC-BR-002). Publishing requires a description, criteria and a deadline (PC-BR-003).
- `Application` is unique per posting and student. Its eligibility snapshot is frozen at apply time. `ApplicationTransition` is its append-only history (PC-AFR-009).
- `InterviewRound` and `RoundParticipation`: a round records date, time and mode (PC-BR-011). A new round must start in the future and end after it starts.
- `Offer` is one-to-one with an application and always has `respond_by` (PC-BR-013).
- `PlacementRecord` has a partial unique index allowing one active record per student per season. A check ties `source` to its origin. `PlacementRecordRevision` is the append-only history of TPO corrections (PC-BR-029).
- `Announcement` has a closed topic list (PC-BR-017). Withdrawal flags the row and never deletes it (PC-AFR-043).
- `NotificationOutbox` is unique on `dedupe_key`, so retries cannot send twice (PC-BR-021).
- `PlacementStatsSnapshot` is materialised per season, so statistics never read the transactional tables.
- `PlacementRegistration`, `ConductIncident` and `ProfileDocument` support the institute's season registration (the configured completeness condition of PC-BR-001), conduct records and placement documents (PC-AFR-003).

## (c) State machine

The declarative table is `TRANSITIONS` in `domain/state_machine.py`.
[application-state-machine.md](application-state-machine.md) and `docs/_diagrams/application-state-machine.mmd` are generated from it.
The spec's states map to the code as follows: Applied is `submitted`, Shortlisted is `shortlisted`, Interview Scheduled is `interview_scheduled`, Offer Extended is `offer_issued`, Offer Accepted is `offer_accepted`, and Offer Rejected is `offer_declined`.
Two spec transitions were missing and are now in the table: `submitted` to `shortlisted` (BW-PC-04), and `interview_scheduled` to `offer_issued` (BW-PC-07).
Opportunity states are `draft`, `pending_approval` (Submitted, BW-PC-03) and `published`.
A recruiter cannot publish a `pending_approval` posting; only the TPO can.

## (d) Permissions

`MODULE["code"]` is `placement`, as are the folder, the URL segment and the permission prefix.
Every verb is from the closed list in `docs/02-iam/rbac-model.md`.
`ROLE_GRANTS` is keyed by the designation exactly as `globals_designation` spells it.
The roles are derived from the actor inventory: Student (PS 2.1), TPO as `placement officer` (PS 2.2), Placement Chairman as `placement chairman` (PS 2.3), and Alumni as `alumini`, the fixture's spelling (PS 2.5).
Company/Recruiter (PS 2.4) has no institute identity, so it signs in through the module's recruiter lane and is authorised by company scope.
The grants to `placement_coordinator` and `Dean Academic` were removed, because no spec document names those roles.

| Permission | Meaning | Held by |
|---|---|---|
| `placement.job_posting.view` | See job postings | student, placement officer, placement chairman |
| `placement.job_posting.manage` | Create and publish postings | placement officer |
| `placement.application.view` | See all applications | placement officer, placement chairman |
| `placement.own_application.view` | See one's own applications | student |
| `placement.application.create` | Apply to a posting | student |
| `placement.application.review` | Shortlist and reject applications | placement officer |
| `placement.application.delete` | Withdraw an application | student |
| `placement.application.revoke` | System auto-withdrawal | system only |
| `placement.interview.create` | Schedule interview rounds | placement officer |
| `placement.offer.create` | Extend an offer | placement officer |
| `placement.offer_response.create` | Accept or decline an offer | student |
| `placement.offer.revoke` | Revoke an issued offer | placement officer |
| `placement.offer_expiry.create` | System offer expiry | system only |
| `placement.company.manage` | Register and approve companies | placement officer |
| `placement.announcement.publish` | Publish announcements | placement officer, placement chairman |
| `placement.report.view` | See operational reports | placement officer, placement chairman |
| `placement.statistic.view` | See anonymised placement statistics | student, placement officer, placement chairman, alumini |
| `placement.sanction.manage` | Record conduct incidents and impose placement sanctions | placement officer |
| `placement.registration.manage` | Approve late registrations and re-registrations | placement officer |
| `placement.registration.create` | Register yourself for a placement season | student |
| `placement.record.manage` | Record off-campus placements and chase offer letters | placement officer |
| `placement.academic_directory.view` | Browse every student's declared CPI | placement officer, placement chairman |

## (e) Endpoints

Every endpoint sits behind `HasModuleGrant("placement")` and then a second gate.
Row visibility always comes from `selectors/scoping.py`, and an out-of-scope id answers 404.

| Path under `/api/v1/placement/` | Methods | Second gate (after `HasModuleGrant("placement")`) |
|---|---|---|
| `postings` | GET, POST | codes, or a recruiter's company scope: `placement.job_posting.view`, `placement.job_posting.manage` |
| `postings/<int:pk>` | GET, PATCH | codes, or a recruiter's company scope: `placement.job_posting.view`, `placement.job_posting.manage` |
| `postings/<int:pk>/publish` | POST | codes, or a recruiter's company scope: `placement.job_posting.manage` |
| `postings/<int:pk>/submit` | POST | codes, or a recruiter's company scope: `placement.job_posting.manage` |
| `postings/<int:pk>/eligibility` | GET | codes: `placement.job_posting.view`, `placement.own_application.view` |
| `applications` | GET | codes, or a recruiter's company scope: `placement.application.view`, `placement.own_application.view` |
| `applications/apply` | POST | codes: `placement.application.create` |
| `applications/<int:pk>/transition` | POST | codes, or a recruiter's company scope: `placement.application.review`, `placement.own_application.view` |
| `applications/<int:pk>/history` | GET | codes, or a recruiter's company scope: `placement.application.view`, `placement.own_application.view` |
| `applications/bulk-transition` | POST | codes, or a recruiter's company scope: `placement.application.review` |
| `documents` | GET, POST | codes: `placement.own_application.view` |
| `documents/<int:pk>` | DELETE | codes: `placement.own_application.view` |
| `documents/<int:pk>/download` | GET | codes, or a recruiter's company scope: `placement.own_application.view`, `placement.application.view` |
| `profile/resume` | GET | codes: `placement.own_application.view` |
| `profiles/<int:user_id>` | GET | codes, or a recruiter's company scope: `placement.application.view` |
| `companies` | GET, POST | codes, or a recruiter's company scope: `placement.company.manage`, `placement.job_posting.view` |
| `companies/register` | POST | none: public endpoint, throttled |
| `companies/<int:pk>/<str:action>` | POST | codes: `placement.company.manage` |
| `interviews/rounds` | GET, POST | codes, or a recruiter's company scope: `placement.interview.create`, `placement.application.review`, `placement.own_application.view` |
| `interviews/rounds/<int:pk>/candidates` | POST | codes, or a recruiter's company scope: `placement.interview.create` |
| `interviews/rounds/<int:pk>/outcome` | POST | codes, or a recruiter's company scope: `placement.interview.create`, `placement.application.review` |
| `offers` | GET | codes, or a recruiter's company scope: `placement.offer.create`, `placement.offer_response.create`, `placement.application.view` |
| `offers/issue` | POST | codes, or a recruiter's company scope: `placement.offer.create` |
| `offers/<int:pk>/respond` | POST | codes: `placement.offer_response.create` |
| `announcements` | GET, POST | codes, or a recruiter's company scope: `placement.announcement.publish`, `placement.job_posting.view`, `placement.statistic.view` |
| `announcements/<int:pk>/withdraw` | POST | codes: `placement.announcement.publish` |
| `students/cpi` | GET | codes: `placement.academic_directory.view` |
| `students/cpi/filters` | GET | codes: `placement.academic_directory.view` |
| `registrations` | GET, POST | codes: `placement.registration.create` |
| `registrations/terms` | GET | codes: `placement.registration.create` |
| `registrations/opt-out` | POST | codes: `placement.registration.create` |
| `registrations/approve-late` | POST | codes: `placement.registration.manage` |
| `registrations/re-register` | POST | codes: `placement.registration.manage` |
| `records` | GET | codes: `placement.own_application.view` |
| `records/clearance` | GET | codes: `placement.own_application.view` |
| `records/<int:pk>/offer-letter` | POST | codes: `placement.own_application.view` |
| `records/<int:pk>/not-joining` | POST | codes: `placement.own_application.view` |
| `records/outstanding` | GET | codes: `placement.report.view`, `placement.record.manage` |
| `records/off-campus` | POST | codes: `placement.record.manage` |
| `records/office` | GET | codes: `placement.report.view`, `placement.record.manage` |
| `records/<int:pk>` | PATCH | codes: `placement.record.manage` |
| `records/<int:pk>/revisions` | GET | codes: `placement.report.view`, `placement.record.manage` |
| `conduct/incidents` | GET, POST | codes: `placement.sanction.manage` |
| `conduct/incidents/<int:pk>/waive` | POST | codes: `placement.sanction.manage` |
| `conduct/sanctions` | POST | codes: `placement.sanction.manage` |
| `conduct/sanctions/lift` | POST | codes: `placement.sanction.manage` |
| `conduct/mine` | GET | codes: `placement.own_application.view` |
| `exports/applications.csv` | GET | codes: `placement.report.view` |
| `exports/placements.csv` | GET | codes: `placement.report.view` |
| `seasons` | GET | codes, or a recruiter's company scope: `placement.job_posting.view`, `placement.report.view`, `placement.statistic.view`, `placement.registration.create`, `placement.registration.manage` |
| `stats` | GET | codes: `placement.statistic.view`, `placement.report.view` |
| `stats/trends` | GET | codes: `placement.report.view` |
| `recruiters/invite` | POST | codes: `placement.company.manage` |
| `recruiters/accept` | POST | none: public endpoint, throttled |
| `recruiters/login` | POST | none: public endpoint, throttled |
| `recruiters/logout` | POST | recruiter session only |
| `recruiters/me` | GET | recruiter session only |

Client routes and their guards:
`profile`, `postings`, `mine`, `offers`, `announcements`, `reports` and `registration` are open to every role the module is granted to, and the server scopes their data.
`companies` needs `placement.company.manage`, `interviews` needs `placement.interview.create`, `records` needs `placement.record.manage`, `registration-approvals` needs `placement.registration.manage`, and `students-cpi` needs `placement.academic_directory.view`.
Every route has a nav item, and every nav item has a route (`ops/checks/nav_matches_routes.py`).

`Fusion-client` sidebar entry for `INTEGRATED_MODULES`: `{ id: "placement", label: "Placement Cell", icon: "Briefcase", to: "/placement", section: "Placement" }`.

## (f) Contracts

`contracts.py` exposes two plural getters.
`get_placement_status(user_ids, placement_year)` returns whether each person is placed.
`get_no_dues_clearances(user_ids)` returns whether placement blocks a no-dues certificate.
The module uses `modules.directory.contracts.get_users` for names, discipline, batch and the portal's profile flag.
It uses the IAM's `get_academic_standings` for the declared CPI (PC-BR-025).
It adds no IAM endpoint and no `fusionlab` connection.

## (g) Scheduled work

- `placement.deliver-notifications` runs every 60 seconds. Without it, no notification email leaves the outbox (PC-BR-021).
- `placement.expire-overdue-offers` runs every 300 seconds. Without it, an unanswered offer never expires and keeps the student out of the pool (PC-BR-013).
- `placement.rebuild-active-stats` runs every 15 minutes. Without it, the statistics pages show old figures.

`manage.py scheduled_work_status` reports whether each one is keeping up.

## (h) Open questions and decisions

Student 1 decided each item below while building, on the instruction to decide them without waiting.
Student 2 must confirm or overturn each one in writing, and the quality report records the answer.

1. ISS-PC-025: the spec does not name the recipient of the Application Submitted, Shortlisting Update and Rejection Update emails. The module sends them to the applicant only.
2. ISS-PC-026: the spec does not name who records a company's approval. The module lets `placement.company.manage` (the TPO) record the institute's decision. A company can register itself (PC-UC-014), and it gains no function until it is approved.
3. TPO decisions: PC-UC-008 says TPO review is not a recruitment decision. The TPO can still record a shortlist or rejection that a company communicated, under PC-BR-030 ("record and expose authorized shortlist ... information supplied through supported PCMS actions").
4. Policy values: the offer deadline defaults to 72 hours per season. Profile completeness is the ERP portal's `profile_completed` flag. Multiple-offer handling is the signed Placement Policy 2026-27 categories (PC-BR-015). `open_placement_season` seeds them.
5. Behaviour beyond the spec is kept, because production uses it: season registration (rules 1, 20, 21), conduct and sanctions (rules 18, 19, 21), offer-letter clearance (rules 22, 24), the CPI directory and CSV exports. None of it widens a role's access beyond its grants.
6. Skills: PC-BR-004 allows skills as a criterion, but the IAM does not project skills, so no rule can check them. The criterion is absent and the posting forms no longer offer it.
7. Alumni identity: the fixture's only alumni designation is `alumini`. Its holders are student-kind accounts, so the platform also gives them the student grants (see 8).
8. Platform gap, outside the module: the IAM session carries the union of every held role's permissions and navigation, while `docs/02-iam/rbac-model.md` says only the acting role counts. A student who also holds `alumini` therefore keeps student access. The fix belongs in `Fusion_System_Administrator` and the platform shell.
9. IAM defect, outside the module: two simultaneous logins of one account can fail with a unique-constraint error in `iam/sync.py::refresh_designations`, which surfaces as a 503 from `/api/v1/auth/login`.
10. Company names are unique, ignoring case. Upstream allowed two companies with one name and gave the second a `-2` slug. A second record would split the company's approvals, postings and history, and a blacklisted company could register again under its own name for a fresh pending record. A duplicate now answers 409 `company_exists`.
11. Three upstream behaviours changed for security. A recruiter's offer data no longer carries `policy_decision`, because it records the student's other offers (PC-BR-009). Only the placement office sets or clears a Dream Slot (policy rule 7); a recruiter's attempt answers 403. Recruiter sign-in failures are counted per email and address, so a stranger who knows the email cannot keep the account locked, and attempts on one account run one at a time, so a burst cannot outrun the count.
