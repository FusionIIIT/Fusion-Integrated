"""Record maintenance — the non-sanctioning write paths (BR-EL-029, 037).

Balance adjustments and annotations are deliberately separate from the
workflow: they are auditable ledger/event entries, never approvals.
"""
from __future__ import annotations

from django.db import transaction

from modules.leave.models import LeaveRequest, LeaveRequestEvent
from modules.leave.services import authz, balances, workflow


def adjust_balance(actor, *, user_id: int, category: str, year: int,
                   days, note: str = ""):
    """BR-EL-037: maintenance only, stamped with its own ledger kind."""
    return balances.adjust(actor, user_id=user_id, category=category,
                           year=year, days=days, note=note)


@transaction.atomic
def annotate(actor, request: LeaveRequest, note: str) -> LeaveRequest:
    authz.require(actor, "leave.record.manage")
    request.admin_note = note
    request.save(update_fields=["admin_note", "updated_at"])
    workflow.record_event(request, LeaveRequestEvent.NOTE, actor=actor,
                          note=note)
    return request
