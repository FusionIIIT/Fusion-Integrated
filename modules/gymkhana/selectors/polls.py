"""Poll reads: tallies are counted, never stored (AFR-GYM-028)."""
from __future__ import annotations

from collections.abc import Sequence

from django.db.models import Count

from modules.gymkhana.models import Vote


def tallies(poll_ids: Sequence[int]) -> dict[int, dict[int, int]]:
    """{poll_id: {choice_id: votes}} in one grouped query."""
    out: dict[int, dict[int, int]] = {}
    rows = (Vote.objects.filter(poll_id__in=list(poll_ids))
            .values("poll_id", "choice_id").annotate(n=Count("id")))
    for row in rows:
        out.setdefault(row["poll_id"], {})[row["choice_id"]] = row["n"]
    return out


def own_votes(user_id: int, poll_ids: Sequence[int]) -> dict[int, int]:
    """{poll_id: choice_id} for this student only."""
    return dict(Vote.objects.filter(user_id=user_id, poll_id__in=list(poll_ids))
                .values_list("poll_id", "choice_id"))
