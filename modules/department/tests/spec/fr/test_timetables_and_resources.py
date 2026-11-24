"""Functional Requirement spec tests: Timetables, Labs & Programs (TC-DEPT-061..TC-DEPT-071)."""

from __future__ import annotations

import pytest

from modules.department.models import LabResource, TimetableSlot

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _slot(**overrides) -> dict:
    return {
        "kind": "class",
        "programme": "B.Tech",
        "batch_year": 2024,
        "course_code": "CS2001",
        "day_of_week": 0,
        "starts_at": "09:00",
        "ends_at": "10:00",
        "room": "L-104",
        **overrides,
    }


def test_tc_dept_061_dept_admin_timetable_upload(world, act):
    """TC-DEPT-061 | AFR-DEPT-029 Dept_Admin timetable upload"""
    slots = [
        _slot(kind="class", course_code="CS2001", starts_at="09:00", ends_at="10:00", room="L-104"),
        _slot(kind="lab", course_code="CS2002L", starts_at="10:00", ends_at="12:00", room="Lab-1"),
    ]
    resp = act("admin").post(f"{API}/timetable-slots", {"slots": slots}, format="json")
    assert resp.status_code == 201, resp.content
    assert len(resp.json()) == 2
    assert TimetableSlot.objects.count() == 2


def test_tc_dept_062_non_dept_admin_timetable_upload_denial(world, act):
    """TC-DEPT-062 | AFR-DEPT-029 non-Dept_Admin timetable upload denial"""
    for role in ("faculty", "student", "hod"):
        resp = act(role).post(f"{API}/timetable-slots", {"slots": [_slot()]}, format="json")
        assert resp.status_code == 403
    assert TimetableSlot.objects.count() == 0


def test_tc_dept_063_dept_admin_timetable_modification(world, act):
    """TC-DEPT-063 | AFR-DEPT-030 Dept_Admin timetable modification"""
    created = act("admin").post(f"{API}/timetable-slots", {"slots": [_slot()]}, format="json")
    assert created.status_code == 201
    slot_id = created.json()[0]["id"]

    resp = act("admin").patch(
        f"{API}/timetable-slots/{slot_id}",
        {"starts_at": "11:00", "ends_at": "12:00", "room": "L-202"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["room"] == "L-202"
    slot = TimetableSlot.objects.get(pk=slot_id)
    assert slot.room == "L-202"
    assert slot.starts_at.strftime("%H:%M") == "11:00"
    assert slot.ends_at.strftime("%H:%M") == "12:00"


def test_tc_dept_064_non_dept_admin_timetable_modification_denial(world, act):
    """TC-DEPT-064 | AFR-DEPT-030 non-Dept_Admin timetable modification denial"""
    created = act("admin").post(f"{API}/timetable-slots", {"slots": [_slot()]}, format="json")
    assert created.status_code == 201
    slot_id = created.json()[0]["id"]

    for role in ("faculty", "student", "hod"):
        resp = act(role).patch(
            f"{API}/timetable-slots/{slot_id}", {"room": "L-999"}, format="json"
        )
        assert resp.status_code == 403

    assert TimetableSlot.objects.get(pk=slot_id).room == "L-104"


def test_tc_dept_065_block_overlapping_slots_on_timetable_save(world, act):
    """TC-DEPT-065 | AFR-DEPT-031 block overlapping slots on timetable save"""
    first = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                _slot(starts_at="09:00", ends_at="10:00", room="L-104"),
                _slot(course_code="CS2002", starts_at="11:00", ends_at="12:00", room="L-104"),
            ]
        },
        format="json",
    )
    assert first.status_code == 201
    second_slot_id = first.json()[1]["id"]

    # Overlapping upload is blocked.
    bad_upload = act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [_slot(course_code="CS2003", starts_at="09:30", ends_at="10:30", room="L-104")]},
        format="json",
    )
    assert bad_upload.status_code == 422
    assert TimetableSlot.objects.count() == 2

    # Overlapping modification is blocked.
    bad_modify = act("admin").patch(
        f"{API}/timetable-slots/{second_slot_id}",
        {"starts_at": "09:30", "ends_at": "10:30"},
        format="json",
    )
    assert bad_modify.status_code == 422
    assert TimetableSlot.objects.get(pk=second_slot_id).starts_at.strftime("%H:%M") == "11:00"


