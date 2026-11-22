# Spec tests: hr_eis

Student 1 (git author name): Student 1
Student 2 (git author name): Student 2
Design commit (hash and subject): 3a18b9c feat(hr_eis): freeze specification test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): b84f210 test(hr_eis): initial baseline specification test suites
Student 1's 10/10 commit the baseline ran on (hash): 7e41c09

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| Baseline | FR | 14 | 12 | 2 | 0 | 88.5% | 80.0% |
| Baseline | UC | 11 | 9 | 2 | 0 | 85.0% | 76.5% |
| Baseline | BR | 12 | 10 | 2 | 0 | 87.2% | 78.0% |
| Baseline | WF | 10 | 8 | 2 | 0 | 84.1% | 75.0% |
| Final (Q2) | FR | 14 | 14 | 0 | 0 | 97.4% | 92.5% |
| Final (Q2) | UC | 11 | 11 | 0 | 0 | 96.8% | 91.0% |
| Final (Q2) | BR | 12 | 12 | 0 | 0 | 98.1% | 94.0% |
| Final (Q2) | WF | 10 | 10 | 0 | 0 | 96.5% | 90.0% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| FR-TC-07 | CFR-04 | FR, UC, WF | Confirmed implementation defect | 500 error when employee without initialized profile posts experience | Fixed in `views.py` `perform_create()` to validate profile existence and raise HTTP 400 | No |
| BR-TC-03 | BR-02 | BR | Confirmed implementation defect | Model allowed `end_date < start_date` on direct ORM save | Fixed in `models.py` `clean()` to enforce chronological integrity | No |
| FR-TC-08 | CFR-04 | FR, UC, BR | Confirmed implementation defect | Staff user could not view experiences belonging to other employees | Fixed in `views.py` `get_queryset()` to permit staff inspection | No |
| WF-TC-05 | WF-02 | WF | Confirmed implementation defect | Unhandled exception on invalid experience dates in workflow | Fixed via DRF standard validation error envelopes | No |
