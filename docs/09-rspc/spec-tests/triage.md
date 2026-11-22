# Spec tests: rspc

Student 1 (git author name): Akshat01g
Student 2 (git author name): Ruthvik Gundelli
Design commit (hash and subject): 6f4a7e2 Add spec-based test designs for FR, UC, BR and WF
Baseline commit (hash and subject): 13a0484 Add spec tests and triage for baseline run
Student 1's 10/10 commit the baseline ran on (hash): 6780668 (confirm with Student 1)

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline (Q1) | FR | 151 | 34 | 1 | 116 | 79.3 | 41.0 |
| baseline (Q1) | UC | 118 | 27 | 1 | 90 | 77.0 | 33.3 |
| baseline (Q1) | BR | 78 | 31 | 3 | 44 | 77.4 | 34.6 |
| baseline (Q1) | WF | 34 | 0 | 1 | 33 | 30.3 | 5.1 |
| Q2 (Final) | FR | 35 | 35 | 0 | 0 | 73.6 | 39.2 |
| Q2 (Final) | UC | 28 | 28 | 0 | 0 | 72.8 | 41.2 |
| Q2 (Final) | BR | 34 | 34 | 0 | 0 | 72.0 | 35.1 |
| Q2 (Final) | WF | 1 | 1 | 0 | 0 | 28.0 | 11.5 |

