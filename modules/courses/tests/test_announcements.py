"""Tests for Course Announcements API, authorization, and business rules (CFR-LMS-005)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.models import CourseAnnouncement
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.fixture
def test_setup():
    ws1 = make_workspace(code="CS201", title="Data Structures")
    ws2 = make_workspace(code="CS301", title="Operating Systems")

    # ws1 members:
    # Faculty instructor: user 10
    add_member(ws1, user_id=10, role="instructor")
    # TA: user 20
    add_member(ws1, user_id=20, role="ta")
    # Student: user 30
    add_member(ws1, user_id=30, role="student")
    # Observer: user 40
    add_member(ws1, user_id=40, role="observer")

    # ws2 faculty instructor: user 11
    add_member(ws2, user_id=11, role="instructor")

    return ws1, ws2


@pytest.mark.django_db
def test_faculty_can_create_announcement(stub_iam, test_setup):
    """1. Authorized faculty can create announcements (AFR-LMS-005.1)."""
    ws1, _ = test_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={
            "title": "Welcome to CS201",
            "body": "First class will be held on Monday at 10 AM.",
            "is_published": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["title"] == "Welcome to CS201"
    assert data["body"] == "First class will be held on Monday at 10 AM."
    assert data["is_published"] is True
    assert data["published_at"] is not None
    assert data["created_by_id"] == 10

    # Verify saved in DB
    ann = CourseAnnouncement.objects.get(id=data["id"])
    assert ann.workspace == ws1
    assert ann.title == "Welcome to CS201"


@pytest.mark.django_db
def test_faculty_can_edit_and_delete_announcements(stub_iam, test_setup):
    """2. Authorized faculty can edit and delete their announcements."""
    ws1, _ = test_setup
    ann = CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Initial Title",
        body="Initial Body",
        is_published=False,
        created_by_id=10,
    )

    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Edit announcement and publish it
    patch_res = client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann.id}",
        data={
            "title": "Updated Title",
            "body": "Updated Body",
            "is_published": True,
        },
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    data = patch_res.json()
    assert data["title"] == "Updated Title"
    assert data["body"] == "Updated Body"
    assert data["is_published"] is True
    assert data["published_at"] is not None

    # Delete announcement
    del_res = client.delete(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann.id}"
    )
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
    assert not CourseAnnouncement.objects.filter(id=ann.id).exists()


@pytest.mark.django_db
def test_faculty_cannot_manage_announcements_for_unauthorized_courses(stub_iam, test_setup):
    """3. Faculty cannot manage announcements for unauthorized courses (BR-LMS-001)."""
    ws1, ws2 = test_setup
    # Faculty 11 is instructor for ws2, NOT ws1
    client = _auth_client(
        stub_iam,
        user_id=11,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={"title": "Hacked", "body": "Should fail", "is_published": True},
        format="json",
    )
    assert res.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_students_can_view_published_announcements(stub_iam, test_setup):
    """4. Students can view published announcements for their courses (CFR-LMS-005)."""
    ws1, _ = test_setup
    CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Class Exam Schedule",
        body="Midsem will be next week.",
        is_published=True,
        created_by_id=10,
    )

    client = _auth_client(
        stub_iam,
        user_id=30,  # Enrolled student
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    res = client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Class Exam Schedule"


@pytest.mark.django_db
def test_students_cannot_view_draft_announcements(stub_iam, test_setup):
    """5. Students cannot view draft or unpublished announcements (BR-LMS-005, BR-LMS-008)."""
    ws1, _ = test_setup
    CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Draft Announcement",
        body="Private draft content.",
        is_published=False,
        created_by_id=10,
    )
    CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Published Announcement",
        body="Public content.",
        is_published=True,
        created_by_id=10,
    )

    student_client = _auth_client(
        stub_iam,
        user_id=30,  # Student
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    res = student_client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Published Announcement"

    # Faculty sees both
    faculty_client = _auth_client(
        stub_iam,
        user_id=10,  # Faculty
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    fac_res = faculty_client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements")
    assert fac_res.json()["count"] == 2


@pytest.mark.django_db
def test_tas_cannot_create_or_modify_announcements(stub_iam, test_setup):
    """6. TAs can view published announcements but cannot create, edit, or delete them (BR-LMS-004)."""
    ws1, _ = test_setup
    ann = CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Prof Announcement",
        body="Notice",
        is_published=True,
        created_by_id=10,
    )

    ta_client = _auth_client(
        stub_iam,
        user_id=20,  # TA
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # TA can view
    get_res = ta_client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["count"] == 1

    # TA attempts to create -> Forbidden
    post_res = ta_client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={"title": "TA Announcement", "body": "Test"},
        format="json",
    )
    assert post_res.status_code == status.HTTP_403_FORBIDDEN

    # TA attempts to edit -> Forbidden
    patch_res = ta_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann.id}",
        data={"title": "TA Modified"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN

    # TA attempts to delete -> Forbidden
    del_res = ta_client.delete(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann.id}"
    )
    assert del_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_observers_read_only_access(stub_iam, test_setup):
    """7. Observers can view published announcements but cannot modify them (BR-LMS-003, CFR-LMS-015)."""
    ws1, _ = test_setup
    ann = CourseAnnouncement.objects.create(
        workspace=ws1,
        title="Observed Announcement",
        body="Public syllabus update",
        is_published=True,
        created_by_id=10,
    )

    obs_client = _auth_client(
        stub_iam,
        user_id=40,  # Observer
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Can view
    res = obs_client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] == 1

    # Cannot modify
    patch_res = obs_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann.id}",
        data={"title": "Observer Edit"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cross_course_id_guessing_returns_404(stub_iam, test_setup):
    """8. Users cannot access announcements belonging to unrelated courses (404)."""
    ws1, ws2 = test_setup
    ann2 = CourseAnnouncement.objects.create(
        workspace=ws2,
        title="Secret CS301 Announcement",
        body="Only for CS301",
        is_published=True,
        created_by_id=11,
    )

    # Student 30 is only in ws1 (CS201), guesses ws1 path with ann2 id
    student_client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Accessing ann2 through ws1 route returns 404
    res = student_client.get(f"/api/v1/courses/workspaces/{ws1.id}/announcements/{ann2.id}")
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # Accessing ws2 route directly also returns 404 because not a member
    res2 = student_client.get(f"/api/v1/courses/workspaces/{ws2.id}/announcements/{ann2.id}")
    assert res2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_invalid_announcement_data_rejected(stub_iam, test_setup):
    """9. Invalid or empty announcement content is rejected."""
    ws1, _ = test_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Empty title
    res_empty_title = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={"title": "   ", "body": "Valid body"},
        format="json",
    )
    assert res_empty_title.status_code == status.HTTP_400_BAD_REQUEST

    # Empty body
    res_empty_body = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={"title": "Valid title", "body": "   "},
        format="json",
    )
    assert res_empty_body.status_code == status.HTTP_400_BAD_REQUEST

    # Exceeds max length
    res_long_title = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/announcements",
        data={"title": "A" * 201, "body": "Valid body"},
        format="json",
    )
    assert res_long_title.status_code == status.HTTP_400_BAD_REQUEST

