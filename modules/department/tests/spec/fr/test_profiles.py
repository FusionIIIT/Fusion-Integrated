"""Functional Requirement spec tests: Profiles (TC-DEPT-052..TC-DEPT-060)."""

from __future__ import annotations

import pytest

from modules.department.models import ProfileRecord
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"
SENSITIVE_FIELDS = {"date_of_birth", "phone", "address", "category", "gender", "medical"}


def _seed_profiles(act) -> dict[str, int]:
    faculty_id = (
        act("admin")
        .post(
            f"{API}/profiles",
            {
                "kind": "faculty",
                "user_id": uid("faculty"),
                "office": "C-201",
                "research_interests": "Distributed Systems",
                "bio": "Professor of CSE.",
            },
            format="json",
        )
        .json()["id"]
    )
    student_id = (
        act("admin")
        .post(
            f"{API}/profiles",
            {
                "kind": "student",
                "user_id": uid("student2"),
                "bio": "Undergraduate researcher.",
                "research_interests": "Compilers",
            },
            format="json",
        )
        .json()["id"]
    )
    alumni_id = (
        act("admin")
        .post(
            f"{API}/profiles",
            {
                "kind": "alumni",
                "display_name": "Riya Sen",
                "graduation_year": 2020,
                "current_position": "Staff Engineer",
                "bio": "Graduated with honors.",
            },
            format="json",
        )
        .json()["id"]
    )
    return {"faculty": faculty_id, "student": student_id, "alumni": alumni_id}


def test_tc_dept_052_dept_admin_profile_management(world, act):
    """TC-DEPT-052 | AFR-DEPT-024 Dept_Admin profile management"""
    ids = _seed_profiles(act)

    upd_fac = act("admin").patch(
        f"{API}/profiles/{ids['faculty']}", {"office": "C-305"}, format="json"
    )
    upd_stu = act("admin").patch(
        f"{API}/profiles/{ids['student']}", {"bio": "Updated student bio."}, format="json"
    )
    upd_alu = act("admin").patch(
        f"{API}/profiles/{ids['alumni']}", {"current_position": "Principal Engineer"}, format="json"
    )
    assert upd_fac.status_code == 200
    assert upd_stu.status_code == 200
    assert upd_alu.status_code == 200

    assert ProfileRecord.objects.get(pk=ids["faculty"]).office == "C-305"
    assert ProfileRecord.objects.get(pk=ids["student"]).bio == "Updated student bio."
    assert ProfileRecord.objects.get(pk=ids["alumni"]).current_position == "Principal Engineer"


def test_tc_dept_053_non_dept_admin_profile_management_denial(world, act):
    """TC-DEPT-053 | AFR-DEPT-024 non-Dept_Admin profile management denial"""
    ids = _seed_profiles(act)

    for role in ("student", "faculty"):
        resp = act(role).patch(
            f"{API}/profiles/{ids['faculty']}", {"office": "Hacked"}, format="json"
        )
        assert resp.status_code == 403

    assert ProfileRecord.objects.get(pk=ids["faculty"]).office == "C-201"


def test_tc_dept_054_student_basic_profile_view(world, act):
    """TC-DEPT-054 | AFR-DEPT-025 Student basic profile view"""
    ids = _seed_profiles(act)

    peer = act("student").get(f"{API}/profiles/{ids['student']}")
    fac = act("student").get(f"{API}/profiles/{ids['faculty']}")
    assert peer.status_code == 200
    assert fac.status_code == 200

    peer_data = peer.json()
    fac_data = fac.json()
    assert peer_data["tier"] == "basic"
    assert peer_data["display_name"]
    assert peer_data["programme"] == "B.Tech"
    assert peer_data["department"] == "CSE"

    assert fac_data["tier"] == "basic"
    assert fac_data["display_name"]
    assert fac_data["department"] == "CSE"


def test_tc_dept_055_student_restricted_from_detailed_or_sensitive_fields(world, act):
    """TC-DEPT-055 | AFR-DEPT-025 Student restricted from detailed or sensitive fields"""
    ids = _seed_profiles(act)
    detailed_fields = {"email", "office", "research_interests", "bio", "batch_year", "username", "user_id"}

    for key in ("student", "faculty"):
        resp = act("student").get(f"{API}/profiles/{ids[key]}")
        assert resp.status_code == 200
        fields = set(resp.json().keys())
        assert not (fields & detailed_fields)
        assert not (fields & SENSITIVE_FIELDS)


