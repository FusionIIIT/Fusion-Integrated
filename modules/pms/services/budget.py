from datetime import datetime
from decimal import Decimal
from django.db import transaction

from modules.pms.models.budget import BudgetStatus, PatentBudget
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def review_budget(
    app_id: int,
    user_id: int,
    decision: str,
    approved_amount: Decimal | None,
    roles: list[str],
    notes: str = "",
) -> PatentBudget:
    """Review and sanction or reject patent filing budget (BW-PMS-08, BW-PMS-09)."""
    app = get_application_scoped(app_id, user_id, roles)
    budget, _ = PatentBudget.objects.get_or_create(application=app)

    budget.budget_status = decision
    if decision == BudgetStatus.APPROVED and approved_amount is not None:
        budget.approved_amount = approved_amount
    budget.decided_by_user_id = user_id
    budget.decision_date = datetime.now()
    if notes:
        budget.escalation_notes = notes

    budget.save()
    return budget
