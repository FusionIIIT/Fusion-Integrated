"""API endpoint and authorization tests for Course Workspace."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace
from modules.directory.models import UserRef

URL_WORKSPACES = "/api/v1/courses/workspaces"


@pytest.fixture
def sample_users():
    fac, _ = UserRef.objects.get_or_create(
        user_id=1,
        defaults={
            "username": "fac001",
            "display_name": "Prof. Alan Turing",
            "kind": "faculty",
            "department": "CSE",
            "email": "turing@iiitdmj.ac.in",
        },
    )
    ta, _ = UserRef.objects.get_or_create(
        user_id=2,
        defaults={
            "username": "ta001",
            "display_name": "Ada Lovelace",
            "kind": "student",
            "department": "CSE",
            "email": "ada@iiitdmj.ac.in",
        },
    )
    stu, _ = UserRef.objects.get_or_create(
        user_id=3,
        defaults={
            "username": "stu001",
            "display_name": "Grace Hopper",
            "kind": "student",
            "department": "CSE",
            "email": "grace@iiitdmj.ac.in",
        },
    )
    obs, _ = UserRef.objects.get_or_create(
        user_id=4,
        defaults={
            "username": "obs001",
            "display_name": "Observer User",
            "kind": "operator",
            "department": "Dean Office",
            "email": "obs@iiitdmj.ac.in",
        },
    )
    return fac, ta, stu, obs


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.mark.django_db
def test_list_workspaces_enforces_module_grant_and_scoping(stub_iam):
    ws1 = make_workspace(code="CS201", semester="Monsoon 2026")
    make_workspace(code="CS202", semester="Monsoon 2026")

    # User enrolled in ws1 only
    add_member(ws1, user_id=10, role="student")

    client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res = client.get(URL_WORKSPACES)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["count"] == 1
    assert data["results"][0]["code"] == "CS201"


@pytest.mark.django_db
def test_list_workspaces_without_module_grant_fails(stub_iam):
    client = _auth_client(stub_iam, user_id=10, modules=(), permissions=(P_WORKSPACE_VIEW,))
    res = client.get(URL_WORKSPACES)
    assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_get_workspace_detail_displays_syllabus_schedule_and_personnel(
    stub_iam, sample_users,
):
    ws = make_workspace(
        code="CS301",
        title="Operating Systems",
        syllabus="Kernel, Processes, Threads, Memory Management",
        schedule="Mon/Wed/Fri 10:00 - 11:00 AM | Room CR-101",
    )
    add_member(ws, user_id=1, role="instructor")
    add_member(ws, user_id=2, role="ta")
    add_member(ws, user_id=3, role="student")

    # Student viewing the course workspace
    client = _auth_client(
        stub_iam,
        user_id=3,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res = client.get(f"{URL_WORKSPACES}/{ws.id}")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["code"] == "CS301"
    assert data["title"] == "Operating Systems"
    assert data["syllabus"] == "Kernel, Processes, Threads, Memory Management"
    assert data["schedule"] == "Mon/Wed/Fri 10:00 - 11:00 AM | Room CR-101"
    assert data["viewer_role"] == "student"
    assert data["can_manage"] is False

    # Check instructors and TAs display
    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["name"] == "Prof. Alan Turing"
    assert data["instructors"][0]["email"] == "turing@iiitdmj.ac.in"

    assert len(data["tas"]) == 1
    assert data["tas"][0]["name"] == "Ada Lovelace"


@pytest.mark.django_db
def test_unenrolled_student_gets_404_on_workspace_detail(stub_iam):
    ws = make_workspace(code="CS501")
    add_member(ws, user_id=1, role="instructor")

    # Student 99 is not enrolled in ws
    client = _auth_client(
        stub_iam,
        user_id=99,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res = client.get(f"{URL_WORKSPACES}/{ws.id}")
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_ta_and_observer_can_view_workspace(stub_iam, sample_users):
    ws = make_workspace(code="CS601")
    add_member(ws, user_id=1, role="instructor")
    add_member(ws, user_id=2, role="ta")
    add_member(ws, user_id=4, role="observer")

    # TA view
    ta_client = _auth_client(
        stub_iam,
        user_id=2,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res_ta = ta_client.get(f"{URL_WORKSPACES}/{ws.id}")
    assert res_ta.status_code == status.HTTP_200_OK
    assert res_ta.json()["viewer_role"] == "ta"
    assert res_ta.json()["can_manage"] is False

    # Observer view (AFR-LMS-015.1, BR-LMS-003)
    obs_client = _auth_client(
        stub_iam,
        user_id=4,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res_obs = obs_client.get(f"{URL_WORKSPACES}/{ws.id}")
    assert res_obs.status_code == status.HTTP_200_OK
    assert res_obs.json()["viewer_role"] == "observer"
    assert res_obs.json()["can_manage"] is False


@pytest.mark.django_db
def test_faculty_can_update_workspace_via_patch(stub_iam):
    ws = make_workspace(code="CS701", title="Original Title")
    add_member(ws, user_id=1, role="instructor")

    fac_client = _auth_client(
        stub_iam,
        user_id=1,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    res = fac_client.patch(
        f"{URL_WORKSPACES}/{ws.id}",
        data={
            "title": "Updated Course Title",
            "syllabus": "Comprehensive 2026 Syllabus",
            "schedule": "Monday 2-5 PM",
            "allow_ta_announcements": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["title"] == "Updated Course Title"
    assert data["syllabus"] == "Comprehensive 2026 Syllabus"
    assert data["allow_ta_announcements"] is True


@pytest.mark.django_db
def test_ta_cannot_update_workspace_via_patch(stub_iam):
    ws = make_workspace(code="CS801")
    add_member(ws, user_id=1, role="instructor")
    add_member(ws, user_id=2, role="ta")

    # TA attempts to patch
    ta_client = _auth_client(
        stub_iam,
        user_id=2,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    res = ta_client.patch(
        f"{URL_WORKSPACES}/{ws.id}",
        data={"syllabus": "Unauthorized TA change"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_observer_cannot_update_workspace_via_patch(stub_iam):
    ws = make_workspace(code="CS901")
    add_member(ws, user_id=1, role="instructor")
    add_member(ws, user_id=4, role="observer")

    obs_client = _auth_client(
        stub_iam,
        user_id=4,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    res = obs_client.patch(
        f"{URL_WORKSPACES}/{ws.id}",
        data={"title": "Observer change"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
