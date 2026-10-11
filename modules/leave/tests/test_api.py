import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    AuthorityRule,
    Calendar,
    CategoryRule,
    Holiday,
    LeaveRequest,
    LedgerEntry,
    Policy,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_setup():
    year = 2026
    cal = Calendar.objects.create(year=year, version="1.0", published=True)
    Holiday.objects.create(calendar=cal, day=datetime.date(year, 1, 26), name="Republic Day", restricted=False)

    policy = Policy.objects.create(
        version="2026.1",
        effective_from=datetime.date(year, 1, 1),
        effective_to=datetime.date(year, 12, 31),
        published=True,
    )

    CategoryRule.objects.create(
        policy=policy, category="CL", annual_credit=Decimal("8.0"), applies_to_faculty=True
    )
    CategoryRule.objects.create(
        policy=policy, category="EL", annual_credit=Decimal("30.0"), carries_forward=True, applies_to_faculty=True
    )

    AuthorityRule.objects.create(
        policy=policy, category="CL", sanctioning_designation="Unit Head", applies_to_faculty=True
    )
    AuthorityRule.objects.create(
        policy=policy, category="EL", establishment_step=True, sanctioning_designation="Dean", applies_to_faculty=True
    )

    LedgerEntry.objects.create(user_id=1001, year=year, category="CL", days=Decimal("8.0"), reason="initial")
    LedgerEntry.objects.create(user_id=1001, year=year, category="EL", days=Decimal("30.0"), reason="initial")

    return {"calendar": cal, "policy": policy}


def _auth_client(stub_iam, user_id=1001, permissions=(), modules=("leave",), role="faculty"):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="faculty",
            modules=modules,
            permissions=permissions,
            active_role=role,
            roles=(role,),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_two_gate_denial_without_module_grant(stub_iam, api_setup):
    # User holds permission but not module grant -> 403
    c = _auth_client(stub_iam, permissions=("leave.request.view_self",), modules=())
    resp = c.get("/api/v1/leave/me/requests")
    assert resp.status_code == 403


def test_two_gate_denial_without_permission(stub_iam, api_setup):
    # User holds module grant but lacks specific permission -> 403
    c = _auth_client(stub_iam, permissions=(), modules=("leave",))
    resp = c.get("/api/v1/leave/me/requests")
    assert resp.status_code == 403


def test_my_requests_and_balances(stub_iam, api_setup):
    user_id = 1001
    LeaveRequest.objects.create(
        user_id=user_id,
        category="CL",
        starts_on=datetime.date(2026, 1, 5),
        ends_on=datetime.date(2026, 1, 6),
        requested_days=Decimal("2.0"),
        reason="Family event",
        state=LeaveState.PENDING_REVIEW,
    )

    c = _auth_client(stub_iam, user_id=user_id, permissions=("leave.request.view_self",))

    # Test requests endpoint
    r_resp = c.get("/api/v1/leave/me/requests")
    assert r_resp.status_code == 200
    r_rows = r_resp.json()["results"] if isinstance(r_resp.json(), dict) else r_resp.json()
    assert len(r_rows) == 1
    assert r_rows[0]["category"] == "CL"

    # Test balances endpoint
    b_resp = c.get("/api/v1/leave/me/balances")
    assert b_resp.status_code == 200
    bal_data = {row["category"]: row["available"] for row in b_resp.json()}
    assert Decimal(bal_data["CL"]) == Decimal("8.0")


def test_apply_and_withdraw_leave_api(stub_iam, api_setup):
    user_id = 1001
    c = _auth_client(
        stub_iam,
        user_id=user_id,
        permissions=("leave.request.create", "leave.request.view_self", "leave.request.withdraw"),
    )

    # 1. Apply for leave
    apply_payload = {
        "category": "CL",
        "starts_on": "2026-01-05",
        "ends_on": "2026-01-06",
        "reason": "Personal work",
    }
    apply_resp = c.post("/api/v1/leave/requests", apply_payload, format="json")
    assert apply_resp.status_code == 201
    req_id = apply_resp.json()["id"]

    # 2. View detail
    detail_resp = c.get(f"/api/v1/leave/requests/{req_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["state"] == "pending_review"

    # 3. Withdraw
    withdraw_resp = c.post(
        f"/api/v1/leave/requests/{req_id}/withdraw",
        {"remark": "Plans changed"},
        format="json",
    )
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.json()["state"] == "withdrawn"


def test_substitute_nominations_api(stub_iam, api_setup):
    applicant_id = 1001
    substitute_id = 2002

    req = LeaveRequest.objects.create(
        user_id=applicant_id,
        category="EL",
        starts_on=datetime.date(2026, 2, 2),
        ends_on=datetime.date(2026, 2, 6),
        requested_days=Decimal("5.0"),
        reason="Research leave",
        substitute_user_id=substitute_id,
        state=LeaveState.SUBMITTED_PENDING_SUBSTITUTE,
    )

    # Substitute views nominations
    c = _auth_client(stub_iam, user_id=substitute_id, permissions=("leave.substitute.respond",))
    noms_resp = c.get("/api/v1/leave/nominations")
    assert noms_resp.status_code == 200
    noms_rows = noms_resp.json()["results"] if isinstance(noms_resp.json(), dict) else noms_resp.json()
    assert len(noms_rows) == 1
    assert noms_rows[0]["id"] == req.id

    # Substitute accepts
    resp = c.post(
        f"/api/v1/leave/nominations/{req.id}/respond",
        {"accepted": True, "remark": "Covering duties"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "pending_review"


def test_review_and_sanction_queues_api(stub_iam, api_setup):
    applicant_id = 1001

    req = LeaveRequest.objects.create(
        user_id=applicant_id,
        category="CL",
        starts_on=datetime.date(2026, 1, 5),
        ends_on=datetime.date(2026, 1, 6),
        requested_days=Decimal("2.0"),
        reason="Personal",
        state=LeaveState.PENDING_REVIEW,
    )

    # Unit head reviews
    c_uh = _auth_client(stub_iam, user_id=900, permissions=("leave.request.review",), role="Unit Head")
    rev_resp = c_uh.get("/api/v1/leave/review")
    assert rev_resp.status_code == 200
    rev_rows = rev_resp.json()["results"] if isinstance(rev_resp.json(), dict) else rev_resp.json()
    assert len(rev_rows) == 1

    dec_resp = c_uh.post(
        f"/api/v1/leave/review/{req.id}",
        {"approve": True, "remark": "Sanctioned by Unit Head"},
        format="json",
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["state"] == "approved"


def test_admin_policy_and_calendar_api(stub_iam, api_setup):
    c_admin = _auth_client(
        stub_iam,
        user_id=1,
        permissions=("leave.policy.manage", "leave.calendar.manage"),
        role="Admin",
    )

    p_resp = c_admin.get("/api/v1/leave/admin/policies")
    assert p_resp.status_code == 200
    p_rows = p_resp.json()["results"] if isinstance(p_resp.json(), dict) else p_resp.json()
    assert len(p_rows) >= 1

    c_resp = c_admin.get("/api/v1/leave/admin/calendars")
    assert c_resp.status_code == 200
    c_rows = c_resp.json()["results"] if isinstance(c_resp.json(), dict) else c_resp.json()
    assert len(c_rows) >= 1
