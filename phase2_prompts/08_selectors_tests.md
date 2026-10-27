# Task: write pytest tests for leave selectors in modules/leave/tests/test_selectors.py

Context:
Pattern to follow: `modules/placement/selectors/applications.py` and its test conventions.
Selectors module to test: `modules/leave/selectors/applications.py`.
Models: `modules.leave.models` (`LeaveCategory`, `LeaveApplication`, `LeaveBalance`).
Database: pytest with `@pytest.mark.django_db`.

## Functions under test
From `modules.leave.selectors.applications`:
1. `applications_for(actor)` -> returns `QuerySet[LeaveApplication]`.
   - If `actor.has_permission("leave_management.application.view")` is True: returns all applications.
   - If actor does not have that permission: returns applications where `user_id == actor.user_id` or `substitute_user_id == actor.user_id`.
   - If actor has no `user_id`: returns `LeaveApplication.objects.none()`.
2. `balances_for(actor)` -> returns `QuerySet[LeaveBalance]`.
   - If `actor.has_permission("leave_management.balance.view")` or `actor.has_permission("leave_management.balance.manage")`: returns all balances.
   - Otherwise: returns balances where `user_id == actor.user_id`.
   - If actor has no `user_id`: returns `LeaveBalance.objects.none()`.

## Fixture / Helper
Create a small helper class or fixture `Principal`:
```python
class DummyPrincipal:
    def __init__(self, user_id=None, permissions=()):
        self.user_id = user_id
        self.permissions = set(permissions)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions
```

## Required tests
1. `test_applications_for_own_only`: Employee with user_id=1 (no admin perm) sees only their own application, not user_id=2's.
2. `test_applications_for_substitute`: Employee with user_id=3 sees application where substitute_user_id=3 even though applicant user_id=1.
3. `test_applications_for_reviewer_sees_all`: Principal with "leave_management.application.view" sees all applications across users.
4. `test_applications_for_anonymous_none`: Principal with user_id=None returns empty queryset.
5. `test_balances_for_own_only`: Employee with user_id=1 sees only their own balance.
6. `test_balances_for_manager_sees_all`: Principal with "leave_management.balance.view" or "leave_management.balance.manage" sees all balances.
7. `test_balances_for_anonymous_none`: Principal with user_id=None returns empty queryset.

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
