"""Both gates, separately, and the acting role only."""
import pytest

from modules.elm.tests.conftest import (
    ADMIN,
    EMPLOYEE,
    FAC,
    FAC2,
    HOD,
    UNIT_HEAD,
    leave,
)

pytestmark = pytest.mark.django_db


def _pending(as_user):
    return as_user(FAC, EMPLOYEE).post("/api/v1/elm/requests", leave("CL"),
                                       format="json").json()["id"]


def test_permission_without_module_grant_is_refused(as_user, policy):
    c = as_user(FAC, EMPLOYEE, modules=())
    assert c.get("/api/v1/elm/requests").status_code == 403
    assert c.post("/api/v1/elm/requests", leave("CL"), format="json").status_code == 403


def test_module_grant_without_permission_is_refused(as_user, policy):
    c = as_user(FAC, ())
    assert c.get("/api/v1/elm/requests").status_code == 403
    assert c.post("/api/v1/elm/requests", leave("CL"), format="json").status_code == 403


def test_student_cannot_apply_even_with_a_stray_grant(as_user, policy, calendar):
    r = as_user(9001, EMPLOYEE, kind="student").post("/api/v1/elm/requests", leave("CL"),
                                                     format="json")
    assert r.status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/elm/queue", "/api/v1/elm/resumptions",
                                  "/api/v1/elm/admin/policies",
                                  "/api/v1/elm/admin/calendars",
                                  "/api/v1/elm/admin/offline",
                                  "/api/v1/elm/admin/accounts?user_id=101"])
def test_plain_employee_reaches_no_office_screen(as_user, policy, path):
    assert as_user(FAC2, EMPLOYEE).get(path).status_code == 403


def test_plain_employee_cannot_decide(as_user, policy, calendar):
    pk = _pending(as_user)
    r = as_user(FAC2, EMPLOYEE).post(f"/api/v1/elm/queue/{pk}/decide",
                                     {"event": "approve"}, format="json")
    assert r.status_code == 403


def test_holding_hod_but_acting_as_faculty_sees_no_queue(as_user, policy, calendar):
    pk = _pending(as_user)
    c = as_user(HOD, EMPLOYEE + UNIT_HEAD, roles=("faculty", "HOD (CSE)"),
                active_role="faculty")
    assert c.get("/api/v1/elm/queue").json()["results"] == []
    assert c.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                  format="json").status_code == 404


def test_another_departments_head_cannot_decide(as_user, policy, calendar):
    pk = _pending(as_user)
    c = as_user(HOD, UNIT_HEAD, roles=("HOD (ECE)",), active_role="HOD (ECE)")
    assert c.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                  format="json").status_code == 404


def test_reject_needs_a_reason(as_user, policy, calendar):
    pk = _pending(as_user)
    c = as_user(HOD, UNIT_HEAD, roles=("HOD (CSE)",), active_role="HOD (CSE)")
    r = c.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "reject"}, format="json")
    assert r.json()["error"]["code"] == "reason_required"


def test_non_substitute_cannot_answer_for_the_substitute(as_user, policy, calendar):
    pk = as_user(FAC, EMPLOYEE).post(
        "/api/v1/elm/requests", leave("CL", substitute_user_id=FAC2),
        format="json").json()["id"]
    r = as_user(201, EMPLOYEE, kind="staff").post(
        f"/api/v1/elm/substitutions/{pk}/respond", {"accept": True}, format="json")
    assert r.status_code == 404


def test_admin_cannot_record_offline_leave_for_self(as_user, policy, calendar):
    r = as_user(701, ADMIN, kind="staff", roles=("Leave Administrator",)).post(
        "/api/v1/elm/admin/offline",
        {"user_id": 701, "category": "CL", "start_date": "2026-01-05",
         "end_date": "2026-01-05", "sanction_reference": "X", "sanctioned_by": "Y",
         "sanctioned_on": "2026-01-01"}, format="json")
    assert r.status_code in (404, 422)


def test_bad_query_param_is_400_not_500(as_user, policy):
    c = as_user(701, ADMIN, kind="staff", roles=("Leave Administrator",))
    assert c.get("/api/v1/elm/admin/accounts?user_id=abc").status_code == 400
