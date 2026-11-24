"""Workflow spec tests: Department Details & Official Changes (TC-WF-13..TC-WF-17)."""

from __future__ import annotations

import pytest

from modules.department.models import Department, OfficialChange
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_wf_13_official_change_approved_path(world, act):
    """TC-WF-13 | BW-DEPT-05 official-change-approved path (CW-DEPT-03 steps 1-2A)"""
    cse = world["CSE"]
    cse.name = "Computer Science"
    cse.core_policies = "Policy v1"
    cse.save(update_fields=["name", "core_policies"])

    # 1. Dept_Admin proposes an official department-detail change updating Name (UC-DEPT-010).
    propose_resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "Computer Science and Engineering"},
        format="json",
    )
    assert propose_resp.status_code == 201, propose_resp.content
    change_id = propose_resp.json()["id"]
    assert propose_resp.json()["status"] == "pending"
    assert OfficialChange.objects.get(pk=change_id).status == "pending"

    assert Department.objects.get(code="CSE").name == "Computer Science"
    before_pub = act("student").get(f"{API}/departments/CSE")
    assert before_pub.status_code == 200
    assert before_pub.json()["name"] == "Computer Science"

    # 2. HOD approves the pending official change (UC-DEPT-012).
    approve_resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": True},
        format="json",
    )
    assert approve_resp.status_code == 200, approve_resp.content
    assert approve_resp.json()["status"] == "approved"
    assert OfficialChange.objects.get(pk=change_id).status == "approved"

    assert Department.objects.get(code="CSE").name == "Computer Science and Engineering"
    after_pub = act("student").get(f"{API}/departments/CSE")
    assert after_pub.status_code == 200
    assert after_pub.json()["name"] == "Computer Science and Engineering"


def test_tc_wf_14_official_change_rejected_path(world, act):
    """TC-WF-14 | BW-DEPT-06 official-change-rejected path (CW-DEPT-03 steps 1-2B)"""
    cse = world["CSE"]
    cse.core_policies = "Policy v1"
    cse.save(update_fields=["core_policies"])

    # 1. Dept_Admin proposes an official change updating Core Policies to Policy v2 (UC-DEPT-010).
    propose_resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Policy v2"},
        format="json",
    )
    assert propose_resp.status_code == 201, propose_resp.content
    change_id = propose_resp.json()["id"]
    assert propose_resp.json()["status"] == "pending"
    assert OfficialChange.objects.get(pk=change_id).status == "pending"

    # 2. HOD rejects the pending official change (UC-DEPT-012).
    reject_resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": False, "reason": "Retain Policy v1"},
        format="json",
    )
    assert reject_resp.status_code == 200, reject_resp.content
    assert reject_resp.json()["status"] == "rejected"
    assert OfficialChange.objects.get(pk=change_id).status == "rejected"

    assert Department.objects.get(code="CSE").core_policies == "Policy v1"
    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["core_policies"] == "Policy v1"


def test_tc_wf_15_general_detail_bypass_path(world, act):
    """TC-WF-15 | CW-DEPT-03 step 1 general-detail-bypass path (BR-DEPT-011)"""
    resp = act("admin").patch(
        f"{API}/departments/CSE",
        {
            "description": "Updated general CSE department description.",
            "office_location": "Academic Block B, Room 302",
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content

    dept = Department.objects.get(code="CSE")
    assert dept.description == "Updated general CSE department description."
    assert dept.office_location == "Academic Block B, Room 302"
    assert OfficialChange.objects.count() == 0

    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["description"] == "Updated general CSE department description."


def test_tc_wf_16_headship_exclusion_boundary(world, act):
    """TC-WF-16 | CW-DEPT-03 headship-exclusion boundary"""
    before_headship = act("student").get(f"{API}/departments/CSE").json()["headship"]
    assert before_headship["user_id"] == uid("hod")

    # Dept_Admin attempts to propose an official department-detail change for Headship (UC-DEPT-010).
    propose_resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "headship", "value": str(uid("next_hod"))},
        format="json",
    )
    assert propose_resp.status_code in (400, 422)

    assert OfficialChange.objects.count() == 0
    after_headship = act("student").get(f"{API}/departments/CSE").json()["headship"]
    assert after_headship["user_id"] == uid("hod")


def test_tc_wf_17_official_change_unauthorized_approver_guard(world, act):
    """TC-WF-17 | CW-DEPT-03 step 2 unauthorized-approver guard (BR-DEPT-013)"""
    cse = world["CSE"]
    cse.core_policies = "Policy v1"
    cse.save(update_fields=["core_policies"])

    propose_resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Policy v2"},
        format="json",
    )
    assert propose_resp.status_code == 201, propose_resp.content
    change_id = propose_resp.json()["id"]

    # Dept_Admin attempts to approve the pending official change (UC-DEPT-012).
    resp = act("admin").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": True},
        format="json",
    )
    assert resp.status_code == 403
    assert OfficialChange.objects.get(pk=change_id).status == "pending"
    assert Department.objects.get(code="CSE").core_policies == "Policy v1"
