"""Travel Allowance (TA) claim lifecycle service tests."""

from decimal import Decimal

import pytest

from modules.iaa.domain.rules import DomainValidationError
from modules.iaa.models import (
    DepartmentBudget,
    IAAConfiguration,
    TAClaimStatus,
)
from modules.iaa.services.approvals import record_travel_decision
from modules.iaa.services.travel import (
    raise_travel_clarification,
    record_travel_processing,
    respond_to_travel_clarification,
    submit_travel_claim,
    verify_travel_claim,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def iaa_config():
    return IAAConfiguration.objects.create(
        financial_year="2026-2027",
        high_value_ta_threshold=Decimal("50000.00"),
        approval_timeout_days=3,
        is_active=True,
    )


@pytest.fixture
def budget_ece():
    return DepartmentBudget.objects.create(
        department="ECE",
        financial_year="2026-2027",
        allocated_amount=Decimal("200000.00"),
        utilized_amount=Decimal("20000.00"),
    )


def test_submit_and_verify_standard_ta_claim(iaa_config, budget_ece):
    items = [
        {"expense_type": "Flight", "amount": "4000.00", "details": "Round trip"},
        {"expense_type": "Hotel", "amount": "3000.00", "details": "2 nights"},
    ]
    claim = submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="ECE",
        purpose="IEEE Conference Presentation",
        departure_date="2026-04-10",
        arrival_date="2026-04-12",
        source_location="Jabalpur",
        destination_location="Bengaluru",
        claimed_amount=Decimal("7000.00"),
        items=items,
    )
    assert claim.status == TAClaimStatus.SUBMITTED
    assert claim.is_locked

    verified = verify_travel_claim(claim.id, finance_user_id=3001, acting_role="finance_staff")
    assert verified.status == TAClaimStatus.VERIFIED
    assert not verified.is_high_value

    recorded = record_travel_processing(claim.id, finance_user_id=3001, acting_role="finance_staff")
    assert recorded.status == TAClaimStatus.RECORDED


def test_high_value_ta_claim_routes_to_approval(iaa_config, budget_ece):
    claim = submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="ECE",
        purpose="International Keynote",
        departure_date="2026-05-01",
        arrival_date="2026-05-10",
        source_location="Jabalpur",
        destination_location="Tokyo",
        claimed_amount=Decimal("75000.00"),
    )
    verified = verify_travel_claim(claim.id, finance_user_id=3001, acting_role="finance_staff")
    assert verified.status == TAClaimStatus.APPROVAL_PENDING
    assert verified.is_high_value

    approved = record_travel_decision(
        claim_id=claim.id,
        approver_id=5001,
        approver_role="Dean",
        decision="approve",
        remarks="International trip approved",
    )
    assert approved.status == TAClaimStatus.APPROVED


def test_claimant_cannot_approve_own_claim(iaa_config, budget_ece):
    claim = submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="ECE",
        purpose="Workshop",
        departure_date="2026-06-01",
        arrival_date="2026-06-05",
        source_location="Jabalpur",
        destination_location="Delhi",
        claimed_amount=Decimal("60000.00"),
    )
    verify_travel_claim(claim.id, finance_user_id=3001, acting_role="finance_staff")

    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        record_travel_decision(
            claim_id=claim.id,
            approver_id=1001,
            approver_role="Dean",
            decision="approve",
            remarks="Self approve",
        )


def test_travel_clarification_cycle(iaa_config, budget_ece):
    claim = submit_travel_claim(
        user_id=1001,
        acting_role="basic_user",
        department="ECE",
        purpose="Field Visit",
        departure_date="2026-07-01",
        arrival_date="2026-07-03",
        source_location="Jabalpur",
        destination_location="Bhopal",
        claimed_amount=Decimal("5000.00"),
    )
    query = raise_travel_clarification(
        claim_id=claim.id,
        finance_user_id=3001,
        acting_role="finance_staff",
        query_text="Boarding pass missing",
    )
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.QUERY_RAISED

    respond_to_travel_clarification(
        query_id=query.id,
        user_id=1001,
        acting_role="basic_user",
        response_text="Boarding pass uploaded",
    )
    claim.refresh_from_db()
    assert claim.status == TAClaimStatus.QUERY_RESPONDED
