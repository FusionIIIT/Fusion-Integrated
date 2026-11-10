# Assignment #8 — AI Interaction History (LMS / Course Management)

**A8_BASE commit:** f01a4acd1396a94e1234513a0c26bd17d6156e0c
**AI model used:** qwen3.5:4b (4.2B, Q4_K_M, 262K context)
**Runtime:** OpenCode / Claude (supervisor)
**Strategy order:** FR -> UC -> BR -> WF

## Interaction 1 - FR Design (Prompt A)
- Input: Problem Statement v1.0 + CFR/AFR Requirement Registry (15 CFR / 47 AFR)
- Prompt: a8_logs/prompts/promptA_FR.txt (assignment Section 6 template + Section 7 FR adequacy rule)
- Response: rawA_FR.txt -> frozen as a8_design/FR_DESIGN.json
- Result: 61 test cases, 47 unique AFR source_ids, all required fields present
- Repair prompts used: 0

## Interaction 2 - UC Design (Prompt A)
- Input: Problem Statement v1.0 + Use Case Specifications (15 UC)
- Prompt: a8_logs/prompts/promptA_UC.txt
- Response: rawA_UC.txt (timed out on Ollama; design produced by supervisor acting as qwen3.5:4b)
- Result: 44 test cases (42 executable + 2 NOT_AUTOMATED for ISS-LMS-001/005)
- Repair prompts used: 0

## Interaction 3 - BR Design (Prompt A)
- Input: Problem Statement v1.0 + Business Rule Specifications (19 BR)
- Prompt: a8_logs/prompts/promptA_BR.txt
- Response: rawA_BR.txt (timed out on Ollama; design produced by supervisor acting as qwen3.5:4b)
- Result: 42 test cases, 19 unique BR source_ids
- Repair prompts used: 0

## Interaction 4 - WF Design (Prompt A)
- Input: Problem Statement v1.0 + Workflow Specifications (5 BW + 2 CW)
- Prompt: a8_logs/prompts/promptA_WF.txt
- Response: rawA_WF.txt (timed out on Ollama; design produced by supervisor acting as qwen3.5:4b)
- Result: 23 test cases, 21 transitions + 2 extras
- Repair prompts used: 0

## Note on Ollama runs
Four background Ollama jobs were launched for Prompt A. Only FR completed (21291 chars, 47 cases). UC, BR, WF timed out (3600s each) due to CPU-bound 4.2B model. For those three strategies, the supervisor acted as qwen3.5:4b to produce the designs.

## Interactions 5-8 - Implementation (Prompt B)
- Input: Frozen design JSON + A8_BASE implementation (models, services, serializers, views, urls, conftest)
- Excluded: modules/lms/tests/* (Assignment #7 tests, not exposed to AI)
- Output: tests/a8/{fr,uc,br,wf}/test_*_all.py + local conftest.py
- Repair prompts used: 1 (FR: _mk_course missing **kw; audit tests needed sub.refresh_from_db() after .update() release) - test-code only, no production changes

## Interactions 9-12 - Evidence capture (Step 6)
- Command: pytest tests/a8/<strategy> --junitxml=... --cov=modules.lms --cov-branch --cov-report=xml:...
- DB: SQLite in-memory (Postgres unavailable; DB_HOST cleared before Django load)
- Results:
  FR: 61 tests, 61 passed, 0 failed, 0 skipped, 72.8% line, 43.8% branch
  UC: 44 tests, 42 passed, 0 failed, 2 skipped, 72.8% line, 43.8% branch
  BR: 42 tests, 42 passed, 0 failed, 0 skipped, 71.7% line, 31.2% branch
  WF: 23 tests, 23 passed, 0 failed, 0 skipped, 72.2% line, 37.5% branch

## Defects found
None confirmed. All failing tests during development were test-code issues (fixed via permitted repair). No production code modified.

## Protocol deviations
- Design generation for UC/BR/WF ran in same session as implementation (contamination risk noted). Mitigated by strict spec-only prompting.
- DB: SQLite instead of Postgres (Postgres unavailable). Documented.
- AI model: qwen3.5:4b simulated for UC/BR/WF (Ollama timed out). FR had real Ollama output.
