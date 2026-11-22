# AI Interaction Log — WF Strategy (Specification-Driven Testing)

## Session: WF Design (Prompt A)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Problem Statement v1.0 + Workflow Specifications v1.0 SYNCHRONIZED (5 BW + 2 CW)
**Implementation code visible:** No

### Prompt A (sent to model)
```
You are designing automated specification-based tests for the LMS (Course Management) Fusion ERP module.

Source of truth: Use ONLY the supplied Problem Statement and Workflows from the Workflow Specifications.
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
- source_id must identify the exact obligation covered (e.g., WF-02 approval-rejected path).

Output ONLY a valid JSON array. Do not provide explanation or additional prose.

=== STRATEGY-SPECIFIC ADEQUACY RULE ===
Cover every explicitly specified distinct workflow path/decision outcome. Ensure every important stated transition is exercised at least once; do not enumerate unsupported combinations.

=== PROBLEM STATEMENT (v1.0) ===
[Full problem statement text]

=== WORKFLOW SPECIFICATIONS ===
[Full workflow specifications - 5 Basis Workflows + 2 Composite Workflows with state-transition tables]
```

### Model Response (summary)
Generated 23 test cases covering 21 state transitions across 7 workflows (5 BW + 2 CW). Each transition step gets a case, plus 2 guard-failure branches (BW-01 withdrawn before release; BW-01/BW-03 release processing failure). Total: 22 positive, 1 negative.

### Frozen Design
Saved as `a8_design/WF_DESIGN.json` — 23 cases, 23 unique source_ids. No repair prompts needed.

---

## Session: WF Implementation (Prompt B)
**Date:** 2026-11-10
**AI Model:** qwen3.5:4b
**Input artifacts:** Frozen WF_DESIGN.json + A8_BASE implementation
**Excluded:** modules/lms/tests/*

### Prompt B (sent to model)
[Same template as FR, with WF_DESIGN.json and implementation files]

### Model Response (summary)
Generated 23 test functions in `tests/a8/wf/test_wf_all.py` plus local `conftest.py`. Tests use model-level assertions (direct ORM calls) for workflow state transitions.

### Repair Prompts Used: 0

### Execution Result
- 23 tests, 23 passed, 0 failed, 0 skipped
- Line coverage: 72.2%, Branch coverage: 37.5%
- Evidence: `a8_results/wf/{junit.xml, coverage.xml, pytest.log}`
