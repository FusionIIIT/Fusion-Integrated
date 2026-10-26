"""Integration tests for ELM API endpoints and workflow lifecycles."""
from datetime import date
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.contracts import get_active_leaves, get_user_balances
from modules.elm.models.balances import LeaveBalance
from modules.elm.models.leaves import LeaveRequest
from modules.elm.services.balances import seed_default_balances


ALL_ELM_PERMISSIONS = (
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
    "elm.leave.review",
    "elm.leave.sanction",
    "elm.leave.admin",
)


def _client(stub_iam, user_id=101, permissions=ALL_ELM_PERMISSIONS):
    stub_iam(make_session(user_id=user_id, permissions=permissions, modules=("elm",), kind="staff"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.mark.django_db
def test_seed_and_retrieve_balances(stub_iam):
    """Verify default balance seeding and endpoint retrieval."""
    user_id = 101
    c = _client(stub_iam, user_id=user_id)
    res = c.get(f"/api/v1/elm/balances/?year=2026")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 6
    cl = next(b for b in data if b["category"] == "CL")
    assert Decimal(cl["available_balance"]) == Decimal("8.00")


@pytest.mark.django_db
def test_apply_for_casual_leave_success(stub_iam):
    """Submit a valid 1-day casual leave application."""
    user_id = 102
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    # Use a weekday
    payload = {
        "category": "CL",
        "start_date": "2026-11-04",
        "end_date": "2026-11-04",
        "reason": "Personal urgent work at bank",
        "is_half_day": False,
    }
    res = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "CL"
    assert data["status"] == "awaiting_unit_head"
    assert Decimal(data["days_calculated"]) == Decimal("1.00")


@pytest.mark.django_db
def test_apply_with_substitute_workflow(stub_iam):
    """Leave requiring substitute moves to awaiting_substitute, then awaiting_unit_head upon acceptance."""
    applicant_id = 103
    substitute_id = 104
    unit_head_id = 105
    authority_id = 106

    seed_default_balances(applicant_id, 2026)

    # 1. Applicant submits
    c_app = _client(stub_iam, user_id=applicant_id)
    payload = {
        "category": "EL",
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "reason": "Attending family wedding",
        "substitute_user_id": substitute_id,
        "unit_head_user_id": unit_head_id,
        "sanctioning_authority_user_id": authority_id,
    }
    create_res = c_app.post("/api/v1/elm/leaves/", payload, format="json")
    assert create_res.status_code == 201
    leave_id = create_res.json()["id"]
    assert create_res.json()["status"] == "awaiting_substitute"

    # 2. Substitute checks queue and accepts
    c_sub = _client(stub_iam, user_id=substitute_id)
    queue_res = c_sub.get("/api/v1/elm/substitute/")
    assert queue_res.status_code == 200
    assert any(item["id"] == leave_id for item in queue_res.json())

    sub_res = c_sub.post(
        f"/api/v1/elm/substitute/{leave_id}/respond/",
        {"accepted": True, "remarks": "I will handle lab duties."},
        format="json",
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "awaiting_unit_head"

    # 3. Unit Head recommends
    c_uh = _client(stub_iam, user_id=unit_head_id)
    uh_res = c_uh.post(
        f"/api/v1/elm/unit-head/{leave_id}/review/",
        {"recommended": True, "remarks": "Recommended for approval."},
        format="json",
    )
    assert uh_res.status_code == 200
    assert uh_res.json()["status"] == "awaiting_sanction"

    # Check balance before sanction
    bal_before = LeaveBalance.objects.get(user_id=applicant_id, year=2026, category="EL")
    assert bal_before.availed_balance == Decimal("0.00")

    # 4. Authority sanctions (approves)
    c_auth = _client(stub_iam, user_id=authority_id)
    sanc_res = c_auth.post(
        f"/api/v1/elm/sanctions/{leave_id}/sanction/",
        {"approved": True, "remarks": "Approved."},
        format="json",
    )
    assert sanc_res.status_code == 200
    assert sanc_res.json()["status"] == "approved"

    # Check that balance was deducted atomically
    bal_after = LeaveBalance.objects.get(user_id=applicant_id, year=2026, category="EL")
    assert bal_after.availed_balance == Decimal("3.00")
    assert bal_after.available_balance == Decimal("27.00")

    # 5. Verify contract get_active_leaves
    active_map = get_active_leaves([applicant_id], on_date=date(2026, 11, 11))
    assert active_map[applicant_id].has_active_leave is True
    assert active_map[applicant_id].category == "EL"


@pytest.mark.django_db
def test_withdraw_leave_application(stub_iam):
    """Employee can withdraw an application that is still in review."""
    user_id = 107
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "CL",
        "start_date": "2026-11-20",
        "end_date": "2026-11-20",
        "reason": "Doctor appointment",
    }
    create_res = c.post("/api/v1/elm/leaves/", payload, format="json")
    leave_id = create_res.json()["id"]

    del_res = c.delete(f"/api/v1/elm/leaves/{leave_id}/")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "withdrawn"


@pytest.mark.django_db
def test_cancel_approved_leave_and_refund_balance(stub_iam):
    """Cancelling an approved leave before start_date refunds the quota."""
    user_id = 108
    authority_id = 109
    seed_default_balances(user_id, 2026)
    c_user = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "RH",
        "start_date": "2026-12-15",
        "end_date": "2026-12-15",
        "reason": "Restricted holiday festival",
    }
    create_res = c_user.post("/api/v1/elm/leaves/", payload, format="json")
    leave_id = create_res.json()["id"]

    # Unit head recommends first
    c_uh = _client(stub_iam, user_id=120)
    c_uh.post(
        f"/api/v1/elm/unit-head/{leave_id}/review/",
        {"recommended": True, "remarks": "Recommended."},
        format="json",
    )

    # Sanction by authority
    c_auth = _client(stub_iam, user_id=authority_id)
    c_auth.post(
        f"/api/v1/elm/sanctions/{leave_id}/sanction/",
        {"approved": True, "remarks": "Approved RH."},
        format="json",
    )

    bal_approved = LeaveBalance.objects.get(user_id=user_id, year=2026, category="RH")
    assert bal_approved.availed_balance == Decimal("1.00")

    # Restore applicant session before cancellation (stub_iam is global – last _client() wins)
    c_user = _client(stub_iam, user_id=user_id)

    # Now cancel prior to start date
    cancel_res = c_user.post(
        f"/api/v1/elm/leaves/{leave_id}/cancel/",
        {"remarks": "Plans changed, cancelling."},
        format="json",
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify balance was refunded
    bal_refunded = LeaveBalance.objects.get(user_id=user_id, year=2026, category="RH")
    assert bal_refunded.availed_balance == Decimal("0.00")
    assert bal_refunded.available_balance == Decimal("2.00")


@pytest.mark.django_db
def test_invalid_date_range_refusal(stub_iam):
    """End date prior to start date is rejected with 400 Bad Request."""
    user_id = 110
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "CL",
        "start_date": "2026-11-20",
        "end_date": "2026-11-15",
        "reason": "Inverted dates",
    }
    res = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_overlapping_leave_rejected(stub_iam):
    """Two applications covering the same dates must be rejected (BR-EL-012)."""
    user_id = 111
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "CL",
        "start_date": "2026-11-25",
        "end_date": "2026-11-26",
        "reason": "First application",
    }
    res1 = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res1.status_code == 201

    # Second application overlaps the first
    payload["reason"] = "Second application — should be rejected"
    res2 = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res2.status_code == 400


