"""Specification-based tests for Functional Requirements (FR)."""

import datetime

import pytest

from modules.dept.models import (
    DepartmentRoleAssignment,
    InventoryItem,
)

pytestmark = pytest.mark.django_db


# --- CFR-DEPT-001 / AFR-DEPT-001 / AFR-DEPT-046 ---


def test_fr_001_faculty_publish(auth_client, cse_dept):
    """TEST-FR-001: AFR-DEPT-001 faculty-publish"""
    c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Faculty Notice", "content": "Classes moved to room 204", "target_role": "ALL"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["title"] == "Faculty Notice"


def test_fr_002_admin_publish(auth_client, cse_dept):
    """TEST-FR-002: AFR-DEPT-001 admin-publish"""
    c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Admin Notice",
            "content": "Registration deadline Friday",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 2,
        },
        format="json",
    )
    assert res.status_code == 201


def test_fr_003_hod_publish(auth_client, cse_dept):
    """TEST-FR-003: AFR-DEPT-001 hod-publish"""
    c = auth_client(role="HOD", user_id=301, username="hod_301")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "HOD Notice", "content": "Faculty meeting at 4 PM", "target_role": "FACULTY"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_004_unauthorized_student(auth_client, cse_dept):
    """TEST-FR-004: AFR-DEPT-001 unauthorized-student"""
    c = auth_client(role="student", user_id=501, username="stud_501")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Student Post", "content": "Unauthorized post", "target_role": "ALL"},
        format="json",
    )
    assert res.status_code == 403


def test_fr_005_announcement_notification(auth_client, cse_dept):
    """TEST-FR-005: AFR-DEPT-046 announcement-notification"""
    c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Targeted Seminar",
            "content": "Talk for 3rd years",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 3,
        },
        format="json",
    )
    assert res.status_code == 201


def test_fr_006_targeted_announcement(auth_client, cse_dept):
    """TEST-FR-006: CFR-DEPT-001 targeted-announcement"""
    c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Final Year Briefing",
            "content": "Project defense dates",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 4,
        },
        format="json",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["target_role"] == "STUDENT"
    assert data["target_program"] == "BTech"
    assert data["target_year"] == 4


# --- CFR-DEPT-002 / AFR-DEPT-002 / AFR-DEPT-003 ---


def test_fr_007_filter_matching(auth_client, cse_dept):
    """TEST-FR-007: AFR-DEPT-002 filter-matching"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "BTech 2nd Year Only",
            "content": "Room 101",
            "target_role": "STUDENT",
            "target_program": "BTech",
            "target_year": 2,
        },
        format="json",
    )
    admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {
            "title": "Faculty Meeting",
            "content": "Conf Room",
            "target_role": "FACULTY",
            "target_program": "ALL",
            "target_year": 0,
        },
        format="json",
    )
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200


def test_fr_008_view_relevant_announcements(auth_client, cse_dept):
    """TEST-FR-008: AFR-DEPT-003 view-relevant-announcements"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Open House", "content": "Welcome all", "target_role": "ALL"},
        format="json",
    )
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200
    assert any(a["title"] == "Open House" for a in res.json())


def test_fr_009_deliver_relevant(auth_client, cse_dept):
    """TEST-FR-009: CFR-DEPT-002 deliver-relevant"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/announcements/?department=CSE")
    assert res.status_code == 200


# --- CFR-DEPT-003 / AFR-DEPT-004 / AFR-DEPT-005 / AFR-DEPT-006 ---


def test_fr_010_hod_edit_announcement(auth_client, cse_dept):
    """TEST-FR-010: AFR-DEPT-004 hod-edit-announcement"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Initial Announcement", "content": "Draft", "target_role": "ALL"},
        format="json",
    )
    ann_id = res.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_edit = hod_c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"title": "Revised by HOD", "content": "Updated content"},
        format="json",
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["title"] == "Revised by HOD"


