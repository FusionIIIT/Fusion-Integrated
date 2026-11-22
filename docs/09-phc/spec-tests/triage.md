# Spec tests: phc

Student 1 (git author name): Atharva — roll 24BCS043
Student 2 (git author name): Vikrant Kumar — roll 24BCS160

Design commit (`phc-21`): frozen four design JSON files under `docs/09-phc/spec-tests/`
Baseline commit: `phc-21` module implementation
Student 1's 10/10 commit the baseline ran on: `phc-21` (module complete, all gates green)

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 56 | 56 | 0 | 0 | 93.26 | 74.14 |
| baseline | UC | 48 | 48 | 0 | 0 | 91.94 | 74.14 |
| baseline | BR | 40 | 40 | 0 | 0 | 85.19 | 63.79 |
| baseline | WF | 12 | 12 | 0 | 0 | 76.25 | 44.83 |
| final | FR | 74 | 74 | 0 | 0 | 94.77 | 71.43 |
| final | UC | 48 | 48 | 0 | 0 | 91.53 | 64.55 |
| final | BR | 47 | 47 | 0 | 0 | 88.56 | 52.73 |
| final | WF | 18 | 18 | 0 | 0 | 81.50 | 40.00 |

The "final" runs are recorded in `/home/atharva/Documents/Fusion/spec-results/final/{fr,uc,br,wf}/`
(`junit.xml`, `coverage.xml`, `pytest.log`), generated from the final tree with
`pytest --cov=modules/phc --cov-branch`. Each folder's run includes that strategy's frozen
design cases plus its A9 adversarial module.

Cases grew from 156 to 187 because 31 adversarial tests were added after review: FR +18
(`fr/test_adversarial.py`), BR +7 (`br/test_adversarial.py`), WF +6 (`wf/test_adversarial.py`).
They cover anonymous/authorization gates, error envelopes (400/401/403/404/409/422/429),
query-budget and throttle behaviour, oversized integers and text, negative thresholds,
cumulative int4 overflow, duplicate doctor/day schedules, IAM originator projection,
notification side effects, cross-patient scoping, role switches and immutable/wrong-stage
transitions. Coverage
percentages are measured over
the full `modules/phc` package (including the new `domain/`, `services/` and `selectors/`
layers), so they are not directly comparable to the baseline, which measured fewer files.

## Failures and skips

None. Every spec test passed on the baseline and on the final run. No test was skipped.
The final JUnit reports record `errors="0" failures="0" skipped="0"` for all four strategies.

## Triage notes

- All four strategies were designed from the frozen specification documents before the implementation was shown to the test author.
- The four frozen designs are preserved unchanged in this folder as `FR_DESIGN.json`, `UC_DESIGN.json`, `BR_DESIGN.json` and `WF_DESIGN.json`.
- No production code was changed in response to a spec test failure, because no spec test failed.
- No test expectation was changed to match the implementation. The adversarial modules were added to close an independent reviewer's coverage finding, and one genuine defect they exposed (transition/requisition views passing `expected_updated_at` as `note`) was fixed in `modules/phc/api/views.py`.
