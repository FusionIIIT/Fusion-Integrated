"""ELM API: wiring, permissions and error mapping. The rules themselves are covered
by the service tests; this checks that HTTP reaches them correctly."""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.contracts import UserDTO
from modules.elm.models import HierarchyRule, HolidayCalendar, LeavePolicy
from modules.elm.services import accounts, policy

pytestmark = pytest.mark.django_db

BASE = "/api/v1/elm"
DAY = "2026-11-02"
DRAFT = {"leave_type": "CL", "start_date": DAY, "end_date": DAY, "reason": "personal"}
PEOPLE = {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"User {i}",
                     kind="staff", department="CSE") for i in (1, 2, 3, 10, 20, 40)}


@pytest.fixture(autouse=True)
def world(db):
    p = patch("modules.elm.services.applications.get_users",
              side_effect=lambda ids: {i: PEOPLE[i] for i in ids if i in PEOPLE})
    p.start()
    policy.publish_policy(LeavePolicy.objects.create(version=1, params=policy.DEFAULT_PARAMS))
    policy.publish_calendar(HolidayCalendar.objects.create(year=2026, version=1))
    HierarchyRule.objects.create(stage="unit_head", approver_id=10, status="published")
    HierarchyRule.objects.create(stage="final", approver_id=40, status="published")
    for uid in (1, 2, 3):
        accounts.credit_annual(uid, 2026, "staff", policy.DEFAULT_PARAMS)
    yield
    p.stop()


