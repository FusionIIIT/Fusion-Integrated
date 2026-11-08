# ELM Model Trial Brief — Assignment 6

## 1. Objective

Implement and evaluate Employee Leave Management (ELM) as a module within the existing Fusion ERP repository. This is Model 1's independent trial. Start from the clean official repository checkout; do not reuse code from an earlier ELM implementation.

The implementation must integrate with the existing Fusion architecture where appropriate rather than creating an unrelated standalone application.

## 2. Repository and trial integrity

- Official repository: https://github.com/FusionIIIT/Fusion-Integrated.git
- Trial baseline commit: `02b01fe`
- Trial directory: `ELM_MODEL_1`
- Treat the supplied ELM documents as the authoritative requirements.
- Inspect the existing repository before choosing an architecture.
- Preserve existing modules and shared infrastructure.
- Do not overwrite or copy implementation code from another trial or the user's older repository.
- Do not push changes to the remote repository.
- Record actual implementation results, test results, limitations, and failures honestly.

## 3. Authoritative specifications

Read the supplied source documents in `docs/ELM/` before implementation:

1. `01_ELM_Problem_Statement_v1.4_FINAL.docx`
2. `02_ELM_Functional_Requirement_Specification_v1.5_FINAL.xlsx`
3. `03_ELM_Use_Case_Specifications_v1.4_FINAL.docx`
4. `04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx`
5. `06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`
6. `06_ELM_Workflow_Specifications_v1.6_FINAL.docx`
7. `Assignment-6-Instructions.docx`

`ELM_SPECIFICATIONS_EXTRACTED.md` contains extracted text for reference. Check the original Word/Excel documents when a table, rule, relationship, or detail is ambiguous. Do not assume the extracted text replaces the original specifications.

The FR workbook contains 32 CFRs and 128 AFRs. Use the complete workbook and traceability matrix to plan coverage; do not implement only the examples in this brief.

## 4. Use-case registry

The synchronized baseline has 20 active use cases and one retired use case.

Active actor-triggered use cases:

- EL-UC-001: Apply for Leave
- EL-UC-002: Respond to Substitute Request
- EL-UC-003: Review Leave-Related Request at Unit Head
- EL-UC-004: Verify and Route Higher-Sanction Request
- EL-UC-005: Make Final Sanctioning Decision
- EL-UC-007: Withdraw Pending Request
- EL-UC-008: Request Cancellation of Approved Leave
- EL-UC-009: Request Extension of Ongoing Leave
- EL-UC-010: Submit Resumption of Duty
- EL-UC-011: Review Resumption
- EL-UC-012: View Leave Balances and History
- EL-UC-013: Obtain Printable/Exportable Leave Application
- EL-UC-014: Maintain Policy and Hierarchy Configuration
- EL-UC-015: Maintain and Publish Holiday/RH Calendar
- EL-UC-016: Record Already-Sanctioned Offline Leave
- EL-UC-017: Maintain Authorized Leave Records
- EL-UC-018: Configure Workflow SLA Thresholds
- EL-UC-019: Nominate Replacement Substitute After Decline

Active event-triggered use cases:

- EL-UC-020: Execute Year-End Leave Processing
- EL-UC-021: Process SLA Threshold Event

Retired use case:

- EL-UC-006: Modify Pending Request. Do not implement this as an active in-place modification workflow. Pending requests must follow the applicable withdrawal and fresh-application process.

Use the full use-case specifications and workflow document to determine states, transitions, actors, preconditions, exceptions, and downstream actions.

## 5. Leave categories and core policy

The application covers Casual Leave (CL), Restricted Holiday (RH), Special Casual Leave (SCL), Earned Leave (EL), Vacation Leave (VL), and Commuted Leave (COL). Station Leave details are captured within the relevant application when applicable, not through an unrelated second leave-request process.

Important baseline rules to verify against the source specifications:

- CL: 8 days annually; half-day accounting is supported; unused balance lapses.
- RH: 2 days annually; requests must match the effective published holiday/RH calendar; unused balance lapses.
- SCL: up to 15 days annually; admissibility is decided by the applicable sanctioning authority; unused balance lapses.
- EL: 30 days annually for non-faculty employees; unused balance carries forward.
- VL: 60 days annually for faculty, tied to applicable vacation periods supplied by the Academic Calendar. At year-end, unused VL converts to EL at 2 VL : 1 EL, including fractional results; VL itself does not carry forward.
- COL: 20 days annually for eligible employees; applicable medical evidence and balance rules must be enforced; unused balance carries forward.
- For EL/COL/VL, the continuous leave interval counts intervening weekends and closed holidays. Do not apply this counting rule indiscriminately to CL/SCL/RH.
- Two CL half-day requests on the same date are not automatically an impermissible overlap.

