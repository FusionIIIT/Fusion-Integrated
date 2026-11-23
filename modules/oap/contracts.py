"""OAP's public surface for other modules. Plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.oap.domain import no_dues as nd
from modules.oap.models import NoDuesCase


@dataclass(frozen=True)
class NoDuesStatusDTO:
    user_id: int
    status: str
    finalized: bool


def get_no_dues_status(user_ids: Sequence[int]) -> dict[int, NoDuesStatusDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    latest: dict[int, NoDuesCase] = {}
    for case in NoDuesCase.objects.filter(user_id__in=ids).order_by("-created_at"):
        latest.setdefault(case.user_id, case)
    out: dict[int, NoDuesStatusDTO] = {}
    for uid, case in latest.items():
        results = dict(case.results.values_list("domain", "result"))
        status = nd.derive_status(results, finalized=case.finalized)
        out[uid] = NoDuesStatusDTO(uid, status, case.finalized)
    return out
