"""Club governance services (UC-GYM-001, UC-GYM-011, UC-GYM-008)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.directory import contracts as directory
from modules.gymkhana.domain.state_machine import ClubEstablishmentStateMachine
from modules.gymkhana.models import Club, ClubLeadershipHistory

if TYPE_CHECKING:
    from fusion_auth.principal import Principal


def create_club(
    *,
    name: str,
    category: str,
    description: str,
    coordinator_id: int,
    co_coordinator_id: int,
    faculty_councillor_id: int,
    changed_by_user_id: int,
) -> Club:
    """Create a new club in 'open' state with validated student/faculty leadership (UC-GYM-001)."""
    if coordinator_id == co_coordinator_id:
        raise BadRequestError(
            "Coordinator and co-coordinator must be distinct students.",
            code="duplicate_coordinators",
        )

    users = directory.get_users([coordinator_id, co_coordinator_id, faculty_councillor_id])
    coord = users.get(coordinator_id)
    co_coord = users.get(co_coordinator_id)
    faculty = users.get(faculty_councillor_id)

    if not coord or coord.kind != "student":
        raise BadRequestError(
            f"User {coordinator_id} is not a valid student.",
            code="invalid_coordinator",
        )
    if not co_coord or co_coord.kind != "student":
        raise BadRequestError(
            f"User {co_coordinator_id} is not a valid student.",
            code="invalid_co_coordinator",
        )
    if not faculty or faculty.kind != "faculty":
        raise BadRequestError(
            f"User {faculty_councillor_id} is not a valid faculty member.",
            code="invalid_faculty_councillor",
        )

    if category not in ("Technical", "Sports", "Cultural"):
        raise BadRequestError(
            f"Category must be Technical, Sports, or Cultural (got {category!r}).",
            code="invalid_category",
        )

    initial_status = ClubEstablishmentStateMachine.transition(None, "create", "student_admin")

    try:
        with transaction.atomic():
            club = Club.objects.create(
                name=name,
                category=category,
                description=description,
                coordinator_id=coordinator_id,
                co_coordinator_id=co_coordinator_id,
                faculty_councillor_id=faculty_councillor_id,
                status=initial_status,
            )
            ClubLeadershipHistory.objects.create(
                club=club,
                coordinator_id=coordinator_id,
                co_coordinator_id=co_coordinator_id,
                effective_from=timezone.now(),
                effective_to=None,
                changed_by_user_id=changed_by_user_id,
            )
            return club
    except IntegrityError as exc:
        raise ConflictError(
            f"A club with name {name!r} already exists.",
            code="club_name_exists",
        ) from exc


def approve_club(
    *,
    club_id: int,
    actor: Principal | None = None,
    actor_user_id: int | None = None,
) -> Club:
    """Approve an open club to confirmed state (UC-GYM-011, BR-GYM-004)."""
    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    if not actor.has_permission("gymkhana.club.approve"):
        raise PermissionDeniedError(
            "This action requires gymkhana.club.approve.",
            code="permission_denied",
        )

    if actor_user_id is None:
        actor_user_id = actor.user_id

    with transaction.atomic():
        try:
            club = Club.objects.select_for_update().get(pk=club_id)
        except Club.DoesNotExist as exc:
            raise NotFoundError(f"Club {club_id} not found.", code="club_not_found") from exc

        new_status = ClubEstablishmentStateMachine.transition(
            club.status, "approve", "student_admin"
        )
        club.status = new_status
        club.save(update_fields=["status", "updated_at"])
        return club


def change_leadership(
    *,
    club: Club,
    new_coordinator_id: int,
    new_co_coordinator_id: int,
    changed_by_user_id: int,
) -> Club:
    """Replace club coordinators, retiring active tenure in history (UC-GYM-008, BR-GYM-016)."""
    if changed_by_user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may change leadership.",
            code="not_club_head",
        )

    if new_coordinator_id == new_co_coordinator_id:
        raise BadRequestError(
            "Coordinator and co-coordinator must be distinct students.",
            code="duplicate_coordinators",
        )

    users = directory.get_users([new_coordinator_id, new_co_coordinator_id])
    coord = users.get(new_coordinator_id)
    co_coord = users.get(new_co_coordinator_id)

    if not coord or coord.kind != "student":
        raise BadRequestError(
            f"User {new_coordinator_id} is not a valid student.",
            code="invalid_coordinator",
        )
    if not co_coord or co_coord.kind != "student":
        raise BadRequestError(
            f"User {new_co_coordinator_id} is not a valid student.",
            code="invalid_co_coordinator",
        )

    now = timezone.now()
    with transaction.atomic():
        locked_club = Club.objects.select_for_update().get(pk=club.pk)

        # 1. Close current active row (BR-GYM-016)
        ClubLeadershipHistory.objects.filter(
            club=locked_club, effective_to__isnull=True
        ).update(effective_to=now)

        # 2. Insert new tenure row
        ClubLeadershipHistory.objects.create(
            club=locked_club,
            coordinator_id=new_coordinator_id,
            co_coordinator_id=new_co_coordinator_id,
            effective_from=now,
            effective_to=None,
            changed_by_user_id=changed_by_user_id,
        )

        # 3. Update Club row
        locked_club.coordinator_id = new_coordinator_id
        locked_club.co_coordinator_id = new_co_coordinator_id
        locked_club.save(update_fields=["coordinator_id", "co_coordinator_id", "updated_at"])
        return locked_club
