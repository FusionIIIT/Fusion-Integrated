"""Business Rule spec tests: Inventory & Stock (TC-DEPT-BR-009..015, TC-DEPT-BR-028..031)."""

from __future__ import annotations

import pytest

from modules.department.models import InventoryItem, StockMovement, StockRequest

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


def test_tc_dept_br_009_permitted_faculty(world, act):
    """TC-DEPT-BR-009 | BR-DEPT-005 permitted-faculty"""
    item_id = _add_item(act, name="Arduino Uno", quantity=10)
    resp = _request_stock(act, item_id, 3, role="faculty")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["status"] == "pending_hod"
    req = StockRequest.objects.get(pk=body["id"])
    assert req.quantity == 3
    assert req.status == "pending_hod"


def test_tc_dept_br_010_prohibited_non_faculty(world, act):
    """TC-DEPT-BR-010 | BR-DEPT-005 prohibited-non-faculty"""
    item_id = _add_item(act, name="Sensor Kit", quantity=10)

    for role in ("student", "admin", "hod"):
        resp = _request_stock(act, item_id, 2, role=role)
        assert resp.status_code == 403

    assert StockRequest.objects.count() == 0


def test_tc_dept_br_011_permitted_hod_decision(world, act):
    """TC-DEPT-BR-011 | BR-DEPT-006 permitted-hod-decision"""
    item_id = _add_item(act, name="Multimeter", quantity=10)
    req_approve = _request_stock(act, item_id, 2).json()["id"]
    req_reject = _request_stock(act, item_id, 2).json()["id"]

    approve_resp = act("hod").post(
        f"{API}/stock-requests/{req_approve}/decide", {"approve": True}, format="json"
    )
    reject_resp = act("hod").post(
        f"{API}/stock-requests/{req_reject}/decide",
        {"approve": False, "reason": "Not needed this term"},
        format="json",
    )
    assert approve_resp.status_code == 200, approve_resp.content
    assert reject_resp.status_code == 200, reject_resp.content
    assert approve_resp.json()["status"] == "approved"
    assert reject_resp.json()["status"] == "rejected"
    assert StockRequest.objects.get(pk=req_approve).status == "approved"
    assert StockRequest.objects.get(pk=req_reject).status == "rejected"


def test_tc_dept_br_012_prohibited_non_hod_decision(world, act):
    """TC-DEPT-BR-012 | BR-DEPT-006 prohibited-non-hod-decision"""
    item_id = _add_item(act, name="Breadboard", quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]

    for role in ("admin", "faculty", "student"):
        for approve in (True, False):
            resp = act(role).post(
                f"{API}/stock-requests/{req_id}/decide", {"approve": approve}, format="json"
            )
            assert resp.status_code == 403

    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"


def test_tc_dept_br_013_permitted_approved_by_dept_admin(world, act):
    """TC-DEPT-BR-013 | BR-DEPT-007 permitted-approved-by-dept-admin"""
    item_id = _add_item(act, name="Logic Analyzer", quantity=10)
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
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 6


def test_tc_dept_br_014_prohibited_unapproved_request(world, act):
    """TC-DEPT-BR-014 | BR-DEPT-007 prohibited-unapproved-request"""
    item_id = _add_item(act, name="Power Supply", quantity=10)
    pending_id = _request_stock(act, item_id, 2).json()["id"]
    rejected_id = _request_stock(act, item_id, 2).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{rejected_id}/decide", {"approve": False}, format="json")
        .status_code
        == 200
    )

    assert act("admin").post(f"{API}/stock-requests/{pending_id}/issue").status_code == 409
    assert act("admin").post(f"{API}/stock-requests/{rejected_id}/issue").status_code == 409
    assert StockRequest.objects.get(pk=pending_id).status == "pending_hod"
    assert StockRequest.objects.get(pk=rejected_id).status == "rejected"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10


def test_tc_dept_br_015_prohibited_non_dept_admin(world, act):
    """TC-DEPT-BR-015 | BR-DEPT-007 prohibited-non-dept-admin"""
    item_id = _add_item(act, name="Stepper Motor", quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    for role in ("hod", "faculty", "student"):
        resp = act(role).post(f"{API}/stock-requests/{req_id}/issue")
        assert resp.status_code == 403

    assert StockRequest.objects.get(pk=req_id).status == "approved"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10


def test_tc_dept_br_028_sufficient_inventory_at_threshold(world, act):
    """TC-DEPT-BR-028 | BR-DEPT-015 sufficient-inventory-at-threshold"""
    item_id = _add_item(act, name="FPGA Board", quantity=5)
    resp = _request_stock(act, item_id, 5)
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == "pending_hod"
    assert StockRequest.objects.get(pk=resp.json()["id"]).status == "pending_hod"


def test_tc_dept_br_029_insufficient_inventory_above_threshold(world, act):
    """TC-DEPT-BR-029 | BR-DEPT-015 insufficient-inventory-above-threshold"""
    item_id = _add_item(act, name="FPGA Board", quantity=5)
    resp = _request_stock(act, item_id, 6)
    assert resp.status_code == 422
    assert StockRequest.objects.count() == 0


def test_tc_dept_br_030_log_created_on_insertion_and_issuance(world, act):
    """TC-DEPT-BR-030 | BR-DEPT-016 log-created-on-insertion-and-issuance"""
    item_id = _add_item(act, name="Soldering Iron", quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    before_count = StockMovement.objects.filter(item_id=item_id).count()

    receipt_resp = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts",
        {"quantity": 5, "note": "Restock"},
        format="json",
    )
    assert receipt_resp.status_code == 201, receipt_resp.content

    issue_resp = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert issue_resp.status_code == 200, issue_resp.content

    movements = list(StockMovement.objects.filter(item_id=item_id).order_by("id"))
    assert len(movements) == before_count + 2
    appended = movements[-2:]
    assert appended[0].kind == StockMovement.RECEIPT
    assert appended[0].quantity == 5
    assert appended[1].kind == StockMovement.ISSUE
    assert appended[1].quantity == 3
    assert appended[1].stock_request_id == req_id


def test_tc_dept_br_031_log_immutability_enforced(world, act):
    """TC-DEPT-BR-031 | BR-DEPT-016 log-immutability-enforced"""
    item_id = _add_item(act, name="Cable Tester", quantity=8)
    movement = StockMovement.objects.get(item_id=item_id, kind=StockMovement.RECEIPT)

    for role in ("admin", "hod"):
        assert act(role).patch(
            f"{API}/stock-movements", {"quantity": 99}, format="json"
        ).status_code in (403, 405)
        assert act(role).delete(f"{API}/stock-movements").status_code in (403, 405)
        assert (
            act(role)
            .patch(f"{API}/stock-movements/{movement.pk}", {"quantity": 99}, format="json")
            .status_code
            == 404
        )
        assert act(role).delete(f"{API}/stock-movements/{movement.pk}").status_code == 404

    with pytest.raises(TypeError):
        movement.quantity = 99
        movement.save()
    with pytest.raises(TypeError):
        movement.delete()
    with pytest.raises(TypeError):
        StockMovement.objects.filter(pk=movement.pk).update(quantity=99)
    with pytest.raises(TypeError):
        StockMovement.objects.filter(pk=movement.pk).delete()

    fresh = StockMovement.objects.get(pk=movement.pk)
    assert fresh.quantity == 8
    assert fresh.kind == StockMovement.RECEIPT
