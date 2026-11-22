"""Tests for Course Assignments API, authorization, and lifecycle (CFR-LMS-006, BR-LMS-004, BR-LMS-010)."""
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.models import CourseAssignment
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.fixture
def assignment_setup():
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
def test_faculty_can_create_assignment(stub_iam, assignment_setup):
    """1. Authorized faculty can create assignments (AFR-LMS-006.1)."""
    ws1, _ = assignment_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={
            "title": "Assignment 1: AVL Trees",
            "description": "Implement a self-balancing AVL tree.",
            "instructions": "Submit standard C++ source code.",
            "is_published": False,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["title"] == "Assignment 1: AVL Trees"
    assert data["description"] == "Implement a self-balancing AVL tree."
    assert data["instructions"] == "Submit standard C++ source code."
    assert data["is_published"] is False
    assert data["created_by_id"] == 10

    # Verify saved in DB
    asgn = CourseAssignment.objects.get(id=data["id"])
    assert asgn.workspace == ws1
    assert asgn.title == "Assignment 1: AVL Trees"


@pytest.mark.django_db
def test_faculty_can_edit_and_delete_assignments(stub_iam, assignment_setup):
    """2. Authorized faculty can edit and delete their assignments."""
    ws1, _ = assignment_setup
    asgn = CourseAssignment.objects.create(
        workspace=ws1,
        title="Assignment Draft",
        description="Draft Description",
        instructions="Draft Instructions",
        is_published=False,
        created_by_id=10,
    )

    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Edit assignment and publish it (CFR-LMS-006, BR-LMS-010)
    patch_res = client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}",
        data={
            "title": "Assignment 1: Red-Black Trees",
            "description": "Updated Description",
            "is_published": True,
        },
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    data = patch_res.json()
    assert data["title"] == "Assignment 1: Red-Black Trees"
    assert data["description"] == "Updated Description"
    assert data["is_published"] is True
    assert data["published_at"] is not None

    # Delete assignment
    del_res = client.delete(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}"
    )
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
    assert not CourseAssignment.objects.filter(id=asgn.id).exists()


