"""PMS Budget Review and Financial Tracking service.

Enforces business rules BR-PMS-048 through 053.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import (
    DEFAULT_BUDGET_THRESHOLD,
    check_budget_escalation,
    validate_budget_components,
)
from modules.pms.domain.errors import (
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import PatentApplication, PatentBudget
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def submit_or_update_budget(
    *,
    application_id: int,
    filing_fees: Decimal,
    attorney_fees: Decimal,
    administrative_costs: Decimal,
    actor_user_id: int,
    threshold_limit: Decimal = DEFAULT_BUDGET_THRESHOLD,
) -> PatentBudget:
    """Submit or update budget line items for an approved patent (UC-PMS-009, CFR-PMS-011)."""
    total = validate_budget_components(filing_fees, attorney_fees, administrative_costs)

    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Precondition check: application must be in an approved status (BR-PMS-052)
        valid_statuses = (
            PatentApplicationStatus.APPROVED.value,
            PatentApplicationStatus.ATTORNEY_ASSIGNED.value,
            PatentApplicationStatus.BUDGET_APPROVED.value,
            PatentApplicationStatus.BUDGET_REJECTED.value,
            PatentApplicationStatus.ESCALATED.value,
        )
        if app.status not in valid_statuses:
            raise PreconditionNotMetError(
                f"Budget submission is only permitted for Approved applications, not '{app.status}' (BR-PMS-052)."
            )

        budget, _ = PatentBudget.objects.get_or_create(application=app)
        budget.filing_fees = filing_fees
        budget.attorney_fees = attorney_fees
        budget.administrative_costs = administrative_costs
        budget.total_cost = total
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

        # Budget availability check (BR-PMS-053)
        if not budget.availability_verified and decision == "Approve":
            raise PreconditionNotMetError("Budget availability could not be verified (BR-PMS-053).")

        now = timezone.now()

        # Check threshold limit escalation (BR-PMS-051)
        is_exceeded = check_budget_escalation(budget.total_cost, budget.threshold_limit)
        if is_exceeded and decision == "Approve":
            # Must escalate rather than approve directly
            decision = "Escalate"

        if decision == "Approve":
            target_status = PatentApplicationStatus.BUDGET_APPROVED
            budget_status = "approved"
        elif decision == "Reject":
            target_status = PatentApplicationStatus.BUDGET_REJECTED
            budget_status = "rejected"
        elif decision == "Escalate":
            target_status = PatentApplicationStatus.ESCALATED
            budget_status = "escalated"
        else:
            raise PreconditionNotMetError(
                f"Invalid budget decision '{decision}'. Must be Approve, Reject, or Escalate."
            )

        validate_transition(app.status, target_status, actor_role="Director")
        prev_status = app.status

        budget.status = budget_status
        budget.decided_by_user_id = director_user_id
        budget.decided_at = now
        budget.justification = justification.strip()
        budget.save()

        app.status = target_status.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=director_user_id,
            action_type=f"budget_{budget_status}",
            from_state=prev_status,
            to_state=app.status,
            details={
                "decision": decision,
                "total_cost": str(budget.total_cost),
                "threshold": str(budget.threshold_limit),
                "justification": justification,
            },
        )

        topic = "budget.escalated" if decision == "Escalate" else "budget.decided"
        enqueue_notification(
            topic=topic,
            dedupe_key=f"pms:budget:decision:{app.id}:{now.timestamp()}",
            subject=f"PMS: Budget Decision - {decision} ({app.application_no})",
            body=f"Budget of {budget.total_cost} for '{app.title}' has been {budget_status}. Justification: {justification}",
            recipient_user_id=app.applicant_user_id,
        )

    return budget
