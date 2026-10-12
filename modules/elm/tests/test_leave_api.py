import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm import registry
from modules.elm.models import LeaveRequest

pytestmark = pytest.mark.django_db

URL = "/api/v1/elm/leave-requests/"
STAFF = ("elm.leave_request.view", "elm.leave_request.manage")
BODY = {"category": "CL", "start_date": "2026-11-02",
        "end_date": "2026-11-03", "reason": "Family function"}


def _as(stub_iam, uid=2001, perms=STAFF, modules=("elm",)):
    stub_iam(make_session(user_id=uid, kind="staff", roles=("staff",),
                          active_role="staff", modules=modules, permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_permission_codes_match_registry():
    declared = {code for code, _ in registry.PERMISSIONS}
    assert set(STAFF) <= declared
    assert set(registry.ROLE_GRANTS["staff"]) <= declared


def test_staff_applies_for_their_own_leave(stub_iam):
    response = _as(stub_iam).post(URL, {**BODY, "user_id": 9999}, format="json")

    assert response.status_code == 201, response.content
    row = LeaveRequest.objects.get()
    assert row.user_id == 2001 and row.status == "pending"


def test_end_before_start_is_refused(stub_iam):
    response = _as(stub_iam).post(
        URL, {**BODY, "end_date": "2026-11-01"}, format="json")

    assert response.status_code == 400


def test_without_manage_cannot_apply(stub_iam):
    client = _as(stub_iam, perms=("elm.leave_request.view",))

    assert client.post(URL, BODY, format="json").status_code == 403


def test_without_module_grant_is_refused(stub_iam):
    assert _as(stub_iam, modules=()).get(URL).status_code == 403


def test_another_persons_request_is_404(stub_iam):
    other = LeaveRequest.objects.create(user_id=3003, category="EL",
                                        start_date="2026-11-02",
                                        end_date="2026-11-02", reason="x")
    client = _as(stub_iam)

    assert client.get(URL).json()["results"] == []
    assert client.get(f"{URL}{other.pk}/").status_code == 404
    assert client.delete(f"{URL}{other.pk}/").status_code == 404


def test_decided_request_cannot_be_edited(stub_iam):
    row = LeaveRequest.objects.create(user_id=2001, category="CL", status="approved",
                                      start_date="2026-11-02",
                                      end_date="2026-11-02", reason="x")

    response = _as(stub_iam).patch(f"{URL}{row.pk}/", {"reason": "y"}, format="json")

    assert response.status_code == 409
