"""Poll services (UC-GYM-006, UC-GYM-007, BW-GYM-02)."""
from __future__ import annotations

import datetime
from collections.abc import Sequence

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.directory import contracts as directory
from modules.gymkhana.domain.polls import (
    is_student_targeted,
    validate_poll_choices,
    validate_poll_vote_choice,
)
from modules.gymkhana.domain.state_machine import PollStateMachine
from modules.gymkhana.models import Club, Poll, PollChoice, PollTarget, PollVote
from modules.gymkhana.services import notifications


def create_poll(
    *,
    club: Club,
    title: str,
    description: str,
    expires_at: datetime.datetime,
    choices: Sequence[str],
    targets: Sequence[dict],
    user_id: int,
) -> Poll:
    """Create a new voting poll with choices and targeted student groups (UC-GYM-006)."""
    if user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may create polls.",
            code="not_club_head",
        )

    if expires_at <= timezone.now():
        raise BadRequestError(
            "Poll expiration time must be in the future.",
            code="invalid_expiry_time",
        )

    cleaned_choices = validate_poll_choices(choices)

    if not targets:
        raise BadRequestError(
            "At least one target group must be specified for the poll.",
            code="empty_targets",
        )

    initial_status = PollStateMachine.transition(None, "create", "club_head")

    with transaction.atomic():
        poll = Poll.objects.create(
            club=club,
            title=title,
            description=description,
            expires_at=expires_at,
            status=initial_status,
            created_by_user_id=user_id,
        )
        for choice_text in cleaned_choices:
            PollChoice.objects.create(poll=poll, text=choice_text)

        for target in targets:
            batch_year = target.get("batch_year")
            if not batch_year:
                raise BadRequestError(
                    "Each poll target must specify a batch_year.",
                    code="target_missing_batch_year",
                )
            discipline = (target.get("discipline") or "all").strip()
            PollTarget.objects.create(
                poll=poll,
                batch_year=int(batch_year),
                discipline=discipline,
            )

        notifications.send_poll_created_notification(poll)
        return poll


def cast_vote(*, poll: Poll, choice_id: int, student_id: int) -> PollVote:
    """Record student vote verifying targeting and preventing duplicates (UC-GYM-007)."""
    now = timezone.now()
    if poll.status != "active" or poll.expires_at <= now:
        raise ConflictError(
            "This poll is no longer active or has expired.",
            code="poll_not_active",
        )

    users = directory.get_users([student_id])
    student = users.get(student_id)
    if not student or student.kind != "student":
        raise BadRequestError(
            f"User {student_id} is not an eligible student.",
            code="invalid_student",
        )

    target_dicts = list(poll.targets.values("batch_year", "discipline"))
    if not is_student_targeted(student.batch_year, student.discipline, target_dicts):
        raise ConflictError(
            "You are not in the targeted audience for this poll.",
            code="student_not_targeted",
        )

    try:
        choice = PollChoice.objects.get(pk=choice_id)
    except PollChoice.DoesNotExist as exc:
        msg = f"Poll choice {choice_id} not found."
        raise BadRequestError(msg, code="choice_not_found") from exc

    validate_poll_vote_choice(poll.id, choice.poll_id)

    try:
        with transaction.atomic():
            return PollVote.objects.create(
                poll=poll,
                choice=choice,
                student_id=student_id,
            )
    except IntegrityError as exc:
        raise ConflictError(
            "You have already voted in this poll.",
            code="duplicate_vote",
        ) from exc
