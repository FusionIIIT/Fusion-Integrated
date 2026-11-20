"""PC-BR-022: the module grant alone opens nothing; every endpoint also needs a permission."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db

API = "/api/v1/placement"
READS = ["postings", "postings/1", "applications/1/history", "documents/1/download",
         "profiles/1", "companies", "interviews/rounds", "offers", "announcements",
         "seasons", "stats", "stats/trends", "records/office", "applications"]
WRITES = ["postings/1/publish", "postings/1/submit", "applications/1/transition",
          "applications/bulk-transition", "interviews/rounds/1/candidates",
          "interviews/rounds/1/outcome", "offers/issue", "offers/1/respond"]


@pytest.fixture
def granted_only(stub_iam):
    # PC-AFR-061: a role holding the module but no placement permission.
    stub_iam(make_session(user_id=5, kind="staff", modules=("placement",), permissions=()))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.mark.parametrize("path", READS)
def test_a_read_needs_a_permission(granted_only, path):
    assert granted_only.get(f"{API}/{path}").status_code == 403


@pytest.mark.parametrize("path", WRITES)
def test_a_write_needs_a_permission(granted_only, path):
    assert granted_only.post(f"{API}/{path}", {}, format="json").status_code == 403
