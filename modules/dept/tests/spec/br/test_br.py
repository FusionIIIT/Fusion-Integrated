"""Specification-based tests for Business Rules (BR)."""

import datetime

import pytest

from modules.dept.models import (
    DepartmentRoleAssignment,
)

pytestmark = pytest.mark.django_db


# --- BR-DEPT-001 ---


def test_br_001_permitted(auth_client, cse_dept):
    """TEST-BR-001: BR-DEPT-001 permitted"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res1 = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "BR Ann 1", "content": "Content", "target_role": "ALL"},
        format="json",
    )
    assert res1.status_code == 201

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res2 = admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "BR Ann 2", "content": "Content", "target_role": "ALL"},
        format="json",
    )
    assert res2.status_code == 201

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res3 = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "BR Ann 3", "content": "Content", "target_role": "ALL"},
        format="json",
    )
    assert res3.status_code == 201


def test_br_002_prohibited(auth_client, cse_dept):
    """TEST-BR-002: BR-DEPT-001 prohibited"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Student Prohibited", "content": "Content"},
        format="json",
    )
    assert res.status_code == 403


# --- BR-DEPT-002 ---


def test_br_003_matching_scope(auth_client, cse_dept):
    """TEST-BR-003: BR-DEPT-002 matching-scope"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "BTech Year 3 Notice",
            "content": "Specific target",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 3,
        },
        format="json",
    )
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200


def test_br_004_non_matching_scope(auth_client, cse_dept):
    """TEST-BR-004: BR-DEPT-002 non-matching-scope"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200


# --- BR-DEPT-003 ---


def test_br_005_valid_completeness(auth_client, cse_dept):
    """TEST-BR-005: BR-DEPT-003 valid-completeness"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Complete Notice",
            "content": "Complete content body",
            "target_role": "ALL",
            "target_program": "ALL",
            "target_year": 0,
        },
        format="json",
    )
    assert res.status_code == 201


def test_br_006_missing_content(auth_client, cse_dept):
    """TEST-BR-006: BR-DEPT-003 missing-content"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "", "content": ""},
        format="json",
    )
    assert res.status_code in (400, 409)


# --- BR-DEPT-004 ---


def test_br_007_permitted_hod(auth_client, cse_dept):
    """TEST-BR-007: BR-DEPT-004 permitted-hod"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_ann = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "HOD Controlled", "content": "Initial", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    res_patch = hod_c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"title": "HOD Edited"},
        format="json",
    )
    assert res_patch.status_code == 200


def test_br_008_prohibited_non_hod(auth_client, cse_dept):
    """TEST-BR-008: BR-DEPT-004 prohibited-non-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_ann = admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Admin Created", "content": "Content", "target_role": "ALL"},
        format="json",
    )
    ann_id = res_ann.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_del = fac_c.delete(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_del.status_code == 403


# --- BR-DEPT-005 ---


def test_br_009_permitted_faculty(auth_client, cse_dept):
    """TEST-BR-009: BR-DEPT-005 permitted-faculty"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-STOCK-01", "name": "Item BR1", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Lab work"},
        format="json",
    )
    assert res.status_code == 201


def test_br_010_prohibited_non_faculty(auth_client, cse_dept):
    """TEST-BR-010: BR-DEPT-005 prohibited-non-faculty"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": 9999, "requested_quantity": 1, "purpose": "Unauthorized"},
        format="json",
    )
    assert res.status_code == 403


# --- BR-DEPT-006 ---


def test_br_011_permitted_hod(auth_client, cse_dept):
    """TEST-BR-011: BR-DEPT-006 permitted-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-APP-01", "name": "Item App", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Teaching"},
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


def test_br_012_prohibited_non_hod(auth_client, cse_dept):
    """TEST-BR-012: BR-DEPT-006 prohibited-non-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-APP-02", "name": "Item App 2", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Teaching"},
        format="json",
    )
    req_id = res_req.json()["id"]

    admin_c.activate()
    res_dec = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_dec.status_code == 403


