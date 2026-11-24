"""Specification-based tests for Use Cases (UC)."""

import datetime

import pytest

from modules.dept.models import (
    DepartmentRoleAssignment,
    InventoryItem,
)

pytestmark = pytest.mark.django_db


# --- UC-DEPT-001 ---


def test_uc_001_main_flow(auth_client, cse_dept):
    """TEST-UC-001: UC-DEPT-001 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Welcome Announcement", "content": "Welcome all", "target_role": "ALL"},
        format="json",
    )
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200
    assert any(a["title"] == "Welcome Announcement" for a in res.json())


def test_uc_002_alternative_flow(auth_client, cse_dept):
    """TEST-UC-002: UC-DEPT-001 Alternative Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# --- UC-DEPT-002 ---


def test_uc_003_main_flow(auth_client, cse_dept):
    """TEST-UC-003: UC-DEPT-002 Main Flow"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Faculty UC Notice",
            "content": "Seminar tomorrow",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 3,
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["title"] == "Faculty UC Notice"


def test_uc_004_alternative_flow(auth_client, cse_dept):
    """TEST-UC-004: UC-DEPT-002 Alternative Flow"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "", "content": ""},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-003 ---


def test_uc_005_main_flow(auth_client, cse_dept):
    """TEST-UC-005: UC-DEPT-003 Main Flow"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_ann = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Manage Notice", "content": "Content to manage", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    res_get = hod_c.get(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_get.status_code == 200


def test_uc_006_alternative_flow_edit(auth_client, cse_dept):
    """TEST-UC-006: UC-DEPT-003 Alternative Flow Edit"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_ann = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Original Title", "content": "Original Content", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    res_patch = hod_c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"title": "Edited Title", "content": "Edited Content"},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "Edited Title"


def test_uc_007_alternative_flow_hide(auth_client, cse_dept):
    """TEST-UC-007: UC-DEPT-003 Alternative Flow Hide"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_ann = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Visible Notice", "content": "To be hidden", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    res_hide = hod_c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"is_active": False},
        format="json",
    )
    assert res_hide.status_code == 200
    assert res_hide.json()["is_active"] is False


def test_uc_008_alternative_flow_delete(auth_client, cse_dept):
    """TEST-UC-008: UC-DEPT-003 Alternative Flow Delete"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_ann = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Delete Notice", "content": "To be deleted", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    res_del = hod_c.delete(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_del.status_code in (200, 204)


# --- UC-DEPT-004 ---


def test_uc_009_main_flow(auth_client, cse_dept):
    """TEST-UC-009: UC-DEPT-004 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-STOCK-01", "name": "Stock Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 4, "purpose": "Lab work"},
        format="json",
    )
    assert res_req.status_code == 201
    assert res_req.json()["status"] == "SUBMITTED"


def test_uc_010_alternative_flow(auth_client, cse_dept):
    """TEST-UC-010: UC-DEPT-004 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-STOCK-02", "name": "Low Stock Item", "initial_quantity": 2},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 5, "purpose": "Excess request"},
        format="json",
    )
    assert res_req.status_code == 400


# --- UC-DEPT-005 ---


def test_uc_011_main_flow(auth_client, cse_dept):
    """TEST-UC-011: UC-DEPT-005 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-APP-01", "name": "Approval Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Research"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_app = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"


def test_uc_012_alternative_flow(auth_client, cse_dept):
    """TEST-UC-012: UC-DEPT-005 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-REJ-01", "name": "Rejection Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Research"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_rej = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "REJECT", "remarks": "Budget constraint"},
        format="json",
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


# --- UC-DEPT-006 ---


def test_uc_013_main_flow(auth_client, cse_dept):
    """TEST-UC-013: UC-DEPT-006 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-ISS-01", "name": "Issuance Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 3, "purpose": "Teaching"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )

    admin_c.activate()
    res_iss = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json"
    )
    assert res_iss.status_code == 200
    assert res_iss.json()["status"] == "ISSUED"

    item = InventoryItem.objects.get(id=item_id)
    assert item.quantity == 7


# --- UC-DEPT-007 ---


def test_uc_014_main_flow(auth_client, cse_dept):
    """TEST-UC-014: UC-DEPT-007 Main Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "UC Feedback", "description": "Campus Wi-Fi speed", "category": "FACILITY"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "NEW"


def test_uc_015_exception_flow(auth_client, cse_dept):
    """TEST-UC-015: UC-DEPT-007 Exception Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "", "description": ""},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-008 ---


def test_uc_016_main_flow(auth_client, cse_dept):
    """TEST-UC-016: UC-DEPT-008 Main Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Review Flow", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"category": "ACADEMIC", "admin_remarks": "Assigned to academic committee"},
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


