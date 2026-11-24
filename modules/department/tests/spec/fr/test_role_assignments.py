"""Functional Requirement spec tests: Role Assignments (TC-DEPT-079..TC-DEPT-089)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.department.models import InventoryItem, RoleTenure, StockRequest
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_079_central_authority_assign_hod_and_dept_admin_roles(world, act):
    """TC-DEPT-079 | AFR-DEPT-047 central authority assign HOD and Dept_Admin roles"""
    now = timezone.now()
    valid_from = now
    valid_to = now + timedelta(days=365)

    hod_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("faculty"),
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
        format="json",
    )
    admin_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "dept_admin",
            "user_id": uid("faculty2"),
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
        format="json",
    )
    assert hod_resp.status_code == 201, hod_resp.content
    assert admin_resp.status_code == 201, admin_resp.content
    assert RoleTenure.objects.filter(department__code="ME", role="hod", user_id=uid("faculty")).exists()
    assert RoleTenure.objects.filter(
        department__code="ME", role="dept_admin", user_id=uid("faculty2")
    ).exists()


def test_tc_dept_080_unauthorized_department_actor_role_assignment_denial(world, act):
    """TC-DEPT-080 | AFR-DEPT-047 unauthorized department actor role assignment denial"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()
    payload = {
        "department": "ME",
        "role": "hod",
        "user_id": uid("faculty"),
        "valid_from": now.isoformat(),
        "valid_to": (now + timedelta(days=365)).isoformat(),
    }

    for role in ("hod", "admin", "faculty", "student"):
        resp = act(role).post(f"{API}/role-assignments", payload, format="json")
        assert resp.status_code == 403

    assert RoleTenure.objects.count() == before_count


