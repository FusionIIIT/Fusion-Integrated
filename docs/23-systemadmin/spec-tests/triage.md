# System Administration (`systemadmin`) Specification Test Triage Log

This triage document tracks the initial evaluation and resolution of specification test failures discovered during the Round Q1 test run of the `systemadmin` module.

---

## 1. Evaluation Context

- **Target Module**: `23-systemadmin` (`modules/systemadmin/`)
- **Student 1 Implementation Commit**: `00cd2fe` (`feat(systemadmin): implement system administration module and initial quality report`)
- **Student 2 Frozen Test Designs Commit**: `53481d0` (`test(systemadmin): freeze spec test designs for FR, UC, BR, and WF`)
- **Test Evaluation Date**: 2026-11-12
- **Evaluator**: Katika Rohith (Roll No: `24BCS117`, GitHub: `katikarohith`)

---

## 2. Initial Test Execution Summary (Round Q1)

Command executed:
```bash
.venv/bin/pytest modules/systemadmin/tests/spec/ -q
```

Result:
```text
8 failed, 315 passed, 10 warnings in 10.63s
Total Tests: 323
Pass Rate: 97.52%
```

Breakdown by category:
- **Functional Requirements (`FR`)**: 112 passed, 2 failed (Total: 114)
- **Use Cases (`UC`)**: 114 passed, 3 failed (Total: 117)
- **Business Rules (`BR`)**: 66 passed, 2 failed (Total: 68)
- **Workflows (`WF`)**: 23 passed, 1 failed (Total: 24)

---

## 3. Defects Identified and Triage Table

| Defect ID | Spec ID | Test Name | Failure Summary | Root Cause Diagnosis | Fix Owner | Open? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | `UC-SA-001` | `test_uc_001_create_basic_user_main_flow` | `AssertionError: Audit log entry with action 'USER_CREATED' not found` | Audit service logged action as `USER_CREATE` instead of spec requirement `USER_CREATED`. | Student 1 | Yes |
| **DEF-002** | `BR-SA-045`, `FR-SA-085`, `UC-SA-079`, `UC-SA-081`, `WF-SA-001` | `test_br_045_permanent_purge_authorization_execution_permitted`<br>`test_fr_085_dual_authorized_permanent_purge_executes`<br>`test_uc_079_authorize_permanent_purge_main_flow`<br>`test_uc_081_authorize_permanent_purge_exc_e1_already_decided`<br>`test_wf_001_purge_approved_basis_path` | `AssertionError: ArchivedHistoricalData record still exists` | `authorize_permanent_purge` sets status to "purged" (soft delete) instead of executing permanent database deletion. | Student 1 | Yes |
| **DEF-003** | `BR-SA-003` | `test_br_003_institute_id_immutability_prohibited` | `AssertionError: 400 Bad Request expected on institute_id mutation` | `UserDetailView` PATCH and PUT endpoints allowed modification of immutable `institute_id` without raising ValidationError / BadRequestError. | Student 1 | Yes |
| **DEF-004** | `FR-SA-071` | `test_fr_071_historical_archival_validates_dependencies` | `Failed: DID NOT RAISE <class 'modules.systemadmin.exceptions.ArchivalError'>` | `ArchivalService.archive_historical_data` did not validate that category must be non-empty and non-whitespace. | Student 1 | Yes |
| **DEF-005** | `BR-SA-018` | `test_br_018_future_role_revocation_effective_date_handling` | Potential deferred status handling inconsistency | Future-dated role revocation was applying status="revoked" immediately instead of keeping active until effective date when not emergency. | Student 1 | Yes |

---

## 4. Remediation Plan

- **Student 1 Action Items**:
  1. Update `UserService.create_basic_user` audit logging action string to `USER_CREATED`.
  2. Implement actual database record deletion in `ArchivalService.authorize_permanent_purge` upon approval.
  3. Enforce `institute_id` immutability in `UserUpdateSerializer` and `UserDetailView` with validation error.
  4. Add category validation check in `ArchivalService.archive_historical_data`.
  5. Correct future-dated role revocation effective date status handling in `RoleService.revoke_role_assignment`.
- **Student 2 Action Items**:
  1. Re-run complete spec test suite once fixes are committed in Commit 4.
  2. Record final verification results (Round Q2) in Commit 5.

---

## 5. Sign-off

- **Evaluator**: Katika Rohith (Student 2 - Reviewer/Tester)
- **Roll Number**: 24BCS117
- **Date**: 2026-11-12
- **Initial Triage Status**: 5 Defects Logged (Remediation Pending Student 1)
