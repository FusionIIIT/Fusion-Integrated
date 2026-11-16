# Spec tests: iwd

Student 1 (git author name): Dinesh (implementation role)  
Student 2 (git author name): Dinesh (verification role)  
Design commit (hash and subject): `32f8d22 Freeze IWD specification test designs`  
Baseline commit (hash and subject): `81f672b Complete IWD module and specification verification`  
Student 1's 10/10 commit the baseline ran on (hash): `81f672b`

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|---------|----------|
| final | FR | 15 | 15 | 0 | 0 | 38.5 | 30.0 |
| final | UC | 19 | 19 | 0 | 0 | 43.63 | 33.33 |
| final | BR | 21 | 21 | 0 | 0 | 40.49 | 32.78 |
| final | WF | 16 | 16 | 0 | 0 | 39.64 | 32.22 |

## Failures and skips

No failures or skipped tests.

The frozen designs are stored beside this record as `FR_DESIGN.json`,
`UC_DESIGN.json`, `BR_DESIGN.json`, and `WF_DESIGN.json`. The executable
tests are stored under `modules/iwd/tests/spec/`, with each test name or
docstring containing its test ID and specification source ID.

The complete backend suite also passed at the baseline: 463 passed.
Django checks and migration checks passed. Frontend typecheck and production
build passed.
