from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from modules.iwd.domain.state_machine import transition
from modules.iwd.models.complaint import Complaint
from modules.iwd.models.inventory import (
    InventoryItem,
    MaterialIssueLedger,
    ProcurementOrder,
)
from modules.iwd.services.audit import record_audit_trail


def issue_materials(
    complaint: Complaint,
    admin_user_id: int,
    item_id: int,
    quantity: int,
) -> MaterialIssueLedger:
    with transaction.atomic():
        item = InventoryItem.objects.select_for_update().get(id=item_id)
        if item.current_stock < quantity:
            msg = f"Insufficient stock for {item.name}. Available: {item.current_stock}"
            raise ValidationError(msg)

        item.current_stock -= quantity
        item.save(update_fields=["current_stock"])

        ledger = MaterialIssueLedger.objects.create(
            complaint=complaint,
            item=item,
            quantity=quantity,
            issued_by_user_id=admin_user_id,
        )

        event = (
            "issue_materials"
            if complaint.status == "materials_available"
            else "issue_materials_direct"
        )
        outcome = transition(complaint.status, event, "iwd_admin")
        if outcome.allowed:
            old_state = complaint.status
            complaint.status = outcome.next_state
            complaint.save(update_fields=["status", "updated_at"])

            record_audit_trail(
                complaint=complaint,
                actor_user_id=admin_user_id,
                acting_role="iwd_admin",
                action="issue_materials",
                from_state=old_state,
                to_state=complaint.status,
                decision_reason=f"Issued {quantity} of {item.name}",
            )

        return ledger


def conduct_procurement_or_bidding(
    complaint: Complaint,
    admin_user_id: int,
    procurement_type: str,
    vendor_name: str,
    quoted_amount: Decimal,
    vendor_details: str = "",
) -> ProcurementOrder:
    estimate = complaint.estimates.order_by("-version").first()
    if not estimate:
        raise ValidationError("Cannot procure without an estimate.")

    event_map = {
        "internal_quotation": "complete_procurement",
        "external_bidding": "select_vendor",
    }
    event = event_map.get(procurement_type)
    if not event:
        raise ValidationError(f"Invalid procurement type: {procurement_type}")

    with transaction.atomic():
        outcome = transition(complaint.status, event, "iwd_admin")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        order = ProcurementOrder.objects.create(
            complaint=complaint,
            estimate=estimate,
            procurement_type=procurement_type,
            vendor_name=vendor_name,
            quoted_amount=quoted_amount,
            vendor_details=vendor_details,
            compliance_confirmed=True,
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=admin_user_id,
            acting_role="iwd_admin",
            action=event,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=f"Procured/Selected {vendor_name} for amount {quoted_amount}",
        )

        return order
