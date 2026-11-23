"""Assert list query counts stay bounded as the visible application set grows."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.models import PatentApplication

pytestmark = pytest.mark.django_db


def _application(index: int) -> PatentApplication:
    return PatentApplication.objects.create(
        application_no=f"PMS-QB-{index:03d}",
        title=f"Query budget application {index}",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Engineering",
        applicant_user_id=10_000 + index,
    )


def test_application_list_query_count_is_bounded_at_two_and_twenty(stub_iam):
    for index in range(2):
        _application(index)

    stub_iam(
        make_session(
            user_id=9001,
            kind="staff",
            roles=("pcc_admin",),
            active_role="pcc_admin",
            permissions=("pms.workflow.monitor", "pms.application.view"),
            modules=("pms",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    with CaptureQueriesContext(connection) as two_rows:
        response = client.get("/api/v1/pms/applications/")
    assert response.status_code == 200

    for index in range(2, 20):
        _application(index)

    with CaptureQueriesContext(connection) as twenty_rows:
        response = client.get("/api/v1/pms/applications/")
    assert response.status_code == 200
    assert len(twenty_rows) == len(two_rows), (
        f"application list used {len(two_rows)} queries for 2 rows and "
        f"{len(twenty_rows)} for 20 rows"
    )