Treat these values as the synchronized baseline, while implementing any configurable values according to the authoritative requirements. Do not invent policy rules absent from the specifications.

## 6. Validation and workflow invariants

- Validate category eligibility, entitlement/balance, dates, applicable calendar/counting rules, and impermissible overlap before a request progresses.
- Where responsibility coverage is required, the substitute must be eligible, must not be the applicant, and must have no impermissible overlapping pending/approved leave during the responsibility period.
- Required substitute acceptance is a gate: no approval routing before acceptance. A decline permits replacement handling or withdrawal as specified.
- CL/RH normally receive a final Unit Head decision.
- SCL/EL/COL/VL follow the required Unit Head recommendation and configured higher-sanction path. A Unit Head's “Not Recommended” is not itself a final rejection.
- Resolve the competent authority using the applicant's context and current hierarchy configuration. Apply the Director-applicant self-sanction path where required.
- Final decisions must be recorded; notify the employee as required and update leave accounts after applicable approval.
- A pending request cannot be edited in place. Withdrawal before final approval must immediately stop remaining processing and prevent later stale approval/rejection actions.
- Approved leave must not be edited in place to cancel it. Cancellation is a separate request before the leave starts, follows the required hierarchy, and restores/adjusts the balance only when approved.
- Extension approval posts only the incremental additional period. Extension rejection preserves the original approved leave.
- Resumption is a reviewed process for applicable leave categories. If the actual resumption date equals the approved end date, do not adjust the approved leave period or balance. Earlier/later resumption requires the prescribed review and applicable record/balance adjustments.
- Policy/hierarchy configuration uses current configured values; do not invent a policy draft/publish/version lifecycle.
- A revised holiday/RH calendar becomes effective through publication. Until then, the current published calendar remains effective.
- Offline-sanctioned leave is entered by an authorized administrator with required evidence; do not create a second approval workflow.
- Year-end processing must implement lapse/carry-forward/conversion rules and record account transactions.
- SLA reminders and escalations must act only on tasks that remain pending and must be logged as specified.

These are high-risk invariants, not a replacement for reading the complete specifications.

## 7. Required engineering approach

Before editing files:

1. Inspect the repository tree, module conventions, dependencies, routing, database models, authentication/authorization, frontend structure, and test setup.
2. Identify the closest existing modules and shared services that can be reused.
3. Report the proposed ELM location and architecture with exact repository paths.
4. Identify dependencies and commands needed to build, run, and test the module.
5. Do not assume a workflow engine, notification service, frontend framework, or database capability exists without verifying it in the repository.

During implementation:

- Follow established project conventions.
- Make changes across the relevant backend, frontend, database, routes, permissions, and tests as the existing architecture requires.
- Avoid duplicating common Fusion infrastructure.
- Add tests for policy validation, workflow transitions, authorization, balance transactions, and critical exception cases.
- Do not claim a requirement is implemented merely because a screen or model exists.
- Keep changes local; do not push to the remote.

## 8. Evaluation and evidence

Record actual observations for:

- Repository baseline and commit.
- Model name/version, runtime, tool, configuration, and local resource usage where available.
- Whether the model successfully accessed and used the specifications and repository.
- Files created or modified and the purpose of each.
- Shared Fusion components reused.
- Build/run commands and actual results.
- Tests passed, failed, skipped, or not run.
- Requirements implemented, partially implemented, or not implemented.
- Problems, workarounds, time spent, and remaining limitations.

The assignment compares independent local model trials. Do not transfer Model 1 implementation files or implementation-specific advice into Model 2's trial. Keep the two repositories separate and report failures honestly.

## 9. First task: read-only repository assessment

For now, inspect only. Do not create, edit, or delete application code.

Report:

1. Repository architecture and relevant existing modules, citing exact paths.
2. Backend, frontend, database, authentication/authorization, and test technologies actually present.
3. Existing shared functionality that ELM could reuse.
4. A proposed ELM module structure consistent with this repository.
5. Dependencies, commands, and likely integration risks.
6. Important requirement ambiguities or gaps that must be checked against the source documents.

Wait for explicit approval before implementing code.
