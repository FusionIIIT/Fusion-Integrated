"""Request and service-record list endpoints must not generate N+1 database queries."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import ClaimDetail, EmployeeServiceRecord, HRRequest

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
                user_id=10, family="ltc", subtype="advance",
                state="awaiting_hr_verification",
            )
            ClaimDetail.objects.create(
                request=request, claim_type="ltc", subtype="advance",
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
