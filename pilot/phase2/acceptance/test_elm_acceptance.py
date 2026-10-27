"""ELM acceptance tests (Phase 2 verification harness).

Written by the reviewer from the ELM specification IDs, NOT by the local
model; they are the yardstick for the local model's code, kept outside modules/ so `make test`
is unaffected. Run: pytest pilot/phase2/acceptance -q
Every request goes through the real API with Fusion's own permission gates; the IAM is the
repository's in-memory fake (conftest.stub_iam).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db

API = "/api/v1/leave/"
EMP = ("leave.application.apply", "leave.application.view_own", "leave.substitute.respond")
UH = ("leave.application.review",)
EST = ("leave.application.review", "leave.application.verify")
SA = ("leave.application.review", "leave.application.sanction")
ADMIN = ("leave.admin.manage",)

APPLICANT, FACULTY, SUB, SUB2 = 101, 111, 102, 103
UNIT_HEAD, OTHER_HEAD, AUTHORITY, ESTT, DIRECTOR, LADMIN = 201, 202, 301, 401, 501, 601


def monday(weeks_ahead=3):
    d = date.today() + timedelta(weeks=weeks_ahead)
    return d - timedelta(days=d.weekday())


def as_user(stub_iam, user_id, perms, kind="staff", modules=("leave",)):
    stub_iam(make_session(user_id=user_id, permissions=perms, modules=modules,
                          kind=kind, roles=("employee",), active_role="employee"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def rows(resp):
    data = resp.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


def reporting_line(user_id, unit_head=UNIT_HEAD, estt=None, authority=AUTHORITY):
    from modules.leave.models import ReportingLine
    return ReportingLine.objects.update_or_create(
        user_id=user_id, defaults={"unit_head_id": unit_head, "establishment_id": estt,
                                   "sanctioning_authority_id": authority})[0]


def apply(stub_iam, user_id=APPLICANT, kind="staff", **body):
    c = as_user(stub_iam, user_id, EMP, kind=kind)
    start = body.pop("start", monday())
    end = body.pop("end", start + timedelta(days=1))
    payload = {"category": "CL", "start_date": str(start), "end_date": str(end),
               "half_day": "none", "purpose": "family function", "station_leave": False,
               "station_address": "", **body}
    return c.post(API + "applications/", payload, format="json")


def decide(stub_iam, user_id, perms, app_id, decision):
    return as_user(stub_iam, user_id, perms).post(
        f"{API}applications/{app_id}/decide/", {"decision": decision, "remark": ""}, format="json")


@pytest.fixture(autouse=True)
def lines(db):
    for uid in (APPLICANT, FACULTY, SUB, SUB2):
        reporting_line(uid)


# ---------------------------------------------------------------- Fusion integration, access
def test_module_grant_is_required(stub_iam):  # BR-EL-036
    c = as_user(stub_iam, APPLICANT, EMP, modules=())
    assert c.get(API + "applications/").status_code == 403


def test_permission_is_required_to_apply(stub_iam):  # BR-EL-036
    c = as_user(stub_iam, APPLICANT, ("leave.application.view_own",))
    r = c.post(API + "applications/", {}, format="json")
    assert r.status_code == 403


# ---------------------------------------------------------------- apply + validation
def test_cl_application_is_routed_to_the_applicants_unit_head(stub_iam):  # EL-UC-001, BR-EL-016
    r = apply(stub_iam)
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["status"] == "pending" and body["stage"] == "unit_head"
    assert body["assignee_id"] == UNIT_HEAD
    assert Decimal(str(body["days"])) == Decimal("2")


def test_cl_counts_weekdays_only(stub_iam):  # BR-EL-011 (continuous count is not for CL)
    fri = monday() + timedelta(days=4)
    r = apply(stub_iam, start=fri, end=fri + timedelta(days=3))
    assert r.status_code == 201, r.content
    assert Decimal(str(r.json()["days"])) == Decimal("2")


def test_el_counts_every_calendar_day(stub_iam):  # BR-EL-011
    fri = monday() + timedelta(days=4)
    r = apply(stub_iam, category="EL", start=fri, end=fri + timedelta(days=3))
    assert r.status_code == 201, r.content
    assert Decimal(str(r.json()["days"])) == Decimal("4")


def test_half_day_cl_is_half_a_day(stub_iam):  # BR-EL-010
    d = monday()
    r = apply(stub_iam, start=d, end=d, half_day="first")
    assert r.status_code == 201, r.content
    assert Decimal(str(r.json()["days"])) == Decimal("0.5")


def test_half_day_is_rejected_for_el(stub_iam):  # BR-EL-010
    d = monday()
    assert apply(stub_iam, category="EL", start=d, end=d, half_day="first").status_code == 400


def test_el_is_not_available_to_faculty(stub_iam):  # BR-EL-005
    assert apply(stub_iam, user_id=FACULTY, kind="faculty", category="EL").status_code == 400


def test_vl_is_not_available_to_staff(stub_iam):  # BR-EL-006
    assert apply(stub_iam, category="VL").status_code == 400


def test_cl_beyond_yearly_entitlement_is_rejected(stub_iam):  # BR-EL-002 (8 days)
    start = monday()
    assert apply(stub_iam, start=start, end=start + timedelta(days=11)).status_code == 400


def test_overlapping_application_is_rejected(stub_iam):  # BR-EL-012
    assert apply(stub_iam).status_code == 201
    assert apply(stub_iam).status_code == 400


def test_first_and_second_half_cl_on_one_day_do_not_overlap(stub_iam):  # BR-EL-012
    d = monday()
    assert apply(stub_iam, start=d, end=d, half_day="first").status_code == 201
    assert apply(stub_iam, start=d, end=d, half_day="second").status_code == 201


def test_missing_reporting_line_is_a_clear_error(stub_iam):  # BR-EL-019
    from modules.leave.models import ReportingLine
    ReportingLine.objects.filter(user_id=APPLICANT).delete()
    assert apply(stub_iam).status_code == 400


# ---------------------------------------------------------------- unit head and sanction
def test_unit_head_final_approval_updates_the_balance(stub_iam):  # BR-EL-016, CFR-EL-016
    app = apply(stub_iam).json()
    r = decide(stub_iam, UNIT_HEAD, UH, app["id"], "approve")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "approved"
    bal = rows(as_user(stub_iam, APPLICANT, EMP).get(API + "balances/", {"year": monday().year}))
    cl = next(b for b in bal if b["category"] == "CL")
    assert Decimal(str(cl["used"])) == Decimal("2")


def test_only_the_assigned_unit_head_can_decide(stub_iam):  # BR-EL-036
    app = apply(stub_iam).json()
    assert decide(stub_iam, OTHER_HEAD, UH, app["id"], "approve").status_code == 404


def test_inbox_lists_only_requests_assigned_to_me(stub_iam):  # EL-UC-003
    app = apply(stub_iam).json()
    mine = rows(as_user(stub_iam, UNIT_HEAD, UH).get(API + "inbox/"))
    other = rows(as_user(stub_iam, OTHER_HEAD, UH).get(API + "inbox/"))
    assert [a["id"] for a in mine] == [app["id"]] and other == []


def test_higher_sanction_leave_needs_a_recommendation_then_the_authority(stub_iam):  # BR-EL-017/018
    app = apply(stub_iam, category="EL").json()
    assert decide(stub_iam, UNIT_HEAD, UH, app["id"], "approve").status_code == 400
    r = decide(stub_iam, UNIT_HEAD, UH, app["id"], "recommended")
    assert r.status_code == 200, r.content
    assert r.json()["stage"] == "sanction" and r.json()["assignee_id"] == AUTHORITY
    r = decide(stub_iam, AUTHORITY, SA, app["id"], "approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_not_recommended_is_not_a_rejection(stub_iam):  # BR-EL-017
    app = apply(stub_iam, category="EL").json()
    r = decide(stub_iam, UNIT_HEAD, UH, app["id"], "not_recommended")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "pending" and r.json()["stage"] == "sanction"


def test_establishment_step_when_configured(stub_iam):  # BR-EL-019, EL-UC-004
    reporting_line(APPLICANT, estt=ESTT)
    app = apply(stub_iam, category="EL").json()
    r = decide(stub_iam, UNIT_HEAD, UH, app["id"], "recommended")
    assert r.json()["stage"] == "establishment" and r.json()["assignee_id"] == ESTT
    r = decide(stub_iam, ESTT, EST, app["id"], "verify")
    assert r.status_code == 200 and r.json()["stage"] == "sanction"


def test_sanction_needs_the_sanction_permission(stub_iam):  # BR-EL-036
    app = apply(stub_iam, category="EL").json()
    decide(stub_iam, UNIT_HEAD, UH, app["id"], "recommended")
    assert decide(stub_iam, AUTHORITY, UH, app["id"], "approve").status_code == 404


def test_director_self_sanctions(stub_iam):  # BR-EL-020
    reporting_line(DIRECTOR, unit_head=DIRECTOR, authority=None)
    app = apply(stub_iam, user_id=DIRECTOR, category="EL").json()
    assert app["stage"] == "sanction" and app["assignee_id"] == DIRECTOR
    assert decide(stub_iam, DIRECTOR, SA, app["id"], "approve").json()["status"] == "approved"


# ---------------------------------------------------------------- substitute consent gate
def test_substitute_must_accept_before_routing(stub_iam):  # BR-EL-015, EL-UC-002
    app = apply(stub_iam, substitute_id=SUB).json()
    assert app["stage"] == "substitute" and app["assignee_id"] == SUB
    assert decide(stub_iam, UNIT_HEAD, UH, app["id"], "approve").status_code == 404
    r = as_user(stub_iam, SUB, EMP).post(f"{API}applications/{app['id']}/substitute-response/",
                                         {"accept": True}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["stage"] == "unit_head" and r.json()["assignee_id"] == UNIT_HEAD


def test_declined_substitute_can_be_replaced(stub_iam):  # BR-EL-015, EL-UC-019
    app = apply(stub_iam, substitute_id=SUB).json()
    r = as_user(stub_iam, SUB, EMP).post(f"{API}applications/{app['id']}/substitute-response/",
                                         {"accept": False}, format="json")
    assert r.json()["substitute_status"] == "declined"
    r = as_user(stub_iam, APPLICANT, EMP).post(f"{API}applications/{app['id']}/replace-substitute/",
                                               {"substitute_id": SUB2}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["assignee_id"] == SUB2 and r.json()["substitute_status"] == "pending"


def test_applicant_cannot_be_own_substitute(stub_iam):  # BR-EL-014
    assert apply(stub_iam, substitute_id=APPLICANT).status_code == 400


def test_substitute_on_leave_is_not_eligible(stub_iam):  # BR-EL-014
    assert apply(stub_iam, user_id=SUB).status_code == 201
    assert apply(stub_iam, substitute_id=SUB).status_code == 400


# ---------------------------------------------------------------- withdrawal and cancellation
def test_withdrawal_stops_processing(stub_iam):  # BR-EL-022, EL-UC-007
    app = apply(stub_iam).json()
    r = as_user(stub_iam, APPLICANT, EMP).post(f"{API}applications/{app['id']}/withdraw/")
    assert r.status_code == 200 and r.json()["status"] == "withdrawn"
    assert decide(stub_iam, UNIT_HEAD, UH, app["id"], "approve").status_code == 404


def test_cancellation_restores_the_balance(stub_iam):  # BR-EL-023, EL-UC-008
    app = apply(stub_iam).json()
    decide(stub_iam, UNIT_HEAD, UH, app["id"], "approve")
    r = as_user(stub_iam, APPLICANT, EMP).post(f"{API}applications/{app['id']}/cancel/")
    assert r.status_code in (200, 201), r.content
    cancel = r.json()
    assert cancel["kind"] == "cancellation" and cancel["assignee_id"] == UNIT_HEAD
    assert decide(stub_iam, UNIT_HEAD, UH, cancel["id"], "approve").status_code == 200
    me = as_user(stub_iam, APPLICANT, EMP)
    assert me.get(f"{API}applications/{app['id']}/").json()["status"] == "cancelled"
    cl = next(b for b in rows(me.get(API + "balances/", {"year": monday().year})) if b["category"] == "CL")
    assert Decimal(str(cl["used"])) == Decimal("0")


# ---------------------------------------------------------------- privacy and admin
def test_other_users_application_is_not_visible(stub_iam):  # BR-EL-036
    app = apply(stub_iam).json()
    c = as_user(stub_iam, SUB2, EMP)
    assert c.get(f"{API}applications/{app['id']}/").status_code == 404
    assert rows(c.get(API + "applications/")) == []


def test_only_leave_admin_maintains_reporting_lines(stub_iam):  # EL-UC-014, BR-EL-037
    body = {"unit_head_id": OTHER_HEAD, "establishment_id": None, "sanctioning_authority_id": AUTHORITY}
    assert as_user(stub_iam, APPLICANT, EMP).put(
        f"{API}reporting-lines/{APPLICANT}/", body, format="json").status_code == 403
    r = as_user(stub_iam, LADMIN, ADMIN).put(f"{API}reporting-lines/{APPLICANT}/", body, format="json")
    assert r.status_code == 200, r.content
    assert apply(stub_iam).json()["assignee_id"] == OTHER_HEAD
