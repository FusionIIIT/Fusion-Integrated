"""Unit tests for RSPC contract dataclasses (no database required)."""
from decimal import Decimal
from modules.rspc.contracts import (
    ResearchProposalContract,
    ConsultancyProjectContract,
    RSPCProjectSummaryContract,
)


def test_research_proposal_contract_structure():
    contract = ResearchProposalContract(
        id=1,
        title="AI in Smart Grid",
        pi_id=101,
        department="CSE",
        funding_agency="SERB",
        budget=Decimal("2500000.00"),
        status="SUBMITTED_HOD",
        start_date="2026-04-01",
        end_date="2028-03-31",
    )
    assert contract.id == 1
    assert contract.pi_id == 101
    assert contract.status == "SUBMITTED_HOD"


def test_consultancy_contract_structure():
    contract = ConsultancyProjectContract(
        id=2,
        title="Industrial Automation",
        pi_id=102,
        client_name="BHEL",
        total_cost=Decimal("450000.00"),
        institutional_share=Decimal("90000.00"),
        status="APPROVED_DEAN",
        start_date="2026-02-01",
        end_date="2026-08-01",
    )
    assert contract.client_name == "BHEL"
    assert contract.institutional_share == Decimal("90000.00")
