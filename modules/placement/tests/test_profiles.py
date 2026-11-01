"""Student placement profiles and structured resume generation (PC-UC-001/023)."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import StudentPlacementProfile

pytestmark = pytest.mark.django_db


def _client(stub_iam, uid=1001):
    stub_iam(make_session(user_id=uid, kind="student", modules=("placement_cell",),
                          permissions=("placement_cell.application.view_self",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_student_can_create_and_update_own_profile(stub_iam):
    client = _client(stub_iam)
    response = client.put("/api/v1/placement/profile", {
        "summary": "Backend developer",
        "skills": ["Python", "Django"],
        "projects": [{"title": "Campus portal", "description": "Built APIs"}],
        "achievements": [{"title": "Hackathon finalist"}],
        "certifications": [{"name": "Cloud fundamentals", "issuer": "Example"}],
        "links": [{"label": "GitHub", "url": "https://github.com/example"}],
    }, format="json")

    assert response.status_code == 200
    profile = StudentPlacementProfile.objects.get(user_id=1001)
    assert profile.skills == ["Python", "Django"]
    assert profile.projects[0]["title"] == "Campus portal"

    response = client.patch("/api/v1/placement/profile", {
        "summary": "Backend and platform developer",
    }, format="json")
    assert response.status_code == 200
    profile.refresh_from_db()
    assert profile.skills == ["Python", "Django"]
    assert profile.summary.startswith("Backend and platform")


def test_student_cannot_access_another_students_profile(stub_iam):
    StudentPlacementProfile.objects.create(user_id=2002, skills=["Secret"])
    response = _client(stub_iam, uid=1001).get("/api/v1/placement/profile")
    assert response.status_code == 200
    assert "Secret" not in str(response.json())


def test_student_can_generate_a_structured_resume(stub_iam, user_ref):
    StudentPlacementProfile.objects.create(
        user_id=1001, summary="Backend developer", skills=["Python"])
    stub_iam(make_session(user_id=1001, kind="student", modules=("placement_cell",),
                          permissions=("placement_cell.application.view_self",)),
             users={1001: user_ref(1001)})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/placement/profile/resume")

    assert response.status_code == 200
    assert response.json()["summary"] == "Backend developer"
    assert response.json()["skills"] == ["Python"]
    assert response.json()["name"] == "Asha Verma"


def test_resume_generation_requires_saved_content(stub_iam, user_ref):
    StudentPlacementProfile.objects.create(user_id=1001)
    stub_iam(make_session(user_id=1001, kind="student", modules=("placement_cell",),
                          permissions=("placement_cell.application.view_self",)),
             users={1001: user_ref(1001)})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/placement/profile/resume")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "resume_content_missing"
