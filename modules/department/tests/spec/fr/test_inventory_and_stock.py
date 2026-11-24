"""Functional Requirement spec tests: Inventory & Stock (TC-DEPT-014..TC-DEPT-037)."""

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


def _add_item(act, name: str = "Oscilloscope Probe", quantity: int = 10, unit: str = "unit") -> int:
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


def test_tc_dept_014_dept_admin_stock_insertion(world, act):
    """TC-DEPT-014 | AFR-DEPT-007 Dept_Admin stock insertion"""
    resp = act("admin").post(
        f"{API}/inventory-items",
        {"name": "Arduino Uno", "unit": "board", "quantity": 12},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    item = InventoryItem.objects.get(pk=resp.json()["id"])
    assert item.name == "Arduino Uno"
    assert item.current_quantity == 12


def test_tc_dept_015_non_dept_admin_stock_insertion_denial(world, act):
    """TC-DEPT-015 | AFR-DEPT-007 non-Dept_Admin stock insertion denial"""
    for role in ("faculty", "hod", "student"):
        resp = act(role).post(
            f"{API}/inventory-items",
            {"name": f"Item by {role}", "unit": "unit", "quantity": 5},
            format="json",
        )
        assert resp.status_code == 403
    assert InventoryItem.objects.count() == 0


def test_tc_dept_016_current_inventory_state_and_quantity(world, act):
    """TC-DEPT-016 | AFR-DEPT-008 current inventory state and quantity"""
    item_id = _add_item(act, name="Logic Analyzer", quantity=10)
    receipt = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts",
        {"quantity": 5},
        format="json",
    )
    assert receipt.status_code == 201
    assert receipt.json()["current_quantity"] == 15

    listed = act("admin").get(f"{API}/inventory-items")
    assert listed.status_code == 200
    items = {i["id"]: i for i in listed.json()["results"]}
    assert items[item_id]["current_quantity"] == 15


def test_tc_dept_017_stock_insertion_log_entry(world, act):
    """TC-DEPT-017 | AFR-DEPT-014 stock insertion log entry"""
    item_id = _add_item(act, name="Breadboard", quantity=20)
    resp = act("admin").get(f"{API}/stock-movements")
    assert resp.status_code == 200
    movements = resp.json()["results"]
    matching = [m for m in movements if m["item"] == item_id and m["kind"] == "receipt"]
    assert len(matching) == 1
    assert matching[0]["quantity"] == 20


def test_tc_dept_018_stock_insertion_log_immutability(world, act):
    """TC-DEPT-018 | AFR-DEPT-014 stock insertion log immutability"""
    item_id = _add_item(act, name="Multimeter", quantity=7)
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
    assert fresh.quantity == 7
    assert fresh.kind == StockMovement.RECEIPT


def test_tc_dept_019_faculty_stock_request_submission(world, act):
    """TC-DEPT-019 | AFR-DEPT-009 Faculty stock request submission"""
    item_id = _add_item(act, name="Raspberry Pi", quantity=10)
    resp = _request_stock(act, item_id, 3)
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == "pending_hod"
    req = StockRequest.objects.get(pk=resp.json()["id"])
    assert req.quantity == 3
    assert req.status == "pending_hod"


def test_tc_dept_020_non_faculty_stock_request_denial(world, act):
    """TC-DEPT-020 | AFR-DEPT-009 non-Faculty stock request denial"""
    item_id = _add_item(act, name="Sensor Kit", quantity=10)
    resp = _request_stock(act, item_id, 2, role="student")
    assert resp.status_code == 403
    assert StockRequest.objects.count() == 0


def test_tc_dept_021_valid_quantity_at_inventory_boundary(world, act):
    """TC-DEPT-021 | AFR-DEPT-010 valid quantity at inventory boundary"""
    item_id = _add_item(act, name="FPGA Board", quantity=5)
    resp = _request_stock(act, item_id, 5)
    assert resp.status_code == 201, resp.content
    assert resp.json()["status"] == "pending_hod"


def test_tc_dept_022_quantity_exceeding_current_inventory(world, act):
    """TC-DEPT-022 | AFR-DEPT-010 quantity exceeding current inventory"""
    item_id = _add_item(act, name="FPGA Board", quantity=5)
    resp = _request_stock(act, item_id, 6)
    assert resp.status_code == 422
    assert StockRequest.objects.count() == 0


def test_tc_dept_023_hod_approve_pending_request(world, act):
    """TC-DEPT-023 | AFR-DEPT-011 HOD approve pending request"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]

    resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert StockRequest.objects.get(pk=req_id).status == "approved"


def test_tc_dept_024_hod_reject_pending_request(world, act):
    """TC-DEPT-024 | AFR-DEPT-011 HOD reject pending request"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]

    resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide",
        {"approve": False, "reason": "Insufficient budget"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert StockRequest.objects.get(pk=req_id).status == "rejected"


def test_tc_dept_025_non_hod_decision_denial(world, act):
    """TC-DEPT-025 | AFR-DEPT-011 non-HOD decision denial"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]

    for role in ("admin", "faculty"):
        for approve in (True, False):
            resp = act(role).post(
                f"{API}/stock-requests/{req_id}/decide",
                {"approve": approve},
                format="json",
            )
            assert resp.status_code == 403

    assert StockRequest.objects.get(pk=req_id).status == "pending_hod"


def test_tc_dept_026_dept_admin_issue_hod_approved_request(world, act):
    """TC-DEPT-026 | AFR-DEPT-012 Dept_Admin issue HOD-approved request"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    resp = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert resp.status_code == 200
    assert resp.json()["status"] == "issued"
    assert StockRequest.objects.get(pk=req_id).status == "issued"


def test_tc_dept_027_block_issuance_without_hod_approval(world, act):
    """TC-DEPT-027 | AFR-DEPT-012 block issuance without HOD approval"""
    item_id = _add_item(act, quantity=10)
    pending_id = _request_stock(act, item_id, 2).json()["id"]
    rejected_id = _request_stock(act, item_id, 2).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{rejected_id}/decide", {"approve": False}, format="json")
        .status_code
        == 200
    )

    pending_resp = act("admin").post(f"{API}/stock-requests/{pending_id}/issue")
    rejected_resp = act("admin").post(f"{API}/stock-requests/{rejected_id}/issue")
    assert pending_resp.status_code == 409
    assert rejected_resp.status_code == 409

    assert StockRequest.objects.get(pk=pending_id).status == "pending_hod"
    assert StockRequest.objects.get(pk=rejected_id).status == "rejected"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10


