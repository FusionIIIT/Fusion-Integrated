from datetime import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.directory import contracts as directory_contracts
from modules.gymkhana.domain.validation import validate_poll_choices
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.poll import PollChoice, PollVote, VotingPoll
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def create_poll(
    *,
    club_id: int,
    acting_user_id: int,
    title: str,
    description: str,
    target_batches: list[str],
    target_branches: list[str],
    expires_at: datetime,
    choices: list[str],
) -> VotingPoll:
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if not is_club_head(acting_user_id, club_id):
        raise PermissionDeniedError(
            "Only the applicable club coordinator or co-coordinator may create voting polls.",
            code="not_club_head",
        )

    try:
        validate_poll_choices(choices)
    except ValueError as e:
        raise BadRequestError(str(e), code="invalid_poll_choices") from e

    poll = VotingPoll.objects.create(
        club=club,
        title=title,
        description=description,
        target_batches=target_batches,
        target_branches=target_branches,
        expires_at=expires_at,
        created_by_id=acting_user_id,
    )

    for choice_text in choices:
        PollChoice.objects.create(
            poll=poll,
            text=choice_text.strip(),
            votes_count=0,
        )

    return poll


@transaction.atomic
def cast_vote(*, poll_id: int, student_id: int, choice_id: int) -> PollVote:
    poll = VotingPoll.objects.select_for_update().filter(id=poll_id).first()
    if not poll:
        raise NotFoundError("Poll not found.", code="poll_not_found")

    if timezone.now() >= poll.expires_at:
        raise ConflictError("Voting poll has expired.", code="poll_expired")

    if PollVote.objects.filter(poll=poll, student_id=student_id).exists():
        raise ConflictError(
            "A student may cast at most one vote in the same poll.",
            code="duplicate_vote",
        )

    # Targeting validation
    users = directory_contracts.get_users([student_id])
    user = users.get(student_id)
    if user and user.kind != "student":
        raise PermissionDeniedError("Only valid students may vote in polls.", code="not_student")

    if user:
        if (
            poll.target_batches
            and user.batch_year
            and str(user.batch_year) not in poll.target_batches
        ):
            raise PermissionDeniedError(
                "You are not in the targeted batch for this poll.", code="not_targeted"
            )
        if poll.target_branches and user.discipline and user.discipline not in poll.target_branches:
            raise PermissionDeniedError(
                "You are not in the targeted branch for this poll.", code="not_targeted"
            )

    choice = PollChoice.objects.select_for_update().filter(id=choice_id, poll=poll).first()
    if not choice:
        raise NotFoundError(
            "Selected poll choice does not belong to this poll.", code="choice_not_found"
        )

    vote = PollVote.objects.create(
        poll=poll,
        choice=choice,
        student_id=student_id,
    )

    choice.votes_count = F("votes_count") + 1
    choice.save(update_fields=["votes_count"])

    return vote
