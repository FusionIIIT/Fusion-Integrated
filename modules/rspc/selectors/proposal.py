"""Proposal selectors for RSPC."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.rspc.models import Proposal, ProposalReview
from modules.rspc.selectors.scoping import scope_proposals


def list_proposals(request, status: str | None = None) -> QuerySet[Proposal]:
    qs = scope_proposals(request).prefetch_related("reviews").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return qs


def get_proposal_reviews(proposal_id: int) -> QuerySet[ProposalReview]:
    return ProposalReview.objects.filter(proposal_id=proposal_id).order_by("created_at")
