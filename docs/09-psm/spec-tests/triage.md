# PSM specification-test baseline triage

## Scope and evidence

- Student 1 baseline reviewed: `95baf00` (`Update PSM docs and test report`)
- Frozen design commit: `a8d280b` (`Freeze PSM specification test designs`)
- Baseline test commit: this commit (`Add PSM specification test suites and baseline triage`)
- Result artifacts are intentionally external to Git at `../spec-results/`; each
  strategy directory contains `pytest.log`, `junit.xml`, and `coverage.xml`.
- No production PSM file was changed while preparing these tests.

## Execution summary

| Run | Strategy | Design cases | Passed | Failed | Skipped | Line coverage | Branch coverage | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | FR | 110 | 52 | 12 | 46 | 41.66% | 53.68% | `../spec-results/baseline/fr/` |
| Q2 rerun | FR | 110 | 64 | 0 | 46 | 44.27% | 57.37% | `../spec-results/Q2/fr/` |
| Baseline | BR | 80 | 33 | 0 | 47 | 29.79% | 47.89% | `../spec-results/baseline/br/` |
| Baseline | UC | 87 | 2 | 6 | 79 | 21.18% | 16.32% | `../spec-results/baseline/uc/` |
| Q2 rerun | UC | 87 | 8 | 0 | 79 | 24.88% | 26.02% | `../spec-results/Q2/uc/` |
| Baseline | WF | 28 | 11 | 0 | 17 | 22.73% | 35.71% | `../spec-results/baseline/wf/` |
| Final verification | FR | 110 | 64 | 0 | 46 | 44.07% | 55.61% | `../spec-results/final/fr/` |
| Final verification | BR | 80 | 33 | 0 | 47 | 29.65% | 46.43% | `../spec-results/final/br/` |
| Final verification | UC | 87 | 8 | 0 | 79 | 24.88% | 26.02% | `../spec-results/final/uc/` |
| Final verification | WF | 28 | 11 | 0 | 17 | 22.73% | 35.71% | `../spec-results/final/wf/` |

The Q2 reruns verify that the baseline failures were test-setup defects, not
production regressions. Remaining skips are intentional `NOT_AUTOMATED`
outcomes for absent PSM capability; they remain open implementation work.

## Closed test-generation / test-implementation findings

| Strategy | Cases | Category | Evidence and resolution | Status |
| --- | --- | --- | --- | --- |
| FR | TC-046, TC-048--TC-050, TC-052--TC-054, TC-056--TC-060 | Test-generation / test-implementation problem | The PO/GRN tests created an indent but did not seed the required `APPROVED` approval-state precondition. The test fixture now establishes that precondition; Q2: 64 passed, 0 failed. | Closed |
| UC | TC-002, TC-003, TC-012, TC-026, TC-029, TC-039 | Test-generation / test-implementation problem | A test fixture forwarded `requestor_id` to the public service, whose supported interface does not accept it. The fixture now creates the indent through the public interface and seeds only its documented preconditions; Q2: 8 passed, 0 failed. | Closed |

## Open skipped-case triage

Every test ID listed below is present in its frozen design JSON and has an
explicit `NOT_AUTOMATED` reason in the corresponding JUnit XML. The source
requirement/use-case/rule/workflow trace is preserved in that design file.

| Strategy | Skipped cases | Category | Evidence | Required owner action | Status |
| --- | --- | --- | --- | --- | --- |
| FR | TC-018, TC-021--TC-023, TC-025--TC-026, TC-029, TC-032, TC-035--TC-036, TC-041--TC-045, TC-055, TC-061--TC-068, TC-070--TC-071, TC-073, TC-088--TC-106 | Confirmed implementation defect | `../spec-results/baseline/fr/junit.xml` records the missing event, workflow, discrepancy, payment, reporting, audit, and notification capabilities. | Implement the PSM services/models/background work needed by the listed FR cases, then replace each skip with the frozen designed assertion. | Open |
| BR | TC-BR-010--TC-BR-014, TC-BR-017--TC-BR-020, TC-BR-025--TC-BR-026, TC-BR-030, TC-BR-032--TC-BR-034, TC-BR-037, TC-BR-041--TC-BR-045, TC-BR-049--TC-BR-054, TC-BR-057--TC-BR-061, TC-BR-063, TC-BR-065--TC-BR-071, TC-BR-073--TC-BR-077, TC-BR-079--TC-BR-080 | Confirmed implementation defect | `../spec-results/baseline/br/junit.xml` records absent rule-enforcement interfaces and state transitions. | Implement the missing rule enforcement, authorization, lifecycle, and reporting behavior; then automate the frozen rule cases. | Open |
| UC | TC-001, TC-004--TC-011, TC-013--TC-025, TC-027--TC-028, TC-030--TC-038, TC-040--TC-052, TC-055--TC-087 | Confirmed implementation defect | `../spec-results/Q2/uc/junit.xml` records absent user-facing/service flows, including the scheduled-report alternatives in TC-086 and TC-087. | Implement the missing use-case services/interfaces and schedule/report capability; then replace each skip with the frozen designed assertion. | Open |
| WF | TC-001--TC-003, TC-007, TC-009, TC-011--TC-014, TC-018--TC-019, TC-021, TC-023--TC-024, TC-026--TC-028 | Confirmed implementation defect | `../spec-results/baseline/wf/junit.xml` records missing workflow/state-machine transitions. | Implement the missing workflow transitions, notifications, and audit records; then automate the frozen workflow cases. | Open |

## Completion gate

This is a Student 2 baseline, not a final green test delivery. The repository
has clean lint/format checks for `modules/psm/tests/spec`, but the 189 open
skips above require Student 1 production implementation before a final run can
have zero skips and zero failures.
