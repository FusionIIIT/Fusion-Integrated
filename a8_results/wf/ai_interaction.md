# AI Interaction Log — Strategy 4: Workflows (WF)

- **Module:** File Tracking System (`modules/fts`)
- **Strategy:** WF (Basic & Composite Workflows: `BW-FTS-01`–`08`, `CW-FTS-01`–`02`)
- **AI Models Used:**
  - **Prompt A (Test Design Generation):** Claude 3.5 Sonnet
  - **Prompt B (Test Implementation & Execution):** Gemini 2.5 Pro via Google Antigravity
- **Date:** 2026-11-02
- **Frozen Test Design:** `a8_design/WF_DESIGN.json` (48 test obligations)
- **Executable Test Suite:** `tests/a8/wf/test_wf_spec.py`

---

## 1. Prompt A — Generate Frozen Test Design
```text
You are designing automated specification-based tests for the File Tracking System (FTS) Fusion ERP module.
Source of truth: Use ONLY the supplied Problem Statement and Workflows.
Do NOT inspect implementation code.
Do NOT infer behavior from implementation.
Do NOT introduce behavior unsupported by the supplied specification.
Generate the minimum non-redundant set of test cases needed to satisfy the strategy-specific adequacy rule in Section 7.

Strategy-specific instruction:
Cover every explicitly specified distinct workflow path/decision outcome. Ensure every important stated transition is exercised at least once; do not enumerate unsupported combinations.

Output ONLY a valid JSON array with fields: test_id, source_id, purpose, preconditions, action_or_input, expected_result, test_type.
```
- **Output:** 48 test obligations saved to `a8_design/WF_DESIGN.json`.

---

## 2. Prompt B — Convert Frozen Design into Executable Tests
```text
You are given:
1. the frozen A8_BASE Fusion implementation, and
2. the frozen WF_DESIGN.json.
Convert these test designs into executable automated backend tests using pytest/pytest-django.
Rules:
- Implement exactly the supplied test cases (TC_WF_001 to TC_WF_048).
- Do not add, remove, merge or reinterpret test cases.
- Preserve each specified expected result.
- Do not modify production code.
- Use the Django isolated test database.
- Every test must contain its test_id and source_id in its name or docstring.
- Store generated tests only under tests/a8/wf/.
If a test genuinely cannot be automated using available backend interfaces, mark with NOT_AUTOMATED: <reason>.
```
- **Output:** `tests/a8/wf/test_wf_spec.py`

---

## 3. Prompt C — Repair Prompts
- **Used:** 0 repair prompts. The suite executed cleanly on initial generation.

---

## 4. Execution & Evidence Summary
- **Execution Command:**
  ```bash
  pytest tests/a8/wf --junitxml=a8_results/wf/junit.xml --cov=modules/fts --cov-branch --cov-report=xml:a8_results/wf/coverage.xml --cov-report=term-missing > a8_results/wf/pytest.log 2>&1
  ```
- **Test Counts:** 48 Total | 43 Passed | 5 Failed (`TC_WF_005`, `010`, `024` exposing DEF-002; `TC_WF_017`, `043` exposing DEF-001) | 0 Skipped
- **Coverage:** Statement = 54.77% (241/440 lines) | Branch = 69.74% (53/76 branches)
