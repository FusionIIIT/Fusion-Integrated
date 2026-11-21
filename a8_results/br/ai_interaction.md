# AI Interaction Log — Strategy 3: Business Rules (BR)

- **Module:** File Tracking System (`modules/fts`)
- **Strategy:** BR (Business Rules `BR-FTS-001` through `BR-FTS-014`)
- **AI Models Used:**
  - **Prompt A (Test Design Generation):** Claude 3.5 Sonnet
  - **Prompt B (Test Implementation & Execution):** Gemini 2.5 Pro via Google Antigravity
- **Date:** 2026-11-02
- **Frozen Test Design:** `a8_design/BR_DESIGN.json` (49 test obligations)
- **Executable Test Suite:** `tests/a8/br/test_br_spec.py`

---

## 1. Prompt A — Generate Frozen Test Design
```text
You are designing automated specification-based tests for the File Tracking System (FTS) Fusion ERP module.
Source of truth: Use ONLY the supplied Problem Statement and Business Rules.
Do NOT inspect implementation code.
Do NOT infer behavior from implementation.
Do NOT introduce behavior unsupported by the supplied specification.
Generate the minimum non-redundant set of test cases needed to satisfy the strategy-specific adequacy rule in Section 7.

Strategy-specific instruction:
Cover every Business Rule with at least one test. Where a rule explicitly has materially different permitted/prohibited outcomes, threshold sides, or stated exceptions, cover each relevant outcome.

Output ONLY a valid JSON array with fields: test_id, source_id, purpose, preconditions, action_or_input, expected_result, test_type.
```
- **Output:** 49 test obligations saved to `a8_design/BR_DESIGN.json`.

---

## 2. Prompt B — Convert Frozen Design into Executable Tests
```text
You are given:
1. the frozen A8_BASE Fusion implementation, and
2. the frozen BR_DESIGN.json.
Convert these test designs into executable automated backend tests using pytest/pytest-django.
Rules:
- Implement exactly the supplied test cases (TC_BR_001 to TC_BR_049).
- Do not add, remove, merge or reinterpret test cases.
- Preserve each specified expected result.
- Do not modify production code.
- Use the Django isolated test database.
- Every test must contain its test_id and source_id in its name or docstring.
- Store generated tests only under tests/a8/br/.
If a test genuinely cannot be automated using available backend interfaces, mark with NOT_AUTOMATED: <reason>.
```
- **Output:** `tests/a8/br/test_br_spec.py`

---

## 3. Prompt C — Repair Prompts
- **Used:** 0 repair prompts. The suite executed cleanly on initial generation.

---

## 4. Execution & Evidence Summary
- **Execution Command:**
  ```bash
  pytest tests/a8/br --junitxml=a8_results/br/junit.xml --cov=modules/fts --cov-branch --cov-report=xml:a8_results/br/coverage.xml --cov-report=term-missing > a8_results/br/pytest.log 2>&1
  ```
- **Test Counts:** 49 Total | 41 Passed | 2 Failed (`TC_BR_018` exposing DEF-002, `TC_BR_038` exposing DEF-001) | 6 Skipped (`NOT_AUTOMATED`)
- **Coverage:** Statement = 60.00% (264/440 lines) | Branch = 64.47% (49/76 branches)
