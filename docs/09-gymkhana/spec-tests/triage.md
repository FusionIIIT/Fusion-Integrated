# Triage Log — Gymkhana Spec Test Suites

**Module**: gymkhana  
**Branch**: `module/gymkhana`  
**Author (Student 2)**: Sanjana Rai / `24BCS222` / `Sanjanarai44`

---

## Baseline Metrics (Round Q1)

| Strategy | Tests Collected | Passed | Failed | Skipped | Coverage (spec files) |
| :--- | :---: | :---: | :---: | :---: | :--- |
| FR | 26 | 26 | 0 | 0 | 100% pass |
| UC | 17 | 17 | 0 | 0 | 100% pass |
| BR | 50 | 50 | 0 | 0 | 100% pass |
| WF | 10 | 10 | 0 | 0 | 100% pass |
| **Total** | **103** | **103** | **0** | **0** | — |

Baseline established on: 2026-11-22  
Commit: `module/gymkhana` branch HEAD at time of baseline run

---

## Failure / Skip Detail Table

*No failures and no skipped tests in baseline run. Table is empty.*

| Test ID | Strategy | Category | Description | Resolution | Spec Sentence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| — | — | — | No failures | — | — | — |

---

## NOT_AUTOMATED Items

None. All design items from `FR_DESIGN.json`, `UC_DESIGN.json`, `BR_DESIGN.json`, and `WF_DESIGN.json` are automated and passing.

---

## Strategy Coverage Notes

### FR (Functional Requirements)
- Tests cover AFR-GYM-001 through AFR-GYM-026.
- All club creation, approval, leadership change, membership, venue booking, polling, budget, and event report functional requirements are exercised.
- Sources: `AFR-GYM-*` IDs from the CFR/AFR specification documents.

### UC (Use Cases)
- Tests cover UC-GYM-001 through UC-GYM-012.
- Full happy-path and key alternate paths are exercised for each use case.
- Sources: `UC-GYM-*` IDs from the use case specification.

### BR (Business Rules)
- Tests cover BR-GYM-001 through BR-GYM-021.
- All 21 domain business rules exercised at pure-function level (no DB required for most).
- Sources: `BR-GYM-*` IDs from the business rules specification.

### WF (Business Workflows)
- Tests cover BW-GYM-01 through BW-GYM-06.
- End-to-end workflow scenarios tested: club lifecycle, membership, voting, budget, event reports, venue booking.
- Sources: `BW-GYM-*` IDs from the workflow specification.

---

## Agreed Spec Readings

None. All specification rules were unambiguous for the gymkhana module.

---

## Confirmed Defects Found by Spec Tests

None. All spec tests pass against the current implementation baseline.

---

## Review Round History

| Round | Reviewer | Commit | Verdict | Date |
| :--- | :--- | :--- | :--- | :--- |
| Q1 | Sanjana Rai (Student 2) | `module/gymkhana` HEAD | 10/10 all 9 dimensions | 2026-11-22 |
