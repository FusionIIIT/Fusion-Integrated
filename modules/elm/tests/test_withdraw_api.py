from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication


pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), uid=126):
    stub_iam(
        make_session(
            user_id=uid,
            kind="employee",
            permissions=permissions,
            modules=("elm",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _application(user_id=126, status="submitted"):
    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        requested_days=Decimal("1.0"),
        reason="Personal work",
        status=status,
    )


def test_employee_can_withdraw_own_pending_application(stub_iam):
    application = _application()
    client = _client(
        stub_iam,
        permissions=("elm.application.withdraw",),
    )

    response = client.post(
        f"/api/v1/elm/applications/{application.pk}/withdraw"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"

    application.refresh_from_db()
    assert application.status == "withdrawn"


def test_employee_cannot_withdraw_another_employees_application(stub_iam):
    application = _application(user_id=999)
    client = _client(
        stub_iam,
        permissions=("elm.application.withdraw",),
    )

    response = client.post(
        f"/api/v1/elm/applications/{application.pk}/withdraw"
    )

    assert response.status_code == 404


def test_approved_application_cannot_be_withdrawn(stub_iam):
    application = _application(status="approved")
    client = _client(
        stub_iam,
        permissions=("elm.application.withdraw",),
    )

    response = client.post(
        f"/api/v1/elm/applications/{application.pk}/withdraw"
    )

    assert response.status_code == 400

    application.refresh_from_db()
    assert application.status == "approved"


def test_withdrawn_application_cannot_be_withdrawn_again(stub_iam):
    application = _application(status="withdrawn")
    client = _client(
        stub_iam,
        permissions=("elm.application.withdraw",),
    )

    response = client.post(
        f"/api/v1/elm/applications/{application.pk}/withdraw"
    )

    assert response.status_code == 400

    application.refresh_from_db()
    assert application.status == "withdrawn"