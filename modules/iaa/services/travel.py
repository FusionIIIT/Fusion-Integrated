"""Travel Allowance (TA) Claim management service (CW-IAA-02, IAA-UC-401..404)."""

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.iaa.domain.rules import (
    check_budget_sufficiency,
    is_high_value_ta,
    validate_travel_completeness,
)
from modules.iaa.domain.state_machine import transition_ta_claim
from modules.iaa.models import (
    ClarificationQuery,
    DepartmentBudget,
    IAAConfiguration,
    TAClaim,
    TAClaimStatus,
    TAExpenseItem,
)
from modules.iaa.services.anomalies import create_anomaly
from modules.iaa.services.audit_trail import record_audit_log


def submit_travel_claim(
    user_id: int,
    acting_role: str,
    department: str,
    purpose: str,
    departure_date: str,
    arrival_date: str,
    source_location: str,
    destination_location: str,
    claimed_amount: Decimal,
    items: list[dict[str, Any]] | None = None,
) -> TAClaim:
    """IAA-UC-401 & IAA-BR-101 & IAA-BR-104: TA claim submission."""
    validate_travel_completeness(
        purpose=purpose,
        departure_date=departure_date,
        arrival_date=arrival_date,
        claimed_amount=claimed_amount,
        source_location=source_location,
        destination_location=destination_location,
    )

    with transaction.atomic():
        claim = TAClaim.objects.create(
            user_id=user_id,
            department=department,
            purpose=purpose,
            departure_date=departure_date,
            arrival_date=arrival_date,
            source_location=source_location,
            destination_location=destination_location,
            claimed_amount=claimed_amount,
            status=TAClaimStatus.SUBMITTED,
            is_locked=True,
        )

        for item in items or []:
            TAExpenseItem.objects.create(
                claim=claim,
                expense_type=item.get("expense_type", "Travel"),
                amount=Decimal(str(item.get("amount", "0"))),
                details=item.get("details", ""),
            )

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="submit_travel_claim",
            target_type="travel",
            target_id=claim.id,
            resulting_status=TAClaimStatus.SUBMITTED,
            details={"claimed_amount": str(claimed_amount)},
        )
        return claim


def verify_travel_claim(
    claim_id: int,
    finance_user_id: int,
    acting_role: str,
) -> TAClaim:
    """IAA-UC-402 & IAA-BR-201 & IAA-BR-202: Finance verification and high-value routing."""
    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().filter(id=claim_id).first()
        if not claim:
            raise NotFoundError("Travel claim not found.")

        # Budget Check (IAA-BR-102)
        budget = DepartmentBudget.objects.filter(department=claim.department).first()
        if budget and not check_budget_sufficiency(budget.available_amount, claim.claimed_amount):
            create_anomaly(
                category="budget_insufficient",
                description=(
                    f"Department budget for {claim.department} insufficient for TA claim. "
                    f"Claimed: {claim.claimed_amount}, Available: {budget.available_amount}"
                ),
                reference_type="travel",
                reference_id=claim.id,
                flagged_by_id=finance_user_id,
                flagged_by_role=acting_role,
            )

        # High-value TA verification (IAA-BR-202)
        config = IAAConfiguration.objects.filter(is_active=True).first()
        threshold = config.high_value_ta_threshold if config else Decimal("50000.00")
        is_high = is_high_value_ta(claim.claimed_amount, threshold)
        claim.is_high_value = is_high

        if is_high:
            new_status = transition_ta_claim(claim.status, "verify_high_value", "finance_staff")
            claim.assigned_approver_role = "Dean"
            claim.approval_assigned_at = timezone.now()
        else:
            new_status = transition_ta_claim(claim.status, "verify_standard", "finance_staff")

        claim.status = new_status
        claim.save()

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="verify_travel_claim",
            target_type="travel",
            target_id=claim.id,
            resulting_status=new_status,
            details={"is_high_value": is_high},
        )
        return claim


def raise_travel_clarification(
    claim_id: int,
    finance_user_id: int,
    acting_role: str,
    query_text: str,
) -> ClarificationQuery:
    if not query_text or not query_text.strip():
        raise BadRequestError("Query text is required.")

    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().filter(id=claim_id).first()
        if not claim:
            raise NotFoundError("Travel claim not found.")

        new_status = transition_ta_claim(claim.status, "raise_query", "finance_staff")
        claim.status = new_status
        claim.save()

        query = ClarificationQuery.objects.create(
            content_type="travel",
            object_id=claim.id,
            sender_id=finance_user_id,
            sender_role=acting_role,
            query_text=query_text,
            status="pending",
        )

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="raise_query",
            target_type="travel",
            target_id=claim.id,
            resulting_status=new_status,
        )
        return query


def respond_to_travel_clarification(
    query_id: int,
    user_id: int,
    acting_role: str,
    response_text: str,
) -> TAClaim:
    if not response_text or not response_text.strip():
        raise BadRequestError("Response text is required.")

    with transaction.atomic():
        query = ClarificationQuery.objects.select_for_update().filter(id=query_id).first()
        if not query or query.content_type != "travel":
            raise NotFoundError("Clarification query not found.")

        claim = TAClaim.objects.select_for_update().filter(id=query.object_id).first()
        if not claim or claim.user_id != user_id:
            raise ConflictError("You can only respond to queries on your own claim.")

        query.response_text = response_text
        query.status = "responded"
        query.responded_at = timezone.now()
        query.save()

        new_status = transition_ta_claim(claim.status, "respond_query", "basic_user")
        claim.status = new_status
        claim.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="respond_query",
            target_type="travel",
            target_id=claim.id,
            resulting_status=new_status,
        )
        return claim


def record_travel_processing(
    claim_id: int,
    finance_user_id: int,
    acting_role: str,
) -> TAClaim:
    """IAA-BR-006 & IAA-UC-404: Non-monetary internal record completion."""
    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().filter(id=claim_id).first()
        if not claim:
            raise NotFoundError("Travel claim not found.")

        new_status = transition_ta_claim(claim.status, "record", "finance_staff")
        claim.status = new_status
        claim.save()

        record_audit_log(
            user_id=finance_user_id,
            acting_role=acting_role,
            action="record_processing",
            target_type="travel",
            target_id=claim.id,
            resulting_status=new_status,
            details={"non_monetary": True},
        )
        return claim
