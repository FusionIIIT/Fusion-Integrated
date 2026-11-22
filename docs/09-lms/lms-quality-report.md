# LMS (Course Management) Quality Report

**Module Code**: `lms`  
**Base Path**: `/lms`  
**Environment**: `module-only`  
**Date**: 22 November 2026

---

## 1. Automated Gate Checks

### 1.1 Backend Verification (`make check`)
- `python manage.py check`: Passed cleanly with zero warnings or errors.
- `python manage.py makemigrations --check --dry-run`: No uncommitted or missing migrations.
- `ruff check modules/lms`: Zero linting or formatting defects.
- `lint-imports`: 5 contracts evaluated, 5 kept, 0 broken. Pure domain boundary strictly held.
- `ops/checks/no_cross_module_fk.py`: Passed (all external actor references use integer IDs).
- `ops/checks/contracts_are_plural.py`: Passed (all contract methods accept and return plural mappings).
- `ops/checks/nav_matches_routes.py`: Passed (navigation declarations align with client route table).
- `python manage.py permission_manifest --check`: Permissions catalog and registry agree.

### 1.2 Frontend Verification (`make check-client`)
- `npm run typecheck` (`tsc --noEmit`): Passed with zero type errors.
- `npm test` (`vitest run`): 35/35 platform tests passed.
- `npm run build` (`vite build`): Built successfully. Module bundle chunk size: 16.02 kB gzip (well below 150 kB threshold).

---

## 2. Test Coverage & Execution Metrics

### 2.1 Module Coverage (Excluding Spec Tests)
- **Command**: `pytest modules/lms --ignore=modules/lms/tests/spec --cov=modules/lms --cov-branch --cov-report=term-missing`
- **Result**: 113 passed.
- **Statement & Branch Coverage**: 90.07% total module coverage (meets >= 90% gate).

### 2.2 Pure Domain Coverage
- **Command**: `pytest modules/lms/tests/test_domain.py --cov=modules/lms/domain --cov-branch --cov-report=term-missing`
- **Result**: 44 passed.
- **Statement & Branch Coverage**: 96.89% domain coverage (meets >= 95% gate).

### 2.3 Specification Test Coverage (Student 2 Spec Suites)
- **FR Suite** (`modules/lms/tests/spec/fr/test_fr.py`): 47/47 passed (100%).
- **UC Suite** (`modules/lms/tests/spec/uc/test_uc.py`): 41/41 passed (100%).
- **BR Suite** (`modules/lms/tests/spec/br/test_br.py`): 36/36 passed (100%).
- **WF Suite** (`modules/lms/tests/spec/wf/test_wf.py`): 21/21 passed (100%).
- **Total Tests Across Entire Module**: 258 passed, 0 failed, 0 skipped.

---

## 3. Test Counts & Journey Mapping

| Test File | Test Count | Scope |
|---|---|---|
| `modules/lms/tests/test_domain.py` | 44 | Entity invariants, validation functions, and lifecycle states |
| `modules/lms/tests/test_services.py` | 38 | Transactional service writes and business logic |
| `modules/lms/tests/test_api.py` | 31 | DRF endpoints, authorization gates, and error serialization |
| `modules/lms/tests/spec/fr/test_fr.py` | 47 | Functional requirement obligations (CFR-01 to CFR-15, AFR-01 to AFR-47) |
| `modules/lms/tests/spec/uc/test_uc.py` | 41 | Use case success and alternative paths (UC-LMS-001 to UC-LMS-015) |
| `modules/lms/tests/spec/br/test_br.py` | 36 | Business rule constraints and policy edges (BR-LMS-001 to BR-LMS-019) |
| `modules/lms/tests/spec/wf/test_wf.py` | 21 | State machine transitions and composite workflows |

---

## 4. Broken-On-Purpose Verification (Mutation Testing)

1. **Course Access Isolation (`BR-LMS-001`)**: Removed course membership check in `get_course_detail`. Caught by `test_tc_br_02_course_unrelated_prohibited` with HTTP 404 / access denied.
2. **Draft Material Concealment (`BR-LMS-005`)**: Removed draft filter from student material selector. Caught by `test_tc_br_09_draft_material_hidden_from_student`.
3. **Closing Cutoff Enforcement (`BR-LMS-013`)**: Bypassed deadline validation in `create_submission`. Caught by `test_tc_br_26_submission_past_due_date` raising ConflictError.
4. **Draft Grade Isolation (`BR-LMS-016`)**: Removed draft status guard from student grade selector. Caught by `test_tc_br_31_draft_grade_hidden_from_student`.
5. **Grade Release Authority (`BR-LMS-017`)**: Removed faculty check in `release_assignment_grades`. Caught by `test_tc_br_34_ta_cannot_release_grades` with PermissionDeniedError.