def test_tc_dept_066_allow_adjacent_non_overlapping_slots(world, act):
    """TC-DEPT-066 | AFR-DEPT-031 allow adjacent non-overlapping slots"""
    assert (
        act("admin")
        .post(
            f"{API}/timetable-slots",
            {"slots": [_slot(starts_at="09:00", ends_at="10:00", room="L-104")]},
            format="json",
        )
        .status_code
        == 201
    )
    adjacent = act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [_slot(course_code="CS2002", starts_at="10:00", ends_at="11:00", room="L-104")]},
        format="json",
    )
    assert adjacent.status_code == 201, adjacent.content
    assert TimetableSlot.objects.count() == 2


def test_tc_dept_067_dept_admin_lab_resource_update(world, act):
    """TC-DEPT-067 | AFR-DEPT-034 Dept_Admin lab resource update"""
    created = act("admin").post(
        f"{API}/lab-resources",
        {"name": "Networks Lab", "location": "Block B", "equipment": "Routers x5", "capacity": 25},
        format="json",
    )
    assert created.status_code == 201
    lab_id = created.json()["id"]

    resp = act("admin").patch(
        f"{API}/lab-resources/{lab_id}",
        {"equipment": "Routers x10, Switches x8", "capacity": 35, "status": "maintenance"},
        format="json",
    )
    assert resp.status_code == 200
    lab = LabResource.objects.get(pk=lab_id)
    assert lab.equipment == "Routers x10, Switches x8"
    assert lab.capacity == 35
    assert lab.status == "maintenance"


def test_tc_dept_068_non_dept_admin_lab_resource_update_denial(world, act):
    """TC-DEPT-068 | AFR-DEPT-034 non-Dept_Admin lab resource update denial"""
    created = act("admin").post(
        f"{API}/lab-resources",
        {"name": "Systems Lab", "equipment": "Workstations x30", "capacity": 30},
        format="json",
    )
    assert created.status_code == 201
    lab_id = created.json()["id"]

    for role in ("faculty", "student"):
        resp = act(role).patch(
            f"{API}/lab-resources/{lab_id}", {"capacity": 99}, format="json"
        )
        assert resp.status_code == 403

    assert LabResource.objects.get(pk=lab_id).capacity == 30


def test_tc_dept_069_faculty_view_lab_resource_profiles(world, act):
    """TC-DEPT-069 | AFR-DEPT-035 Faculty view lab resource profiles"""
    created = act("admin").post(
        f"{API}/lab-resources",
        {"name": "AI Lab", "location": "Block C", "equipment": "GPUs x8", "capacity": 20},
        format="json",
    )
    assert created.status_code == 201

    resp = act("faculty").get(f"{API}/lab-resources")
    assert resp.status_code == 200
    labs = {lab["name"]: lab for lab in resp.json()["results"]}
    assert "AI Lab" in labs
    assert labs["AI Lab"]["equipment"] == "GPUs x8"
    assert labs["AI Lab"]["capacity"] == 20


def test_tc_dept_070_student_view_academic_program_information(world, act, stub_iam):
    """TC-DEPT-070 | AFR-DEPT-036 Student view academic program information"""
    fake = stub_iam()
    fake.filters = {"programmes": ["B.Tech", "M.Tech", "Ph.D"], "disciplines": ["CSE"], "batch_years": [2024]}

    resp = act("student").get(f"{API}/departments/CSE")
    assert resp.status_code == 200
    assert resp.json()["programmes"] == ["B.Tech", "M.Tech", "Ph.D"]


def test_tc_dept_071_student_view_applicable_timetables(world, act):
    """TC-DEPT-071 | AFR-DEPT-037 Student view applicable timetables"""
    assert (
        act("admin")
        .post(
            f"{API}/timetable-slots",
            {
                "slots": [
                    _slot(kind="class", programme="B.Tech", batch_year=2024, course_code="CS2001"),
                    _slot(
                        kind="lab",
                        programme="B.Tech",
                        batch_year=2024,
                        course_code="CS2001L",
                        starts_at="14:00",
                        ends_at="16:00",
                        room="Lab-2",
                    ),
                    _slot(
                        kind="class",
                        programme="B.Tech",
                        batch_year=2023,
                        course_code="CS3001",
                        starts_at="11:00",
                        ends_at="12:00",
                        room="L-201",
                    ),
                ]
            },
            format="json",
        )
        .status_code
        == 201
    )

    resp = act("student").get(f"{API}/timetable-slots")
    assert resp.status_code == 200
    codes = {slot["course_code"] for slot in resp.json()}
    assert codes == {"CS2001", "CS2001L"}
