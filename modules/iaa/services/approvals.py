"""Approval service enforcing segregation of duties and escalation."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.iaa.domain.rules import (
    validate_decision_remarks,
    validate_segregation_of_duties,
)
from modules.iaa.models import (
    ApprovalAction,
    ApprovalHierarchyRule,
    DecisionType,
    ExpenseVoucherRequest,
    RequestStatus,
    TAClaim,
    TAClaimStatus,
)
from modules.iaa.services.audit_trail import record_audit_log
from modules.iaa.services.notifications import emit_notification


def determine_approval_route(request_type: str, total_amount: Decimal) -> tuple[int, list[str]]:
    """IAA-BR-002: Configured approval routing based on amount and request type."""
    rules = ApprovalHierarchyRule.objects.filter(
        request_type=request_type,
        min_amount__lte=total_amount,
    ).order_by("-min_amount")

    for rule in rules:
        if rule.max_amount is None or total_amount <= rule.max_amount:
            return rule.required_levels, rule.approver_roles

    # Default fallback: 1 level by HOD for amounts < 25,000; 2 levels (HOD + Dean) for higher
    if total_amount >= Decimal("100000.00"):
        return 3, ["HOD", "Dean", "Director"]
    if total_amount >= Decimal("25000.00"):
        return 2, ["HOD", "Dean"]
    return 1, ["HOD"]


def record_request_decision(
    request_id: int,
    approver_id: int,
    approver_role: str,
    decision: str,  # "approve" or "reject"
    remarks: str,
) -> ExpenseVoucherRequest:
    # IAA-BR-005: remarks mandatory
    validate_decision_remarks(remarks)

    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            raise NotFoundError("Expense/Voucher request not found.")

        # IAA-BR-001: creator cannot approve same request
        validate_segregation_of_duties(creator_id=req.user_id, approver_id=approver_id)

        # Verify eligible states
        if req.status not in ("finance_validated", "approval_pending", "escalated"):
            raise ConflictError(
                f"Request in status '{req.status}' cannot receive an approval decision."
            )

        level = req.current_approval_level

        if decision == "reject":
            new_status = RequestStatus.REJECTED
        else:
            if level < req.required_approval_levels:
                new_status = RequestStatus.APPROVAL_PENDING
                req.current_approval_level = level + 1
            else:
                new_status = RequestStatus.APPROVED

        req.status = new_status
        req.approval_assigned_at = (
            timezone.now() if new_status == RequestStatus.APPROVAL_PENDING else None
        )
        req.save()

        ApprovalAction.objects.create(
            content_type="request",
            object_id=req.id,
            actor_id=approver_id,
            actor_role=approver_role,
            decision=DecisionType.APPROVE if decision == "approve" else DecisionType.REJECT,
            remarks=remarks,
            level=level,
        )

        record_audit_log(
            user_id=approver_id,
            acting_role=approver_role,
            action=f"request_{decision}",
            target_type="request",
            target_id=req.id,
            resulting_status=new_status,
            details={"level": level, "remarks": remarks},
        )

        emit_notification(
            recipient_ids=[req.user_id],
            title=f"Request {decision.capitalize()}d",
            message=f"Your request {req.title} was {decision}d at level {level}.",
            target_type="request",
            target_id=req.id,
        )

        return req


def record_travel_decision(
    claim_id: int,
    approver_id: int,
    approver_role: str,
    decision: str,
    remarks: str,
) -> TAClaim:
    validate_decision_remarks(remarks)

    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().filter(id=claim_id).first()
        if not claim:
            raise NotFoundError("Travel claim not found.")

        validate_segregation_of_duties(creator_id=claim.user_id, approver_id=approver_id)

        if claim.status not in ("approval_pending", "escalated"):
            raise ConflictError(
                f"Travel claim in status '{claim.status}' cannot receive authority decision."
            )

        new_status = TAClaimStatus.APPROVED if decision == "approve" else TAClaimStatus.REJECTED
        claim.status = new_status
        claim.save()

        ApprovalAction.objects.create(
            content_type="travel",
            object_id=claim.id,
            actor_id=approver_id,
            actor_role=approver_role,
            decision=DecisionType.APPROVE if decision == "approve" else DecisionType.REJECT,
            remarks=remarks,
            level=1,
        )

        record_audit_log(
            user_id=approver_id,
            acting_role=approver_role,
            action=f"travel_{decision}",
            target_type="travel",
            target_id=claim.id,
            resulting_status=new_status,
            details={"remarks": remarks},
        )

        return claim


def escalate_overdue_approval(
    target_type: str, target_id: int, higher_authority_role: str = "Director"
) -> None:
    """IAA-BR-401 & IAA-UC-203: Automatic timeout escalation."""
    with transaction.atomic():
        if target_type == "request":
            req = ExpenseVoucherRequest.objects.select_for_update().filter(id=target_id).first()
            if req and req.status in ("finance_validated", "approval_pending"):
                req.status = RequestStatus.ESCALATED
                req.assigned_approver_role = higher_authority_role
                req.approval_assigned_at = timezone.now()
                req.save()
                record_audit_log(
                    user_id=0,
                    acting_role="system",
                    action="timeout_escalation",
                    target_type="request",
                    target_id=req.id,
                    resulting_status=RequestStatus.ESCALATED,
                    details={"assigned_to": higher_authority_role},
                )
        elif target_type == "travel":
            claim = TAClaim.objects.select_for_update().filter(id=target_id).first()
            if claim and claim.status == TAClaimStatus.APPROVAL_PENDING:
                claim.status = TAClaimStatus.ESCALATED
                claim.assigned_approver_role = higher_authority_role
                claim.approval_assigned_at = timezone.now()
                claim.save()
                record_audit_log(
                    user_id=0,
                    acting_role="system",
                    action="timeout_escalation",
                    target_type="travel",
                    target_id=claim.id,
                    resulting_status=TAClaimStatus.ESCALATED,
                    details={"assigned_to": higher_authority_role},
                )
