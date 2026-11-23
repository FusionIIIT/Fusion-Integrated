"""Voting poll services for Gymkhana."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from django.db import transaction
from django.db.models import F

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.gymkhana.domain.constants import (
    CLUB_STATUS_CONFIRMED,
    POLL_STATUS_ACTIVE,
    POLL_STATUS_EXPIRED,
)
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import (
    validate_poll_active,
    validate_poll_choices,
    validate_target_groups,
)
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.poll import (
    Poll,
    PollChoice,
    PollTargetGroup,
    PollVote,
)
from modules.gymkhana.selectors.polls import is_student_targeted
from modules.gymkhana.selectors.scoping import is_club_head
from modules.gymkhana.services.notifications import announce_poll


@transaction.atomic
def create_poll(
    *,
    club_id: int,
    actor_id: int,
    title: str,
    description: str,
    expires_at: datetime.datetime,
    choices: Sequence[str],
    target_groups: Sequence[tuple[str, str]],  # (batch, branch)
) -> Poll:
    """Create a targeted poll (UC-GYM-006, CFR-GYM-005, AFR-GYM-023, BW-GYM-02)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError("Only the active Club Head can create voting polls.")

    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError("Voting polls can only be created for confirmed clubs.")

    now = datetime.datetime.now(datetime.UTC)
    if expires_at <= now:
        raise BadRequestError("Poll expiration date must be in the future.")

    try:
        clean_choices = validate_poll_choices(choices)
        clean_groups = validate_target_groups(target_groups)
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc

    poll = Poll.objects.create(
        club=club,
        created_by_id=actor_id,
        title=title.strip(),
        description=description.strip(),
        expires_at=expires_at,
        status=POLL_STATUS_ACTIVE,
    )

    PollChoice.objects.bulk_create(
        [PollChoice(poll=poll, choice_text=text) for text in clean_choices]
    )
    PollTargetGroup.objects.bulk_create(
        [PollTargetGroup(poll=poll, batch=batch, branch=branch) for batch, branch in clean_groups]
    )
    announce_poll(poll)
    return poll


@transaction.atomic
def cast_vote(
    *,
    poll_id: int,
    student_id: int,
    choice_id: int,
    student_batch: str | None = None,
    student_branch: str | None = None,
) -> PollVote:
    """Record one vote and its tally (UC-GYM-007, AFR-GYM-027, AFR-GYM-028, BR-GYM-015)."""
    poll = (
        Poll.objects.select_for_update()
        .prefetch_related("target_groups")
        .filter(id=poll_id)
        .first()
    )
    if not poll:
        raise NotFoundError(f"Poll {poll_id} not found.")

    if poll.status != POLL_STATUS_ACTIVE:
        raise BadRequestError("Voting is only allowed on active polls.")

    now = datetime.datetime.now(datetime.UTC)
    try:
        validate_poll_active(poll.expires_at, now)
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc

    if not is_student_targeted(poll, student_batch, student_branch):
        raise PermissionDeniedError("You are not in the target group for this poll.")

    if PollVote.objects.filter(poll=poll, student_id=student_id).exists():
        raise ConflictError("You have already cast a vote in this poll.")

    choice = PollChoice.objects.select_for_update().filter(id=choice_id, poll=poll).first()
    if not choice:
        raise NotFoundError(f"Choice {choice_id} does not belong to this poll.")

    vote = PollVote.objects.create(
        poll=poll,
        student_id=student_id,
        choice=choice,
    )
    choice.vote_count = F("vote_count") + 1
    choice.save(update_fields=["vote_count"])
    return vote


def expire_overdue_polls() -> int:
    """Close voting polls that have passed expiration date."""
    now = datetime.datetime.now(datetime.UTC)
    return Poll.objects.filter(status=POLL_STATUS_ACTIVE, expires_at__lte=now).update(
        status=POLL_STATUS_EXPIRED
    )
