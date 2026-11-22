from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory_contracts
from modules.gymkhana.domain.constants import ROLE_CO_COORDINATOR, ROLE_COORDINATOR
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.selectors.scoping import is_club_head


def _validate_students(student_ids: list[int]) -> None:
    users = directory_contracts.get_users(student_ids)
    for sid in student_ids:
        u = users.get(sid)
        if not u or u.kind != "student":
            raise BadRequestError(
                f"Selected leader {sid} must reference a valid student.",
                code="invalid_student_leader",
            )


@transaction.atomic
def change_leadership(
    *,
    club_id: int,
    acting_user_id: int,
    new_coordinator_id: int,
    new_co_coordinator_id: int,
) -> Club:
    club = Club.objects.select_for_update().filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if not is_club_head(acting_user_id, club_id):
        raise PermissionDeniedError(
            "Only the current club coordinator or co-coordinator may change club leadership.",
            code="not_club_head",
        )

    _validate_students([new_coordinator_id, new_co_coordinator_id])

    ClubLeadership.objects.filter(club=club, is_current=True).update(is_current=False)

    ClubLeadership.objects.create(
        club=club,
        student_id=new_coordinator_id,
        role=ROLE_COORDINATOR,
        is_current=True,
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=new_co_coordinator_id,
        role=ROLE_CO_COORDINATOR,
        is_current=True,
    )

    return club