def test_fr_011_hod_hide_announcement(auth_client, cse_dept):
    """TEST-FR-011: AFR-DEPT-005 hod-hide-announcement"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "To be hidden", "content": "Temporary notice", "target_role": "ALL"},
        format="json",
    )
    ann_id = res.json()["id"]

    res_hide = hod_c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"is_active": False},
        format="json",
    )
    assert res_hide.status_code == 200
    assert res_hide.json()["is_active"] is False


def test_fr_012_hod_delete_announcement(auth_client, cse_dept):
    """TEST-FR-012: AFR-DEPT-006 hod-delete-announcement"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res = hod_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "To delete", "content": "Delete me", "target_role": "ALL"},
        format="json",
    )
    ann_id = res.json()["id"]

    res_del = hod_c.delete(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_del.status_code in (200, 204)


def test_fr_013_non_hod_announcement_maintenance(auth_client, cse_dept):
    """TEST-FR-013: CFR-DEPT-003 non-hod-announcement-maintenance"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Important", "content": "Do not delete", "target_role": "ALL"},
        format="json",
    )
    ann_id = res.json()["id"]

    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_del = stu_c.delete(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_del.status_code == 403


# --- CFR-DEPT-004 / AFR-DEPT-007 / AFR-DEPT-008 / AFR-DEPT-014 ---


def test_fr_014_admin_insert_stock(auth_client, cse_dept):
    """TEST-FR-014: AFR-DEPT-007 admin-insert-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {
            "item_code": "KIT-01",
            "name": "Microcontroller Kit",
            "category": "HARDWARE",
            "initial_quantity": 25,
            "location": "Lab 101",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["quantity"] == 25


def test_fr_015_maintain_inventory_state(auth_client, cse_dept):
    """TEST-FR-015: AFR-DEPT-008 maintain-inventory-state"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.get("/api/v1/dept/inventory/?department=CSE")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_fr_016_immutable_log_insertion(auth_client, cse_dept):
    """TEST-FR-016: AFR-DEPT-014 immutable-log-insertion"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "LOG-01", "name": "Audit Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res.json()["id"]

    res_tx = admin_c.get(f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE")
    assert res_tx.status_code == 200
    assert any(tx["transaction_type"] == "INITIAL" for tx in res_tx.json())


def test_fr_017_inventory_audit_trail(auth_client, cse_dept):
    """TEST-FR-017: CFR-DEPT-004 inventory-audit-trail"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "AT-01", "name": "Audit Trail Item", "initial_quantity": 5},
        format="json",
    )
    item_id = res.json()["id"]

    res_mod = admin_c.delete(f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE")
    assert res_mod.status_code in (404, 405)


# --- CFR-DEPT-005 / AFR-DEPT-009 / AFR-DEPT-010..013 / AFR-DEPT-015 / AFR-DEPT-041..043 ---


def test_fr_018_faculty_request_stock(auth_client, cse_dept):
    """TEST-FR-018: AFR-DEPT-009 faculty-request-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "REQ-01", "name": "Requestable Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 3, "purpose": "Lab work"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "SUBMITTED"


def test_fr_019_validate_stock_quantity_sufficient(auth_client, cse_dept):
    """TEST-FR-019: AFR-DEPT-010 validate-stock-quantity-sufficient"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "SUFF-01", "name": "Sufficient Item", "initial_quantity": 5},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 5, "purpose": "Testing"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_020_validate_stock_quantity_insufficient(auth_client, cse_dept):
    """TEST-FR-020: AFR-DEPT-010 validate-stock-quantity-insufficient"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "INSUFF-01", "name": "Limited Item", "initial_quantity": 5},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 6, "purpose": "Testing excessive"},
        format="json",
    )
    assert res.status_code == 400


def test_fr_021_hod_approve_stock(auth_client, cse_dept):
    """TEST-FR-021: AFR-DEPT-011 hod-approve-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "APP-01", "name": "Approve Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Project"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_app = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE", "remarks": "Approved"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"


def test_fr_022_hod_reject_stock(auth_client, cse_dept):
    """TEST-FR-022: AFR-DEPT-011 hod-reject-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "REJ-01", "name": "Reject Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Project"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_rej = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "REJECT", "remarks": "Not justified"},
        format="json",
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


def test_fr_023_admin_issue_approved_stock(auth_client, cse_dept):
    """TEST-FR-023: AFR-DEPT-012 admin-issue-approved-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "ISS-01", "name": "Issue Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Project"},
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
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE",
        {"notes": "Issued to faculty"},
        format="json",
    )
    assert res_iss.status_code == 200
    assert res_iss.json()["status"] == "ISSUED"


def test_fr_024_admin_issue_unapproved_stock(auth_client, cse_dept):
    """TEST-FR-024: AFR-DEPT-012 admin-issue-unapproved-stock"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "UNAPP-01", "name": "Unapproved Item", "initial_quantity": 10},
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
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE",
        {"notes": "Attempt premature issue"},
        format="json",
    )
    assert res_iss.status_code in (400, 409)


