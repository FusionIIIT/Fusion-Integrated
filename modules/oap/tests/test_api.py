"""API Integration tests for Other Academic Procedures.

Tests workflow endpoints, serializers, and permission barriers.
"""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.oap.models.nodues import DepartmentType

pytestmark = pytest.mark.django_db

ALL_OAP_PERMS = (
    "oap.request.view_self",
    "oap.leave.create",
    "oap.leave.view_self",
    "oap.leave.recommend",
    "oap.leave.approve",
    "oap.bonafide.create",
    "oap.bonafide.view_self",
    "oap.bonafide.issue",
    "oap.nodues.view",
    "oap.nodues.initiate",
    "oap.nodues.signoff",
    "oap.nodues.finalize",
    "oap.branchchange.apply",
    "oap.branchchange.manage",
    "oap.branchchange.approve",
)


def _client(stub_iam, user_id=1001, permissions=None, modules=("oap",)):
    perms = permissions if permissions is not None else ALL_OAP_PERMS
    stub_iam(make_session(user_id=user_id, modules=modules, permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def test_unauthenticated_request_is_refused():
    c = APIClient()
    res = c.get("/api/v1/oap/leave/")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_module_grant_is_refused(stub_iam):
    c = _client(stub_iam, modules=())
    res = c.get("/api/v1/oap/leave/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_leave_api_workflow(stub_iam):
    c = _client(stub_iam)
    # 1. Apply for leave
    res = c.post(
        "/api/v1/oap/leave/",
        {
            "student_id": "24BCS205",
            "student_name": "Rahul Kumar",
            "leave_type": "CASUAL",
            "start_date": "2026-11-28",
            "end_date": "2026-11-30",
            "reason": "Personal work",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    leave_id = res.data["id"]

    # 2. Recommend action
    res_rec = c.post(
        f"/api/v1/oap/leave/{leave_id}/recommend/",
        {"supervisor_id": "FAC_01", "remarks": "Recommended"},
    )
    assert res_rec.status_code == status.HTTP_200_OK
    assert res_rec.data["status"] == "RECOMMENDED"

    # 3. HoD approve action
    res_approve = c.post(
        f"/api/v1/oap/leave/{leave_id}/hod_approve/",
        {"hod_id": "HOD_CSE", "remarks": "Approved by Head"},
    )
    assert res_approve.status_code == status.HTTP_200_OK
    assert res_approve.data["status"] == "APPROVED"


def test_leave_api_reject_and_cancel(stub_iam):
    c = _client(stub_iam)
    # Reject flow
    res = c.post(
        "/api/v1/oap/leave/",
        {
            "student_id": "24BCS205",
            "student_name": "Rahul Kumar",
            "leave_type": "CASUAL",
            "start_date": "2026-12-05",
            "end_date": "2026-12-06",
            "reason": "Short trip",
        },
    )
    leave_id = res.data["id"]
    res_rej = c.post(
        f"/api/v1/oap/leave/{leave_id}/hod_reject/",
        {"hod_id": "HOD_CSE", "remarks": "Rejected by HoD"},
    )
    assert res_rej.status_code == status.HTTP_200_OK
    assert res_rej.data["status"] == "REJECTED"

    # Cancel flow
    res2 = c.post(
        "/api/v1/oap/leave/",
        {
            "student_id": "24BCS205",
            "student_name": "Rahul Kumar",
            "leave_type": "CASUAL",
            "start_date": "2026-12-10",
            "end_date": "2026-12-11",
            "reason": "Cancel test",
        },
    )
    leave_id2 = res2.data["id"]
    res_cancel = c.post(
        f"/api/v1/oap/leave/{leave_id2}/cancel/",
        {"student_id": "24BCS205"},
    )
    assert res_cancel.status_code == status.HTTP_200_OK
    assert res_cancel.data["status"] == "CANCELLED"


def test_leave_permission_barrier(stub_iam):
    # Student cannot approve leave
    c = _client(stub_iam, permissions=("oap.leave.create", "oap.leave.view_self"))
    res = c.post(
        "/api/v1/oap/leave/",
        {
            "student_id": "24BCS205",
            "student_name": "Rahul Kumar",
            "leave_type": "CASUAL",
            "start_date": "2026-11-28",
            "end_date": "2026-11-30",
            "reason": "Personal work",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    leave_id = res.data["id"]

    res_approve = c.post(
        f"/api/v1/oap/leave/{leave_id}/hod_approve/",
        {"hod_id": "HOD_CSE", "remarks": "Approved by Head"},
    )
    assert res_approve.status_code == status.HTTP_403_FORBIDDEN


def test_bonafide_api_workflow(stub_iam):
    c = _client(stub_iam)
    # 1. Apply for bonafide
    res = c.post(
        "/api/v1/oap/bonafide/",
        {
            "student_id": "24BCS205",
            "purpose": "PASSPORT",
            "details": "Passport issuance verification",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    bona_id = res.data["id"]

    # 2. Download before approval should return 403 Forbidden
    res_dl_fail = c.get(f"/api/v1/oap/bonafide/{bona_id}/download/")
    assert res_dl_fail.status_code == status.HTTP_403_FORBIDDEN

    # 3. Approve and issue
    res_issue = c.post(
        f"/api/v1/oap/bonafide/{bona_id}/approve_and_issue/",
        {"issued_by": "ACAD_ADMIN", "remarks": "Approved and signed"},
    )
    assert res_issue.status_code == status.HTTP_200_OK
    assert res_issue.data["status"] == "APPROVED"

    # 4. Download after approval succeeds with 200
    res_dl = c.get(f"/api/v1/oap/bonafide/{bona_id}/download/")
    assert res_dl.status_code == status.HTTP_200_OK
    assert "download_url" in res_dl.data

    # 5. Reject bonafide
    res_apply2 = c.post(
        "/api/v1/oap/bonafide/",
        {"student_id": "24BCS205", "purpose": "VISA", "details": "Visa"},
    )
    bona_id2 = res_apply2.data["id"]
    res_rej = c.post(
        f"/api/v1/oap/bonafide/{bona_id2}/reject/",
        {"issued_by": "ACAD_ADMIN", "reason": "Insufficient evidence"},
    )
    assert res_rej.status_code == status.HTTP_200_OK
    assert res_rej.data["status"] == "REJECTED"


def test_no_dues_api_workflow(stub_iam):
    c = _client(stub_iam)
    # 1. Initiate no dues
    res = c.post(
        "/api/v1/oap/no-dues/",
        {"student_id": "24BCS205", "reason": "GRADUATION"},
    )
    assert res.status_code == status.HTTP_201_CREATED
    nd_id = res.data["id"]

    # 2. Department sign-offs
    for dept in DepartmentType.values:
        res_sign = c.post(
            f"/api/v1/oap/no-dues/{nd_id}/department_signoff/",
            {"department": dept, "status": "CLEARED", "signoff_by": "LIBRARIAN"},
        )
        assert res_sign.status_code == status.HTTP_200_OK

    # 3. Finalize
    res_fin = c.post(
        f"/api/v1/oap/no-dues/{nd_id}/finalize/",
        {"finalized_by": "ACAD_ADMIN"},
    )
    assert res_fin.status_code == status.HTTP_200_OK
    assert res_fin.data["cleared"] is True


def test_branch_change_api_workflow(stub_iam):
    c = _client(stub_iam)
    res = c.post(
        "/api/v1/oap/branch-change/",
        {
            "student_id": "24BCS205",
            "current_branch": "ECE",
            "preferred_branch_1": "CSE",
            "preferred_branch_2": "DSAI",
            "current_cpi": "9.20",
            "credits_completed": 40,
            "has_backlogs": False,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    bc_id = res.data["id"]

    # Verify eligibility endpoint
    res_v = c.post(f"/api/v1/oap/branch-change/{bc_id}/verify/")
    assert res_v.status_code == status.HTTP_200_OK
    assert res_v.data["eligible"] is True

    # Allocate endpoint
    res_alloc = c.post(
        f"/api/v1/oap/branch-change/{bc_id}/allocate/",
        {"allocated_branch": "CSE", "approved_by": "DEAN_ACAD"},
    )
    assert res_alloc.status_code == status.HTTP_200_OK
    assert res_alloc.data["status"] == "APPROVED"
