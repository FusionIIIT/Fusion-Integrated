"""API endpoint integration tests."""

import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.dept.models import (
    Department,
    InventoryItem,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def cse_dept():
    return Department.objects.create(code="CSE", name="Computer Science and Engineering")


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_announcements_flow(stub_iam, cse_dept):
    c = _client(
        stub_iam,
        user_id=101,
        modules=("dept",),
        permissions=("dept.announcement.view", "dept.announcement.create"),
        roles=("faculty",),
    )

    # Create announcement
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Exam Schedule", "content": "Midsems start next week", "target_role": "ALL"},
        format="json",
    )
    assert res.status_code == 201
    ann_id = res.json()["id"]

    # View announcement
    res_list = c.get("/api/v1/dept/announcements/?department=CSE")
    assert res_list.status_code == 200
    ids = [a["id"] for a in res_list.json()]
    assert ann_id in ids


def test_inventory_and_stock_request_lifecycle(stub_iam, cse_dept):
    # Admin creates inventory
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.inventory.view", "dept.inventory.create", "dept.stock_request.issue"),
        roles=("Dept_Admin",),
    )
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {
            "item_code": "MARKER-01",
            "name": "Whiteboard Markers",
            "category": "CONSUMABLE",
            "initial_quantity": 20,
        },
        format="json",
    )
    assert res_item.status_code == 201
    item_id = res_item.json()["id"]

    # Faculty submits request
    fac_c = _client(
        stub_iam,
        user_id=201,
        modules=("dept",),
        permissions=("dept.stock_request.view", "dept.stock_request.create"),
        roles=("faculty",),
    )
    res_req = fac_c.post(
        "/api/v1/dept/stock-requests/?department=CSE",
        {"inventory_item_id": item_id, "requested_quantity": 5, "purpose": "CS101 lectures"},
        format="json",
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]
    assert res_req.json()["status"] == "SUBMITTED"

    # HOD approves request
    hod_c = _client(
        stub_iam,
        user_id=301,
        modules=("dept",),
        permissions=("dept.stock_request.approve", "dept.stock_request.view"),
        roles=("HOD",),
    )
    res_app = hod_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/decision/?department=CSE",
        {"decision": "APPROVE", "remarks": "Approved for teaching"},
        format="json",
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # Admin issues stock
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.inventory.view", "dept.inventory.create", "dept.stock_request.issue"),
        roles=("Dept_Admin",),
    )
    res_issue = admin_c.post(
        f"/api/v1/dept/stock-requests/{req_id}/issue/?department=CSE",
        {"notes": "Issued pack of 5"},
        format="json",
    )
    assert res_issue.status_code == 200
    assert res_issue.json()["status"] == "ISSUED"

    # Inventory quantity decremented from 20 to 15
    item = InventoryItem.objects.get(id=item_id)
    assert item.quantity == 15


