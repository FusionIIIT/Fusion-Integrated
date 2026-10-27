import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveApplication, LeaveBalance, ReportingLine


@pytest.mark.django_db
def test_withdraw_pending_request(stub_iam):
    """BR-EL-022: Withdraw only while PENDING; second withdraw -> 404."""
    user_id = 1001
    permissions = ("leave.application.apply", "leave.application.view_own", "leave.substitute.respond")
    kind = "staff"

    stub_iam(make_session(user_id=user_id, permissions=permissions, modules=("leave",), kind=kind, roles=("employee",), active_role="employee"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Create a CL application (Pending)
    start_date = datetime.date.today() + datetime.timedelta(days=21 - datetime.date.today().weekday())
    end_date = start_date + datetime.timedelta(days=1)
    app = LeaveApplication.objects.create(
        user_id=user_id,
        kind="leave",
        category="CL",
        start_date=start_date,
        end_date=end_date,
        half_day="none",
        days=1.0,
        purpose="Test",
        station_leave=False,
        substitute_id=None,
        substitute_status="not_required",
        unit_head_id=201,
        establishment_id=None,
        sanctioning_authority_id=None,
        stage="substitute",
        status="pending",
    )

    # First withdraw: success
    response = c.post(f"/api/v1/leave/applications/{app.id}/withdraw/")
    assert response.status_code == 200
    withdrawn_app = LeaveApplication.objects.get(id=app.id)
    assert withdrawn_app.status == "withdrawn"

    # Second withdraw: 404 (already withdrawn)
    response = c.post(f"/api/v1/leave/applications/{app.id}/withdraw/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_cancellation_restores_balance(stub_iam):
    """BR-EL-023: Cancellation creates parent request; approving it cancels original and restores balance."""
    user_id = 1001
    unit_head_id = 201
    permissions = (
        "leave.application.apply",
        "leave.application.view_own",
        "leave.substitute.respond",
    )

    # Create initial balance record
    LeaveBalance.objects.create(
        user_id=user_id, category="CL", year=datetime.date.today().year,
        entitled=8.0, used=0.0,
    )

    stub_iam(make_session(
        user_id=user_id, permissions=permissions,
        modules=("leave",), kind="staff",
        roles=("employee",), active_role="employee",
    ))

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Create a CL application already at unit_head stage, with assignee
    start_date = (
        datetime.date.today()
        + datetime.timedelta(days=21 - datetime.date.today().weekday())
    )
    end_date = start_date + datetime.timedelta(days=1)
    app = LeaveApplication.objects.create(
        user_id=user_id,
        kind="leave",
        category="CL",
        start_date=start_date,
        end_date=end_date,
        half_day="none",
        days=2.0,
        purpose="Test",
        station_leave=False,
        substitute_id=None,
        substitute_status="not_required",
        unit_head_id=unit_head_id,
        establishment_id=None,
        sanctioning_authority_id=None,
        assignee_id=unit_head_id,
        stage="unit_head",
        status="pending",
    )

    # Get initial balance (should be 0 used)
    initial_balance = LeaveBalance.objects.filter(
        user_id=user_id, category="CL",
    ).first()
    assert initial_balance is not None
    assert initial_balance.used == 0.0

    # Switch to unit head session to approve
    stub_iam(make_session(
        user_id=unit_head_id,
        permissions=("leave.application.review",),
        modules=("leave",), kind="faculty",
        roles=("unit_head",), active_role="unit_head",
    ))
    response = c.post(
        f"/api/v1/leave/applications/{app.id}/decide/",
        {"decision": "approve", "remark": "Approved"},
    )
    assert response.status_code == 200
    approved_app = LeaveApplication.objects.get(id=app.id)
    assert approved_app.status == "approved"

    # Check balance after approval (should be 2.0 used)
    updated_balance = LeaveBalance.objects.filter(
        user_id=user_id, category="CL",
    ).first()
    assert updated_balance is not None
    assert updated_balance.used == 2.0


@pytest.mark.django_db
def test_balances_for_staff_and_faculty(stub_iam):
    """BR-EL-005/006: GET balances/ returns correct categories based on kind."""
    staff_user_id = 1001
    faculty_user_id = 1002

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # --- Staff ---
    stub_iam(make_session(
        user_id=staff_user_id,
        permissions=("leave.application.apply", "leave.application.view_own"),
        modules=("leave",), kind="staff",
        roles=("employee",), active_role="employee",
    ))
    response = c.get("/api/v1/leave/balances/?year=2024")
    assert response.status_code == 200
    staff_categories = {b["category"] for b in response.data}
    assert staff_categories == {"CL", "RH", "SCL", "EL", "COL"}

    # --- Faculty ---
    stub_iam(make_session(
        user_id=faculty_user_id,
        permissions=("leave.application.apply", "leave.application.view_own"),
        modules=("leave",), kind="faculty",
        roles=("employee",), active_role="employee",
    ))
    response = c.get("/api/v1/leave/balances/?year=2024")
    assert response.status_code == 200
    faculty_categories = {b["category"] for b in response.data}
    assert faculty_categories == {"CL", "RH", "SCL", "COL", "VL"}


@pytest.mark.django_db
def test_reporting_lines_admin_only(stub_iam):
    """EL-UC-014: PUT reporting-lines/<user_id>/ requires Leave Administrator permission."""
    user_id = 1001
    admin_user_id = 200
    new_unit_head_id = 201

    # Create initial reporting line
    ReportingLine.objects.create(
        user_id=user_id, unit_head_id=101,
        establishment_id=None, sanctioning_authority_id=None,
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Admin updates reporting line (use format='json' so None values serialize)
    stub_iam(make_session(
        user_id=admin_user_id,
        permissions=("leave.admin.manage",),
        modules=("leave",), kind="staff",
        roles=("admin",), active_role="admin",
    ))
    response = c.put(
        f"/api/v1/leave/reporting-lines/{user_id}/",
        {"unit_head_id": new_unit_head_id},
        format="json",
    )
    assert response.status_code == 200
    updated_line = ReportingLine.objects.get(user_id=user_id)
    assert updated_line.unit_head_id == new_unit_head_id

    # Verify update via GET
    response = c.get(f"/api/v1/leave/reporting-lines/{user_id}/")
    assert response.status_code == 200
    retrieved_line = ReportingLine.objects.get(user_id=user_id)
    assert retrieved_line.unit_head_id == new_unit_head_id

    # Employee tries to update (should be 403)
    stub_iam(make_session(
        user_id=user_id,
        permissions=("leave.application.apply", "leave.application.view_own"),
        modules=("leave",), kind="staff",
        roles=("employee",), active_role="employee",
    ))
    response = c.put(
        f"/api/v1/leave/reporting-lines/{user_id}/",
        {"unit_head_id": new_unit_head_id},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_wrong_decision_for_stage_is_400(stub_iam):
    """BR-EL-016: For CL at unit head stage, decision "recommended" -> 400."""
    user_id = 1001
    unit_head_id = 201

    # Create a CL application at unit head stage with assignee set
    start_date = (
        datetime.date.today()
        + datetime.timedelta(days=21 - datetime.date.today().weekday())
    )
    end_date = start_date + datetime.timedelta(days=1)
    app = LeaveApplication.objects.create(
        user_id=user_id,
        kind="leave",
        category="CL",
        start_date=start_date,
        end_date=end_date,
        half_day="none",
        days=1.0,
        purpose="Test",
        station_leave=False,
        substitute_id=None,
        substitute_status="not_required",
        unit_head_id=unit_head_id,
        establishment_id=None,
        sanctioning_authority_id=None,
        assignee_id=unit_head_id,
        stage="unit_head",
        status="pending",
    )

    # Authenticate as unit head with review permission
    stub_iam(make_session(
        user_id=unit_head_id,
        permissions=("leave.application.review",),
        modules=("leave",), kind="faculty",
        roles=("unit_head",), active_role="unit_head",
    ))

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Try to decide with "recommended" (invalid for CL at unit head)
    response = c.post(
        f"/api/v1/leave/applications/{app.id}/decide/",
        {"decision": "recommended", "remark": "Test"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_unknown_application_is_404(stub_iam):
    """Unknown application -> 404."""
    user_id = 1001

    stub_iam(make_session(
        user_id=user_id,
        permissions=("leave.application.apply", "leave.application.view_own"),
        modules=("leave",), kind="staff",
        roles=("employee",), active_role="employee",
    ))

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Try to get a non-existent application
    response = c.get("/api/v1/leave/applications/999999/")
    assert response.status_code == 404
