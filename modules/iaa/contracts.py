"""iaa's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count

from modules.iaa.domain import state_machine as sm
from modules.iaa.models import AuditObservation, FinancialRecord


@dataclass(frozen=True)
class OpenItemsDTO:
    user_id: int
    open_records: int
    open_observations: int


def get_open_item_counts(user_ids: Sequence[int]) -> dict[int, OpenItemsDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    records = dict(FinancialRecord.objects.filter(user_id__in=ids)
                   .exclude(status__in=sm.RECORD_TERMINAL)
                   .values("user_id").annotate(n=Count("id")).values_list("user_id", "n"))
    observations = dict(AuditObservation.objects.filter(respondent_user_id__in=ids)
                        .exclude(status=sm.OBS_CLOSED)
                        .values("respondent_user_id").annotate(n=Count("id"))
                        .values_list("respondent_user_id", "n"))
    return {uid: OpenItemsDTO(uid, records.get(uid, 0), observations.get(uid, 0)) for uid in ids}