def test_feedback_lifecycle(stub_iam, cse_dept):
    # Student submits feedback
    stu_c = _client(
        stub_iam,
        user_id=501,
        modules=("dept",),
        permissions=("dept.feedback.create", "dept.feedback.view"),
        roles=("student",),
    )
    res_sub = stu_c.post(
        "/api/v1/dept/feedback/?department=CSE",
        {
            "category": "INFRASTRUCTURE",
            "title": "Projector Issue",
            "description": "Lab 1 projector flickering",
        },
        format="json",
    )
    assert res_sub.status_code == 201
    fb_id = res_sub.json()["id"]
    assert res_sub.json()["status"] == "NEW"

    # Admin reviews
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.feedback.review", "dept.feedback.resolve", "dept.feedback.view"),
        roles=("Dept_Admin",),
    )
    res_rev = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/review/?department=CSE",
        {"admin_remarks": "Technician scheduled"},
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "UNDER_REVIEW"

    # Admin resolves
    res_res = admin_c.post(
        f"/api/v1/dept/feedback/{fb_id}/resolve/?department=CSE",
        {"action": "RESOLVE", "remarks": "Replaced HDMI cable"},
        format="json",
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_timetable_conflict_rejected(stub_iam, cse_dept):
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.timetable.view", "dept.timetable.manage"),
        roles=("Dept_Admin",),
    )

    # Create slot 1 (Monday 9:00 - 10:00, Room 101, Prof X)
    res1 = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "B.Tech CSE",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "course_code": "CS101",
            "course_name": "Intro to CS",
            "instructor_id": "prof_x",
            "room_or_lab": "Room 101",
        },
        format="json",
    )
    assert res1.status_code == 201

    # Overlapping slot in same room (09:30 - 10:30, Room 101) -> 409 Conflict
    res2 = admin_c.post(
        "/api/v1/dept/timetables/?department=CSE",
        {
            "program": "B.Tech CSE",
            "academic_year": 2026,
            "semester": 1,
            "day_of_week": 0,
            "start_time": "09:30:00",
            "end_time": "10:30:00",
            "course_code": "CS102",
            "course_name": "Data Structures",
            "instructor_id": "prof_y",
            "room_or_lab": "Room 101",
        },
        format="json",
    )
    assert res2.status_code == 409


def test_announcements_patch_and_delete(stub_iam, cse_dept):
    c = _client(
        stub_iam,
        user_id=101,
        modules=("dept",),
        permissions=(
            "dept.announcement.view",
            "dept.announcement.create",
            "dept.announcement.manage",
        ),
        roles=("HOD",),
    )
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Initial", "content": "Content", "target_role": "ALL"},
        format="json",
    )
    assert res.status_code == 201
    ann_id = res.json()["id"]

    # Patch
    res_patch = c.patch(
        f"/api/v1/dept/announcements/{ann_id}/?department=CSE",
        {"title": "Updated Title"},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "Updated Title"

    # Delete (soft delete)
    res_del = c.delete(f"/api/v1/dept/announcements/{ann_id}/?department=CSE")
    assert res_del.status_code == 204


def test_inventory_add_stock_and_transactions(stub_iam, cse_dept):
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.inventory.view", "dept.inventory.create"),
        roles=("Dept_Admin",),
    )
    res_item = admin_c.post(
        "/api/v1/dept/inventory/?department=CSE",
        {"item_code": "CHAIR-01", "name": "Office Chair", "initial_quantity": 5},
        format="json",
    )
    assert res_item.status_code == 201
    item_id = res_item.json()["id"]

    # Add stock
    res_add = admin_c.post(
        f"/api/v1/dept/inventory/{item_id}/add-stock/?department=CSE",
        {"quantity": 10, "notes": "New delivery"},
        format="json",
    )
    assert res_add.status_code == 200
    assert res_add.json()["quantity"] == 15

    # List transactions
    res_tx = admin_c.get(f"/api/v1/dept/inventory/{item_id}/transactions/?department=CSE")
    assert res_tx.status_code == 200
    txs = res_tx.json()
    assert len(txs) >= 2


