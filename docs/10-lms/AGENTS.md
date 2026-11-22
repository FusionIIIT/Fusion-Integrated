# AGENTS.md — Assignment 7 LMS Course Management Governance

## Project Identity & Scope
- **Module:** LMS (Course Management) inside Fusion ERP (FusionIIIT).
- **Dedicated Branch:** lms-course-management.
- **Target PR:** Abhinavreddy2006/Fusion-Integrated:lms-course-management -> FusionIIIT/Fusion-Integrated:main.

## Role Separation & Model Governance
- **Antigravity (Gemini):** Project Orchestrator, task decomposition, repository inspection, build/test coordinator. Antigravity must NEVER generate LMS application code.
- **Local Qwen 2.5 7B:** Sole authorized AI coder (Model: qwen2.5:7b, Quantization: Q4_K_M, Digest prefix: 845dbda0ea48, Windows Ollama endpoint: http://localhost:11434/v1). Local Qwen authors all LMS code, models, services, APIs, tests, and technical documentation.

## Protection of Completed ELM Project
- **ELM Branch Assignment:** The branch assignment6b/elm-review and PR #269 are completed and protected.
- **No Modifications to Modules/ELM:** Absolutely no modifications to modules/elm, docs/09-elm, ELM migrations, or ELM history.
- **LMS Branch Origin:** LMS branch is branched purely from canonical main (02b01fe).

## Authoritative Specifications & Open Issues
- **Authoritative Documents:** 01 Problem Statement, 02 Requirement Registry, 03 Use Cases, 04 Business Rules, 05 Workflows, 06 Traceability Matrix.
- **Unresolved Policy Issues:** The 6 unresolved policy issues (ISS-LMS-001 through ISS-LMS-006) MUST remain explicitly unresolved (NEEDS CLARIFICATION). No silent policy invention.

## Safe Tool Policies & Approvals
- **Mandatory Human Approval:** Before writing/editing files, executing migrations, or running git operations.
- **Full Persistence and Logging:** Full persistence and logging in local_agent/logs/ (timestamps, model digest, prompts, responses).