"""The HTTP surface: who can do what, and what happens to the balance."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveBalance, LeaveRequest

pytestmark = pytest.mark.django_db

EMPLOYEE = ("leave.request.view_self", "leave.request.create", "leave.request.delete")
UNIT_HEAD = (*EMPLOYEE, "leave.request.view", "leave.request.review")
SANCTIONING = (*EMPLOYEE, "leave.request.view", "leave.request.approve")


def client_for(stub_iam, user_id, perms, kind="staff"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("leave",),
                          permissions=perms, roles=(kind,), active_role=kind))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def apply(c, **kw):
    body = {"category": "CL", "start_date": "2026-11-02", "end_date": "2026-11-03",
            "reason": "Family function", **kw}
    return c.post("/api/v1/elm/requests/apply", body, format="json")


def test_employee_applies_and_sees_it_pending(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE)
    r = apply(c)
    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "pending"
    assert Decimal(r.json()["days"]) == 2
    assert r.json()["allowed_transitions"] == ["withdrawn"]


def test_without_the_module_grant_everything_is_403(stub_iam):
    stub_iam(make_session(user_id=1001, kind="staff", modules=(), permissions=EMPLOYEE))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert apply(c).status_code == 403


def test_students_are_refused(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE, kind="student")
    r = apply(c)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "ineligible_category"


def test_overlap_is_refused(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE)
    assert apply(c).status_code == 201
    r = apply(c, start_date="2026-11-03", end_date="2026-11-04")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "overlapping_leave"


def test_pending_requests_cannot_overspend_the_balance(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE)
    assert apply(c, start_date="2026-11-02", end_date="2026-11-06").status_code == 201  # 5
    r = apply(c, start_date="2026-11-09", end_date="2026-11-12")                         # 4 > 3
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "insufficient_balance"


def test_employees_see_only_their_own_requests(stub_iam):
    LeaveRequest.objects.create(applicant_user_id=2002, category="CL", days=1,
                                start_date="2026-11-02", end_date="2026-11-02",
                                reason="x")
    c = client_for(stub_iam, 1001, EMPLOYEE)
    apply(c)
    rows = c.get("/api/v1/elm/requests").json()["results"]
    assert [r["applicant_user_id"] for r in rows] == [1001]


def test_a_foreign_request_is_404(stub_iam):
    other = LeaveRequest.objects.create(applicant_user_id=2002, category="CL", days=1,
                                        start_date="2026-11-02", end_date="2026-11-02",
                                        reason="x")
    c = client_for(stub_iam, 1001, EMPLOYEE)
    assert c.get(f"/api/v1/elm/requests/{other.pk}").status_code == 404
    r = c.post(f"/api/v1/elm/requests/{other.pk}/transition",
               {"to_status": "withdrawn"}, format="json")
    assert r.status_code == 404


def test_unit_head_approves_casual_leave_and_balance_is_spent(stub_iam):
    req_id = apply(client_for(stub_iam, 1001, EMPLOYEE)).json()["id"]

    head = client_for(stub_iam, 9, UNIT_HEAD, kind="faculty")
    r = head.post(f"/api/v1/elm/requests/{req_id}/transition",
                  {"to_status": "approved", "remarks": "OK"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["status"] == "approved"
    assert [h["to_status"] for h in r.json()["history"]] == ["pending", "approved"]
    assert LeaveBalance.objects.get(user_id=1001, category="CL").availed == 2


def test_earned_leave_goes_through_recommendation_then_sanction(stub_iam):
    req_id = apply(client_for(stub_iam, 1001, EMPLOYEE), category="EL").json()["id"]
    url = f"/api/v1/elm/requests/{req_id}/transition"

    head = client_for(stub_iam, 9, UNIT_HEAD, kind="faculty")
    assert head.post(url, {"to_status": "approved"}, format="json").status_code == 409
    assert head.post(url, {"to_status": "not_recommended"},
                     format="json").json()["status"] == "not_recommended"

    registrar = client_for(stub_iam, 7, SANCTIONING)
    assert registrar.post(url, {"to_status": "approved"},
                          format="json").json()["status"] == "approved"


def test_nobody_approves_their_own_leave(stub_iam):
    c = client_for(stub_iam, 9, UNIT_HEAD, kind="faculty")
    req_id = apply(c).json()["id"]
    r = c.post(f"/api/v1/elm/requests/{req_id}/transition",
               {"to_status": "approved"}, format="json")
    assert r.status_code == 403


def test_withdrawal_frees_the_reserved_days_and_is_final(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE)
    req_id = apply(c, start_date="2026-11-02", end_date="2026-11-06").json()["id"]
    url = f"/api/v1/elm/requests/{req_id}/transition"
    assert c.post(url, {"to_status": "withdrawn"}, format="json").status_code == 200

    head = client_for(stub_iam, 9, UNIT_HEAD, kind="faculty")
    assert head.post(url, {"to_status": "approved"}, format="json").status_code == 409

    c = client_for(stub_iam, 1001, EMPLOYEE)
    cl = next(b for b in c.get("/api/v1/elm/balances?year=2026").json()
              if b["category"] == "CL")
    assert Decimal(cl["available"]) == 8


def test_station_leave_details_are_required(stub_iam):
    c = client_for(stub_iam, 1001, EMPLOYEE)
    r = apply(c, is_station_leave=True, station_address="Bhopal")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "missing_station_details"
    r = apply(c, is_station_leave=True, station_address="Bhopal",
              station_contact="9876543210")
    assert r.status_code == 201


def test_balances_hide_categories_the_employee_does_not_hold(stub_iam):
    staff = client_for(stub_iam, 1001, EMPLOYEE).get("/api/v1/elm/balances?year=2026").json()
    assert "VL" not in [b["category"] for b in staff]
    faculty = client_for(stub_iam, 1002, EMPLOYEE, kind="faculty").get(
        "/api/v1/elm/balances?year=2026").json()
    assert "VL" in [b["category"] for b in faculty]
    assert "EL" not in [b["category"] for b in faculty]
