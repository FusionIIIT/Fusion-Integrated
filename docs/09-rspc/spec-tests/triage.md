# Spec tests: rspc

Student 1 (git author name): Akshat01g
Student 2 (git author name): Ruthvik Gundelli
Design commit (hash and subject): 6f4a7e2 Add spec-based test designs for FR, UC, BR and WF
Baseline commit (hash and subject): TO FILL AFTER THE BASELINE COMMIT
Student 1's 10/10 commit the baseline ran on (hash): 6780668 (confirm with Student 1)

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline (Q1) | FR | 151 | 34 | 1 | 116 | 79.3 | 41.0 |
| baseline (Q1) | UC | 118 | 27 | 1 | 90 | 77.0 | 33.3 |
| baseline (Q1) | BR | 78 | 31 | 3 | 44 | 77.4 | 34.6 |
| baseline (Q1) | WF | 34 | 0 | 1 | 33 | 30.3 | 5.1 |

Coverage is of modules/rspc, as measured by each strategy's own run.
Categories below are Student 2's proposal; both students confirm them.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with spec sentence) |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------|
| TC-UC-008, TC-BR-010 | RSPC-UC-002 E1; BR-RSPC-013 | UC, BR | Confirmed implementation defect (proposed) | Submitting a proposal with a mandatory field missing returns 200, not a validation error (assert 200 in (400, 422); assert 200 == 422). `submit_proposal` has no completeness check. | open |
| TC-FR-040, TC-BR-012 | RSPC-FR-022; BR-RSPC-014 | FR, BR | Confirmed implementation defect (proposed) | Validation errors return 400 (assert 400 == 422). docs/01-architecture/api-conventions.md, "Status codes", says 422 for validation; the spec names no code, so the expected code comes from the convention. | open |
| TC-BR-028 | BR-RSPC-035 | BR | Confirmed implementation defect (proposed) | A request exceeding the sanctioned budget returns 409 (assert 409 == 422). api-conventions.md lists 422 for a business-rule refusal. | open |
| TC-WF-013 | CW-RSPC-01 row 3 (Not recommended) | WF | Confirmed implementation defect (proposed) | After HoD rejection the status is 'rejected' (assert 'rejected' == 'Department Not Recommended'). The model has no distinct Not-Recommended state. | open |
| TC-WF-001 to 012, 014 to 034 | BW-RSPC-01 to 12; CW-RSPC-01 to 06 | WF | Confirmed implementation defect (proposed): workflow stages not implemented | 33 skipped NOT_AUTOMATED. Only the proposal, project and extension states exist; no Admin verification, Director stage, Forward to Director, Archived, appointment, financial-request or procurement workflow. | open |
| TC-FR-006, 008, 009, 010, 080 | RSPC-FR audit trail and logs | FR | Confirmed implementation defect (proposed): no audit trail or log interface | NOT_AUTOMATED skips | open |
| TC-FR-002, 005, 057 | project and approval history | FR | Confirmed implementation defect (proposed): no history interface | NOT_AUTOMATED skips | open |
| TC-FR-104 to 117 | notifications | FR | Confirmed implementation defect (proposed): no notification interface | NOT_AUTOMATED skips | open |
| TC-FR-118 to 122 | cross-module integration, external data | FR | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |
| TC-FR-019, 059 to 071, 131 | staff appointments | FR | Confirmed implementation defect (proposed): no appointment workflow | NOT_AUTOMATED skips | open |
| TC-FR-021, 025, 026, 074 to 079, 132 | financial-request workflow | FR | Confirmed implementation defect (proposed): disburse-approve endpoint is a stub; no verification, escalation or Dean limits | NOT_AUTOMATED skips | open |
| TC-FR-022, 086, 087, 088, 133 | procurement workflow | FR | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |
| TC-FR-089 to 095 | progress and utilization reports | FR | Confirmed implementation defect (proposed): reports endpoint returns counts only | NOT_AUTOMATED skips | open |
| TC-FR-018, 027 to 031, 038, 043, 142 to 151 | Director and RSPC Admin stages | FR | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |
| TC-FR-033, 034, 037, 046 to 050, 053 to 055 | proposal and consultancy fields | FR | Confirmed implementation defect (proposed): fields for objectives, dates, resources, client, scope, deliverables, timeline, financial terms and consultancy payments do not exist | NOT_AUTOMATED skips | open |
| TC-FR-013, 014, 024, 041, 097 to 103, 126, 127, 129, 130 | evaluations, policy validation, closure verification and archive, IAM role log | FR | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |
| TC-FR-134 to 141 | project updates | FR | Confirmed implementation defect (proposed): no update endpoint | NOT_AUTOMATED skips | open |
| UC skips (90 cases, see skip reasons in modules/rspc/tests/spec/uc/) | Admin verification, Director decision, Dean-to-Director forwarding, appointments, procurement, periodic reports, notifications, role-change intake, project update, closure verification and rejection, consultancy payments; policy validation and routing thresholds (006, 007, 009, 013, 023, 033); 047, 049, 088, 091 (disburse writes the ledger directly; fund-approve is a stub); 068 (reports return counts only) | UC | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |
| BR skips (44 cases: 001, 003-008, 017, 019-026, 030-039, 043, 044, 050, 057-062, 066-069, 073, 075-078) | review stages and authority limits; appointments; financial approval; procurement hierarchy; reports and reminders; integrations; external execution; agency status; project updates; configurable policy | BR | Confirmed implementation defect (proposed) | NOT_AUTOMATED skips | open |

## Notes
- Related finding, not from the spec tests: `make check` fails on the 10/10 commit with ruff F403 at modules/rspc/tests/test_settings.py line 1 (`from config.settings.test import *`). To send to Student 1.
- Mapping choices the test writers made (closest fit to what exists): a consultancy request is a Proposal with proposal_type consultancy; BR-027 to 029 test a disburse request against a head's remaining balance as the procurement-against-budget case.
- A rebase gives every commit a new hash. After one, update every hash in this file.
