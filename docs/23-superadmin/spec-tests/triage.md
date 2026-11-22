# Spec tests: superadmin

Student 1 (git author name): Nikhil Jain
Student 2 (git author name): Paladugu Taraka Ram
Design commit (hash and subject): e8f1a23 Student 2: Freeze spec test design for FR, UC, BR, and WF
Baseline commit (hash and subject): b4c7d89 Student 2: Initial spec test baseline and triage log
Student 1's 10/10 commit the baseline ran on (hash): a1b2c3d

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 32 | 31 | 1 | 0 | 43% | 19% |
| baseline | UC | 27 | 26 | 1 | 0 | 41% | 21% |
| baseline | BR | 27 | 26 | 1 | 0 | 34% | 13% |
| baseline | WF | 10 | 9 | 1 | 0 | 32% | 20% |
| **baseline total** | **ALL** | **96** | **92** | **4** | **0** | **44%** | **20%** |
| final | FR | 32 | 32 | 0 | 0 | 43% | 19% |
| final | UC | 27 | 27 | 0 | 0 | 41% | 21% |
| final | BR | 27 | 27 | 0 | 0 | 34% | 13% |
| final | WF | 10 | 10 | 0 | 0 | 32% | 20% |
| **final total** | **ALL** | **96** | **96** | **0** | **0** | **45%** | **22%** |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| FR-TEST-025, UC-TEST-019, BR-TEST-007, WF-TEST-008 | CFR-SA-012-E1, UC-SA-018 Alternative A1, BR-SA-005 condition-false, BW-SA-08 window-expiry | FR, UC, BR, WF | Confirmed implementation defect (DEF-SA-01) | When restoration is attempted on an account whose reversibility window has expired, the service raised ConflictError but rolled back the transaction, leaving the account in ARCHIVED_REVERSIBLE instead of committing ARCHIVED_PERMANENT. | Fixed in services/user_archive.py by committing status update to ARCHIVED_PERMANENT prior to raising ConflictError. Covered by FR-TEST-025, UC-TEST-019, BR-TEST-007, WF-TEST-008. | No |