@pytest.mark.django_db
def test_faculty_cannot_manage_assignments_for_unauthorized_courses(stub_iam, assignment_setup):
    """3. Faculty cannot manage assignments for unauthorized courses (BR-LMS-001)."""
    ws1, ws2 = assignment_setup
    # Faculty 11 is instructor for ws2, NOT ws1
    client = _auth_client(
        stub_iam,
        user_id=11,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={"title": "Unauthorized Assignment", "is_published": True},
        format="json",
    )
    assert res.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_students_can_view_published_assignments(stub_iam, assignment_setup):
    """4. Students can view published assignments for their courses."""
    ws1, _ = assignment_setup
    CourseAssignment.objects.create(
        workspace=ws1,
        title="Assignment 2: Graph BFS",
        description="Implement BFS traversal.",
        instructions="Python 3.12 script.",
        is_published=True,
        created_by_id=10,
    )

    client = _auth_client(
        stub_iam,
        user_id=30,  # Enrolled student
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    res = client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Assignment 2: Graph BFS"
    assert data["results"][0]["instructions"] == "Python 3.12 script."


@pytest.mark.django_db
def test_students_cannot_view_draft_assignments(stub_iam, assignment_setup):
    """5. Students cannot view draft or unpublished assignments (BR-LMS-010)."""
    ws1, _ = assignment_setup
    CourseAssignment.objects.create(
        workspace=ws1,
        title="Draft Exam Problem",
        description="Private draft problem.",
        is_published=False,
        created_by_id=10,
    )
    CourseAssignment.objects.create(
        workspace=ws1,
        title="Published Assignment",
        description="Public problem.",
        is_published=True,
        created_by_id=10,
    )

    student_client = _auth_client(
        stub_iam,
        user_id=30,  # Student
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    res = student_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Published Assignment"

    # Faculty sees both
    faculty_client = _auth_client(
        stub_iam,
        user_id=10,  # Faculty
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    fac_res = faculty_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert fac_res.json()["count"] == 2


@pytest.mark.django_db
def test_tas_cannot_create_or_modify_assignments(stub_iam, assignment_setup):
    """6. TAs can view published assignments but cannot modify or create them (BR-LMS-004, AFR-LMS-014.3)."""
    ws1, _ = assignment_setup
    asgn = CourseAssignment.objects.create(
        workspace=ws1,
        title="Prof Assignment",
        description="Prof problem",
        is_published=True,
        created_by_id=10,
    )

    ta_client = _auth_client(
        stub_iam,
        user_id=20,  # TA
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # TA can view published assignments
    get_res = ta_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["count"] == 1

    # TA attempts to create -> Forbidden
    post_res = ta_client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={"title": "TA Assignment"},
        format="json",
    )
    assert post_res.status_code == status.HTTP_403_FORBIDDEN

    # TA attempts to edit -> Forbidden
    patch_res = ta_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}",
        data={"title": "TA Modified"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN

    # TA attempts to delete -> Forbidden
    del_res = ta_client.delete(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}"
    )
    assert del_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_observers_read_only_access_to_assignments(stub_iam, assignment_setup):
    """7. Observers can view published assignments but cannot modify them (BR-LMS-003, CFR-LMS-015)."""
    ws1, _ = assignment_setup
    asgn = CourseAssignment.objects.create(
        workspace=ws1,
        title="Observed Assignment",
        description="Public problem",
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
    res = obs_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] == 1

    # Cannot modify
    patch_res = obs_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}",
        data={"title": "Observer Edit"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cross_course_assignment_guessing_returns_404(stub_iam, assignment_setup):
    """8. Users cannot access assignments belonging to unrelated courses (404)."""
    ws1, ws2 = assignment_setup
    asgn2 = CourseAssignment.objects.create(
        workspace=ws2,
        title="Secret CS301 Assignment",
        description="Only for CS301",
        is_published=True,
        created_by_id=11,
    )

    # Student 30 is only in ws1 (CS201), guesses ws1 path with asgn2 id
    student_client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Accessing asgn2 through ws1 route returns 404
    res = student_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn2.id}")
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # Accessing ws2 route directly also returns 404 because not a member
    res2 = student_client.get(f"/api/v1/courses/workspaces/{ws2.id}/assignments/{asgn2.id}")
    assert res2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_invalid_assignment_data_rejected(stub_iam, assignment_setup):
    """9. Invalid assignment data is rejected (empty title, max length exceeded)."""
    ws1, _ = assignment_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Empty title
    res_empty_title = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={"title": "   ", "description": "Valid desc"},
        format="json",
    )
    assert res_empty_title.status_code == status.HTTP_400_BAD_REQUEST

    # Exceeds max length
    res_long_title = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={"title": "A" * 201, "description": "Valid desc"},
        format="json",
    )
    assert res_long_title.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_faculty_can_configure_and_update_deadline(stub_iam, assignment_setup):
    """10. Authorized faculty can configure, update, and clear assignment deadlines."""
    ws1, _ = assignment_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    future_due = timezone.now() + timedelta(days=7)
    future_iso = future_due.isoformat()

    # Create assignment with deadline
    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={
            "title": "Assignment with Deadline",
            "description": "Deadline testing",
            "instructions": "Due next week",
            "due_at": future_iso,
            "is_published": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    asgn_id = data["id"]
    assert data["due_at"] is not None
    assert data["has_passed"] is False

    # Check database state
    asgn = CourseAssignment.objects.get(id=asgn_id)
    assert asgn.due_at is not None
    assert asgn.has_passed is False

    # Faculty updates deadline
    new_due = timezone.now() + timedelta(days=14)
    patch_res = client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn_id}",
        data={"due_at": new_due.isoformat()},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    patch_data = patch_res.json()
    assert patch_data["due_at"] is not None
    assert patch_data["has_passed"] is False

    # Faculty clears deadline
    clear_res = client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn_id}",
        data={"clear_due_at": True},
        format="json",
    )
    assert clear_res.status_code == status.HTTP_200_OK
    clear_data = clear_res.json()
    assert clear_data["due_at"] is None
    assert clear_data["has_passed"] is False

    asgn.refresh_from_db()
    assert asgn.due_at is None
    assert asgn.has_passed is False


