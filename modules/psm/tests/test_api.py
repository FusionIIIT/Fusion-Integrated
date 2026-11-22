"""API integration and scoping tests for PSM endpoints."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.psm.models.indent import Indent, IndentPriority, IndentStatus
from modules.psm.models.item import ItemCategory, ItemMaster
from modules.psm.models.vendor import Vendor, VendorStatus

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-auth-token")
    return client


def test_unauthenticated_request_rejected():
    client = APIClient()
    resp = client.get("/api/v1/psm/indents")
    assert resp.status_code in (401, 403)


def test_indent_scoping_and_foreign_id_404(stub_iam):
    ItemMaster.objects.create(
        item_code="ITM-API-01",
        name="Keyboards",
        category=ItemCategory.EQUIPMENT,
    )

    # Indent for user 1001
    ind1 = Indent.objects.create(
        indent_number="IND-API-1001",
        user_id=1001,
        department_code="CSE",
        title="Keyboards CSE",
        purpose="Replacement",
        status=IndentStatus.DRAFT,
        estimated_total=Decimal("5000.00"),
    )
    # Indent for user 2002
    ind2 = Indent.objects.create(
        indent_number="IND-API-2002",
        user_id=2002,
        department_code="ECE",
        title="Keyboards ECE",
        purpose="Replacement",
        status=IndentStatus.DRAFT,
        estimated_total=Decimal("5000.00"),
    )

    client1001 = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("psm",),
        permissions=("psm.indent.view", "psm.indent.create"),
    )

    # User 1001 should only see ind1 in list
    resp = client1001.get("/api/v1/psm/indents")
    assert resp.status_code == 200
    indents = resp.json()
    assert len(indents) == 1
    assert indents[0]["id"] == ind1.id

    # User 1001 accessing foreign indent 2002 gets 404
    resp_foreign = client1001.get(f"/api/v1/psm/indents/{ind2.id}")
    assert resp_foreign.status_code == 404


def test_indent_create_and_submit_api(stub_iam):
    item = ItemMaster.objects.create(
        item_code="ITM-API-02",
        name="Mouse",
        category=ItemCategory.EQUIPMENT,
    )
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("psm",),
        permissions=("psm.indent.view", "psm.indent.create"),
    )

    # Create indent
    payload = {
        "department_code": "CSE",
        "title": "Optical Mice",
        "purpose": "Hardware lab",
        "priority": IndentPriority.NORMAL,
        "items": [
            {
                "item_master_id": item.id,
                "quantity_requested": 5,
                "estimated_unit_cost": "300.00",
                "specifications": "USB Wired",
            }
        ],
    }
    resp = client.post("/api/v1/psm/indents", payload, format="json")
    assert resp.status_code == 201
    created = resp.json()
    assert created["status"] == IndentStatus.DRAFT
    assert Decimal(created["estimated_total"]) == Decimal("1500.00")
    indent_id = created["id"]

    # Submit indent
    resp_submit = client.post(f"/api/v1/psm/indents/{indent_id}/submit")
    assert resp_submit.status_code == 200
    assert resp_submit.json()["status"] == IndentStatus.SUBMITTED


def test_vendor_list_and_verify_api(stub_iam):
    vendor = Vendor.objects.create(
        vendor_code="VND-API-01",
        name="API Tech Solutions",
        gstin="29ABCDE1234F1Z8",
        status=VendorStatus.PENDING_VERIFICATION,
    )
    client = _auth_client(
        stub_iam,
        user_id=3001,
        modules=("psm",),
        permissions=("psm.vendor.view", "psm.vendor.manage"),
    )

    # List vendors
    resp = client.get("/api/v1/psm/vendors")
    assert resp.status_code == 200
    vendors = resp.json()
    assert any(v["id"] == vendor.id for v in vendors)

    # Verify vendor
    resp_verify = client.post(f"/api/v1/psm/vendors/{vendor.id}/verify")
    assert resp_verify.status_code == 200
    assert resp_verify.json()["status"] == VendorStatus.VERIFIED


def test_items_catalog_api(stub_iam):
    ItemMaster.objects.create(
        item_code="ITM-CAT-01",
        name="Graph Paper",
        category=ItemCategory.CONSUMABLE,
    )
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("psm",),
        permissions=("psm.indent.view", "psm.indent.create"),
    )
    resp = client.get("/api/v1/psm/items")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["item_code"] == "ITM-CAT-01" for i in items)
