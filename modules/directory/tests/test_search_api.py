"""Who may read the institute directory."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), kind="student", uid=1001):
    stub_iam(make_session(user_id=uid, kind=kind, permissions=permissions,
                          modules=("placement_cell",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def people():
    for i, (name, roll) in enumerate([("ABHAY SINGH", "21BEC002"),
                                      ("BHARAT RAO", "21BCS010")]):
        UserRef.objects.create(user_id=4000 + i, username=roll,
                               display_name=name, kind="student",
                               email=f"{roll.lower()}@iiitdmj.ac.in",
                               is_active=True)


def test_a_student_cannot_enumerate_the_directory(stub_iam, people):
    """Names, roll numbers and institute emails for the whole cohort."""
    c = _client(stub_iam)
    assert c.get("/api/v1/directory/users?limit=100").status_code == 403


def test_staff_may_search(stub_iam, people):
    c = _client(stub_iam, permissions=("directory.user.search",),
                kind="staff", uid=9)
    body = c.get("/api/v1/directory/users?q=abhay").json()
    assert [r["username"] for r in body["results"]] == ["21BEC002"]


def test_an_empty_query_returns_nothing(stub_iam, people):
    """A blank q used to mean "everyone", which is a dump, not a type-ahead."""
    c = _client(stub_iam, permissions=("directory.user.search",),
                kind="staff", uid=9)
    assert c.get("/api/v1/directory/users").json()["results"] == []
