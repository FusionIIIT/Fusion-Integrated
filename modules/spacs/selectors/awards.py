"""Selectors for Convocation Awards and candidate evaluations."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.spacs.models import AwardCandidate, AwardCycle


def visible_award_cycles(principal) -> QuerySet[AwardCycle]:
    """Visible award cycles for caller.

    - Convener (spacs.award.manage): all cycles.
    - Committee member (spacs.award.review): cycles under evaluation or prepared.
    - General users / students (spacs.award.view): published cycles only.
    """
    qs = AwardCycle.objects.select_related("scheme", "policy_version")
    if principal is not None and principal.has_permission("spacs.award.manage"):
        return qs

    if principal is not None and principal.has_permission("spacs.award.review"):
        return qs.filter(status__in=["pool_prepared", "under_evaluation", "result_recorded", "published"])

    return qs.filter(status="published")


def get_award_cycle(cycle_id: int, principal) -> AwardCycle | None:
    return visible_award_cycles(principal).filter(pk=cycle_id).first()


def visible_candidates(award_cycle_id: int, principal) -> QuerySet[AwardCandidate]:
    cycle = get_award_cycle(award_cycle_id, principal)
    if cycle is None:
        return AwardCandidate.objects.none()

    qs = AwardCandidate.objects.filter(award_cycle_id=award_cycle_id)
    if cycle.status == "published":
        # In published state, public can view approved awardees
        if principal is not None and (principal.has_permission("spacs.award.manage") or principal.has_permission("spacs.award.review")):
            return qs
        return qs.filter(final_outcome="approved")
    return qs
