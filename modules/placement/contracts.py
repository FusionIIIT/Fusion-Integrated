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


@dataclass(frozen=True)
class NoDuesClearanceDTO:
    """Rule 24, for whoever issues the certificate.

    `blocking` names each company still owing a signed offer letter, so the
    academic office can tell a student what to do instead of just refusing.
    """

    user_id: int
    cleared: bool
    blocking: tuple[str, ...]
    message: str


def get_no_dues_clearances(user_ids: Sequence[int]
                           ) -> dict[int, NoDuesClearanceDTO]:
    """Whether placement blocks a no-dues certificate (rule 24).

    Plural because the academic office checks a graduating batch, not a person.
    A student with no placement is cleared — the rule only bites on the placed.
    """
    from modules.placement.services import clearance

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    return {
        uid: NoDuesClearanceDTO(uid, verdict.cleared, verdict.blocking,
                                verdict.message)
        for uid, verdict in clearance.no_dues_clearances(ids).items()
    }
