"""Workflow spec tests: Role Reassignment & Access Transition (TC-WF-18..TC-WF-22)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.department.models import (
    Feedback,
    InventoryItem,
    OfficialChange,
    RoleTenure,
    StockRequest,
)
from modules.department.services import roles as role_service
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_wf_18_hod_reassignment_and_headship_sync_path(world, act):
    """TC-WF-18 | BW-DEPT-07 hod-reassignment-and-headship-sync path (CW-DEPT-04 steps 1A-2A)"""
    # Preconditions: pending stock request and pending official change to verify HOD access transfer.
    item_id = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Router", "quantity": 5}, format="json")
        .json()["id"]
    )
    stock_req_id = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 1}, format="json")
        .json()["id"]
    )
    change_id = (
        act("admin")
        .post(
            f"{API}/official-changes",
            {"field": "core_policies", "value": "Updated policy"},
            format="json",
        )
        .json()["id"]
    )

    assert act("student").get(f"{API}/departments/CSE").json()["headship"]["user_id"] == uid("hod")

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    # 1. Institute Admin records a valid time-bound HOD reassignment (UC-DEPT-020).
    assign_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": effective.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert assign_resp.status_code == 201, assign_resp.content
    incoming_id = assign_resp.json()["id"]
    assert RoleTenure.objects.get(pk=incoming_id).transition_applied_at is None

    # 2. The recorded HOD reassignment reaches its effective time and System applies it (UC-DEPT-022).
    applied = role_service.apply_transitions(now=now)
    assert applied == 1
    assert RoleTenure.objects.get(pk=incoming_id).transition_applied_at is not None

    active_hods = RoleTenure.objects.filter(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("next_hod")

    # Employee A's HOD access is immediately revoked.
    old_hod_stock = act("hod").post(
        f"{API}/stock-requests/{stock_req_id}/decide", {"approve": True}, format="json"
    )
    assert old_hod_stock.status_code in (403, 404)
    assert StockRequest.objects.get(pk=stock_req_id).status == "pending_hod"

    old_hod_change = act("hod").post(
        f"{API}/official-changes/{change_id}/decide", {"approve": True}, format="json"
    )
    assert old_hod_change.status_code in (403, 404)
    assert OfficialChange.objects.get(pk=change_id).status == "pending"

    # Employee B's HOD access is immediately granted.
    new_hod_stock = act("next_hod").post(
        f"{API}/stock-requests/{stock_req_id}/decide", {"approve": True}, format="json"
    )
    assert new_hod_stock.status_code == 200, new_hod_stock.content
    assert new_hod_stock.json()["status"] == "approved"

    new_hod_change = act("next_hod").post(
        f"{API}/official-changes/{change_id}/decide", {"approve": True}, format="json"
    )
    assert new_hod_change.status_code == 200, new_hod_change.content
    assert new_hod_change.json()["status"] == "approved"

    # Displayed department Headship is automatically synchronized to Employee B.
    dept_resp = act("student").get(f"{API}/departments/CSE")
    assert dept_resp.status_code == 200
    assert dept_resp.json()["headship"]["user_id"] == uid("next_hod")


def test_tc_wf_19_dept_admin_reassignment_and_access_transition_path(world, act):
    """TC-WF-19 | BW-DEPT-08 dept-admin-reassignment-and-access-transition path (CW-DEPT-04 steps 1B-2B)"""
    # Preconditions: approved stock request and new feedback to verify Dept_Admin access transfer.
    item_id = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Switch", "quantity": 10}, format="json")
        .json()["id"]
    )
    stock_req_id = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 2}, format="json")
        .json()["id"]
    )
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{stock_req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    fb_id = (
        act("student")
        .post(f"{API}/feedback", {"subject": "Lab PC", "body": "Needs reboot."}, format="json")
        .json()["id"]
    )

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    # 1. Institute Admin records a valid time-bound Dept_Admin reassignment (UC-DEPT-020).
    assign_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "dept_admin",
            "user_id": uid("faculty2"),
            "valid_from": effective.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert assign_resp.status_code == 201, assign_resp.content
    incoming_id = assign_resp.json()["id"]
    assert RoleTenure.objects.get(pk=incoming_id).transition_applied_at is None

    # 2. The recorded Dept_Admin reassignment reaches its effective time and System applies it (UC-DEPT-022).
    applied = role_service.apply_transitions(now=now)
    assert applied == 1
    assert RoleTenure.objects.get(pk=incoming_id).transition_applied_at is not None

    active_admins = RoleTenure.objects.filter(
        department=world["CSE"], role="dept_admin", valid_from__lte=now, valid_to__gt=now
    )
    assert active_admins.count() == 1
    assert active_admins.first().user_id == uid("faculty2")

    # Employee C's Dept_Admin access is immediately revoked.
    old_admin_issue = act("admin").post(f"{API}/stock-requests/{stock_req_id}/issue")
    assert old_admin_issue.status_code in (403, 404)
    assert StockRequest.objects.get(pk=stock_req_id).status == "approved"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10

    old_admin_review = act("admin").post(
        f"{API}/feedback/{fb_id}/review", {"category": "facilities"}, format="json"
    )
    assert old_admin_review.status_code in (403, 404)
    assert Feedback.objects.get(pk=fb_id).status == "new"

    # Employee D's Dept_Admin access is immediately granted.
    new_admin_client = act("faculty2", active_role="deptadmin_cse", also_holds=("deptadmin_cse",))
    new_admin_issue = new_admin_client.post(f"{API}/stock-requests/{stock_req_id}/issue")
    assert new_admin_issue.status_code == 200, new_admin_issue.content
    assert new_admin_issue.json()["status"] == "issued"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 8

    new_admin_review = new_admin_client.post(
        f"{API}/feedback/{fb_id}/review", {"category": "facilities"}, format="json"
    )
    assert new_admin_review.status_code == 200, new_admin_review.content
    assert new_admin_review.json()["status"] == "under_review"


def test_tc_wf_20_role_reassignment_unauthorized_actor_guard(world, act):
    """TC-WF-20 | CW-DEPT-04 step 1 unauthorized-role-assignment guard (BR-DEPT-021)"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()

    resp = act("hod").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": now.isoformat(),
            "valid_to": (now + timedelta(days=400)).isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 403
    assert RoleTenure.objects.count() == before_count

    active_hods = RoleTenure.objects.filter(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("hod")
    assert act("student").get(f"{API}/departments/CSE").json()["headship"]["user_id"] == uid("hod")


def test_tc_wf_21_role_reassignment_invalid_tenure_guard(world, act):
    """TC-WF-21 | CW-DEPT-04 step 1 invalid-tenure guard (BR-DEPT-022)"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()

    # End date earlier than start date.
    inverted = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": (now + timedelta(days=10)).isoformat(),
            "valid_to": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert inverted.status_code == 422

    # Missing tenure end date.
    missing_end = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": (now + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert missing_end.status_code in (400, 422)

    assert RoleTenure.objects.count() == before_count
    active_hods = RoleTenure.objects.filter(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("hod")


def test_tc_wf_22_role_reassignment_unique_active_role_guard(world, act):
    """TC-WF-22 | CW-DEPT-04 step 1 unique-active-role guard (BR-DEPT-023)"""
    start = timezone.now() - timedelta(seconds=10)
    end = start + timedelta(days=365)

    # Preconditions: Employee A (faculty) is active HOD and Employee C (admin) is active Dept_Admin for ME.
    hod_setup = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("faculty"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    admin_setup = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "dept_admin",
            "user_id": uid("admin"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert hod_setup.status_code == 201, hod_setup.content
    assert admin_setup.status_code == 201, admin_setup.content

    # 1. Attempt to add Employee B as a second concurrently active HOD without ending/replacing Employee A.
    concurrent_hod = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert concurrent_hod.status_code == 409
    assert concurrent_hod.json()["error"]["code"] == "tenure_overlap"

    # 2. Attempt to add Employee D as a second concurrently active Dept_Admin without ending/replacing Employee C.
    concurrent_admin = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "dept_admin",
            "user_id": uid("faculty2"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert concurrent_admin.status_code == 409
    assert concurrent_admin.json()["error"]["code"] == "tenure_overlap"

    now = timezone.now()
    active_hods = RoleTenure.objects.filter(
        department__code="ME", role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("faculty")

    active_admins = RoleTenure.objects.filter(
        department__code="ME", role="dept_admin", valid_from__lte=now, valid_to__gt=now
    )
    assert active_admins.count() == 1
    assert active_admins.first().user_id == uid("admin")
