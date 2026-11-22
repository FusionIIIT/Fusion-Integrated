"""Targeted polls (BW-GYM-02: UC-GYM-006, UC-GYM-007)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation, Target
from modules.gymkhana.models import Poll, PollChoice, PollTarget, Vote
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import audit, notifications, people
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused

P_CREATE = "gymkhana.poll.create"
P_VOTE = "gymkhana.vote.create"

_ALREADY_VOTED = "You have already voted in this poll. Your vote is unchanged."


def _text(value: str, field: str, message: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainError(message, code="missing_field",
                          details=[{"field": field, "message": message}])
    return text


@transaction.atomic
def create_poll(*, actor, club_id: int, title: str, description: str, expires_on: date,
                choices: Sequence[str], targets: Sequence[Target]) -> Poll:
    require(actor, P_CREATE)
    club = scoping.led_clubs(actor).filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("No such club among the clubs you lead.")
    title = _text(title, "title", "Enter the poll's title.")
    description = _text(description, "description", "Describe what the poll is about.")
    try:
        labels = rules.check_choices(choices)
        groups = rules.check_targets(targets)
        rules.check_expiry(expires_on, timezone.localdate())
    except RuleViolation as exc:
        raise refused(exc) from exc
    poll = Poll.objects.create(club=club, title=title, description=description,
                               expires_on=expires_on, created_by_user_id=actor.user_id)
    PollChoice.objects.bulk_create(
        [PollChoice(poll=poll, label=label, position=i) for i, label in enumerate(labels)])
    PollTarget.objects.bulk_create(
        [PollTarget(poll=poll, batch_year=g.batch_year, discipline=g.discipline)
         for g in groups])
    audit.record("poll.created", object_type="poll", object_id=poll.pk, actor=actor,
                 club_id=club.pk, choices=len(labels), targets=len(groups))
    # AFR-GYM-025: one broadcast row, expanded to the audience by the drain.
    notifications.enqueue(
        topic=notifications.POLL_CREATED, dedupe_key=f"poll.created:{poll.pk}",
        subject=f"{club.name}: new poll \"{title}\"",
        body=f"{club.name} has opened a poll, \"{title}\", until {expires_on:%d %b %Y}.",
        is_broadcast=True, payload={"poll_id": poll.pk, "club_id": club.pk})
    return poll


def cast_vote(*, actor, poll_id: int, choice_id: int) -> Vote:
    """UC-GYM-007: one vote, by a targeted student, in an unexpired poll."""
    require(actor, P_VOTE)
    batch_year, discipline = people.cohort_of(actor.user_id)
    # Not in the audience: the poll is not theirs to see (BR-GYM-013), so not found.
    poll = scoping.polls_targeting(batch_year, discipline).filter(pk=poll_id).first()
    if poll is None:
        raise NotFoundError("No such poll is open to you.")
    if not rules.poll_is_active(poll.expires_on, timezone.localdate()):
        raise ConflictError("This poll has closed. Votes are no longer accepted.",
                            code="poll_closed")
    choice = PollChoice.objects.filter(pk=choice_id, poll=poll).first()
    if choice is None:
        raise DomainError("Choose one of this poll's choices.", code="invalid_choice",
                          details=[{"field": "choice_id", "message": "Not a choice "
                                                                     "of this poll."}])
    if Vote.objects.filter(poll=poll, user_id=actor.user_id).exists():
        raise ConflictError(_ALREADY_VOTED, code="already_voted")
    try:
        with transaction.atomic():
            vote = Vote.objects.create(poll=poll, choice=choice, user_id=actor.user_id)
            # The choice is left out, so the trail cannot be read as a ballot.
            audit.record("vote.cast", object_type="poll", object_id=poll.pk,
                         actor=actor, club_id=poll.club_id)
    except IntegrityError as exc:
        raise ConflictError(_ALREADY_VOTED, code="already_voted") from exc
    return vote
