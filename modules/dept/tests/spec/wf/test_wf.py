"""Specification-based tests for Workflows (WF)."""

import datetime

import pytest

from modules.dept.models import (
    DepartmentRoleAssignment,
    InventoryItem,
)

pytestmark = pytest.mark.django_db


# --- BW-DEPT-01 / BW-DEPT-02 / CW-DEPT-01 ---


def test_wf_001_bw_dept_01_approval_and_issuance_path(auth_client, cse_dept):
    """TEST-WF-001: BW-DEPT-01 approval-and-issuance-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "WF-ITEM-01", "name": "WF Item 1", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    # Step 1: Faculty requests stock
    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 3, "purpose": "WF Step 1"},
        format="json",
    )
    assert res_req.status_code == 201
    assert res_req.json()["status"] == "SUBMITTED"
    req_id = res_req.json()["id"]

    # Step 2: HOD approves
    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_app = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # Step 3: Dept_Admin issues
    admin_c.activate()
    res_iss = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE", format="json"
    )
    assert res_iss.status_code == 200
    assert res_iss.json()["status"] == "ISSUED"

    item = InventoryItem.objects.get(id=item_id)
    assert item.quantity == 7


def test_wf_002_bw_dept_02_rejection_path(auth_client, cse_dept):
    """TEST-WF-002: BW-DEPT-02 rejection-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "WF-ITEM-02", "name": "WF Item 2", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 2, "purpose": "WF Step 2"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_rej = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "REJECT", "remarks": "Not needed"},
        format="json",
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


def test_wf_003_cw_dept_01_composite_stock_approved_path(auth_client, cse_dept):
    """TEST-WF-003: CW-DEPT-01 composite-stock-approved-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "CW-ITEM-01", "name": "CW Item 1", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 4, "purpose": "CW Path A"},
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


def test_wf_004_cw_dept_01_composite_stock_rejected_path(auth_client, cse_dept):
    """TEST-WF-004: CW-DEPT-01 composite-stock-rejected-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "CW-ITEM-02", "name": "CW Item 2", "initial_quantity": 10},
        format="json",
    )
    item_id = res_item.json()["id"]

    fac_c = auth_client(role="faculty", user_id=101, username="fac_101")
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 3, "purpose": "CW Path B"},
        format="json",
    )
    req_id = res_req.json()["id"]

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_rej = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "REJECT"},
        format="json",
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


# --- BW-DEPT-03 / BW-DEPT-04 / CW-DEPT-02 ---


def test_wf_005_bw_dept_03_admin_disposition_path(auth_client, cse_dept):
    """TEST-WF-005: BW-DEPT-03 admin-disposition-path"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "BW Feedback 1", "description": "Need lab access", "category": "INFRASTRUCTURE"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"admin_remarks": "Reviewed by Admin"},
        format="json",
    )
    assert res_rev.status_code == 200

    res_close = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "CLOSE", "remarks": "Access granted"},
        format="json",
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"


def test_wf_006_bw_dept_04_hod_oversight_path(auth_client, cse_dept):
    """TEST-WF-006: BW-DEPT-04 hod-oversight-path"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "BW Feedback 2", "description": "Curriculum feedback", "category": "ACADEMIC"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")

    hod_c = auth_client(role="HOD", user_id=301, username="hod_301")
    res_res = hod_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "Curriculum updated"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_wf_007_cw_dept_02_composite_feedback_admin_path(auth_client, cse_dept):
    """TEST-WF-007: CW-DEPT-02 composite-feedback-admin-path"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "CW Feedback 1", "description": "Admin path test", "category": "OTHER"},
        format="json",
    )
    fb_id = res_fb.json()["id"]

    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    admin_c.post(f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE", format="json")
    res_res = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_wf_008_cw_dept_02_composite_feedback_hod_path(auth_client, cse_dept):
    """TEST-WF-008: CW-DEPT-02 composite-feedback-hod-path"""
    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_fb = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {"title": "CW Feedback 2", "description": "HOD path test", "category": "ACADEMIC"},
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
    assert res_res.json()["status"] == "RESOLVED"


# --- BW-DEPT-05 / BW-DEPT-06 / CW-DEPT-03 ---


def test_wf_009_bw_dept_05_official_change_approved_path(auth_client, cse_dept):
    """TEST-WF-009: BW-DEPT-05 official-change-approved-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "BW Approved Policy",
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


def test_wf_010_bw_dept_06_official_change_rejected_path(auth_client, cse_dept):
    """TEST-WF-010: BW-DEPT-06 official-change-rejected-path"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "BW Rejected Policy",
            "justification": "Test rule",
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


def test_wf_011_cw_dept_03_composite_official_change_approved(auth_client, cse_dept):
    """TEST-WF-011: CW-DEPT-03 composite-official-change-approved"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "CW Approved Policy",
            "justification": "Senate update",
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


def test_wf_012_cw_dept_03_composite_official_change_rejected(auth_client, cse_dept):
    """TEST-WF-012: CW-DEPT-03 composite-official-change-rejected"""
    admin_c = auth_client(role="Dept_Admin", user_id=999, username="admin_999")
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "CW Rejected Policy",
            "justification": "Test reject",
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


# --- BW-DEPT-07 / BW-DEPT-08 / CW-DEPT-04 ---


def test_wf_013_bw_dept_07_hod_reassignment_headship_sync(auth_client, cse_dept):
    """TEST-WF-013: BW-DEPT-07 hod-reassignment-headship-sync"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_wf_hod_new",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201

    stu_c = auth_client(role="student", user_id=501, username="stud_501")
    res_det = stu_c.get("/api/v1/dept/details/?department=CSE")
    assert res_det.status_code == 200
    assert res_det.json()["head_of_department_id"] == "prof_wf_hod_new"


def test_wf_014_bw_dept_08_admin_reassignment_access_transition(auth_client, cse_dept):
    """TEST-WF-014: BW-DEPT-08 admin-reassignment-access-transition"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "DEPT_ADMIN",
            "user_id": "admin_wf_trans",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assign_id = res.json()["id"]

    res_rev = inst_c.post(f"/api/v1/dept/roles/{assign_id}/revoke/?department=CSE", format="json")
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "REVOKED"


def test_wf_015_cw_dept_04_composite_hod_reassignment_path(auth_client, cse_dept):
    """TEST-WF-015: CW-DEPT-04 composite-hod-reassignment-path"""
    DepartmentRoleAssignment.objects.filter(department=cse_dept, role_name="HOD").delete()
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_cw_hod",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201


def test_wf_016_cw_dept_04_composite_admin_reassignment_path(auth_client, cse_dept):
    """TEST-WF-016: CW-DEPT-04 composite-admin-reassignment-path"""
    inst_c = auth_client(role="Institute Admin", user_id=1, username="inst_admin")
    now = datetime.datetime.now(datetime.UTC)
    res = inst_c.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "DEPT_ADMIN",
            "user_id": "admin_cw_trans",
            "start_date": now.isoformat(),
            "end_date": (now + datetime.timedelta(days=365)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 201
