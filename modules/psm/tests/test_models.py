"""Database model and constraint tests for PSM."""
import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from modules.psm.models.discrepancy import DiscrepancyReport, DiscrepancyStatus, DiscrepancyType
from modules.psm.models.goods_receipt import GoodsReceiptNote, GRNItem, GRNStatus
from modules.psm.models.indent import Indent, IndentItem, IndentStatus
from modules.psm.models.inventory import StockItem, StockLedger, StockTransactionType
from modules.psm.models.item import ItemCategory, ItemMaster
from modules.psm.models.purchase_order import POLineItem, POStatus, ProcurementMethod, PurchaseOrder
from modules.psm.models.vendor import Vendor, VendorStatus

pytestmark = pytest.mark.django_db


def test_model_string_representations():
    vendor = Vendor.objects.create(
        vendor_code="VEND-001",
        name="Global Tech",
        status=VendorStatus.VERIFIED,
    )
    assert "VEND-001 - Global Tech (VERIFIED)" in str(vendor)

    item = ItemMaster.objects.create(
        item_code="ITEM-001",
        name="Laser Printer",
        category=ItemCategory.EQUIPMENT,
    )
    assert "ITEM-001 - Laser Printer" in str(item)

    indent = Indent.objects.create(
        indent_number="IND-2026-0001",
        user_id=101,
        department_code="CSE",
        title="Lab Printers",
        purpose="Required for students",
        status=IndentStatus.DRAFT,
        estimated_total=Decimal("50000.00"),
    )
    assert "IND-2026-0001 - Lab Printers [DRAFT]" in str(indent)

    item_line = IndentItem.objects.create(
        indent=indent,
        item_master=item,
        quantity_requested=5,
        estimated_unit_cost=Decimal("10000.00"),
    )
    assert item_line.total_cost == Decimal("50000.00")

    po = PurchaseOrder.objects.create(
        po_number="PO-2026-0001",
        indent=indent,
        vendor=vendor,
        status=POStatus.ISSUED,
        procurement_method=ProcurementMethod.DIRECT,
        total_amount=Decimal("50000.00"),
    )
    assert "PO-2026-0001 -> Global Tech [ISSUED]" in str(po)

    po_line = POLineItem.objects.create(
        purchase_order=po,
        item_master=item,
        quantity_ordered=5,
        unit_price=Decimal("10000.00"),
    )
    assert po_line.total_cost == Decimal("50000.00")

    grn = GoodsReceiptNote.objects.create(
        grn_number="GRN-2026-0001",
        purchase_order=po,
        store_keeper_user_id=102,
        challan_number="CH-999",
        receipt_date=datetime.date.today(),
        status=GRNStatus.INSPECTION_PENDING,
    )
    assert "GRN-2026-0001 for PO-2026-0001 [INSPECTION_PENDING]" in str(grn)

    grn_item = GRNItem.objects.create(
        grn=grn,
        po_line_item=po_line,
        quantity_received=5,
        quantity_accepted=4,
        quantity_rejected=1,
    )
    assert grn_item.quantity_received == 5

    stock = StockItem.objects.create(
        item_master=item,
        quantity_on_hand=20,
        quantity_reserved=5,
    )
    assert "ITEM-001: OnHand=20, Res=5" in str(stock)
    assert stock.available_quantity == 15

    ledger = StockLedger.objects.create(
        stock_item=stock,
        transaction_type=StockTransactionType.RECEIPT_CREDIT,
        quantity=20,
        balance_after=20,
        recorded_by_user_id=102,
    )
    assert ledger.quantity == 20
    assert "ITEM-001 | RECEIPT_CREDIT | Qty=20" in str(ledger)

    discrepancy = DiscrepancyReport.objects.create(
        discrepancy_code="DISC-2026-0001",
        grn=grn,
        reported_by_user_id=102,
        discrepancy_type=DiscrepancyType.DAMAGED,
        status=DiscrepancyStatus.OPEN_HOLD_PAYMENT,
    )
    assert "DISC-2026-0001 (DAMAGED) [OPEN_HOLD_PAYMENT]" in str(discrepancy)


def test_database_constraints():
    item = ItemMaster.objects.create(
        item_code="ITEM-TEST",
        name="Test Item",
        category=ItemCategory.CONSUMABLE,
    )

    # Indent estimated total non-negative constraint
    with pytest.raises(IntegrityError), transaction.atomic():
        Indent.objects.create(
            indent_number="IND-ERR",
            user_id=1,
            department_code="CSE",
            title="Negative",
            purpose="Testing constraint",
            estimated_total=Decimal("-10.00"),
        )

    # Indent item quantity must be positive
    indent = Indent.objects.create(
        indent_number="IND-VALID",
        user_id=1,
        department_code="CSE",
        title="Valid Indent",
        purpose="Valid",
        estimated_total=Decimal("100.00"),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        IndentItem.objects.create(
            indent=indent,
            item_master=item,
            quantity_requested=0,
            estimated_unit_cost=Decimal("100.00"),
        )

    # Stock reserved must be <= on_hand
    with pytest.raises(IntegrityError), transaction.atomic():
        StockItem.objects.create(
            item_master=item,
            quantity_on_hand=5,
            quantity_reserved=10,
        )
