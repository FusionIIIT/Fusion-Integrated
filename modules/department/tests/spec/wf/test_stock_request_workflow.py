"""Workflow spec tests: Stock Request Lifecycle (TC-WF-01..TC-WF-06)."""

from __future__ import annotations

import pytest

from modules.department.models import (
    DepartmentNotification,
    InventoryItem,
    StockMovement,
    StockRequest,
)
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _add_item(act, name: str = "Oscilloscope", quantity: int = 10, unit: str = "unit") -> int:
    resp = act("admin").post(
        f"{API}/inventory-items",
        {"name": name, "unit": unit, "quantity": quantity},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    return resp.json()["id"]


def _request_stock(act, item_id: int, quantity: int, role: str = "faculty", purpose: str = "Lab"):
    return act(role).post(
        f"{API}/stock-requests",
        {"item": item_id, "quantity": quantity, "purpose": purpose},
        format="json",
    )


def test_tc_wf_01_stock_request_approved_and_issued_path(world, act):
    """TC-WF-01 | BW-DEPT-01 approved-and-issued path (CW-DEPT-01 steps 1-2A-3)"""
    item_id = _add_item(act, name="Arduino Kit", quantity=10)
    assert StockRequest.objects.count() == 0

    # 1. Faculty submits a stock request for quantity 3 (UC-DEPT-004).
    submit_resp = _request_stock(act, item_id, 3, purpose="Embedded lab")
    assert submit_resp.status_code == 201, submit_resp.content
    req_id = submit_resp.json()["id"]
    assert submit_resp.json()["status"] == "pending_hod"
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    assert (
        DepartmentNotification.objects.filter(
            topic="stock_request.created", recipient_user_id=uid("admin")
        ).count()
        == 1
    )
    assert (
        DepartmentNotification.objects.filter(
            topic="stock_request.pending_hod", recipient_user_id=uid("hod")
        ).count()
        == 1
    )

    # 2. HOD approves the pending stock request (UC-DEPT-005).
    approve_resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert approve_resp.status_code == 200, approve_resp.content
    assert approve_resp.json()["status"] == "approved"
    assert StockRequest.objects.get(pk=req_id).status == "approved"

    # 3. Dept_Admin allocates and marks the approved stock request as Issued (UC-DEPT-006).
    issue_resp = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert issue_resp.status_code == 200, issue_resp.content
    assert issue_resp.json()["status"] == "issued"
    assert StockRequest.objects.get(pk=req_id).status == "issued"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 7

    movement = StockMovement.objects.get(item_id=item_id, kind=StockMovement.ISSUE)
    assert movement.quantity == 3
    assert movement.stock_request_id == req_id
    with pytest.raises(TypeError):
        movement.quantity = 99
        movement.save()
    with pytest.raises(TypeError):
        movement.delete()

    issued_notifs = DepartmentNotification.objects.filter(
        topic="stock_request.issued", recipient_user_id=uid("faculty")
    )
    assert issued_notifs.count() == 1
    assert "issued" in issued_notifs.first().subject.lower()

    history_resp = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert history_resp.status_code == 200
    issued_ids = {row["id"] for row in history_resp.json()["results"]}
    assert req_id in issued_ids


def test_tc_wf_02_stock_request_hod_rejected_path(world, act):
    """TC-WF-02 | BW-DEPT-02 hod-rejected path (CW-DEPT-01 steps 1-2B)"""
    item_id = _add_item(act, name="Logic Probe", quantity=10)
    assert StockRequest.objects.count() == 0

    # 1. Faculty submits a stock request for quantity 4 (UC-DEPT-004).
    submit_resp = _request_stock(act, item_id, 4, purpose="Circuit testing")
    assert submit_resp.status_code == 201, submit_resp.content
    req_id = submit_resp.json()["id"]
    assert submit_resp.json()["status"] == "pending_hod"
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    # 2. HOD rejects the pending stock request (UC-DEPT-005).
    reject_resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide",
        {"approve": False, "reason": "Insufficient budget"},
        format="json",
    )
    assert reject_resp.status_code == 200, reject_resp.content
    assert reject_resp.json()["status"] == "rejected"
    assert StockRequest.objects.get(pk=req_id).status == "rejected"

    rejected_notifs = DepartmentNotification.objects.filter(
        topic="stock_request.rejected", recipient_user_id=uid("faculty")
    )
    assert rejected_notifs.count() == 1
    assert "rejected" in rejected_notifs.first().subject.lower()

    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10
    assert not StockMovement.objects.filter(item_id=item_id, kind=StockMovement.ISSUE).exists()


def test_tc_wf_03_stock_request_insufficient_inventory_guard(world, act):
    """TC-WF-03 | CW-DEPT-01 step 1 insufficient-inventory guard (BR-DEPT-015)"""
    item_id = _add_item(act, name="FPGA Dev Kit", quantity=5)

    resp = _request_stock(act, item_id, 6, purpose="VLSI lab")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "insufficient_stock"

    assert StockRequest.objects.count() == 0
    assert not DepartmentNotification.objects.filter(
        topic="stock_request.pending_hod", recipient_user_id=uid("hod")
    ).exists()
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 5


def test_tc_wf_04_stock_request_unauthorized_requester_guard(world, act):
    """TC-WF-04 | CW-DEPT-01 step 1 unauthorized-requester guard (BR-DEPT-005)"""
    item_id = _add_item(act, name="Breadboard", quantity=10)

    resp = _request_stock(act, item_id, 1, role="student", purpose="Project")
    assert resp.status_code == 403
    assert StockRequest.objects.count() == 0


def test_tc_wf_05_stock_request_unauthorized_approver_guard(world, act):
    """TC-WF-05 | CW-DEPT-01 step 2 unauthorized-approver guard (BR-DEPT-006)"""
    item_id = _add_item(act, name="Power Supply", quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"

    resp = act("admin").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert resp.status_code == 403
    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"


def test_tc_wf_06_stock_request_unapproved_issuance_guard(world, act):
    """TC-WF-06 | CW-DEPT-01 step 3 unapproved-issuance guard (BR-DEPT-007)"""
    item_id = _add_item(act, name="Signal Generator", quantity=10)

    pending_id = _request_stock(act, item_id, 2, purpose="Pending request").json()["id"]
    rejected_id = _request_stock(act, item_id, 2, purpose="Rejected request").json()["id"]
    assert (
        act("hod")
        .post(
            f"{API}/stock-requests/{rejected_id}/decide",
            {"approve": False, "reason": "Not approved"},
            format="json",
        )
        .status_code
        == 200
    )

    # 1. Dept_Admin attempts to issue the stock request in Pending HOD Approval.
    pending_issue = act("admin").post(f"{API}/stock-requests/{pending_id}/issue")
    assert pending_issue.status_code == 409

    # 2. Dept_Admin attempts to issue the stock request in Rejected state.
    rejected_issue = act("admin").post(f"{API}/stock-requests/{rejected_id}/issue")
    assert rejected_issue.status_code == 409

    assert StockRequest.objects.get(pk=pending_id).status == "pending_hod"
    assert StockRequest.objects.get(pk=rejected_id).status == "rejected"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10
    assert not StockMovement.objects.filter(item_id=item_id, kind=StockMovement.ISSUE).exists()
