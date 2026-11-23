"""Poll read selectors for Gymkhana."""

from __future__ import annotations

import datetime

from django.db.models import Exists, OuterRef, Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain.constants import ALL_GROUPS, POLL_STATUS_ACTIVE
from modules.gymkhana.models.poll import Poll, PollTargetGroup, PollVote


def get_poll_by_id(poll_id: int) -> Poll:
    """Return poll with choices and target groups or raise NotFound."""
    poll = (
        Poll.objects.filter(id=poll_id)
        .prefetch_related("choices", "target_groups")
        .select_related("club")
        .first()
    )
    if not poll:
        raise NotFoundError(f"Poll {poll_id} not found.")
    return poll


def student_has_voted(poll_id: int, student_id: int) -> bool:
    """Check if student already voted in this poll (BR-GYM-015)."""
    return PollVote.objects.filter(poll_id=poll_id, student_id=student_id).exists()


def is_student_targeted(poll: Poll, batch: str | None, branch: str | None) -> bool:
    """Check whether a student's batch and branch match poll target groups (BR-GYM-013)."""
    targets = poll.target_groups.all()
    if not targets:
        return True

    def matches(selected: str, own: str | None) -> bool:
        wanted = selected.lower()
        return wanted == ALL_GROUPS or (own is not None and wanted == own.lower())

    return any(matches(t.batch, batch) and matches(t.branch, branch) for t in targets)


def _targets(batch: str | None, branch: str | None) -> Q:
    """One group of the poll matches on batch and branch together (BR-GYM-013)."""
    batch_q, branch_q = Q(batch__iexact=ALL_GROUPS), Q(branch__iexact=ALL_GROUPS)
    if batch:
        batch_q |= Q(batch__iexact=batch)
    if branch:
        branch_q |= Q(branch__iexact=branch)
    groups = PollTargetGroup.objects.filter(poll=OuterRef("pk"))
    return Q(Exists(groups.filter(batch_q, branch_q))) | ~Q(Exists(groups))


def list_active_polls_for_student(
    batch: str | None = None,
    branch: str | None = None,
    now: datetime.datetime | None = None,
) -> QuerySet[Poll]:
    """Active, unexpired polls addressed to this batch and branch (BR-GYM-014)."""
    current_time = now or datetime.datetime.now(datetime.UTC)
    return (
        Poll.objects.filter(
            _targets(batch, branch), status=POLL_STATUS_ACTIVE, expires_at__gt=current_time
        )
        .select_related("club")
        .prefetch_related("choices", "target_groups")
    )


def polls_for(
    user_id: int,
    batch: str | None,
    branch: str | None,
    now: datetime.datetime | None = None,
) -> QuerySet[Poll]:
    """Polls addressed to this person and active, or their own club's (AFR-GYM-026, BR-GYM-014)."""
    current_time = now or datetime.datetime.now(datetime.UTC)
    votable = Q(status=POLL_STATUS_ACTIVE, expires_at__gt=current_time) & _targets(batch, branch)
    heads = Q(club__coordinator_id=user_id) | Q(club__co_coordinator_id=user_id)
    return (
        Poll.objects.filter(votable | heads)
        .select_related("club")
        .prefetch_related("choices", "target_groups")
        .annotate(voted=Exists(PollVote.objects.filter(poll=OuterRef("pk"), student_id=user_id)))
    )
