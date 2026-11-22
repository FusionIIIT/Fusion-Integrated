"""
API-Level Authorization & Permission Enforcement Tests for PSM.
Tests both permitted (200/201) and forbidden (403) operations for all 10 declared PSM permissions.
"""

from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.psm.models import (
    Indent,
    Vendor,
    PurchaseOrder,
    StockItem,
)

pytestmark = pytest.mark.django_db


def _as(stub_iam, uid=1001, perms=(), has_module=True):
    modules = ("psm",) if has_module else ()
    stub_iam(make_session(user_id=uid, kind="student", modules=modules, permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token valid-test-token")
    return client


def test_no_module_grant_returns_403(stub_iam):
    """Gate 1: User without module grant cannot enter PSM."""
    client = _as(stub_iam, uid=1001, perms=("psm.indent.view",), has_module=False)
    resp = client.get("/api/v1/psm/indents/")
    assert resp.status_code == 403
    assert resp.data["error"]["message"] == "This module is not available to your role."


def test_indent_view_permission(stub_iam):
    """Gate 2: psm.indent.view required to view indents."""
    ind = Indent.objects.create(
        indent_id="IND-PERM-001",
        requestor_id=1001,
        item_details="Monitor 27-inch",
        quantity=2,
        estimated_cost=Decimal("30000.00"),
        justification="Lab monitor",
        status="SUBMITTED",
    )

    # Denied without permission
    client_denied = _as(stub_iam, uid=1001, perms=())
    assert client_denied.get("/api/v1/psm/indents/").status_code == 403
    assert client_denied.get(f"/api/v1/psm/indents/{ind.id}/").status_code == 403
    assert client_denied.get(f"/api/v1/psm/indents/{ind.id}/versions/").status_code == 403

    # Permitted with permission
    client_allowed = _as(stub_iam, uid=1001, perms=("psm.indent.view",))
    resp = client_allowed.get("/api/v1/psm/indents/")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert client_allowed.get(f"/api/v1/psm/indents/{ind.id}/").status_code == 200
    assert client_allowed.get(f"/api/v1/psm/indents/{ind.id}/versions/").status_code == 200


def test_indent_create_permission(stub_iam):
    """Gate 2: psm.indent.create required to create indents."""
    payload = {
        "item_details": "Ergonomic Keyboards",
        "quantity": 5,
        "estimated_cost": "15000.00",
        "justification": "Ergonomics",
    }

    client_denied = _as(stub_iam, uid=1001, perms=("psm.indent.view",))
    assert client_denied.post("/api/v1/psm/indents/", payload, format="json").status_code == 403

    client_allowed = _as(stub_iam, uid=1001, perms=("psm.indent.create",))
    resp = client_allowed.post("/api/v1/psm/indents/", payload, format="json")
    assert resp.status_code == 201
    assert Indent.objects.filter(item_details="Ergonomic Keyboards").exists()


def test_indent_manage_permission(stub_iam):
    """Gate 2: psm.indent.manage required to transition indents."""
    ind = Indent.objects.create(
        indent_id="IND-PERM-002",
        requestor_id=1001,
        item_details="Server Rack",
        quantity=1,
        estimated_cost=Decimal("50000.00"),
        justification="Server room",
        status="SUBMITTED",
    )

    transition_payload = {"target_state": "STOCK_CHECKED"}

    # Standard user without manage permission cannot review or transition
    client_denied = _as(stub_iam, uid=1001, perms=("psm.indent.view", "psm.indent.create"))
    assert client_denied.post(f"/api/v1/psm/indents/{ind.id}/transition/", transition_payload, format="json").status_code == 403

    # Officer with psm.indent.manage can transition
    client_allowed = _as(stub_iam, uid=999, perms=("psm.indent.manage",))
    resp = client_allowed.post(f"/api/v1/psm/indents/{ind.id}/transition/", transition_payload, format="json")
    assert resp.status_code == 200
    ind.refresh_from_db()
    assert ind.status == "STOCK_CHECKED"


def test_indent_patch_manage_permission_and_rules(stub_iam):
    """Gate 2: PATCH /api/v1/psm/indents/{pk}/ requires psm.indent.manage and respects workflow rules."""
    ind = Indent.objects.create(
        indent_id="IND-PATCH-001",
        requestor_id=1001,
        item_details="Old Item Details",
        quantity=2,
        estimated_cost=Decimal("20000.00"),
        justification="Initial requirement",
        status="SUBMITTED",
    )

    patch_payload = {
        "item_details": "Updated Item Details",
        "quantity": 3,
        "estimated_cost": "30000.00",
    }

    # 1. Principal without psm.indent.manage receives 403 Forbidden
    client_no_manage = _as(stub_iam, uid=1001, perms=("psm.indent.view", "psm.indent.create"))
    resp_denied = client_no_manage.patch(f"/api/v1/psm/indents/{ind.id}/", patch_payload, format="json")
    assert resp_denied.status_code == 403
    ind.refresh_from_db()
    assert ind.item_details == "Old Item Details"

    # 2. Principal with psm.indent.manage is allowed to modify in SUBMITTED state
    client_manage = _as(stub_iam, uid=999, perms=("psm.indent.view", "psm.indent.manage"))
    resp_allowed = client_manage.patch(f"/api/v1/psm/indents/{ind.id}/", patch_payload, format="json")
    assert resp_allowed.status_code == 200
    ind.refresh_from_db()
    assert ind.item_details == "Updated Item Details"
    assert ind.quantity == 3
    assert ind.current_version == 2

    # 3. Business rule restriction (BR-PSM-007): Indent in non-modifiable state (APPROVED) cannot be modified
    ind.status = "APPROVED"
    ind.save()
    resp_rule_denied = client_manage.patch(f"/api/v1/psm/indents/{ind.id}/", {"quantity": 4}, format="json")
    assert resp_rule_denied.status_code == 400


def test_indent_withdraw_permissions_and_ownership(stub_iam):
    """Gate 2: POST /api/v1/psm/indents/{pk}/withdraw/ requires psm.indent.create/manage and enforces ownership."""
    # Indent owned by user 1001 in SUBMITTED status
    ind_user1 = Indent.objects.create(
        indent_id="IND-WD-001",
        requestor_id=1001,
        item_details="Lab Kit",
        quantity=1,
        estimated_cost=Decimal("5000.00"),
        justification="Lab experiment",
        status="SUBMITTED",
    )
    # Indent owned by user 1001 in DRAFT status
    ind_draft = Indent.objects.create(
        indent_id="IND-WD-DRAFT",
        requestor_id=1001,
        item_details="Draft Hardware",
        quantity=2,
        estimated_cost=Decimal("8000.00"),
        justification="Draft requirement",
        status="DRAFT",
    )
    # Indent owned by user 2002 in SUBMITTED status
    ind_user2 = Indent.objects.create(
        indent_id="IND-WD-002",
        requestor_id=2002,
        item_details="Oscilloscope",
        quantity=1,
        estimated_cost=Decimal("40000.00"),
        justification="Lab testing",
        status="SUBMITTED",
    )
    # Indent owned by user 1001 in APPROVED status
    ind_approved = Indent.objects.create(
        indent_id="IND-WD-APPROVED",
        requestor_id=1001,
        item_details="Approved Components",
        quantity=1,
        estimated_cost=Decimal("12000.00"),
        justification="Approved project",
        status="APPROVED",
    )

    # 1. User with ONLY psm.indent.view receives 403 Forbidden (viewing does not grant withdrawal)
    client_view_only = _as(stub_iam, uid=1001, perms=("psm.indent.view",))
    assert client_view_only.post(f"/api/v1/psm/indents/{ind_user1.id}/withdraw/").status_code == 403

    # 2. Original requester (user 1001) can withdraw their own DRAFT and SUBMITTED indents
    client_owner = _as(stub_iam, uid=1001, perms=("psm.indent.view", "psm.indent.create"))
    resp_withdraw_sub = client_owner.post(f"/api/v1/psm/indents/{ind_user1.id}/withdraw/")
    assert resp_withdraw_sub.status_code == 200
    ind_user1.refresh_from_db()
    assert ind_user1.status == "WITHDRAWN"

    resp_withdraw_draft = client_owner.post(f"/api/v1/psm/indents/{ind_draft.id}/withdraw/")
    assert resp_withdraw_draft.status_code == 200
    ind_draft.refresh_from_db()
    assert ind_draft.status == "WITHDRAWN"

    # 3. User 1001 with psm.indent.create cannot withdraw user 2002's indent
    # 3a. Normal user 1001 receives 404 (out-of-scope; existence not leaked)
    assert client_owner.get(f"/api/v1/psm/indents/{ind_user2.id}/").status_code == 404
    assert client_owner.post(f"/api/v1/psm/indents/{ind_user2.id}/withdraw/").status_code == 404

    # 3b. User 1001 with psm.indent.view_all + create receives 400 (ownership check rejects)
    client_other_scoped = _as(stub_iam, uid=1001, perms=("psm.indent.view", "psm.indent.view_all", "psm.indent.create"))
    resp_other_withdraw = client_other_scoped.post(f"/api/v1/psm/indents/{ind_user2.id}/withdraw/")
    assert resp_other_withdraw.status_code == 400
    ind_user2.refresh_from_db()
    assert ind_user2.status == "SUBMITTED"

    # 4. Manager with psm.indent.manage (uid=999) is NOT blocked by queryset scoping and can access and withdraw user 2002's indent
    client_admin = _as(stub_iam, uid=999, perms=("psm.indent.view", "psm.indent.manage"))
    assert client_admin.get(f"/api/v1/psm/indents/{ind_user2.id}/").status_code == 200
    resp_admin_withdraw = client_admin.post(f"/api/v1/psm/indents/{ind_user2.id}/withdraw/")
    assert resp_admin_withdraw.status_code == 200
    ind_user2.refresh_from_db()
    assert ind_user2.status == "WITHDRAWN"

    # 5. APPROVED indent cannot be withdrawn by either requester or manager (state machine rule)
    resp_owner_app = client_owner.post(f"/api/v1/psm/indents/{ind_approved.id}/withdraw/")
    assert resp_owner_app.status_code == 400
    resp_admin_app = client_admin.post(f"/api/v1/psm/indents/{ind_approved.id}/withdraw/")
    assert resp_admin_app.status_code == 400
    ind_approved.refresh_from_db()
    assert ind_approved.status == "APPROVED"



def test_indent_view_all_scoping_permission(stub_iam):
    """Gate 2: psm.indent.view_all controls queryset scoping across users."""
    Indent.objects.create(
        indent_id="IND-USER-1",
        requestor_id=1001,
        item_details="User 1 Item",
        quantity=1,
        estimated_cost=Decimal("1000.00"),
        justification="Test",
        status="SUBMITTED",
    )
    Indent.objects.create(
        indent_id="IND-USER-2",
        requestor_id=2002,
        item_details="User 2 Item",
        quantity=1,
        estimated_cost=Decimal("2000.00"),
        justification="Test",
        status="SUBMITTED",
    )

    # User 1 without psm.indent.view_all sees only their own indent
    client_standard = _as(stub_iam, uid=1001, perms=("psm.indent.view",))
    resp_standard = client_standard.get("/api/v1/psm/indents/")
    assert resp_standard.status_code == 200
    assert len(resp_standard.data) == 1
    assert resp_standard.data[0]["indent_id"] == "IND-USER-1"

    # User 1 with psm.indent.view_all sees both indents
    client_admin = _as(stub_iam, uid=1001, perms=("psm.indent.view", "psm.indent.view_all"))
    resp_admin = client_admin.get("/api/v1/psm/indents/")
    assert resp_admin.status_code == 200
    assert len(resp_admin.data) == 2


def test_vendor_permissions(stub_iam):
    """Gate 2: psm.vendor.view vs psm.vendor.manage."""
    ven = Vendor.objects.create(
        name="Tech Solutions",
        gst_number="27ABCDE1234F1Z5",
        bank_account_number="1234567890",
        bank_ifsc="HDFC0001111",
        is_verified=False,
    )

    # 1. View permissions
    client_no_view = _as(stub_iam, uid=1001, perms=())
    assert client_no_view.get("/api/v1/psm/vendors/").status_code == 403
    assert client_no_view.get(f"/api/v1/psm/vendors/{ven.id}/").status_code == 403

    client_view = _as(stub_iam, uid=1001, perms=("psm.vendor.view",))
    assert client_view.get("/api/v1/psm/vendors/").status_code == 200
    assert client_view.get(f"/api/v1/psm/vendors/{ven.id}/").status_code == 200

    # 2. Manage permissions (Create and Verify)
    create_payload = {
        "name": "Office Supplies Corp",
        "gst_number": "07AAAAA0000A1Z5",
        "bank_account_number": "999888777",
        "bank_ifsc": "SBIN0001234",
    }
    assert client_view.post("/api/v1/psm/vendors/", create_payload, format="json").status_code == 403
    assert client_view.patch(f"/api/v1/psm/vendors/{ven.id}/", {"is_verified": True}, format="json").status_code == 403

    client_manage = _as(stub_iam, uid=999, perms=("psm.vendor.view", "psm.vendor.manage"))
    resp_create = client_manage.post("/api/v1/psm/vendors/", create_payload, format="json")
    assert resp_create.status_code == 201

    resp_verify = client_manage.patch(f"/api/v1/psm/vendors/{ven.id}/", {"is_verified": True}, format="json")
    assert resp_verify.status_code == 200
    ven.refresh_from_db()
    assert ven.is_verified is True


def test_purchase_order_and_grn_permissions(stub_iam):
    """Gate 2: psm.po.view vs psm.po.create."""
    ven = Vendor.objects.create(
        name="Hardware Hub",
        gst_number="29ABCDE1234F1Z8",
        bank_account_number="555666777",
        bank_ifsc="ICIC0002222",
        is_verified=True,
    )
    ind = Indent.objects.create(
        indent_id="IND-PO-001",
        requestor_id=1001,
        item_details="Laptops",
        quantity=3,
        estimated_cost=Decimal("150000.00"),
        justification="Laptops",
        status="APPROVED",
    )
    ind_for_create = Indent.objects.create(
        indent_id="IND-PO-CREATE-002",
        requestor_id=1001,
        item_details="Workstations",
        quantity=2,
        estimated_cost=Decimal("180000.00"),
        justification="Workstations",
        status="APPROVED",
    )
    po = PurchaseOrder.objects.create(
        po_number="PO-2026-0001",
        indent=ind,
        vendor=ven,
        procurement_method="DIRECT",
        total_cost=Decimal("150000.00"),
        delivery_schedule="2026-12-31",
        status="ISSUED",
    )

    # 1. PO View checks
    client_no_view = _as(stub_iam, uid=1001, perms=())
    assert client_no_view.get("/api/v1/psm/purchase-orders/").status_code == 403
    assert client_no_view.get("/api/v1/psm/grn/").status_code == 403

    client_view = _as(stub_iam, uid=1001, perms=("psm.po.view",))
    assert client_view.get("/api/v1/psm/purchase-orders/").status_code == 200
    assert client_view.get("/api/v1/psm/grn/").status_code == 200

    # 2. PO & GRN Create checks
    po_payload_denied = {
        "indent_id": ind_for_create.id,
        "vendor_id": ven.id,
        "procurement_method": "DIRECT",
        "total_cost": "180000.00",
        "delivery_schedule": "2026-12-31",
    }
    grn_payload_denied = {
        "purchase_order_id": po.id,
        "accepted_quantity": 3,
        "rejected_quantity": 0,
        "inspection_remarks": "Tested",
    }

    # Denied for client without psm.po.create
    assert client_view.post("/api/v1/psm/purchase-orders/", po_payload_denied, format="json").status_code == 403
    assert client_view.post("/api/v1/psm/grn/", grn_payload_denied, format="json").status_code == 403

    # Permitted for client with psm.po.create
    client_create = _as(stub_iam, uid=999, perms=("psm.po.view", "psm.po.create"))
    # Verify successful Purchase Order creation via API
    resp_po = client_create.post("/api/v1/psm/purchase-orders/", po_payload_denied, format="json")
    assert resp_po.status_code == 201
    assert PurchaseOrder.objects.filter(indent=ind_for_create).exists()

    # Verify successful GRN recording via API
    resp_grn = client_create.post("/api/v1/psm/grn/", grn_payload_denied, format="json")
    assert resp_grn.status_code == 201


def test_stock_permissions(stub_iam):
    """Gate 2: psm.stock.view vs psm.stock.manage."""
    item = StockItem.objects.create(
        item_code="STK-CABLE-01",
        name="Cat6 Ethernet Cable",
        department="CENTRAL_STORE",
        central_stock=200,
        department_stock=50,
        reserved_stock=0,
    )

    # 1. Stock view checks
    client_no_view = _as(stub_iam, uid=1001, perms=())
    assert client_no_view.get("/api/v1/psm/stock-items/").status_code == 403
    assert client_no_view.get("/api/v1/psm/transfers/").status_code == 403

    client_view = _as(stub_iam, uid=1001, perms=("psm.stock.view",))
    assert client_view.get("/api/v1/psm/stock-items/").status_code == 200
    assert client_view.get("/api/v1/psm/transfers/").status_code == 200

    # 2. Stock transfer manage checks
    transfer_payload = {
        "source_department": "CENTRAL_STORE",
        "destination_department": "CSE",
        "stock_item_id": item.id,
        "quantity": 10,
    }
    assert client_view.post("/api/v1/psm/transfers/", transfer_payload, format="json").status_code == 403

    client_manage = _as(stub_iam, uid=999, perms=("psm.stock.view", "psm.stock.manage"))
    resp_transfer = client_manage.post("/api/v1/psm/transfers/", transfer_payload, format="json")
    assert resp_transfer.status_code == 201
