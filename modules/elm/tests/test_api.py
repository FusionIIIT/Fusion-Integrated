"""Ownership is enforced by the selector, so a foreign id is a 404 not a 403."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session, stub_iam, user_ref
from modules.elm.models import LeaveType, LeaveApplication
from modules.directory.models import UserRef


pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_type():
    return LeaveType.objects.create(code="CL", name="Casual Leave")


def test_create_leave_application(stub_iam, leave_type, user_ref):
    session = make_session(user_id=1001, kind="faculty", modules=("elm",), permissions=("elm.application.create",))
    stub_iam(session, users={1001: user_ref(1001)})
    UserRef.objects.update_or_create(user_id=1001, defaults={"username": "u1001", "display_name": "User 1001", "kind": "faculty"})
    
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    data = {
        "leave_type": leave_type.code,
        "start_date": "2023-10-01",
        "end_date": "2023-10-05",
        "is_half_day": False,
        "reason": "Sick"
    }

    response = c.post("/api/v1/elm/applications/create", data, format="json")
    assert response.status_code == 201
    created_application = LeaveApplication.objects.get(pk=response.json()["id"])
    assert created_application.applicant_id == 1001
    assert created_application.status == "PENDING"


def test_create_leave_application_without_permission(stub_iam, leave_type, user_ref):
    session = make_session(user_id=2002, kind="student", modules=("elm",), permissions=())
    stub_iam(session, users={2002: user_ref(2002)})
    UserRef.objects.update_or_create(user_id=2002, defaults={"username": "u2002", "display_name": "User 2002", "kind": "faculty"})
    
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    data = {
        "leave_type": leave_type.code,
        "start_date": "2023-10-01",
        "end_date": "2023-10-05",
        "is_half_day": False,
        "reason": "Sick"
    }

    response = c.post("/api/v1/elm/applications/create", data, format="json")
    assert response.status_code == 403


def test_create_leave_application_with_invalid_status(stub_iam, leave_type, user_ref):
    session = make_session(user_id=1001, kind="faculty", modules=("elm",), permissions=("elm.application.create",))
    stub_iam(session, users={1001: user_ref(1001)})
    UserRef.objects.update_or_create(user_id=1001, defaults={"username": "u1001", "display_name": "User 1001", "kind": "faculty"})
    
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    data = {
        "leave_type": leave_type.code,
        "start_date": "2023-10-01",
        "end_date": "2023-10-05",
        "is_half_day": False,
        "reason": "Sick",
        "status": "APPROVED"
    }

    response = c.post("/api/v1/elm/applications/create", data, format="json")
    assert response.status_code == 201
    created_application = LeaveApplication.objects.get(pk=response.json()["id"])
    assert created_application.applicant_id == 1001
    assert created_application.status == "PENDING"


def test_view_leave_applications(stub_iam, leave_type, user_ref):
    session = make_session(user_id=1001, kind="faculty", modules=("elm",), permissions=("elm.application.view",))
    stub_iam(session, users={1001: user_ref(1001)})
    UserRef.objects.update_or_create(user_id=1001, defaults={"username": "u1001", "display_name": "User 1001", "kind": "faculty"})
    UserRef.objects.update_or_create(user_id=1002, defaults={"username": "u1002", "display_name": "User 1002", "kind": "faculty"})

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    for uid in (1001, 1002):
        LeaveApplication.objects.create(
            applicant_id=uid, leave_type_id="CL", start_date="2023-10-01",
            end_date="2023-10-05", is_half_day=False, reason="Sick")

    response = c.get("/api/v1/elm/applications")
    assert response.status_code == 200
    applications = response.json()
    assert len(applications) == 1
    assert applications[0]["applicant"] == 1001


def _payload(start, end, **kw):
    return {"leave_type": "CL", "start_date": start, "end_date": end,
            "is_half_day": False, "reason": "Personal", **kw}


def _post(stub_iam, uid, payload):
    UserRef.objects.update_or_create(user_id=uid, defaults={
        "username": f"u{uid}", "display_name": f"User {uid}", "kind": "faculty"})
    stub_iam(make_session(user_id=uid, kind="faculty", modules=("elm",),
                          permissions=("elm.application.create",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c.post("/api/v1/elm/applications/create", payload, format="json")


def test_end_before_start_is_rejected(stub_iam, leave_type):
    assert _post(stub_iam, 1001, _payload("2026-11-05", "2026-11-01")).status_code == 400


def test_overlap_with_own_pending_is_rejected(stub_iam, leave_type):
    assert _post(stub_iam, 1001, _payload("2026-11-02", "2026-11-04")).status_code == 201
    assert _post(stub_iam, 1001, _payload("2026-11-04", "2026-11-06")).status_code == 400


def test_adjacent_leave_is_allowed(stub_iam, leave_type):
    assert _post(stub_iam, 1001, _payload("2026-11-02", "2026-11-04")).status_code == 201
    assert _post(stub_iam, 1001, _payload("2026-11-05", "2026-11-06")).status_code == 201


def test_another_users_overlap_is_allowed(stub_iam, leave_type):
    assert _post(stub_iam, 1001, _payload("2026-11-02", "2026-11-04")).status_code == 201
    assert _post(stub_iam, 1002, _payload("2026-11-02", "2026-11-04")).status_code == 201


from modules.elm.models import UnitHeadAssignment


def _setup_app(code="CL", status="PENDING"):
    for uid in (1001, 2001, 3001):
        UserRef.objects.update_or_create(user_id=uid, defaults={
            "username": f"u{uid}", "display_name": f"User {uid}", "kind": "faculty"})
    UnitHeadAssignment.objects.update_or_create(employee_id=1001, defaults={"unit_head_id": 2001})
    LeaveType.objects.get_or_create(code=code, defaults={"name": code})
    return LeaveApplication.objects.create(
        applicant_id=1001, leave_type_id=code, start_date="2026-11-02",
        end_date="2026-11-03", is_half_day=False, reason="x", status=status)


def _decide(stub_iam, uid, pk, decision, perms=("elm.application.approve",)):
    stub_iam(make_session(user_id=uid, kind="faculty", modules=("elm",), permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c.post(f"/api/v1/elm/applications/{pk}/decide", {"decision": decision}, format="json")


def test_unit_head_approves_cl(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 2001, app.pk, "approve").status_code == 200
    app.refresh_from_db()
    assert app.status == "APPROVED" and app.decided_by_id == 2001 and app.decided_at is not None


def test_unit_head_rejects_cl(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 2001, app.pk, "reject").status_code == 200
    app.refresh_from_db()
    assert app.status == "REJECTED"


def test_user_who_is_not_the_unit_head_gets_404(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 3001, app.pk, "approve").status_code == 404
    app.refresh_from_db()
    assert app.status == "PENDING"


def test_applicant_cannot_decide_own_request(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 1001, app.pk, "approve").status_code == 404
    app.refresh_from_db()
    assert app.status == "PENDING"


def test_decision_requires_approve_permission(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 2001, app.pk, "approve", perms=()).status_code == 403


def test_non_pending_request_cannot_be_decided(stub_iam):
    app = _setup_app(status="WITHDRAWN")
    assert _decide(stub_iam, 2001, app.pk, "approve").status_code == 400
    app.refresh_from_db()
    assert app.status == "WITHDRAWN"


def test_unit_head_cannot_finally_approve_higher_sanction_leave(stub_iam):
    app = _setup_app(code="EL")
    assert _decide(stub_iam, 2001, app.pk, "approve").status_code == 400
    app.refresh_from_db()
    assert app.status == "PENDING"


def test_invalid_decision_value_is_rejected(stub_iam):
    app = _setup_app()
    assert _decide(stub_iam, 2001, app.pk, "maybe").status_code == 400