def test_labs_lifecycle(stub_iam, cse_dept):
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.lab_resource.view", "dept.lab_resource.manage"),
        roles=("Dept_Admin",),
    )
    res_lab = admin_c.post(
        "/api/v1/dept/labs/?department=CSE",
        {
            "lab_name": "AI Lab",
            "location": "Room 303",
            "description": "High performance GPUs",
            "in_charge_id": "prof_ai",
        },
        format="json",
    )
    assert res_lab.status_code == 201
    lab_id = res_lab.json()["id"]

    # Patch lab
    res_patch = admin_c.patch(
        f"/api/v1/dept/labs/{lab_id}/?department=CSE",
        {"lab_name": "AI & Robotics Lab", "location": "Room 303"},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["lab_name"] == "AI & Robotics Lab"


def test_profiles_and_privacy_masking(stub_iam, cse_dept):
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.profile.view", "dept.profile.manage"),
        roles=("Dept_Admin",),
    )
    res_prof = admin_c.post(
        "/api/v1/dept/profiles/?department=CSE",
        {
            "user_id": "stud_101",
            "profile_type": "STUDENT",
            "contact_phone": "+91-9876543210",
            "emergency_contact": "Parent: 9876543211",
            "batch_or_roll": "2024CS01",
        },
        format="json",
    )
    assert res_prof.status_code == 201

    # Student viewing profiles (contacts must be masked)
    stu_c = _client(
        stub_iam,
        user_id=501,
        modules=("dept",),
        permissions=("dept.profile.view",),
        roles=("student",),
    )
    res_list = stu_c.get("/api/v1/dept/profiles/?department=CSE")
    assert res_list.status_code == 200
    profiles = res_list.json()
    stud_prof = next(p for p in profiles if p["user_id"] == "stud_101")
    assert stud_prof["contact_phone"] is None
    assert stud_prof["emergency_contact"] is None


def test_department_details_and_official_change_flow(stub_iam, cse_dept):
    admin_c = _client(
        stub_iam,
        user_id=999,
        modules=("dept",),
        permissions=("dept.detail.view", "dept.detail.update"),
        roles=("Dept_Admin",),
    )

    # Get details
    res_det = admin_c.get("/api/v1/dept/details/?department=CSE")
    assert res_det.status_code == 200

    # Patch general description
    res_desc = admin_c.patch(
        "/api/v1/dept/details/?department=CSE",
        {"description": "Premier department for computing"},
        format="json",
    )
    assert res_desc.status_code == 200
    assert res_desc.json()["description"] == "Premier department for computing"

    # Propose official change
    res_prop = admin_c.post(
        "/api/v1/dept/details/propose-change/?department=CSE",
        {
            "field_name": "core_policies",
            "new_value": "Updated academic integrity policy",
            "justification": "Senate resolution 42",
        },
        format="json",
    )
    assert res_prop.status_code == 201
    change_id = res_prop.json()["id"]

    # HOD reviews and approves
    hod_c = _client(
        stub_iam,
        user_id=301,
        modules=("dept",),
        permissions=("dept.detail.view", "dept.detail.approve"),
        roles=("HOD",),
    )
    res_pending = hod_c.get("/api/v1/dept/details/pending-changes/?department=CSE")
    assert res_pending.status_code == 200
    ids = [c["id"] for c in res_pending.json()]
    assert change_id in ids

    res_dec = hod_c.post(
        f"/api/v1/dept/details/pending-changes/{change_id}/decision/?department=CSE",
        {"decision": "APPROVE", "reason": "Consistent with Senate decision"},
        format="json",
    )
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "APPROVED"

    # Verify department policies updated
    res_after = hod_c.get("/api/v1/dept/details/?department=CSE")
    assert res_after.json()["core_policies"] == "Updated academic integrity policy"


def test_role_governance_api(stub_iam, cse_dept):
    inst_admin = _client(
        stub_iam,
        user_id=1,
        modules=("dept",),
        permissions=("dept.role_assignment.view", "dept.role_assignment.manage"),
        roles=("Institute Admin",),
    )

    now = datetime.datetime.now(datetime.UTC)
    start_str = now.isoformat()
    end_str = (now + datetime.timedelta(days=365)).isoformat()

    # Assign HOD role
    res_assign = inst_admin.post(
        "/api/v1/dept/roles/?department=CSE",
        {
            "role_name": "HOD",
            "user_id": "prof_new_hod",
            "start_date": start_str,
            "end_date": end_str,
        },
        format="json",
    )
    assert res_assign.status_code == 201
    assign_id = res_assign.json()["id"]
    assert res_assign.json()["status"] == "ACTIVE"

    # Revoke role
    res_rev = inst_admin.post(
        f"/api/v1/dept/roles/{assign_id}/revoke/?department=CSE",
        format="json",
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "REVOKED"