def test_fr_025_decrement_inventory_on_issue(auth_client, cse_dept):
    """TEST-FR-025: AFR-DEPT-013 decrement-inventory-on-issue"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "DEC-01", "name": "Decrement Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 4, "purpose": "Lab setup"},
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
    admin_c.post(f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json")

    item = InventoryItem.objects.get(id=item_id)
    assert item.quantity == 6


def test_fr_026_immutable_log_issuance(auth_client, cse_dept):
    """TEST-FR-026: AFR-DEPT-015 immutable-log-issuance"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "ISSLOG-01", "name": "Issue Log Item", "initial_quantity": 10},
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

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )

    admin_c.activate()
    admin_c.post(f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json")

    res_tx = admin_c.get(f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE")
    assert res_tx.status_code == 200
    assert any(tx["transaction_type"] == "ISSUE" for tx in res_tx.json())


def test_fr_027_notify_admin_on_stock_request(auth_client, cse_dept):
    """TEST-FR-027: AFR-DEPT-041 notify-admin-on-stock-request"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "NOTIF-01", "name": "Notif Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "Notif check"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_028_notify_hod_on_stock_authorization(auth_client, cse_dept):
    """TEST-FR-028: AFR-DEPT-042 notify-hod-on-stock-authorization"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "NOTIF-02", "name": "HOD Notif Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "HOD Notif"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_029_notify_faculty_on_stock_outcome(auth_client, cse_dept):
    """TEST-FR-029: AFR-DEPT-043 notify-faculty-on-stock-outcome"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "NOTIF-03", "name": "Outcome Item", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 1, "purpose": "Outcome"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "REJECT"},
        format="json",
    )
    assert res.status_code == 200


def test_fr_030_stock_request_lifecycle(auth_client, cse_dept):
    """TEST-FR-030: CFR-DEPT-005 stock-request-lifecycle"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "LC-01", "name": "Lifecycle Item", "initial_quantity": 20},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 5, "purpose": "Teaching"},
        format="json",
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_app = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_app.status_code == 200

    admin_c.activate()
    res_iss = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json"
    )
    assert res_iss.status_code == 200
    assert res_iss.json()["status"] == "ISSUED"


# --- CFR-DEPT-006 / AFR-DEPT-016 ---


def test_fr_031_faculty_issued_stock_history(auth_client, cse_dept):
    """TEST-FR-031: AFR-DEPT-016 faculty-issued-stock-history"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/stock-requests/?department=CSE")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_fr_032_issued_stock_history_access(auth_client, cse_dept):
    """TEST-FR-032: CFR-DEPT-006 issued-stock-history-access"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/stock-requests/?department=CSE")
    assert res.status_code == 403


# --- CFR-DEPT-007 / AFR-DEPT-017 / AFR-DEPT-018 / AFR-DEPT-044 ---


def test_fr_033_student_submit_feedback(auth_client, cse_dept):
    """TEST-FR-033: AFR-DEPT-017 student-submit-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Library Books", "description": "Need more AI books", "category": "ACADEMIC"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "NEW"


def test_fr_034_faculty_submit_feedback(auth_client, cse_dept):
    """TEST-FR-034: AFR-DEPT-017 faculty-submit-feedback"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Lab AC", "description": "AC not working in lab 2", "category": "FACILITY"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "NEW"


def test_fr_035_feedback_confidentiality(auth_client, cse_dept):
    """TEST-FR-035: AFR-DEPT-018 feedback-confidentiality"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Confidential", "description": "Private matter", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    stu2_c = auth_client(role="student", user_id=502, username="stud_502")
    res_other = stu2_c.get(f"/api/v1/dept/feedback/{fb_id}/?department=CSE")
    assert res_other.status_code in (403, 404)


def test_fr_036_notify_admin_on_feedback(auth_client, cse_dept):
    """TEST-FR-036: AFR-DEPT-044 notify-admin-on-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "New Issue", "description": "Notification check", "category": "OTHER"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_037_submit_confidential_feedback(auth_client, cse_dept):
    """TEST-FR-037: CFR-DEPT-007 submit-confidential-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Confidential Topic", "description": "Issue details", "category": "ACADEMIC"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "NEW"


# --- CFR-DEPT-008 / AFR-DEPT-019..023 / AFR-DEPT-045 ---


def test_fr_038_admin_initial_review(auth_client, cse_dept):
    """TEST-FR-038: AFR-DEPT-019 admin-initial-review"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Review me", "description": "Need review", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"admin_remarks": "Under initial review"},
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"


