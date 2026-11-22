"""Expense & Voucher lifecycle service tests."""

from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.iaa.domain.rules import DomainValidationError
from modules.iaa.models import (
    ApprovalHierarchyRule,
    DepartmentBudget,
    RequestStatus,
)
from modules.iaa.services.approvals import record_request_decision
from modules.iaa.services.requests import (
    create_expense_request,
    raise_request_clarification,
    record_request_processing,
    respond_to_request_clarification,
    review_and_validate_request,
    submit_expense_request,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def budget_cse():
    return DepartmentBudget.objects.create(
        department="CSE",
        financial_year="2026-2027",
        allocated_amount=Decimal("100000.00"),
        utilized_amount=Decimal("10000.00"),
    )


@pytest.fixture
def hierarchy_rules():
    ApprovalHierarchyRule.objects.create(
        request_type="expense",
        min_amount=Decimal("0.00"),
        max_amount=Decimal("25000.00"),
        required_levels=1,
        approver_roles=["HOD"],
    )
    ApprovalHierarchyRule.objects.create(
        request_type="expense",
        min_amount=Decimal("25000.01"),
        max_amount=Decimal("100000.00"),
        required_levels=2,
        approver_roles=["HOD", "Dean"],
    )


def test_create_and_submit_expense_request(budget_cse, hierarchy_rules):
    items = [
        {"description": "Paper", "category": "Office", "amount": "100.00"},
        {"description": "Pens", "category": "Office", "amount": "50.00"},
    ]
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Stationery Supplies",
        description="Office stationery",
        items=items,
    )
    assert req.status == RequestStatus.DRAFT
    assert req.total_amount == Decimal("150.00")
    assert not req.is_locked

    submitted = submit_expense_request(req.id, user_id=1001, acting_role="basic_user")
    assert submitted.status == RequestStatus.SUBMITTED
    assert submitted.is_locked


def test_submit_validates_completeness_and_ownership(budget_cse):
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Empty Request",
        items=[],
    )
    with pytest.raises(DomainValidationError):
        submit_expense_request(req.id, user_id=1001, acting_role="basic_user")

    with pytest.raises(ConflictError, match="only submit your own"):
        submit_expense_request(req.id, user_id=2002, acting_role="basic_user")


def test_finance_validation_and_approval_flow(budget_cse, hierarchy_rules):
    items = [{"description": "Hardware", "category": "Lab", "amount": "5000.00"}]
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Lab equipment",
        items=items,
    )
    submit_expense_request(req.id, user_id=1001, acting_role="basic_user")

    validated = review_and_validate_request(
        req.id, finance_user_id=3001, acting_role="finance_staff"
    )
    assert validated.status == RequestStatus.FINANCE_VALIDATED
    assert validated.required_approval_levels == 1
    assert validated.assigned_approver_role == "HOD"

    approved = record_request_decision(
        request_id=req.id,
        approver_id=4001,
        approver_role="HOD",
        decision="approve",
        remarks="Approved as per plan",
    )
    assert approved.status == RequestStatus.APPROVED

    recorded = record_request_processing(
        request_id=req.id,
        finance_user_id=3001,
        acting_role="finance_staff",
    )
    assert recorded.status == RequestStatus.RECORDED


def test_creator_cannot_approve_own_request(budget_cse, hierarchy_rules):
    items = [{"description": "Books", "category": "Library", "amount": "2000.00"}]
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Books",
        items=items,
    )
    submit_expense_request(req.id, user_id=1001, acting_role="basic_user")
    review_and_validate_request(req.id, finance_user_id=3001, acting_role="finance_staff")

    with pytest.raises(DomainValidationError, match="Creator or claimant cannot approve"):
        record_request_decision(
            request_id=req.id,
            approver_id=1001,
            approver_role="HOD",
            decision="approve",
            remarks="Self approving",
        )


def test_clarification_query_and_response_cycle(budget_cse):
    items = [{"description": "Laptops", "category": "IT", "amount": "12000.00"}]
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="IT Purchase",
        items=items,
    )
    submit_expense_request(req.id, user_id=1001, acting_role="basic_user")

    query = raise_request_clarification(
        request_id=req.id,
        finance_user_id=3001,
        acting_role="finance_staff",
        query_text="Please provide quotations",
    )
    req.refresh_from_db()
    assert req.status == RequestStatus.QUERY_RAISED

    respond_to_request_clarification(
        query_id=query.id,
        user_id=1001,
        acting_role="basic_user",
        response_text="Quotations attached",
    )
    req.refresh_from_db()
    assert req.status == RequestStatus.QUERY_RESPONDED


def test_insufficient_budget_creates_anomaly(budget_cse):
    budget_cse.allocated_amount = Decimal("500.00")
    budget_cse.utilized_amount = Decimal("400.00")
    budget_cse.save()

    items = [{"description": "High cost item", "category": "IT", "amount": "300.00"}]
    req = create_expense_request(
        user_id=1001,
        acting_role="basic_user",
        department="CSE",
        request_type="expense",
        title="Server",
        items=items,
    )
    submit_expense_request(req.id, user_id=1001, acting_role="basic_user")
    review_and_validate_request(req.id, finance_user_id=3001, acting_role="finance_staff")

    from modules.iaa.models import Anomaly

    anomaly = Anomaly.objects.filter(reference_type="request", reference_id=req.id).first()
    assert anomaly is not None
    assert anomaly.category == "budget_insufficient"
