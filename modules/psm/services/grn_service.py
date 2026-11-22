from collections.abc import Sequence
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.psm.domain.state_machines import transition_grn
from modules.psm.domain.validators import ValidationError
from modules.psm.models.goods_receipt import (
    GoodsReceiptNote,
    GRNItem,
    GRNStatus,
)
from modules.psm.models.purchase_order import POLineItem, POStatus, PurchaseOrder
from modules.psm.services.discrepancy_service import raise_discrepancy
from modules.psm.services.inventory_service import credit_stock_from_grn


def generate_grn_number() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"GRN-{timestamp}"


@transaction.atomic
def create_grn(
    po_id: int,
    user_id: int,
    receipt_date: date,
    challan_number: str = "",
    invoice_number: str = "",
    items_data: Sequence[dict[str, Any]] = (),
) -> GoodsReceiptNote:
    """Logs physical delivery of items against a Purchase Order."""
    po = PurchaseOrder.objects.select_for_update().get(pk=po_id)
    if po.status not in [POStatus.ISSUED, POStatus.PARTIALLY_DELIVERED]:
        raise ValidationError(f"Cannot receive goods for PO in status '{po.status}'.")

    grn = GoodsReceiptNote.objects.create(
        grn_number=generate_grn_number(),
        purchase_order=po,
        store_keeper_user_id=user_id,
        challan_number=challan_number.strip(),
        invoice_number=invoice_number.strip(),
        receipt_date=receipt_date,
        status=GRNStatus.INSPECTION_PENDING,
    )

    has_rejections = False
    for item_data in items_data:
        po_line = POLineItem.objects.get(pk=item_data["po_line_item_id"])
        received = int(item_data["quantity_received"])
        accepted = int(item_data.get("quantity_accepted", received))
        rejected = int(item_data.get("quantity_rejected", 0))

        if accepted + rejected != received:
            raise ValidationError(
                f"Accepted ({accepted}) + Rejected ({rejected}) must equal Received ({received})."
            )

        grn_item = GRNItem.objects.create(
            grn=grn,
            po_line_item=po_line,
            quantity_received=received,
            quantity_accepted=accepted,
            quantity_rejected=rejected,
            rejection_remarks=item_data.get("rejection_remarks", ""),
        )

        if rejected > 0:
            has_rejections = True

        if accepted > 0:
            credit_stock_from_grn(grn_item, user_id=user_id)

    if has_rejections:
        grn.status = transition_grn(grn.status, "FLAG_DISCREPANCY", "store_keeper")
        grn.save(update_fields=["status", "updated_at"])
        # Raise discrepancy report automatically which freezes payment hold
        raise_discrepancy(
            grn_id=grn.id,
            user_id=user_id,
            discrepancy_type="DAMAGED",
            details="Partial rejection of goods during store keeper inspection.",
        )
    else:
        grn.status = transition_grn(grn.status, "ACCEPT_ALL", "store_keeper")
        grn.save(update_fields=["status", "updated_at"])

    # Update PO delivery status
    po.status = POStatus.COMPLETED
    po.save(update_fields=["status", "updated_at"])

    return grn


@transaction.atomic
def acknowledge_grn(grn_id: int, user_id: int) -> GoodsReceiptNote:
    """Enforces CFR-PSM-009: Indentor receipt acknowledgement."""
    grn = GoodsReceiptNote.objects.select_for_update().get(pk=grn_id)
    if grn.purchase_order.indent.user_id != user_id:
        raise ValidationError("Only the indent requestor may acknowledge goods receipt.")

    grn.indentor_acknowledged = True
    grn.indentor_acknowledged_at = timezone.now()
    if grn.status == GRNStatus.ACCEPTED:
        grn.status = transition_grn(grn.status, "INDENTOR_CONFIRM", "requestor")
    fields_to_update = [
        "indentor_acknowledged",
        "indentor_acknowledged_at",
        "status",
        "updated_at",
    ]
    grn.save(update_fields=fields_to_update)
    return grn
