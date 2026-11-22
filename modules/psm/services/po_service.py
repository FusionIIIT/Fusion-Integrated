from datetime import date

from django.db import transaction
from django.utils import timezone

from modules.psm.domain.state_machines import transition_po
from modules.psm.domain.threshold_policy import determine_procurement_method
from modules.psm.domain.validators import (
    ValidationError,
    validate_vendor_verified_for_po,
)
from modules.psm.models.indent import Indent, IndentStatus
from modules.psm.models.purchase_order import (
    POLineItem,
    POStatus,
    PurchaseOrder,
)
from modules.psm.models.vendor import Vendor


def generate_po_number() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"PO-{timestamp}"


@transaction.atomic
def create_purchase_order(
    indent_id: int,
    vendor_id: int,
    delivery_due_date: date | None = None,
    user_id: int | None = None,
) -> PurchaseOrder:
    """Creates a Purchase Order from an APPROVED indent and VERIFIED vendor."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)
    if indent.status != IndentStatus.APPROVED:
        raise ValidationError(
            f"Cannot create PO for indent with status '{indent.status}'. Must be APPROVED."
        )

    if hasattr(indent, "purchase_order"):
        raise ValidationError(f"Purchase order already exists for indent {indent.indent_number}.")

    vendor = Vendor.objects.get(pk=vendor_id)
    validate_vendor_verified_for_po(vendor)

    method = determine_procurement_method(indent.estimated_total)

    po = PurchaseOrder.objects.create(
        po_number=generate_po_number(),
        indent=indent,
        vendor=vendor,
        procurement_method=method,
        total_amount=indent.estimated_total,
        status=POStatus.DRAFT,
        delivery_due_date=delivery_due_date,
        issued_by_user_id=user_id,
    )

    for item in indent.items.all():
        POLineItem.objects.create(
            purchase_order=po,
            item_master=item.item_master,
            quantity_ordered=item.quantity_requested,
            unit_price=item.estimated_unit_cost,
        )

    return po


@transaction.atomic
def issue_purchase_order(po_id: int, user_id: int) -> PurchaseOrder:
    """Issues the purchase order to the vendor."""
    po = PurchaseOrder.objects.select_for_update().get(pk=po_id)
    next_state = transition_po(po.status, "ISSUE", "purchase_officer")
    po.status = next_state
    po.issued_by_user_id = user_id
    po.issued_at = timezone.now()
    po.save(update_fields=["status", "issued_by_user_id", "issued_at", "updated_at"])
    return po


@transaction.atomic
def cancel_purchase_order(po_id: int, user_id: int) -> PurchaseOrder:
    po = PurchaseOrder.objects.select_for_update().get(pk=po_id)
    next_state = transition_po(po.status, "CANCEL", "purchase_officer")
    po.status = next_state
    po.save(update_fields=["status", "updated_at"])
    return po
