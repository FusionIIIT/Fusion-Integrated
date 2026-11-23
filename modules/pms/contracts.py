"""PMS's public surface for other modules. Read-only and plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Q

from modules.pms.domain import state_machine as sm
from modules.pms.models import Application, Inventor


@dataclass(frozen=True)
class PatentSummaryDTO:
    user_id: int
    filed: int
    granted: int


def get_patent_summaries(user_ids: Sequence[int]) -> dict[int, PatentSummaryDTO]:
    """Filed and granted counts per person, as applicant or institute-user inventor."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    apps = Application.objects.filter(status__in=[sm.FILED, sm.GRANTED]).filter(
        Q(applicant_user_id__in=ids) | Q(inventors__user_id__in=ids)).distinct()
    people: dict[int, set[tuple[int, str]]] = {i: set() for i in ids}
    rows = apps.values_list("pk", "status", "applicant_user_id")
    for pk, status, applicant in rows:
        if applicant in people:
            people[applicant].add((pk, status))
    for pk, status, uid in (Inventor.objects.filter(application__in=apps, user_id__in=ids)
                            .values_list("application_id", "application__status", "user_id")):
        people[uid].add((pk, status))
    return {uid: PatentSummaryDTO(uid, sum(1 for _, s in seen if s == sm.FILED),
                                  sum(1 for _, s in seen if s == sm.GRANTED))
            for uid, seen in people.items()}