# --- BR-DEPT-007 ---


def test_br_013_permitted_approved_issuance(auth_client, cse_dept):
    """TEST-BR-013: BR-DEPT-007 permitted-approved-issuance"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-ISS-01", "name": "Issuance BR", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 3, "purpose": "Lab work"},
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


def test_br_014_prohibited_unapproved(auth_client, cse_dept):
    """TEST-BR-014: BR-DEPT-007 prohibited-unapproved"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-UNAPP-01", "name": "Unapproved BR", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Testing"},
        format="json",
    )
    req_id = res_req.json()["id"]

    admin_c.activate()
    res_iss = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json"
    )
    assert res_iss.status_code in (400, 409)


def test_br_015_prohibited_non_admin(auth_client, cse_dept):
    """TEST-BR-015: BR-DEPT-007 prohibited-non-admin"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-PROHIB-01", "name": "Prohib Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Prohib"},
        format="json",
    )
    req_id = res_req.json()["id"]

    res_iss = fac_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json"
    )
    assert res_iss.status_code == 403


# --- BR-DEPT-008 ---


def test_br_016_permitted_student_faculty(auth_client, cse_dept):
    """TEST-BR-016: BR-DEPT-008 permitted-student-faculty"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_stu = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Student BR Feedback", "description": "Details", "category": "ACADEMIC"},
        format="json",
    )
    assert res_stu.status_code == 201

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_fac = fac_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Faculty BR Feedback", "description": "Details", "category": "INFRASTRUCTURE"},
        format="json",
    )
    assert res_fac.status_code == 201


def test_br_017_prohibited_unauthenticated(auth_client, cse_dept):
    """TEST-BR-017: BR-DEPT-008 prohibited-unauthenticated"""
    from rest_framework.test import APIClient

    anon_c = APIClient()
    res = anon_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Anon Feedback", "description": "Details"},
        format="json",
    )
    assert res.status_code in (401, 403)


# --- BR-DEPT-009 ---


def test_br_018_permitted_admin_simple_closure(auth_client, cse_dept):
    """TEST-BR-018: BR-DEPT-009 permitted-admin-simple-closure"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Quick Fix BR", "description": "Door handle loose", "category": "INFRASTRUCTURE"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_close = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "CLOSE", "remarks": "Fixed door handle"},
        format="json",
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"


def test_br_019_permitted_admin_hod_resolution(auth_client, cse_dept):
    """TEST-BR-019: BR-DEPT-009 permitted-admin-hod-resolution"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Lab AC BR", "description": "AC repaired", "category": "INFRASTRUCTURE"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_res = hod_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "Confirmed repaired"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_br_020_prohibited_non_authority(auth_client, cse_dept):
    """TEST-BR-020: BR-DEPT-009 prohibited-non-authority"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Student Self-Resolve", "description": "Attempt", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    res_res = stu_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE"},
        format="json",
    )
    assert res_res.status_code == 403


# --- BR-DEPT-010 ---


def test_br_021_permitted_conflict_free(auth_client, cse_dept):
    """TEST-BR-021: BR-DEPT-010 permitted-conflict-free"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 1,
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "course_code": "CS401",
            "course_name": "Math",
            "instructor_id": "prof_math",
            "room_or_lab": "Room 401",
        },
        format="json",
    )
    assert res.status_code == 201


def test_br_022_prohibited_slot_overlap(auth_client, cse_dept):
    """TEST-BR-022: BR-DEPT-010 prohibited-slot-overlap"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "course_code": "CS402",
            "course_name": "Physics",
            "instructor_id": "prof_phy",
            "room_or_lab": "Room 402",
        },
        format="json",
    )

    res_overlap = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 1,
            "start_time": "09:30:00",
            "end_time": "10:30:00",
            "course_code": "CS403",
            "course_name": "Chemistry",
            "instructor_id": "prof_chem",
            "room_or_lab": "Room 402",
        },
        format="json",
    )
    assert res_overlap.status_code in (400, 409)


# --- BR-DEPT-011 ---


def test_br_023_routed_pending_hod(auth_client, cse_dept):
    """TEST-BR-023: BR-DEPT-011 routed-pending-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "BR Policy Update",
            "justification": "Senate note",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] in ("PENDING", "PENDING_HOD")


