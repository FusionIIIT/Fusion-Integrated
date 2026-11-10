# AI Interaction Log — UC Strategy (Specification-Driven Testing)

## Session: UC Design (Prompt A)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Problem Statement v1.0 + Use Case Specifications v1.0 SYNCHRONIZED (15 UCs)
**Implementation code visible:** No

### Prompt A (sent to model)
```
You are designing automated specification-based tests for the LMS (Course Management) Fusion ERP module.

Source of truth: Use ONLY the supplied Problem Statement and Use Cases from the Use Case Specifications.
Do NOT inspect implementation code.
Do NOT infer behavior from implementation.
Do NOT introduce behavior unsupported by the supplied specification.
Generate the minimum non-redundant set of test cases needed to satisfy the strategy-specific adequacy rule below.

For every test case output exactly these fields:
- test_id
- source_id
- purpose
- preconditions
- action_or_input
- expected_result
- test_type
- source_id must identify the exact obligation covered (e.g., UC-05 Main Flow, UC-05 Alternative A1).

Output ONLY a valid JSON array. Do not provide explanation or additional prose.

=== STRATEGY-SPECIFIC ADEQUACY RULE ===
Cover the main success flow of every Use Case and every explicitly specified alternative/exception flow with at least one test. Do not invent additional flows.

=== PROBLEM STATEMENT (v1.0) ===
[Full problem statement text]

=== USE CASE SPECIFICATIONS ===
[Full use case specifications - 15 UCs with main/alternative/exception flows]
```

### Model Response (summary)
Generated 44 test cases covering all 15 Use Cases. Each UC has its main flow plus every explicitly specified alternative and exception flow. Two cases (UC-010 late submission, UC-010 resubmission) marked as `skipped` with `NOT_AUTOMATED` reason since the corresponding policies are unresolved in PS v1.0 (ISS-LMS-001, ISS-LMS-005). No behavior was invented for unresolved policies.

### Frozen Design
Saved as `a8_design/UC_DESIGN.json` — 44 cases (42 executable + 2 skipped), 44 unique source_ids. No repair prompts needed.

---

## Session: UC Implementation (Prompt B)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Frozen UC_DESIGN.json + A8_BASE implementation
**Excluded:** modules/lms/tests/*

### Prompt B (sent to model)
[Same template as FR, with UC_DESIGN.json and implementation files]

### Model Response (summary)
Generated 44 test functions in `tests/a8/uc/test_uc_all.py` plus local `conftest.py`. Two NOT_AUTOMATED cases implemented as `pytest.skip("NOT_AUTOMATED: ...")`.

### Repair Prompts Used: 0

### Execution Result
- 44 tests, 42 passed, 0 failed, 2 skipped
- Line coverage: 72.8%, Branch coverage: 43.8%
- Evidence: `a8_results/uc/{junit.xml, coverage.xml, pytest.log}`
