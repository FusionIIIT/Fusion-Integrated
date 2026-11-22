"""Durable PHC notifications written inside the event's transaction (BR-11, BR-13)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from modules.phc.domain.policy import OUTBOX_TOPICS
from modules.phc.models import NotificationOutbox


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None, recipient_role: str = "",
            payload: dict | None = None) -> NotificationOutbox | None:
    """Queue one notification; return None when the key was already queued."""
    if topic not in OUTBOX_TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not recipient_role:
        raise ValueError("A notification needs a recipient.")
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id, recipient_role=recipient_role,
                payload=payload or {},
            )
    except IntegrityError:
        return None


def claim_status_notice(claim, action: str) -> NotificationOutbox | None:
    """Notify the claimant whenever a claim changes state."""
    labels = {
        "submit": "submitted", "review": "sent for verification",
        "verify": "sent for sanction", "sanction_approve": "approved",
        "sanction_reject": "rejected", "payment": "paid",
    }
    label = labels.get(action, "updated")
    return enqueue(
        topic="claim.status_changed",
        dedupe_key=f"claim:{claim.pk}:{claim.state}:{action}",
        subject=f"Reimbursement claim {claim.pk} {label}",
        body=(f"Your reimbursement claim {claim.pk} was {label}. "
              "Open My Reimbursement Claims for the full history."),
        recipient_user_id=claim.employee_id,
        payload={"claim_id": claim.pk, "state": claim.state, "action": action},
    )


def requisition_notice(requisition, decision: str) -> NotificationOutbox | None:
    """Notify the originating PHC staff member of an approval or rejection."""
    label = {"approve": "approved", "reject": "rejected"}.get(decision, decision)
    return enqueue(
        topic="requisition.decided",
        dedupe_key=f"requisition:{requisition.pk}:{requisition.state}",
        subject=f"Requisition {requisition.pk} {label}",
        body=(f"Requisition {requisition.pk} was {label}. "
              "Open Procurement Requisitions for the decision note."),
        recipient_user_id=requisition.originator_id,
        payload={"requisition_id": requisition.pk, "state": requisition.state},
    )


def low_stock_notice(item, quantity: int) -> NotificationOutbox | None:
    """Alert PHC staff when stock falls below the reorder threshold."""
    return enqueue(
        topic="inventory.low_stock",
        dedupe_key=f"low-stock:{item.pk}:{quantity}",
        subject=f"Low stock: {item.name}",
        body=(f"{item.name} is down to {quantity} {item.unit}, below its reorder "
              f"threshold of {item.reorder_threshold}."),
        recipient_role="phc_staff",
        payload={"item_id": item.pk, "quantity": quantity},
    )