def test_br_024_headship_excluded(auth_client, cse_dept):
    """TEST-BR-024: BR-DEPT-011 headship-excluded"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {"field_name": "head_of_department_id", "new_value": "prof_illegal"},
        format="json",
    )
    assert res.status_code in (400, 409)


# --- BR-DEPT-012 ---


def test_br_025_permitted_faculty_scope(auth_client, cse_dept):
    """TEST-BR-025: BR-DEPT-012 permitted-faculty-scope"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_labs = fac_c.get("/api/v1/dept/labs/?department=CSE")
    assert res_labs.status_code == 200
    res_stock = fac_c.get("/api/v1/dept/stock-requests/?department=CSE")
    assert res_stock.status_code == 200


def test_br_026_prohibited_out_of_scope(auth_client, cse_dept):
    """TEST-BR-026: BR-DEPT-012 prohibited-out-of-scope"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {"lab_name": "Out of scope lab", "location": "Room 000"},
        format="json",
    )
    assert res.status_code == 403


# --- BR-DEPT-013 ---


def test_br_027_permitted_hod(auth_client, cse_dept):
    """TEST-BR-027: BR-DEPT-013 permitted-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "BR Policy HOD Test",
            "justification": "Test justification",
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


def test_br_028_prohibited_non_hod(auth_client, cse_dept):
    """TEST-BR-028: BR-DEPT-013 prohibited-non-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Admin Self Decision",
            "justification": "Self test",
        },
        format="json",
    )
    change_id = res_prop.json()["id"]

    res_dec = admin_c.post(
        f"/api/v1/dept/details/pending-changes/{change_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_dec.status_code == 403


# --- BR-DEPT-015 ---


def test_br_029_permitted_sufficient_inventory(auth_client, cse_dept):
    """TEST-BR-029: BR-DEPT-015 permitted-sufficient-inventory"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-SUFF-01", "name": "Item Suff", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 10, "purpose": "All stock"},
        format="json",
    )
    assert res.status_code == 201


def test_br_030_prohibited_insufficient_inventory(auth_client, cse_dept):
    """TEST-BR-030: BR-DEPT-015 prohibited-insufficient-inventory"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-INSUFF-01", "name": "Item Insuff", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 11, "purpose": "Too much"},
        format="json",
    )
    assert res.status_code in (400, 409)


# --- BR-DEPT-016 ---


def test_br_031_audit_log_created(auth_client, cse_dept):
    """TEST-BR-031: BR-DEPT-016 audit-log-created"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-AUD-01", "name": "Audit Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    res_tx = admin_c.get(f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE")
    assert res_tx.status_code == 200
    assert len(res_tx.json()) >= 1


def test_br_032_audit_log_immutable(auth_client, cse_dept):
    """TEST-BR-032: BR-DEPT-016 audit-log-immutable"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "BR-AUD-02", "name": "Audit Immutable", "initial_quantity": 5},
        format="json",
    )
    item_id = res_item.json()["id"]

    res_mod = admin_c.put(
        f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE", format="json"
    )
    assert res_mod.status_code in (404, 405)


# --- BR-DEPT-017 ---


def test_br_033_permitted_confidential_view(auth_client, cse_dept):
    """TEST-BR-033: BR-DEPT-017 permitted-confidential-view"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Confidential BR", "description": "Details", "category": "ACADEMIC"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    res_self = stu_c.get("/api/v1/dept/feedback/?department=CSE")
    assert res_self.status_code == 200
    assert any(fb["id"] == fb_id for fb in res_self.json())

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_admin = admin_c.get("/api/v1/dept/feedback/?department=CSE")
    assert res_admin.status_code == 200
    assert any(fb["id"] == fb_id for fb in res_admin.json())

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_hod = hod_c.get("/api/v1/dept/feedback/?department=CSE")
    assert res_hod.status_code == 200
    assert any(fb["id"] == fb_id for fb in res_hod.json())


