# Assignment 8 Final Submission Audit

**Pair:** 2 — Quizzes — 24bcs055 / 24bcs111  
**A8_BASE:** `c66c8f447b43dd7cd1331a02a85f455d7b7a947b`  
**Branch:** `assignment8/spec-driven-testing-20261108`  
**Audit outcome:** **Not submission-ready without disclosure/approval of the outstanding evidence and protocol gaps.**

## Executive result

The four frozen designs contain 123 cases. Each design `test_id` is represented once in its corresponding pytest suite, with a matching `source_id`; the supplied text-match audit reports zero missing IDs for all strategies. The final suites contain 123 nodes: 40 passed, 3 failed, and 80 explicitly skipped with `NOT_AUTOMATED` reasons. No frozen design or production-code changes were made.

The three failures are valid, reproducible BR assertions exposing one shared-root defect in state-machine guard enforcement. They are recorded as one confirmed defect, not three. The submission still has 54/123 cases not automated, the exact test-design prompts and separate frozen test snapshots were not preserved, and BR used three test-code-changing follow-ups against the two-prompt limit.

The per-case mapping is in [A8_TRACEABILITY_MATRIX.csv](./A8_TRACEABILITY_MATRIX.csv). The workbook and compact ZIP are separate deliverables; the ZIP contains the available required evidence and explicitly marks missing prompt evidence rather than fabricating it.

## Strategy execution and coverage

JUnit, coverage XML, and logs were regenerated sequentially with distinct `COVERAGE_FILE` values. Percentages below come from each strategy's isolated `coverage.xml` (`lines-covered / lines-valid`, `branches-covered / branches-valid`).

| Strategy | Tests | Passed | Failed | Skipped | Line coverage | Branch coverage | Duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| FR | 68 | 14 | 0 | 54 | 209/291 = 71.82% | 28/42 = 66.67% | 1.131 s |
| UC | 19 | 8 | 0 | 11 | 192/291 = 65.98% | 27/42 = 64.29% | 0.813 s |
| BR | 24 | 9 | 3 | 12 | 208/291 = 71.48% | 27/42 = 64.29% | 1.150 s |
| WF | 12 | 9 | 0 | 3 | 165/291 = 56.70% | 13/42 = 30.95% | 0.954 s |
| **Total** | **123** | **40** | **3** | **80** | — | — | — |

JUnit node counts, failure/skip counts, and pytest log summaries agree for all strategies. BR has three assertion failures and zero pytest errors; they are not setup failures.

## Design-to-test traceability

| Strategy | Frozen cases | One-to-one mapped | Executed (non-skipped) | Passed | Failed | NOT_AUTOMATED | Missing | Duplicated | Incorrect source mapping |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FR | 68 | 68 | 14 | 14 | 0 | 54 | 0 | 0 | 0 |
| UC | 19 | 19 | 8 | 8 | 0 | 11 | 0 | 0 | 0 |
| BR | 24 | 24 | 12 | 9 | 3 | 12 | 0 | 0 | 0 |
| WF | 12 | 12 | 9 | 9 | 0 | 3 | 0 | 0 | 0 |
| **Total** | **123** | **123** | **43** | **40** | **3** | **80** | **0** | **0** | **0** |

The audit script reports: FR `frozen=68 missing=0 skipped=54`; UC `19/0/11`; BR `24/0/12`; WF `12/0/3`. The skipped cases remain individually mapped and have explicit reasons. Their intended flows require missing service/API, persistence, authorization, orchestration, UI, or external interfaces; the executable domain tests are scoped to callable behavior and do not claim end-to-end coverage. WF's three skips require evaluation orchestration not exposed by the available M3 interface.

## Skipped tests and defects

- **Skipped:** FR 54, UC 11, BR 12, WF 3; total 80. The test functions contain explicit `pytest.skip("NOT_AUTOMATED: ...")` messages naming the unavailable interface/behavior. No tests were automatically unskipped.
- **Confirmed defect:** one unique BR defect, exposed by `BR-BR-QZ-006`, `BR-BR-QZ-021`, and `BR-BR-QZ-023` (source IDs `BR-QZ-006`, `BR-QZ-021`, `BR-QZ-023`).
  1. The business rules require availability boundaries, configured result visibility, and permission-gated archival.
  2. The tests use valid M1/M3 domain states and assert those specified denials.
  3. All three failures reproduce in the isolated BR suite.
  4. `modules/quiz/state_machine.py::apply_transition` invokes `row.guard(ctx)` but ignores a returned `False`, then proceeds to the destination state. The applicable guards in `quiz_machine.py` and `result_machine.py` return booleans.
- Discovery overlap: **1 unique to BR; 0 shared; 0 found by FR, UC, or WF.** Three failing tests refer to the same guard-handling root cause and are logged once in the workbook.
- Production code was intentionally not changed.

## Integrity and required artifacts

Verified:

- Four frozen design JSON files and four strategy test folders are present.
- Four JUnit XML, coverage XML, and pytest logs are present and current.
- `git diff` against A8_BASE for `modules/quiz` is empty; frozen designs are unchanged from repository HEAD.
- Existing non-A8 test files were not changed during this audit.
- Workbook retains the four original sheets and its formulas; one unique BR defect row is populated.
- ZIP contains only the requested workbook, designs, strategy tests, prompt records, execution results, and `code_reference.txt`; its size is checked separately.

Not preserved / not verifiable:

- The exact original test-design prompt for each strategy is unavailable. The prompt files say this directly; they do not reconstruct it.
- Separate RAW/FINAL frozen test snapshots and the full AI interaction history were not found. The questionnaire says full chat transcripts are not required, but exact test-design prompts remain required.
- Exact model/version and whether the same model/session setup was used for every strategy cannot be verified. No Qwen model is claimed.
- Pair roll numbers and module name were supplied by the user; no model/version was supplied as verifiable execution evidence.

## Protocol deviations and readiness

- BR required **three test-code-changing follow-ups**, exceeding the allowed maximum of two by one. FR, UC, and WF each used two test-code-changing follow-ups.
- The missing original test-design prompts and separate snapshots prevent confirmation that all prompt/snapshot submission requirements are met.
- The 80 justified `NOT_AUTOMATED` cases and three genuine BR failures are reported, not concealed. No production changes, expected-result changes, `xfail`, or fabricated results were used.

**Final readiness: NOT READY TO CLAIM FULL COMPLIANCE.** The package is a factual evidence bundle, not a clean/pass-complete submission. Before submitting, the pair should consult the instructor about the BR follow-up limit and the missing original design prompts/snapshots, and report the BR defect/failures as recorded.
