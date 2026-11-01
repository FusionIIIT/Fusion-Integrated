# Assignment 7 IAA implementation progress

## Scope and source versions

- Assignment: Assignment 7, Institute Accounts and Audits (IAA).
- Team roll numbers: 24BCS202 and 24BCS258.
- Submission guideline: `Assignment 7 Submission Guidelines.docx` (provided 2026-11-02).
- Problem statement: `01_IAA_Problem_Statement_v1.2_SYNCHRONIZED.docx` (synchronized v1.2).
- Requirements: `02_IAA_Requirement_Registry_CFR_AFR_v1.3_FINAL.docx` (final v1.3).
- Use cases: `03_IAA_Use_Case_Specifications_v1.3_FINAL.docx` (final v1.3).
- Business rules: `04_IAA_Business_Rule_Specifications_v1.3_FINAL.docx` (final v1.3).
- Workflows: `05_IAA_Workflow_Specifications_v1.3_FINAL.docx` (final v1.3).
- Traceability: `06_IAA_CFR_AFR_Traceability_Matrix_v1.3_FINAL.xlsx` (final v1.3; six worksheets inspected).
- No newer IAA specification or prior-analysis workbook was present in the supplied specification directory.

## Requirements discovered

- 18 consolidated requirements (CFR-IAA-01 through CFR-IAA-18) and 75 atomic requirements (AFR-IAA-001 through AFR-IAA-075).
- 25 actor-triggered use cases (IAA-UC-101 through IAA-UC-704) and 2 event-triggered use cases (IAA-UC-203 and IAA-UC-304).
- 19 business rules (IAA-BR-001 through IAA-BR-504).
- 19 basis workflows (BW-IAA-01 through BW-IAA-19) and 4 composite workflows (CW-IAA-01 through CW-IAA-04).
- Actors: Basic User, Finance Staff, HoD, Dean, Director, Auditor, System Admin. HoD, Dean, and Director are distinct roles. System Admin is barred from operational financial data and approval work. Internal processing records governance completion only; it does not execute a payment.
- Policy thresholds and timeout durations must be configurable; no numeric values may be hard-coded. Budget insufficiency creates an anomaly path, not automatic rejection.
- The source traceability workbook has no row-level mapping data in columns E-J (UC, BR, workflow, transition, minimum representation, coverage) for any of its 75 AFR rows, despite its summary claiming 75/75 full coverage. The UC, BR, and workflow indexes also leave requirement cross-references blank. Exact source-authored AFR crosswalks therefore cannot be asserted from these files.
- The source package defines actor roles but does not map them to actual IAM designation names. The user authorized using the exact actor labels as IAA role keys. Identity/module grants remain IAM-owned; the current repo has no IAM role-switch/write endpoint, so IAA role switching uses a locally assigned IAA role context.
- Out of scope includes real monetary transfers; preserve the exact exclusions from PS section 10 during implementation.

## Repository baseline

- Source repository: `Usha2007-feb/Fusion-Integrated` (personal fork).
- Target repository: `FusionIIIT/Fusion-Integrated`, base branch `main` at `02b01fea4a67b257ea7000009f06a1561699550e`.
- Working branch: `assignment7-iaa`, based on target `main`; the local `main`/fork `origin/main` were 36 commits behind.
- Starting worktree contained only the unrelated untracked `ELM_SPECIFICATIONS(2).code-workspace`; it is preserved.
- No IAA module, route, registry entry, or IAA tests exist on the base branch.
- Architecture uses independent Django modules, module-owned models/migrations, pure-Python domain rules, selectors for visibility, services for writes, IAM `Principal` permission checks, `modules/<name>/registry.py`, and lazy client module routes.
- `core/` must not import modules; modules must only cross boundaries through a peer's `contracts.py`; no cross-module foreign keys are allowed.

## Implementation plan

