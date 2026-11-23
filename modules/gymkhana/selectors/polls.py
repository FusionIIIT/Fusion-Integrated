"""Poll read selectors for Gymkhana."""

from __future__ import annotations

import datetime

from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain.constants import POLL_STATUS_ACTIVE
from modules.gymkhana.models.poll import Poll, PollVote


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
    for t in targets:
        match_batch = t.batch.lower() == "all" or (batch and t.batch.lower() == batch.lower())
        match_branch = t.branch.lower() == "all" or (branch and t.branch.lower() == branch.lower())
        if match_batch and match_branch:
            return True
    return False


def list_active_polls_for_student(
    batch: str | None = None,
    branch: str | None = None,
    now: datetime.datetime | None = None,
) -> QuerySet[Poll]:
    """Return active polls that have not expired."""
    current_time = now or datetime.datetime.now(datetime.UTC)
    qs = (
        Poll.objects.filter(status=POLL_STATUS_ACTIVE, expires_at__gt=current_time)
        .select_related("club")
        .prefetch_related("choices", "target_groups")
    )
    if not batch and not branch:
        return qs
    # Filter in Python or via target groups
    target_q = Q(target_groups__batch__iexact="all")
    if batch:
        target_q |= Q(target_groups__batch__iexact=batch)
    branch_q = Q(target_groups__branch__iexact="all")
    if branch:
        branch_q |= Q(target_groups__branch__iexact=branch)
    return qs.filter(target_q & branch_q).distinct()
