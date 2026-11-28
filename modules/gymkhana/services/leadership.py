"""Leadership change (UC-GYM-008, BR-GYM-016): old assignments end, new ones start, together."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation
from modules.gymkhana.models import Club, LeadershipAssignment
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import audit, people
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused
from modules.gymkhana.services.inputs import NOT_LED

P_ASSIGN = "gymkhana.leadership.assign"


@transaction.atomic
def change_leadership(*, actor, club_id: int, coordinator_user_id: int,
                      co_coordinator_user_id: int) -> dict[str, int]:
    """Returns the club's current leaders as {role: user_id}."""
    require(actor, P_ASSIGN)
    club = (Club.objects.select_for_update()
            .filter(pk=club_id, pk__in=scoping.led_clubs(actor).values("pk")).first())
    if club is None:
        raise NotFoundError(NOT_LED)
    try:
        rules.check_distinct_leaders(coordinator_user_id, co_coordinator_user_id)
    except RuleViolation as exc:
        raise refused(exc) from exc
    people.require_students({"coordinator_user_id": coordinator_user_id,
                             "co_coordinator_user_id": co_coordinator_user_id})

    wanted = {LeadershipAssignment.COORDINATOR: coordinator_user_id,
              LeadershipAssignment.CO_COORDINATOR: co_coordinator_user_id}
    current = {a.role: a for a in scoping.current_leaders().filter(club=club)}
    changing = [role for role, uid in wanted.items()
                if role not in current or current[role].user_id != uid]
    if not changing:
        return wanted
    now = timezone.now()
    # Ended first, so a swap of the two leaders never trips the one-seat-per-person index.
    LeadershipAssignment.objects.filter(
        pk__in=[current[r].pk for r in changing if r in current]).update(
        valid_to=now, updated_at=now)
    LeadershipAssignment.objects.bulk_create([
        LeadershipAssignment(club=club, user_id=wanted[role], role=role, valid_from=now,
                             assigned_by_user_id=actor.user_id)
        for role in changing])
    audit.record("leadership.changed", object_type="club", object_id=club.pk,
                 actor=actor, club_id=club.pk,
                 ended=[current[r].user_id for r in changing if r in current],
                 started=[wanted[r] for r in changing])
    return wanted
