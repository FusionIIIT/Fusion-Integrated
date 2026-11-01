"""Patent budget creation, approval and escalation services (BW-PMS-08, 09, 10)."""

from __future__ import annotations

import decimal

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_DIRECTOR,
    DEFAULT_BUDGET_THRESHOLD,
    STATUS_APPROVED,
    STATUS_ATTORNEY_ASSIGNED,
    STATUS_BUDGET_APPROVED,
    STATUS_BUDGET_ESCALATED,
    STATUS_BUDGET_REJECTED,
)
from modules.pms.domain.exceptions import ValidationError
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import PatentApplication, PatentBudget, PmsConfiguration
from modules.pms.services.audit import record_audit_event


def get_budget_threshold() -> decimal.Decimal:
    """Retrieve configured escalation threshold limit (BR-PMS-051)."""
    cfg = PmsConfiguration.objects.filter(key="BUDGET_ESCALATION_THRESHOLD").first()
    if cfg:
        try:
            return decimal.Decimal(cfg.value)
        except decimal.InvalidOperation:
            pass
    return decimal.Decimal(str(DEFAULT_BUDGET_THRESHOLD))


@transaction.atomic
def create_or_update_budget(
    application: PatentApplication,
    filing_fees: decimal.Decimal | float | int,
    attorney_fees: decimal.Decimal | float | int,
    administrative_costs: decimal.Decimal | float | int,
    user_id: int,
) -> PatentBudget:
    """Create or update budget items for an application (BR-PMS-048, 049, 050)."""
    f_fees = decimal.Decimal(str(filing_fees))
    a_fees = decimal.Decimal(str(attorney_fees))
    adm_fees = decimal.Decimal(str(administrative_costs))

    if f_fees < 0 or a_fees < 0 or adm_fees < 0:
        raise ValidationError("Budget fee amounts cannot be negative.")

    total = f_fees + a_fees + adm_fees

    budget, _ = PatentBudget.objects.update_or_create(
        application=application,
        defaults={
            "filing_fees": f_fees,
            "attorney_fees": a_fees,
            "administrative_costs": adm_fees,
            "total_cost": total,
            "status": "draft",
        },
    )

    record_audit_event(
        application=application,
        user_id=user_id,
        actor_role="staff",
        action_type="save_budget",
        details={"total_cost": str(total)},
    )

    return budget


@transaction.atomic
def decide_patent_budget(
    application: PatentApplication,
    director_user_id: int,
    decision: str,  # "approve" or "reject"
    justification: str = "",
) -> PatentBudget:
    """Director budget decision: Approve, Reject, or Escalation (BW-08, 09, 10, BR-PMS-051)."""
    # 1. Budget approval permitted only when application status is Approved (BR-PMS-052)
    if application.status not in (STATUS_APPROVED, STATUS_ATTORNEY_ASSIGNED):
        msg = f"Budget approval permitted only for approved applications ({application.status!r})."
        raise ValidationError(msg, rule_id="BR-PMS-052")

    budget = application.budget
    if not budget:
        raise ValidationError("No budget recorded for this application.")

    threshold = get_budget_threshold()
    prev_status = application.status

    if decision == "approve":
        # Check if exceeds threshold -> auto-escalation (BR-PMS-051, BW-PMS-10)
        if budget.total_cost > threshold:
            validate_transition(application.status, STATUS_BUDGET_ESCALATED, ACTOR_DIRECTOR)
            application.status = STATUS_BUDGET_ESCALATED
            application.save()

            budget.status = "escalated"
            budget.director_user_id = director_user_id
            escalation_msg = (
                f"Exceeds threshold {threshold}. Escalated for institutional approval. "
                f"{justification}"
            )
            budget.justification = escalation_msg
            budget.reviewed_at = timezone.now()
            budget.save()

            record_audit_event(
                application=application,
                user_id=director_user_id,
                actor_role=ACTOR_DIRECTOR,
                action_type="budget_escalated",
                previous_state=prev_status,
                new_state=STATUS_BUDGET_ESCALATED,
                details={"total_cost": str(budget.total_cost), "threshold": str(threshold)},
            )
            return budget

        # Standard approval (BW-PMS-08)
        validate_transition(application.status, STATUS_BUDGET_APPROVED, ACTOR_DIRECTOR)
        application.status = STATUS_BUDGET_APPROVED
        application.save()

        budget.status = "approved"
        budget.director_user_id = director_user_id
        budget.justification = justification.strip()
        budget.reviewed_at = timezone.now()
        budget.save()

        record_audit_event(
            application=application,
            user_id=director_user_id,
            actor_role=ACTOR_DIRECTOR,
            action_type="budget_approved",
            previous_state=prev_status,
            new_state=STATUS_BUDGET_APPROVED,
            details={"total_cost": str(budget.total_cost)},
        )
    elif decision == "reject":
        # Rejection (BW-PMS-09)
        validate_transition(application.status, STATUS_BUDGET_REJECTED, ACTOR_DIRECTOR)
        application.status = STATUS_BUDGET_REJECTED
        application.save()

        budget.status = "rejected"
        budget.director_user_id = director_user_id
        budget.justification = justification.strip()
        budget.reviewed_at = timezone.now()
        budget.save()

        record_audit_event(
            application=application,
            user_id=director_user_id,
            actor_role=ACTOR_DIRECTOR,
            action_type="budget_rejected",
            previous_state=prev_status,
            new_state=STATUS_BUDGET_REJECTED,
            details={"justification": justification.strip()},
        )
    else:
        msg = f"Invalid budget decision {decision!r}. Must be 'approve' or 'reject'."
        raise ValidationError(msg)

    return budget
