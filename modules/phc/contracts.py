"""PHC public contracts surface. The ONLY thing other modules may import.

Plural by signature on purpose (contracts_are_plural check).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PatientRecordSummaryDTO:
    patient_user_id: int
    total_visits: int
    latest_visit_date: str | None


@dataclass(frozen=True)
class ActiveAnnouncementDTO:
    id: int
    title: str
    content: str
    priority: str
    published_date: str


def get_patient_record_summaries(user_ids: Sequence[int]) -> dict[int, PatientRecordSummaryDTO]:
    """Batched lookup of patient clinical summaries."""
    from modules.phc.models.patient_records import PatientVisit

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    result = {}
    for uid in ids:
        visits = PatientVisit.objects.filter(patient_user_id=uid).order_by("-visit_date")
        count = visits.count()
        latest = str(visits.first().visit_date) if count > 0 else None
        result[uid] = PatientRecordSummaryDTO(
            patient_user_id=uid,
            total_visits=count,
            latest_visit_date=latest,
        )
    return result


def get_reimbursement_claim_counts(user_ids: Sequence[int]) -> dict[int, int]:
    """Batched count of submitted claims per user."""
    from modules.phc.models.reimbursement import ReimbursementClaim

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    return {
        uid: ReimbursementClaim.objects.filter(claimant_user_id=uid).count()
        for uid in ids
    }
