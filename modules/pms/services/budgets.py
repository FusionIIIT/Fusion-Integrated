"""PMS Budget Review and Financial Tracking service.

Enforces business rules BR-PMS-048 through 053.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import check_budget_escalation, validate_budget_components
from modules.pms.domain.errors import (
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
)
from modules.pms.models import PatentApplication, PatentBudget
from modules.pms.services.audit import log_audit
from modules.pms.services.configuration import load_policy
from modules.pms.services.notifications import enqueue_notification


def submit_or_update_budget(
    *,
    application_id: int,
    filing_fees: Decimal,
    attorney_fees: Decimal,
    administrative_costs: Decimal,
    actor_user_id: int,
    threshold_limit: Decimal | None = None,
) -> PatentBudget:
    """Submit or update budget line items for an approved patent (UC-PMS-009, CFR-PMS-011)."""
    total = validate_budget_components(filing_fees, attorney_fees, administrative_costs)

    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Budget is its own workflow record; its decision is permitted only
        # while the application itself remains Approved (BR-PMS-052).
        if app.status != PatentApplicationStatus.APPROVED.value:
            raise PreconditionNotMetError(
                f"Budget submission is only permitted for Approved applications, "
                f"not '{app.status}' (BR-PMS-052)."
            )

        budget, _ = PatentBudget.objects.get_or_create(application=app)
        budget.filing_fees = filing_fees
        budget.attorney_fees = attorney_fees
        budget.administrative_costs = administrative_costs
        budget.total_cost = total
        # The escalation threshold is operator policy (DEC-7). When none is
        # configured the column keeps its legacy value and is not consulted by
        # decide_budget — no invented default is applied here.
        policy_threshold = load_policy().budget_threshold
        if policy_threshold is not None:
            budget.threshold_limit = policy_threshold
        elif threshold_limit is not None:
            budget.threshold_limit = threshold_limit
        budget.status = "pending_approval"
        budget.save()

        log_audit(
            application=app,
            actor_user_id=actor_user_id,
            action_type="budget_updated",
            details={
                "filing_fees": str(filing_fees),
                "attorney_fees": str(attorney_fees),
                "administrative_costs": str(administrative_costs),
                "total_cost": str(total),
            },
        )

    return budget


def decide_budget(
    *,
    application_id: int,
    director_user_id: int,
    decision: str,  # "Approve", "Reject", "Escalate"
    justification: str = "",
) -> PatentBudget:
    """Director decision on proposed patent budget (UC-PMS-009, CFR-PMS-011, CFR-PMS-030)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)
        budget = app.budget

        if app.status != PatentApplicationStatus.APPROVED.value:
            raise PreconditionNotMetError(
                "Budget decisions are only permitted while the application is Approved "
                "(BR-PMS-052)."
            )
        if budget.status != "pending_approval":
            raise PreconditionNotMetError(
                "A budget decision requires a budget pending approval."
            )

        # Budget availability check (BR-PMS-053)
        if not budget.availability_verified and decision == "Approve":
            raise PreconditionNotMetError("Budget availability could not be verified (BR-PMS-053).")

        now = timezone.now()

        # Escalation is driven by configured policy only (BR-PMS-051, DEC-7).
        # With no threshold configured there is nothing to compare, so the
        # decision stands as recorded — PMS does not invent a limit.
        threshold = load_policy().budget_threshold
        if (
            threshold is not None
            and decision == "Approve"
            and check_budget_escalation(budget.total_cost, threshold)
        ):
            decision = "Escalate"

        if decision == "Approve":
            budget_status = "approved"
        elif decision == "Reject":
            budget_status = "rejected"
        elif decision == "Escalate":
            budget_status = "escalated"
        else:
            raise PreconditionNotMetError(
                f"Invalid budget decision '{decision}'. Must be Approve, Reject, or Escalate."
            )

        budget.status = budget_status
        budget.decided_by_user_id = director_user_id
        budget.decided_at = now
        budget.justification = justification.strip()
        budget.save()

        log_audit(
            application=app,
            actor_user_id=director_user_id,
            action_type=f"budget_{budget_status}",
            details={
                "decision": decision,
                "budget_status": budget_status,
                "total_cost": str(budget.total_cost),
                "threshold": str(threshold) if threshold is not None else "not configured",
                "justification": justification,
            },
        )

        topic = "budget.escalated" if decision == "Escalate" else "budget.decided"
        enqueue_notification(
            topic=topic,
            dedupe_key=f"pms:budget:decision:{app.id}:{now.timestamp()}",
            subject=f"PMS: Budget Decision - {decision} ({app.application_no})",
            body=(
                f"Budget of {budget.total_cost} for '{app.title}' has been "
                f"{budget_status}. Justification: {justification}"
            ),
            recipient_user_id=app.applicant_user_id,
        )

    return budget
