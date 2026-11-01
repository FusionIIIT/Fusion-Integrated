"""RSPC public contract — the ONLY thing other modules may import (ADR-0013).

All functions are plural by signature to prevent N+1 queries.
Returns immutable DTOs / simple dicts / counts.
Never mutates data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from django.db.models import Count, Q

from modules.rspc.models import ResearchProject, ConsultancyProject
from modules.rspc.domain.state_machine import PROPOSAL_TERMINAL, CONSULTANCY_TERMINAL


@dataclass(frozen=True)
class ProjectCountsDTO:
    user_id: int
    active_proposals: int
    approved_proposals: int
    active_consultancies: int
    approved_consultancies: int


def get_project_counts(user_ids: Sequence[int]) -> dict[int, ProjectCountsDTO]:
    """Retrieve active and approved research and consultancy counts for users."""
    prop_rows = (
        ResearchProject.objects.filter(user_id__in=user_ids)
        .values("user_id")
        .annotate(
            active=Count("pk", filter=~Q(status__in=PROPOSAL_TERMINAL)),
            approved=Count("pk", filter=Q(status__in=["dean_approved", "director_approved"])),
        )
    )
    prop_map = {r["user_id"]: r for r in prop_rows}

    cons_rows = (
        ConsultancyProject.objects.filter(user_id__in=user_ids)
        .values("user_id")
        .annotate(
            active=Count("pk", filter=~Q(status__in=CONSULTANCY_TERMINAL)),
            approved=Count("pk", filter=Q(status__in=["dean_approved", "director_approved"])),
        )
    )
    cons_map = {r["user_id"]: r for r in cons_rows}

    result = {}
    for uid in user_ids:
        p = prop_map.get(uid, {"active": 0, "approved": 0})
        c = cons_map.get(uid, {"active": 0, "approved": 0})
        result[uid] = ProjectCountsDTO(
            user_id=uid,
            active_proposals=p["active"],
            approved_proposals=p["approved"],
            active_consultancies=c["active"],
            approved_consultancies=c["approved"],
        )
    return result
