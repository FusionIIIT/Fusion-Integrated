"""Tests for PSM public contract surface (cross-module boundary)."""
from decimal import Decimal

import pytest

from modules.psm.contracts import get_indents, get_stock_levels, get_vendor_statuses
from modules.psm.models.indent import Indent, IndentStatus
from modules.psm.models.inventory import StockItem
from modules.psm.models.item import ItemCategory, ItemMaster
from modules.psm.models.vendor import Vendor, VendorStatus

pytestmark = pytest.mark.django_db


def test_get_indents_contract():
    # Empty sequence
    assert get_indents([]) == {}

    indent1 = Indent.objects.create(
        indent_number="IND-CONTRACT-1",
        user_id=101,
        department_code="CSE",
        title="Keyboards",
        purpose="Lab replacement",
        status=IndentStatus.SUBMITTED,
        estimated_total=Decimal("12000.00"),
    )
    indent2 = Indent.objects.create(
        indent_number="IND-CONTRACT-2",
        user_id=102,
        department_code="ECE",
        title="Oscilloscopes",
        purpose="VLSI lab",
        status=IndentStatus.APPROVED,
        estimated_total=Decimal("80000.00"),
    )

    results = get_indents([indent1.id, indent2.id, 99999])
    assert len(results) == 2
    assert results[indent1.id].indent_number == "IND-CONTRACT-1"
    assert results[indent1.id].status == IndentStatus.SUBMITTED
    assert results[indent1.id].estimated_total == Decimal("12000.00")
    assert results[indent2.id].status == IndentStatus.APPROVED


def test_get_stock_levels_contract():
    assert get_stock_levels([]) == {}

    item1 = ItemMaster.objects.create(
        item_code="STK-001",
        name="A4 Paper Rim",
        category=ItemCategory.CONSUMABLE,
    )
    item2 = ItemMaster.objects.create(
        item_code="STK-002",
        name="Whiteboard Marker",
        category=ItemCategory.CONSUMABLE,
    )
    StockItem.objects.create(item_master=item1, quantity_on_hand=100, quantity_reserved=20)
    StockItem.objects.create(item_master=item2, quantity_on_hand=50, quantity_reserved=0)

    results = get_stock_levels(["STK-001", "STK-002", "NONEXISTENT"])
    assert len(results) == 2
    assert results["STK-001"].quantity_on_hand == 100
    assert results["STK-001"].quantity_reserved == 20
    assert results["STK-001"].available_quantity == 80
    assert results["STK-002"].available_quantity == 50


def test_get_vendor_statuses_contract():
    assert get_vendor_statuses([]) == {}

    v1 = Vendor.objects.create(
        vendor_code="VND-C1",
        name="Verified Supplier",
        gstin="29ABCDE1234F1Z1",
        status=VendorStatus.VERIFIED,
    )
    v2 = Vendor.objects.create(
        vendor_code="VND-C2",
        name="Pending Supplier",
        gstin="29ABCDE1234F1Z2",
        status=VendorStatus.PENDING_VERIFICATION,
    )

    results = get_vendor_statuses([v1.id, v2.id, 88888])
    assert len(results) == 2
    assert results[v1.id].is_verified is True
    assert results[v2.id].is_verified is False
    assert results[v1.id].name == "Verified Supplier"
