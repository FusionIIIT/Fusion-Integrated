"""Query count budget tests for list endpoints."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import SpacsCatalogueEntry

pytestmark = pytest.mark.django_db


def _client(stub_iam):
    stub_iam(
        make_session(
            user_id=1,
            kind="staff",
            roles=("spacs_convener",),
            active_role="spacs_convener",
            permissions=("spacs.scheme.view", "spacs.cycle.view"),
            modules=("spacs",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_scheme_list_query_budget(stub_iam, django_assert_num_queries):
    """Listing schemes should use a constant query budget regardless of row count."""
    for i in range(3):
        SpacsCatalogueEntry.objects.create(
            scheme_code=f"SCH-00{i}",
            name=f"Scheme {i}",
            scheme_type="scholarship",
            status="published",
        )

    c = _client(stub_iam)
    with django_assert_num_queries(1):
        c.get("/api/v1/spacs/schemes")

    for i in range(3, 8):
        SpacsCatalogueEntry.objects.create(
            scheme_code=f"SCH-00{i}",
            name=f"Scheme {i}",
            scheme_type="scholarship",
            status="published",
        )

    with django_assert_num_queries(1):
        c.get("/api/v1/spacs/schemes")
