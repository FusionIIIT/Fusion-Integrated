import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import IamUnavailable, UserRef
from modules.department.models import Announcement
from modules.department.permissions import VIEW_ANNOUNCEMENT

pytestmark = pytest.mark.django_db
URL = "/api/v1/department/announcements"


@pytest.fixture
def reader(stub_iam):
    session = make_session(modules=["department"], permissions=[VIEW_ANNOUNCEMENT])
    identity = UserRef(session.user_id, "student", "Student", "student",
                       department="Computing", programme="BTech", batch_year=2024)
    fake = stub_iam(session=session, users={identity.user_id: identity})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")
    return client, fake


@pytest.mark.parametrize("target", [
    {"department": "Design"},
    {"target_roles": ["faculty"]},
    {"target_programmes": ["MTech"]},
    {"target_batch_years": [2025]},
    {"is_active": False},
])
def test_announcement_list_only_includes_active_relevant_rows(reader, target):
    """UC-DEPT-001, BR-DEPT-002, AFR-DEPT-002/003."""
    client, _ = reader
    relevant = Announcement.objects.create(
        department="Computing", content="Course registration opens",
        target_roles=["student", "faculty"], target_programmes=["BTech"],
        target_batch_years=[2024, 2026],
    )
    Announcement.objects.create(**({"department": "Computing", "content": "Other audience"} | target))

    response = client.get(URL)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [relevant.id]
    assert "no-store" in response["Cache-Control"]


def test_nonapplicable_target_axes_and_missing_department(reader):
    """BR-DEPT-002 and UC-DEPT-001 empty state."""
    client, fake = reader
    relevant = Announcement.objects.create(department="Computing", content="All Computing users")
    assert [row["id"] for row in client.get(URL).json()["results"]] == [relevant.id]

    fake.users.clear()
    assert client.get(URL).json()["results"] == []


@pytest.mark.parametrize(("modules", "permissions"), [
    ([], [VIEW_ANNOUNCEMENT]),
    (["department"], []),
])
def test_announcement_list_requires_both_grants(reader, modules, permissions):
    client, fake = reader
    fake.session = make_session(modules=modules, permissions=permissions)

    assert client.get(URL).status_code == 403


def test_announcement_list_handles_identity_outage(reader, monkeypatch):
    client, fake = reader

    def unavailable(user_ids):
        raise IamUnavailable("temporarily unavailable")

    monkeypatch.setattr(fake, "get_users", unavailable)
    assert client.get(URL).status_code == 503


def test_only_acting_role_controls_department_access(reader):
    client, fake = reader
    fake.session = make_session(modules=["department"], permissions=[VIEW_ANNOUNCEMENT],
                                roles=["student", "staff"], active_role="staff")
    assert client.get(URL).status_code == 403
    assert client.get("/api/v1/department/access").json() == {"permissions": []}

    fake.session = make_session(modules=["department"], permissions=[VIEW_ANNOUNCEMENT],
                                roles=["student", "ug_student"], active_role="ug_student")
    assert client.get("/api/v1/department/access").json() == {"permissions": [VIEW_ANNOUNCEMENT]}
    assert client.get(URL).status_code == 200
