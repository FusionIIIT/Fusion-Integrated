"""Both gates separately, the acting role, self-decision, and every endpoint against the wrong caller."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave import registry
from modules.leave.tests.conftest import (
    DEPUTY_REGISTRAR,
    DIRECTOR,
    FACULTY_CSE,
    FACULTY_CSE_2,
    HOD_CSE,
    HRADMIN,
    STAFF_RO,
    STUDENT,
    apply_payload,
)

pytestmark = pytest.mark.django_db

DECLARED = {code for code, _ in registry.PERMISSIONS}


def raw_client(stub_iam, *, perms=(), modules=("leave",), uid=FACULTY_CSE, kind="faculty",
               roles=("faculty",), active_role="faculty"):
    assert set(perms) <= DECLARED, set(perms) - DECLARED
    stub_iam(make_session(user_id=uid, kind=kind, permissions=perms, modules=modules,
                          roles=roles, active_role=active_role))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_every_permission_a_grant_names_is_declared():
    granted = {c for codes in registry.ROLE_GRANTS.values() for c in codes}
    assert granted <= DECLARED


def test_grants_use_real_erp_spellings():
    """The join key: a typo here is a grant that reaches nobody."""
    assert {"HOD (CSE)", "Deputy Registrar", "Registrar", "Director", "hradmin",
            "Dean_s"} <= set(registry.ROLE_GRANTS)
    assert "student" not in registry.ROLE_GRANTS


def test_module_grant_without_permission_is_refused(configured, stub_iam):
    c = raw_client(stub_iam, perms=())
    assert c.post("/api/v1/leave/requests", apply_payload(), format="json").status_code == 403
    assert c.get("/api/v1/leave/overview").status_code == 403


def test_permission_without_module_grant_is_refused(configured, stub_iam):
    c = raw_client(stub_iam, perms=registry.ROLE_GRANTS["faculty"], modules=())
    assert c.post("/api/v1/leave/requests", apply_payload(), format="json").status_code == 403
    assert c.get("/api/v1/leave/overview").status_code == 403


def test_anonymous_is_refused(configured):
    assert APIClient().get("/api/v1/leave/overview").status_code in (401, 403)


def test_a_student_has_no_leave(configured, client_for, stub_iam):
    c = client_for(STUDENT)
    assert c.get("/api/v1/leave/overview").status_code == 403
    forged = raw_client(stub_iam, perms=registry.ROLE_GRANTS["faculty"], uid=STUDENT,
                        kind="student", roles=("student",), active_role="student")
    r = forged.post("/api/v1/leave/requests", apply_payload(), format="json")
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_an_employee"


def test_acting_role_decides_the_queue(configured, client_for):
    """One person, two designations: acting as faculty shows no HOD queue and cannot decide."""
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    as_hod = client_for(HOD_CSE)
    [task] = as_hod.get("/api/v1/leave/queue").json()
    as_faculty = client_for(HOD_CSE, as_role="faculty")
    assert as_faculty.get("/api/v1/leave/queue").status_code == 200
    assert as_faculty.get("/api/v1/leave/queue").json() == []
    r = as_faculty.post(f"/api/v1/leave/tasks/{task['id']}/decide", {"action": "approve"},
                        format="json")
    assert r.status_code == 404


def test_another_hod_cannot_decide(configured, client_for, stub_iam):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    [task] = client_for(HOD_CSE).get("/api/v1/leave/queue").json()
    ece = raw_client(stub_iam, perms=registry.ROLE_GRANTS["HOD (ECE)"], uid=555,
                     roles=("faculty", "HOD (ECE)"), active_role="HOD (ECE)")
    assert ece.get("/api/v1/leave/queue").json() == []
    assert ece.post(f"/api/v1/leave/tasks/{task['id']}/decide", {"action": "approve"},
                    format="json").status_code == 404
    assert ece.get(f"/api/v1/leave/requests/{task['request']['id']}").status_code == 404


def test_a_unit_head_never_reviews_their_own_leave(configured, client_for):
    r = client_for(HOD_CSE, as_role="faculty").post("/api/v1/leave/requests", apply_payload(),
                                                     format="json")
    assert r.status_code == 201
    assert client_for(HOD_CSE).get("/api/v1/leave/queue").json() == []
    assert [t["assignee_designation"] for t in
            client_for(DIRECTOR).get("/api/v1/leave/queue").json()] == ["Director"]


def test_a_forged_role_cannot_approve_own_request(configured, stub_iam):
    """Holding HOD (CSE) while being the applicant still refuses the decision."""
    c = raw_client(stub_iam, perms=registry.ROLE_GRANTS["faculty"])
    req = c.post("/api/v1/leave/requests", apply_payload(), format="json").json()
    from modules.leave.models import Task

    task = Task.objects.get(request_id=req["id"])
    forged = raw_client(stub_iam, perms=registry.ROLE_GRANTS["HOD (CSE)"],
                        roles=("faculty", "HOD (CSE)"), active_role="HOD (CSE)")
    r = forged.post(f"/api/v1/leave/tasks/{task.pk}/decide", {"action": "approve"},
                    format="json")
    assert r.status_code == 403 and r.json()["error"]["code"] == "own_request"


def test_director_self_sanction_needs_the_director_acting_as_director(configured, client_for):
    client_for(DIRECTOR, as_role="faculty").post("/api/v1/leave/requests", apply_payload(),
                                                 format="json")
    from modules.leave.models import Task

    task = Task.objects.get(step="director")
    for c in (client_for(DIRECTOR, as_role="faculty"), client_for(DEPUTY_REGISTRAR)):
        r = c.post(f"/api/v1/leave/tasks/{task.pk}/decide", {"action": "approve"},
                   format="json")
        assert r.status_code in (403, 404)


def test_unit_head_cannot_forward_or_sanction(configured, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                 apply_payload(category="COL", start="2026-03-09",
                                               end="2026-03-10"), format="json")
    hod = client_for(HOD_CSE)
    [task] = hod.get("/api/v1/leave/queue").json()
    for action in ("approve", "forward"):
        r = hod.post(f"/api/v1/leave/tasks/{task['id']}/decide", {"action": action},
                     format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] in ("invalid_action", "invalid_transition")


def test_cannot_act_on_someone_elses_request(configured, client_for):
    req = client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(),
                                       format="json").json()
    other = client_for(FACULTY_CSE_2)
    for path in ("withdraw", "cancellation", "extension", "substitute", "resumption"):
        r = other.post(f"/api/v1/leave/requests/{req['id']}/{path}",
                       {"reason": "x", "end_date": "2026-03-20", "substitute_user_id": 1,
                        "resumption_date": "2026-03-02"}, format="json")
        assert r.status_code == 404, (path, r.content)
    assert other.get(f"/api/v1/leave/requests/{req['id']}").status_code == 404
    assert other.get(f"/api/v1/leave/requests/{req['id']}/document").status_code == 404


@pytest.mark.parametrize("method,path", [
    ("get", "/api/v1/leave/admin/policy"), ("post", "/api/v1/leave/admin/policy"),
    ("get", "/api/v1/leave/admin/hierarchy"), ("post", "/api/v1/leave/admin/hierarchy"),
    ("get", "/api/v1/leave/admin/sla"), ("post", "/api/v1/leave/admin/sla"),
    ("get", "/api/v1/leave/admin/calendars"), ("post", "/api/v1/leave/admin/calendars"),
    ("post", "/api/v1/leave/admin/calendars/1/publish"),
    ("get", "/api/v1/leave/admin/vacations"),
    ("get", f"/api/v1/leave/admin/records?user_id={STAFF_RO}"),
    ("post", "/api/v1/leave/admin/records/offline"),
    ("post", "/api/v1/leave/admin/records/adjustments"),
    ("get", "/api/v1/leave/admin/year-end"), ("get", "/api/v1/leave/admin/readiness"),
])
def test_admin_endpoints_refuse_an_employee_and_an_approver(configured, client_for, method,
                                                             path):
    for uid in (FACULTY_CSE, HOD_CSE, DIRECTOR):
        r = getattr(client_for(uid), method)(path, {}, format="json")
        assert r.status_code == 403, (uid, path)


def test_an_approver_cannot_apply_while_acting_unless_also_an_employee(configured, stub_iam):
    c = raw_client(stub_iam, perms=registry.ROLE_GRANTS["Registrar"], kind="staff",
                   roles=("Registrar",), active_role="Registrar", uid=777)
    assert c.post("/api/v1/leave/requests", apply_payload(), format="json").status_code == 403


def test_hradmin_cannot_record_or_adjust_their_own_leave(configured, client_for):
    c = client_for(HRADMIN)
    r = c.post("/api/v1/leave/admin/records/adjustments",
               {"user_id": HRADMIN, "year": 2026, "category": "CL", "delta": "5",
                "reference": "OO-1", "note": "x"}, format="json")
    assert r.status_code == 403 and r.json()["error"]["code"] == "own_record"


def test_garbage_query_params_are_400(configured, client_for):
    c = client_for(FACULTY_CSE)
    assert c.get("/api/v1/leave/overview?year=abc").status_code == 400
    assert c.get("/api/v1/leave/requests?year=x").status_code == 400
    assert client_for(HRADMIN).get("/api/v1/leave/admin/records?user_id=x").status_code == 400
