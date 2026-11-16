# Spec tests: iwd

Student 1 (git author name): Copilot implementation session  
Student 2 (git author name): Copilot independent verification session  
Design commit (hash and subject): recorded when the frozen design artifacts are committed  
Baseline commit (hash and subject): recorded when the implementation baseline is committed  
Student 1's 10/10 commit the baseline ran on (hash): not applicable to this local checkout

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|---------|----------|
| final | FR | 15 | 15 | 0 | 0 | 39 | 30 |
| final | UC | 19 | 19 | 0 | 0 | 44 | 33 |
| final | BR | 21 | 21 | 0 | 0 | 40 | 33 |
| final | WF | 16 | 16 | 0 | 0 | 40 | 32 |

## Failures and skips

No failures or skipped tests.

The frozen designs are stored beside this record as `FR_DESIGN.json`,
`UC_DESIGN.json`, `BR_DESIGN.json`, and `WF_DESIGN.json`. The executable
tests are stored under `modules/iwd/tests/spec/`, with each test name or
docstring containing its test ID and specification source ID.
