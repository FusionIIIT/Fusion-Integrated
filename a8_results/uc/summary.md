# UC pytest run summary

## Scope

- Frozen design: `a8_design/UC_DESIGN.json`
- Test cases: 128 unique sequential IDs (`TC-UC-001` through `TC-UC-128`)
- Use cases: 31, all represented in `tests/a8/uc/test_mapping.csv`
- The coverage matrix maps main, alternative, and exception flows. Blocked scenarios retain their frozen reasons.
- The 14 blocked cases were skipped, not counted as passed.
- No FR tests were reused. No production code, application settings, models, APIs, or ELM files were changed.

## Final isolated run

| Result | Count |
|---|---:|
| Total | 128 |
| Passed | 109 |
| Failed | 5 |
| Skipped/blocked | 14 |
| Errors | 0 |
| Execution time | 7.77 seconds |
| MMS line coverage | 78.53% (1,006 / 1,281 lines) |

Failed IDs: `TC-UC-003`, `TC-UC-046`, `TC-UC-065`, `TC-UC-066`, `TC-UC-078`.

Blocked IDs: `TC-UC-011`, `TC-UC-032`, `TC-UC-033`, `TC-UC-058`, `TC-UC-063`, `TC-UC-073`, `TC-UC-081`, `TC-UC-086`, `TC-UC-087`, `TC-UC-094`, `TC-UC-095`, `TC-UC-119`, `TC-UC-125`, `TC-UC-126`.

See `a8_results/uc/implementation_defects.md` for the observed failure details.

## Commands executed

```text
./.venv/bin/python -m pytest --collect-only tests/a8/uc/test_uc_cases.py
./.venv/bin/ruff check tests/a8/uc/test_uc_cases.py
./.venv/bin/python -m pytest tests/a8/uc/test_uc_cases.py --cov=modules.mms --cov-report=xml:a8_results/uc/coverage.xml --junitxml=a8_results/uc/junit.xml > a8_results/uc/pytest.log 2>&1
```

The pytest command was run twice. The first run exposed one test assertion that was stricter than the frozen expected result for `TC-UC-067`; that assertion was mechanically corrected to check rejection without requiring a specific HTTP status, and the isolated suite was rerun. The five remaining failures were not repaired.

## Artifacts

- Pytest cases: `tests/a8/uc/test_uc_cases.py`
- Test-to-use-case/flow mapping: `tests/a8/uc/test_mapping.csv`
- Pytest output: `a8_results/uc/pytest.log`
- JUnit XML: `a8_results/uc/junit.xml`
- Coverage XML: `a8_results/uc/coverage.xml`
- Implementation discrepancies: `a8_results/uc/implementation_defects.md`
