# PMS Specification Test Triage

## 1. Current test results

Results from `../spec-results/current-check/`.

| Strategy | Passed | Failed | Skipped |
|---|---:|---:|---:|
| FR | 207 | 3 | 0 |
| UC | 1 | 52 | 0 |
| BR | 109 | 2 | 12 |
| WF | 22 | 0 | 0 |
| **Total** | **339** | **57** | **12** |

These are current-check results, not a fully passing final run.

## 2. FR failures

| Test ID | Observed failure | Category |
|---|---|---|
| TC-111 / AFR-141 | Applicant prior-art search returns HTTP 503 instead of 200 | Endpoint/service integration mismatch |
| TC-112 / AFR-142 | Attorney prior-art search returns HTTP 503 instead of 200 | Endpoint/service integration mismatch |
| TC-153 / AFR-183 | Financial and budget report contains zero expected records | Report/data mismatch |

## 3. UC failures

There are 52 failing UC tests (TC-049 to TC-101, excluding TC-056).
The following categories are based on the observed pytest errors.
They describe test-to-implementation mismatches; they do not independently
establish whether the test or implementation is incorrect.

| Category | Observed evidence |
|---|---|
| URL namespace | Repeated `NoReverseMatch`: `pms` is not a registered namespace |
| Missing status constant | `PatentApplicationStatus.APPEAL_UNDER_REVIEW` does not exist |
| Service signature mismatch | Unsupported keyword arguments and positional arguments passed to keyword-only services |
| Notification behavior/dependency | Missing deadline alert records; `notifications.get_users` is unavailable |
| Deadline result fields | Missing `expired` and `escalated` result keys |
| Visibility/selector mismatch | Expected application absent from `visible_applications()` for Director |
| Configuration mismatch | `review_sla_days` is not a recognized configuration key |
| Validation mismatch | Expected `ValueError` was not raised |
| Missing or unexpected data | `NoneType` object has no attribute `pk`; expected query results are empty |

Detailed errors are retained in:
`../spec-results/triage-details/uc-details.txt`

## 4. BR failures

| Test ID | Observed failure | Category |
|---|---|---|
| BR-TC-064 | `decide_renewal()` attempts transition from `filed` to `renewal_approved`, raising `InvalidTransitionError` | State-transition mismatch |
| BR-TC-142 | Expected `ExternalServiceUnavailableError` was not raised; external filing succeeded and status changed from `approved` to `filed` | Expected external-service failure not reproduced |

## 5. BR tests marked NOT_AUTOMATED

| Test ID | Source ID | Reason |
|---|---|---|
| BR-TC-045 | BR-PMS-042 | No automatic attorney expertise ranking/filtering |
| BR-TC-049 | BR-PMS-045 | No rejection of non-panel preferred attorney at submission |
| BR-TC-060 | BR-PMS-055 | No external patent-office format validator |
| BR-TC-107 | BR-PMS-099 | No separate office-action deadline rule toggle |
| BR-TC-070 | BR-PMS-066 | No deadline-rule availability flag |
| BR-TC-023 | BR-PMS-022 | No toggle for unavailable director assignment rules |
| BR-TC-024 | BR-PMS-023 | No automated Director-domain matching service |
| BR-TC-025 | BR-PMS-024 | No automated Director workload-balancing service |
| BR-TC-085 | BR-PMS-076 | No policy flag disabling electronic signature collection |
| BR-TC-087 | BR-PMS-077 | No separate electronic-signature validation gate |
| BR-TC-091 | BR-PMS-084 | No dedicated previous-version retrieval endpoint/selector |
| BR-TC-092 | BR-PMS-086 | No standalone document-download/view endpoint/selector |

All 12 are explicitly marked `NOT_AUTOMATED` in the tests.

## 6. WF results

All 22 workflow specification tests passed. No failures or skips were reported.

## 7. Coverage and limitations

- UC currently contains only continuation tests UC-TC-049 to UC-TC-101.
- UC-TC-001 to UC-TC-048 are not present in the current test folder.
- Failure categories above are based on observed test output and should not be
  interpreted as confirmed production defects without specification review.
- The current run is not a fully passing final run.
