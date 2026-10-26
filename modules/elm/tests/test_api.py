import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveType

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id):
    stub_iam(
        make_session(user_id=user_id, modules=("elm",))
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


@pytest.fixture
def leave_type():
    return LeaveType.objects.create(leave_type="CL")


@pytest.fixture
def application(leave_type):
    return LeaveApplication.objects.create(
        applicant_id=1001,
        leave_type=leave_type,
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="Personal work",
        status="AWAITING_APPROVAL",
    )


def test_employee_cannot_withdraw_another_employees_application(
    stub_iam, application
):
    client = _client(stub_iam, user_id=2002)

    response = client.post(
        f"/api/v1/elm/applications/{application.id}/withdraw"
    )

    assert response.status_code == 404

    application.refresh_from_db()
    assert application.status == "AWAITING_APPROVAL"


def test_employee_can_withdraw_their_own_pending_application(
    stub_iam, application
):
    client = _client(stub_iam, user_id=1001)

    response = client.post(
        f"/api/v1/elm/applications/{application.id}/withdraw"
    )

    assert response.status_code == 200

    application.refresh_from_db()
    assert application.status == "WITHDRAWN"


def test_withdrawing_a_nonexistent_application_returns_404(stub_iam):
    client = _client(stub_iam, user_id=1001)

    response = client.post(
        "/api/v1/elm/applications/999999/withdraw"
    )

    assert response.status_code == 404
