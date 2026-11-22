# Quizzing final-check triage

Branch: `a9`

Reviewed commit: `6047e07`

Scope: final Student 2 review of the quizzing implementation against the synchronized specification set. No production implementation files were changed.

## Result

The module is **not ready for a 10/10 sign-off**. The five issues raised in the initial review were not fully resolved by `6047e07`; the earlier source checks were too permissive and passed on comments, docstrings, or surface-level names. The checks have been tightened to check for behavior and wiring. They now produce five failures and five passes.

## Focused checks

| Run | Checks | Passed | Failed | Skipped |
|-----|-------:|-------:|-------:|--------:|
| Focused spec assertions | 10 | 5 | 5 | 0 |
| Existing Quizzing service test | 1 | 1 | 0 | 0 |

The test command used an in-memory SQLite database and disabled project migrations to work around the unavailable PostgreSQL service. This is a local diagnostic run, not the repository's canonical test environment. The focused source assertions use Python's standard library and can run without a database.

## Open specification gaps

| Test ID | Source ID | Category | Evidence at `6047e07` | Required follow-up | Status |
|---------|-----------|----------|----------------------|--------------------|--------|
| QZ-SPEC-001 | AFR-QZ-001.3 | Implementation gap | `get_student_quizzes()` returns all published/closed quizzes for every non-empty `student_id`; the ID is not used in a queryset predicate. `get_quiz_for_actor()` also exposes every published/closed quiz. | Apply real student eligibility scoping to both list and detail access. | Open |
| QZ-SPEC-002 | AFR-QZ-005.2 | Implementation gap | Question-bank creation and routes exist, but search covers bank title and question retrieval filters only by type. There is no topic/difficulty filter or topic/unit question field. | Implement the required subject/topic, difficulty, and type search/filter behavior and test reuse. | Open |
| QZ-SPEC-003 | BR-QZ-017 | Implementation gap | A Celery task and `modules/quizzing/schedule.py` exist, but `config/celery.py` merges only the Placement schedule. The quizzing expiry task is therefore not registered in Beat. | Register the quizzing Beat schedule and verify the task runs on an idle expired attempt. | Open |
| QZ-SPEC-004 | AFR-QZ-012.2–012.5 | Implementation gap | `AiEvaluationService` performs local keyword matching against `correct_answer`; it accepts no professor criteria and returns no strengths or missing/incorrect concepts. The marks are advisory, but the specified AI evaluation flow is absent. | Implement the specified evaluation component inputs/outputs and retain Professor confirmation as the final grade. | Open |
| QZ-SPEC-005 | AFR-QZ-015.2 | Implementation gap | `get_quiz_performance_metrics()` sets `total_enrolled` equal to `attempted_count` and returns no not-attempted count. | Calculate enrolled and attempted populations separately and expose not-attempted students/count as specified. | Open |

These five failed checks are candidates for confirmed defects. The source evidence is clear, but full PostgreSQL-backed API verification was unavailable.

## Checks that passed

| Test ID | Source ID | Evidence |
|---------|-----------|----------|
| QZ-SPEC-006 | BR-QZ-008 | `start_attempt()` counts prior attempts and applies the configured maximum. |
| QZ-SPEC-007 | BR-QZ-006 | Schedule validation rejects an end time at or before the start and a non-positive duration. |
| QZ-SPEC-008 | BR-QZ-016 | `save_answer()` rejects changes when an attempt is no longer in progress. |
| QZ-SPEC-009 | BR-QZ-010 | Linear navigation invokes the rule that rejects backward movement. |
| QZ-SPEC-010 | BR-QZ-021 | Serializers mask student scores and feedback until grades are released. |

## Additional implementation and security findings

