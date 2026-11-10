# FR pytest run

The test module contains one pytest case for each frozen identifier
`TC-FR-001` through `TC-FR-117`. The suite was run independently against the
existing MMS implementation.

## Final run

| Metric | Result |
|---|---:|
| Total | 117 |
| Passed | 92 |
| Failed | 11 |
| Skipped / blocked | 14 |
| Errors | 0 |
| Execution time | 6.118 seconds |
| MMS line coverage | 74.79% (958 / 1,281 lines) |

The final pytest exit code was non-zero because 11 executable requirements
failed. These are recorded separately in [implementation_defects.md](./implementation_defects.md)
and were not fixed.

## Command

```sh
set -o pipefail && ./.venv/bin/python -m pytest tests/a8/fr/test_fr_cases.py --cov=modules.mms --cov-report=xml:a8_results/fr/coverage.xml --junitxml=a8_results/fr/junit.xml -q --no-header 2>&1 | tee a8_results/fr/pytest.log
```

The isolated pytest command was run three times while making no more than two
test/setup repair passes. The counts above and the artifacts below are from the
final run.

## Artifacts

- Pytest output: [pytest.log](./pytest.log)
- JUnit XML: [junit.xml](./junit.xml)
- Coverage XML: [coverage.xml](./coverage.xml)
- Test-to-requirement map: [test_mapping.csv](../../tests/a8/fr/test_mapping.csv)
- Implementation findings: [implementation_defects.md](./implementation_defects.md)

## Blocked / unresolved frozen cases

These were skipped, not treated as passing:

- `TC-FR-045` — the current implementation has no fixed monthly charge input or bill field.
- `TC-FR-048` — no previous-balance input or balance roll-forward rule is defined.
- `TC-FR-090`, `TC-FR-093` — approval requires a policy-provided special-food charge, but the frozen cases provide no amount or policy value.
- `TC-FR-092` — the institution-defined special-food decision period is unspecified.
- `TC-FR-097`–`TC-FR-102` — the frozen cases do not identify the fulfillment actor; implementation comments identify this as unresolved policy.
- `TC-FR-111` — no Warden feedback/trend report contract is exposed.
- `TC-FR-113` — no rebate-consumption report contract is exposed.
- `TC-FR-114` — the API exposes feedback entries but no summary contract is specified.
