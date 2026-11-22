"""Tests for Course Materials API, authorization, and release scheduling (CFR-LMS-003, CFR-LMS-004)."""
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.models import CourseMaterial, CourseMaterialSection
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.fixture
def materials_setup():
    ws1 = make_workspace(code="CS201", title="Data Structures")
    ws2 = make_workspace(code="CS301", title="Operating Systems")

    add_member(ws1, user_id=10, role="instructor")
    add_member(ws1, user_id=20, role="ta")
    add_member(ws1, user_id=30, role="student")
    add_member(ws1, user_id=40, role="observer")

    add_member(ws2, user_id=11, role="instructor")

    return ws1, ws2


@pytest.mark.django_db
def test_faculty_can_create_materials_and_sections(stub_iam, materials_setup):
    """Faculty can create sections and supported materials (note, link)."""
    ws1, _ = materials_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Create Section
    sec_res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/sections",
        data={"title": "Module 1: Binary Trees", "sort_order": 1},
        format="json",
    )
    assert sec_res.status_code == status.HTTP_201_CREATED
    sec_id = sec_res.json()["id"]

    # Create Note Material
    note_res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/materials",
        data={
            "title": "Lecture 1 Notes",
            "material_type": "note",
            "content": "Trees are hierarchical data structures.",
            "section_id": sec_id,
            "is_published": True,
        },
        format="json",
    )
    assert note_res.status_code == status.HTTP_201_CREATED
    assert note_res.json()["title"] == "Lecture 1 Notes"

    # Create Link Material
    link_res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/materials",
        data={
            "title": "Reference Documentation",
            "material_type": "link",
            "link_url": "https://docs.python.org/3/",
            "section_id": sec_id,
            "is_published": True,
        },
        format="json",
    )
    assert link_res.status_code == status.HTTP_201_CREATED
    assert link_res.json()["link_url"] == "https://docs.python.org/3/"


@pytest.mark.django_db
def test_scheduled_materials_visibility_rules(stub_iam, materials_setup):
    """Scheduled materials unavailable to students until release_at (BR-LMS-005, BR-LMS-006)."""
    ws1, _ = materials_setup
    now = timezone.now()

    # Future release material
    mat_future = CourseMaterial.objects.create(
        workspace=ws1,
        title="Future Lecture Slides",
        material_type="note",
        content="Future content",
        is_published=True,
        release_at=now + timedelta(days=2),
        created_by_id=10,
    )

    # Already released material
    mat_past = CourseMaterial.objects.create(
        workspace=ws1,
        title="Past Lecture Slides",
        material_type="note",
        content="Available content",
        is_published=True,
        release_at=now - timedelta(hours=1),
        created_by_id=10,
    )

    # Student client
    stu_client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    res = stu_client.get(f"/api/v1/courses/workspaces/{ws1.id}/materials")
    assert res.status_code == status.HTTP_200_OK
    items = res.json()["results"]
    titles = [i["title"] for i in items]
    assert "Past Lecture Slides" in titles
    assert "Future Lecture Slides" not in titles

    # Faculty client sees both
    fac_client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    fac_res = fac_client.get(f"/api/v1/courses/workspaces/{ws1.id}/materials")
    fac_titles = [i["title"] for i in fac_res.json()["results"]]
    assert "Past Lecture Slides" in fac_titles
    assert "Future Lecture Slides" in fac_titles


@pytest.mark.django_db
def test_ta_and_observer_material_restrictions(stub_iam, materials_setup):
    """TAs and Observers have read-only access to published materials (BR-LMS-003, BR-LMS-004)."""
    ws1, _ = materials_setup
    mat = CourseMaterial.objects.create(
        workspace=ws1,
        title="Published Material",
        material_type="note",
        content="Read only",
        is_published=True,
        created_by_id=10,
    )

    # TA cannot create
    ta_client = _auth_client(
        stub_iam,
        user_id=20,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res = ta_client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/materials",
        data={"title": "TA Material", "material_type": "note", "content": "test"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Observer cannot edit
    obs_client = _auth_client(
        stub_iam,
        user_id=40,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res2 = obs_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/materials/{mat.id}",
        data={"title": "Hacked"},
        format="json",
    )
    assert res2.status_code == status.HTTP_403_FORBIDDEN

