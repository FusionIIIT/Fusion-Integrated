# ELM (Leave) — what we have done

Rough first cut on branch `elmByMe`. Push on next user prompt.

## Files added

- `modules/leave/apps.py` — LeaveConfig
- `modules/leave/models.py` — LeaveRequest + LeaveTransition
- `modules/leave/domain/state_machine.py` — draft to approved flow
- `modules/leave/domain/entitlement.py` — yearly credit dict, carry set
- `modules/leave/contracts.py` — get_leave_balances (plural)
- `modules/leave/selectors/leaves.py` — leaves_for, is_staff
- `modules/leave/services/leaves.py` — submit_leave, move, transition
- `modules/leave/api/serializers.py` — read + apply + transition
- `modules/leave/api/views.py` — List, Apply, Transition
- `modules/leave/api/urls.py` — requests, requests/apply, requests/<pk>/transition
- `modules/leave/registry.py` — MODULE elm planned, nav, permissions, grants
- `modules/leave/events.py` — elm.leave.applied, elm.leave.status_changed
- `modules/leave/tasks.py` — year_end_process
- `modules/leave/migrations/0001_initial.py` — leave_request + leave_transition
- `modules/leave/tests/test_domain.py` — table, illegal, terminal, entitlement

## Wiring changed (mechanical only)

- `config/settings/base.py` — DOMAIN_MODULES add modules.leave
- `config/urls.py` — api/v1/leave/ include
- `.importlinter` — leave in modules-only-touch-contracts, domain pure,
  new leave-layers contract

## Known rough edges

- Overlap check missing, balance check is guard name only.
- Weekend counting simplified, RH calendar not wired.
- Frontend not done, seed/permissions not run, migration not applied.
