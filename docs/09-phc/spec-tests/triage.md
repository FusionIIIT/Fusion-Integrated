# Spec tests: phc

Student 1 (git author name): Manoj Kumar  
Student 2 (git author name): 24BCS012  
Design commit (hash and subject): b105ac2 Freeze PHC specification test designs for FR, UC, BR, and WF  
Baseline commit (hash and subject): pending commit Add executable spec test suites and baseline triage log  
Student 1's 10/10 commit the baseline ran on (hash): 3104a9b  

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 45 | 43 | 2 | 0 | 71.56% | 44.23% |
| baseline | UC | 33 | 31 | 2 | 0 | 67.22% | 41.35% |
| baseline | BR | 24 | 22 | 2 | 0 | 68.72% | 37.50% |
| baseline | WF | 18 | 17 | 1 | 0 | 37.20% | 24.04% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| FR-TEST-003, UC-TEST-012 | AFR-PHC-003, PHC-UC-08 | FR, UC | Confirmed implementation defect | Attendance status validation missing; invalid status does not raise ValueError | Student 1 to validate status against DoctorAttendance.STATUS_CHOICES | Yes |
| FR-TEST-012, UC-TEST-004 | AFR-PHC-011, PHC-UC-03 | FR, UC | Confirmed implementation defect | Patient medical records download returns JSON instead of application/pdf | Student 1 to return binary PDF stream with %PDF magic header | Yes |
| BR-TEST-013 | PHC-BR-07 | BR | Confirmed implementation defect | Reorder threshold alert triggers strictly below (<) rather than at or below (<=) threshold | Student 1 to update threshold comparison logic in domain entity | Yes |
| BR-TEST-024, WF-TEST-010 | PHC-BR-14, CW-PHC-01 | BR, WF | Confirmed implementation defect | Claim in terminal state (Rejected/Reimbursed) does not raise ClaimImmutableError on save | Student 1 to enforce clean/save immutability check on terminal claims | Yes |
