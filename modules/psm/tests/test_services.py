"""Service-layer integration tests for PSM workflows."""
import datetime
from decimal import Decimal

import pytest

from modules.psm.domain.threshold_policy import ProcurementMethod
from modules.psm.domain.validators import ValidationError
from modules.psm.models.discrepancy import DiscrepancyStatus
from modules.psm.models.goods_receipt import GRNStatus
from modules.psm.models.indent import IndentPriority, IndentStatus
from modules.psm.models.inventory import StockItem
from modules.psm.models.item import ItemCategory, ItemMaster
from modules.psm.models.purchase_order import POStatus
from modules.psm.models.vendor import VendorStatus
from modules.psm.services.discrepancy_service import resolve_discrepancy
from modules.psm.services.grn_service import acknowledge_grn, create_grn
from modules.psm.services.indent_service import (
    cancel_indent,
    create_indent,
    review_dept_indent,
    review_director_indent,
    review_ps_indent,
    submit_indent,
)
from modules.psm.services.inventory_service import fulfill_internal_stock, reserve_stock
from modules.psm.services.po_service import create_purchase_order, issue_purchase_order
from modules.psm.services.vendor_service import register_vendor, verify_vendor

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_item():
    return ItemMaster.objects.create(
        item_code="ITM-SVC-01",
        name="Scientific Calculator",
        category=ItemCategory.EQUIPMENT,
    )


def test_indent_full_lifecycle(test_item):
    # 1. Create indent
    items_data = [
        {
            "item_master_id": test_item.id,
            "quantity_requested": 10,
            "estimated_unit_cost": "1500.00",
            "specifications": "Casio FX-991EX",
        }
    ]
    indent = create_indent(
        user_id=101,
        department_code="CSE",
        title="Lab Equipment",
        purpose="Required for lab exams",
        priority=IndentPriority.NORMAL,
        items_data=items_data,
    )
    assert indent.status == IndentStatus.DRAFT
    assert indent.estimated_total == Decimal("15000.00")

    # Only requestor can submit
    with pytest.raises(ValidationError, match="Only the indent creator"):
        submit_indent(indent.id, user_id=999)

    indent = submit_indent(indent.id, user_id=101)
    assert indent.status == IndentStatus.SUBMITTED

    # Department approval
    with pytest.raises(ValidationError, match="Rejection justification cannot be empty"):
        review_dept_indent(indent.id, user_id=201, action="REJECT", remarks="")

    indent = review_dept_indent(indent.id, user_id=201, action="APPROVE")
    assert indent.status == IndentStatus.PENDING_PS_REVIEW

    # PS Review (under 2.5L, standard approval)
    indent = review_ps_indent(indent.id, user_id=301, action="APPROVE")
    assert indent.status == IndentStatus.APPROVED


def test_high_value_indent_director_escalation(test_item):
    # Over 2.5L threshold
    items_data = [
        {
            "item_master_id": test_item.id,
            "quantity_requested": 100,
            "estimated_unit_cost": "3000.00",
            "specifications": "High precision",
        }
    ]
    indent = create_indent(
        user_id=101,
        department_code="MECH",
        title="Heavy Lab Rig",
        purpose="Research grant",
        priority=IndentPriority.HIGH,
        items_data=items_data,
    )
    assert indent.estimated_total == Decimal("300000.00")
    submit_indent(indent.id, user_id=101)
    review_dept_indent(indent.id, user_id=201, action="APPROVE")

    # PS Review escalates to Director
    indent = review_ps_indent(indent.id, user_id=301, action="APPROVE")
    assert indent.status == IndentStatus.PENDING_DIRECTOR_APPROVAL

    # Director approval
    indent = review_director_indent(indent.id, user_id=401, action="APPROVE")
    assert indent.status == IndentStatus.APPROVED


def test_indent_cancellation(test_item):
    items_data = [
        {
            "item_master_id": test_item.id,
            "quantity_requested": 2,
            "estimated_unit_cost": "500.00",
        }
    ]
    indent = create_indent(
        user_id=101,
        department_code="ECE",
        title="Cables",
        purpose="General",
        priority=IndentPriority.LOW,
        items_data=items_data,
    )
    with pytest.raises(ValidationError, match="Only the indent creator"):
        cancel_indent(indent.id, user_id=999)

    cancelled = cancel_indent(indent.id, user_id=101)
    assert cancelled.status == IndentStatus.CANCELLED


def test_vendor_service_and_po_issuance(test_item):
    # Invalid GSTIN validation
    with pytest.raises(ValidationError, match="15-character GSTIN"):
        register_vendor(
            name="Alpha Corp",
            gstin="SHORT",
            email="info@alpha.com",
            phone="9876543210",
        )

    # Register valid vendor
    vendor = register_vendor(
        name="Alpha Suppliers",
        gstin="29ABCDE1234F1Z5",
        email="orders@alpha.com",
        phone="9876543210",
    )
    assert vendor.status == VendorStatus.PENDING_VERIFICATION

    # Attempting PO creation with unverified vendor must fail
    items_data = [
        {
            "item_master_id": test_item.id,
            "quantity_requested": 5,
            "estimated_unit_cost": "2000.00",
        }
    ]
    indent = create_indent(
        user_id=101,
        department_code="CSE",
        title="Monitors",
        purpose="Lab setup",
        priority=IndentPriority.NORMAL,
        items_data=items_data,
    )
    submit_indent(indent.id, 101)
    review_dept_indent(indent.id, 201, "APPROVE")
    review_ps_indent(indent.id, 301, "APPROVE")

    with pytest.raises(ValidationError, match="Only VERIFIED vendors"):
        create_purchase_order(indent_id=indent.id, vendor_id=vendor.id)

    # Verify vendor
    vendor = verify_vendor(vendor.id, user_id=301)
    assert vendor.status == VendorStatus.VERIFIED

    # PO creation succeeds
    po = create_purchase_order(
        indent_id=indent.id,
        vendor_id=vendor.id,
        delivery_due_date=datetime.date.today() + datetime.timedelta(days=14),
        user_id=301,
    )
    assert po.status == POStatus.DRAFT
    assert po.procurement_method == ProcurementMethod.DIRECT
    assert po.lines.count() == 1

    # Issue PO
    po = issue_purchase_order(po.id, user_id=301)
    assert po.status == POStatus.ISSUED
    assert po.issued_at is not None


