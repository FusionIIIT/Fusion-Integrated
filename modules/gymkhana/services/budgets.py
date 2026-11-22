"""Budget request services (UC-GYM-009, BR-GYM-017, BR-GYM-018)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from core.files import drive
from core.files.drive import InvalidDriveLink
from modules.gymkhana.models import Club, ClubBudgetRequest


def submit_budget_request(
    *,
    club: Club,
    amount: Decimal | float | int,
    purpose: str,
    description: str,
    supporting_file_url: str,
    user_id: int,
) -> ClubBudgetRequest:
    """Submit club budget request with non-negative amount and Drive link (UC-GYM-009)."""
    if user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may submit budget requests.",
            code="not_club_head",
        )

    if club.status != "confirmed":
        raise ConflictError(
            "Budget requests can only be submitted for confirmed clubs.",
            code="club_not_confirmed",
        )

    amount_dec = Decimal(str(amount))
    if amount_dec < 0:
        raise BadRequestError(
            "Budget amount must be zero or greater.",
            code="negative_amount",
        )

    try:
        drive_ref = drive.parse(supporting_file_url)
    except InvalidDriveLink as exc:
        raise BadRequestError(exc.message, code=exc.code) from exc

    with transaction.atomic():
        return ClubBudgetRequest.objects.create(
            club=club,
            amount=amount_dec,
            purpose=purpose,
            description=description,
            supporting_file_url=drive_ref.url,
            supporting_file_id=drive_ref.file_id,
            status="open",
            submitted_by_user_id=user_id,
        )
