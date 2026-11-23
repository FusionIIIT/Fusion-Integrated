"""Budget services: append-only ledger, decisions, reversals and threshold escalation."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import PatentBudgetLedger, PatentPolicy
from modules.patents.selectors import scoping
from modules.patents.services import audit, notifications

DECISION_KINDS = ("APPROVAL", "ESCALATION")


def record_budget_entry(
    actor,
    application_id: int,
    entry_type: str,
    amount: Decimal | str,
    category: str,
    notes: str = "",
) -> PatentBudgetLedger:
    """Record a budget request. It is the only row that starts a budget item."""
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
            entry_kind="REQUEST",
            entry_type=entry_type,
            amount=dec_amount,
            category=category,
            authorized_by_user_id=getattr(actor, "user_id", 0),
            notes=notes,
            status="PENDING",
        )


def _latest_decision(request: PatentBudgetLedger) -> PatentBudgetLedger | None:
    return (
        request.linked_entries.filter(entry_kind__in=DECISION_KINDS)
        .order_by("-id")
        .first()
    )


def decide_budget(
    actor,
    entry_id: int,
    decision: str,  # "APPROVE", "REJECT"
    notes: str = "",
) -> PatentBudgetLedger:
    """Record a decision as a new row. Above the threshold it is recorded as an ESCALATION."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required to decide budget.")
    if decision not in ("APPROVE", "REJECT"):
        raise ConflictError(f"Invalid budget decision: {decision}")

    with transaction.atomic():
        request = (
            PatentBudgetLedger.objects.select_for_update()
            .filter(pk=entry_id, entry_kind="REQUEST")
            .first()
        )
        if request is None:
            raise NotFoundError("Budget request not found.")

        previous = _latest_decision(request)
        if previous is not None and previous.entry_kind != "ESCALATION":
            raise ConflictError("Budget request has already been decided.")

        if decision == "REJECT":
            kind, status = "APPROVAL", "REJECTED"
        else:
            policy = PatentPolicy.objects.filter(is_active=True).first()
            threshold = policy.cost_escalation_threshold if policy else None
            over = threshold is not None and request.amount > threshold
            if over and previous is None:
                kind, status = "ESCALATION", "ESCALATED"
            else:
                kind, status = "APPROVAL", "APPROVED"

        decision_row = PatentBudgetLedger.objects.create(
            application=request.application,
            entry_kind=kind,
            replaces_entry=request,
            entry_type=request.entry_type,
            amount=request.amount,
            currency=request.currency,
            category=request.category,
            status=status,
            authorized_by_user_id=getattr(actor, "user_id", request.authorized_by_user_id),
            notes=notes,
        )
        audit.record(
            actor, "budget_decision", request.application, new_state=status,
            entry_kind=kind, amount=str(request.amount), currency=request.currency,
            category=request.category,
        )

    _notify_budget_decision(decision_row, request)
    return decision_row


def _notify_budget_decision(decision: PatentBudgetLedger, request: PatentBudgetLedger) -> None:
    """Budget approval, rejection or escalation notice (PMS-AFR-196, CFR-PMS-030)."""
    app = decision.application
    outcome = {"APPROVED": "approved", "REJECTED": "rejected", "ESCALATED": "escalated"}.get(
        decision.status, decision.status.lower(),
    )
    notifications.notify(
        [app.user_id, request.authorized_by_user_id],
        app,
        f"Budget {outcome}",
        f"The {request.entry_type} budget of {request.amount} {request.currency} was {outcome}.",
    )


def track_escalation(
    actor,
    application_id: int,
    entry_id: int | None = None,
    notes: str = "",
) -> PatentBudgetLedger:
    """PCC_ADMIN records an escalated case as tracked while the external decision is pending.

    PMS invents no higher-authority decision: the row only records that the case is being
    handled (BW-PMS-10 step 2, UC-PMS-027).
    """
    if not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("PCC_ADMIN authority required to handle escalations.")

    with transaction.atomic():
        requests = PatentBudgetLedger.objects.select_for_update().filter(
            application_id=application_id, entry_kind="REQUEST",
        )
        if entry_id is not None:
            requests = requests.filter(pk=entry_id)
        target = None
        for request in requests.order_by("id"):
            latest = _latest_decision(request)
            if latest is not None and latest.status == "ESCALATED":
                target = (request, latest)
                break
        if target is None:
            raise ConflictError("No escalated budget case is waiting to be tracked.")
        request, latest = target
        row = PatentBudgetLedger.objects.create(
            application=request.application,
            entry_kind="ESCALATION",
            replaces_entry=request,
            entry_type=request.entry_type,
            amount=request.amount,
            currency=request.currency,
            category=request.category,
            status="ESCALATION_TRACKED",
            authorized_by_user_id=getattr(actor, "user_id", 0),
            notes=notes,
        )
        audit.record(
            actor, "budget_escalation_tracked", request.application,
            "ESCALATED", "ESCALATION_TRACKED", amount=str(request.amount), notes=notes,
        )
    return row


def reverse_budget_entry(actor, approval_id: int, notes: str = "") -> PatentBudgetLedger:
    """Reverse an approved decision with a new REVERSAL row. The approval row is kept."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required to reverse a budget decision.")

    with transaction.atomic():
        approval = (
            PatentBudgetLedger.objects.select_for_update()
            .filter(pk=approval_id, entry_kind="APPROVAL", status="APPROVED")
            .first()
        )
        if approval is None:
            raise NotFoundError("Approved budget decision not found.")
        if approval.linked_entries.filter(entry_kind="REVERSAL").exists():
            raise ConflictError("Budget decision has already been reversed.")

        return PatentBudgetLedger.objects.create(
            application=approval.application,
            entry_kind="REVERSAL",
            replaces_entry=approval,
            entry_type=approval.entry_type,
            amount=approval.amount,
            currency=approval.currency,
            category=approval.category,
            status="REVERSED",
            authorized_by_user_id=getattr(actor, "user_id", approval.authorized_by_user_id),
            notes=notes,
        )


def approved_total(application_id: int) -> Decimal:
    """Approved spend for an application: approvals minus reversals, derived from the ledger."""
    approved = (
        PatentBudgetLedger.objects.filter(
            application_id=application_id, entry_kind="APPROVAL", status="APPROVED",
        ).aggregate(total=Sum("amount"))["total"]
    ) or Decimal("0")
    reversed_ = (
        PatentBudgetLedger.objects.filter(
            application_id=application_id, entry_kind="REVERSAL",
        ).aggregate(total=Sum("amount"))["total"]
    ) or Decimal("0")
    return approved - reversed_