---

## 5. Adversarial Audit & Security Checklist

- **Access Control & RBAC**: Every endpoint enforces `IamSessionAuthentication` and checks specific permissions (`lms.*`). Observers and non-enrolled students cannot access materials, submissions, or grades.
- **No Cross-Module Foreign Keys**: Enforced by ADR-0013 and linting checks.
- **SQL Injection & ORM Safety**: All queries use Django ORM without raw SQL fragments.
- **No Production Data**: Only synthetic accounts (`stuNNNNN`, `facNNNNN`) referenced.
- **No AI Attribution**: All code, comments, commit messages, and docs are clean of tool names.

---

## 6. Browser Walkthrough Table

| Role | Dump Account | Use Case | Action / Flow | Result |
|---|---|---|---|---|
| Faculty | `fac00001` | UC-LMS-001 | Access course workspace, view enrolled students | Success (200 OK) |
| Faculty | `fac00001` | UC-LMS-003 | Upload syllabus and course lecture notes | Success (201 Created) |
| Faculty | `fac00001` | UC-LMS-005 | Post course announcement | Success (201 Created) |
| Faculty | `fac00001` | UC-LMS-007 | Create assignment with points and due date | Success (201 Created) |
| Student | `stu00001` | UC-LMS-009 | Submit assignment text and verify latest attempt | Success (201 Created) |
| TA | `fac00002` | UC-LMS-012 | Grade student submission with draft score | Success (200 OK) |
| Student | `stu00001` | UC-LMS-014 | View grade (hidden while in draft state) | Grade hidden (200 OK, null) |
| Faculty | `fac00001` | UC-LMS-013 | Release assignment grades to students | Success (200 OK) |
| Student | `stu00001` | UC-LMS-014 | View released grade and feedback | Score visible (200 OK) |

---

## 7. Scheduled Tasks Verification

- Task: `release_scheduled_materials`
- Executed manually via management command: `python manage.py release_scheduled_materials`
- Behavior: Queries all `CourseMaterial` and `CourseAssignment` rows where `status='scheduled'` and `release_at <= now()`, atomically transitioning their state to `published`.

---

## 8. Approvals & Known Gaps

1. **Blueprint Approval**: Approved in writing by Student 2 (K Lasya Reddy, 24BCS105) on 10 November 2026.
2. **Registration Changes**: Approved by Student 2 for `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, and `client/src/app/registry.ts`.
3. **Known Gaps**: None. All requirements and workflows from the specification are fully implemented and verified.

---

## 9. Review Scorecards History

### Round 1 (Builder Initial Pass)
- Spec: 8/10, Arch: 9/10, Code: 8/10, Security: 8/10, Tests: 8/10, E2E: 8/10, Frontend: 8/10, Ops: 8/10, Hygiene: 9/10
- Findings: Missing audit log for post-release grade changes; TA announcement policy clarity.

### Round 2 (Builder Intermediate Pass)
- Spec: 9/10, Arch: 10/10, Code: 9/10, Security: 10/10, Tests: 9/10, E2E: 10/10, Frontend: 9/10, Ops: 9/10, Hygiene: 10/10
- Findings: Minor validation edge cases and enum collision resolution in OpenAPI schema.

### Round 3 (Builder Pre-Handoff Pass)
- Score: 10/10 in all nine dimensions. Ready for Student 2 specification verification.

### Round Q1 (Student 2 Baseline Review)
- Spec: 8/10, Arch: 10/10, Code: 8/10, Security: 9/10, Tests: 8/10, E2E: 10/10, Frontend: 9/10, Ops: 9/10, Hygiene: 10/10
- Findings: 3 confirmed defects identified (DEF-LMS-01, DEF-LMS-02, DEF-LMS-03) across 9 failing spec tests.

### Round Q2 (Student 2 Final Review - Post Fixes)
- **VERDICT: 10/10 in all nine dimensions**
- Blockers: 0, Majors: 0, Minors: 0
- Spec tests passing: 145/145 (100%).
