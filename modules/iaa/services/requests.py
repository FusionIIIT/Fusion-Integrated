"""Expense & Voucher Request management service (CW-IAA-01, IAA-UC-101..105)."""

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.iaa.domain.rules import (
    check_budget_sufficiency,
    validate_record_not_locked,
    validate_request_completeness,
)
from modules.iaa.domain.state_machine import transition_expense_request
from modules.iaa.models import (
    ClarificationQuery,
    DepartmentBudget,
    ExpenseItem,
    ExpenseVoucherRequest,
    RequestStatus,
)
from modules.iaa.services.anomalies import create_anomaly
from modules.iaa.services.approvals import determine_approval_route
from modules.iaa.services.audit_trail import record_audit_log


def create_expense_request(
    user_id: int,
    acting_role: str,
    department: str,
    request_type: str,
    title: str,
    description: str = "",
    items: list[dict[str, Any]] | None = None,
) -> ExpenseVoucherRequest:
    with transaction.atomic():
        total_amount = sum(Decimal(str(item.get("amount", "0"))) for item in (items or []))
        req = ExpenseVoucherRequest.objects.create(
            user_id=user_id,
            department=department,
            request_type=request_type,
            title=title,
            description=description,
            total_amount=total_amount,
            status=RequestStatus.DRAFT,
            is_locked=False,
        )

        for item_data in items or []:
            ExpenseItem.objects.create(
                request=req,
                description=item_data.get("description", "Item"),
                category=item_data.get("category", "General"),
                amount=Decimal(str(item_data.get("amount", "0"))),
                receipt_reference=item_data.get("receipt_reference", ""),
            )

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="create_request_draft",
            target_type="request",
            target_id=req.id,
            resulting_status=RequestStatus.DRAFT,
            details={"title": title, "total_amount": str(total_amount)},
        )
        return req


def submit_expense_request(
    request_id: int,
    user_id: int,
    acting_role: str,
) -> ExpenseVoucherRequest:
    """Completeness check on submission and post-submission lock."""
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            raise NotFoundError("Request not found.")
        if req.user_id != user_id:
            raise ConflictError("You can only submit your own request.")

        validate_record_not_locked(req.is_locked)
        validate_request_completeness(
            title=req.title,
            description=req.description,
            department=req.department,
            total_amount=req.total_amount,
            items_count=req.items.count(),
        )

        new_status = transition_expense_request(req.status, "submit", "basic_user")
        req.status = new_status
        req.is_locked = True  # IAA-BR-104: post-submission lock
        req.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="submit_request",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
        )
        return req


def review_and_validate_request(
    request_id: int,
    finance_user_id: int,
    acting_role: str,
) -> ExpenseVoucherRequest:
    """IAA-UC-103: Finance review and budget validation (IAA-BR-102)."""
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            raise NotFoundError("Request not found.")

        # Budget Availability Validation (IAA-BR-102)
        budget = DepartmentBudget.objects.filter(department=req.department).first()
        if budget and not check_budget_sufficiency(budget.available_amount, req.total_amount):
            # Budget insufficiency creates material anomaly (IAA-BR-102, IAA-BR-103)
            create_anomaly(
                category="budget_insufficient",
                description=(
                    f"Department budget for {req.department} is insufficient. "
                    f"Requested: {req.total_amount}, Available: {budget.available_amount}"
                ),
                reference_type="request",
                reference_id=req.id,
                flagged_by_id=finance_user_id,
                flagged_by_role=acting_role,
            )

        # Route determination (IAA-BR-002)
        levels, roles = determine_approval_route(req.request_type, req.total_amount)
        req.required_approval_levels = levels
        req.assigned_approver_role = roles[0] if roles else "HOD"
        req.approval_assigned_at = timezone.now()

        new_status = transition_expense_request(req.status, "validate", "finance_staff")
        req.status = new_status
        req.save()

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="finance_validate",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
            details={"levels": levels, "first_approver_role": req.assigned_approver_role},
        )
        return req


def raise_request_clarification(
    request_id: int,
    finance_user_id: int,
    acting_role: str,
    query_text: str,
) -> ClarificationQuery:
    if not query_text or not query_text.strip():
        raise BadRequestError("Query text is required.")

    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            raise NotFoundError("Request not found.")

        new_status = transition_expense_request(req.status, "raise_query", "finance_staff")
        req.status = new_status
        req.save()

        query = ClarificationQuery.objects.create(
            content_type="request",
            object_id=req.id,
            sender_id=finance_user_id,
            sender_role=acting_role,
            query_text=query_text,
            status="pending",
        )

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="raise_query",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
            details={"query_id": query.id},
        )
        return query


def respond_to_request_clarification(
    query_id: int,
    user_id: int,
    acting_role: str,
    response_text: str,
) -> ExpenseVoucherRequest:
    if not response_text or not response_text.strip():
        raise BadRequestError("Response text is required.")

    with transaction.atomic():
        query = ClarificationQuery.objects.select_for_update().filter(id=query_id).first()
        if not query or query.content_type != "request":
            raise NotFoundError("Clarification query not found.")

        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=query.object_id).first()
        if not req or req.user_id != user_id:
            raise ConflictError("You can only respond to queries on your own request.")

        query.response_text = response_text
        query.status = "responded"
        query.responded_at = timezone.now()
        query.save()

        new_status = transition_expense_request(req.status, "respond_query", "basic_user")
        req.status = new_status
        req.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="respond_query",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
        )
        return req


def record_request_processing(
    request_id: int,
    finance_user_id: int,
    acting_role: str,
) -> ExpenseVoucherRequest:
    """IAA-BR-006 & IAA-UC-105: Internal processing is non-monetary record completion."""
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            raise NotFoundError("Request not found.")

        new_status = transition_expense_request(req.status, "record", "finance_staff")
        req.status = new_status
        req.save()

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="record_processing",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
            details={"non_monetary": True},
        )
        return req