Coverage is of modules/rspc, as measured by each strategy's own run.
Categories below are confirmed by both students per Step 9.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------|-------|
| TC-UC-008, TC-BR-010 | RSPC-UC-002 E1; BR-RSPC-013 | UC, BR | Confirmed implementation defect | Submitting a proposal with a mandatory field missing returns 200, not a validation error (assert 200 in (400, 422); assert 200 == 422). `submit_proposal` has no completeness check. | Fixed in 85f9647; TC-UC-008 and TC-BR-010 pass at 5885192. | no |
| TC-FR-040, TC-BR-012 | RSPC-FR-022; BR-RSPC-014 | FR, BR | Confirmed implementation defect | Validation errors return 400 (assert 400 == 422). docs/01-architecture/api-conventions.md, "Status codes", says 422 for validation; the spec names no code, so the expected code comes from the convention. | Fixed in 85f9647; TC-FR-040 and TC-BR-012 pass at 5885192. | no |
| TC-BR-028 | BR-RSPC-035 | BR | Confirmed implementation defect | A request exceeding the sanctioned budget returns 409 (assert 409 == 422). api-conventions.md lists 422 for a business-rule refusal. | Fixed in 85f9647; TC-BR-028 passes at 5885192. | no |
| TC-WF-013 | CW-RSPC-01 row 3 (Not recommended) | WF | Confirmed implementation defect | After HoD rejection the status is 'rejected' (assert 'rejected' == 'Department Not Recommended'). The model has no distinct Not-Recommended state. | Fixed in 85f9647; TC-WF-013 passes at 5885192. | no |
| TC-WF-001 to 012, 014 to 034 | BW-RSPC-01 to 12; CW-RSPC-01 to 06 | WF | Specification scope agreement | 33 skipped NOT_AUTOMATED. Only proposal, project, extension and closure states exist in core baseline. Problem Statement Section 1: "RSPC uses Fusion platform services such as dashboard access, RBAC, notification delivery, and integration mechanisms." Both students agreed administrative verification, Director escalation, and secondary workflows are deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in WF_DESIGN.json. | no |
| TC-FR-006, 008, 009, 010, 080 | RSPC-FR audit trail and logs | FR | Specification scope agreement | Problem Statement Section 1: "Platform-wide authentication, user account provisioning, role assignment, and core notifications are external to RSPC." Both students agreed audit stream query APIs deferred beyond append-only ledger and proposal review logs per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-002, 005, 057 | project and approval history | FR | Specification scope agreement | RSPC-CFR-001: Faculty access to own proposal/project records supported; distinct project approval-history views deferred beyond proposal review timeline per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-104 to 117 | notifications | FR | Specification scope agreement | Problem Statement Section 1: "Platform-wide authentication, user account provisioning, role assignment, and core notifications are external to RSPC." Both students agreed automated notification outbox deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-118 to 122 | cross-module integration, external data | FR | Specification scope agreement | RSPC-CFR-022: "Scope Boundary: RSPC shall exchange, reference, or record RSPC-relevant information through integration mechanisms... external agency sync external to RSPC core." Both students agreed external API sync deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-019, 059 to 071, 131 | staff appointments | FR | Specification scope agreement | RSPC-CFR-025: "Project Staff HR/Payroll Scope Boundary: RSPC shall not perform HR master-data management or payroll/payment execution for project-based staff appointments." Both students agreed recruitment workflow deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-021, 025, 026, 074 to 079, 132 | financial-request workflow | FR | Specification scope agreement | RSPC-CFR-026: "Project Finance Payment-Execution Scope Boundary: RSPC shall not perform payment execution..." Both students agreed multi-tier escalation deferred beyond append-only fund ledger and disburse/approve per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-022, 086, 087, 088, 133 | procurement workflow | FR | Specification scope agreement | RSPC-CFR-027: "Procurement and Inventory Execution Scope Boundary: RSPC shall not perform store inventory issuance or procurement execution." Both students agreed procurement requisition workflows deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-089 to 095 | progress and utilization reports | FR | Specification scope agreement | RSPC-CFR-014: Periodic SE/UC generation beyond project aggregate counts and ledger exports deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-018, 027 to 031, 038, 043, 142 to 151 | Director and RSPC Admin stages | FR | Specification scope agreement | Problem Statement Section 1: Core research grant approval workflow is complete with HoD endorsement and Dean approval; multi-tier RSPC Admin verification and Director escalation stages deferred per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-033, 034, 037, 046 to 050, 053 to 055 | proposal and consultancy fields | FR | Specification scope agreement | Problem Statement Section 1 & RSPC-CFR-009: Consultancy project workflow and client billing deferred beyond core research grant baseline per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-013, 014, 024, 041, 097 to 103, 126, 127, 129, 130 | evaluations, policy validation, closure verification and archive, IAM role log | FR | Specification scope agreement | RSPC-CFR-020 & CFR-024: Mid-term evaluation committees, closure verification archives, and IAM role log synchronization deferred per scope boundary (CFR-024) and Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| TC-FR-134 to 141 | project updates | FR | Specification scope agreement | RSPC-CFR-028: "Lifecycle-Permitted Faculty Project Updates": Post-sanction project amendment APIs deferred beyond project extension and closure lifecycle per Blueprint Step 3.8(h). Skipped stubs deleted per Step 9 rule 3; designs preserved in FR_DESIGN.json. | no |
| UC skips (90 cases, see skip reasons in modules/rspc/tests/spec/uc/) | Admin verification, Director decision, Dean-to-Director forwarding, appointments, procurement, periodic reports, notifications, role-change intake, project update, closure verification and rejection, consultancy payments; policy validation and routing thresholds | UC | Specification scope agreement | Problem Statement Section 1 & Blueprint Step 3.8(h): Use cases for Admin verification, Director decision, appointments, procurement indents, reports, notifications, role sync, and consultancy billing deferred beyond core research grant lifecycle baseline. Both students agreed. Skipped stubs deleted per Step 9 rule 3; designs preserved in UC_DESIGN.json. | no |
| BR skips (44 cases: 001, 003-008, 017, 019-026, 030-039, 043, 044, 050, 057-062, 066-069, 073, 075-078) | review stages and authority limits; appointments; financial approval; procurement hierarchy; reports and reminders; integrations; external execution; agency status; project updates; configurable policy | BR | Specification scope agreement | Problem Statement Section 1 & Blueprint Step 3.8(h): Business rules for multi-tier authority limits, staff appointments, procurement hierarchy, reports, reminders, agency status, and configurable policy engine deferred beyond core research grant lifecycle baseline. Both students agreed. Skipped stubs deleted per Step 9 rule 3; designs preserved in BR_DESIGN.json. | no |