def test_tc_dept_028_non_dept_admin_issuance_denial(world, act):
    """TC-DEPT-028 | AFR-DEPT-012 non-Dept_Admin issuance denial"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    for role in ("faculty", "hod"):
        resp = act(role).post(f"{API}/stock-requests/{req_id}/issue")
        assert resp.status_code == 403

    assert StockRequest.objects.get(pk=req_id).status == "approved"


def test_tc_dept_029_automatic_inventory_decrement_on_issuance(world, act):
    """TC-DEPT-029 | AFR-DEPT-013 automatic inventory decrement on issuance"""
    item_id = _add_item(act, name="Stepper Motor", quantity=12)
    req_id = _request_stock(act, item_id, 4).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )

    resp = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert resp.status_code == 200
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 8


def test_tc_dept_030_stock_issuance_log_entry(world, act):
    """TC-DEPT-030 | AFR-DEPT-015 stock issuance log entry"""
    item_id = _add_item(act, name="Power Supply", quantity=10)
    req_id = _request_stock(act, item_id, 3).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200

    resp = act("admin").get(f"{API}/stock-movements")
    assert resp.status_code == 200
    issue_entries = [
        m for m in resp.json()["results"] if m["item"] == item_id and m["kind"] == "issue"
    ]
    assert len(issue_entries) == 1
    assert issue_entries[0]["quantity"] == 3
    assert issue_entries[0]["stock_request"] == req_id


def test_tc_dept_031_stock_issuance_log_immutability(world, act):
    """TC-DEPT-031 | AFR-DEPT-015 stock issuance log immutability"""
    item_id = _add_item(act, name="Soldering Station", quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200
    movement = StockMovement.objects.get(item_id=item_id, kind=StockMovement.ISSUE)

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
    assert fresh.quantity == 2
    assert fresh.kind == StockMovement.ISSUE


def test_tc_dept_032_dept_admin_notification_on_new_stock_request(world, act):
    """TC-DEPT-032 | AFR-DEPT-041 Dept_Admin notification on new stock request"""
    item_id = _add_item(act, quantity=10)
    resp = _request_stock(act, item_id, 2)
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.created", recipient_user_id=uid("admin")
    )
    assert notifs.count() == 1
    assert str(req_id) in notifs.first().subject


def test_tc_dept_033_hod_notification_on_stock_request_requiring_authorization(world, act):
    """TC-DEPT-033 | AFR-DEPT-042 HOD notification on stock request requiring authorization"""
    item_id = _add_item(act, quantity=10)
    resp = _request_stock(act, item_id, 2)
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.pending_hod", recipient_user_id=uid("hod")
    )
    assert notifs.count() == 1
    assert str(req_id) in notifs.first().subject


def test_tc_dept_034_faculty_notification_on_issued_outcome(world, act):
    """TC-DEPT-034 | AFR-DEPT-043 Faculty notification on Issued outcome"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.issued", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "issued" in notifs.first().subject.lower()


def test_tc_dept_035_faculty_notification_on_rejected_outcome(world, act):
    """TC-DEPT-035 | AFR-DEPT-043 Faculty notification on Rejected outcome"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req_id}/decide", {"approve": False}, format="json")
        .status_code
        == 200
    )

    notifs = DepartmentNotification.objects.filter(
        topic="stock_request.rejected", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "rejected" in notifs.first().subject.lower()


def test_tc_dept_036_no_faculty_notification_on_intermediate_hod_approval(world, act):
    """TC-DEPT-036 | AFR-DEPT-043 no Faculty notification on intermediate HOD approval"""
    item_id = _add_item(act, quantity=10)
    req_id = _request_stock(act, item_id, 2).json()["id"]

    resp = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json"
    )
    assert resp.status_code == 200

    assert not DepartmentNotification.objects.filter(recipient_user_id=uid("faculty")).exists()


def test_tc_dept_037_faculty_view_relevant_issued_stock_history(world, act):
    """TC-DEPT-037 | AFR-DEPT-016 Faculty view relevant issued-stock history"""
    item_id = _add_item(act, quantity=20)
    fac_a_issued = _request_stock(act, item_id, 2, role="faculty").json()["id"]
    fac_b_issued = _request_stock(act, item_id, 3, role="faculty2").json()["id"]
    fac_a_pending = _request_stock(act, item_id, 1, role="faculty").json()["id"]

    for req_id in (fac_a_issued, fac_b_issued):
        assert (
            act("hod")
            .post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
            .status_code
            == 200
        )
        assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 200

    resp = act("faculty").get(f"{API}/stock-requests?status=issued")
    assert resp.status_code == 200
    returned_ids = {r["id"] for r in resp.json()["results"]}
    assert fac_a_issued in returned_ids
    assert fac_b_issued not in returned_ids
    assert fac_a_pending not in returned_ids
