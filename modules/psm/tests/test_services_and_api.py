"""
Django Integration & Workflow Tests for PSM Selectors, Services, Contracts, and API Views.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from django.test import TestCase
from rest_framework.test import APIClient

from modules.psm.models import (
    Indent,
    IndentVersion,
    Vendor,
    PurchaseOrder,
    GoodsReceiptNote,
    StockItem,
    StockTransfer,
)
from modules.psm.selectors.scoping import get_visible_indents_for_user
from modules.psm.selectors.indents import list_indents, get_indent_by_id, get_indent_version_history
from modules.psm.selectors.vendors import list_vendors, get_vendor_by_id
from modules.psm.selectors.stock import get_allocable_stock, list_stock_items
from modules.psm.services.indents import (
    create_indent,
    modify_indent,
    transition_indent,
    withdraw_indent,
)
from modules.psm.services.stock import reserve_stock, initiate_stock_transfer
from modules.psm.services.procurement import (
    create_vendor,
    verify_vendor,
    create_purchase_order,
    record_grn,
)
from modules.psm.contracts import get_indents, get_vendors, get_stock_items
from core.api.exceptions import BadRequestError as ValidationError, NotFoundError


def _make_principal(user_id=101, username="test_user", active_role="EMPLOYEE", is_admin=False):
    p = MagicMock()
    p.user_id = user_id
    p.id = user_id
    p.username = username
    p.active_role = "PS_ADMIN" if is_admin else active_role
    p.roles = (p.active_role,)
    p.is_superuser = is_admin
    p.has_module = lambda m: m == "psm"
    p.has_permission = lambda perm: is_admin
    return p


class PSMWorkflowTestCase(TestCase):
    def setUp(self):
        self.user1 = _make_principal(user_id=101, username="faculty_1")
        self.user2 = _make_principal(user_id=102, username="faculty_2")
        self.admin = _make_principal(user_id=999, username="store_admin", is_admin=True)

    def test_indent_lifecycle_and_versioning(self):
        # 1. Create indent
        indent = create_indent(
            principal=self.user1,
            item_details="High Performance Compute Workstation",
            quantity=2,
            estimated_cost=Decimal("180000.00"),
            justification="CAD and Simulation Laboratory Work",
            priority="HIGH",
        )
        self.assertEqual(indent.requestor_id, 101)
        self.assertEqual(indent.status, "SUBMITTED")
        self.assertEqual(indent.current_version, 1)
        self.assertEqual(indent.versions.count(), 1)

        # 2. Modify indent (in SUBMITTED status - BR-PSM-007)
        modified = modify_indent(
            principal=self.user1,
            indent_id=indent.id,
            quantity=3,
            estimated_cost=Decimal("270000.00"),
        )
        self.assertEqual(modified.quantity, 3)
        self.assertEqual(modified.current_version, 2)
        # Should now have 2 versions archived
        self.assertEqual(indent.versions.count(), 2)

        # 3. Transitions
        # STOCK_CHECKED
        t1 = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="STOCK_CHECKED",
        )
        self.assertEqual(t1.status, "STOCK_CHECKED")

        # Now in STOCK_CHECKED, modification must fail (BR-PSM-007)
        with self.assertRaises(ValidationError):
            modify_indent(
                principal=self.user1,
                indent_id=indent.id,
                quantity=4,
            )

        # DEPT_REVIEWED
        t2 = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="DEPT_REVIEWED",
        )
        self.assertEqual(t2.status, "DEPT_REVIEWED")

        # HEAD_RECOMMENDED
        t3 = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="HEAD_RECOMMENDED",
        )
        self.assertEqual(t3.status, "HEAD_RECOMMENDED")

        # AWAITING_FINAL_APPROVAL
        t4 = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="AWAITING_FINAL_APPROVAL",
        )
        self.assertEqual(t4.status, "AWAITING_FINAL_APPROVAL")

        # APPROVED
        t5 = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="APPROVED",
        )
        self.assertEqual(t5.status, "APPROVED")

    def test_indent_rejection_mandates_justification(self):
        indent = create_indent(
            principal=self.user1,
            item_details="Office Stationery",
            quantity=50,
            estimated_cost=Decimal("5000.00"),
            justification="Quarterly refill",
        )
        # Rejection without justification must fail (BR-PSM-005)
        with self.assertRaises(ValidationError):
            transition_indent(
                principal=self.admin,
                indent_id=indent.id,
                target_state="REJECTED",
                justification="",
            )

        # Rejection with justification succeeds
        rejected = transition_indent(
            principal=self.admin,
            indent_id=indent.id,
            target_state="REJECTED",
            justification="Sufficient stationery available in store room.",
        )
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.rejection_justification, "Sufficient stationery available in store room.")

    def test_scoping_isolation(self):
        # User 1 creates an indent
        ind1 = create_indent(
            principal=self.user1,
            item_details="Projector Bulb",
            quantity=1,
            estimated_cost=Decimal("8000.00"),
            justification="Classroom projector",
        )

        # User 2 creates an indent
        ind2 = create_indent(
            principal=self.user2,
            item_details="Whiteboard Markers",
            quantity=20,
            estimated_cost=Decimal("1200.00"),
            justification="Dept seminar room",
        )

        # User 1 should only see ind1
        user1_indents = list_indents(self.user1)
        self.assertIn(ind1, user1_indents)
        self.assertNotIn(ind2, user1_indents)

        # User 2 cannot access ind1 by id (returns None -> 404)
        out_of_scope = get_indent_by_id(self.user2, ind1.id)
        self.assertIsNone(out_of_scope)

        # Admin sees both
        admin_indents = list_indents(self.admin)
        self.assertIn(ind1, admin_indents)
        self.assertIn(ind2, admin_indents)

    def test_procurement_po_and_grn_workflow(self):
        # 1. Register vendor
        vendor = create_vendor(
            name="Apex Computers Ltd",
            gst_number="27AAACA1234A1Z5",
            bank_account_number="9876543210123",
            bank_ifsc="HDFC0001234",
            compliance_docs_url="https://drive.google.com/test",
        )
        self.assertFalse(vendor.is_verified)

        indent = create_indent(
            principal=self.user1,
            item_details="Network Switch 24-Port",
            quantity=2,
            estimated_cost=Decimal("45000.00"),
            justification="Server rack upgrade",
        )

        # 2. Attempting to issue PO to unverified vendor must fail
        with self.assertRaises(ValidationError):
            create_purchase_order(
                indent_id=indent.id,
                vendor_id=vendor.id,
                procurement_method="DIRECT",
                total_cost=Decimal("45000.00"),
                delivery_schedule="2026-12-31",
            )

        # 3. Verify vendor
        verified_vendor = verify_vendor(vendor_id=vendor.id)
        self.assertTrue(verified_vendor.is_verified)

        # 4. Now issue PO succeeds
        po = create_purchase_order(
            indent_id=indent.id,
            vendor_id=vendor.id,
            procurement_method="DIRECT",
            total_cost=Decimal("45000.00"),
            delivery_schedule="2026-12-31",
        )
        self.assertEqual(po.status, "ISSUED")

        # 5. Record Goods Receipt Note (GRN)
        grn = record_grn(
            purchase_order_id=po.id,
            accepted_quantity=2,
            rejected_quantity=0,
            inspection_remarks="All 2 switches tested and functional.",
        )
        self.assertTrue(grn.is_confirmed)
        self.assertFalse(grn.has_discrepancy)
        po.refresh_from_db()
        self.assertEqual(po.status, "DELIVERED")

    def test_stock_allocation_and_transfers(self):
        item = StockItem.objects.create(
            item_code="A4-PAPER-75GSM",
            name="A4 Paper Reams 75 GSM",
            department="CENTRAL_STORE",
            central_stock=500,
            department_stock=50,
            reserved_stock=20,
        )
        # Allocable = 500 + 50 - 20 = 530
        self.assertEqual(get_allocable_stock(item.id), 530)

        # Reserve stock
        reserve_stock(stock_item_id=item.id, quantity=50)
        item.refresh_from_db()
        self.assertEqual(item.reserved_stock, 70)
        self.assertEqual(get_allocable_stock(item.id), 480)

        # Stock transfer
        transfer = initiate_stock_transfer(
            source_dept="CENTRAL_STORE",
            dest_dept="CSE",
            stock_item_id=item.id,
            quantity=30,
        )
        self.assertEqual(transfer.status, "REQUESTED")
        self.assertEqual(transfer.quantity, 30)

    def test_plural_contracts(self):
        """Test CI Rule: All cross-module contracts are plural."""
        ind = create_indent(
            principal=self.user1,
            item_details="Lab Chairs",
            quantity=10,
            estimated_cost=Decimal("25000.00"),
            justification="Lab seating",
        )
        ind_data = get_indents([ind.id])
        self.assertEqual(len(ind_data), 1)
        self.assertEqual(ind_data[0]["indent_id"], ind.indent_id)

        ven = create_vendor(
            name="Seating World",
            gst_number="29ABCDE1234F1Z2",
            bank_account_number="1234567890",
            bank_ifsc="SBIN0004321",
        )
        ven_data = get_vendors([ven.id])
        self.assertEqual(len(ven_data), 1)
        self.assertEqual(ven_data[0]["name"], "Seating World")