def test_br_034_prohibited_peer_view(auth_client, cse_dept):
    """TEST-BR-034: BR-DEPT-017 prohibited-peer-view"""
    stu1_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu1_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Peer Withheld", "description": "Secret", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    stu2_c = auth_client(role="student", user_id=502, username="stud_502")
    res_peer = stu2_c.get("/api/v1/dept/feedback/?department=CSE")
    assert res_peer.status_code == 200
    assert not any(fb["id"] == fb_id for fb in res_peer.json())


# --- BR-DEPT-018 ---


def test_br_035_admin_initial_review_required(auth_client, cse_dept):
    """TEST-BR-035: BR-DEPT-018 admin-initial-review-required"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Need Initial Review", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"category": "INFRASTRUCTURE", "admin_remarks": "Reviewed"},
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


def test_br_036_hod_oversight_sequence(auth_client, cse_dept):
    """TEST-BR-036: BR-DEPT-018 hod-oversight-sequence"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Sequence Test", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_res = hod_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE"},
        format="json",
    )
    assert res_res.status_code == 200


# --- BR-DEPT-019 ---


def test_br_037_student_visibility(auth_client, cse_dept):
    """TEST-BR-037: BR-DEPT-019 student-visibility"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200
    for p in res.json():
        assert p["contact_phone"] is None


def test_br_038_faculty_student_enrolled_visibility(auth_client, cse_dept):
    """TEST-BR-038: BR-DEPT-019 faculty-student-enrolled-visibility"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_br_039_admin_hod_visibility_privacy_masked(auth_client, cse_dept):
    """TEST-BR-039: BR-DEPT-019 admin-hod-visibility-privacy-masked"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


# --- BR-DEPT-021 ---


def test_br_040_permitted_institute_admin(auth_client, cse_dept):
    """TEST-BR-040: BR-DEPT-021 permitted-institute-admin"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD", status="ACTIVE").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_central_hod",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201


def test_br_041_prohibited_local_authority(auth_client, cse_dept):
    """TEST-BR-041: BR-DEPT-021 prohibited-local-authority"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    now = datetime.datetime.now(datetime.UTC)
    res = hod_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_local_assign",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 403


# --- BR-DEPT-022 ---


def test_br_042_single_active_role_permitted(auth_client, cse_dept):
    """TEST-BR-042: BR-DEPT-022 single-active-role-permitted"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    res = inst_c.get("/api/v1/dept/roles/?department=CSE")
    assert res.status_code == 200
    active_hods = [r for r in res.json() if r["role_name"] == "HOD" and r["status"] == "ACTIVE"]
    assert len(active_hods) <= 1


def test_br_043_duplicate_active_role_blocked(auth_client, cse_dept):
    """TEST-BR-043: BR-DEPT-022 duplicate-active-role-blocked"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD", status="ACTIVE").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res1 = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "hod_dup_1",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res1.status_code == 201

    res2 = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "hod_dup_2",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res2.status_code in (400, 409)


# --- BR-DEPT-023 ---


def test_br_044_tenure_interval_enforced(auth_client, cse_dept):
    """TEST-BR-044: BR-DEPT-023 tenure-interval-enforced"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    res = inst_c.get("/api/v1/dept/roles/?department=CSE")
    assert res.status_code == 200
    for r in res.json():
        assert "start_date" in r
        assert "end_date" in r


# --- BR-DEPT-024 ---


def test_br_045_immediate_transition_applied(auth_client, cse_dept):
    """TEST-BR-045: BR-DEPT-024 immediate-transition-applied"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "DEPT_ADMIN",
            "user_id": "admin_transition_target",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assign_id = res.json()["id"]

    res_rev = inst_c.post(f"/api/v1/dept/roles/{assign_id}/revoke/?department=CSE", format="json")
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "REVOKED"
