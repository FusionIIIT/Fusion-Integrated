"""Use Case spec tests: Inventory & Stock (TC-DEPT-008..TC-DEPT-012, TC-DEPT-038..TC-DEPT-039)."""

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


def _add_item(act, name: str = "Arduino Uno", quantity: int = 10, unit: str = "board") -> int:
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


def test_tc_dept_008_faculty_submit_valid_stock_request(world, act):
    """TC-DEPT-008 | UC-DEPT-004 Main Success Scenario"""
    item_id = _add_item(act, name="Raspberry Pi", quantity=10)

    resp = _request_stock(act, item_id, 4, purpose="Embedded systems lab")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["status"] == "pending_hod"

    req = StockRequest.objects.get(pk=body["id"])
    assert req.status == "pending_hod"
    assert req.quantity == 4
    assert req.requester_id == uid("faculty")

    admin_notifs = DepartmentNotification.objects.filter(
        topic="stock_request.created", recipient_user_id=uid("admin")
    )
    hod_notifs = DepartmentNotification.objects.filter(
        topic="stock_request.pending_hod", recipient_user_id=uid("hod")
    )
    assert admin_notifs.count() == 1
    assert hod_notifs.count() == 1


def test_tc_dept_009_reject_stock_request_exceeding_inventory(world, act):
    """TC-DEPT-009 | UC-DEPT-004 Alternative Flow: Current inventory is insufficient"""
    item_id = _add_item(act, name="FPGA Board", quantity=5)

    resp = _request_stock(act, item_id, 6)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "insufficient_stock"
    assert StockRequest.objects.count() == 0
    assert not DepartmentNotification.objects.filter(
        topic__in=("stock_request.pending_hod", "stock_request.created")
    ).exists()


def test_tc_dept_010_hod_approve_pending_stock_request(world, act):
    """TC-DEPT-010 | UC-DEPT-005 Main Success Scenario / Alternative Flow: Approved outcome"""
    item_id = _add_item(act, name="Logic Analyzer", quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]

    resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "approved"
    assert StockRequest.objects.get(pk=req_id).status == "approved"

    admin_approved = act("admin").get(f"{API}/stock-requests?status=approved")
    assert admin_approved.status_code == 200
    assert req_id in {r["id"] for r in admin_approved.json()["results"]}

    assert not DepartmentNotification.objects.filter(recipient_user_id=uid("faculty")).exists()


def test_tc_dept_011_hod_reject_pending_stock_request(world, act):
    """TC-DEPT-011 | UC-DEPT-005 Alternative Flow: Rejected outcome"""
    item_id = _add_item(act, name="Oscilloscope Probe", quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]

    resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide",
        {"approve": False, "reason": "Deferred to next semester"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "rejected"
    assert StockRequest.objects.get(pk=req_id).status == "rejected"

    admin_approved = act("admin").get(f"{API}/stock-requests?status=approved")
    assert req_id not in {r["id"] for r in admin_approved.json()["results"]}
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 409

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.rejected", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "rejected" in notifs.first().subject.lower()


def test_tc_dept_012_dept_admin_issue_approved_stock_request(world, act):
    """TC-DEPT-012 | UC-DEPT-006 Main Success Scenario"""
    item_id = _add_item(act, name="Stepper Motor", quantity=12)
    req_id = _request_stock(act, item_id, 4).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    resp = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "issued"
    assert StockRequest.objects.get(pk=req_id).status == "issued"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 8

    movement = StockMovement.objects.get(item_id=item_id, kind=StockMovement.ISSUE)
    assert movement.quantity == 4
    assert movement.stock_request_id == req_id
    with pytest.raises(TypeError):
        movement.quantity = 99
        movement.save()
    with pytest.raises(TypeError):
        movement.delete()

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.issued", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "issued" in notifs.first().subject.lower()


def test_tc_dept_038_dept_admin_insert_stock_receipt(world, act):
    """TC-DEPT-038 | UC-DEPT-019 Main Success Scenario"""
    created = act("admin").post(
        f"{API}/inventory-items",
        {"name": "Multimeter", "unit": "unit", "quantity": 10, "note": "Initial delivery"},
        format="json",
    )
    assert created.status_code == 201, created.content
    item_id = created.json()["id"]

    receipt = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts",
        {"quantity": 5, "note": "Restock batch"},
        format="json",
    )
    assert receipt.status_code == 201, receipt.content
    assert receipt.json()["current_quantity"] == 15

    movements = list(
        StockMovement.objects.filter(item_id=item_id, kind=StockMovement.RECEIPT).order_by("id")
    )
    assert [m.quantity for m in movements] == [10, 5]
    with pytest.raises(TypeError):
        movements[0].quantity = 99
        movements[0].save()
    with pytest.raises(TypeError):
        movements[0].delete()

    tracked = act("admin").get(f"{API}/inventory-items")
    assert tracked.status_code == 200
    by_id = {item["id"]: item for item in tracked.json()["results"]}
    assert by_id[item_id]["current_quantity"] == 15


def test_tc_dept_039_reject_invalid_stock_insertion_data(world, act):
    """TC-DEPT-039 | UC-DEPT-019 Alternative Flow: Invalid stock data"""
    item_id = _add_item(act, name="Soldering Iron", quantity=8)
    before_item_count = InventoryItem.objects.count()
    before_movement_count = StockMovement.objects.count()

    zero_qty = act("admin").post(
        f"{API}/inventory-items",
        {"name": "Bad Zero Item", "unit": "unit", "quantity": 0},
        format="json",
    )
    assert zero_qty.status_code in (400, 422)
    assert "error" in zero_qty.json()

    missing_name = act("admin").post(
        f"{API}/inventory-items",
        {"unit": "unit", "quantity": 5},
        format="json",
    )
    assert missing_name.status_code in (400, 422)
    assert "error" in missing_name.json()

    negative_receipt = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts",
        {"quantity": -3},
        format="json",
    )
    assert negative_receipt.status_code in (400, 422)
    assert "error" in negative_receipt.json()

    assert InventoryItem.objects.count() == before_item_count
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 8
    assert StockMovement.objects.count() == before_movement_count
