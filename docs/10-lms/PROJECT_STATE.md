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
- **Sole AI Coding Agent:** qwen2.5:7b (Q4_K_M, Digest prefix: 845dbda0ea48, Windows Ollama)
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
- **Current Phase:** Phase 0 / Phase 1 Initialization (Git Branching & Project Memory Scaffolding)
- **CFR Count:** 15 Core Functional Requirements
- **AFR Count:** 47 Atomic Functional Requirements
- **BR Count:** 19 Business Rules
- **UC Count:** 15 Use Cases
- **BW/CW Count:** 5 Basis Workflows, 2 Composite Workflows
- **Open Issues:** 6 unresolved policy issues (ISS-LMS-001 to ISS-LMS-006)