"""PHC services: notifications outbox.

Populates PhcNotification rows; actual delivery is best-effort (console/email).
PHC-BR-07, PHC-BR-11, PHC-BR-13.
"""

from __future__ import annotations

import logging

from django.utils import timezone

from modules.phc.models import PhcNotification

log = logging.getLogger("fusion.phc.notifications")


def _enqueue(
    *,
    recipient_user_id: int,
    event_type: str,
    subject: str,
    body: str,
    reference_id: int | None = None,
    reference_type: str = "",
) -> PhcNotification:
    return PhcNotification.objects.create(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        subject=subject,
        body=body,
        reference_id=reference_id,
        reference_type=reference_type,
    )


def notify_claim_status_changed(
    *,
    claim,
    to_status: str,
    actor_user_id: int | None = None,
) -> None:
    """PHC-BR-13: Notify the claimant on every claim status change."""
    status_labels = {
        "pending_phc_review": "Pending PHC Review",
        "pending_accounts_verification": "Pending Accounts Verification",
        "pending_sanction": "Pending Sanction",
        "approved_for_payment": "Approved for Payment",
        "reimbursed": "Reimbursed",
        "rejected": "Rejected",
    }
    label = status_labels.get(to_status, to_status)
    _enqueue(
        recipient_user_id=claim.user_id,
        event_type="claim_status_changed",
        subject=f"Reimbursement Claim #{claim.pk} - Status: {label}",
        body=(
            f"Your medical bill reimbursement claim #{claim.pk} has been updated.\n"
            f"Current status: {label}\n"
            f"Please log in to PHC to view the details."
        ),
        reference_id=claim.pk,
        reference_type="reimbursement_claim",
    )
    log.info("phc.notify.claim_status claim=%s to=%s", claim.pk, to_status)


def notify_requisition_decided(
    *,
    requisition,
    new_status: str,
    actor_user_id: int | None = None,
) -> None:
    """PHC-BR-11: Notify the originating PHC Staff member of approval/rejection."""
    verb = "approved" if new_status == "approved" else "rejected"
    _enqueue(
        recipient_user_id=requisition.submitted_by_user_id,
        event_type="requisition_decided",
        subject=f"Procurement Requisition #{requisition.pk} has been {verb}",
        body=(
            f"Your inventory procurement requisition '{requisition.title}' "
            f"(#{requisition.pk}) has been {verb}.\n"
            f"Decision notes: {requisition.decision_notes or 'None'}\n"
            f"Please log in to PHC for details."
        ),
        reference_id=requisition.pk,
        reference_type="procurement_requisition",
    )
    log.info("phc.notify.requisition req=%s status=%s", requisition.pk, new_status)


def notify_low_stock(*, item, actor_user_id: int | None = None) -> None:
    """PHC-BR-07: enqueue an in-app low-stock warning for the acting PHC Staff member."""
    if actor_user_id is None:
        log.warning("phc.notify.low_stock_missing_recipient item=%s", item.pk)
        return
    _enqueue(
        recipient_user_id=actor_user_id,
        event_type="low_stock_alert",
        subject=f"Low-Stock Alert: {item.name}",
        body=(
            f"Inventory item '{item.name}' has fallen below its reorder threshold.\n"
            f"Current stock: {item.stock_quantity} {item.unit}\n"
            f"Reorder threshold: {item.reorder_threshold} {item.unit}\n"
            f"Please raise a procurement requisition."
        ),
        reference_id=item.pk,
        reference_type="inventory_item",
    )
    log.info("phc.notify.low_stock item=%s qty=%s", item.pk, item.stock_quantity)


def deliver_pending(limit: int = 200) -> dict:
    """Best-effort delivery for the PHC notification outbox.

    Currently logs to console; a real deployment would send emails here.
    Returns a summary dict for logging.
    """

    rows = list(PhcNotification.objects.filter(delivered=False).order_by("created_at")[:limit])
    delivered = failed = skipped = 0
    for n in rows:
        if n.recipient_user_id == -1:
            # broadcast — log and mark; real delivery would fan out
            log.info("phc.notify.broadcast type=%s ref=%s", n.event_type, n.reference_id)
            n.delivered = True
            n.delivered_at = timezone.now()
            n.save(update_fields=["delivered", "delivered_at", "attempts"])
            delivered += 1
            continue
        try:
            n.attempts += 1
            log.info(
                "phc.notify.deliver to=%s subject=%s",
                n.recipient_user_id,
                n.subject,
            )
            n.delivered = True
            n.delivered_at = timezone.now()
            n.save(update_fields=["delivered", "delivered_at", "attempts"])
            delivered += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("phc.notify.deliver_failed notif=%s err=%s", n.pk, exc)
            n.save(update_fields=["attempts"])
            failed += 1
    return {"delivered": delivered, "failed": failed, "skipped": skipped}