def as_user(stub_iam, uid, *permissions):
    """The fake identity service answers with ONE session at a time, so call this
    immediately before each request and use the client it returns right away."""
    stub_iam(make_session(user_id=uid, kind="staff", permissions=permissions,
                          modules=("elm",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token t{uid}")
    return client


def make_draft(stub_iam, uid=1, body=None):
    r = as_user(stub_iam, uid, "elm.request.create").post(
        f"{BASE}/requests", body or DRAFT, format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def test_applying_needs_the_permission(stub_iam):
    c = as_user(stub_iam, 1)
    assert c.post(f"{BASE}/requests", DRAFT, format="json").status_code == 403


def test_a_cl_request_runs_from_draft_to_approval(stub_iam):
    rid = make_draft(stub_iam)
    r = as_user(stub_iam, 1, "elm.request.create").post(
        f"{BASE}/requests/{rid}/submit", {}, format="json")
    assert r.json()["status"] == "awaiting_unit_head"

    tasks = as_user(stub_iam, 10, "elm.task.view").get(f"{BASE}/tasks").json()
    assert [t["request"]["id"] for t in tasks["results"]] == [rid]

    r = as_user(stub_iam, 10, "elm.task.view").post(
        f"{BASE}/requests/{rid}/unit-head", {"outcome": "approved"}, format="json")
    assert r.json()["status"] == "approved"

    bal = as_user(stub_iam, 1, "elm.account.view_self").get(f"{BASE}/balances?year=2026").json()
    assert {a["leave_type"]: float(a["balance"]) for a in bal["accounts"]}["CL"] == 7


def test_only_the_task_holder_can_decide(stub_iam):
    rid = make_draft(stub_iam)
    as_user(stub_iam, 1, "elm.request.create").post(f"{BASE}/requests/{rid}/submit", {}, format="json")
    r = as_user(stub_iam, 99, "elm.task.view").post(
        f"{BASE}/requests/{rid}/unit-head", {"outcome": "approved"}, format="json")
    assert r.status_code == 400
    r = as_user(stub_iam, 10).post(
        f"{BASE}/requests/{rid}/unit-head", {"outcome": "approved"}, format="json")
    assert r.status_code == 403


def test_nobody_else_can_submit_or_act_on_my_draft(stub_iam):
    rid = make_draft(stub_iam)
    # Probing another user's request returns 404 (IDOR protection)
    r = as_user(stub_iam, 2, "elm.request.create").post(
        f"{BASE}/requests/{rid}/submit", {}, format="json")
    assert r.status_code == 404
    r_withdraw = as_user(stub_iam, 2, "elm.request.create").post(
        f"{BASE}/requests/{rid}/withdraw", {}, format="json")
    assert r_withdraw.status_code == 404
    r_cancel = as_user(stub_iam, 2, "elm.request.create").post(
        f"{BASE}/requests/{rid}/cancel", {}, format="json")
    assert r_cancel.status_code == 404


def test_someone_elses_request_is_not_visible(stub_iam):
    rid = make_draft(stub_iam)
    r = as_user(stub_iam, 2, "elm.request.view_self").get(f"{BASE}/requests/{rid}")
    assert r.status_code == 404


def test_service_errors_use_the_platform_envelope(stub_iam):
    too_long = dict(DRAFT, end_date="2026-11-13")           # 10 weekdays, balance is 8
    r = as_user(stub_iam, 1, "elm.request.create").post(
        f"{BASE}/requests", too_long, format="json")
    assert r.status_code == 400
    assert r.json()["error"]["message"]


def test_malformed_input_is_a_validation_error(stub_iam):
    body = {k: v for k, v in DRAFT.items() if k != "reason"}
    r = as_user(stub_iam, 1, "elm.request.create").post(f"{BASE}/requests", body, format="json")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_withdrawn_request_cannot_be_decided(stub_iam):
    rid = make_draft(stub_iam)
    as_user(stub_iam, 1, "elm.request.create").post(f"{BASE}/requests/{rid}/submit", {}, format="json")
    r = as_user(stub_iam, 1, "elm.request.create").post(
        f"{BASE}/requests/{rid}/withdraw", {}, format="json")
    assert r.json()["status"] == "withdrawn"
    r = as_user(stub_iam, 10, "elm.task.view").post(
        f"{BASE}/requests/{rid}/unit-head", {"outcome": "approved"}, format="json")
    assert r.status_code == 400


def test_applicant_can_print_their_application(stub_iam):
    rid = make_draft(stub_iam)
    r = as_user(stub_iam, 1, "elm.request.view_self").get(f"{BASE}/requests/{rid}/print")
    assert r.status_code == 200
    assert r.json()["applicant"]["name"] == "User 1"

    # HTML printable representation (EL-UC-013)
    r_html = as_user(stub_iam, 1, "elm.request.view_self").get(f"{BASE}/requests/{rid}/print?format=html")
    assert r_html.status_code == 200
    assert "text/html" in r_html["Content-Type"]
    assert "Employee Leave Application Form" in r_html.content.decode("utf-8")


def test_policy_admin_needs_the_permission(stub_iam):
    body = {"params": policy.DEFAULT_PARAMS}
    assert as_user(stub_iam, 1).post(f"{BASE}/admin/policy", body, format="json").status_code == 403


def test_publishing_a_new_policy_takes_effect(stub_iam):
    params = dict(policy.DEFAULT_PARAMS, CL=10)
    r = as_user(stub_iam, 20, "elm.policy.manage").post(
        f"{BASE}/admin/policy", {"params": params}, format="json")
    assert r.status_code == 201
    assert policy.get_effective_policy().params["CL"] == 10


def test_an_incomplete_policy_is_refused_and_the_old_one_stays(stub_iam):
    r = as_user(stub_iam, 20, "elm.policy.manage").post(
        f"{BASE}/admin/policy", {"params": {"CL": 3}}, format="json")
    assert r.status_code == 400
    assert policy.get_effective_policy().params["CL"] == 8


def test_calendar_publish_and_duplicate_rejected(stub_iam):
    day = {"date": "2026-12-25", "kind": "holiday", "name": "Christmas"}
    ok = as_user(stub_iam, 20, "elm.calendar.manage").post(
        f"{BASE}/admin/calendar", {"year": 2026, "days": [day]}, format="json")
    assert ok.status_code == 201 and ok.json()["version"] == 2
    dup = as_user(stub_iam, 20, "elm.calendar.manage").post(
        f"{BASE}/admin/calendar", {"year": 2026, "days": [day, day]}, format="json")
    assert dup.status_code == 400


def test_offline_record_updates_the_balance(stub_iam):
    body = {"applicant_id": 1, "leave_type": "EL", "start_date": "2026-11-02",
            "end_date": "2026-11-06", "reference": "Office Order 12/2026",
            "sanctioned_by": "Registrar", "sanctioned_on": "2026-10-01"}
    r = as_user(stub_iam, 20, "elm.offline.record").post(
        f"{BASE}/admin/offline", body, format="json")
    assert r.status_code == 201 and r.json()["status"] == "approved"
    bal = as_user(stub_iam, 1, "elm.account.view_self").get(f"{BASE}/balances?year=2026").json()
    assert {a["leave_type"]: float(a["balance"]) for a in bal["accounts"]}["EL"] == 25
