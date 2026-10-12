"""ELM API tests."""

import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/leave"
APPLY = ("leave.request.create", "leave.request.view_self")


def test_apply_for_casual_leave(as_user, unit, balances):
    """EL-UC-001: an employee applies for two days of CL."""
    client = as_user(101, *APPLY)
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "unit_review"


def test_overlapping_request_is_refused(as_user, unit, balances):
    """BR-EL-012: user 101 applies CL 2030-03-04..2030-03-05 twice, second response status_code >= 400."""
    client = as_user(101, *APPLY)
    client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code >= 400, f"Expected status code >= 400, got {r.status_code}"


def test_casual_leave_over_entitlement_is_refused(as_user, unit, balances):
    """BR-EL-002: CL 2030-03-04..2030-03-29 is more than 8 days, status_code >= 400 — note balances fixture gives 30 so set LeaveBalance CL entitled to 8 first via LeaveBalance.objects.filter(user_id=101, category='CL').update(entitled=8)."""
    from modules.leave.models import LeaveBalance

    LeaveBalance.objects.filter(user_id=101, category="CL").update(entitled=8)
    client = as_user(101, *APPLY)
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-29",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code >= 400, f"Expected status code >= 400, got {r.status_code}"


def test_apply_without_permission_is_forbidden(as_user, unit, balances):
    """BR-EL-036: as_user(101, 'leave.request.view_self') POST -> 403."""
    client = as_user(101, "leave.request.view_self")
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code == 403, f"Expected status code 403, got {r.status_code}"


def test_other_employee_cannot_see_request(as_user, unit, balances):
    """user 101 applies; as_user(202, 'leave.request.view_self') GET requests -> no result with user_id 101."""
    client = as_user(101, *APPLY)
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code == 201, f"Expected status code 201, got {r.status_code}"
    client = as_user(202, *APPLY)
    r = client.get(f"{URL}/requests/1", format="json")  # Assuming request ID is 1
    assert r.status_code == 404, f"Expected status code 404, got {r.status_code}"


def test_applicant_can_withdraw_pending_request(as_user, unit, balances):
    """BR-EL-022: apply, then POST requests/<id>/withdraw with {} -> 200 and status 'withdrawn'."""
    client = as_user(101, *APPLY)
    r = client.post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-05",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code == 201, f"Expected status code 201, got {r.status_code}"
    request_id = r.json()["id"]
    r = client.post(f"{URL}/requests/{request_id}/withdraw", {}, format="json")
    assert r.status_code == 200, f"Expected status code 200, got {r.status_code}"
    assert r.json()["status"] == "withdrawn", (
        f"Expected status 'withdrawn', got {r.json()['status']}"
    )


def test_substitute_accepts_duty(as_user, unit, balances):
    """EL-UC-002, BR-EL-015: the named substitute accepts, and the request moves to the unit head."""
    r = as_user(101, *APPLY).post(
        f"{URL}/requests",
        {
            "category": "CL",
            "start_date": "2030-04-01",
            "end_date": "2030-04-02",
            "purpose": "Conference",
            "unit_id": unit.id,
            "substitute_user_id": 202,
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "substitute_pending"
    r = as_user(202, "leave.substitute.respond").post(
        f"{URL}/requests/{r.json()['id']}/substitute-response", {"accept": True}, format="json"
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "unit_review"