@pytest.mark.django_db
def test_students_view_deadlines_and_cannot_modify(stub_iam, assignment_setup):
    """11. Students can view deadlines and passed status, but cannot modify deadlines."""
    ws1, _ = assignment_setup
    past_due = timezone.now() - timedelta(days=2)
    future_due = timezone.now() + timedelta(days=5)

    asgn_past = CourseAssignment.objects.create(
        workspace=ws1,
        title="Past Assignment",
        due_at=past_due,
        is_published=True,
        created_by_id=10,
    )
    asgn_future = CourseAssignment.objects.create(
        workspace=ws1,
        title="Upcoming Assignment",
        due_at=future_due,
        is_published=True,
        created_by_id=10,
    )

    student_client = _auth_client(
        stub_iam,
        user_id=30,  # Enrolled student
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Student views list
    res = student_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments")
    assert res.status_code == status.HTTP_200_OK
    items = {item["id"]: item for item in res.json()["results"]}

    assert items[asgn_past.id]["due_at"] is not None
    assert items[asgn_past.id]["has_passed"] is True

    assert items[asgn_future.id]["due_at"] is not None
    assert items[asgn_future.id]["has_passed"] is False

    # Student attempts to change deadline -> Forbidden
    tamper_res = student_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn_past.id}",
        data={"due_at": (timezone.now() + timedelta(days=10)).isoformat()},
        format="json",
    )
    assert tamper_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_ta_and_observer_view_deadlines_read_only(stub_iam, assignment_setup):
    """12. TAs and Observers can view deadlines but cannot modify them."""
    ws1, _ = assignment_setup
    future_due = timezone.now() + timedelta(days=3)
    asgn = CourseAssignment.objects.create(
        workspace=ws1,
        title="Deadline for Review",
        due_at=future_due,
        is_published=True,
        created_by_id=10,
    )

    # TA read-only
    ta_client = _auth_client(
        stub_iam,
        user_id=20,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    ta_get = ta_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}")
    assert ta_get.status_code == status.HTTP_200_OK
    assert ta_get.json()["due_at"] is not None
    assert ta_get.json()["has_passed"] is False

    ta_patch = ta_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}",
        data={"clear_due_at": True},
        format="json",
    )
    assert ta_patch.status_code == status.HTTP_403_FORBIDDEN

    # Observer read-only
    obs_client = _auth_client(
        stub_iam,
        user_id=40,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    obs_get = obs_client.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}")
    assert obs_get.status_code == status.HTTP_200_OK
    assert obs_get.json()["due_at"] is not None

    obs_patch = obs_client.patch(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn.id}",
        data={"due_at": (timezone.now() + timedelta(days=20)).isoformat()},
        format="json",
    )
    assert obs_patch.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_missing_deadline_and_invalid_datetime_validation(stub_iam, assignment_setup):
    """13. Missing deadlines return null/false; invalid datetimes return 400 Bad Request."""
    ws1, _ = assignment_setup
    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )

    # Create without deadline
    res_no_due = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={"title": "Assignment Without Deadline", "is_published": True},
        format="json",
    )
    assert res_no_due.status_code == status.HTTP_201_CREATED
    data = res_no_due.json()
    assert data["due_at"] is None
    assert data["has_passed"] is False

    # Attempt to pass invalid datetime format
    res_invalid_date = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments",
        data={
            "title": "Invalid Date Assignment",
            "due_at": "not-a-valid-timestamp",
            "is_published": True,
        },
        format="json",
    )
    assert res_invalid_date.status_code == status.HTTP_400_BAD_REQUEST


