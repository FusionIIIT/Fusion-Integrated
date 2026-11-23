"""Club budget request services for Gymkhana."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.constants import BUDGET_STATUS_OPEN, CLUB_STATUS_CONFIRMED
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import (
    validate_budget_amount,
    validate_file_present,
)
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def submit_budget_request(
    *,
    club_id: int,
    actor_id: int,
    amount: Decimal | float | int,
    purpose: str,
    description: str,
    supporting_file,
) -> ClubBudgetRequest:
    """Submit a non-negative club budget request with mandatory file (UC-GYM-009, CFR-GYM-006)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError("Only the active Club Head can submit budget requests.")

    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError("Budget requests can only be submitted for confirmed clubs.")

    try:
        clean_amount = validate_budget_amount(amount)
        validate_file_present(bool(supporting_file), "supporting_file")
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc

    return ClubBudgetRequest.objects.create(
        club=club,
        submitted_by_id=actor_id,
        amount=clean_amount,
        purpose=purpose.strip(),
        description=description.strip(),
        supporting_file=supporting_file,
        status=BUDGET_STATUS_OPEN,
    )
