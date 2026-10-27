# Task: write modules/leave/tests/test_api.py (output the COMPLETE file)

Context:
Pattern to follow: `modules/placement/tests/test_api.py`.
Client: `from rest_framework.test import APIClient`.
Fixtures available globally from `conftest.py`: `stub_iam`, `make_session`.
Database mark: `pytestmark = pytest.mark.django_db`.
Models: `LeaveCategory`, `LeaveApplication`, `LeaveBalance` from `modules.leave.models`.

## Client helper
```python
def _client(stub_iam, **kw):
    defaults = {
        "user_id": 1,
        "modules": ("leave_management",),
        "permissions": (
            "leave_management.application.view_self",
            "leave_management.application.create",
            "leave_management.application.view",
            "leave_management.application.review",
            "leave_management.application.delete",
            "leave_management.application.respond",
            "leave_management.balance.view",
        ),
    }
    defaults.update(kw)
    stub_iam(make_session(**defaults))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c
```

## Required Tests

1. `test_categories_endpoint`:
   Create a LeaveCategory ("CL", "Casual Leave").
   Client with module "leave_management" and permission "leave_management.application.view_self" gets `/api/v1/leave/categories`.
   Status code is 200, json length is at least 1.

2. `test_balances_endpoint_scopes_to_own`:
   Create CL category. Create balance for user 1 (8.0 days) and user 2 (8.0 days).
   Client authenticated as user 1 with permission "leave_management.balance.view" (without view-all) gets `/api/v1/leave/balances`.
   Status is 200. Only user 1's balance is returned.

3. `test_apply_endpoint_success`:
   Create CL category and balance for user 1.
   Client as user 1 posts to `/api/v1/leave/applications/apply` with payload:
   `{"category_code": "CL", "start_date": "2026-11-02", "end_date": "2026-11-03", "reason": "Personal work"}`
   Status is 201 Created. Response json has "status" == "awaiting_unit_head".

4. `test_apply_endpoint_invalid_dates`:
   Client as user 1 posts to `/api/v1/leave/applications/apply` with `end_date < start_date`.
   Status is 409 Conflict.

5. `test_applications_list_and_detail`:
   Create CL app for user 1 and user 2.
   Client as user 1 gets `/api/v1/leave/applications`. Only user 1's app is returned.
   Client as user 1 gets `/api/v1/leave/applications/{user_1_app_id}` -> 200 OK.
   Client as user 1 gets `/api/v1/leave/applications/{user_2_app_id}` -> 404 Not Found (ownership scoped).

6. `test_transition_endpoint_approve`:
   Create CL app for user 1 in "awaiting_unit_head". Create balance for user 1 (8.0 days).
   Client authenticated as reviewer (user_id=2, permission "leave_management.application.review") posts to `/api/v1/leave/applications/{app.id}/transition` with payload:
   `{"to_status": "approved", "reason": "Approved by HOD"}`
   Status is 200 OK. Response json status is "approved".

7. `test_application_history`:
   Create CL app with a transition.
   Client as user 1 gets `/api/v1/leave/applications/{app.id}/history`.
   Status is 200 OK. List of transitions is returned.

8. `test_unauthenticated_request_rejected`:
   Client without credentials gets `/api/v1/leave/categories`.
   Status is 401 Unauthorized.

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
