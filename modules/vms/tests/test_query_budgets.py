"""Query counts for VMS list endpoints, ensuring no N+1 query regression."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.vms.services.registration import request_or_create_visit

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, **session_kwargs):
    stub_iam(make_session(**session_kwargs))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_visit_list_query_budget(stub_iam, django_assert_num_queries):
    """Assert query count is constant and does not scale linearly with visits count (select_related)."""
    now = timezone.now()
    for i in range(5):
        request_or_create_visit(
            visitor_data={
                "first_name": f"User{i}",
                "last_name": "Test",
                "phone": f"90000000{i:02d}",
                "email": f"u{i}@example.com",
                "id_type": "aadhaar",
                "id_number": f"IDNUM{i:05d}",
            },
            host_user_id=10,
            purpose=f"Meeting {i}",
            valid_from=now,
            valid_to=now + timedelta(hours=2),
        )

    client = _auth_client(stub_iam, user_id=10, modules=("vms",), permissions=("vms.visit.create",))

    # Expect efficient single query with select_related for visits list
    with django_assert_num_queries(1):
        res = client.get("/api/v1/vms/visits/")
        assert res.status_code == 200
        assert len(res.data) == 5