1. Establish the IAA domain model and explicit legal state transitions for requests, TA claims, approvals, anomalies, and audit observations from the source workflow tables. Keep thresholds, timers, routing criteria, and supported policy values configurable.
2. Add IAA-owned models and migrations for configuration, requests/claims and evidence metadata, approval assignments/decisions, anomalies, audit observations/responses, notifications, and append-only action history. Use IAM IDs without foreign keys.
3. Implement selectors and transactional services that enforce ownership, active-role permissions, segregation of duties, validation, guards, routing, escalation, and audit attribution.
4. Add authenticated APIs and registry/navigation permissions. Wire only the specified event-triggered automation for overdue approvals and configured automatic anomalies, plus notifications where required.
5. Add the IAA client routes, role-appropriate request queues/forms/review/detail/report views, state displays, and validation feedback using the existing shell and UI patterns.
6. Build an AFR-level coverage matrix with acceptance checks and repository paths, clearly distinguishing direct source links from any mappings derived from text. Add requirement-mapped backend and frontend tests.
7. Run requested repository checks, IAA tests, migrations checks, client tests/build, inspect the diff, and update this report with actual results.

## Approval and change-management

- User authorized creating the `assignment7-iaa` feature branch and continuing after the plan is documented.
- The initial request prohibited commit/push until explicit authorization. The later user request explicitly authorized committing, pushing, and creating the PR. The unrelated workspace file remains excluded. The Assignment 7 Google Form was not submitted.
- The user authorized deriving and labeling candidate AFR-to-UC/BR/workflow links from detailed specification prose, and using the exact actor labels as IAA role keys.

## Implementation status

- Stage 1 (source review): completed; all six source files reviewed, including 23 workflows and 101 transition rows.
- Stage 2 (repository architecture): completed.
- Stage 3 (coverage matrix): completed for all 75 AFRs with derived links identified as candidates; the supplied RTM has no authored row-level crosswalk.
- Stage 4 (plan): documented above and implementation proceeded under the user's instruction.
- Stage 5 (implementation): backend models/domain/services/selectors/API/tasks/tests and client routes/API/workspace are present. Generated IAM permission manifest/catalogue entries were added and checked for orphaned grants and unreferenced permissions; systematic notification coverage still needs a final requirements audit.
- Stage 6 (verification): Python `compileall` passed. Django generated `modules/iaa/migrations/0001_initial.py`, and `makemigrations --check --dry-run` reported no changes using Django 5.2 with minimal IAA-only settings. IAA pytest suite passed 10 tests using an in-process `StrEnum` compatibility shim and SQLite because only Python 3.10 is available and PostgreSQL is not running; these are not full production-runtime checks. Client typecheck passed; Vitest passed 35 tests; Vite production build passed.
- Stage 7 (final diff and PR): the reviewed 40-file IAA-only change set is pushed to `Usha2007-feb/Fusion-Integrated:assignment7-iaa`; PR [#512](https://github.com/FusionIIIT/Fusion-Integrated/pull/512) is open against `FusionIIIT/Fusion-Integrated:main`.

## Files and verification log

- This report: `ASSIGNMENT7_PROGRESS.md`.
- Traceability matrix: `ASSIGNMENT7_TRACEABILITY.md` (75 AFRs and source transition inventory).
- Implemented files: `modules/iaa/`, `client/src/modules/iaa/`, and integration changes in config and client registry (see `git status`).
- Verification: `compileall`, project `manage.py check` (with Python 3.10 StrEnum compatibility shim), permission-manifest check, navigation-route check, migration consistency check, IAA pytest (10 passed under the compatibility/SQLite setup), client typecheck, Vitest (35 passed), Vite production build, and final `git diff --check` passed. Full project tests on Python 3.12/PostgreSQL were not run.
- Remaining: complete notification/test coverage review and rerun the full backend test suite on Python 3.12 with PostgreSQL available. The source RTM mapping defect remains documented. The local unrelated `ELM_SPECIFICATIONS(2).code-workspace` remains untracked and excluded from the PR.
