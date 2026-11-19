"""RSPC module's public contract surface.

Follows Fusion ERP architectural constraints:
- Plural by signature (ADR-0007, contracts_are_plural check).
- Uses dataclasses and pure signatures.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ResearchProposalContract:
    id: int
    title: str
    pi_id: int
    department: str
    funding_agency: str
    budget: Decimal
    status: str
    start_date: str
    end_date: str


@dataclass(frozen=True)
class ConsultancyProjectContract:
    id: int
    title: str
    pi_id: int
    client_name: str
    total_cost: Decimal
    institutional_share: Decimal
    status: str
    start_date: str
    end_date: str


@dataclass(frozen=True)
class RSPCProjectSummaryContract:
    project_id: int
    project_type: str
    title: str
    pi_id: int
    total_sanctioned_budget: Decimal
    status: str


def get_user_proposals(
    user_ids: Sequence[int],
) -> dict[int, list[ResearchProposalContract]]:
    """Query research proposals for multiple users (PIs). Plural by signature."""
    from modules.rspc.models import ResearchProposal

    ids = {int(i) for i in user_ids}
    result: dict[int, list[ResearchProposalContract]] = {uid: [] for uid in ids}

    qs = ResearchProposal.objects.filter(pi_id__in=ids)
    for p in qs:
        contract = ResearchProposalContract(
            id=p.id,
            title=p.title,
            pi_id=p.pi_id,
            department=p.department,
            funding_agency=p.funding_agency,
            budget=p.budget,
            status=p.status,
            start_date=p.start_date.isoformat(),
            end_date=p.end_date.isoformat(),
        )
        result[p.pi_id].append(contract)

    return result


def get_user_consultancies(
    user_ids: Sequence[int],
) -> dict[int, list[ConsultancyProjectContract]]:
    """Query consultancy projects for multiple users. Plural by signature."""
    from modules.rspc.models import ConsultancyProject

    ids = {int(i) for i in user_ids}
    result: dict[int, list[ConsultancyProjectContract]] = {uid: [] for uid in ids}

    qs = ConsultancyProject.objects.filter(pi_id__in=ids)
    for c in qs:
        contract = ConsultancyProjectContract(
            id=c.id,
            title=c.title,
            pi_id=c.pi_id,
            client_name=c.client_name,
            total_cost=c.total_cost,
            institutional_share=c.institutional_share,
            status=c.status,
            start_date=c.start_date.isoformat(),
            end_date=c.end_date.isoformat(),
        )
        result[c.pi_id].append(contract)

    return result


def get_proposals_by_id(
    proposal_ids: Sequence[int],
) -> dict[int, ResearchProposalContract | None]:
    """Query research proposals by their primary keys. Plural by signature."""
    from modules.rspc.models import ResearchProposal

    ids = {int(i) for i in proposal_ids}
    result: dict[int, ResearchProposalContract | None] = {pid: None for pid in ids}

    qs = ResearchProposal.objects.filter(id__in=ids)
    for p in qs:
        result[p.id] = ResearchProposalContract(
            id=p.id,
            title=p.title,
            pi_id=p.pi_id,
            department=p.department,
            funding_agency=p.funding_agency,
            budget=p.budget,
            status=p.status,
            start_date=p.start_date.isoformat(),
            end_date=p.end_date.isoformat(),
        )

    return result
