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
| Q2       | BR | 42 | 22 | 0 | 20 | 78% | 65% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TEST-BR-004 | BR-DEPT-002-MISMATCH | BR | Confirmed implementation defect | `announcement_selectors` returned all announcements without filtering | Fixed in commit `ac8106d`: added `relevant_announcements()` audience filtering | Closed |
| TEST-BR-005 | BR-DEPT-004-HOD-EDIT | BR | Confirmed implementation defect | Missing `edit()` in `announcement_service` | Fixed in commit `ac8106d`: added `edit()` service function with HOD role check | Closed |
| TEST-BR-015 | BR-DEPT-007-UNAPPROVED-PROHIBITED | BR | Confirmed implementation defect | Direct status change to `ISSUED` did not raise ValidationError | Fixed in commit `ac8106d`: added status transition validation in `StockRequest.clean()` | Closed |
| TEST-BR-028 | BR-DEPT-015-EXCEEDS-PROHIBITED | BR | Confirmed implementation defect | Exceeding available quantity did not raise ValidationError | Fixed in commit `ac8106d`: added inventory quantity boundary check in `StockRequest.clean()` | Closed |
| TEST-BR-030 | BR-DEPT-016-DECREMENT | BR | Confirmed implementation defect | Issuance of stock did not decrement inventory quantity | Fixed in commit `ac8106d`: added automatic decrement of `item.quantity` in `StockRequest.save()` | Closed |
| TEST-BR-019..027 | BR-DEPT-008..014 | BR | NOT_AUTOMATED: External service | Hardware calibration integration tests | Covered via Playwright E2E test flows | Closed |
