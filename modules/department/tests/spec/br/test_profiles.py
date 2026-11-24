"""Business Rule spec tests: Profiles (TC-DEPT-BR-036..TC-DEPT-BR-038)."""

from __future__ import annotations

import pytest

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


def test_tc_dept_br_036_student_viewer_scope(world, act):
    """TC-DEPT-BR-036 | BR-DEPT-019 student-viewer-scope"""
    ids = _seed_profiles(act)
    detailed_fields = {
        "email",
        "office",
        "research_interests",
        "bio",
        "batch_year",
        "username",
        "user_id",
        "graduation_year",
        "current_position",
        "is_active",
    }

    for key in ("student", "faculty"):
        resp = act("student").get(f"{API}/profiles/{ids[key]}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "basic"
        assert data["display_name"]
        assert data["department"] == "CSE"
        keys = set(data.keys())
        assert not (keys & detailed_fields)
        assert not (keys & SENSITIVE_FIELDS)


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: No course-teaching or course-enrollment interface, model, or IAM "
        "projection exists in Fusion-Integrated A8_BASE to associate a Faculty member with "
        "enrolled Students (Q2), so the enrolled-Student detailed-view portion of BR-DEPT-019 "
        "cannot be set up or verified."
    )
)
def test_tc_dept_br_037_faculty_viewer_scope(world, act):
    """TC-DEPT-BR-037 | BR-DEPT-019 faculty-viewer-scope"""


def test_tc_dept_br_038_hod_and_dept_admin_viewer_scope(world, act):
    """TC-DEPT-BR-038 | BR-DEPT-019 hod-and-dept-admin-viewer-scope"""
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