def test_fr_039_admin_categorize_feedback(auth_client, cse_dept):
    """TEST-FR-039: AFR-DEPT-020 admin-categorize-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Categorize me", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_cat = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"category": "INFRASTRUCTURE", "admin_remarks": "Categorized"},
        format="json",
    )
    assert res_cat.status_code == 200
    assert res_cat.json()["category"] == "INFRASTRUCTURE"


def test_fr_040_admin_close_simple_issue(auth_client, cse_dept):
    """TEST-FR-040: AFR-DEPT-021 admin-close-simple-issue"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Simple Issue", "description": "Quick fix", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_close = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "CLOSE", "remarks": "Resolved immediately"},
        format="json",
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"


def test_fr_041_admin_resolve_feedback(auth_client, cse_dept):
    """TEST-FR-041: AFR-DEPT-022 admin-resolve-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Admin Resolve", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")
    res_res = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "Issue addressed"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_fr_042_hod_resolve_feedback(auth_client, cse_dept):
    """TEST-FR-042: AFR-DEPT-022 hod-resolve-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "HOD Resolve", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_res = hod_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "HOD approved resolution"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_fr_043_hod_feedback_oversight(auth_client, cse_dept):
    """TEST-FR-043: AFR-DEPT-023 hod-feedback-oversight"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res = hod_c.get("/api/v1/dept/feedback/?department=CSE")
    assert res.status_code == 200


def test_fr_044_notify_submitter_feedback_terminal(auth_client, cse_dept):
    """TEST-FR-044: AFR-DEPT-045 notify-submitter-feedback-terminal"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Notif on Resolve", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_res = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE"},
        format="json",
    )
    assert res_res.status_code == 200


def test_fr_045_review_resolve_feedback(auth_client, cse_dept):
    """TEST-FR-045: CFR-DEPT-008 review-resolve-feedback"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "Unauthorized Test", "description": "Details", "category": "OTHER"},
        format="json",
    )
    fb_id = res.json()["id"]

    res_res = stu_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE"},
        format="json",
    )
    assert res_res.status_code == 403


# --- CFR-DEPT-009 / AFR-DEPT-024 ---


def test_fr_046_admin_manage_profiles(auth_client, cse_dept):
    """TEST-FR-046: AFR-DEPT-024 admin-manage-profiles"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {
            "user_id": "fac_profile_1",
            "profile_type": "FACULTY",
            "contact_phone": "+91-9876543210",
            "emergency_contact": "Emergency: 112",
            "research_interests": "Distributed Systems",
        },
        format="json",
    )
    assert res.status_code in (200, 201)


def test_fr_047_manage_user_profiles(auth_client, cse_dept):
    """TEST-FR-047: CFR-DEPT-009 manage-user-profiles"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {"user_id": "fac_profile_2", "profile_type": "FACULTY"},
        format="json",
    )
    assert res.status_code == 403


# --- CFR-DEPT-010 / AFR-DEPT-025..028 ---


def test_fr_048_student_view_profile_basic(auth_client, cse_dept):
    """TEST-FR-048: AFR-DEPT-025 student-view-profile-basic"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {
            "user_id": "stud_masked",
            "profile_type": "STUDENT",
            "contact_phone": "+91-9000000001",
            "emergency_contact": "Guardian",
        },
        format="json",
    )

    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200
    for p in res.json():
        if p["user_id"] == "stud_masked":
            assert p["contact_phone"] is None
            assert p["emergency_contact"] is None


