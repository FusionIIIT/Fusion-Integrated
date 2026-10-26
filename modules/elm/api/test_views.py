"""API tests for employee self-service leave management."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.models import LeaveApplication, LeaveBalance, LeavePolicy, LeaveTransition

pytestmark = pytest.mark.django_db

APPLICATIONS_URL = "/api/v1/elm/applications/"
BALANCES_URL = "/api/v1/elm/balances/"
SUBMIT_URL = "/api/v1/elm/submit/"

VIEW_PERMISSION = "elm.leave.view_self"
APPLY_PERMISSION = "elm.leave.apply"


def make_client(
    stub_iam,
    *,
    user_id=1001,
    permissions=(),
    modules=("elm",),
    kind="staff",
):
    """Authenticate through the same IAM fixture used by the rest of Fusion."""
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            modules=modules,
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def make_staff(user_id):
    return UserRef.objects.create(
        user_id=user_id,
        username=f"staff{user_id}",
        display_name=f"Staff {user_id}",
        kind="staff",
        is_active=True,
    )


def response_rows(response):
    """Support both paginated and unpaginated DRF list responses."""
    body = response.json()
    if isinstance(body, dict):
        return body.get("results", body)
    return body


def test_unauthenticated_access_is_denied():
    response = APIClient().get(APPLICATIONS_URL)

    assert response.status_code == 401


def test_module_grant_is_required(stub_iam):
    client = make_client(
        stub_iam,
        permissions=(VIEW_PERMISSION,),
        modules=(),
    )

    response = client.get(APPLICATIONS_URL)

    assert response.status_code == 403


def test_view_permission_is_required(stub_iam):
    client = make_client(stub_iam, permissions=())

    response = client.get(APPLICATIONS_URL)

    assert response.status_code == 403


def test_employee_sees_only_their_own_applications(stub_iam):
    LeaveApplication.objects.create(
        applicant_user_id=1001,
        leave_code="CL",
        start_date="2026-10-27",
        end_date="2026-10-27",
        purpose="Personal work",
    )
    LeaveApplication.objects.create(
        applicant_user_id=2002,
        leave_code="CL",
        start_date="2026-10-28",
        end_date="2026-10-28",
        purpose="Another employee's leave",
    )

    client = make_client(stub_iam, permissions=(VIEW_PERMISSION,))
    response = client.get(APPLICATIONS_URL)

    assert response.status_code == 200
    rows = response_rows(response)
    assert len(rows) == 1
    assert rows[0]["applicant_user_id"] == 1001


def test_employee_sees_only_their_own_balances(stub_iam):
    LeaveBalance.objects.create(
        user_id=1001,
        leave_code="CL",
        leave_year=2026,
        opening_balance="8.00",
    )
    LeaveBalance.objects.create(
        user_id=2002,
        leave_code="CL",
        leave_year=2026,
        opening_balance="5.00",
    )

    client = make_client(stub_iam, permissions=(VIEW_PERMISSION,))
    response = client.get(BALANCES_URL)

    assert response.status_code == 200
    rows = response_rows(response)
    assert len(rows) == 1
    assert rows[0]["user_id"] == 1001
    assert rows[0]["available"] == "8.00"


def test_employee_can_submit_their_own_leave(stub_iam):
    make_staff(1001)
    LeavePolicy.objects.create(
        code="CL",
        name="Casual Leave",
        annual_entitlement="8.00",
        active=True,
    )
    LeaveBalance.objects.create(
        user_id=1001,
        leave_code="CL",
        leave_year=2026,
        opening_balance="8.00",
    )

    client = make_client(
        stub_iam,
        permissions=(APPLY_PERMISSION,),
    )
    response = client.post(
        SUBMIT_URL,
        {
            "leave_code": "CL",
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
            "half_day": "full",
            "purpose": "Personal work",
        },
        format="json",
    )

    assert response.status_code == 201, response.content.decode()
    assert LeaveApplication.objects.count() == 1

    application = LeaveApplication.objects.get()
    assert application.applicant_user_id == 1001
    assert application.purpose == "Personal work"
    assert application.status == "unit_head_review"


def test_submission_requires_apply_permission(stub_iam):
    client = make_client(stub_iam, permissions=())

    response = client.post(
        SUBMIT_URL,
        {
            "leave_code": "CL",
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
            "purpose": "Personal work",
        },
        format="json",
    )

    assert response.status_code == 403
    assert LeaveApplication.objects.count() == 0


def make_pending_application(user_id=1001, status="unit_head_review"):
    return LeaveApplication.objects.create(
        applicant_user_id=user_id,
        leave_code="CL",
        start_date="2026-10-27",
        end_date="2026-10-27",
        purpose="Personal work",
        status=status,
    )


def test_applicant_can_withdraw_pending_leave(stub_iam):
    application = make_pending_application()
    client = make_client(
        stub_iam,
        permissions=("elm.leave.view_self", "elm.leave.withdraw_self"),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/withdraw/",
        {},
        format="json",
    )

    assert response.status_code == 200, response.content.decode()
    application.refresh_from_db()
    assert application.status == "withdrawn"

    transition = LeaveTransition.objects.get(
        application=application,
        action="withdraw",
    )
    assert transition.from_status == "unit_head_review"
    assert transition.to_status == "withdrawn"
    assert transition.actor_user_id == 1001


def test_applicant_cannot_withdraw_another_employees_leave(stub_iam):
    application = make_pending_application(user_id=2002)
    client = make_client(
        stub_iam,
        permissions=("elm.leave.view_self", "elm.leave.withdraw_self"),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/withdraw/",
        {},
        format="json",
    )

    assert response.status_code == 404
    application.refresh_from_db()
    assert application.status == "unit_head_review"
    assert not LeaveTransition.objects.filter(
        application=application,
        action="withdraw",
    ).exists()


def test_withdrawal_requires_its_specific_permission(stub_iam):
    application = make_pending_application()
    client = make_client(
        stub_iam,
        permissions=("elm.leave.view_self",),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/withdraw/",
        {},
        format="json",
    )

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == "unit_head_review"


def test_approved_leave_cannot_use_withdrawal_endpoint(stub_iam):
    application = make_pending_application(status="approved")
    client = make_client(
        stub_iam,
        permissions=("elm.leave.view_self", "elm.leave.withdraw_self"),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/withdraw/",
        {},
        format="json",
    )

    assert response.status_code == 409
    application.refresh_from_db()
    assert application.status == "approved"


def make_substitute_application(substitute_user_id=3003):
    return LeaveApplication.objects.create(
        applicant_user_id=1001,
        leave_code="CL",
        start_date="2026-10-27",
        end_date="2026-10-27",
        purpose="Personal work",
        status="awaiting_substitute",
        substitute_user_id=substitute_user_id,
    )


def test_substitute_can_accept_pending_leave(stub_iam):
    application = make_substitute_application()
    client = make_client(
        stub_iam,
        user_id=3003,
        permissions=("elm.leave.substitute_respond",),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/substitute-response/",
        {"response": "accept"},
        format="json",
    )

    assert response.status_code == 200, response.content.decode()
    application.refresh_from_db()
    assert application.status == "unit_head_review"

    transition = LeaveTransition.objects.get(
        application=application,
        action="substitute_accept",
    )
    assert transition.actor_user_id == 3003
    assert transition.metadata == {"response": "accept"}


def test_substitute_can_decline_pending_leave(stub_iam):
    application = make_substitute_application()
    client = make_client(
        stub_iam,
        user_id=3003,
        permissions=("elm.leave.substitute_respond",),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/substitute-response/",
        {"response": "decline"},
        format="json",
    )

    assert response.status_code == 200, response.content.decode()
    application.refresh_from_db()
    assert application.status == "applicant_action"

    transition = LeaveTransition.objects.get(
        application=application,
        action="substitute_decline",
    )
    assert transition.actor_user_id == 3003


def test_only_nominated_substitute_can_respond(stub_iam):
    application = make_substitute_application(substitute_user_id=3003)
    client = make_client(
        stub_iam,
        user_id=4004,
        permissions=("elm.leave.substitute_respond",),
    )

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/substitute-response/",
        {"response": "accept"},
        format="json",
    )

    assert response.status_code == 404
    application.refresh_from_db()
    assert application.status == "awaiting_substitute"


def test_substitute_response_requires_specific_permission(stub_iam):
    application = make_substitute_application()
    client = make_client(stub_iam, user_id=3003, permissions=())

    response = client.post(
        f"{APPLICATIONS_URL}{application.pk}/substitute-response/",
        {"response": "accept"},
        format="json",
    )

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == "awaiting_substitute"
