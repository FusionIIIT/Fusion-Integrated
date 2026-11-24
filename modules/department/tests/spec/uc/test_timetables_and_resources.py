"""Use Case spec tests: Timetables, Labs & Academic Info (TC-DEPT-018..019, 023..024, 034..037)."""

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


def test_tc_dept_018_dept_admin_upload_and_modify_conflict_free_timetable(world, act):
    """TC-DEPT-018 | UC-DEPT-009 Main Success Scenario"""
    upload = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                _slot(kind="class", course_code="CS2001", starts_at="09:00", ends_at="10:00", room="L-104"),
                _slot(kind="lab", course_code="CS2001L", starts_at="10:00", ends_at="12:00", room="Lab-1"),
            ]
        },
        format="json",
    )
    assert upload.status_code == 201, upload.content
    assert len(upload.json()) == 2
    assert TimetableSlot.objects.count() == 2

    slot_id = upload.json()[0]["id"]
    modified = act("admin").patch(
        f"{API}/timetable-slots/{slot_id}",
        {"starts_at": "14:00", "ends_at": "15:00", "room": "L-202"},
        format="json",
    )
    assert modified.status_code == 200, modified.content
    slot = TimetableSlot.objects.get(pk=slot_id)
    assert slot.room == "L-202"
    assert slot.starts_at.strftime("%H:%M") == "14:00"
    assert slot.ends_at.strftime("%H:%M") == "15:00"


def test_tc_dept_019_block_timetable_save_on_slot_conflict(world, act):
    """TC-DEPT-019 | UC-DEPT-009 Alternative Flow: Slot conflict detected"""
    initial = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                _slot(course_code="CS2001", starts_at="09:00", ends_at="10:00", room="L-104"),
                _slot(course_code="CS2002", starts_at="11:00", ends_at="12:00", room="L-104"),
            ]
        },
        format="json",
    )
    assert initial.status_code == 201
    second_id = initial.json()[1]["id"]

    bad_upload = act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [_slot(course_code="CS2003", starts_at="09:30", ends_at="10:30", room="L-104")]},
        format="json",
    )
    assert bad_upload.status_code == 422
    assert bad_upload.json()["error"]["code"] == "timetable_conflict"
    assert bad_upload.json()["error"]["details"]
    assert TimetableSlot.objects.count() == 2

    bad_modify = act("admin").patch(
        f"{API}/timetable-slots/{second_id}",
        {"starts_at": "09:30", "ends_at": "10:30"},
        format="json",
    )
    assert bad_modify.status_code == 422
    assert bad_modify.json()["error"]["code"] == "timetable_conflict"
    assert bad_modify.json()["error"]["details"]
    assert TimetableSlot.objects.get(pk=second_id).starts_at.strftime("%H:%M") == "11:00"


def test_tc_dept_023_faculty_view_lab_resources_and_issued_stock_history(world, act):
    """TC-DEPT-023 | UC-DEPT-011 Main Success Scenario"""
    cse_lab = act("admin").post(
        f"{API}/lab-resources",
        {"name": "Systems Lab", "location": "Block C", "equipment": "Workstations x30", "capacity": 30},
        format="json",
    )
    ece_lab = act("ece_admin").post(
        f"{API}/lab-resources",
        {"name": "VLSI Lab", "location": "Block B", "equipment": "FPGA Kits x15", "capacity": 20},
        format="json",
    )
    assert cse_lab.status_code == 201
    assert ece_lab.status_code == 201

    item_id = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Sensor Kit", "quantity": 10}, format="json")
        .json()["id"]
    )
    own_req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 2}, format="json")
        .json()["id"]
    )
    other_req = (
        act("faculty2")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 3}, format="json")
        .json()["id"]
    )
    for req_id in (own_req, other_req):
        assert (
            act("hod")
            .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
            .status_code
            == 200
        )
        assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200

    labs_resp = act("faculty").get(f"{API}/lab-resources")
    assert labs_resp.status_code == 200
    lab_names = {lab["name"] for lab in labs_resp.json()["results"]}
    assert lab_names == {"Systems Lab"}

    issued_resp = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert issued_resp.status_code == 200
    issued_ids = {r["id"] for r in issued_resp.json()["results"]}
    assert issued_ids == {own_req}


