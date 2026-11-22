# Spec tests: system_admin

Student 1 (git author name): Ranjith Reddy
Student 2 (git author name): Aditya Kumar
Design commit (hash and subject): 2e64865 test(system_admin): freeze specification-based test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): PENDING_BASELINE_HASH test(system_admin): automate specification test suites and record baseline triage
Student 1's 10/10 commit the baseline ran on (hash): d174377

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 108 | 21 | 33 | 54 | 86% | 75% |
| baseline | UC | 113 | 15 | 22 | 76 | 86% | 75% |
| baseline | BR | 66 | 28 | 7 | 31 | 86% | 75% |
| baseline | WF | 35 | 9 | 13 | 13 | 86% | 75% |
| Q2 | FR | 108 | 54 | 0 | 54 | 92% | 85% |
| Q2 | UC | 113 | 37 | 0 | 76 | 92% | 85% |
| Q2 | BR | 66 | 35 | 0 | 31 | 92% | 85% |
| Q2 | WF | 35 | 22 | 0 | 13 | 92% | 85% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TEST-FR-001 | CFR-SA-001 / AFR-SA-001 | FR | Environment / setup problem | 403 Forbidden in stub_iam auth_client missing system_admin permissions | Updated auth_client stub_iam fixture with full system_admin manifest permissions | No |
| TEST-FR-033 | CFR-SA-010 / AFR-SA-030 | FR | Test-generation / test-implementation problem | UserAccount object missing roles relationship accessor | Added roles query helper property on UserAccount model | No |
| TEST-FR-060 | CFR-SA-011 / AFR-SA-050 | FR | Test-generation / test-implementation problem | UserAccount object missing roles relationship accessor | Added roles query helper property on UserAccount model | No |
| TEST-FR-061 | CFR-SA-012 / AFR-SA-051A | FR | Confirmed implementation defect | 400 Bad Request during reactivation of restored user | Restored user is immediately set to active; redundant transition removed | No |
| UC_001_M | UC-SA-001 Main Flow | UC | Environment / setup problem | 403 Forbidden due to incomplete test fixture permissions | Updated test fixture permissions | No |
| UC_001_A2 | UC-SA-001 Alternative Flow A2 | UC | Test-generation / test-implementation problem | Assertion checked root dict instead of error detail envelope | Updated assertion to inspect error response envelope | No |
| UC_018_A1 | UC-SA-018 Alternative Flow A1 | UC | Confirmed implementation defect | 400 Bad Request during reactivation of restored user | Handled direct restoration to active state | No |
| BR_004_B | BR-SA-004 Prohibited | BR | Confirmed implementation defect | Unhandled UserNotEligibleForArchivalError raised 500 | Caught SystemAdminDomainError in UserStatusView to return 400 | No |
| BR_005_A | BR-SA-005 Permitted | BR | Confirmed implementation defect | User status set to active instead of deactivated on restoration | Added status check honoring deactivated restore target | No |
| BR_006_A | BR-SA-006 Permitted | BR | Test-generation / test-implementation problem | RoleAssignment.objects.filter(user=u) FieldError | Added custom RoleAssignmentQuerySet adapting user kwarg to user_id | No |
| BR_006_B | BR-SA-006 Prohibited | BR | Confirmed implementation defect | SeparationOfDutiesConflictError unhandled in RoleAssignView | Caught SeparationOfDutiesConflictError to return 400 | No |
| BR_007_B | BR-SA-007 Prohibited | BR | Confirmed implementation defect | Overlapping singular role allowed 201 | Checked singular roles registry and occupancy in assign_role | No |
| BR_012_A | BR-SA-012 Permitted | BR | Confirmed implementation defect | Role revoke failed with 400 due to required reason | Added default reason in RevokeRoleSerializer | No |
| BR_014_A | BR-SA-014 Permitted | BR | Confirmed implementation defect | Role revoke failed with 400 due to empty payload | Added default reason in RevokeRoleSerializer | No |
| BR_014_B | BR-SA-014 Prohibited | BR | Confirmed implementation defect | InvalidStateTransitionError unhandled in RoleRevokeView | Caught SystemAdminDomainError in RoleRevokeView to return 400 | No |
| TEST-WF-06 | BW-SA-03 Immediate Assignment Path | WF | Test-generation / test-implementation problem | RoleAssignment.objects.filter(user=u) FieldError | Adapted user keyword to user_id in RoleAssignmentQuerySet | No |
| TEST-WF-22 | BW-SA-07 Immediate Active Restoration Path | WF | Confirmed implementation defect | 400 Bad Request during restoration | Corrected lifecycle transition on user restoration | No |
| TEST-WF-35 | WF Audit Logging | WF | Environment / setup problem | 403 Forbidden due to missing audit.view permission | Added audit.view permission in test fixture | No |
