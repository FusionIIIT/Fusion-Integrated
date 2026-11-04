"""Award cycles, candidate sheets, and published results selectors for SPACS.

Enforces:
- CFR-SPACS-013 (Award Candidate Sourcing)
- CFR-SPACS-014 (Award Evaluation, Approval and Publication)
- BR-SPACS-019 (Committee evaluation access)
"""
from __future__ import annotations

from django.db.models import QuerySet
from modules.spacs.models import AwardCycle, AwardCandidate


def get_active_award_cycles() -> QuerySet[AwardCycle]:
    return (
        AwardCycle.objects.select_related("policy_version", "policy_version__catalogue_entry")
        .order_by("-convocation_year")
    )


def get_award_cycle(cycle_id: int) -> AwardCycle | None:
    return (
        AwardCycle.objects.filter(pk=cycle_id)
        .select_related("policy_version", "policy_version__catalogue_entry")
        .prefetch_related("candidates")
        .first()
    )


def get_candidate_evaluation_sheet(cycle_id: int) -> QuerySet[AwardCandidate]:
    return (
        AwardCandidate.objects.filter(award_cycle_id=cycle_id)
        .order_by("-is_eligible", "-evaluation_score", "id")
    )


def get_published_award_winners(convocation_year: int | None = None) -> QuerySet[AwardCandidate]:
    qs = AwardCandidate.objects.filter(
        award_cycle__status="published",
        is_final_winner=True,
    ).select_related("award_cycle", "award_cycle__policy_version", "award_cycle__policy_version__catalogue_entry")

    if convocation_year:
        qs = qs.filter(award_cycle__convocation_year=convocation_year)

    return qs.order_by("-award_cycle__convocation_year", "award_cycle_id")
