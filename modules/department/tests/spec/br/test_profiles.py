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


def test_tc_dept_br_037_faculty_viewer_scope(world, act):
    """TC-DEPT-BR-037 | BR-DEPT-019 faculty-viewer-scope"""
    ids = _seed_profiles(act)
    enrolled_student_resp = act("admin").post(
        f"{API}/profiles",
        {
            "kind": "student",
            "user_id": uid("student"),
            "bio": "First-year CSE student.",
            "research_interests": "Systems",
        },
        format="json",
    )
    assert enrolled_student_resp.status_code == 201
    enrolled_student_id = enrolled_student_resp.json()["id"]

    other_faculty_resp = act("admin").post(
        f"{API}/profiles",
        {
            "kind": "faculty",
            "user_id": uid("faculty2"),
            "office": "C-202",
            "research_interests": "Databases",
            "bio": "Associate Professor of CSE.",
        },
        format="json",
    )
    assert other_faculty_resp.status_code == 201
    other_faculty_id = other_faculty_resp.json()["id"]

    slot_resp = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                {
                    "kind": "class",
                    "programme": "B.Tech",
                    "batch_year": 2024,
                    "course_code": "CS2001",
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

    full_only_fields = {"user_id", "bio", "graduation_year", "is_active"}
    detailed_and_full_only = {"username", "discipline", "batch_year"} | full_only_fields
    non_basic_fields = (
        {"email", "office", "research_interests", "current_position"} | detailed_and_full_only
    )
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
    expected_limited_fields = {
        "id",
        "kind",
        "display_name",
        "programme",
        "department",
        "email",
        "office",
        "research_interests",
        "current_position",
    }

    enrolled = act("faculty").get(f"{API}/profiles/{enrolled_student_id}")
    assert enrolled.status_code == 200
    enrolled_data = enrolled.json()
    assert enrolled_data["tier"] == "detailed"
    assert expected_detailed_fields.issubset(set(enrolled_data.keys()))
    assert enrolled_data["username"] == f"u{uid('student')}"
    assert enrolled_data["email"] == f"u{uid('student')}@example.test"
    assert enrolled_data["programme"] == "B.Tech"
    assert enrolled_data["discipline"] == "CSE"
    assert enrolled_data["batch_year"] == 2024
    assert enrolled_data["research_interests"] == "Systems"
    assert not (set(enrolled_data.keys()) & full_only_fields)
    assert not (set(enrolled_data.keys()) & SENSITIVE_FIELDS)

    non_enrolled = act("faculty").get(f"{API}/profiles/{ids['student']}")
    assert non_enrolled.status_code == 200
    non_enrolled_data = non_enrolled.json()
    assert non_enrolled_data["tier"] == "basic"
    assert not (set(non_enrolled_data.keys()) & non_basic_fields)
    assert not (set(non_enrolled_data.keys()) & SENSITIVE_FIELDS)

    for target_id in (other_faculty_id, ids["alumni"]):
        resp = act("faculty").get(f"{API}/profiles/{target_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "limited"
        assert expected_limited_fields.issubset(set(data.keys()))
        assert not (set(data.keys()) & detailed_and_full_only)
        assert not (set(data.keys()) & SENSITIVE_FIELDS)


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
