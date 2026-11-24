"""Business Rule spec tests: Timetables & Resources (TC-DEPT-BR-020, 021, 024, 025)."""

from __future__ import annotations

import pytest

from modules.department.models import TimetableSlot

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


def test_tc_dept_br_020_conflict_free_permitted(world, act):
    """TC-DEPT-BR-020 | BR-DEPT-010 conflict-free-permitted"""
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
    assert TimetableSlot.objects.count() == 2

    slot_id = upload.json()[0]["id"]
    modify = act("admin").patch(
        f"{API}/timetable-slots/{slot_id}",
        {"starts_at": "14:00", "ends_at": "15:00", "room": "L-202"},
        format="json",
    )
    assert modify.status_code == 200, modify.content
    updated = TimetableSlot.objects.get(pk=slot_id)
    assert updated.room == "L-202"
    assert updated.starts_at.strftime("%H:%M") == "14:00"
    assert updated.ends_at.strftime("%H:%M") == "15:00"


def test_tc_dept_br_021_overlapping_slots_blocked(world, act):
    """TC-DEPT-BR-021 | BR-DEPT-010 overlapping-slots-blocked"""
    created = act("admin").post(
        f"{API}/timetable-slots",
        {
            "slots": [
                _slot(course_code="CS2001", starts_at="09:00", ends_at="10:00", room="L-104"),
                _slot(course_code="CS2002", starts_at="11:00", ends_at="12:00", room="L-104"),
            ]
        },
        format="json",
    )
    assert created.status_code == 201
    second_id = created.json()[1]["id"]

    overlap_upload = act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [_slot(course_code="CS2003", starts_at="09:30", ends_at="10:30", room="L-104")]},
        format="json",
    )
    assert overlap_upload.status_code == 422
    assert TimetableSlot.objects.count() == 2

    overlap_modify = act("admin").patch(
        f"{API}/timetable-slots/{second_id}",
        {"starts_at": "09:30", "ends_at": "10:30"},
        format="json",
    )
    assert overlap_modify.status_code == 422
    preserved = TimetableSlot.objects.get(pk=second_id)
    assert preserved.starts_at.strftime("%H:%M") == "11:00"
    assert preserved.ends_at.strftime("%H:%M") == "12:00"


def test_tc_dept_br_024_in_scope_faculty_resources(world, act):
    """TC-DEPT-BR-024 | BR-DEPT-012 in-scope-faculty-resources"""
    lab_resp = act("admin").post(
        f"{API}/lab-resources",
        {"name": "Systems Lab", "location": "Block A", "equipment": "Servers x4", "capacity": 30},
        format="json",
    )
    assert lab_resp.status_code == 201

    item_id = (
        act("admin")
        .post(
            f"{API}/inventory-items",
            {"name": "HDMI Cable", "unit": "cable", "quantity": 10},
            format="json",
        )
        .json()["id"]
    )
    req_id = (
        act("faculty")
        .post(
            f"{API}/stock-requests",
            {"item": item_id, "quantity": 2, "purpose": "Demo"},
            format="json",
        )
        .json()["id"]
    )
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200

    labs_view = act("faculty").get(f"{API}/lab-resources")
    assert labs_view.status_code == 200
    lab_names = {lab["name"] for lab in labs_view.json()["results"]}
    assert "Systems Lab" in lab_names

    stock_view = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert stock_view.status_code == 200
    issued_ids = {r["id"] for r in stock_view.json()["results"]}
    assert req_id in issued_ids


def test_tc_dept_br_025_out_of_scope_resources_excluded(world, act):
    """TC-DEPT-BR-025 | BR-DEPT-012 out-of-scope-resources-excluded"""
    # Another department's lab resource is out of CSE Faculty scope.
    assert (
        act("ece_admin")
        .post(
            f"{API}/lab-resources",
            {"name": "ECE VLSI Lab", "location": "Block E", "equipment": "ASIC kits", "capacity": 20},
            format="json",
        )
        .status_code
        == 201
    )

    # Another Faculty member's issued stock request is out of viewing Faculty scope.
    item_id = (
        act("admin")
        .post(
            f"{API}/inventory-items",
            {"name": "USB Hub", "unit": "unit", "quantity": 10},
            format="json",
        )
        .json()["id"]
    )
    other_req_id = (
        act("faculty2")
        .post(
            f"{API}/stock-requests",
            {"item": item_id, "quantity": 2, "purpose": "Other faculty lab"},
            format="json",
        )
        .json()["id"]
    )
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{other_req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{other_req_id}/issue").status_code == 200

    labs_resp = act("faculty").get(f"{API}/lab-resources")
    assert labs_resp.status_code == 200
    assert "ECE VLSI Lab" not in {lab["name"] for lab in labs_resp.json()["results"]}

    stock_resp = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert stock_resp.status_code == 200
    assert other_req_id not in {r["id"] for r in stock_resp.json()["results"]}

    # Administrative stock-movement ledger is restricted outside Faculty scope.
    assert act("faculty").get(f"{API}/stock-movements").status_code == 403
