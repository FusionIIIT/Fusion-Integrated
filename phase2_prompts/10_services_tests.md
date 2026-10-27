# Task: write pytest tests for leave services in modules/leave/tests/test_services.py

Context:
Pattern to follow: `modules/placement/services/applications.py` and its test conventions.
Module under test: `modules/leave/services/applications.py`.
Models: `LeaveCategory`, `LeaveApplication`, `LeaveApplicationTransition`, `LeaveBalance` from `modules.leave.models`.
Domain exceptions: `ConflictError`, `NotFoundError`, `PermissionDeniedError` from `core.api.exceptions`.
Pure state machine: `modules.leave.domain.state_machine as sm`.
Database: `@pytest.mark.django_db` on all tests / `pytestmark = pytest.mark.django_db`.

## Functions under test in `modules.leave.services.applications`
1. `apply(*, user_id, category_code, start_date, end_date, half_day="", reason="", is_station_leave=False, station_details=None, substitute_user_id=None, applicant_is_director=False, medical_evidence_ref="") -> LeaveApplication`
2. `transition(*, application_id, to_status, actor, reason="", scope=None, recommendation="", role=None, replacement_substitute_id=None) -> LeaveApplication`
3. `actor_kind(actor, application=None, role=None) -> str`

## Helper Principal
```python
class DummyPrincipal:
    def __init__(self, user_id=None, permissions=(), roles=(), actor_kind=None):
        self.user_id = user_id
        self.permissions = set(permissions)
        self.roles = set(roles)
        self.actor_kind = actor_kind

    def has_permission(self, code: str) -> bool:
        return code in self.permissions
```

## Fixtures needed
- `cl_cat`: LeaveCategory code="CL", name="Casual Leave"
- `el_cat`: LeaveCategory code="EL", name="Earned Leave"
- `cl_balance`: LeaveBalance for user_id=1, category=cl_cat, year=2026, balance_days=Decimal("8.0")
- `el_balance`: LeaveBalance for user_id=1, category=el_cat, year=2026, balance_days=Decimal("30.0")

## Tests required
1. `test_apply_cl_happy_path`: Applies for CL from 2026-11-02 to 2026-11-03 (Monday..Tuesday). Days charged is 2.0. Status is "awaiting_unit_head". An audit transition record is created.
2. `test_apply_with_substitute`: If substitute_user_id is given, initial status is "awaiting_substitute".
3. `test_apply_applicant_director`: If applicant_is_director=True, initial status is "awaiting_director_self_sanction".
4. `test_apply_end_before_start_raises`: end_date < start_date raises ConflictError.
5. `test_apply_overlap_raises`: applying for dates overlapping an existing active application raises ConflictError.
6. `test_apply_insufficient_balance_raises`: applying for 5 days when balance is only 2 days raises ConflictError.
7. `test_transition_unit_head_approve_cl_deducts_balance`:
   Unit head approves CL application in "awaiting_unit_head". Status becomes "approved". Balance is deducted (8.0 - 2.0 = 6.0). Application's `balance_deducted` is recorded as 2.0.
8. `test_transition_unit_head_reject_requires_reason`:
   Unit head rejects without reason raises ConflictError ("has_reason" guard). With reason, status becomes "rejected", balance is NOT deducted.
9. `test_transition_substitute_accept_and_decline`:
   Substitute accepts -> status moves to "awaiting_unit_head", substitute_response becomes "accepted".
   Substitute declines with reason -> status moves to "applicant_action_required", substitute_response becomes "declined".
10. `test_transition_withdraw_pending`:
    Employee withdraws application from "awaiting_unit_head" with reason. Status becomes "withdrawn", withdrawn_reason is set.
11. `test_transition_cancellation_restores_balance`:
    Approved CL leave (2.0 days deducted) cancelled before start date:
    - Employee requests cancellation: status moves to "cancellation_pending_unit_head".
    - Unit head approves cancellation: status moves to "cancelled".
    - Balance is restored back (+2.0 days), balance_deducted becomes 0.
12. `test_transition_unauthorized_actor_raises`:
    Employee attempting to approve raises PermissionDeniedError.
    User without required permission raises PermissionDeniedError.

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs. Max line length 100.
