"""Use Case spec tests: Profiles (TC-DEPT-029..TC-DEPT-033)."""

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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: No course-teaching or course-enrollment interface, model, or IAM "
        "projection exists in Fusion-Integrated A8_BASE to associate a Faculty member with "
        "enrolled Students (Q2)."
    )
)
def test_tc_dept_029_faculty_view_student_profile_in_course(world, act):
    """TC-DEPT-029 | UC-DEPT-015 Main Success Scenario"""


def test_tc_dept_030_faculty_restricted_for_student_not_in_courses(world, act):
    """TC-DEPT-030 | UC-DEPT-015 Alternative Flow: Faculty requests a Student not in the Faculty member's courses"""
    ids = _seed_profiles(act)
    resp = act("faculty").get(f"{API}/profiles/{ids['student']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "basic"
    detailed_fields = {"email", "office", "research_interests", "bio", "batch_year", "username", "user_id"}
    assert not (set(data.keys()) & detailed_fields)
    assert not (set(data.keys()) & SENSITIVE_FIELDS)


def test_tc_dept_031_hod_and_dept_admin_view_excludes_sensitive_personal_data(world, act):
    """TC-DEPT-031 | UC-DEPT-015 Alternative Flow: Privacy-protected sensitive personal data excluded from HOD/Dept_Admin view"""
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
            assert not (set(data.keys()) & SENSITIVE_FIELDS)


def test_tc_dept_032_dept_admin_manage_department_profiles(world, act):
    """TC-DEPT-032 | UC-DEPT-016 Main Success Scenario"""
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


def test_tc_dept_033_dept_admin_profile_update_validation_failure(world, act):
    """TC-DEPT-033 | UC-DEPT-016 Alternative Flow: Validation fails"""
    ids = _seed_profiles(act)
    before_alumni = ProfileRecord.objects.get(pk=ids["alumni"])

    blank_name = act("admin").patch(
        f"{API}/profiles/{ids['alumni']}", {"display_name": "   "}, format="json"
    )
    assert blank_name.status_code == 422
    assert blank_name.json()["error"]["code"] == "profile_incomplete"

    bad_year = act("admin").patch(
        f"{API}/profiles/{ids['alumni']}", {"graduation_year": 1800}, format="json"
    )
    assert bad_year.status_code in (400, 422)

    after_alumni = ProfileRecord.objects.get(pk=ids["alumni"])
    assert after_alumni.display_name == before_alumni.display_name
    assert after_alumni.graduation_year == before_alumni.graduation_year
