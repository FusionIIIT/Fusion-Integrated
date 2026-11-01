"""Tests for RSPC public contracts.
Ensures plural signatures, DTO structure, and safe behavior with empty/missing IDs.
"""

from decimal import Decimal

from modules.rspc.contracts import (
    ProjectSummaryDTO,
    ProposalCountsDTO,
    get_project_summaries,
    get_projects_by_codes,
    get_proposal_counts,
)


def test_contract_dtos_structure():
    """Verify DTO dataclasses instantiate properly."""
    summary = ProjectSummaryDTO(
        user_id=101,
        active_count=2,
        completed_count=1,
        total_sanctioned_budget=Decimal("5000000.00"),
        total_utilized_budget=Decimal("1200000.00"),
    )
    assert summary.user_id == 101
    assert summary.active_count == 2
    assert summary.total_sanctioned_budget == Decimal("5000000.00")

    prop = ProposalCountsDTO(user_id=101, submitted_count=3, approved_count=2)
    assert prop.user_id == 101
    assert prop.submitted_count == 3
    assert prop.approved_count == 2


def test_get_project_summaries_empty_input():
    """Empty user IDs list returns empty dict without querying."""
    res = get_project_summaries([])
    assert res == {}


def test_get_proposal_counts_empty_input():
    """Empty user IDs list returns empty dict."""
    res = get_proposal_counts([])
    assert res == {}


def test_get_projects_by_codes_empty_input():
    """Empty project codes list returns empty dict."""
    res = get_projects_by_codes([])
    assert res == {}
