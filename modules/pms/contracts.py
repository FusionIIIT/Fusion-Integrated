"""Contract interface for the Patent Management System.

This is the ONLY file in modules.pms that other modules may import directly.
All cross-module getters must take a sequence of IDs (never singular).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Q

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import CoInventor, PatentApplication


@dataclass(frozen=True)
class PatentSummaryDTO:
    total_applications: int
    submitted: int
    under_review: int
    filed: int
    granted: int
    withdrawn: int


def get_patent_counts(user_ids: Sequence[int]) -> dict[int, PatentSummaryDTO]:
    """Retrieve patent count summary per applicant/inventor for a sequence of user IDs."""
    if not user_ids:
        return {}

    id_set = set(user_ids)
    # Direct applicants
    qs = (
        PatentApplication.objects.filter(applicant_user_id__in=id_set)
        .values("applicant_user_id")
        .annotate(
            total=Count("id"),
            submitted=Count("id", filter=Q(status=PatentApplicationStatus.SUBMITTED.value)),
            under_review=Count("id", filter=Q(status=PatentApplicationStatus.UNDER_REVIEW.value)),
            filed=Count("id", filter=Q(status=PatentApplicationStatus.FILED.value)),
            granted=Count("id", filter=Q(status=PatentApplicationStatus.GRANTED.value)),
            withdrawn=Count("id", filter=Q(status=PatentApplicationStatus.WITHDRAWN.value)),
        )
    )

    result = {}
    for r in qs:
        uid = r["applicant_user_id"]
        result[uid] = PatentSummaryDTO(
            total_applications=r["total"],
            submitted=r["submitted"],
            under_review=r["under_review"],
            filed=r["filed"],
            granted=r["granted"],
            withdrawn=r["withdrawn"],
        )

    # Co-inventor applications
    coinv_qs = (
        CoInventor.objects.filter(user_id__in=id_set)
        .select_related("application")
        .values("user_id", "application__status")
    )
    for c in coinv_qs:
        uid = c["user_id"]
        st = c["application__status"]
        if uid not in result:
            result[uid] = PatentSummaryDTO(
                total_applications=0, submitted=0, under_review=0, filed=0, granted=0, withdrawn=0
            )
        prev = result[uid]
        result[uid] = PatentSummaryDTO(
            total_applications=prev.total_applications + 1,
            submitted=prev.submitted + (1 if st == PatentApplicationStatus.SUBMITTED.value else 0),
            under_review=prev.under_review
            + (1 if st == PatentApplicationStatus.UNDER_REVIEW.value else 0),
            filed=prev.filed + (1 if st == PatentApplicationStatus.FILED.value else 0),
            granted=prev.granted + (1 if st == PatentApplicationStatus.GRANTED.value else 0),
            withdrawn=prev.withdrawn + (1 if st == PatentApplicationStatus.WITHDRAWN.value else 0),
        )

    for uid in id_set:
        if uid not in result:
            result[uid] = PatentSummaryDTO(0, 0, 0, 0, 0, 0)

    return result


def get_director_active_workload(director_user_ids: Sequence[int]) -> dict[int, int]:
    """Retrieve active review count for a sequence of Director user IDs."""
    if not director_user_ids:
        return {}
    qs = (
        PatentApplication.objects.filter(
            assigned_director_user_id__in=director_user_ids,
            status=PatentApplicationStatus.UNDER_REVIEW.value,
        )
        .values("assigned_director_user_id")
        .annotate(active_count=Count("id"))
    )
    counts = {r["assigned_director_user_id"]: r["active_count"] for r in qs}
    return {uid: counts.get(uid, 0) for uid in director_user_ids}


def get_attorney_active_workload(attorney_user_ids: Sequence[int]) -> dict[int, int]:
    """Retrieve active assigned application count for a sequence of Attorney user IDs."""
    if not attorney_user_ids:
        return {}
    active_statuses = [
        PatentApplicationStatus.ATTORNEY_ASSIGNED.value,
        PatentApplicationStatus.ASSIGNMENT_OFFERED.value,
        PatentApplicationStatus.BUDGET_APPROVED.value,
        PatentApplicationStatus.PRE_FILING_SATISFIED.value,
        PatentApplicationStatus.OFFICE_ACTION_RECORDED.value,
        PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL.value,
    ]
    qs = (
        PatentApplication.objects.filter(
            assigned_attorney_user_id__in=attorney_user_ids,
            status__in=active_statuses,
        )
        .values("assigned_attorney_user_id")
        .annotate(active_count=Count("id"))
    )
    counts = {r["assigned_attorney_user_id"]: r["active_count"] for r in qs}
    return {uid: counts.get(uid, 0) for uid in attorney_user_ids}