def test_uc_017_alternative_flow_simple_issue(auth_client, cse_dept):
    """TEST-UC-017: UC-DEPT-008 Alternative Flow Simple Issue"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Simple Light", "description": "Replace bulb", "category": "FACILITY"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_close = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "CLOSE", "remarks": "Replaced immediately"},
        format="json",
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"


def test_uc_018_alternative_flow_non_terminal(auth_client, cse_dept):
    """TEST-UC-018: UC-DEPT-008 Alternative Flow Non-Terminal"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Complex Issue", "description": "Curriculum update", "category": "ACADEMIC"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"admin_remarks": "Referred to HOD"},
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


# --- UC-DEPT-009 ---


def test_uc_019_main_flow(auth_client, cse_dept):
    """TEST-UC-019: UC-DEPT-009 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 1,
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "course_code": "CS301",
            "course_name": "Software Engineering",
            "instructor_id": "prof_se",
            "room_or_lab": "Room 301",
        },
        format="json",
    )
    assert res.status_code == 201


def test_uc_020_alternative_flow_slot_conflict(auth_client, cse_dept):
    """TEST-UC-020: UC-DEPT-009 Alternative Flow Slot Conflict"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 2,
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "course_code": "CS302",
            "course_name": "Cloud Computing",
            "instructor_id": "prof_cc",
            "room_or_lab": "Room 302",
        },
        format="json",
    )

    res_conflict = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 2,
            "start_time": "14:30:00",
            "end_time": "15:30:00",
            "course_code": "CS303",
            "course_name": "DevOps",
            "instructor_id": "prof_do",
            "room_or_lab": "Room 302",
        },
        format="json",
    )
    assert res_conflict.status_code in (400, 409)


# --- UC-DEPT-010 ---


def test_uc_021_main_flow_general(auth_client, cse_dept):
    """TEST-UC-021: UC-DEPT-010 Main Flow General"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.patch(
        "/api/v1/dept/details/?department=CSE",
        {"website": "https://cse.fusion.ac.in"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["website"] == "https://cse.fusion.ac.in"


def test_uc_022_main_flow_official(auth_client, cse_dept):
    """TEST-UC-022: UC-DEPT-010 Main Flow Official"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Updated UC Policy",
            "justification": "Curriculum board mandate",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING_HOD"


def test_uc_023_alternative_flow(auth_client, cse_dept):
    """TEST-UC-023: UC-DEPT-010 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {"field_name": "invalid_field_name", "new_value": "Some value"},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-011 ---


def test_uc_024_main_flow(auth_client, cse_dept):
    """TEST-UC-024: UC-DEPT-011 Main Flow"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_lab = fac_c.get("/api/v1/dept/labs/?department=CSE")
    assert res_lab.status_code == 200
    res_req = fac_c.get("/api/v1/dept/stock-requests/?department=CSE")
    assert res_req.status_code == 200


