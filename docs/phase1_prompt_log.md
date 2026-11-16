# Phase 1 — AI Interaction & Prompt Log

## Session Metadata
- **Code LLM**: `deepseek-coder:6.7b`
- **Model Family**: DeepSeek
- **Parameter Size**: 7B
- **Quantization**: `Q4_0`
- **Inference Runtime**: Ollama (`ollama run deepseek-coder:6.7b`)
- **Coding Agent / Tool**: Continue (VS Code repository-aware assistant)
- **Target Repository**: Fusion-Integrated (`FusionIIIT:main`)
- **Date**: October 2026

---

## Interaction 1: Domain Architecture & Requirements Alignment

### User Prompt:
```text
We are implementing the Employee Leave Management (ELM) module for Fusion ERP based on the CS3010 Lab 5 EBC/BCE domain analysis model and the specifications in files_software_ev.
The target workflow is BW-HR-01 (direct approval).
Requirements to enforce:
- BR-HR-002: Leave application submission
- BR-HR-007: Mandatory fields (leave type, duration > 0, valid dates, non-empty justification)
- BR-HR-008: Leave balance check prior to deduction
- BR-HR-009: Approval authority routing (Faculty -> HOD, Staff -> Registrar)
- BR-HR-010: Automated balance deduction upon approval
- BR-HR-023: Valid state transitions (Draft -> Pending -> Approved / Rejected)
- BR-HR-034: Supported leave types (Casual, Restricted, Medical, Earned, Vacation, Sabbatical)

Generate the pure Python domain layer under modules/leave/domain/:
1. entities.py: Plain dataclasses for LeaveRequest, LeaveBalance, ApprovalDecision
2. rules.py: Pure validation functions without Django dependencies
3. state_machine.py: State transitions and actor permission resolution
```

### Assistant Response (deepseek-coder:6.7b via Continue):
```python
# Generated modules/leave/domain/entities.py
# Generated modules/leave/domain/rules.py
# Generated modules/leave/domain/state_machine.py
```
*Generated pure Python domain classes, state machine dictionary with allowed transitions `(DRAFT -> PENDING_CURRENT_AUTHORITY)`, `(PENDING_CURRENT_AUTHORITY -> APPROVED)`, `(PENDING_CURRENT_AUTHORITY -> REJECTED)`, and authority selection logic.*

---

## Interaction 2: Database Models & Service Layer

### User Prompt:
```text
Now generate the persistence and service layer for the leave module adhering to Fusion Base boundary constraints:
1. modules/leave/models.py:
   - LeaveRequest (plain integer user_id, no cross-module foreign keys)
   - LeaveBalance (user_id, leave_type, year, total_entitlement, consumed_days, available_balance)
   - ApprovalDecision (request foreign key, authority_id, outcome, remarks, timestamp)
   - ApprovingAuthority (role, department, authority_user_id)
2. modules/leave/services/submission.py:
   - submit_leave_request: validates balance and rules, creates LeaveRequest in pending state
3. modules/leave/services/decisions.py:
   - record_approval_decision: updates status, deducts balance if approved, records decision audit
4. modules/leave/selectors/leaves.py:
   - Query helpers for user's leaves, user's balances, and pending requests for authorities
```

### Assistant Response (deepseek-coder:6.7b via Continue):
```python
# Generated modules/leave/models.py
# Generated modules/leave/services/submission.py
# Generated modules/leave/services/decisions.py
# Generated modules/leave/selectors/leaves.py
```
*Generated Django models avoiding cross-module foreign keys, transaction-wrapped service functions executing domain rule validations before model persistence, and selector query functions.*

---

## Interaction 3: REST API & Module Integration

### User Prompt:
```text
Create the DRF API endpoints and register the module with Fusion Base:
1. modules/leave/api/serializers.py:
   - Serializers for LeaveRequest, LeaveBalance, ApprovalDecision, and input payloads
2. modules/leave/api/views.py:
   - LeaveRequestListCreateView (/api/v1/leave/requests/)
   - LeaveBalanceListView (/api/v1/leave/balances/)
   - PendingApprovalsListView (/api/v1/leave/pending/)
   - DecideLeaveRequestView (/api/v1/leave/requests/<pk>/decide/)
3. Register module nav and metadata in modules/leave/registry.py and manifest.json.
```

### Assistant Response (deepseek-coder:6.7b via Continue):
```python
# Generated modules/leave/api/serializers.py
# Generated modules/leave/api/views.py
# Generated modules/leave/api/urls.py
# Generated modules/leave/registry.py
# Generated modules/leave/manifest.json
```
*Generated API views with permission checks, URL routing, and registry metadata matching Fusion Base conventions.*

---

## Interaction 4: Frontend Client Interface

### User Prompt:
```text
Generate the React + Mantine frontend module under client/src/modules/leave/:
- types.ts: TypeScript interfaces
- api.ts: React Query hooks using http client
- pages/ApplyLeavePage.tsx: Leave application form with balance preview
- pages/MyLeavesPage.tsx: Table of submitted leaves with status badges
- pages/LeaveBalancesPage.tsx: Cards showing entitlement, consumed, and remaining quota
- pages/PendingApprovalsPage.tsx: Authority review interface with approve/reject actions
- routes.tsx: Module route definitions
```

### Assistant Response (deepseek-coder:6.7b via Continue):
```tsx
// Generated client/src/modules/leave/types.ts
// Generated client/src/modules/leave/api.ts
// Generated client/src/modules/leave/pages/ApplyLeavePage.tsx
// Generated client/src/modules/leave/pages/MyLeavesPage.tsx
// Generated client/src/modules/leave/pages/LeaveBalancesPage.tsx
// Generated client/src/modules/leave/pages/PendingApprovalsPage.tsx
// Generated client/src/modules/leave/routes.tsx
```
*Generated client pages using Mantine UI components and React Query hooks wired to the backend API endpoints.*

---

## Interaction 5: Domain Unit Tests

### User Prompt:
```text
Write unit tests in modules/leave/tests/test_domain.py testing the pure domain layer:
- Legal state machine transitions (BW-HR-01 canonical path)
- Illegal transition rejection
- Actor authorization enforcement
- Terminal state verification
- BR-HR-007 mandatory fields validation
- BR-HR-008 balance check
- BR-HR-009 routing authority selection
- BR-HR-010 balance deduction calculation
- BR-HR-034 supported leave types
```

### Assistant Response (deepseek-coder:6.7b via Continue):
```python
# Generated modules/leave/tests/test_domain.py
```
*Generated unit test suite verifying all domain rules, runnable directly via `python -m unittest modules.leave.tests.test_domain`.*
