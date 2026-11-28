# Gymkhana: where each spec id is enforced

Written by `ops/docs/gymkhana_reference.py`; do not edit by hand.

| Id | Requires | Enforced at |
|---|---|---|
| BR-GYM-001 | Leaders are valid students | [modules/gymkhana/services/people.py:38](../../modules/gymkhana/services/people.py#L38) |
| BR-GYM-002 | Councillor is valid faculty | [modules/gymkhana/services/people.py:42](../../modules/gymkhana/services/people.py#L42) |
| BR-GYM-003 | Category is Technical, Sports or Cultural | [modules/gymkhana/domain/rules.py:36](../../modules/gymkhana/domain/rules.py#L36) |
| BR-GYM-004 | Open on creation, confirmed by Student Admin | [modules/gymkhana/domain/state_machine.py:49](../../modules/gymkhana/domain/state_machine.py#L49) |
| BR-GYM-005 | Start before end | [modules/gymkhana/domain/rules.py:56](../../modules/gymkhana/domain/rules.py#L56) |
| BR-GYM-006 | No overlap in a venue on a date | [modules/gymkhana/services/bookings.py:63](../../modules/gymkhana/services/bookings.py#L63) |
| BR-GYM-007 | Apply only to a confirmed club | [modules/gymkhana/services/memberships.py:31](../../modules/gymkhana/services/memberships.py#L31) |
| BR-GYM-008 | Different clubs remain open | [modules/gymkhana/models/memberships.py:25](../../modules/gymkhana/models/memberships.py#L25) |
| BR-GYM-009 | No duplicate same-club application | [modules/gymkhana/models/memberships.py:26](../../modules/gymkhana/models/memberships.py#L26) |
| BR-GYM-010 | Only the club's current leaders act as Club Head | [modules/gymkhana/selectors/scoping.py:39](../../modules/gymkhana/selectors/scoping.py#L39) |
| BR-GYM-011 | Approval moves open to confirmed with remarks | [modules/gymkhana/services/memberships.py:95](../../modules/gymkhana/services/memberships.py#L95) |
| BR-GYM-012 | At least two choices | [modules/gymkhana/domain/rules.py:108](../../modules/gymkhana/domain/rules.py#L108) |
| BR-GYM-013 | Poll audience by batch and branch | [modules/gymkhana/domain/rules.py:181](../../modules/gymkhana/domain/rules.py#L181) |
| BR-GYM-014 | Only an active, unexpired poll | [modules/gymkhana/services/polls.py:67](../../modules/gymkhana/services/polls.py#L67) |
| BR-GYM-015 | One vote per student per poll | [modules/gymkhana/models/polls.py:69](../../modules/gymkhana/models/polls.py#L69) |
| BR-GYM-016 | Superseded leaders stop being current | [modules/gymkhana/services/leadership.py:47](../../modules/gymkhana/services/leadership.py#L47) |
| BR-GYM-017 | Budget amount zero or more | [modules/gymkhana/domain/rules.py:99](../../modules/gymkhana/domain/rules.py#L99) |
| BR-GYM-018 | Budget needs its supporting file | [modules/gymkhana/services/budget.py:35](../../modules/gymkhana/services/budget.py#L35) |
| BR-GYM-019 | Report needs its file | [modules/gymkhana/services/reports.py:32](../../modules/gymkhana/services/reports.py#L32) |
| BR-GYM-020 | Configured venue only | [modules/gymkhana/services/bookings.py:24](../../modules/gymkhana/services/bookings.py#L24) |
| BR-GYM-021 | Councillor reads only their club's reports | [modules/gymkhana/selectors/scoping.py:108](../../modules/gymkhana/selectors/scoping.py#L108) |
| UC-GYM-001 | Create New Club | [modules/gymkhana/services/clubs.py:23](../../modules/gymkhana/services/clubs.py#L23) |
| UC-GYM-002 | Book Club Session | [modules/gymkhana/services/bookings.py:121](../../modules/gymkhana/services/bookings.py#L121) |
| UC-GYM-003 | Book Club Event | [modules/gymkhana/services/bookings.py:128](../../modules/gymkhana/services/bookings.py#L128) |
| UC-GYM-004 | Apply for Club Membership | [modules/gymkhana/services/memberships.py:26](../../modules/gymkhana/services/memberships.py#L26) |
| UC-GYM-005 | Approve Club Membership | [modules/gymkhana/services/memberships.py:64](../../modules/gymkhana/services/memberships.py#L64) |
| UC-GYM-006 | Create Voting Poll | [modules/gymkhana/services/polls.py:27](../../modules/gymkhana/services/polls.py#L27) |
| UC-GYM-007 | Vote in Poll | [modules/gymkhana/services/polls.py:59](../../modules/gymkhana/services/polls.py#L59) |
| UC-GYM-008 | Change Club Leadership | [modules/gymkhana/services/leadership.py:21](../../modules/gymkhana/services/leadership.py#L21) |
| UC-GYM-009 | Request Club Budget | [modules/gymkhana/services/budget.py:22](../../modules/gymkhana/services/budget.py#L22) |
| UC-GYM-010 | Submit Club Event Report | [modules/gymkhana/services/reports.py:23](../../modules/gymkhana/services/reports.py#L23) |
| UC-GYM-011 | Approve Club | [modules/gymkhana/services/clubs.py:76](../../modules/gymkhana/services/clubs.py#L76) |
| UC-GYM-012 | Review Club Event Report | [modules/gymkhana/api/views.py:522](../../modules/gymkhana/api/views.py#L522) |
| BW-GYM-01 | Club Membership Enrollment | [modules/gymkhana/domain/state_machine.py:50](../../modules/gymkhana/domain/state_machine.py#L50) |
| BW-GYM-02 | Targeted Poll Participation | [modules/gymkhana/services/polls.py:59](../../modules/gymkhana/services/polls.py#L59) |
| BW-GYM-03 | Club Establishment and Confirmation | [modules/gymkhana/domain/state_machine.py:47](../../modules/gymkhana/domain/state_machine.py#L47) |
| CFR-GYM-001 | Club establishment | [modules/gymkhana/services/clubs.py:23](../../modules/gymkhana/services/clubs.py#L23) |
| CFR-GYM-002 | Leadership change | [modules/gymkhana/services/leadership.py:21](../../modules/gymkhana/services/leadership.py#L21) |
| CFR-GYM-003 | Session and event booking | [modules/gymkhana/services/bookings.py:75](../../modules/gymkhana/services/bookings.py#L75) |
| CFR-GYM-004 | Membership enrolment | [modules/gymkhana/services/memberships.py:26](../../modules/gymkhana/services/memberships.py#L26) |
| CFR-GYM-005 | Targeted polling | [modules/gymkhana/services/polls.py:27](../../modules/gymkhana/services/polls.py#L27) |
| CFR-GYM-006 | Budget request submission | [modules/gymkhana/services/budget.py:22](../../modules/gymkhana/services/budget.py#L22) |
| CFR-GYM-007 | Event reports and councillor review | [modules/gymkhana/selectors/scoping.py:108](../../modules/gymkhana/selectors/scoping.py#L108) |
| AFR-GYM-001 | Create club with its fields | [modules/gymkhana/services/clubs.py:57](../../modules/gymkhana/services/clubs.py#L57) |
| AFR-GYM-002 | Leaders valid students at creation | [modules/gymkhana/services/clubs.py:40](../../modules/gymkhana/services/clubs.py#L40) |
| AFR-GYM-003 | Councillor valid faculty | [modules/gymkhana/services/clubs.py:42](../../modules/gymkhana/services/clubs.py#L42) |
| AFR-GYM-004 | Category restricted | [modules/gymkhana/models/clubs.py:30](../../modules/gymkhana/models/clubs.py#L30) |
| AFR-GYM-005 | New club recorded open | [modules/gymkhana/services/clubs.py:59](../../modules/gymkhana/services/clubs.py#L59) |
| AFR-GYM-006 | Student Admin confirms | [modules/gymkhana/services/clubs.py:88](../../modules/gymkhana/services/clubs.py#L88) |
| AFR-GYM-007 | Club Head replaces leaders | [modules/gymkhana/services/leadership.py:21](../../modules/gymkhana/services/leadership.py#L21) |
| AFR-GYM-008 | New leaders valid students | [modules/gymkhana/services/leadership.py:33](../../modules/gymkhana/services/leadership.py#L33) |
| AFR-GYM-009 | Only current leaders remain | [modules/gymkhana/models/clubs.py:69](../../modules/gymkhana/models/clubs.py#L69) |
| AFR-GYM-010 | Book a session | [modules/gymkhana/services/bookings.py:121](../../modules/gymkhana/services/bookings.py#L121) |
| AFR-GYM-011 | Start precedes end | [modules/gymkhana/domain/rules.py:56](../../modules/gymkhana/domain/rules.py#L56) |
| AFR-GYM-012 | No overlapping booking | [modules/gymkhana/services/bookings.py:66](../../modules/gymkhana/services/bookings.py#L66) |
| AFR-GYM-013 | Notify on session booked | [modules/gymkhana/services/bookings.py:106](../../modules/gymkhana/services/bookings.py#L106) |
| AFR-GYM-014 | Book an event | [modules/gymkhana/services/bookings.py:128](../../modules/gymkhana/services/bookings.py#L128) |
| AFR-GYM-015 | Notify on event booked | [modules/gymkhana/services/bookings.py:109](../../modules/gymkhana/services/bookings.py#L109) |
| AFR-GYM-016 | Apply to a confirmed club | [modules/gymkhana/services/memberships.py:26](../../modules/gymkhana/services/memberships.py#L26) |
| AFR-GYM-017 | Applications to several clubs | [modules/gymkhana/models/memberships.py:25](../../modules/gymkhana/models/memberships.py#L25) |
| AFR-GYM-018 | No duplicate application | [modules/gymkhana/services/memberships.py:43](../../modules/gymkhana/services/memberships.py#L43) |
| AFR-GYM-019 | Application recorded open | [modules/gymkhana/services/memberships.py:47](../../modules/gymkhana/services/memberships.py#L47) |
| AFR-GYM-020 | Club Head sees pending applications | [modules/gymkhana/selectors/scoping.py:72](../../modules/gymkhana/selectors/scoping.py#L72) |
| AFR-GYM-021 | Approve with optional remarks | [modules/gymkhana/services/memberships.py:100](../../modules/gymkhana/services/memberships.py#L100) |
| AFR-GYM-022 | Approved becomes confirmed | [modules/gymkhana/services/memberships.py:99](../../modules/gymkhana/services/memberships.py#L99) |
| AFR-GYM-023 | Create a poll | [modules/gymkhana/services/polls.py:27](../../modules/gymkhana/services/polls.py#L27) |
| AFR-GYM-024 | At least two choices | [modules/gymkhana/domain/rules.py:15](../../modules/gymkhana/domain/rules.py#L15) |
| AFR-GYM-025 | Notify target students | [modules/gymkhana/services/notifications.py:100](../../modules/gymkhana/services/notifications.py#L100) |
| AFR-GYM-026 | Eligible student sees active polls | [modules/gymkhana/selectors/scoping.py:91](../../modules/gymkhana/selectors/scoping.py#L91) |
| AFR-GYM-027 | Eligible student casts one choice | [modules/gymkhana/services/polls.py:59](../../modules/gymkhana/services/polls.py#L59) |
| AFR-GYM-028 | No second vote; counted tally | [modules/gymkhana/selectors/polls.py:11](../../modules/gymkhana/selectors/polls.py#L11) |
| AFR-GYM-029 | Submit a budget request | [modules/gymkhana/services/budget.py:22](../../modules/gymkhana/services/budget.py#L22) |
| AFR-GYM-030 | Reject negative or missing file | [modules/gymkhana/services/budget.py:31](../../modules/gymkhana/services/budget.py#L31) |
| AFR-GYM-031 | Stored open, no approval | [modules/gymkhana/models/budget.py:30](../../modules/gymkhana/models/budget.py#L30) |
| AFR-GYM-032 | Submit an event report | [modules/gymkhana/services/reports.py:23](../../modules/gymkhana/services/reports.py#L23) |
| AFR-GYM-033 | Report file required | [modules/gymkhana/services/reports.py:32](../../modules/gymkhana/services/reports.py#L32) |
| AFR-GYM-034 | Assigned councillor reviews reports | [modules/gymkhana/selectors/scoping.py:57](../../modules/gymkhana/selectors/scoping.py#L57) |
