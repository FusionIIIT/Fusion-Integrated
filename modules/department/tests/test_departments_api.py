"""Tests for the Department API endpoints."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.department.models import Department
from modules.department.selectors.scoping import P_VIEW_DEPARTMENTS

pytestmark = pytest.mark.django_db

# --- Fixtures and Setup ---

@pytest.fixture
def department_data(db):
    """Creates a set of departments for testing."""
    departments = [
        Department.objects.create(code="CSE", name="Computer Science Engineering", is_active=True),
        Department.objects.create(code="DESIGN", name="Design Studies", is_active=True),
        Department.objects.create(code="ECE", name="Electronics and Communication", is_active=True),
        Department.objects.create(code="LART", name="Liberal Arts", is_active=True),
        Department.objects.create(code="ME", name="Mechanical Engineering", is_active=True),
        Department.objects.create(code="NS", name="Natural Sciences", is_active=True),
        Department.objects.create(code="INACTIVE", name="Inactive Dept", is_active=False),
    ]
    return departments

@pytest.fixture
def student_membership(db, department_data):
    """Creates student memberships for testing scoping."""
    # Student 1: CSE
    user1 = UserRef(user_id=1001, username="u1001", display_name="Student 1", kind="student", discipline="CSE")
    # Student 2: DESIGN
    user2 = UserRef(user_id=1002, username="u1002", display_name="Student 2", kind="student", discipline="Design")
    # Student 3: Empty discipline (should see nothing)
    user3 = UserRef(user_id=1003, username="u1003", display_name="Student 3", kind="student", discipline="")
    # Student 4: Matches LART by name
    user4 = UserRef(user_id=1004, username="u1004", display_name="Student 4", kind="student", discipline="liberal arts")
    return {
        1001: user1,
        1002: user2,
        1003: user3,
        1004: user4,
    }

@pytest.fixture
def faculty_membership(db, department_data):
    """Creates faculty memberships for testing scoping."""
    # Faculty 1: CSE
    user1 = UserRef(user_id=2001, username="u2001", display_name="Faculty 1", kind="faculty", department="CSE")
    # Faculty 2: ECE
    user2 = UserRef(user_id=2002, username="u2002", display_name="Faculty 2", kind="faculty", department="ECE")
    # Faculty 3: Faculty with no department (should see nothing)
    user3 = UserRef(user_id=2003, username="u2003", display_name="Faculty 3", kind="faculty", department="")
    return {
        2001: user1,
        2002: user2,
        2003: user3,
    }

# --- Test Cases ---

def test_department_list_success_with_module_grant_and_permission(
    stub_iam, department_data, student_membership
):
    """Tests successful retrieval for a student with matching discipline."""
    # Student 1001 is in CSE
    stub_iam(make_session(user_id=1001, kind="student", roles=("student",),
                                  active_role="student", modules=("department",),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={1001: student_membership[1001]})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")

    assert response.status_code == 200
    data = response.data
    assert "results" in data
    assert len(data["results"]) > 0

    # Should only see CSE (and potentially others if they match the name/code)
    codes_seen = {d['code'] for d in data["results"]}
    assert "CSE" in codes_seen
    assert "INACTIVE" not in codes_seen

def test_department_list_student_empty_discipline_returns_empty_list(
    stub_iam, department_data, student_membership
):
    """Tests student with empty discipline sees no departments."""
    # Student 1003 has empty discipline
    stub_iam(make_session(user_id=1003, kind="student", roles=("student",),
                                  active_role="student", modules=("department",),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={1003: student_membership[1003]})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")

    assert response.status_code == 200
    assert response.data["results"] == []

def test_department_list_student_matches_by_name_case_insensitive(
    stub_iam, department_data, student_membership
):
    """Tests student matching by name case-insensitively."""
    # Student 1004 matches LART by name
    stub_iam(make_session(user_id=1004, kind="student", roles=("student",),
                                  active_role="student", modules=("department",),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={1004: student_membership[1004]})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")

    assert response.status_code == 200
    data = response.data
    codes_seen = {d['code'] for d in data["results"]}
    assert "LART" in codes_seen

def test_department_list_faculty_sees_only_member_departments(
    stub_iam, department_data, faculty_membership
):
    """Tests faculty sees only departments they are assigned to."""
    # Faculty 2002 is in ECE
    stub_iam(make_session(user_id=2002, kind="faculty", roles=("faculty",),
                                  active_role="faculty", modules=("department",),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={2002: faculty_membership[2002]})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")

    assert response.status_code == 200
    data = response.data
    codes_seen = {d['code'] for d in data["results"]}
    assert "ECE" in codes_seen
    assert "CSE" not in codes_seen
    assert "INACTIVE" not in codes_seen

def test_department_list_admin_sees_all_active_departments(
    stub_iam, department_data
):
    """Tests institute_admin role sees all active departments."""
    # Institute Admin role
    stub_iam(make_session(user_id=999, kind="faculty", roles=("faculty",),
                                  active_role="acadadmin", modules=("department",),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={999: UserRef(user_id=999, username="admin", display_name="Admin", kind="faculty", department="CSE")})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")

    assert response.status_code == 200
    data = response.data
    codes_seen = {d['code'] for d in data["results"]}
    assert "CSE" in codes_seen
    assert "DESIGN" in codes_seen
    assert "INACTIVE" not in codes_seen # Should filter inactive

def test_department_list_403_without_permission(stub_iam, department_data):
    """Tests 403 when permission is missing."""
    # User has module grant but no specific permission
    stub_iam(make_session(user_id=1001, kind="student", roles=("student",),
                                  active_role="student", modules=("department",),
                                  permissions=()),
              users={1001: UserRef(user_id=1001, username="u1001", display_name="Student 1", kind="student", discipline="CSE")})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")
    assert response.status_code == 403

def test_department_list_403_without_module_grant(stub_iam, department_data):
    """Tests 403 when module grant is missing."""
    # User has permission but no module grant
    stub_iam(make_session(user_id=1001, kind="student", roles=("student",),
                                  active_role="student", modules=(),
                                  permissions=(P_VIEW_DEPARTMENTS,)),
              users={1001: UserRef(user_id=1001, username="u1001", display_name="Student 1", kind="student", discipline="CSE")})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.get("/api/v1/department/departments")
    assert response.status_code == 403

# --- Scheduling Check ---

def test_schedule_entry_is_present_in_celery_beat_schedule(
    # This test relies on the configuration being correctly set up in config/celery.py
    # and the task being defined in modules/department/tasks.py
    # We check for the specific task name/frequency.
):
    """Verifies the notification delivery task is scheduled every 60 seconds."""
    from config.celery import app

    # Check if the task is registered in the beat schedule using the correct key from schedule.py
    assert 'department.deliver-notifications' in app.conf.beat_schedule

    # Check the schedule details (should be every 60 seconds)
    schedule_info = app.conf.beat_schedule['department.deliver-notifications']
    assert schedule_info["schedule"] == 60.0
