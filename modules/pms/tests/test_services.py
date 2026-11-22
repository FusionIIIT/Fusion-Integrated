from datetime import date
from decimal import Decimal
import pytest

from modules.pms.models.application import ApplicationStatus
from modules.pms.models.budget import BudgetStatus
from modules.pms.services.applications import (
    create_draft,
    submit_application,
    withdraw_application,
)
from modules.pms.services.attorney import (
    assign_attorney,
    respond_assignment,
)
from modules.pms.services.budget import review_budget
from modules.pms.services.filing import record_external_filing, record_grant
from modules.pms.services.finance import record_reversal, record_transaction
from modules.pms.services.reviews import assign_director, submit_review


@pytest.mark.django_db
def test_full_application_lifecycle():
    # 1. Create draft
    app = create_draft(
        applicant_user_id=101,
        title="High-Pressure Hydrogen Electrolyzer",
        abstract="Novel membrane stack design",
        claims="Claim 1: An improved electrolyzer cell.",
    )
    assert app.status == ApplicationStatus.DRAFT

    # 2. Submit application
    app = submit_application(app.id, actor_user_id=101, actor_roles=["applicant"])
    assert app.status == ApplicationStatus.SUBMITTED

    # 3. Assign director
    app = assign_director(app.id, coordinator_user_id=901, director_user_id=301, roles=["pms_coordinator"])
    assert app.status == ApplicationStatus.UNDER_REVIEW
    assert app.assigned_director_id == 301

    # 4. Review and approve
    submit_review(
        app_id=app.id,
        reviewer_user_id=301,
        verdict="recommend_approval",
        comments="Meets novelty and inventive step criteria.",
        scores={"novelty": 9, "inventive_step": 8, "commercial": 8},
        roles=["director"],
    )
    app.refresh_from_db()
    assert app.status == ApplicationStatus.APPROVED

    # 5. Sanction budget
    review_budget(
        app_id=app.id,
        user_id=901,
        decision=BudgetStatus.APPROVED,
        approved_amount=Decimal("75000.00"),
        roles=["Dean R&D"],
    )
    assert app.budget.budget_status == BudgetStatus.APPROVED

    # 6. Assign attorney
    app = assign_attorney(app.id, coordinator_user_id=901, attorney_user_id=501, roles=["pms_coordinator"])
    assert app.status == ApplicationStatus.ATTORNEY_ASSIGNED

    # 7. Attorney accepts
    app = respond_assignment(app.id, attorney_user_id=501, accepted=True, roles=["pms_attorney"])
    assert app.status == ApplicationStatus.FILING_IN_PROGRESS

    # 8. Record external filing
    app = record_external_filing(
        app.id,
        user_id=501,
        official_filing_number="202611004521",
        filing_date=date.today(),
        roles=["pms_attorney"],
    )
    assert app.status == ApplicationStatus.FILED


@pytest.mark.django_db
def test_financial_ledger_append_only():
    app = create_draft(applicant_user_id=101, title="Thermal Fluid Heat Pipe")
    
    # Record transaction
    txn = record_transaction(
        app_id=app.id,
        user_id=901,
        transaction_type="filing_fee",
        amount=Decimal("8000.00"),
        reference_no="IPO-PAY-001",
        roles=["pms_coordinator"],
    )
    assert app.financial_transactions.count() == 1
    assert txn.amount == Decimal("8000.00")

    # Record reversal
    rev = record_reversal(txn.id, user_id=901, reason="Fee overcharge correction", roles=["pms_coordinator"])
    assert app.financial_transactions.count() == 2
    assert rev.amount == Decimal("-8000.00")
