# HR-EIS — Student 1 technical handoff

**Branch:** [module/hreis](https://github.com/keptbeetle/Fusion-Integrated/tree/module/hreis)
**Working checkout:** `D:\fusion\Fusion-Integrated-A9-HREIS`
**Date:** 2026-11-22
**Status:** technical handoff candidate; independent review and formal approvals must be read from the latest quality-report checkpoint.

## Read first

- `hreis-quality-report.md`, section 25: current verification and open boundaries;
  earlier numbered sections are historical checkpoints.
- `browser-coverage.md`: all 21 live use-case mappings and isolated test commands.
- `hreis-blueprint.md`: source interpretation and unresolved institutional choices.
- `hreis-traceability-status.md`: 193 live IDs, 188 direct builder-test links and
  six explicit source/integration gaps.
- `browser-walkthrough.md`: all twelve designations and real request-log evidence.
- `hreis-reference.md`: generated, validated enforcement links for 193 live IDs.
- `review-remediation.md`: the initial independent scorecard and candidate fixes.
- `procedure-deviation.md`: owner's instruction to continue, and the absence of
  independent written Student 2 approval.
- `student2-approval-request.md`: unsigned paperwork for later review.

## Implemented journeys

Employees read their official records and verified balances, submit and track
leave, submit LTC/CPDA advances or reimbursements, and submit annual appraisals.
Request Details shows the maintained authority history, rejection reasons and
reported financial status history within the same server-side row scope.

HR creates/revises official records, records verified leave credits, publishes
immutable effective-dated policy, verifies documentary/eligibility evidence,
assigns appraisal reviewers, and reads restricted audit/compliance information.
HOD/current authority forwards or rejects; final authority approves or finalizes
appraisals into immutable service history. Self-approval is refused.

Accountant correctness review and externally referenced status recording are
separate permissions. Terminal financial statuses are immutable, and each
recorded status has an immutable historical entry. Processing can be recorded
while external status is unavailable, then a later report is appended. These operations record
externally attested information; they do not execute or verify an actual payment.

Workflow notifications, configured pending-action reminders and policy/deadline
notices create durable dashboard/outbox evidence. Generation is idempotent and
does not advance workflow state. The configured email backend is the delivery
boundary; official SMTP/provider operation is not certified by synthetic tests.

## Reproduce verification

Use the README's Linux/WSL setup, Node 20.19 or a newer supported LTS, PostgreSQL
and Redis. Supply the local development DB credential in the environment without
committing it. Run `make check`, `make check-client`, the two coverage commands in
the quality report, and the production-settings deployment check from CI.

For Chromium use `client/e2e/hreis/run-isolated.sh` as documented in
`browser-coverage.md`. It requires synthetic IAM on 8001 and free ports 8002/5173.
It creates, migrates and drops its own database. A temporary synthetic IAM service
credential is revoked at exit. Never point the fixture opt-in at institutional IAM.

Builder tests are under `modules/hreis/tests`, frontend tests under
`client/src/modules/hreis`, and browser journeys under `client/e2e/hreis`.
Raw logs, audit output and previous mutation/mobile evidence are outside Git at
`D:\HR(EIS)\lab 9\evidence` and the adjacent mutation-results directories.

The unmerged module now has one clean initial migration. Use a fresh database
for a clean installation; preserve and separately upgrade any older draft data.

## Deferred boundaries

Student 2 communication and written approvals remain deferred at the owner's
request. No signature, institutional policy ruling or formal review score is
assumed. The provisional `Accounts Admin` mapping still requires institutional
confirmation. Actual document storage, finance exchange, provider credentials and
operational delivery need the external systems described in the source documents.

Student 2's reserved `modules/hreis/tests/spec` and
`docs/09-hreis/spec-tests` have not been authored or edited by Student 1. The
independent specification-test phase and final institutional pull request are
separate from this branch handoff. Do not describe this document as final
Assignment 9 approval or a production deployment certificate.
