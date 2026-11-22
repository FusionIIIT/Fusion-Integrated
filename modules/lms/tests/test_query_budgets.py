"""Query budget tests: assert max query count per list endpoint."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.models import CourseMaterial

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def many_materials():
    for i in range(20):
        CourseMaterial.objects.create(
            course_id=1, user_id=1, title=f"Mat {i}", material_type="note",
            content="x", status="published",
        )


def test_materials_list_query_budget(stub_iam, django_assert_num_queries, many_materials):
    c = _client(stub_iam, user_id=100, modules=("lms",),
                permissions=("lms.material.view",))
    with django_assert_num_queries(1):
        resp = c.get("/api/v1/lms/courses/1/materials/")
    assert resp.status_code == 200