def test_tc_dept_056_faculty_detailed_view_for_enrolled_course_students(world, act):
    """TC-DEPT-056 | AFR-DEPT-026 Faculty detailed view for enrolled course Students"""
    ids = _seed_profiles(act)
    slot_resp = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                {
                    "kind": "class",
                    "programme": "B.Tech",
                    "batch_year": 2023,
                    "course_code": "CS3001",
                    "day_of_week": 0,
                    "starts_at": "09:00",
                    "ends_at": "10:00",
                    "instructor_user_id": uid("faculty"),
                }
            ]
        },
        format="json",
    )
    assert slot_resp.status_code == 201

    resp = act("faculty").get(f"{API}/profiles/{ids['student']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "detailed"
    expected_detailed_fields = {
        "id",
        "kind",
        "display_name",
        "programme",
        "department",
        "email",
        "office",
        "research_interests",
        "current_position",
        "username",
        "discipline",
        "batch_year",
    }
    full_only_fields = {"user_id", "bio", "graduation_year", "is_active"}
    assert expected_detailed_fields.issubset(set(data.keys()))
    assert data["username"] == f"u{uid('student2')}"
    assert data["email"] == f"u{uid('student2')}@example.test"
    assert data["programme"] == "B.Tech"
    assert data["discipline"] == "CSE"
    assert data["batch_year"] == 2023
    assert data["research_interests"] == "Compilers"
    assert not (set(data.keys()) & full_only_fields)
    assert not (set(data.keys()) & SENSITIVE_FIELDS)


def test_tc_dept_057_faculty_restricted_for_students_not_in_their_courses(world, act):
    """TC-DEPT-057 | AFR-DEPT-026 Faculty restricted for Students not in their courses"""
    ids = _seed_profiles(act)
    resp = act("faculty").get(f"{API}/profiles/{ids['student']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "basic"
    detailed_fields = {"email", "office", "research_interests", "bio", "batch_year", "username", "user_id"}
    assert not (set(data.keys()) & detailed_fields)


def test_tc_dept_058_faculty_limited_scope_view_of_faculty_and_alumni(world, act):
    """TC-DEPT-058 | AFR-DEPT-027 Faculty limited-scope view of Faculty and Alumni"""
    ids = _seed_profiles(act)
    full_only_fields = {"bio", "user_id", "username", "batch_year", "graduation_year", "is_active"}

    for key in ("faculty", "alumni"):
        resp = act("faculty").get(f"{API}/profiles/{ids[key]}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "limited"
        assert "office" in data and "research_interests" in data and "current_position" in data
        assert not (set(data.keys()) & full_only_fields)
        assert not (set(data.keys()) & SENSITIVE_FIELDS)


def test_tc_dept_059_hod_and_dept_admin_full_non_sensitive_profile_view(world, act):
    """TC-DEPT-059 | AFR-DEPT-028 HOD and Dept_Admin full non-sensitive profile view"""
    ids = _seed_profiles(act)
    expected_full_fields = {
        "id",
        "kind",
        "user_id",
        "username",
        "display_name",
        "programme",
        "department",
        "discipline",
        "batch_year",
        "email",
        "office",
        "research_interests",
        "bio",
        "graduation_year",
        "current_position",
        "is_active",
    }

    for viewer in ("hod", "admin"):
        for key in ("faculty", "student", "alumni"):
            resp = act(viewer).get(f"{API}/profiles/{ids[key]}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tier"] == "full"
            assert expected_full_fields.issubset(set(data.keys()))


def test_tc_dept_060_exclusion_of_sensitive_personal_data(world, act):
    """TC-DEPT-060 | AFR-DEPT-028 exclusion of sensitive personal data"""
    ids = _seed_profiles(act)

    for viewer in ("hod", "admin"):
        for key in ("faculty", "student", "alumni"):
            resp = act(viewer).get(f"{API}/profiles/{ids[key]}")
            assert resp.status_code == 200
            assert not (set(resp.json().keys()) & SENSITIVE_FIELDS)