@pytest.mark.django_db
def test_ownership_enforced_on_withdraw(stub_iam):
    """A user cannot withdraw another user's leave application."""
    owner_id = 112
    intruder_id = 113
    seed_default_balances(owner_id, 2026)

    c_owner = _client(stub_iam, user_id=owner_id)
    payload = {
        "category": "CL",
        "start_date": "2026-12-01",
        "end_date": "2026-12-01",
        "reason": "Owner's leave",
    }
    create_res = c_owner.post("/api/v1/elm/leaves/", payload, format="json")
    leave_id = create_res.json()["id"]

    c_intruder = _client(stub_iam, user_id=intruder_id)
    del_res = c_intruder.delete(f"/api/v1/elm/leaves/{leave_id}/")
    assert del_res.status_code == 404   # 404 not 403 — don't leak existence


@pytest.mark.django_db
def test_station_leave_requires_address_and_phone(stub_iam):
    """Station leave must supply station_address and emergency_phone (serializer validation)."""
    user_id = 114
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "CL",
        "start_date": "2026-12-02",
        "end_date": "2026-12-02",
        "reason": "Conference trip",
        "leaving_station": True,
        # station_address and emergency_phone intentionally omitted
    }
    res = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_half_day_with_different_dates_rejected_by_serializer(stub_iam):
    """Serializer rejects half-day leave spanning multiple days before service is called."""
    user_id = 115
    seed_default_balances(user_id, 2026)
    c = _client(stub_iam, user_id=user_id)

    payload = {
        "category": "CL",
        "start_date": "2026-12-10",
        "end_date": "2026-12-11",
        "reason": "Half day but spans two days",
        "is_half_day": True,
        "half_day_period": "first_half",
    }
    res = c.post("/api/v1/elm/leaves/", payload, format="json")
    assert res.status_code == 400