def test_tc_dept_024_faculty_resource_views_empty_state(world, act):
    """TC-DEPT-024 | UC-DEPT-011 Alternative Flow: No data exists in the selected view"""
    # Seed only out-of-scope data (ECE lab and another faculty's issued stock request).
    assert (
        act("ece_admin")
        .post(f"{API}/lab-resources", {"name": "ECE Only Lab", "capacity": 20}, format="json")
        .status_code
        == 201
    )
    item_id = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Breadboard", "quantity": 10}, format="json")
        .json()["id"]
    )
    other_req = (
        act("faculty2")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 2}, format="json")
        .json()["id"]
    )
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{other_req}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{other_req}/issue").status_code == 200

    labs_resp = act("faculty").get(f"{API}/lab-resources")
    assert labs_resp.status_code == 200
    assert labs_resp.json()["results"] == []

    issued_resp = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert issued_resp.status_code == 200
    assert issued_resp.json()["results"] == []


def test_tc_dept_034_dept_admin_update_lab_resource_details(world, act):
    """TC-DEPT-034 | UC-DEPT-017 Main Success Scenario"""
    created = act("admin").post(
        f"{API}/lab-resources",
        {"name": "Networks Lab", "location": "Block B", "equipment": "Routers x5", "capacity": 25},
        format="json",
    )
    assert created.status_code == 201
    lab_id = created.json()["id"]

    resp = act("admin").patch(
        f"{API}/lab-resources/{lab_id}",
        {"equipment": "Routers x12, Switches x10", "capacity": 40, "status": "maintenance"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    lab = LabResource.objects.get(pk=lab_id)
    assert lab.equipment == "Routers x12, Switches x10"
    assert lab.capacity == 40
    assert lab.status == LabResource.MAINTENANCE


def test_tc_dept_035_reject_invalid_lab_resource_update(world, act):
    """TC-DEPT-035 | UC-DEPT-017 Alternative Flow: Validation fails"""
    created = act("admin").post(
        f"{API}/lab-resources",
        {"name": "AI Lab", "location": "Block C", "equipment": "GPUs x8", "capacity": 20},
        format="json",
    )
    assert created.status_code == 201
    lab_id = created.json()["id"]

    blank_name = act("admin").patch(
        f"{API}/lab-resources/{lab_id}", {"name": "   "}, format="json"
    )
    assert blank_name.status_code == 422

    negative_capacity = act("admin").patch(
        f"{API}/lab-resources/{lab_id}", {"capacity": -10}, format="json"
    )
    assert negative_capacity.status_code in (400, 422)

    bad_status = act("admin").patch(
        f"{API}/lab-resources/{lab_id}", {"status": "decommissioned"}, format="json"
    )
    assert bad_status.status_code in (400, 422)

    lab = LabResource.objects.get(pk=lab_id)
    assert lab.name == "AI Lab"
    assert lab.equipment == "GPUs x8"
    assert lab.capacity == 20
    assert lab.status == LabResource.AVAILABLE


def test_tc_dept_036_student_view_academic_program_and_timetable(world, act, stub_iam):
    """TC-DEPT-036 | UC-DEPT-018 Main Success Scenario"""
    fake = stub_iam()
    fake.filters = {
        "programmes": ["B.Tech", "M.Tech", "Ph.D"],
        "disciplines": ["CSE"],
        "batch_years": [2024],
    }

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
    before_slots = TimetableSlot.objects.count()

    prog_resp = act("student").get(f"{API}/departments/CSE")
    assert prog_resp.status_code == 200
    assert prog_resp.json()["programmes"] == ["B.Tech", "M.Tech", "Ph.D"]

    tt_resp = act("student").get(f"{API}/timetable-slots")
    assert tt_resp.status_code == 200
    assert {slot["course_code"] for slot in tt_resp.json()} == {"CS2001", "CS2001L"}
    assert TimetableSlot.objects.count() == before_slots


def test_tc_dept_037_student_empty_academic_program_and_timetable_state(world, act, stub_iam):
    """TC-DEPT-037 | UC-DEPT-018 Alternative Flow: No applicable timetable/program data is published"""
    fake = stub_iam()
    fake.filters = {"programmes": [], "disciplines": ["CSE"], "batch_years": [2024]}

    # Publish only a slot for another batch year so nothing applies to the 2024 student.
    assert (
        act("admin")
        .post(
            f"{API}/timetable-slots",
            {"slots": [_slot(programme="B.Tech", batch_year=2023, course_code="CS3001")]},
            format="json",
        )
        .status_code
        == 201
    )
    before_slots = TimetableSlot.objects.count()

    prog_resp = act("student").get(f"{API}/departments/CSE")
    assert prog_resp.status_code == 200
    assert prog_resp.json()["programmes"] == []

    tt_resp = act("student").get(f"{API}/timetable-slots")
    assert tt_resp.status_code == 200
    assert tt_resp.json() == []
    assert TimetableSlot.objects.count() == before_slots
