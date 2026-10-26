from datetime import date
from decimal import Decimal

import pytest
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.domain.leave import Stage
from modules.elm.models import LeaveApplication, LeaveApprovalRoute

pytestmark = pytest.mark.django_db


def client_for(stub_iam, *, user_id, permissions=(), modules=("leave_elm",)):
    stub_iam(make_session(user_id=user_id, kind="staff", roles=("staff",),
                          permissions=permissions, modules=modules))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    return client


def application(employee_id):
    return LeaveApplication.objects.create(
        employee_id=employee_id, category="CL", start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1), chargeable_days=Decimal(1), reason="Test",
        current_step_order=1, current_stage=Stage.UNIT_HEAD,
    )


def test_review_api_requires_module_and_review_permission(stub_iam):
    c = client_for(stub_iam, user_id=9)
    assert c.get("/api/v1/leave/applications/pending").status_code == 403
    c = client_for(stub_iam, user_id=9, permissions=("leave_elm.application.review",), modules=())
    assert c.get("/api/v1/leave/applications/pending").status_code == 403


def test_review_api_returns_only_current_assignments(stub_iam):
    assigned, other = application(7), application(8)
    for employee_id, approver_id in ((7, 9), (8, 10)):
        LeaveApprovalRoute.objects.create(employee_id=employee_id, category="CL",
                                          step_order=1, stage=Stage.UNIT_HEAD,
                                          approver_user_id=approver_id)
    c = client_for(stub_iam, user_id=9, permissions=("leave_elm.application.review",))
    rows = c.get("/api/v1/leave/applications/pending").json()
    assert [row["id"] for row in rows] == [assigned.id]
    assert other.id not in [row["id"] for row in rows]


def test_own_applications_api_hides_other_employees(stub_iam):
    mine, other = application(7), application(8)
    c = client_for(stub_iam, user_id=7, permissions=("leave_elm.application.view_self",))
    rows = c.get("/api/v1/leave/applications").json()
    assert [row["id"] for row in rows] == [mine.id]
    assert other.id not in [row["id"] for row in rows]


def test_leave_types_openapi_response_is_an_array():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    response = schema["paths"]["/api/v1/leave/types"]["get"]["responses"]["200"]
    assert response["content"]["application/json"]["schema"]["type"] == "array"
    assert response["content"]["application/json"]["schema"]["items"]["$ref"].endswith(
        "/LeaveType"
    )
