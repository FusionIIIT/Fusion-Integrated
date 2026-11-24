"""Functional Requirement spec tests: Department Details & Official Changes (TC-DEPT-072..TC-DEPT-078)."""

from __future__ import annotations

import pytest

from modules.department.models import Department, OfficialChange

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def test_tc_dept_072_dept_admin_update_general_department_information(world, act):
    """TC-DEPT-072 | AFR-DEPT-038 Dept_Admin update general department information"""
    resp = act("admin").patch(
        f"{API}/departments/CSE",
        {
            "description": "Department of Computer Science and Engineering.",
            "contact_email": "cse-office@iiitdmj.ac.in",
            "office_location": "Core Lab Block, 2nd Floor",
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    dept = Department.objects.get(code="CSE")
    assert dept.description == "Department of Computer Science and Engineering."
    assert dept.contact_email == "cse-office@iiitdmj.ac.in"
    assert dept.office_location == "Core Lab Block, 2nd Floor"


def test_tc_dept_073_non_dept_admin_general_info_update_denial(world, act):
    """TC-DEPT-073 | AFR-DEPT-038 non-Dept_Admin general info update denial"""
    original_desc = Department.objects.get(code="CSE").description
    for role in ("faculty", "student"):
        resp = act(role).patch(
            f"{API}/departments/CSE",
            {"description": f"Unauthorized update by {role}"},
            format="json",
        )
        assert resp.status_code == 403

    assert Department.objects.get(code="CSE").description == original_desc


def test_tc_dept_074_official_change_kept_pending_before_hod_approval(world, act):
    """TC-DEPT-074 | AFR-DEPT-039 official change kept pending before HOD approval"""
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


def test_tc_dept_075_reject_independent_headship_edit_via_official_detail_path(world, act):
    """TC-DEPT-075 | AFR-DEPT-039 reject independent Headship edit via official-detail path"""
    resp = act("admin").post(
        f"{API}/official-changes",
        {"field": "headship", "value": "3011"},
        format="json",
    )
    assert resp.status_code in (400, 422)
    assert OfficialChange.objects.count() == 0


def test_tc_dept_076_hod_approve_official_detail_change(world, act):
    """TC-DEPT-076 | AFR-DEPT-040 HOD approve official detail change"""
    proposed = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Minimum 75% attendance required."},
        format="json",
    )
    assert proposed.status_code == 201
    change_id = proposed.json()["id"]

    resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": True},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert OfficialChange.objects.get(pk=change_id).status == "approved"

    published = act("student").get(f"{API}/departments/CSE")
    assert published.status_code == 200
    assert published.json()["core_policies"] == "Minimum 75% attendance required."


def test_tc_dept_077_hod_reject_official_detail_change(world, act):
    """TC-DEPT-077 | AFR-DEPT-040 HOD reject official detail change"""
    original_name = Department.objects.get(code="CSE").name
    proposed = act("admin").post(
        f"{API}/official-changes",
        {"field": "name", "value": "Proposed New Name"},
        format="json",
    )
    assert proposed.status_code == 201
    change_id = proposed.json()["id"]

    resp = act("hod").post(
        f"{API}/official-changes/{change_id}/decide",
        {"approve": False, "reason": "Retain official institute naming."},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert OfficialChange.objects.get(pk=change_id).status == "rejected"
    assert Department.objects.get(code="CSE").name == original_name


def test_tc_dept_078_non_hod_official_change_decision_denial(world, act):
    """TC-DEPT-078 | AFR-DEPT-040 non-HOD official change decision denial"""
    proposed = act("admin").post(
        f"{API}/official-changes",
        {"field": "core_policies", "value": "Updated policy text."},
        format="json",
    )
    assert proposed.status_code == 201
    change_id = proposed.json()["id"]

    for role in ("admin", "faculty"):
        for approve in (True, False):
            resp = act(role).post(
                f"{API}/official-changes/{change_id}/decide",
                {"approve": approve},
                format="json",
            )
            assert resp.status_code == 403

    assert OfficialChange.objects.get(pk=change_id).status == "pending"
