# Assignment 8 — WF Backend Test Run

## Design and execution

- Frozen design: `a8_design/WF_DESIGN.json` (left unchanged)
- Pytest suite: `tests/a8/wf/`
- Workflow inventory: 21 (16 basis and 5 composite)
- Frozen test cases: 24
- Final run: 24 total; 14 passed; 0 failed; 0 errors; 10 skipped as frozen BLOCKED cases
- Final execution time: 3.974 seconds
- MMS line coverage: 67.37% (863 of 1,281 executable lines across `modules.mms`)
- Final failed IDs: none
- Blocked/skipped IDs: TC-WF-003, TC-WF-007, TC-WF-009, TC-WF-010, TC-WF-011, TC-WF-012, TC-WF-016, TC-WF-018, TC-WF-022, TC-WF-024
- Workflow coverage matrix: all 32 frozen matrix entries retained; 27 are TESTABLE and 5 are BLOCKED. Composite entries intentionally map to the same basis-path tests.
- Traceability: all 24 frozen test IDs are present in `tests/a8/wf/test_mapping.csv`.

The initial test run exposed a test assertion mismatch between the JSON numeric balance and serialized bill total for TC-WF-023. The assertion was made representation-safe in the test only; the final run passed. No production code, application settings, models, APIs, behavior, or ELM files were changed.

## Commands

Final isolated suite (executed after the one test-code repair):

```sh
.venv/bin/pytest tests/a8/wf/test_wf_cases.py -q --junitxml=a8_results/wf/junit.xml --cov=modules.mms --cov-report=xml:a8_results/wf/coverage.xml --cov-report=term-missing > a8_results/wf/pytest.log 2>&1
```

Ruff:

```sh
.venv/bin/ruff check tests/a8/wf
```

Both the final WF suite and Ruff completed successfully. The suite was run independently; no other A8 strategy suite was included.

## Artifacts

- `tests/a8/wf/test_wf_cases.py`
- `tests/a8/wf/test_mapping.csv`
- `a8_results/wf/pytest.log`
- `a8_results/wf/junit.xml`
- `a8_results/wf/coverage.xml`
- `a8_results/wf/implementation_defects.md`