def test_grn_goods_receipt_and_acknowledgement(test_item):
    vendor = register_vendor(
        name="Beta Logistics",
        gstin="33ABCDE1234F1Z6",
        email="beta@logistics.com",
        phone="9876543211",
    )
    verify_vendor(vendor.id, user_id=301)

    items_data = [
        {
            "item_master_id": test_item.id,
            "quantity_requested": 10,
            "estimated_unit_cost": "100.00",
        }
    ]
    indent = create_indent(
        user_id=101,
        department_code="DES",
        title="Styluses",
        purpose="Design studio",
        priority=IndentPriority.NORMAL,
        items_data=items_data,
    )
    submit_indent(indent.id, 101)
    review_dept_indent(indent.id, 201, "APPROVE")
    review_ps_indent(indent.id, 301, "APPROVE")

    po = create_purchase_order(indent.id, vendor.id, user_id=301)
    issue_purchase_order(po.id, user_id=301)
    po_line = po.lines.first()

    # Create GRN with 10 accepted items
    grn_items = [
        {
            "po_line_item_id": po_line.id,
            "quantity_received": 10,
            "quantity_accepted": 10,
            "quantity_rejected": 0,
        }
    ]
    grn = create_grn(
        po_id=po.id,
        user_id=501,
        receipt_date=datetime.date.today(),
        challan_number="CH-1001",
        items_data=grn_items,
    )
    assert grn.status == GRNStatus.ACCEPTED

    # Indentor receipt acknowledgement
    with pytest.raises(ValidationError, match="Only the indent requestor"):
        acknowledge_grn(grn.id, user_id=999)

    grn = acknowledge_grn(grn.id, user_id=101)
    assert grn.indentor_acknowledged is True
    assert grn.status == GRNStatus.CLOSED


def test_grn_discrepancy_and_resolution(test_item):
    vendor = register_vendor(
        name="Gamma Traders",
        gstin="27ABCDE1234F1Z7",
        email="gamma@traders.com",
        phone="9876543212",
    )
    verify_vendor(vendor.id, user_id=301)

    indent = create_indent(
        user_id=101,
        department_code="PHY",
        title="Lenses",
        purpose="Optics lab",
        priority=IndentPriority.HIGH,
        items_data=[
            {
                "item_master_id": test_item.id,
                "quantity_requested": 10,
                "estimated_unit_cost": "500.00",
            }
        ],
    )
    submit_indent(indent.id, 101)
    review_dept_indent(indent.id, 201, "APPROVE")
    review_ps_indent(indent.id, 301, "APPROVE")

    po = create_purchase_order(indent.id, vendor.id, user_id=301)
    issue_purchase_order(po.id, user_id=301)
    po_line = po.lines.first()

    # Storekeeper reports 8 accepted, 2 rejected (damaged)
    grn = create_grn(
        po_id=po.id,
        user_id=501,
        receipt_date=datetime.date.today(),
        challan_number="CH-2002",
        items_data=[
            {
                "po_line_item_id": po_line.id,
                "quantity_received": 10,
                "quantity_accepted": 8,
                "quantity_rejected": 2,
                "rejection_remarks": "Cracked lenses",
            }
        ],
    )
    assert grn.status == GRNStatus.DISCREPANT
    assert hasattr(grn, "discrepancy_report")
    assert grn.discrepancy_report.status == DiscrepancyStatus.OPEN_HOLD_PAYMENT

    # Resolve discrepancy
    resolved = resolve_discrepancy(
        discrepancy_id=grn.discrepancy_report.id,
        user_id=301,
        resolution_summary="Vendor provided replacement units; verified ok.",
    )
    assert resolved.status == DiscrepancyStatus.RESOLVED


def test_inventory_reservation_and_internal_fulfillment(test_item):
    stock = StockItem.objects.create(
        item_master=test_item,
        quantity_on_hand=50,
        quantity_reserved=0,
    )

    # Reserve 20 units
    stock = reserve_stock(stock.id, quantity=20, user_id=501, reference_id="REF-01")
    assert stock.quantity_reserved == 20
    assert stock.available_quantity == 30

    # Reserving more than available fails
    with pytest.raises(ValidationError, match="Cannot reserve"):
        reserve_stock(stock.id, quantity=35, user_id=501)

    # Internal fulfillment
    indent = create_indent(
        user_id=101,
        department_code="CSE",
        title="Stock items",
        purpose="Immediate lab consumption",
        priority=IndentPriority.NORMAL,
        items_data=[
            {
                "item_master_id": test_item.id,
                "quantity_requested": 15,
                "estimated_unit_cost": "100.00",
            }
        ],
    )
    submit_indent(indent.id, 101)
    review_dept_indent(indent.id, 201, "APPROVE")
    review_ps_indent(indent.id, 301, "APPROVE")

    fulfilled_indent = fulfill_internal_stock(indent.id, user_id=501)
    assert fulfilled_indent.status == IndentStatus.FULFILLED

    stock.refresh_from_db()
    assert stock.quantity_on_hand == 35  # 50 - 15
