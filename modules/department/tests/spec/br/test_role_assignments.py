"""Business Rule spec tests: Role Assignments (TC-DEPT-BR-039..TC-DEPT-BR-045)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.department.models import InventoryItem, RoleTenure, StockRequest
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_br_039_permitted_central_admin_and_headship_sync(world, act):
    """TC-DEPT-BR-039 | BR-DEPT-021 permitted-central-admin-and-headship-sync"""
    now = timezone.now()
    valid_from = now - timedelta(seconds=1)
    valid_to = now + timedelta(days=400)

    hod_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
        format="json",
    )
    admin_resp = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "dept_admin",
            "user_id": uid("faculty2"),
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
        format="json",
    )
    assert hod_resp.status_code == 201, hod_resp.content
    assert admin_resp.status_code == 201, admin_resp.content

    dept_resp = act("student").get(f"{API}/departments/CSE")
    assert dept_resp.status_code == 200
    assert dept_resp.json()["headship"]["user_id"] == uid("next_hod")


def test_tc_dept_br_040_prohibited_non_central_actor(world, act):
    """TC-DEPT-BR-040 | BR-DEPT-021 prohibited-non-central-actor"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()
    before_hod = (
        RoleTenure.objects.get(
            department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
        ).user_id
    )
    before_admin = (
        RoleTenure.objects.get(
            department=world["CSE"], role="dept_admin", valid_from__lte=now, valid_to__gt=now
        ).user_id
    )

    for actor in ("hod", "admin", "faculty", "student"):
        for target_role in ("hod", "dept_admin"):
            resp = act(actor).post(
                f"{API}/role-assignments",
                {
                    "department": "CSE",
                    "role": target_role,
                    "user_id": uid("faculty2"),
                    "valid_from": now.isoformat(),
                    "valid_to": (now + timedelta(days=400)).isoformat(),
                },
                format="json",
            )
            assert resp.status_code == 403

    assert RoleTenure.objects.count() == before_count
    assert (
        RoleTenure.objects.get(
            department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
        ).user_id
        == before_hod
    )
    assert (
        RoleTenure.objects.get(
            department=world["CSE"], role="dept_admin", valid_from__lte=now, valid_to__gt=now
        ).user_id
        == before_admin
    )


def test_tc_dept_br_041_duplicate_active_role_blocked(world, act):
    """TC-DEPT-BR-041 | BR-DEPT-022 duplicate-active-role-blocked"""
    start = timezone.now() - timedelta(seconds=10)
    end = start + timedelta(days=365)

    for role in ("hod", "dept_admin"):
        first = act("central").post(
            f"{API}/role-assignments",
            {
                "department": "ME",
                "role": role,
                "user_id": uid("faculty"),
                "valid_from": start.isoformat(),
                "valid_to": end.isoformat(),
            },
            format="json",
        )
        assert first.status_code == 201, first.content

        duplicate = act("central").post(
            f"{API}/role-assignments",
            {
                "department": "ME",
                "role": role,
                "user_id": uid("faculty2"),
                "valid_from": start.isoformat(),
                "valid_to": end.isoformat(),
            },
            format="json",
        )
        assert duplicate.status_code == 409

        now = timezone.now()
        active = RoleTenure.objects.filter(
            department__code="ME", role=role, valid_from__lte=now, valid_to__gt=now
        )
        assert active.count() == 1
        assert active.first().user_id == uid("faculty")


def test_tc_dept_br_042_zero_active_role_blocked(world, act):
    """TC-DEPT-BR-042 | BR-DEPT-022 zero-active-role-blocked"""
    now = timezone.now()
    for role in ("hod", "dept_admin"):
        active = RoleTenure.objects.get(
            department=world["CSE"], role=role, valid_from__lte=now, valid_to__gt=now
        )

        end_early = act("central").patch(
            f"{API}/role-assignments/{active.pk}",
            {"valid_to": (now + timedelta(days=10)).isoformat()},
            format="json",
        )
        assert end_early.status_code == 422

        end_now = act("central").patch(
            f"{API}/role-assignments/{active.pk}",
            {"valid_to": (now - timedelta(seconds=1)).isoformat()},
            format="json",
        )
        assert end_now.status_code == 422

        delete_attempt = act("central").delete(f"{API}/role-assignments/{active.pk}")
        assert delete_attempt.status_code in (403, 405)

        assert (
            RoleTenure.objects.filter(
                department=world["CSE"], role=role, valid_from__lte=now, valid_to__gt=now
            ).count()
            == 1
        )


def test_tc_dept_br_043_valid_tenure_interval(world, act):
    """TC-DEPT-BR-043 | BR-DEPT-023 valid-tenure-interval"""
    start = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
    end = start + timedelta(days=180)

    for role, holder in (("hod", "faculty"), ("dept_admin", "faculty2")):
        resp = act("central").post(
            f"{API}/role-assignments",
            {
                "department": "ME",
                "role": role,
                "user_id": uid(holder),
                "valid_from": start.isoformat(),
                "valid_to": end.isoformat(),
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        tenure = RoleTenure.objects.get(pk=resp.json()["id"])
        assert tenure.valid_from == start
        assert tenure.valid_to == end


def test_tc_dept_br_044_missing_or_invalid_tenure_interval(world, act):
    """TC-DEPT-BR-044 | BR-DEPT-023 missing-or-invalid-tenure-interval"""
    now = timezone.now()
    before_count = RoleTenure.objects.count()

    missing = act("central").post(
        f"{API}/role-assignments",
        {"department": "ME", "role": "hod", "user_id": uid("faculty")},
        format="json",
    )
    assert missing.status_code in (400, 422)

    equal_bounds = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("faculty"),
            "valid_from": (now + timedelta(days=5)).isoformat(),
            "valid_to": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert equal_bounds.status_code == 422

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


def test_tc_dept_br_045_immediate_transition_revoke_and_grant(world, act):
    """TC-DEPT-BR-045 | BR-DEPT-024 immediate-transition-revoke-and-grant"""
    item_id = (
        act("admin")
        .post(
            f"{API}/inventory-items",
            {"name": "Network Switch", "unit": "unit", "quantity": 10},
            format="json",
        )
        .json()["id"]
    )
    req_id = (
        act("faculty")
        .post(
            f"{API}/stock-requests",
            {"item": item_id, "quantity": 2, "purpose": "Lab setup"},
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

    # Outgoing HOD is immediately denied; incoming HOD is immediately permitted.
    outgoing_hod = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert outgoing_hod.status_code in (403, 404)
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    incoming_hod = act("next_hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert incoming_hod.status_code == 200, incoming_hod.content
    assert incoming_hod.json()["status"] == "approved"

    # Outgoing Dept_Admin is immediately denied; incoming Dept_Admin is immediately permitted.
    outgoing_admin = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert outgoing_admin.status_code in (403, 404)
    assert StockRequest.objects.get(pk=req_id).status == "approved"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10

    incoming_admin = act(
        "faculty2", active_role="deptadmin_cse", also_holds=("deptadmin_cse",)
    ).post(f"{API}/stock-requests/{req_id}/issue")
    assert incoming_admin.status_code == 200, incoming_admin.content
    assert incoming_admin.json()["status"] == "issued"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 8
