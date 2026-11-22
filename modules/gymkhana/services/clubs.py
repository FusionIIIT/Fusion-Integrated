"""Club establishment and confirmation (BW-GYM-03: UC-GYM-001, UC-GYM-011)."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.domain.rules import RuleViolation
from modules.gymkhana.models import Club, LeadershipAssignment
from modules.gymkhana.services import audit, people
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused

P_CREATE = "gymkhana.club.create"
P_APPROVE = "gymkhana.club.approve"

_NAME_TAKEN = "A club with this name already exists. Choose a different name."


def _required_text(value: str, field: str, label: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainError(f"Enter the club's {label}.", code="missing_field",
                          details=[{"field": field, "message": f"Enter the {label}."}])
    return text


def create_club(*, actor, name: str, category: str, description: str,
                coordinator_user_id: int, co_coordinator_user_id: int,
                faculty_councillor_user_id: int) -> Club:
    """UC-GYM-001: a new club, open, with its two student leaders and councillor."""
    require(actor, P_CREATE)
    sm.resolve(sm.CLUB, sm.NONE, sm.CREATE, sm.STUDENT_ADMIN)
    name = _required_text(name, "name", "name")
    description = _required_text(description, "description", "description")
    try:
        category = rules.check_category(category)
        rules.check_distinct_leaders(coordinator_user_id, co_coordinator_user_id)
    except RuleViolation as exc:
        raise refused(exc) from exc
    # BR-GYM-001 and BR-GYM-002, reported together so every bad field is named at once.
    problems = []
    for check, fields in (
            (people.require_students, {"coordinator_user_id": coordinator_user_id,
                                       "co_coordinator_user_id": co_coordinator_user_id}),
            (people.require_faculty,
             {"faculty_councillor_user_id": faculty_councillor_user_id})):
        try:
            check(fields)
        except DomainError as exc:
            problems.extend(exc.details)
    if problems:
        raise DomainError("Some of the selected people are not valid for their role. "
                          "Correct the highlighted fields.", code="invalid_assignment",
                          details=problems)
    if Club.objects.filter(name__iexact=name).exists():
        raise ConflictError(_NAME_TAKEN, code="club_name_taken")
    try:
        with transaction.atomic():
            now = timezone.now()
            club = Club.objects.create(
                name=name, category=category, description=description,
                status=sm.OPEN, faculty_councillor_user_id=faculty_councillor_user_id,
                created_by_user_id=actor.user_id)
            LeadershipAssignment.objects.bulk_create([
                LeadershipAssignment(club=club, user_id=uid, role=role, valid_from=now,
                                     assigned_by_user_id=actor.user_id)
                for role, uid in ((LeadershipAssignment.COORDINATOR, coordinator_user_id),
                                  (LeadershipAssignment.CO_COORDINATOR,
                                   co_coordinator_user_id))])
            audit.record("club.created", object_type="club", object_id=club.pk,
                         actor=actor, club_id=club.pk, status=sm.OPEN)
    except IntegrityError as exc:
        # Two requests racing for one name; the database decided.
        raise ConflictError(_NAME_TAKEN, code="club_name_taken") from exc
    return club


@transaction.atomic
def approve_club(*, actor, club_id: int) -> Club:
    """UC-GYM-011: an open club becomes confirmed; nothing else may move."""
    require(actor, P_APPROVE)
    club = Club.objects.select_for_update().filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("No such club.")
    try:
        t = sm.resolve(sm.CLUB, club.status, sm.APPROVE, sm.STUDENT_ADMIN)
    except sm.InvalidTransition as exc:
        raise ConflictError("This club is already confirmed.",
                            code="club_already_confirmed") from exc
    club.status = t.to
    club.approved_by_user_id = actor.user_id
    club.approved_at = timezone.now()
    club.save(update_fields=["status", "approved_by_user_id", "approved_at", "updated_at"])
    audit.record("club.approved", object_type="club", object_id=club.pk, actor=actor,
                 club_id=club.pk, status=t.to)
    return club
