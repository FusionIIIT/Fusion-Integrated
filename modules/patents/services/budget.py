"""Budget services: ledger entries and threshold escalation.

Enforces BR-PMS-048..053, BR-PMS-128.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import PatentBudgetLedger, PatentPolicy
from modules.patents.selectors import scoping


def record_budget_entry(
    actor,
    application_id: int,
    entry_type: str,
    amount: Decimal | str,
    category: str,
    notes: str = "",
) -> PatentBudgetLedger:
    """Record an append-only budget ledger entry."""
    scope = scoping.applications_for(actor)
    app = scope.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")

    dec_amount = Decimal(str(amount))
    if dec_amount <= Decimal("0"):
        raise ConflictError("Budget amount must be positive.")

    with transaction.atomic():
        return PatentBudgetLedger.objects.create(
            application=app,
            entry_type=entry_type,
            amount=dec_amount,
            category=category,
            authorized_by_user_id=getattr(actor, "user_id", 0),
            notes=notes,
            status="PENDING",
        )


def decide_budget(
    actor,
    entry_id: int,
    decision: str,  # "APPROVE", "REJECT"
    notes: str = "",
) -> PatentBudgetLedger:
    """Director decision on budget ledger entry; escalates if above policy threshold."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required to decide budget.")

    with transaction.atomic():
        entry = PatentBudgetLedger.objects.select_for_update().filter(pk=entry_id).first()
        if entry is None:
            raise NotFoundError("Budget entry not found.")

        # Check threshold in policy
        policy = PatentPolicy.objects.filter(is_active=True).first()
        threshold = policy.cost_escalation_threshold if policy else None

        if decision == "APPROVE":
            if threshold is not None and entry.amount > threshold:
                entry.status = "ESCALATED"
            else:
                entry.status = "APPROVED"
        elif decision == "REJECT":
            entry.status = "REJECTED"
        else:
            raise ConflictError(f"Invalid budget decision: {decision}")

        entry.notes = f"{entry.notes}\nDecision notes: {notes}".strip()
        entry.authorized_by_user_id = getattr(actor, "user_id", entry.authorized_by_user_id)
        entry.save()

    return entry
