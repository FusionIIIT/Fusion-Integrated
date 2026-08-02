"""placement's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.placement.models import Application


@dataclass(frozen=True)
class PlacementStatusDTO:
    user_id: int
    is_placed: bool
    accepted_count: int


def get_placement_status(user_ids: Sequence[int],
                         placement_year: str) -> dict[int, PlacementStatusDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (Application.objects
            .filter(user_id__in=ids, posting__placement_year=placement_year,
                    status="offer_accepted")
            .values_list("user_id", flat=True))
    counts: dict[int, int] = {}
    for uid in rows:
        counts[uid] = counts.get(uid, 0) + 1
    return {uid: PlacementStatusDTO(uid, counts.get(uid, 0) > 0, counts.get(uid, 0))
            for uid in ids}
