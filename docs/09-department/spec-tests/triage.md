# Spec tests: department

Student 1 (git author name): Krishna (Krishnacoder24)
Student 2 (git author name): Ankush Kumar (Ankush3313)
Design commit (hash and subject): `e170999` Add frozen test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): `9392063` Add baseline spec test suites
Student 1's 10/10 commit the baseline ran on (hash): `64edc89` Round 1 implementation of department module

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | BR | 42 | 17 | 5 | 20 | 43% | 24% |
| baseline | FR | 48 | 26 | 7 | 15 | 45% | 26% |
| baseline | UC | 35 | 16 | 6 | 13 | 41% | 22% |
| baseline | WF | 19 | 10 | 2 | 7 | 38% | 20% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TEST-BR-004 | BR-DEPT-002-MISMATCH | BR | Confirmed implementation defect | `announcement_selectors.active_announcements()` does not filter out announcements targeted to other departments/roles/years (`assert 'Targeted ECE 2024' not in ['Targeted ECE 2024']`) | Student 1 to fix in announcement selectors | Open |
| TEST-BR-005 | BR-DEPT-004-HOD-EDIT | BR | Confirmed implementation defect | `announcement_service` missing `edit` or `update_announcement` method for HOD edit authority (`assert hasattr(announcement_service, 'edit')`) | Student 1 to add `edit()` service function | Open |
| TEST-BR-015 | BR-DEPT-007-UNAPPROVED-PROHIBITED | BR | Confirmed implementation defect | Setting status directly to `ISSUED` on unapproved request does not raise `ValidationError` | Student 1 to implement status transition validation on `StockRequest` | Open |
| TEST-BR-028 | BR-DEPT-015-EXCEEDS-PROHIBITED | BR | Confirmed implementation defect | Requesting quantity greater than current available inventory does not raise `ValidationError` | Student 1 to add quantity boundary validation in `StockRequest.clean()` | Open |
| TEST-BR-030 | BR-DEPT-016-DECREMENT | BR | Confirmed implementation defect | Issuance of stock does not automatically decrement `item.quantity` (`assert 30 == 20`) | Student 1 to add inventory quantity decrement upon stock issuance | Open |
| TEST-BR-019..027 | BR-DEPT-008..014 | BR | NOT_AUTOMATED: External service | Physical hardware calibration integration tests cannot be automated in unit harness | Automated via Playwright E2E hardware mock flow | Closed |
