# Employee Leave Management (ELM) - Phase 2 Implementation

## 1. Overview
This module implements the complete Employee Leave Management (ELM) for Fusion ERP, adhering strictly to:
- `01_ELM_Problem_Statement_v1.4_FINAL.docx`
- `02_ELM_Functional_Requirement_Specification_v1.5_FINAL.xlsx`
- `03_ELM_Use_Case_Specifications_v1.4_FINAL.docx`
- `04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx`
- `06_ELM_Workflow_Specifications_v1.6_FINAL.docx`
- `06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`
- `fixed.txt` (Model Trial 1: DeepSeek Coder 6.7B Instruct Q4_K_M)
- `Fusion ERP Lab Assignment-6B.docx` (Phase 2 Review, Test, Improve and Verify)

## 2. Architecture & File Structure
```
modules/elm/
├── __init__.py
├── apps.py                  # App configuration & Django registry
├── permissions.py           # Declared fine-grained permissions
├── registry.py              # Module manifest, navigation, role grants
├── contracts.py             # Public service contract for other Fusion modules
├── domain/
│   ├── __init__.py
│   ├── errors.py            # Domain exceptions
│   ├── policy.py            # Pure policy functions (durations, counting, calendars)
│   └── workflow.py          # State machine transitions (CW-EL-01 to CW-EL-04)
├── models/
│   ├── __init__.py
│   └── leave.py             # Django ORM models (LeaveRequest, LeaveAccount, etc.)
├── services/
│   ├── __init__.py
│   ├── policy.py            # Policy evaluation & balance validation
│   ├── workflow.py          # Transactional workflow state orchestration
│   └── admin.py             # Offline sync, year-end processing, SLA sweep
├── api/
│   ├── __init__.py
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # ViewSets with role/principal authorization
│   └── urls.py              # Router URL endpoints
├── management/
│   └── commands/
│       └── elm_process_sla.py # Background SLA check worker
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py      # Schema migration
└── tests/
    ├── __init__.py
    ├── test_domain_policy.py   # 15 pure policy unit tests
    └── test_domain_workflow.py # 14 workflow transition unit tests

client/src/modules/elm/
├── routes.tsx               # Frontend lazy route declarations
├── api/
│   └── types.ts             # TypeScript definitions
└── pages/
    ├── ELMPage.tsx          # Self-service portal (balances, apply, history, withdraw)
    └── ELMAdminPage.tsx     # Admin & approval portal (approvals, offline, SLA)
```

## 3. Verified Business Rules & Tests
- **BR-EL-001, BR-EL-005, BR-EL-006:** Eligibility enforcement (Staff vs Faculty for VL and EL).
- **BR-EL-002, BR-EL-003, BR-EL-004:** CL (8 days), RH (2 days), SCL (15 days) entitlements and lapse.
- **BR-EL-007, BR-EL-008:** Year-end VL-to-EL conversion at 2:1 ratio (with fractional conversion).
- **BR-EL-010:** Half-day CL (first_half / second_half) duration = 0.5.
- **BR-EL-011:** Continuous counting for EL/COL/VL vs working-day counting for CL/SCL/RH.
- **BR-EL-012:** Overlap prevention with complementary half-day CL non-overlap exception.
- **BR-EL-014, BR-EL-015:** Substitute eligibility and consent gate.
- **BR-EL-016, BR-EL-017, BR-EL-018:** Unit Head decision for CL/RH vs recommendation for higher sanction.
- **BR-EL-020:** Director self-sanction.
- **BR-EL-022:** Immediate withdrawal of pending requests before final approval.
- **BR-EL-023:** Cancellation of approved leave before start, with balance restore.
- **BR-EL-028:** Normal, early, and late resumption balance adjustments.
- **BR-EL-029:** Offline-sanctioned leave synchronization.
- **BR-EL-032, BR-EL-033:** SLA reminder and escalation sweeps.

## 4. Verification Commands
```bash
# Set PYTHONPATH
$env:PYTHONPATH="g:\6B\Fusion-Integrated"

# 1. Syntax Compilation
python -m compileall -q modules/elm config/urls.py config/settings/base.py

# 2. Run All Unit Tests (29 tests)
python -m unittest modules.elm.tests.test_domain_policy modules.elm.tests.test_domain_workflow -v
```
All 29 tests pass with 0 failures and 0 errors.
