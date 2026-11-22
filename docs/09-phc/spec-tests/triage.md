# Spec tests: phc

Student 1 (git author name): Manoj Kumar  
Student 2 (git author name): 24BCS012  
Design commit (hash and subject): b105ac2 Freeze PHC specification test designs for FR, UC, BR, and WF  
Baseline commit (hash and subject): b73c841 Add executable spec test suites and baseline triage log  
Student 1's 10/10 commit the baseline ran on (hash): 3104a9b  

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 45 | 43 | 2 | 0 | 71.56% | 44.23% |
| baseline | UC | 33 | 31 | 2 | 0 | 67.22% | 41.35% |
| baseline | BR | 24 | 22 | 2 | 0 | 68.72% | 37.50% |
| baseline | WF | 18 | 17 | 1 | 0 | 37.20% | 24.04% |
| Q2 (final) | FR | 45 | 45 | 0 | 0 | 72.84% | 45.10% |
| Q2 (final) | UC | 33 | 33 | 0 | 0 | 68.41% | 42.02% |
| Q2 (final) | BR | 24 | 24 | 0 | 0 | 70.15% | 38.24% |
| Q2 (final) | WF | 18 | 18 | 0 | 0 | 38.52% | 25.00% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| FR-TEST-003, UC-TEST-012 | AFR-PHC-003, PHC-UC-08 | FR, UC | Confirmed implementation defect | Attendance status validation missing; invalid status does not raise ValueError | Fixed in commit 965dde8: `mark_attendance` enforces validation against `DoctorAttendance.STATUS_CHOICES` raising `ValueError`. Verified passing in Q2. | No |
| FR-TEST-012, UC-TEST-004 | AFR-PHC-011, PHC-UC-03 | FR, UC | Confirmed implementation defect | Patient medical records download returns JSON instead of application/pdf | Fixed in commit 965dde8: `PatientRecordDownloadView` returns binary PDF stream with %PDF header and `Content-Type: application/pdf`. Verified passing in Q2. | No |
| BR-TEST-013 | PHC-BR-07 | BR | Confirmed implementation defect | Reorder threshold alert triggers strictly below (<) rather than at or below (<=) threshold | Fixed in commit 965dde8: `StockThresholdEvaluation.is_low_stock` evaluates `<= reorder_threshold`. Verified passing in Q2. | No |
| BR-TEST-024, WF-TEST-010 | PHC-BR-14, CW-PHC-01 | BR, WF | Confirmed implementation defect | Claim in terminal state (Rejected/Reimbursed) does not raise ClaimImmutableError on save | Fixed in commit 965dde8: `ReimbursementClaim.clean()` and `save()` enforce immutability on terminal claims raising `ClaimImmutableError`. Verified passing in Q2. | No |

## Student 2 Review (Round Q2)

- Spec fidelity: 10/10
- Architecture & isolation: 10/10
- Code quality & design: 10/10
- Security & access control: 10/10
- Testing & coverage: 10/10
- E2E & live behaviour: 10/10
- Frontend: 10/10
- Operability & docs: 10/10
- Hygiene: 10/10

**VERDICT: 10/10 in all nine dimensions**
