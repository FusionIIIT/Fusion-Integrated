# Assignment 6B — ELM Phase-2 Review Notes

## Scope
This branch starts from the Assignment 6A branch and contains the ELM module changes for Phase 2. The earlier branch is left unchanged. This is a working submission, not a claim of deployment readiness.

## Issues addressed in this iteration
- Represent resumption review as an explicit terminal state with a persisted outcome so a reviewed resumption cannot be processed again.
- Normalize older closed/reviewed rows through a data migration.
- Lock application/balance rows for write paths that could otherwise race.
- Reject stale substitute requests and responses for applications no longer awaiting consent.
- Keep a rejected cancellation request separate from the original approved leave.
- Record a distinct year-end carry-forward ledger event and avoid granting annual entitlement twice when the next-year balance already exists.
- Add/adjust API and state-transition tests, and update the employee list to show resumption outcome/status.

## Evidence and verification status
- The working copy was prepared from the full ELM project snapshot provided for this assignment, not from another pair's source.
- Python syntax compilation was performed on the prepared working copy. Django-backed tests were not executed because Django dependencies were unavailable in the preparation environment.
- Frontend build, database migrations against a real database, live IAM/Fusion integration, and end-to-end browser workflows remain unverified.
- Do not interpret the existence of tests as evidence that they pass. Run the commands in the repository environment and replace this status with actual results.

## Remaining work
1. Install project dependencies using the repository's documented environment.
2. Run the migration plan, apply migrations to a disposable development database, and check for schema drift.
3. Run the ELM service/API tests and the full project test/check target.
4. Build the frontend and exercise the module through Fusion login and permission grants.
5. Compare the resulting behavior against the full ELM functional, business-rule, use-case, workflow and traceability specifications.
6. Record failing tests, fixes, evidence and unresolved issues before marking the PR ready for review.
