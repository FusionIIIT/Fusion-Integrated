"""Club management services for Gymkhana."""

from __future__ import annotations

from collections.abc import Sequence

from django.db import IntegrityError, transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import CLUB_STATUS_OPEN
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.state_machines import transition_club
from modules.gymkhana.domain.validation import (
    validate_club_category,
    validate_distinct_leaders,
)
from modules.gymkhana.models.club import Club, ClubLeadershipHistory
from modules.gymkhana.selectors.scoping import is_club_head


def _verify_student_leaders(coordinator_id: int, co_coordinator_id: int) -> None:
    """Both leaders are valid students (BR-GYM-001, AFR-GYM-002, AFR-GYM-008)."""
    try:
        validate_distinct_leaders(coordinator_id, co_coordinator_id)
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc
    users = get_users([coordinator_id, co_coordinator_id])
    coord = users.get(coordinator_id)
    co_coord = users.get(co_coordinator_id)
    if not coord or coord.kind != "student":
        raise BadRequestError(f"User {coordinator_id} is not a valid student.")
    if not co_coord or co_coord.kind != "student":
        raise BadRequestError(f"User {co_coordinator_id} is not a valid student.")


def _verify_faculty_councillor(faculty_councillor_id: int) -> None:
    """The councillor is a valid faculty member (BR-GYM-002, AFR-GYM-003)."""
    users = get_users([faculty_councillor_id])
    councillor = users.get(faculty_councillor_id)
    if not councillor or councillor.kind != "faculty":
        raise BadRequestError(f"User {faculty_councillor_id} is not a valid faculty member.")


@transaction.atomic
def create_club(
    *,
    name: str,
    category: str,
    description: str,
    coordinator_id: int,
    co_coordinator_id: int,
    faculty_councillor_id: int,
    creator_id: int,
) -> Club:
    """Create an open club (UC-GYM-001, CFR-GYM-001, AFR-GYM-001, AFR-GYM-005)."""
    try:
        norm_category = validate_club_category(category)
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc
    _verify_student_leaders(coordinator_id, co_coordinator_id)
    _verify_faculty_councillor(faculty_councillor_id)

    if Club.objects.filter(name__iexact=name.strip()).exists():
        raise ConflictError(f"A club with name '{name.strip()}' already exists.")

    try:
        with transaction.atomic():
            club = Club.objects.create(
                name=name.strip(),
                category=norm_category,
                description=description.strip(),
                coordinator_id=coordinator_id,
                co_coordinator_id=co_coordinator_id,
                faculty_councillor_id=faculty_councillor_id,
                status=CLUB_STATUS_OPEN,
            )
    except IntegrityError as exc:
        raise ConflictError(f"A club with name '{name.strip()}' already exists.") from exc
    ClubLeadershipHistory.objects.create(
        club=club,
        coordinator_id=coordinator_id,
        co_coordinator_id=co_coordinator_id,
        changed_by_id=creator_id,
    )
    return club


@transaction.atomic
def approve_club(*, club_id: int, approver_id: int, roles: Sequence[str]) -> Club:
    """Confirm an open club (UC-GYM-011, BR-GYM-004, AFR-GYM-006, BW-GYM-03)."""
    if "student_admin" not in roles:
        raise PermissionDeniedError("Only Student Admin can approve and confirm clubs.")

    club = Club.objects.select_for_update().filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    try:
        new_status = transition_club(club.status, "CONFIRM", "student_admin")
    except DomainError as exc:
        raise ConflictError(str(exc)) from exc

    club.status = new_status
    club.save(update_fields=["status", "updated_at"])
    return club


@transaction.atomic
def change_leadership(
    *,
    club_id: int,
    actor_id: int,
    new_coordinator_id: int,
    new_co_coordinator_id: int,
) -> Club:
    """Replace both leaders (UC-GYM-008, CFR-GYM-002, AFR-GYM-007, AFR-GYM-009, BR-GYM-016)."""
    club = Club.objects.select_for_update().filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError(
            "Only the active coordinator or co-coordinator can change club leadership."
        )

    _verify_student_leaders(new_coordinator_id, new_co_coordinator_id)

    club.coordinator_id = new_coordinator_id
    club.co_coordinator_id = new_co_coordinator_id
    club.save(update_fields=["coordinator_id", "co_coordinator_id", "updated_at"])

    ClubLeadershipHistory.objects.create(
        club=club,
        coordinator_id=new_coordinator_id,
        co_coordinator_id=new_co_coordinator_id,
        changed_by_id=actor_id,
    )
    return club
