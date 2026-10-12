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


def test_unit_head_approves_casual_leave(as_user, unit, balances):
    """BR-EL-016: user 101 applies CL; as_user(500, 'leave.request.review') POSTs requests/<id>/review {'outcome': 'approve'} -> 200 and status 'approved'."""
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
    request_id = r.json()["id"]

    client = as_user(500, "leave.request.review")
    r = client.post(f"{URL}/requests/{request_id}/review", {"outcome": "approve"}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "approved"


def test_earned_leave_goes_through_routing_and_sanction(as_user, unit, balances):
    """BR-EL-017/018: user 101 applies EL 2030-03-04..2030-03-08; unit head 500 posts review {'outcome': 'recommend'} -> status 'routing'; as_user(600, 'leave.request.route') posts requests/<id>/route {} -> status 'sanction'; as_user(700, 'leave.request.sanction') posts requests/<id>/sanction {'decision': 'approve'} -> status 'approved'."""
    client = as_user(101, *APPLY)
    r = client.post(
        f"{URL}/requests",
        {
            "category": "EL",
            "start_date": "2030-03-04",
            "end_date": "2030-03-08",
            "purpose": "Family function",
            "unit_id": unit.id,
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    request_id = r.json()["id"]

    client = as_user(500, "leave.request.review")
    r = client.post(f"{URL}/requests/{request_id}/review", {"outcome": "recommend"}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "routing"

    client = as_user(600, "leave.request.route")
    r = client.post(f"{URL}/requests/{request_id}/route", {}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "sanction"

    client = as_user(700, "leave.request.sanction")
    r = client.post(f"{URL}/requests/{request_id}/sanction", {"decision": "approve"}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "approved"


def test_unit_head_of_other_unit_cannot_review(as_user, unit, balances):
    """BR-EL-036: as_user(999, 'leave.request.review') review -> status_code 404."""
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
    request_id = r.json()["id"]

    client = as_user(999, "leave.request.review")
    r = client.post(f"{URL}/requests/{request_id}/review", {"outcome": "approve"}, format="json")
    assert r.status_code == 404, r.content