- The Question Bank question endpoint authorizes a general author role but does not verify that the caller owns the bank or is associated with its course. A professor who knows another bank's ID can read or add questions there (BR-QZ-002).
- Quiz creation checks the author role but does not verify that the professor is associated with the submitted `course_code` (BR-QZ-002).
- `QuizService.save_answer()` has an alternate argument form that sets `student_id` to `None`, bypassing the service-level attempt-owner check. The current API call supplies the student ID; the alternate form remains unsafe for any other caller (BR-QZ-004).
- No complete activity audit trail for quiz creation/changes, submission, evaluation, and result release was found (BR-QZ-022). Integrity-event logging does not cover those events.
- No notification generation for the specified student/professor events was found (BR-QZ-024 / AFR-QZ-016.1–016.2).
- Quiz instructions are stored only as `description`; there is no separate instructions field. Quiz update/edit endpoints are absent, and the QuestionType enum has no fill-in-the-blank type (AFR-QZ-002.3–002.5, AFR-QZ-004.5).
- Quiz result records do not include the full set of stated fields such as percentage, correct/incorrect/unanswered counts, and time taken (AFR-QZ-013.1).

## Requested project checks

The Windows `mingw32-make` binary could not launch in this environment (system DLL relocation). I ran the available recipes directly where possible:

| Check | Result | Evidence / limitation |
|-------|--------|-----------------------|
| `make check` | **Fail / incomplete** | Exact Make target could not start. `manage.py check` passed; `ruff check .`, import-linter, cross-module FK, and plural-contract checks passed. `makemigrations --check --dry-run` reported required changes in a new `0002` migration. `permission_manifest --check` reported a stale manifest. OpenAPI generation failed with serializer inference errors and operation ID collisions. Navigation check failed for three quizzing links/routes. PostgreSQL was unavailable, so canonical full-suite tests did not run. |
| `make check-client` | **Fail** | Exact Make target could not start. `npm test` passed: 4 files, 35 tests. `npm run typecheck` and `npm run build` failed on unused React imports and an optional-number type error in `QuizGradingPage.tsx`. |
| `make e2e` | **Not available** | No `e2e` Make target, Playwright configuration, or client E2E test files are present in this checkout. |

## Nine-dimension scorecard

| Dimension | Status | Evidence |
|-----------|--------|----------|
| Spec | **Fail** | Five focused requirements remain unmet; additional missing behaviors are listed above. |
| Arch | **Fail** | Migration drift, stale permission manifest, and OpenAPI generation errors. |
| Code | **Fail** | Eligibility scoping and analytics behavior are incorrect; question-bank filtering is incomplete. |
| Security | **Fail** | Quiz eligibility/course scope and question-bank ownership are not enforced consistently; alternate `save_answer()` form bypasses owner validation. |
| Tests | **Fail** | Five focused checks fail; only the existing single Quizzing service test passed under the local SQLite override. Canonical PostgreSQL tests were unavailable. |
| E2E | **Not verified** | No E2E target or browser test suite is present. |
| Frontend | **Fail** | Client typecheck/build fail, and the navigation check reports three quizzing route/sidebar mismatches. |
| Ops | **Fail** | The quizzing expiry schedule is not registered with Celery Beat; canonical database-backed checks could not run. |
| Hygiene | **Partial / fail overall** | `ruff check .` passes, but generated migrations/permissions are stale and the schema cannot be generated cleanly. |

## Environment and reproducibility

- Focused source checks: `.venv\\Scripts\\python.exe -m unittest discover -s modules/quizzing/tests/spec -v` (5 failures, 5 passes).
- Quizzing tests: `pytest modules/quizzing/tests` under a temporary in-memory SQLite override with migrations disabled (five specification assertions fail; the existing Quizzing service test passes).
- PostgreSQL on `127.0.0.1:5432` was not available. The local SQLite run does not substitute for the canonical PostgreSQL suite.
- `npm ci` installed the locked client packages in ignored `client/node_modules`; no tracked package files were changed.

No open issue can be closed honestly until the implementation and the failed gates are corrected. This triage records the remaining work rather than changing expected results to make the suite green.
