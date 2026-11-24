"""Use Case spec tests: Role Assignments & Transitions (TC-DEPT-040..TC-DEPT-044)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import DatabaseError
from django.utils import timezone

from modules.department.models import DepartmentNotification, RoleTenure, StockRequest
from modules.department.services import notifications as notification_service
from modules.department.services import roles as role_service
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_040_central_admin_record_valid_role_assignment(world, act):
    """TC-DEPT-040 | UC-DEPT-020 Main Success Scenario"""
    start = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
    end = start + timedelta(days=365)

    hod_resp = act("central").post(
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
    admin_resp = act("central").post(
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
    assert hod_resp.status_code == 201, hod_resp.content
    assert admin_resp.status_code == 201, admin_resp.content

    hod_tenure = RoleTenure.objects.get(pk=hod_resp.json()["id"])
    assert hod_tenure.department.code == "ME"
    assert hod_tenure.role == "hod"
    assert hod_tenure.user_id == uid("faculty")
    assert hod_tenure.valid_from == start
    assert hod_tenure.valid_to == end

    admin_tenure = RoleTenure.objects.get(pk=admin_resp.json()["id"])
    assert admin_tenure.department.code == "ME"
    assert admin_tenure.role == "dept_admin"
    assert admin_tenure.user_id == uid("faculty2")
    assert admin_tenure.valid_from == start
    assert admin_tenure.valid_to == end


def test_tc_dept_041_block_role_assignment_violating_unique_active_role(world, act):
    """TC-DEPT-041 | UC-DEPT-020 Alternative Flow: Proposed assignment violates unique active-role cardinality"""
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
    assert first.status_code == 201, first.content

    concurrent = act("central").post(
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
    assert concurrent.status_code == 409
    assert concurrent.json()["error"]["code"] == "tenure_overlap"

    now = timezone.now()
    active_hods = RoleTenure.objects.filter(
        department__code="ME", role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active_hods.count() == 1
    assert active_hods.first().user_id == uid("faculty")


def test_tc_dept_042_effective_hod_reassignment_revokes_grants_and_syncs_headship(world, act):
    """TC-DEPT-042 | UC-DEPT-022 Main Success Scenario"""
    item_id = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Cable Tester", "quantity": 5}, format="json")
        .json()["id"]
    )
    req_id = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 1}, format="json")
        .json()["id"]
    )

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    reassigned = act("central").post(
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
    assert reassigned.status_code == 201, reassigned.content
    applied = role_service.apply_transitions(now=now)
    assert applied == 1

    # Outgoing HOD is immediately refused.
    outgoing_resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert outgoing_resp.status_code in (403, 404)
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    # Incoming HOD is immediately granted HOD access.
    incoming_resp = act("next_hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert incoming_resp.status_code == 200
    assert incoming_resp.json()["status"] == "approved"

    # Exactly one active HOD exists for CSE and transition was stamped.
    active = RoleTenure.objects.filter(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active.count() == 1
    assert active.first().user_id == uid("next_hod")
    assert active.first().transition_applied_at is not None

    # Displayed Headship is synchronized to incoming active HOD.
    dept_resp = act("student").get(f"{API}/departments/CSE")
    assert dept_resp.status_code == 200
    assert dept_resp.json()["headship"]["user_id"] == uid("next_hod")


def test_tc_dept_043_initial_role_assignment_with_no_outgoing_holder(world, act):
    """TC-DEPT-043 | UC-DEPT-022 Alternative Flow: Initial assignment with no outgoing holder"""
    assert not RoleTenure.objects.filter(department__code="ME", role="hod").exists()

    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=365)

    created = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "ME",
            "role": "hod",
            "user_id": uid("faculty"),
            "valid_from": effective.isoformat(),
            "valid_to": end.isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201, created.content

    applied = role_service.apply_transitions(now=now)
    assert applied == 1

    active = RoleTenure.objects.filter(
        department__code="ME", role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active.count() == 1
    assert active.first().user_id == uid("faculty")
    assert active.first().transition_applied_at is not None

    assert DepartmentNotification.objects.filter(
        topic="role.effective", recipient_user_id=uid("faculty")
    ).exists()

    # Incoming holder has HOD context for ME and Headship is synchronized.
    me_hod = act("faculty", active_role="HOD (ME)", also_holds=("HOD (ME)",))
    ctx_resp = me_hod.get(f"{API}/context")
    assert ctx_resp.status_code == 200
    assert ctx_resp.json() == {"role": "hod", "department": "ME"}

    dept_resp = me_hod.get(f"{API}/departments/ME")
    assert dept_resp.status_code == 200
    assert dept_resp.json()["headship"]["user_id"] == uid("faculty")


def test_tc_dept_044_transition_failure_never_authorizes_dual_or_inconsistent_holders(
    world, act, monkeypatch
):
    """TC-DEPT-044 | UC-DEPT-022 Exception Flow: Transition must not authorize role state violating BR-DEPT-022 or BR-DEPT-024"""
    now = timezone.now()
    effective = now - timedelta(seconds=1)
    end = now + timedelta(days=400)

    # Record a valid reassignment, then trigger a failure during UC-DEPT-022 apply_transitions.
    reassigned = act("central").post(
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
    assert reassigned.status_code == 201, reassigned.content
    incoming_id = reassigned.json()["id"]

    def _fail_notify(*args, **kwargs):
        raise DatabaseError("Simulated transition failure")

    monkeypatch.setattr(notification_service, "enqueue", _fail_notify)
    with pytest.raises(DatabaseError):
        role_service.apply_transitions(now=now)

    # The failed transition step rolled back cleanly without creating multiple active holders.
    assert RoleTenure.objects.get(pk=incoming_id).transition_applied_at is None
    active = RoleTenure.objects.filter(
        department=world["CSE"], role="hod", valid_from__lte=now, valid_to__gt=now
    )
    assert active.count() == 1

    # Outgoing and incoming holders do NOT simultaneously hold active HOD access.
    out_ctx = act("hod").get(f"{API}/context").json()
    in_ctx = act("next_hod").get(f"{API}/context").json()
    assert not (out_ctx["department"] == "CSE" and in_ctx["department"] == "CSE")
    assert out_ctx["department"] is None
    assert in_ctx == {"role": "hod", "department": "CSE"}
