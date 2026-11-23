"""Inventory check before procurement and work-linked material issue (BR-IWD-010, BR-IWD-011)."""

from modules.iwd.domain.cost_bands import BAND_LOW
from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail, InventoryItem, MaterialIssue


def check_stock_and_issue(
    complaint_id: int, item_id: int, quantity: int, user_id: int, remarks: str = ""
) -> Complaint:
    """Issue available stock or route to procurement on shortage (UC-IWD-061, BR-IWD-010)."""
    complaint = Complaint.objects.get(id=complaint_id)
    item = InventoryItem.objects.get(id=item_id)
    prev = complaint.status

    if item.stock_quantity >= quantity:
        # Issue available stock
        item.stock_quantity -= quantity
        item.save()
        MaterialIssue.objects.create(
            complaint=complaint,
            item=item,
            quantity=quantity,
            issued_by_user_id=user_id,
            remarks=remarks,
        )
        complaint.status = get_next_state(prev, "issue_stock", "iwd_admin")
        complaint.save()

        DecisionAuditTrail.objects.create(
            complaint=complaint,
            actor_user_id=user_id,
            actor_role="iwd_admin",
            action="issue_stock",
            previous_state=prev,
            new_state=complaint.status,
            remarks=f"Issued {quantity} {item.unit} of {item.name}",
        )
    else:
        # Stock shortage -> route to procurement
        estimate = complaint.estimates.latest("created_at")
        action = "shortage_low" if estimate.cost_band == BAND_LOW else "shortage_mid"
        complaint.status = get_next_state(prev, action, "iwd_admin")
        complaint.save()

        DecisionAuditTrail.objects.create(
            complaint=complaint,
            actor_user_id=user_id,
            actor_role="iwd_admin",
            action="stock_shortage",
            previous_state=prev,
            new_state=complaint.status,
            remarks=f"Shortage for {item.name}. Routed to procurement.",
        )

    return complaint


def complete_procurement(complaint_id: int, user_id: int) -> Complaint:
    """Mark procurement completed and make material available for issue (UC-IWD-071)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "procure_complete", "iwd_admin")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=user_id,
        actor_role="iwd_admin",
        action="complete_procurement",
        previous_state=prev,
        new_state=complaint.status,
        remarks="Material procured and available",
    )
    return complaint
