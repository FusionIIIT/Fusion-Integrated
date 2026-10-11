"""End-to-end flows through the HTTP layer, with the IAM faked."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.elm import registry
from modules.elm.models import (
    LeaveRequest,
    LedgerEntry,
    Notification,
    SanctionRoute,
    UnitHead,
)

pytestmark = pytest.mark.django_db

EMPLOYEE = ("elm.leave_request.view", "elm.leave_request.create")
UNIT_HEAD = ("elm.leave_task.view", "elm.leave_request.review")
AUTHORITY = ("elm.leave_task.view", "elm.leave_request.approve")
ESTABLISHMENT = ("elm.leave_task.view", "elm.leave_request.assign",
                 "elm.leave_request.approve")
ADMIN = ("elm.policy.update", "elm.holiday_calendar.publish",
         "elm.leave_record.create")

STAFF, FACULTY, HEAD, SUB, DR, REG, OTHER = 501, 502, 503, 504, 505, 506, 507
PEOPLE = {
    STAFF: ("staff", "Office"), FACULTY: ("faculty", "CSE"),
    HEAD: ("faculty", "CSE"), SUB: ("faculty", "CSE"),
    DR: ("staff", "Establishment"), REG: ("staff", "Registry"),
    OTHER: ("staff", "Office"),
}
USERS = {uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                      kind=kind, department=dept)
         for uid, (kind, dept) in PEOPLE.items()}


def monday(weeks=2):
    d = date.today() + timedelta(weeks=weeks)
    return d - timedelta(days=d.weekday())


@pytest.fixture
def as_user(stub_iam):
    def _as(uid, perms, roles=None, modules=("elm",)):
        kind = PEOPLE.get(uid, ("staff", ""))[0]
        stub_iam(make_session(user_id=uid, kind=kind, permissions=perms,
                              modules=modules, roles=roles or (kind,),
                              active_role=(roles or (kind,))[0]),
                 users=USERS)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client
    return _as


@pytest.fixture
def hierarchy():
    UnitHead.objects.create(unit="CSE", head_user_id=HEAD)
    UnitHead.objects.create(unit="Office", head_user_id=HEAD)
    for kind in ("faculty", "staff"):
        for cat in ("SCL", "EL", "COL", "VL"):
            SanctionRoute.objects.create(category=cat, applicant_kind=kind,
                                         authority_user_id=REG)


def _apply(client, **body):
    return client.post("/api/v1/elm/requests", body, format="json")


def test_registry_declares_every_permission_these_tests_use():
    declared = {code for code, _ in registry.PERMISSIONS}
    assert set(EMPLOYEE + UNIT_HEAD + AUTHORITY + ESTABLISHMENT + ADMIN) <= declared
    for codes in registry.ROLE_GRANTS.values():
        assert set(codes) <= declared


def test_plain_employee_sees_entitlement(as_user):
    r = as_user(STAFF, EMPLOYEE).get("/api/v1/elm/balances")
    assert r.status_code == 200
    assert Decimal(r.json()["balances"]["CL"]) == 8
    assert Decimal(r.json()["balances"]["EL"]) == 30
    assert Decimal(r.json()["balances"]["VL"]) == 0


def test_cl_unit_head_approves_and_balance_is_debited(as_user, hierarchy):
    start = monday()
    r = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
               end_date=start + timedelta(days=1), purpose="Family function")
    assert r.status_code == 201, r.json()
    req = r.json()
    assert req["state"] == "awaiting_unit_head" and req["assignee_id"] == HEAD
    assert Decimal(req["days"]) == 2

    head = as_user(HEAD, UNIT_HEAD)
    assert [t["id"] for t in head.get("/api/v1/elm/tasks").json()["results"]] \
        == [req["id"]]
    r = head.post(f"/api/v1/elm/tasks/{req['id']}/decide",
                  {"outcome": "approve"}, format="json")
    assert r.status_code == 200 and r.json()["state"] == "approved"
    bal = as_user(STAFF, EMPLOYEE).get("/api/v1/elm/balances").json()
    assert Decimal(bal["balances"]["CL"]) == 6
    assert Notification.objects.filter(user_id=STAFF).exists()


def test_el_needs_recommendation_then_sanction(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="EL", start_date=start,
                 end_date=start + timedelta(days=6)).json()
    head = as_user(HEAD, UNIT_HEAD)
    r = head.post(f"/api/v1/elm/tasks/{req['id']}/decide",
                  {"outcome": "approve"}, format="json")
    assert r.status_code == 409
    r = head.post(f"/api/v1/elm/tasks/{req['id']}/decide",
                  {"outcome": "not_recommended"}, format="json")
    assert r.json()["state"] == "awaiting_sanction"
    assert r.json()["assignee_id"] == REG
    r = as_user(REG, AUTHORITY).post(f"/api/v1/elm/tasks/{req['id']}/decide",
                                     {"outcome": "approve"}, format="json")
    assert r.json()["state"] == "approved"
    assert LedgerEntry.objects.get(request_id=req["id"]).days == Decimal(-7)


def test_establishment_step_when_configured(as_user, hierarchy):
    SanctionRoute.objects.filter(category="SCL", applicant_kind="staff").update(
        establishment_user_id=DR)
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="SCL", start_date=start,
                 end_date=start).json()
    r = as_user(HEAD, UNIT_HEAD).post(f"/api/v1/elm/tasks/{req['id']}/decide",
                                      {"outcome": "recommended"}, format="json")
    assert r.json()["state"] == "awaiting_establishment"
    r = as_user(DR, ESTABLISHMENT).post(f"/api/v1/elm/tasks/{req['id']}/decide",
                                        {"outcome": "forward"}, format="json")
    assert r.json()["state"] == "awaiting_sanction"


def test_substitute_decline_then_replacement(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(FACULTY, EMPLOYEE), category="CL", start_date=start,
                 end_date=start, substitute_id=SUB).json()
    assert req["state"] == "awaiting_substitute"
    sub = as_user(SUB, EMPLOYEE)
    assert len(sub.get("/api/v1/elm/substitute-requests").json()["results"]) == 1
    r = sub.post(f"/api/v1/elm/substitute-requests/{req['id']}/respond",
                 {"accept": False}, format="json")
    assert r.json()["state"] == "applicant_action_required"
    r = sub.post(f"/api/v1/elm/substitute-requests/{req['id']}/respond",
                 {"accept": True}, format="json")
    assert r.json()["error"]["code"] == "stale_response"
    r = as_user(FACULTY, EMPLOYEE).post(
        f"/api/v1/elm/requests/{req['id']}/substitute", {"substitute_id": OTHER},
        format="json")
    assert r.json()["state"] == "awaiting_substitute"
    r = as_user(OTHER, EMPLOYEE).post(
        f"/api/v1/elm/substitute-requests/{req['id']}/respond", {"accept": True},
        format="json")
    assert r.json()["state"] == "awaiting_unit_head"


def test_substitute_cannot_be_self_or_on_leave(as_user, hierarchy):
    start = monday()
    client = as_user(FACULTY, EMPLOYEE)
    r = _apply(client, category="CL", start_date=start, end_date=start,
               substitute_id=FACULTY)
    assert r.json()["error"]["code"] == "substitute_is_applicant"
    _apply(as_user(SUB, EMPLOYEE), category="CL", start_date=start, end_date=start)
    r = _apply(as_user(FACULTY, EMPLOYEE), category="CL", start_date=start,
               end_date=start, substitute_id=SUB)
    assert r.json()["error"]["code"] == "substitute_unavailable"


def test_overlap_refused_but_other_cl_half_allowed(as_user, hierarchy):
    start = monday()
    client = as_user(STAFF, EMPLOYEE)
    assert _apply(client, category="CL", start_date=start, end_date=start,
                  half="first").status_code == 201
    assert _apply(client, category="CL", start_date=start, end_date=start,
                  half="second").status_code == 201
    r = _apply(client, category="CL", start_date=start, end_date=start)
    assert r.json()["error"]["code"] == "overlap"


def test_pending_requests_reserve_balance(as_user, hierarchy):
    start = monday()
    client = as_user(STAFF, EMPLOYEE)
    assert _apply(client, category="RH", start_date=start, end_date=start
                  ).json()["error"]["code"] == "not_restricted_holiday"
    r = _apply(client, category="CL", start_date=start,
               end_date=start + timedelta(days=11))
    assert r.json()["error"]["code"] == "insufficient_balance"


def test_withdraw_stops_further_decisions(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
                 end_date=start).json()
    r = as_user(STAFF, EMPLOYEE).post(f"/api/v1/elm/requests/{req['id']}/withdraw")
    assert r.json()["state"] == "withdrawn"
    r = as_user(HEAD, UNIT_HEAD).post(f"/api/v1/elm/tasks/{req['id']}/decide",
                                      {"outcome": "approve"}, format="json")
    assert r.status_code == 404
    assert Notification.objects.filter(user_id=HEAD, request_id=req["id"]).count() == 2


def test_cancellation_restores_balance(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
                 end_date=start).json()
    head = as_user(HEAD, UNIT_HEAD)
    head.post(f"/api/v1/elm/tasks/{req['id']}/decide", {"outcome": "approve"},
              format="json")
    r = as_user(STAFF, EMPLOYEE).post(f"/api/v1/elm/requests/{req['id']}/withdraw")
    assert r.status_code == 409
    canc = as_user(STAFF, EMPLOYEE).post(
        f"/api/v1/elm/requests/{req['id']}/cancel", {"reason": "Plans changed"},
        format="json").json()
    assert canc["kind"] == "cancellation" and canc["assignee_id"] == HEAD
    as_user(HEAD, UNIT_HEAD).post(f"/api/v1/elm/tasks/{canc['id']}/decide",
                                  {"outcome": "approve"}, format="json")
    assert LeaveRequest.objects.get(pk=req["id"]).state == "cancelled"
    bal = as_user(STAFF, EMPLOYEE).get("/api/v1/elm/balances").json()
    assert Decimal(bal["balances"]["CL"]) == 8


def test_director_self_sanctions(as_user, hierarchy):
    start = monday()
    client = as_user(FACULTY, EMPLOYEE, roles=("faculty", "Director"))
    req = _apply(client, category="EL", start_date=start, end_date=start)
    assert req.json()["error"]["code"] == "insufficient_balance"
    req = _apply(client, category="COL", start_date=start, end_date=start).json()
    assert req["state"] == "awaiting_director" and req["assignee_id"] == FACULTY
    r = as_user(FACULTY, AUTHORITY, roles=("Director",)).post(
        f"/api/v1/elm/tasks/{req['id']}/decide", {"outcome": "approve"},
        format="json")
    assert r.json()["state"] == "approved"


# -- refusals -------------------------------------------------------------------
def test_no_module_grant_is_refused(as_user):
    r = as_user(STAFF, EMPLOYEE, modules=()).get("/api/v1/elm/balances")
    assert r.status_code == 403


def test_module_without_permission_is_refused(as_user):
    client = as_user(STAFF, ())
    assert client.get("/api/v1/elm/balances").status_code == 403
    assert _apply(client, category="CL", start_date=monday(),
                  end_date=monday()).status_code == 403
    assert client.get("/api/v1/elm/tasks").status_code == 403
    assert client.get("/api/v1/elm/admin/policy").status_code == 403


def test_employee_cannot_see_or_act_on_anothers_request(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
                 end_date=start).json()
    other = as_user(OTHER, EMPLOYEE)
    assert other.get(f"/api/v1/elm/requests/{req['id']}").status_code == 404
    assert other.post(f"/api/v1/elm/requests/{req['id']}/withdraw").status_code == 404
    assert other.get("/api/v1/elm/requests").json()["results"] == []


def test_reviewer_role_without_assignment_sees_nothing(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
                 end_date=start).json()
    stranger = as_user(OTHER, UNIT_HEAD)
    assert stranger.get("/api/v1/elm/tasks").json()["results"] == []
    r = stranger.post(f"/api/v1/elm/tasks/{req['id']}/decide",
                      {"outcome": "approve"}, format="json")
    assert r.status_code == 404


def test_acting_role_only_sees_its_own_queue(as_user, hierarchy):
    start = monday()
    req = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=start,
                 end_date=start).json()
    as_faculty = as_user(HEAD, EMPLOYEE, roles=("faculty", "HOD (CSE)"))
    assert as_faculty.get("/api/v1/elm/tasks").status_code == 403
    r = as_faculty.post(f"/api/v1/elm/tasks/{req['id']}/decide",
                        {"outcome": "approve"}, format="json")
    assert r.status_code == 403


def test_unit_head_cannot_approve_own_leave(as_user, hierarchy):
    r = _apply(as_user(HEAD, EMPLOYEE), category="CL", start_date=monday(),
               end_date=monday())
    assert r.json()["error"]["code"] == "unit_head_is_applicant"


def test_bad_query_param_is_400(as_user):
    r = as_user(STAFF, EMPLOYEE).get("/api/v1/elm/balances?year=abc")
    assert r.status_code == 400


def test_missing_unit_head_names_the_gap(as_user):
    r = _apply(as_user(STAFF, EMPLOYEE), category="CL", start_date=monday(),
               end_date=monday())
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "unit_head_missing"
