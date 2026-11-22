"""Request and service-record list endpoints must not generate N+1 database queries."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from modules.hreis.models import (
    ApprovalRouteStep,
    AuditEvent,
    ClaimDetail,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    Notification,
)
from modules.hreis.tests.actors import make_session

pytestmark = pytest.mark.django_db


def admin_client(stub_iam, *, user_id=99, role="hradmin", permissions=()):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="staff" if role == "hradmin" else "faculty",
            roles=(role,),
            active_role=role,
            permissions=permissions,
            modules=("hreis",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return client


def measured_list(client, uri, expected):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(uri)
    assert response.status_code == 200, response.content
    assert len(response.json()["results"]) == expected
    return len(queries)


def test_hr_uc_005_claim_summary_request_list_query_count_stays_constant(stub_iam):
    """HR-UC-005: claim summaries should scale without per-request database queries."""
    client = admin_client(stub_iam, role="faculty", user_id=10, permissions=("hreis.request.view",))

    def create_claim_rows(start, stop):
        for index in range(start, stop):
            request = HRRequest.objects.create(
                user_id=10,
                family="ltc",
                subtype="advance",
                state="awaiting_hr_verification",
            )
            ClaimDetail.objects.create(
                request=request,
                claim_type="ltc",
                subtype="advance",
                prescribed_form_reference=f"form-{index}",
            )

    create_claim_rows(0, 2)
    few = measured_list(client, "/api/v1/hreis/requests/", 2)
    create_claim_rows(2, 20)
    many = measured_list(client, "/api/v1/hreis/requests/", 20)
    assert many == few, f"N+1 request queries: 2 rows used {few}, 20 rows used {many}"
    assert many <= 6, f"Unexpectedly expensive request list: {many} database queries"


def test_hr_uc_002_service_record_list_query_count_stays_constant(stub_iam):
    """HR-UC-002 / HR-UC-001: authorized record lists should scale at a fixed query cost."""
    client = admin_client(stub_iam, permissions=("hreis.service_record.view",))

    def create_records(start, stop):
        for index in range(start, stop):
            EmployeeServiceRecord.objects.create(
                user_id=100 + index,
                department="CSE",
                designation_snapshot="Faculty",
                appointment_details={},
            )

    create_records(0, 2)
    few = measured_list(client, "/api/v1/hreis/service-records/", 2)
    create_records(2, 20)
    many = measured_list(client, "/api/v1/hreis/service-records/", 20)
    assert many == few, f"N+1 service-record queries: 2 rows used {few}, 20 rows used {many}"
    assert many <= 6, f"Unexpectedly expensive record list: {many} database queries"


@pytest.mark.parametrize(
    "name,role,permission",
    [
        ("requests/approvals", "Registrar", "hreis.approval.view"),
        ("notifications", "hradmin", "hreis.notification.view"),
        ("audit", "hradmin", "hreis.audit.view"),
        ("compliance/requests", "hradmin", "hreis.audit.view"),
        ("policies", "hradmin", "hreis.policy.view"),
    ],
)
def test_each_remaining_list_has_constant_populated_query_budget(stub_iam, name, role, permission):
    permissions = (permission, "hreis.request.view", "hreis.leave.approve")
    client = admin_client(stub_iam, user_id=99, role=role, permissions=permissions)

    def populate(start, stop):
        for index in range(start, stop):
            if name in {"requests/approvals", "compliance/requests"}:
                row = HRRequest.objects.create(
                    user_id=100 + index, family="leave", state="pending_authority"
                )
                ApprovalRouteStep.objects.create(
                    request=row,
                    position=0,
                    designation="Registrar",
                    policy_version_label="synthetic",
                )
            elif name == "notifications":
                Notification.objects.create(
                    recipient_user_id=99,
                    event_key=f"budget-{index}",
                    title="Synthetic",
                    message="Synthetic",
                )
            elif name == "audit":
                AuditEvent.objects.create(
                    event_key=f"budget-{index}",
                    action="synthetic",
                    resource_kind="test",
                    resource_id=index,
                )
            else:
                start_at = timezone.now() - timedelta(days=index + 1)
                HRPolicyVersion.objects.create(
                    family="leave",
                    version=index + 1,
                    effective_from=start_at,
                    effective_until=start_at + timedelta(hours=1),
                    parameters={},
                    approved_by_user_id=99,
                    approved_designation="hradmin",
                )

    populate(0, 2)
    few = measured_list(client, f"/api/v1/hreis/{name}/", 2)
    populate(2, 20)
    many = measured_list(client, f"/api/v1/hreis/{name}/", 20)
    assert many == few, f"{name}: 2 rows={few}, 20 rows={many}"
    assert many <= 6