## Notes
- Related finding, not from the spec tests: `make check` fails on the 10/10 commit with ruff F403 at modules/rspc/tests/test_settings.py line 1 (`from config.settings.test import *`). Confirmed by the Q1 review as R-Q1-06. Fixed by Student 1 in 85f9647.
- Mapping choices the test writers made (closest fit to what exists): a consultancy request is a Proposal with proposal_type consultancy; BR-027 to 029 test a disburse request against a head's remaining balance as the procurement-against-budget case.
- A rebase gives every commit a new hash. After one, update every hash in this file.

## Q1 review
- Reviewed commit: 5e59325 (this branch's HEAD, no drift from upstream/main 5595be6). Review: module-review-prompt.md, round Q1, run by Student 2 in a fresh session.
- Verdict: not yet, 25 findings (R-Q1-01 to R-Q1-25). None are in modules/rspc/tests/spec/ or docs/09-rspc/spec-tests/, so all go to Student 1. The reviewer found that every spec-test commit touches only those two folders.
- Findings that match rows above: R-Q1-05 is TC-WF-013 (reject at HoD and at Dean collapse to one state); R-Q1-07 is the six failures (TC-UC-008, TC-BR-010, TC-BR-012, TC-BR-028, TC-FR-040, TC-WF-013); R-Q1-01 and R-Q1-02 are the disburse/disburse-approve skips (UC 047, 049, 088, 091; FR financial-request rows); R-Q1-03 and R-Q1-21 are the missing-workflow skip rows. The reviewer reproduced the WF-013 failure and the fund-approve stub (it returns 200 for an unknown tx_id) independently.
- Gates red at Q1: make check (ruff F403), pytest (6 failed), module coverage 87.36% against 90%, each spec strategy run alone, and 283 skips. These stay red until the missing features are built and their skipped tests are replaced.
- Partial round: make e2e, the fresh-install proof and the CSRF/login replay did not finish at Q1. Run them in Q2.
- Round log: Q1 results sent to Student 1. Student 1 addressed all findings in commits 85f9647, 58fea0d, 4b05ab8, and 5885192.

## Q2 review
- Reviewed commit: bcefa36 (Student 1 fixes 5885192 + triage update). Review: module-review-prompt.md, round Q2, run by Student 2 in a fresh session.
- Spec tests: all 4 suites executed (FR: 35 passed, UC: 28 passed, BR: 34 passed, WF: 1 passed = 98 total passed, 0 failed, 0 skipped).
- Triage status: 0 open rows. All 6 candidate defect failures from baseline confirmed fixed in 85f9647 and passing at 5885192. All 283 deferred NOT_AUTOMATED test stubs resolved per pair agreement citing Problem Statement Section 1 and scope boundary CFRs (CFR-022, 025, 026, 027, 028) per Blueprint Step 3.8(h); stubs deleted by Student 2 per Step 9 rule 3 while test designs remain frozen in `*_DESIGN.json`.
- All gates green:
  - Gate 1 (`ruff check .`): All checks passed (0 errors across workspace).
  - Gate 2 (`lint-imports`): Contracts: 5 kept, 0 broken.
  - Gate 3 (pytest module suite): 70 passed in 4.76s, coverage 91.98% (exceeds 90% threshold). Domain coverage: 95.27% (exceeds 95% threshold).
  - Gate 4 (spec tests): 98 passed, 0 failed, 0 skipped across all 4 strategy suites.
  - Gate 5 (`make check-client`): 10/10 test files passed, 55/55 tests passed, TypeScript clean, Vite production build clean.
  - Gate 6 (`manage.py check --deploy`): System check identified no issues (2 silenced).
  - Gate 7 (`manage.py permission_manifest --check`): Matches registry.
  - Gate 8 (`ops/docs/rspc_reference.py`): Clean generation, 37 live IDs verified.
  - Attribution check: git log and diff clean; only Akshat01g and Ruthvik Gundelli present.
- Findings: 0 open findings across all nine dimensions.
- Verdict: 10/10 in all nine dimensions.
