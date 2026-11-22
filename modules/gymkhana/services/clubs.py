from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory_contracts
from modules.gymkhana.domain.constants import (
    CLUB_CATEGORIES,
    ROLE_CO_COORDINATOR,
    ROLE_COORDINATOR,
    STATUS_OPEN,
)
from modules.gymkhana.domain.state_machine import transition_club
from modules.gymkhana.models.club import Club, ClubLeadership


def _validate_students(student_ids: list[int]) -> None:
    users = directory_contracts.get_users(student_ids)
    for sid in student_ids:
        u = users.get(sid)
        if not u or u.kind != "student":
            raise BadRequestError(
                f"Selected leader {sid} must reference a valid student.",
                code="invalid_student_leader",
            )


def _validate_faculty(faculty_id: int) -> None:
    users = directory_contracts.get_users([faculty_id])
    u = users.get(faculty_id)
    if not u or u.kind != "faculty":
        raise BadRequestError(
            f"Club Faculty Councillor {faculty_id} must reference a valid faculty member.",
            code="invalid_faculty_councillor",
        )


@transaction.atomic
def create_club(
    *,
    name: str,
    category: str,
    description: str,
    coordinator_id: int,
    co_coordinator_id: int,
    faculty_councillor_id: int,
) -> Club:
    if category not in CLUB_CATEGORIES:
        raise BadRequestError(
            f"Club category must be one of {', '.join(CLUB_CATEGORIES)}.",
            code="invalid_club_category",
        )
    _validate_students([coordinator_id, co_coordinator_id])
    _validate_faculty(faculty_councillor_id)

    if Club.objects.filter(name=name).exists():
        raise ConflictError(
            f"A club named {name!r} already exists.",
            code="club_name_conflict",
        )

    club = Club.objects.create(
        name=name,
        category=category,
        description=description,
        faculty_councillor_id=faculty_councillor_id,
        status=STATUS_OPEN,
    )

    ClubLeadership.objects.create(
        club=club,
        student_id=coordinator_id,
        role=ROLE_COORDINATOR,
        is_current=True,
    )
    ClubLeadership.objects.create(
        club=club,
        student_id=co_coordinator_id,
        role=ROLE_CO_COORDINATOR,
        is_current=True,
    )

    return club


@transaction.atomic
def confirm_club(club_id: int) -> Club:
    club = Club.objects.select_for_update().filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    try:
        new_status = transition_club(club.status, "confirm")
    except ValueError as e:
        raise ConflictError(str(e), code="illegal_club_transition") from e

    club.status = new_status
    club.save(update_fields=["status", "updated_at"])
    return club
