# 10-lms/PROJECT_STATE.md — LMS Course Management Project State

## 1. Project Coordinates:
- **Module Name:** LMS (Course Management)
- **Platform:** Fusion ERP (FusionIIIT)
- **Repository:** Fusion-Integrated
- **User Fork:** Abhinavreddy2006/Fusion-Integrated
- **Upstream:** FusionIIIT/Fusion-Integrated
- **Base Commit:** 02b01fea4a67b257ea7000009f06a1561699550e (canonical upstream/main)
- **Active Module Branch:** lms-course-management
- **Submission Target:** PR to FusionIIIT/Fusion-Integrated:main

## 2. AI Governance & Model Coordinates:
- **Sole AI Coding Agent:** qwen2.5:7b (Q4_K_M, Full Digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, Windows Ollama)
- **Project Orchestrator:** Antigravity (Gemini Pro) — orchestration, test coordination, no product code generation.
- **Logging Directory:** local_agent/logs/ (verbatim prompts, responses, timestamps, model digests)

## 3. ELM Assignment Protection Boundary:
- **Branch:** assignment6b/elm-review (commit 886092b)
- **PR:** #269
- **Status:** COMPLETED, FROZEN, PROTECTED. Zero commits, zero diffs, zero merges.

## 4. Repository Layout & Planned Module Coordinates:
- **Backend Module:** modules/lms/
- **Frontend Module:** client/src/modules/lms/
- **Canonical Documentation:** docs/10-lms/
- **API Root:** /api/v1/lms/
- **UI Base Path:** /courses

## 5. Operational Metrics & Phase Status:
- **Current Phase:** Phase 4 Backend Services, Selectors, REST APIs and Permissions (COMPLETED)
- **PR Status:** Official PR #437 Open on FusionIIIT/Fusion-Integrated:main
- **Architecture Documents:** DOMAIN_MODEL.md, WORKFLOW_DESIGN.md, INTEGRATION_DESIGN.md, ARCHITECTURE_PLAN.md
- **CFR Count:** 15 Core Functional Requirements
- **AFR Count:** 47 Atomic Functional Requirements
- **BR Count:** 19 Business Rules
- **UC Count:** 15 Use Cases
- **BW/CW Count:** 5 Basis Workflows, 2 Composite Workflows
- **Open Issues:** 6 unresolved policy issues (ISS-LMS-001 to ISS-LMS-006, strictly NEEDS CLARIFICATION)
- **Implemented Backend Models:** 10 domain models in `modules/lms/models/` (`Course`, `CourseMembership`, `ModuleSection`, `CourseMaterial`, `Announcement`, `Assignment`, `Submission`, `Grade`, `GradeAuditLog`, `ScheduledRelease`)
- **Database Migrations:** `modules/lms/migrations/0001_initial.py`, `modules/lms/migrations/0002_alter_gradeauditlog_grade.py`
- **Module Contracts:** `modules/lms/contracts.py` (DTOs and batched queries, satisfying `.importlinter`)
- **Implemented Query Selectors:** `modules/lms/selectors/` (`courses.py`, `content.py`, `assignments.py`, `submissions.py`, `grades.py`)
- **Implemented Business Services:** `modules/lms/services/` (`courses.py`, `content.py`, `assignments.py`, `storage.py`, `submissions.py`, `grading.py`, `release.py`, `management/commands/lms_process_scheduled_releases.py`)
- **Implemented Role-Based Permissions:** `modules/lms/api/permissions.py` (Instructor, TA, Student, Observer isolation, multi-role cardinality)
- **Mounted REST API:** `/api/v1/lms/` in `config/urls.py` via `modules/lms/api/` (`serializers.py`, `views.py`, `urls.py`)
- **Automated Test Suite:** 38 tests passing in 3.74s across 7 test files (`test_models.py`, `test_constraints.py`, `test_audit_immutability.py`, `test_selectors.py`, `test_services.py`, `test_permissions.py`, `test_api.py`)
- **Repository Verification:** `manage.py check` (0 issues), `lint-imports` (4 kept, 0 broken), `git diff --check` (clean)