def test_tc_dept_081_time_bounded_role_validity_period_persisted(world, act):
    """TC-DEPT-081 | AFR-DEPT-048 time-bounded role validity period persisted"""
    start = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
    end = start + timedelta(days=180)

    resp = act("central").post(
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
    assert resp.status_code == 201, resp.content
    tenure = RoleTenure.objects.get(pk=resp.json()["id"])
    assert tenure.valid_from == start
    assert tenure.valid_to == end


def test_tc_dept_082_reject_missing_or_invalid_validity_period(world, act):
    """TC-DEPT-082 | AFR-DEPT-048 reject missing or invalid validity period"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()

    missing_bounds = act("central").post(
        f"{API}/role-assignments",
        {"department": "ME", "role": "hod", "user_id": uid("faculty")},
        format="json",
    )
    assert missing_bounds.status_code == 400

    inverted_bounds = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "dept_admin",
            "user_id": uid("faculty2"),
            "valid_from": (now + timedelta(days=10)).isoformat(),
            "valid_to": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert inverted_bounds.status_code == 422
    assert RoleTenure.objects.count() == before_count


def test_tc_dept_083_immediate_access_revocation_for_outgoing_role_holder(world, act):
    """TC-DEPT-083 | AFR-DEPT-049 immediate access revocation for outgoing role holder"""
    item_id = (
        act("admin")
        .post(
            f"{API}/inventory-items",
            {"name": "Cable Tester", "unit": "unit", "quantity": 5},
            format="json",
        )
        .json()["id"]
    )
    req_id = (
        act("faculty")
        .post(
            f"{API}/stock-requests",
            {"item": item_id, "quantity": 1, "purpose": "Testing"},
            format="json",
        )
        .json()["id"]
    )

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    assert (
        act("central")
        .post(
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
        .status_code
        == 201
    )
    assert (
        act("central")
        .post(
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
        .status_code
        == 201
    )

    # Outgoing HOD is immediately refused on HOD-only action; request stays pending.
    hod_resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert hod_resp.status_code in (403, 404)
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    # Outgoing Dept_Admin is immediately refused on Dept_Admin-only action; no item created.
    before_items = InventoryItem.objects.count()
    admin_resp = act("admin").post(
        f"{API}/inventory-items",
        {"name": "Unauthorized Item", "unit": "unit", "quantity": 3},
        format="json",
    )
    assert admin_resp.status_code in (403, 404, 422)
    assert InventoryItem.objects.count() == before_items


def test_tc_dept_084_immediate_access_grant_for_incoming_role_holder(world, act):
    """TC-DEPT-084 | AFR-DEPT-050 immediate access grant for incoming role holder"""
    item_id = (
        act("admin")
        .post(
            f"{API}/inventory-items",
            {"name": "Crimping Tool", "unit": "unit", "quantity": 5},
            format="json",
        )
        .json()["id"]
    )
    req_id = (
        act("faculty")
        .post(
            f"{API}/stock-requests",
            {"item": item_id, "quantity": 1, "purpose": "Lab wiring"},
            format="json",
        )
        .json()["id"]
    )

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    assert (
        act("central")
        .post(
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
        .status_code
        == 201
    )
    assert (
        act("central")
        .post(
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
        .status_code
        == 201
    )

    hod_resp = act("next_hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert hod_resp.status_code == 200
    assert hod_resp.json()["status"] == "approved"

    admin_resp = act(
        "faculty2", active_role="deptadmin_cse", also_holds=("deptadmin_cse",)
    ).post(
        f"{API}/inventory-items",
        {"name": "Patch Cable", "unit": "cable", "quantity": 10},
        format="json",
    )
    assert admin_resp.status_code == 201
    assert InventoryItem.objects.filter(name="Patch Cable").exists()


def test_tc_dept_085_prevent_multiple_concurrent_active_hods(world, act):
    """TC-DEPT-085 | AFR-DEPT-051 prevent multiple concurrent active HODs"""
    start = timezone.now() - timedelta(seconds=10)
    end = start + timedelta(days=365)

    first = act("central").post(
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
    assert first.status_code == 201

    second = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("faculty2"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert second.status_code == 409
    now = timezone.now()
    active_hods = RoleTenure.objects.filter(
        department__code="ME", role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("faculty")


def test_tc_dept_086_prevent_zero_active_hods(world, act):
    """TC-DEPT-086 | AFR-DEPT-051 prevent zero active HODs"""
    now = timezone.now()
    active_hod = RoleTenure.objects.get(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )

    shorten = act("central").patch(
        f"{API}/role-assignments/{active_hod.pk}",
        {"valid_to": (now + timedelta(days=10)).isoformat()},
        format="json",
    )
    assert shorten.status_code == 422

    end_now = act("central").patch(
        f"{API}/role-assignments/{active_hod.pk}",
        {"valid_to": (now - timedelta(seconds=1)).isoformat()},
        format="json",
    )
    assert end_now.status_code == 422

    assert (
        RoleTenure.objects.filter(
            department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
        ).count()
        == 1
    )


def test_tc_dept_087_prevent_multiple_concurrent_active_dept_admins(world, act):
    """TC-DEPT-087 | AFR-DEPT-052 prevent multiple concurrent active Dept_Admins"""
    start = timezone.now() - timedelta(seconds=10)
    end = start + timedelta(days=365)

    first = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "dept_admin",
            "user_id": uid("faculty"),
            "valid_from": start.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert first.status_code == 201

    second = act("central").post(
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
    assert second.status_code == 409
    now = timezone.now()
    active_admins = RoleTenure.objects.filter(
        department__code="ME", role="dept_admin", valid_from__lte=now, valid_to__gt=now
    )
    assert active_admins.count() == 1
    assert active_admins.first().user_id == uid("faculty")


def test_tc_dept_088_prevent_zero_active_dept_admins(world, act):
    """TC-DEPT-088 | AFR-DEPT-052 prevent zero active Dept_Admins"""
    now = timezone.now()
    active_admin = RoleTenure.objects.get(
        department=world["CSE"], role="dept_admin", valid_from__lte=now, valid_to__gt=now
    )

    shorten = act("central").patch(
        f"{API}/role-assignments/{active_admin.pk}",
        {"valid_to": (now + timedelta(days=10)).isoformat()},
        format="json",
    )
    assert shorten.status_code == 422

    end_now = act("central").patch(
        f"{API}/role-assignments/{active_admin.pk}",
        {"valid_to": (now - timedelta(seconds=1)).isoformat()},
        format="json",
    )
    assert end_now.status_code == 422

    assert (
        RoleTenure.objects.filter(
            department=world["CSE"], role="dept_admin", valid_from__lte=now, valid_to__gt=now
        ).count()
        == 1
    )


def test_tc_dept_089_displayed_headship_derived_from_active_hod_assignment(world, act):
    """TC-DEPT-089 | AFR-DEPT-053 displayed Headship derived from active HOD assignment"""
    before = act("student").get(f"{API}/departments/CSE")
    assert before.status_code == 200
    assert before.json()["headship"]["user_id"] == uid("hod")

    now = timezone.now()
    reassign = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": (now - timedelta(seconds=1)).isoformat(),
            "valid_to": (now + timedelta(days=400)).isoformat(),
        },
        format="json",
    )
    assert reassign.status_code == 201, reassign.content

    after = act("student").get(f"{API}/departments/CSE")
    assert after.status_code == 200
    assert after.json()["headship"]["user_id"] == uid("next_hod")
