"""RSPC Module Public Contract.
Follows the Fusion ERP rule: The ONLY file other modules may import from modules.rspc.
Every getter function is strictly plural by signature to prevent N+1 queries.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Q, Sum

from modules.rspc.domain.entities import ProjectLifecycleStatus, ProposalStatus
from modules.rspc.models import ResearchProposal, RSPCProject


@dataclass(frozen=True)
class ProjectSummaryDTO:
    user_id: int
    active_count: int
    completed_count: int
    total_sanctioned_budget: Decimal
    total_utilized_budget: Decimal


@dataclass(frozen=True)
class ProposalCountsDTO:
    user_id: int
    submitted_count: int
    approved_count: int


def get_project_summaries(user_ids: Sequence[int]) -> dict[int, ProjectSummaryDTO]:
    """Retrieve RSPC project summaries for a collection of faculty user IDs. Plural by signature."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = (
        RSPCProject.objects.filter(pi_user_id__in=ids)
        .values("pi_user_id")
        .annotate(
            active=Count("pk", filter=Q(status=ProjectLifecycleStatus.ACTIVE.value)),
            completed=Count(
                "pk",
                filter=Q(
                    status__in=[
                        ProjectLifecycleStatus.COMPLETED.value,
                        ProjectLifecycleStatus.ARCHIVED.value,
                    ]
                ),
            ),
            sanctioned=Sum("sanctioned_budget"),
            utilized=Sum("utilized_budget"),
        )
    )

    result: dict[int, ProjectSummaryDTO] = {}
    for r in rows:
        uid = r["pi_user_id"]
        result[uid] = ProjectSummaryDTO(
            user_id=uid,
            active_count=r["active"] or 0,
            completed_count=r["completed"] or 0,
            total_sanctioned_budget=r["sanctioned"] or Decimal("0.00"),
            total_utilized_budget=r["utilized"] or Decimal("0.00"),
        )

    for uid in ids:
        if uid not in result:
            result[uid] = ProjectSummaryDTO(
                user_id=uid,
                active_count=0,
                completed_count=0,
                total_sanctioned_budget=Decimal("0.00"),
                total_utilized_budget=Decimal("0.00"),
            )

    return result


def get_proposal_counts(user_ids: Sequence[int]) -> dict[int, ProposalCountsDTO]:
    """Retrieve proposal counts for faculty user IDs. Plural by signature."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = (
        ResearchProposal.objects.filter(faculty_user_id__in=ids)
        .values("faculty_user_id")
        .annotate(
            submitted=Count("pk"),
            approved=Count("pk", filter=Q(status=ProposalStatus.APPROVED.value)),
        )
    )

    result: dict[int, ProposalCountsDTO] = {}
    for r in rows:
        uid = r["faculty_user_id"]
        result[uid] = ProposalCountsDTO(
            user_id=uid,
            submitted_count=r["submitted"] or 0,
            approved_count=r["approved"] or 0,
        )

    for uid in ids:
        if uid not in result:
            result[uid] = ProposalCountsDTO(
                user_id=uid,
                submitted_count=0,
                approved_count=0,
            )

    return result


def get_projects_by_codes(project_codes: Sequence[str]) -> dict[str, dict]:
    """Retrieve project metadata for a list of project codes. Plural by signature."""
    codes = {str(c).strip() for c in project_codes if c}
    if not codes:
        return {}

    projects = RSPCProject.objects.filter(project_code__in=codes)
    return {
        p.project_code: {
            "title": p.title,
            "project_type": p.project_type,
            "pi_user_id": p.pi_user_id,
            "department_id": p.department_id,
            "status": p.status,
            "sanctioned_budget": float(p.sanctioned_budget),
            "utilized_budget": float(p.utilized_budget),
        }
        for p in projects
    }
