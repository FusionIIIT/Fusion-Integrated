import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models.leave_application import LeaveApplication
from modules.elm.models.leave_types import LeaveBalance, LeaveType

pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_type_cl():
    return LeaveType.objects.create(code="CL", name="Casual Leave", annual_entitlement=8)


@pytest.fixture
def leave_balance_user7(leave_type_cl):
    LeaveBalance.objects.create(user_id=7, leave_type=leave_type_cl, year=2026, balance=8)


def test_no_module_grant_403(stub_iam):
    stub_iam(
        make_session(user_id=7, kind="faculty", modules=(), permissions=("elm.leave.view_self",))
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")
    r = c.get("/api/v1/elm/leave-applications/")
    assert r.status_code == 403


def test_user_sees_only_own_applications(stub_iam, leave_type_cl):
    # User 500's application
    LeaveApplication.objects.create(
        user_id=500,
        leave_type=leave_type_cl,
        status="AWAITING_UNIT_HEAD_REVIEW",
        start_date="2026-11-01",
        end_date="2026-11-02",
        purpose="Test",
    )
    # User 7's application
    LeaveApplication.objects.create(
        user_id=7,
        leave_type=leave_type_cl,
        status="AWAITING_UNIT_HEAD_REVIEW",
        start_date="2026-11-01",
        end_date="2026-11-02",
        purpose="Test",
    )
    stub_iam(
        make_session(
            user_id=7,
            kind="faculty",
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.view"),
        )
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")
    r = c.get("/api/v1/elm/leave-applications/")
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["user_id"] == 7


def test_leave_types_post_delete_405(stub_iam):
    stub_iam(
        make_session(
            user_id=7,
            kind="faculty",
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.view"),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")

    r_post = c.post(
        "/api/v1/elm/leave-types/",
        {"code": "NEW", "name": "New", "annual_entitlement": 5},
        format="json",
    )
    assert r_post.status_code == 405

    r_delete = c.delete("/api/v1/elm/leave-types/1/")
    assert r_delete.status_code == 405


def test_leave_applications_put_patch_delete_405(stub_iam):
    stub_iam(
        make_session(
            user_id=7, kind="faculty", modules=("elm",), permissions=("elm.leave.view_self",)
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")

    # Test PUT
    r_put = c.put("/api/v1/elm/leave-applications/1/", {"status": "APPROVED"}, format="json")
    assert r_put.status_code == 405

    # Test PATCH
    r_patch = c.patch("/api/v1/elm/leave-applications/1/", {"status": "APPROVED"}, format="json")
    assert r_patch.status_code == 405

    # Test DELETE
    r_delete = c.delete("/api/v1/elm/leave-applications/1/")
    assert r_delete.status_code == 405


def test_apply_leave_success(stub_iam, leave_type_cl, leave_balance_user7):
    stub_iam(
        make_session(
            user_id=7,
            kind="faculty",
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.create"),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")

    r = c.post(
        "/api/v1/elm/leave-applications/",
        {
            "leave_type": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "purpose": "Test",
            "status": "APPROVED",
            "user_id": 999,
        },
        format="json",
    )

    assert r.status_code == 201
    app_id = r.json()["id"]
    app = LeaveApplication.objects.get(id=app_id)
    assert app.user_id == 7
    assert app.status == "AWAITING_UNIT_HEAD_REVIEW"


def test_record_decision_rules(stub_iam, leave_type_cl):
    # Setup
    app = LeaveApplication.objects.create(
        user_id=500,
        leave_type=leave_type_cl,
        status="AWAITING_UNIT_HEAD_REVIEW",
        start_date="2026-11-01",
        end_date="2026-11-02",
        purpose="Test",
    )

    # 1. No permission
    stub_iam(
        make_session(
            user_id=7, kind="faculty", modules=("elm",), permissions=("elm.leave.view_self",)
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token t")
    r = c.post(
        "/api/v1/elm/record-decision/",
        {"application_id": app.id, "action": "approve"},
        format="json",
    )
    assert r.status_code == 403

    # 2. Approver is applicant
    stub_iam(
        make_session(
            user_id=500, kind="faculty", modules=("elm",), permissions=("elm.leave.approve",)
        )
    )
    c.credentials(HTTP_AUTHORIZATION="Token t")
    r = c.post(
        "/api/v1/elm/record-decision/",
        {"application_id": app.id, "action": "approve"},
        format="json",
    )
    assert r.status_code == 403

    # 3. Success
    stub_iam(
        make_session(
            user_id=7, kind="faculty", modules=("elm",), permissions=("elm.leave.approve",)
        )
    )
    c.credentials(HTTP_AUTHORIZATION="Token t")
    r = c.post(
        "/api/v1/elm/record-decision/",
        {"application_id": app.id, "action": "approve"},
        format="json",
    )
    assert r.status_code == 200
    app.refresh_from_db()
    assert app.status == "APPROVED"
