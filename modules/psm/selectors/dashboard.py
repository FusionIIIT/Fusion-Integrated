# Real-time scoped PSM dashboard summary (PSM-UC-030, AFR-PSM-081, BR-PSM-020).
from __future__ import annotations

from django.db.models import Count

from modules.psm.domain import state_machine as sm
from modules.psm.selectors import scoping


def dashboard_summary(actor) -> dict:
    """Compute real-time process counts within the caller's authorized scope."""
    indents = scoping.indents_for(actor)
    indent_by_status = {
        row["status"]: row["c"] for row in indents.values("status").annotate(c=Count("id"))
    }
    pos = scoping.purchase_orders_for(actor)
    po_by_status = {row["status"]: row["c"] for row in pos.values("status").annotate(c=Count("id"))}
    open_discrepancies = scoping.discrepancies_for(actor).exclude(status=sm.DISC_CLOSED).count()
    pending_transfers = (
        scoping.transfers_for(actor)
        .filter(status__in=(sm.TRANSFER_REQUESTED, sm.TRANSFER_DISPATCHED))
        .count()
    )
    invoices = scoping.invoices_for(actor)
    invoices_on_hold = invoices.filter(status=sm.INV_ON_HOLD).count()
    invoices_pending_payment = invoices.filter(
        status__in=(sm.INV_VERIFIED, sm.INV_PARTIALLY_PAID)
    ).count()
    return {
        "active_role": scoping.active_role_of(actor),
        "indents_total": sum(indent_by_status.values()),
        "indents_pending_approval": sum(
            indent_by_status.get(s, 0) for s in sm.INDENT_PENDING_APPROVAL
        ),
        "indents_by_status": indent_by_status,
        "purchase_orders_total": sum(po_by_status.values()),
        "purchase_orders_by_status": po_by_status,
        "open_discrepancies": open_discrepancies,
        "pending_transfers": pending_transfers,
        "invoices_on_hold": invoices_on_hold,
        "invoices_pending_payment": invoices_pending_payment,
    }
