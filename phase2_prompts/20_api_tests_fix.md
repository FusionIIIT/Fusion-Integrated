# Task: Fix modules/leave/tests/test_api.py (output the COMPLETE file)

Context:
In Django DRF views for Leave (`modules/leave/api/views.py`), list views return raw JSON lists (e.g. `response.json()` is a `list`, NOT a dictionary with `"results"`).
So check `len(response.json())` and index `response.json()[0]`.

Model fields in `modules/leave/models.py`:
1. `LeaveBalance`:
   Fields are `user_id`, `category`, `year`, `balance_days`. (Do NOT use `balance=8.0`, use `balance_days=8.0, year=2026`).
2. `LeaveApplication`:
   Required fields: `user_id`, `category`, `start_date=date(2026, 11, 2)`, `end_date=date(2026, 11, 3)`, `reason="Personal work"`, `status="awaiting_unit_head"`.

Client helper:
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

Test specifics:
1. `test_categories_endpoint`:
   `LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `c = _client(stub_iam)`
   `response = c.get("/api/v1/leave/categories")`
   `assert response.status_code == 200`
   `assert len(response.json()) >= 1`

2. `test_balances_endpoint_scopes_to_own`:
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)`
   `LeaveBalance.objects.create(user_id=2, category=cl, year=2026, balance_days=8.0)`
   Client authenticated as user 1 with ONLY permission "leave_management.application.view_self" (so `actor.has_permission("leave_management.balance.view")` is False):
   `c = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))`
   `response = c.get("/api/v1/leave/balances")`
   `assert response.status_code == 200`
   `data = response.json()`
   `assert len(data) == 1`
   `assert data[0]["user_id"] == 1`

3. `test_apply_endpoint_success`:
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)`
   `c = _client(stub_iam, user_id=1)`
   `payload = {"category_code": "CL", "start_date": "2026-11-02", "end_date": "2026-11-03", "reason": "Personal work"}`
   `response = c.post("/api/v1/leave/applications/apply", data=payload)`
   `assert response.status_code == 201`
   `assert response.json()["status"] == "awaiting_unit_head"`

4. `test_apply_endpoint_invalid_dates`:
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)`
   `c = _client(stub_iam, user_id=1)`
   `payload = {"category_code": "CL", "start_date": "2026-11-03", "end_date": "2026-11-02", "reason": "Invalid dates"}`
   `response = c.post("/api/v1/leave/applications/apply", data=payload)`
   `assert response.status_code == 409`

5. `test_applications_list_and_detail`:
   `from datetime import date`
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `app1 = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Work 1", status="awaiting_unit_head")`
   `app2 = LeaveApplication.objects.create(user_id=2, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Work 2", status="awaiting_unit_head")`
   Client as user 1 with permission "leave_management.application.view_self" (without "view"):
   `c1 = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))`
   `resp_list = c1.get("/api/v1/leave/applications")`
   `assert resp_list.status_code == 200`
   `assert len(resp_list.json()) == 1`
   `assert resp_list.json()[0]["id"] == app1.id`
   `resp_detail_own = c1.get(f"/api/v1/leave/applications/{app1.id}")`
   `assert resp_detail_own.status_code == 200`
   `resp_detail_other = c1.get(f"/api/v1/leave/applications/{app2.id}")`
   `assert resp_detail_other.status_code == 404`

6. `test_transition_endpoint_approve`:
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)`
   `app = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Personal", status="awaiting_unit_head")`
   Client authenticated as reviewer (user_id=2, role="unit_head" / review permission):
   `c = _client(stub_iam, user_id=2, permissions=("leave_management.application.review", "leave_management.application.view"))`
   `payload = {"to_status": "approved", "reason": "Approved by HOD"}`
   `response = c.post(f"/api/v1/leave/applications/{app.id}/transition", data=payload)`
   `assert response.status_code == 200`
   `assert response.json()["status"] == "approved"`

7. `test_application_history`:
   `from modules.leave.models import LeaveApplicationTransition`
   `cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")`
   `app = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Personal", status="approved")`
   `LeaveApplicationTransition.objects.create(application=app, from_status="awaiting_unit_head", to_status="approved", actor_user_id=2, reason="Approved")`
   `c1 = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))`
   `response = c1.get(f"/api/v1/leave/applications/{app.id}/history")`
   `assert response.status_code == 200`
   `assert len(response.json()) >= 1`

8. `test_unauthenticated_request_rejected`:
   `c = APIClient()`
   `response = c.get("/api/v1/leave/categories")`
   `assert response.status_code == 401`

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
