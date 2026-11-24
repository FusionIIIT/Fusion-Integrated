"""Use Case spec tests: Department Details & Official Changes (TC-DEPT-020..022, 025..026)."""

from __future__ import annotations

import pytest

from modules.department.models import Department, OfficialChange

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_020_dept_admin_update_general_department_details(world, act):
    """TC-DEPT-020 | UC-DEPT-010 Main Success Scenario (General/non-official detail update)"""
    resp = act("admin").patch(
        f"{API}/departments/CSE",
        {
            "description": "Department of Computer Science and Engineering.",
            "contact_email": "cse@iiitdmj.ac.in",
            "office_location": "Core Lab Block, Room 201",
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    dept = Department.objects.get(code="CSE")
    assert dept.description == "Department of Computer Science and Engineering."
    assert dept.contact_email == "cse@iiitdmj.ac.in"
    assert dept.office_location == "Core Lab Block, Room 201"
    assert OfficialChange.objects.count() == 0


def test_tc_dept_021_dept_admin_propose_official_department_detail_change(world, act):
    """TC-DEPT-021 | UC-DEPT-010 Main Success Scenario (Official department detail proposal)"""
    original_name = Department.objects.get(code="CSE").name

    resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "School of Computer Science and Engineering"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == "pending"
    assert OfficialChange.objects.get(pk=resp.json()["id"]).status == "pending"

    assert Department.objects.get(code="CSE").name == original_name
    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["name"] == original_name


def test_tc_dept_022_reject_invalid_department_detail_updates(world, act):
    """TC-DEPT-022 | UC-DEPT-010 Alternative Flow: Validation failure"""
    before_email = Department.objects.get(code="CSE").contact_email

    bad_general = act("admin").patch(
        f"{API}/departments/CSE",
        {"contact_email": "not-a-valid-email"},
        format="json",
    )
    assert bad_general.status_code in (400, 422)
    assert "error" in bad_general.json()

    bad_official_blank = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "   "},
        format="json",
    )
    assert bad_official_blank.status_code == 422
    assert "error" in bad_official_blank.json()

    bad_official_field = act("admin").post(
        f"{API}/official-changes",
        {"field": "headship", "value": "3011"},
        format="json",
    )
    assert bad_official_field.status_code in (400, 422)

    assert Department.objects.get(code="CSE").contact_email == before_email
    assert OfficialChange.objects.count() == 0


def test_tc_dept_025_hod_approve_pending_official_detail_change(world, act):
    """TC-DEPT-025 | UC-DEPT-012 Main Success Scenario (Approved outcome)"""
    proposed = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Minimum 75% attendance is mandatory."},
        format="json",
    )
    assert proposed.status_code == 201
    change_id = proposed.json()["id"]

    resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": True},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "approved"
    assert OfficialChange.objects.get(pk=change_id).status == "approved"

    assert Department.objects.get(code="CSE").core_policies == "Minimum 75% attendance is mandatory."
    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["core_policies"] == "Minimum 75% attendance is mandatory."


def test_tc_dept_026_hod_reject_pending_official_detail_change(world, act):
    """TC-DEPT-026 | UC-DEPT-012 Alternative Flow: Rejected outcome"""
    original_name = Department.objects.get(code="CSE").name
    proposed = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "Proposed Renamed Department"},
        format="json",
    )
    assert proposed.status_code == 201
    change_id = proposed.json()["id"]

    resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": False, "reason": "Keep existing official name."},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "rejected"
    assert OfficialChange.objects.get(pk=change_id).status == "rejected"
    assert Department.objects.get(code="CSE").name == original_name
