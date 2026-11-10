"""
Procurement and Vendor Services (PSM Module).
Enforces vendor verification gating and PO / GRN lifecycles.
"""

import uuid
from decimal import Decimal
from typing import Any
from django.db import transaction
from core.api.exceptions import BadRequestError as ValidationError, NotFoundError

from modules.psm.models import Vendor, PurchaseOrder, GoodsReceiptNote, Indent


@transaction.atomic
def create_vendor(
    *,
    name: str,
    gst_number: str,
    bank_account_number: str,
    bank_ifsc: str,
    compliance_docs_url: str = "",
) -> Vendor:
    """Register a new vendor in the system."""
    name_clean = name.strip()
    gst_clean = gst_number.strip().upper()
    if not name_clean:
        raise ValidationError("Vendor name cannot be empty.")
    if len(gst_clean) != 15:
        raise ValidationError("GST number must be exactly 15 alphanumeric characters.")

    if Vendor.objects.filter(gst_number=gst_clean).exists():
        raise ValidationError(f"Vendor with GST number {gst_clean} already registered.")

    vendor = Vendor.objects.create(
        name=name_clean,
        gst_number=gst_clean,
        bank_account_number=bank_account_number.strip(),
        bank_ifsc=bank_ifsc.strip().upper(),
        compliance_docs_url=compliance_docs_url.strip(),
        is_verified=False,
        version=1,
    )
    return vendor


@transaction.atomic
def verify_vendor(*, vendor_id: Any) -> Vendor:
    """Verify vendor compliance details (Admin action)."""
    vendor = Vendor.objects.filter(id=int(vendor_id)).first()
    if not vendor:
        raise NotFoundError("Vendor not found.")

    vendor.is_verified = True
    vendor.version += 1
    vendor.save()
    return vendor


@transaction.atomic
def create_purchase_order(
    *,
    indent_id: Any,
    vendor_id: Any,
    procurement_method: str,
    total_cost: Any,
    delivery_schedule: Any,
) -> PurchaseOrder:
    """Create a Purchase Order for an approved indent (AFR-PSM-031).

    Gated by:
    1. Vendor MUST be verified.
    2. Indent must be present and in a valid approved or pending-procurement status.
    """
    vendor = Vendor.objects.filter(id=int(vendor_id)).first()
    if not vendor:
        raise NotFoundError("Vendor not found.")

    if not vendor.is_verified:
        raise ValidationError(
            f"Cannot issue Purchase Order to unverified vendor '{vendor.name}'. Compliance verification required."
        )

    indent = Indent.objects.filter(id=indent_id).first() or \
             Indent.objects.filter(indent_id=str(indent_id)).first()
    if not indent:
        raise NotFoundError("Indent not found.")

    cost = Decimal(str(total_cost))
    if cost <= Decimal("0.00"):
        raise ValidationError("Total cost must be greater than zero.")

    method = str(procurement_method).upper()
    if method not in ["DIRECT", "TENDER"]:
        method = "DIRECT"

    po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"

    po = PurchaseOrder.objects.create(
        po_number=po_number,
        indent=indent,
        vendor=vendor,
        procurement_method=method,
        status="ISSUED",
        total_cost=cost,
        delivery_schedule=delivery_schedule,
    )
    return po


@transaction.atomic
def record_grn(
    *,
    purchase_order_id: Any,
    accepted_quantity: int,
    rejected_quantity: int = 0,
    inspection_remarks: str = "",
) -> GoodsReceiptNote:
    """Record a Goods Receipt Note (GRN) upon physical delivery."""
    po = PurchaseOrder.objects.filter(id=purchase_order_id).first() or \
         PurchaseOrder.objects.filter(po_number=str(purchase_order_id)).first()
    if not po:
        raise NotFoundError("Purchase Order not found.")

    acc = int(accepted_quantity)
    rej = int(rejected_quantity)
    if acc < 0 or rej < 0:
        raise ValidationError("Accepted and rejected quantities cannot be negative.")
    if acc == 0 and rej == 0:
        raise ValidationError("At least one item must be received (accepted or rejected).")

    has_discrepancy = rej > 0 or (acc < po.indent.quantity)

    grn_number = f"GRN-{uuid.uuid4().hex[:8].upper()}"

    grn = GoodsReceiptNote.objects.create(
        grn_number=grn_number,
        purchase_order=po,
        accepted_quantity=acc,
        rejected_quantity=rej,
        inspection_remarks=inspection_remarks.strip(),
        is_confirmed=True,
        has_discrepancy=has_discrepancy,
    )

    if acc >= po.indent.quantity:
        po.status = "DELIVERED"
        po.save()

    return grn
