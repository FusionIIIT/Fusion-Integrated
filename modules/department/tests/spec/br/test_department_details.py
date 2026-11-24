"""Business Rule spec tests: Department Details & Official Changes (TC-DEPT-BR-022, 023, 026, 027)."""

from __future__ import annotations

import pytest

from modules.department.models import Department, OfficialChange
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_br_022_official_change_pending_until_hod_approval(world, act):
    """TC-DEPT-BR-022 | BR-DEPT-011 official-change-pending-until-hod-approval"""
    original_name = Department.objects.get(code="CSE").name

    resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "School of Computer Science"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == "pending"
    assert OfficialChange.objects.get(pk=resp.json()["id"]).status == "pending"

    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["name"] == original_name


def test_tc_dept_br_023_headship_identity_exclusion(world, act):
    """TC-DEPT-BR-023 | BR-DEPT-011 headship-identity-exclusion"""
    admin_attempt = act("admin").post(
        f"{API}/official-changes",
        {"field": "headship", "value": str(uid("next_hod"))},
        format="json",
    )
    assert admin_attempt.status_code in (400, 422)

    hod_attempt = act("hod").post(
        f"{API}/official-changes",
        {"field": "headship", "value": str(uid("next_hod"))},
        format="json",
    )
    assert hod_attempt.status_code in (400, 403, 422)

    assert OfficialChange.objects.count() == 0
    dept = act("student").get(f"{API}/departments/CSE")
    assert dept.status_code == 200
    assert dept.json()["headship"]["user_id"] == uid("hod")


def test_tc_dept_br_026_permitted_hod_decision(world, act):
    """TC-DEPT-BR-026 | BR-DEPT-013 permitted-hod-decision"""
    original_name = Department.objects.get(code="CSE").name

    policy_prop = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Updated core policy for lab attendance."},
        format="json",
    )
    name_prop = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "Rejected Department Name"},
        format="json",
    )
    assert policy_prop.status_code == 201
    assert name_prop.status_code == 201
    policy_id = policy_prop.json()["id"]
    name_id = name_prop.json()["id"]

    approve_resp = act("hod").post(
        f"{API}/official-changes/{policy_id}/decide", {"approve": True}, format="json"
    )
    reject_resp = act("hod").post(
        f"{API}/official-changes/{name_id}/decide",
        {"approve": False, "reason": "Keep official name."},
        format="json",
    )
    assert approve_resp.status_code == 200, approve_resp.content
    assert reject_resp.status_code == 200, reject_resp.content
    assert OfficialChange.objects.get(pk=policy_id).status == "approved"
    assert OfficialChange.objects.get(pk=name_id).status == "rejected"

    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["core_policies"] == "Updated core policy for lab attendance."
    assert published.json()["name"] == original_name


def test_tc_dept_br_027_prohibited_non_hod_decision(world, act):
    """TC-DEPT-BR-027 | BR-DEPT-013 prohibited-non-hod-decision"""
    original_policies = Department.objects.get(code="CSE").core_policies
    prop = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Pending policy update."},
        format="json",
    )
    assert prop.status_code == 201
    change_id = prop.json()["id"]

    for role in ("admin", "faculty", "student"):
        for approve in (True, False):
            resp = act(role).post(
                f"{API}/official-changes/{change_id}/decide",
                {"approve": approve},
                format="json",
            )
            assert resp.status_code == 403

    assert OfficialChange.objects.get(pk=change_id).status == "pending"
    assert Department.objects.get(code="CSE").core_policies == original_policies