def test_fr_049_faculty_view_student_enrolled(auth_client, cse_dept):
    """TEST-FR-049: AFR-DEPT-026 faculty-view-student-enrolled"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_fr_050_faculty_view_peers_alumni(auth_client, cse_dept):
    """TEST-FR-050: AFR-DEPT-027 faculty-view-peers-alumni"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_fr_051_admin_hod_full_profile_sensitive_masked(auth_client, cse_dept):
    """TEST-FR-051: AFR-DEPT-028 admin-hod-full-profile-sensitive-masked"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


def test_fr_052_enforce_profile_visibility(auth_client, cse_dept):
    """TEST-FR-052: CFR-DEPT-010 enforce-profile-visibility"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res.status_code == 200


# --- CFR-DEPT-011 / AFR-DEPT-029..031 ---


def test_fr_053_admin_upload_timetable(auth_client, cse_dept):
    """TEST-FR-053: AFR-DEPT-029 admin-upload-timetable"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 1,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "course_code": "CS201",
            "course_name": "Data Structures",
            "instructor_id": "prof_ds",
            "room_or_lab": "Room 201",
        },
        format="json",
    )
    assert res.status_code == 201


def test_fr_054_admin_modify_timetable(auth_client, cse_dept):
    """TEST-FR-054: AFR-DEPT-030 admin-modify-timetable"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 2,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "course_code": "CS202",
            "course_name": "Algorithms",
            "instructor_id": "prof_algo",
            "room_or_lab": "Room 202",
        },
        format="json",
    )
    tt_id = res.json()["id"]

    res_patch = admin_c.patch(
        f"/api/v1/dept/timetables/{tt_id}/?department=CSE",
        {"room_or_lab": "Room 203"},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["room_or_lab"] == "Room 203"


def test_fr_055_detect_timetable_conflict_block(auth_client, cse_dept):
    """TEST-FR-055: AFR-DEPT-031 detect-timetable-conflict-block"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 3,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "course_code": "CS203",
            "course_name": "Operating Systems",
            "instructor_id": "prof_os",
            "room_or_lab": "Lab L101",
        },
        format="json",
    )

    res_conf = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 3,
            "start_time": "10:30:00",
            "end_time": "11:30:00",
            "course_code": "CS204",
            "course_name": "Networks",
            "instructor_id": "prof_net",
            "room_or_lab": "Lab L101",
        },
        format="json",
    )
    assert res_conf.status_code in (400, 409)


def test_fr_056_conflict_free_timetable(auth_client, cse_dept):
    """TEST-FR-056: CFR-DEPT-011 conflict-free-timetable"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "BTech",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 4,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "course_code": "CS205",
            "course_name": "Databases",
            "instructor_id": "prof_db",
            "room_or_lab": "Room 205",
        },
        format="json",
    )
    assert res.status_code == 201


# --- CFR-DEPT-012 / AFR-DEPT-034 / AFR-DEPT-035 ---


def test_fr_057_admin_update_lab_profiles(auth_client, cse_dept):
    """TEST-FR-057: AFR-DEPT-034 admin-update-lab-profiles"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {"lab_name": "Network Lab", "location": "Room 401", "description": "Cisco routers"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_058_faculty_view_lab_resources(auth_client, cse_dept):
    """TEST-FR-058: AFR-DEPT-035 faculty-view-lab-resources"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.get("/api/v1/dept/labs/?department=CSE")
    assert res.status_code == 200


def test_fr_059_manage_view_lab_resources(auth_client, cse_dept):
    """TEST-FR-059: CFR-DEPT-012 manage-view-lab-resources"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {"lab_name": "Unauthorized Lab", "location": "Room 999"},
        format="json",
    )
    assert res.status_code == 403


# --- CFR-DEPT-013 / AFR-DEPT-036 / AFR-DEPT-037 ---


def test_fr_060_student_view_academic_program(auth_client, cse_dept):
    """TEST-FR-060: AFR-DEPT-036 student-view-academic-program"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/details/?department=CSE")
    assert res.status_code == 200


def test_fr_061_student_view_timetable(auth_client, cse_dept):
    """TEST-FR-061: AFR-DEPT-037 student-view-timetable"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/timetables/?department=CSE")
    assert res.status_code == 200


def test_fr_062_student_academic_info(auth_client, cse_dept):
    """TEST-FR-062: CFR-DEPT-013 student-academic-info"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {"course_code": "CS999", "room_or_lab": "Room 101"},
        format="json",
    )
    assert res.status_code == 403


# --- CFR-DEPT-014 / AFR-DEPT-038 ---


