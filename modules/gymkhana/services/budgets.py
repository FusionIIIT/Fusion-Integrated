from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.validation import validate_budget_amount
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def submit_budget_request(
    *,
    club_id: int,
    acting_user_id: int,
    amount: Decimal | float | int,
    purpose: str,
    description: str,
    supporting_file,
) -> ClubBudgetRequest:
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if not is_club_head(acting_user_id, club_id):
        raise PermissionDeniedError(
            "Only the applicable club coordinator or co-coordinator may request a club budget.",
            code="not_club_head",
        )

    try:
        validate_budget_amount(amount)
    except ValueError as e:
        raise BadRequestError(str(e), code="invalid_budget_amount") from e

    if not supporting_file:
        raise BadRequestError(
            "A club budget request must include its required supporting file.",
            code="missing_supporting_file",
        )

    return ClubBudgetRequest.objects.create(
        club=club,
        amount=amount,
        purpose=purpose,
        description=description,
        supporting_file=supporting_file,
        submitted_by_id=acting_user_id,
        status="open",
    )
