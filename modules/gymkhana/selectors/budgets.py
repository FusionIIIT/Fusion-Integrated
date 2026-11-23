"""Budget read selectors for Gymkhana."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.gymkhana.models.budget import ClubBudgetRequest


def get_budget_by_id(budget_id: int) -> ClubBudgetRequest:
    """Return budget request by ID or raise NotFound."""
    req = ClubBudgetRequest.objects.select_related("club").filter(id=budget_id).first()
    if not req:
        raise NotFoundError(f"Budget request {budget_id} not found.")
    return req
