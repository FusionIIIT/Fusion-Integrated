# AI Interaction Log — FR Strategy (Specification-Driven Testing)

## Session: FR Design (Prompt A)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Problem Statement v1.0 + Requirement Registry (CFR/AFR) v1.0 SYNCHRONIZED
**Implementation code visible:** No

### Prompt A (sent to model)
```
You are designing automated specification-based tests for the LMS (Course Management) Fusion ERP module.

Source of truth: Use ONLY the supplied Problem Statement and CFR/AFR from the Requirement Registry.
Do NOT inspect implementation code.
Do NOT infer behavior from implementation.
Do NOT introduce behavior unsupported by the supplied specification.
Generate the minimum non-redundant set of test cases needed to satisfy the strategy-specific adequacy rule below. Do not stop at an arbitrary number, do not omit an explicit test obligation to reduce the test count, and do not invent unsupported behavior. Prefer observable behavior that can subsequently be automated using pytest/pytest-django.

For every test case output exactly these fields:
- test_id
- source_id
- purpose
- preconditions
- action_or_input
- expected_result
- test_type
- source_id must identify the exact obligation covered.

Output ONLY a valid JSON array. Do not provide explanation or additional prose.

=== STRATEGY-SPECIFIC ADEQUACY RULE ===
Cover every testable CFR/AFR with at least one test. Add a separate negative/boundary/validation/authorization case only where the requirement explicitly defines such a condition or outcome.

=== PROBLEM STATEMENT (v1.0) ===
[Full problem statement text - 15 CFRs, 47 AFRs]

=== CFR/AFR REQUIREMENT REGISTRY ===
[Full requirement registry text]
```

### Model Response (summary)
Generated 61 test cases covering all 47 AFRs under 15 CFRs. Each case has exactly the 7 required fields. Test types: 38 positive, 23 negative. Source IDs map 1:1 to AFR-LMS-xxx.x identifiers. No implementation behavior was inferred — all expected results trace directly to the specification.

### Frozen Design
Saved as `a8_design/FR_DESIGN.json` — 61 cases, 47 unique source_ids, all required fields present. No repair prompts needed.

---

## Session: FR Implementation (Prompt B)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Frozen FR_DESIGN.json + A8_BASE implementation (models, services, serializers, views, urls, conftest)
**Implementation code visible:** Yes (Step 4 — code exposure permitted after design freeze)
**Excluded:** modules/lms/tests/* (Assignment #7 tests)

### Prompt B (sent to model)
```
You are given:
1. the frozen A8_BASE Fusion implementation, and
2. the frozen FR_DESIGN.json.

Convert these test designs into executable automated backend tests using pytest/pytest-django.
Rules:
- Implement exactly the supplied test cases.
- Do not add, remove, merge or reinterpret test cases.
- Preserve each specified expected result.
- Do not modify production code.
- Use the Django isolated test database.
- Reuse existing Fusion test infrastructure where appropriate.
- Do not mock the behavior being tested.
- Do not use xfail to hide failures.
- Every test must contain its test_id and source_id in its name or docstring.
- Store generated tests only under tests/a8/fr/.
If a test genuinely cannot be automated, create it as a skipped pytest test with: NOT_AUTOMATED: <reason>.
```

### Model Response (summary)
Generated 61 executable test functions in `tests/a8/fr/test_fr_all.py` plus a local `conftest.py` with `_login` helper. Each test carries its test_id and source_id in the docstring. Uses root `conftest.py` fixtures (`stub_iam`, `make_session`).

### Repair Prompts Used: 1
1. `_mk_course` helper missing `**kw` parameter — added `**kw` to accept `allow_ta_announcements` etc.
2. Audit tests needed `sub.refresh_from_db()` after `release_assignment_grades()` (which uses `.update()`) before re-grading to trigger audit creation.

### Execution Result
- 61 tests, 61 passed, 0 failed, 0 skipped
- Line coverage: 72.8%, Branch coverage: 43.8%
- Evidence: `a8_results/fr/{junit.xml, coverage.xml, pytest.log}`