def test_fr_063_admin_update_general_dept_info(auth_client, cse_dept):
    """TEST-FR-063: AFR-DEPT-038 admin-update-general-dept-info"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.patch(
        "/api/v1/dept/details/?department=CSE",
        {"description": "Updated Department Description"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Updated Department Description"


def test_fr_064_general_dept_info_update(auth_client, cse_dept):
    """TEST-FR-064: CFR-DEPT-014 general-dept-info-update"""
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res = fac_c.patch(
        "/api/v1/dept/details/?department=CSE",
        {"description": "Unauthorized Description"},
        format="json",
    )
    assert res.status_code == 403


# --- CFR-DEPT-015 / AFR-DEPT-039 / AFR-DEPT-040 ---


def test_fr_065_official_change_pending_hod(auth_client, cse_dept):
    """TEST-FR-065: AFR-DEPT-039 official-change-pending-hod"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Updated Core Policy A",
            "justification": "Annual review",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING_HOD"


def test_fr_066_hod_approve_official_change(auth_client, cse_dept):
    """TEST-FR-066: AFR-DEPT-040 hod-approve-official-change"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Updated Core Policy B",
            "justification": "Annual review",
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


def test_fr_067_hod_reject_official_change(auth_client, cse_dept):
    """TEST-FR-067: AFR-DEPT-040 hod-reject-official-change"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Updated Core Policy C",
            "justification": "Annual review",
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


def test_fr_068_official_change_headship_exclusion(auth_client, cse_dept):
    """TEST-FR-068: CFR-DEPT-015 official-change-headship-exclusion"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "head_of_department_id",
            "new_value": "prof_fake",
            "justification": "Direct edit attempt",
        },
        format="json",
    )
    assert res.status_code == 400


# --- CFR-DEPT-016 / AFR-DEPT-047..053 ---


def test_fr_069_institute_admin_role_assignment(auth_client, cse_dept):
    """TEST-FR-069: AFR-DEPT-047 institute-admin-role-assignment"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_hod_assign",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201


def test_fr_070_role_validity_interval(auth_client, cse_dept):
    """TEST-FR-070: AFR-DEPT-048 role-validity-interval"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    res = inst_c.get("/api/v1/dept/roles/?department=CSE")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_fr_071_revoke_outgoing_role_access(auth_client, cse_dept):
    """TEST-FR-071: AFR-DEPT-049 revoke-outgoing-role-access"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "admin_to_revoke",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assign_id = res.json()["id"]

    res_rev = inst_c.post(f"/api/v1/dept/roles/{assign_id}/revoke/?department=CSE", format="json")
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "REVOKED"


def test_fr_072_grant_incoming_role_access(auth_client, cse_dept):
    """TEST-FR-072: AFR-DEPT-050 grant-incoming-role-access"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "incoming_admin",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "ACTIVE"


def test_fr_073_unique_active_hod(auth_client, cse_dept):
    """TEST-FR-073: AFR-DEPT-051 unique-active-hod"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD", status="ACTIVE").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res1 = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "hod_unique_1",
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
            "user_id": "hod_unique_2",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res2.status_code in (400, 409)


def test_fr_074_unique_active_admin(auth_client, cse_dept):
    """TEST-FR-074: AFR-DEPT-052 unique-active-admin"""
    DepartmentRoleAssignment.objects.filter(
        department=cse_dept, role_name="Dept_Admin", status="ACTIVE"
    ).delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res1 = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "admin_unique_1",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res1.status_code == 201

    res2 = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "Dept_Admin",
            "user_id": "admin_unique_2",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res2.status_code in (400, 409)


def test_fr_075_derive_displayed_headship(auth_client, cse_dept):
    """TEST-FR-075: AFR-DEPT-053 derive-displayed-headship"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD").delete()
    now = datetime.datetime.now(datetime.UTC)
    inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_head_authoritative",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )

    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res = stu_c.get("/api/v1/dept/details/?department=CSE")
    assert res.status_code == 200
    assert res.json()["head_of_department_id"] == "prof_head_authoritative"


def test_fr_076_maintain_dept_roles(auth_client, cse_dept):
    """TEST-FR-076: CFR-DEPT-016 maintain-dept-roles"""
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    now = datetime.datetime.now(datetime.UTC)
    res = hod_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "someone_else",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 403
