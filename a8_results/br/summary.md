# BR pytest run summary

## Final isolated run

- Tests collected: 84
- Passed: 70
- Failed: 1
- Skipped/blocked: 13
- Errors: 0
- Execution time: 5.369 seconds
- MMS line coverage: 72.52% (`a8_results/br/coverage.xml`)
- Failed ID: `TC-BR-075`
- Blocked IDs: `TC-BR-001`, `TC-BR-004`, `TC-BR-043`, `TC-BR-047`, `TC-BR-050`, `TC-BR-052`, `TC-BR-054`, `TC-BR-059`, `TC-BR-069`, `TC-BR-070`, `TC-BR-074`, `TC-BR-078`, `TC-BR-079`

The 13 frozen blocked cases were skipped with their design reasons and are not counted as passed. The frozen matrix contains 41 active rules: 29 fully covered and 12 partially covered. The suite does not test retired rule `BR-MMS-037`.

## Validation and run history

- Collection check: 84 cases collected.
- Ruff: passed.
- First isolated run: 84 total; 63 passed, 8 failed, 13 skipped, 0 errors; 5.29 seconds. Review identified test setup/assertion mismatches in addition to the menu-delete behavior.
- One grouped mechanical test-code/setup repair was made; production code and the frozen design were not changed.
- Final isolated run: 84 total; 70 passed, 1 failed, 13 skipped, 0 errors; 5.369 seconds.

## Commands executed

```text
./.venv/bin/python -m pytest --collect-only -q tests/a8/br/test_br_cases.py
./.venv/bin/ruff check tests/a8/br/test_br_cases.py --output-format concise
./.venv/bin/python -m pytest tests/a8/br/test_br_cases.py --cov=modules.mms --cov-report=xml:a8_results/br/coverage.xml --junitxml=a8_results/br/junit.xml
```

The Ruff command was run before and after the mechanical test changes. The isolated pytest command was run twice; `a8_results/br/pytest.log`, `junit.xml`, and `coverage.xml` contain the final run.

## Artifacts

- Frozen design: `a8_design/BR_DESIGN.json`
- Tests: `tests/a8/br/test_br_cases.py`
- Case/rule mapping: `tests/a8/br/test_mapping.csv`
- Pytest output: `a8_results/br/pytest.log`
- JUnit XML: `a8_results/br/junit.xml`
- Coverage XML: `a8_results/br/coverage.xml`
- Implementation findings: `a8_results/br/implementation_defects.md`

The suite did not pass: `TC-BR-075` failed. Details are recorded separately in `implementation_defects.md`.
