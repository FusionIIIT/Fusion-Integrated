# DEF-LMS-01 — Self-grading refusal

Phase: Step 8 defect handoff, Student 1 response. Recorded 23 November 2026 (IST).
Base: `600a6469438611af71c2081d2d21ffa2a7d0a503`. No independent Q1 verdict is claimed.

## Reported defect and authority

The partner handoff identifies TEST-BR-038 and TEST-UC-038: a person associated
as both Student and Faculty/TA could grade their own submission. Both tests
returned HTTP 200 before this fix. The 16 new builder regressions also failed
before the production change, reproducing creation/edit/release conflicts.

The current forwarded ruling explicitly prohibits this conflict. The unchanged
BR-LMS-015 authorizes/attributes Faculty and TA grading, but does not itself
contain the self-grading prohibition. The preserved 22 November blueprint approval
also lacks the newly quoted sentence. [D-07](policy-decisions.md#d-07--grader-and-submission-owner-must-differ)
therefore records the current handoff as an adopted clarification, without editing
the original specifications or signed approval.

## Implementation and atomicity

`services/grading.save_grade` locks and re-reads the authorized submission, then
calls the pure `domain.rules.independent_grader` rule. If the acting user is the
owner, it raises the standard HTTP 422 domain response with code
`CANNOT_GRADE_OWN_SUBMISSION` and an action directing the owner to another
authorized grader. The refusal occurs before grade/audit mutation, within the
existing atomic transaction. The same choke point covers POST, PATCH and release.
Course/module/verb/role/state authorization still applies.

Builder regressions exercise both Faculty and TA acting roles across absent,
Draft and Released grades, both POST and PATCH, Faculty self-release, exact error
codes and unchanged Submission/Grade/GradeAuditLog records. An independent
authorized grader can still grade successfully after the owner is refused.

## Verification

- Both reported partner cases pass unchanged.
- All LMS tests: 388 passed (225 builder cases plus 163 spec cases).
- Strategies run separately: FR 51, UC 47, BR 45, WF 20; 163/163 passed.
- Module branch coverage: 98.64%; pure domain: 100%.
- Full `make check` passed using the supplied `config.settings.test` settings.
- The first broad attempt selected development settings and had two IAM mock URL
  mismatches; the command was corrected to the supplied test settings without
  changing code, mocks or the harness, and verification passed.
- Every partner spec/design/triage file matches its pre-fix SHA-256. Student 1
  changed no file in either reserved spec-test directory.

The exact commands and machine logs are preserved in the local DEF-LMS-01 handoff.
This fix is local pending publication approval; commit identity is recorded in
that handoff manifest. No new dependency, database migration or shared platform
change is introduced.

## Review status and ownership

The partner triage currently calls f09c49d a 10/10 revision. The actual completed
Round 3 verdict on that commit had 13 open findings. Student 1 has left the
partner-owned triage untouched; Student 2 should correct that historical label.
This defect fix does not close the other Round 3 findings or provide a new
independent scorecard. Q1 verification and updates to spec-test triage remain
Student 2's work.