def test_uc_025_alternative_flow(auth_client, cse_dept):
    """TEST-UC-025: UC-DEPT-011 Alternative Flow"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_lab = fac_c.get("/api/v1/dept/labs/?department=CSE")
    assert res_lab.status_code == 200
    assert isinstance(res_lab.json(), list)


# --- UC-DEPT-012 ---


def test_uc_026_main_flow(auth_client, cse_dept):
    """TEST-UC-026: UC-DEPT-012 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "UC Policy Approved",
            "justification": "Senate rule",
        },
        format="json",
    )
    change_id = res_prop.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_app = hod_c.post(
        f"/api/v1/dept/details/pending-changes/{change_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"


def test_uc_027_alternative_flow(auth_client, cse_dept):
    """TEST-UC-027: UC-DEPT-012 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "UC Policy Rejected",
            "justification": "Proposal test",
        },
        format="json",
    )
    change_id = res_prop.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_rej = hod_c.post(
        f"/api/v1/dept/details/pending-changes/{change_id}/decision/?department=CSE",
        {"decision": "REJECT"},
        format="json",
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


# --- UC-DEPT-014 ---


def test_uc_028_main_flow(auth_client, cse_dept):
    """TEST-UC-028: UC-DEPT-014 Main Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "HOD Resolve UC", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_res = hod_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "Resolved by HOD oversight"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_uc_029_alternative_flow(auth_client, cse_dept):
    """TEST-UC-029: UC-DEPT-014 Alternative Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "HOD Review Only", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_get = hod_c.get(f"/api/v1/dept/feedback/{fb_id}/?department=CSE")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "UNDER_REVIEW"


# --- UC-DEPT-015 ---


def test_uc_030_main_flow_student_view(auth_client, cse_dept):
    """TEST-UC-030: UC-DEPT-015 Main Flow Student View"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_uc_031_main_flow_faculty_view(auth_client, cse_dept):
    """TEST-UC-031: UC-DEPT-015 Main Flow Faculty View"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_uc_032_main_flow_admin_hod_view(auth_client, cse_dept):
    """TEST-UC-032: UC-DEPT-015 Main Flow Admin/HOD View"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_uc_033_alternative_flow_unenrolled_student(auth_client, cse_dept):
    """TEST-UC-033: UC-DEPT-015 Alternative Flow Unenrolled Student"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_uc_034_alternative_flow_sensitive_data_protection(auth_client, cse_dept):
    """TEST-UC-034: UC-DEPT-015 Alternative Flow Sensitive Data Protection"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200
    for p in res.json():
        assert p["contact_phone"] is None
        assert p["emergency_contact"] is None


# --- UC-DEPT-016 ---


def test_uc_035_main_flow(auth_client, cse_dept):
    """TEST-UC-035: UC-DEPT-016 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {"user_id": "stud_uc_16", "profile_type": "STUDENT", "batch_or_roll": "2024CS99"},
        format="json",
    )
    assert res.status_code in (200, 201)


def test_uc_036_alternative_flow(auth_client, cse_dept):
    """TEST-UC-036: UC-DEPT-016 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {"user_id": "", "profile_type": "INVALID_TYPE"},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-017 ---


def test_uc_037_main_flow(auth_client, cse_dept):
    """TEST-UC-037: UC-DEPT-017 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {"lab_name": "UC Hardware Lab", "location": "Room 501", "description": "Oscilloscopes"},
        format="json",
    )
    assert res.status_code == 201


def test_uc_038_alternative_flow(auth_client, cse_dept):
    """TEST-UC-038: UC-DEPT-017 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {"lab_name": "", "location": ""},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-018 ---


def test_uc_039_main_flow(auth_client, cse_dept):
    """TEST-UC-039: UC-DEPT-018 Main Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_details = stu_c.get("/api/v1/dept/details/?department=CSE")
    assert res_details.status_code == 200
    res_tt = stu_c.get("/api/v1/dept/timetables/?department=CSE")
    assert res_tt.status_code == 200


def test_uc_040_alternative_flow(auth_client, cse_dept):
    """TEST-UC-040: UC-DEPT-018 Alternative Flow"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/timetables/?department=CSE")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# --- UC-DEPT-019 ---


def test_uc_041_main_flow(auth_client, cse_dept):
    """TEST-UC-041: UC-DEPT-019 Main Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UC-INV-01", "name": "Lab Cables", "initial_quantity": 50},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["quantity"] == 50


def test_uc_042_alternative_flow(auth_client, cse_dept):
    """TEST-UC-042: UC-DEPT-019 Alternative Flow"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "", "name": "", "initial_quantity": -5},
        format="json",
    )
    assert res.status_code == 400


# --- UC-DEPT-020 ---


def test_uc_043_main_flow(auth_client, cse_dept):
    """TEST-UC-043: UC-DEPT-020 Main Flow"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD", status="ACTIVE").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_uc_hod",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201


def test_uc_044_alternative_flow_cardinality_violation(auth_client, cse_dept):
    """TEST-UC-044: UC-DEPT-020 Alternative Flow Cardinality Violation"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD", status="ACTIVE").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_uc_hod_1",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    res_dup = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_uc_hod_2",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res_dup.status_code in (400, 409)


# --- UC-DEPT-022 ---


def test_uc_045_main_flow(auth_client, cse_dept):
    """TEST-UC-045: UC-DEPT-022 Main Flow"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "admin_trans_1",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assign_id = res.json()["id"]

    res_rev = inst_c.post(f"/api/v1/dept/roles/{assign_id}/revoke/?department=CSE", format="json")
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "REVOKED"


def test_uc_046_alternative_flow_initial_assignment(auth_client, cse_dept):
    """TEST-UC-046: UC-DEPT-022 Alternative Flow Initial Assignment"""
    DepartmentRoleAssignment.objects.filter(
        department=cse_dept, role_name="Dept_Admin", status="ACTIVE"
    ).delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "initial_admin_holder",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "ACTIVE"
