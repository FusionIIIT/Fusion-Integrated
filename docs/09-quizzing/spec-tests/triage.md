# Quizzing spec check triage

Branch: `a9`

Review scope: initial 10-check source-level review against the synchronized Quizzing specifications.

Method: Python standard-library `unittest`; Django/pytest dependencies are not installed in this checkout.

## Results

| Run | Checks | Passed | Failed | Skipped | Result |
|-----|-------:|-------:|-------:|--------:|--------|
| Initial source review | 10 | 5 | 5 | 0 | 5/10 checks pass; five gaps flagged |

Run command:

```text
python -m unittest discover -s modules/quizzing/tests/spec -v
```

## Failures and candidate gaps

| Test ID | Source ID | Category | Evidence from branch `a9` | What needs attention | Status |
|---------|-----------|----------|----------------------------|---------------------|--------|
| QZ-SPEC-001 | AFR-QZ-001.3 | Candidate implementation gap | `get_student_quizzes(student_id)` filters only by quiz status; `student_id` is unused. | Scope student quiz listings and access to the student's eligibility. | Open; static check only |
| QZ-SPEC-002 | AFR-QZ-005.2 | Candidate implementation gap | Question and QuestionBank models/selectors exist, but the module URL table and views expose no question-bank management/search API. | Provide a supported professor interface to store, search/filter, and reuse bank questions. | Open; static check only |
| QZ-SPEC-003 | BR-QZ-017 | Candidate implementation gap | Expiry is checked during `save_answer`; no task or other event trigger submits an idle attempt at its deadline. | Ensure expiry triggers auto-submission without requiring another student request. | Open; static check only |
| QZ-SPEC-004 | AFR-QZ-012.2 | Candidate implementation gap | The service layer contains no AI evaluation integration or advisory evaluation result fields. Manual score override exists. | Add the AI-assisted path while keeping suggestions advisory and Professor-confirmed marks final. | Open; static check only |
| QZ-SPEC-005 | AFR-QZ-015.2 | Candidate implementation gap | No aggregate quiz metrics implementation or performance/report endpoint was found. | Expose the specified enrolled/attempted/not-attempted counts, average/high/low scores, and pass percentage. | Open; static check only |

These are implementation gaps indicated by source inspection, not confirmed runtime defects. The checks should be rerun as API/database tests in the configured project environment before treating the gaps as confirmed defects.

## Checks that passed

| Test ID | Source ID | Evidence |
|---------|-----------|----------|
| QZ-SPEC-006 | BR-QZ-008 | `start_attempt` counts existing attempts and calls `validate_attempt_limit` with `quiz.max_attempts`. |
| QZ-SPEC-007 | BR-QZ-006 | `validate_quiz_schedule` rejects an end time at or before the start and a non-positive duration. |
| QZ-SPEC-008 | BR-QZ-016 | `save_answer` refuses updates unless the attempt is `IN_PROGRESS`. |
| QZ-SPEC-009 | BR-QZ-010 | Linear navigation calls the back-navigation rule, which rejects an order before the last completed order. |
| QZ-SPEC-010 | BR-QZ-021 | Serializers mask scores and feedback while grades have not been released. |

## Additional areas not covered by the ten checks

- A complete audit trail for quiz creation/changes, attempts, evaluation, and result release was not found; the module has integrity-event logs, which do not by themselves cover the listed audit events (BR-QZ-022).
- Notification generation for the listed student and professor events was not found (BR-QZ-024 / AFR-QZ-016.1–016.2).
- The quiz model/API does not expose student instructions or a separately configured maximum-marks field, and there is no quiz update endpoint for pre-activation edits (AFR-QZ-002.3–002.5). These need direct integration checks.
- Background-application handling, tab blocking, image-based questions, and optional student performance-history fields are listed as unresolved or conditional in the synchronized traceability matrix; no pass/fail assertion was made for them.

## Environment limitation

The repository's Django/pytest environment is not installed in this checkout. `python -m pytest modules/quizzing/tests -q` could not start because `pytest` is unavailable. The source-level `unittest` checks executed and returned five assertion failures, as listed above; they do not execute Django services, serializers, or database behavior.
