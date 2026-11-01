"""LTC and CPDA Claim services (BR-HR-016 to 022, BR-HR-035)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.hreis.domain.claims import (
    ClaimStatus,
    ClaimType,
    PaymentStatus,
    VerificationStatus,
    validate_cpda_submission,
    validate_financial_settlement,
    validate_ltc_submission,
)
from modules.hreis.domain.workflow import DecisionOutcome, get_next_authority, validate_decision
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, LtcRequest
from modules.hreis.services.audit import log_hr_action
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.service_records import get_or_create_service_record
from modules.hreis.services.workflow_config import get_workflow_config


# --- LTC SERVICES ---

@transaction.atomic
def submit_ltc_request(
    *,
    user_id: int,
    username: str,
    request_type: str,
    block_year: str,
    travel_from: str,
    travel_to: str,
    travel_start_date: date,
    travel_end_date: date,
    estimated_amount: Decimal,
    claimed_amount: Decimal | None = None,
    supporting_documents: list[str] | None = None,
) -> LtcRequest:
    service_rec = get_or_create_service_record(user_id)

    try:
        validate_ltc_submission(
            request_type=request_type,
            block_year=block_year,
            travel_from=travel_from,
            travel_to=travel_to,
            estimated_amount=estimated_amount,
            claimed_amount=claimed_amount,
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    ltc = LtcRequest.objects.create(
        user_id=user_id,
        request_type=request_type,
        block_year=block_year,
        travel_from=travel_from,
        travel_to=travel_to,
        travel_start_date=travel_start_date,
        travel_end_date=travel_end_date,
        estimated_amount=estimated_amount,
        claimed_amount=claimed_amount,
        supporting_documents=supporting_documents or [],
        status=ClaimStatus.SUBMITTED.value,
        verification_status=VerificationStatus.PENDING.value,
        approval_history=[
            {
                "action": "submitted",
                "actor_id": user_id,
                "actor_username": username,
                "timestamp": timezone.now().isoformat(),
            }
        ],
    )

    log_hr_action(
        actor_id=user_id,
        actor_username=username,
        actor_role="employee",
        action="submit_ltc_request",
        entity_type="ltc_request",
        entity_id=ltc.id,
        details={"type": request_type, "block_year": block_year},
    )

    send_hr_notification(
        user_id=user_id,
        title="LTC Request Submitted",
        message=f"Your LTC {request_type.capitalize()} request for block {block_year} has been submitted.",
        category="submission",
        link=f"/hr/ltc/{ltc.id}",
    )

    return ltc


@transaction.atomic
def verify_ltc_request(
    *,
    ltc_id: int,
    verdict: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> LtcRequest:
    """HR Administrator verifies documentation and eligibility (BR-HR-017)."""
    ltc = LtcRequest.objects.select_for_update().filter(id=ltc_id).first()
    if not ltc:
        raise NotFoundError("LTC request not found.")

    if verdict not in ("verified", "returned", "rejected"):
        raise BadRequestError("Verification verdict must be 'verified', 'returned', or 'rejected'.")

    service_rec = get_or_create_service_record(ltc.user_id)
    hierarchy = get_workflow_config("approval_hierarchy")
    first_role = get_next_authority("", service_rec.category, hierarchy) or "hod"

    ltc.verification_status = verdict
    ltc.verification_remarks = remarks

    if verdict == "verified":
        ltc.status = "pending_approval"
        ltc.current_authority_role = first_role
        notify_msg = f"Your LTC claim was verified by HR Admin and routed to {first_role.upper()}."
    elif verdict == "returned":
        ltc.status = ClaimStatus.RETURNED.value
        notify_msg = f"Your LTC claim was returned by HR Admin for correction. Remarks: {remarks}"
    else:
        ltc.status = ClaimStatus.REJECTED.value
        notify_msg = f"Your LTC claim was rejected during HR verification. Remarks: {remarks}"

    hist = list(ltc.approval_history or [])
    hist.append({
        "action": f"verification_{verdict}",
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "remarks": remarks,
        "timestamp": timezone.now().isoformat(),
    })
    ltc.approval_history = hist
    ltc.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=f"verify_ltc_{verdict}",
        entity_type="ltc_request",
        entity_id=ltc.id,
        details={"verdict": verdict, "remarks": remarks},
    )

    send_hr_notification(
        user_id=ltc.user_id,
        title=f"LTC Claim Verification: {verdict.capitalize()}",
        message=notify_msg,
        category="approval" if verdict == "verified" else "rejection",
        link=f"/hr/ltc/{ltc.id}",
    )

    return ltc


@transaction.atomic
def decide_ltc_request(
    *,
    ltc_id: int,
    outcome: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> LtcRequest:
    ltc = LtcRequest.objects.select_for_update().filter(id=ltc_id).first()
    if not ltc:
        raise NotFoundError("LTC request not found.")

    if ltc.verification_status != VerificationStatus.VERIFIED.value:
        raise BadRequestError("Cannot decide on unverified LTC request.")

    service_rec = get_or_create_service_record(ltc.user_id)
    hierarchy = get_workflow_config("approval_hierarchy")
    next_role = get_next_authority(ltc.current_authority_role, service_rec.category, hierarchy)

    try:
        validate_decision(
            outcome=outcome,
            current_status=ltc.status,
            remarks=remarks,
            can_forward=next_role is not None,
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    if outcome == DecisionOutcome.FORWARDED.value:
        ltc.status = ClaimStatus.FORWARDED.value
        ltc.current_authority_role = next_role or ltc.current_authority_role
        notify_msg = f"Your LTC claim has been forwarded to {ltc.current_authority_role.upper()}."
    elif outcome == DecisionOutcome.APPROVED.value:
        ltc.status = ClaimStatus.APPROVED.value
        ltc.payment_status = PaymentStatus.PROCESSING.value
        notify_msg = "Your LTC claim was approved and sent to Accountant for settlement processing."
    else:
        ltc.status = ClaimStatus.REJECTED.value
        notify_msg = f"Your LTC claim was rejected. Remarks: {remarks}"

    hist = list(ltc.approval_history or [])
    hist.append({
        "action": outcome,
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "remarks": remarks,
        "timestamp": timezone.now().isoformat(),
    })
    ltc.approval_history = hist
    ltc.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=f"ltc_{outcome}",
        entity_type="ltc_request",
        entity_id=ltc.id,
        details={"outcome": outcome, "remarks": remarks},
    )

    send_hr_notification(
        user_id=ltc.user_id,
        title=f"LTC Claim {outcome.capitalize()}",
        message=notify_msg,
        category=outcome,
        link=f"/hr/ltc/{ltc.id}",
    )

    return ltc


@transaction.atomic
def settle_ltc_claim(
    *,
    ltc_id: int,
    passed_amount: Decimal,
    reference_id: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> LtcRequest:
    """Accountant verifies financial correctness and records settlement (BR-HR-018, BR-HR-035)."""
    ltc = LtcRequest.objects.select_for_update().filter(id=ltc_id).first()
    if not ltc:
        raise NotFoundError("LTC request not found.")

    if ltc.status != ClaimStatus.APPROVED.value:
        raise BadRequestError("Only approved LTC claims can be settled.")

    try:
        validate_financial_settlement(passed_amount=passed_amount, reference_id=reference_id)
    except Exception as e:
        raise BadRequestError(str(e)) from e

    ltc.passed_amount = passed_amount
    ltc.payment_status = PaymentStatus.PAID.value
    ltc.payment_reference = reference_id
    ltc.status = ClaimStatus.SETTLED.value
    ltc.settlement_details = {
        "passed_amount": str(passed_amount),
        "reference_id": reference_id,
        "accountant_id": actor_id,
        "accountant_name": actor_username,
        "settled_at": timezone.now().isoformat(),
        "remarks": remarks,
    }

    hist = list(ltc.approval_history or [])
    hist.append({
        "action": "settled",
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "passed_amount": str(passed_amount),
        "reference": reference_id,
        "timestamp": timezone.now().isoformat(),
    })
    ltc.approval_history = hist
    ltc.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="settle_ltc_claim",
        entity_type="ltc_request",
        entity_id=ltc.id,
        details={"passed_amount": str(passed_amount), "reference": reference_id},
    )

    send_hr_notification(
        user_id=ltc.user_id,
        title="LTC Claim Settled",
        message=f"Your LTC claim has been settled for amount INR {passed_amount}. Ref: {reference_id}.",
        category="approval",
        link=f"/hr/ltc/{ltc.id}",
    )

    return ltc


# --- CPDA SERVICES ---

@transaction.atomic
def submit_cpda_request(
    *,
    user_id: int,
    username: str,
    request_type: str,
    purpose: str,
    amount: Decimal,
    supporting_documents: list[str],
) -> CpdaRequest:
    service_rec = get_or_create_service_record(user_id)

    try:
        validate_cpda_submission(
            request_type=request_type,
            purpose=purpose,
            amount=amount,
            available_balance=service_rec.cpda_balance,
            supporting_documents=supporting_documents,
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    cpda = CpdaRequest.objects.create(
        user_id=user_id,
        request_type=request_type,
        purpose=purpose,
        amount=amount,
        supporting_documents=supporting_documents,
        status=ClaimStatus.SUBMITTED.value,
        verification_status=VerificationStatus.PENDING.value,
        approval_history=[
            {
                "action": "submitted",
                "actor_id": user_id,
                "actor_username": username,
                "timestamp": timezone.now().isoformat(),
            }
        ],
    )

    log_hr_action(
        actor_id=user_id,
        actor_username=username,
        actor_role="employee",
        action="submit_cpda_request",
        entity_type="cpda_request",
        entity_id=cpda.id,
        details={"purpose": purpose, "amount": str(amount)},
    )

    send_hr_notification(
        user_id=user_id,
        title="CPDA Request Submitted",
        message=f"Your CPDA request for INR {amount} ({purpose}) has been submitted.",
        category="submission",
        link=f"/hr/cpda/{cpda.id}",
    )

    return cpda


@transaction.atomic
def verify_cpda_request(
    *,
    cpda_id: int,
    verdict: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> CpdaRequest:
    """HR Administrator verifies CPDA claim eligibility and bills (BR-HR-021)."""
    cpda = CpdaRequest.objects.select_for_update().filter(id=cpda_id).first()
    if not cpda:
        raise NotFoundError("CPDA request not found.")

    if verdict not in ("verified", "returned", "rejected"):
        raise BadRequestError("Verification verdict must be 'verified', 'returned', or 'rejected'.")

    service_rec = get_or_create_service_record(cpda.user_id)
    hierarchy = get_workflow_config("approval_hierarchy")
    first_role = get_next_authority("", service_rec.category, hierarchy) or "hod"

    cpda.verification_status = verdict
    cpda.verification_remarks = remarks

    if verdict == "verified":
        cpda.status = "pending_approval"
        cpda.current_authority_role = first_role
        notify_msg = f"Your CPDA claim was verified by HR Admin and routed to {first_role.upper()}."
    elif verdict == "returned":
        cpda.status = ClaimStatus.RETURNED.value
        notify_msg = f"Your CPDA claim was returned by HR Admin for clarification: {remarks}"
    else:
        cpda.status = ClaimStatus.REJECTED.value
        notify_msg = f"Your CPDA claim was rejected during HR verification: {remarks}"

    hist = list(cpda.approval_history or [])
    hist.append({
        "action": f"verification_{verdict}",
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "remarks": remarks,
        "timestamp": timezone.now().isoformat(),
    })
    cpda.approval_history = hist
    cpda.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=f"verify_cpda_{verdict}",
        entity_type="cpda_request",
        entity_id=cpda.id,
        details={"verdict": verdict, "remarks": remarks},
    )

    send_hr_notification(
        user_id=cpda.user_id,
        title=f"CPDA Claim Verification: {verdict.capitalize()}",
        message=notify_msg,
        category="approval" if verdict == "verified" else "rejection",
        link=f"/hr/cpda/{cpda.id}",
    )

    return cpda


@transaction.atomic
def decide_cpda_request(
    *,
    cpda_id: int,
    outcome: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> CpdaRequest:
    cpda = CpdaRequest.objects.select_for_update().filter(id=cpda_id).first()
    if not cpda:
        raise NotFoundError("CPDA request not found.")

    if cpda.verification_status != VerificationStatus.VERIFIED.value:
        raise BadRequestError("Cannot decide on unverified CPDA request.")

    service_rec = get_or_create_service_record(cpda.user_id)
    hierarchy = get_workflow_config("approval_hierarchy")
    next_role = get_next_authority(cpda.current_authority_role, service_rec.category, hierarchy)

    try:
        validate_decision(
            outcome=outcome,
            current_status=cpda.status,
            remarks=remarks,
            can_forward=next_role is not None,
        )
    except Exception as e:
        raise BadRequestError(str(e)) from e

    if outcome == DecisionOutcome.FORWARDED.value:
        cpda.status = ClaimStatus.FORWARDED.value
        cpda.current_authority_role = next_role or cpda.current_authority_role
        notify_msg = f"Your CPDA claim has been forwarded to {cpda.current_authority_role.upper()}."
    elif outcome == DecisionOutcome.APPROVED.value:
        cpda.status = ClaimStatus.APPROVED.value
        cpda.disbursement_status = PaymentStatus.PROCESSING.value
        notify_msg = "Your CPDA claim was approved and sent to Accountant for disbursement."
    else:
        cpda.status = ClaimStatus.REJECTED.value
        notify_msg = f"Your CPDA claim was rejected. Remarks: {remarks}"

    hist = list(cpda.approval_history or [])
    hist.append({
        "action": outcome,
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "remarks": remarks,
        "timestamp": timezone.now().isoformat(),
    })
    cpda.approval_history = hist
    cpda.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=f"cpda_{outcome}",
        entity_type="cpda_request",
        entity_id=cpda.id,
        details={"outcome": outcome, "remarks": remarks},
    )

    send_hr_notification(
        user_id=cpda.user_id,
        title=f"CPDA Claim {outcome.capitalize()}",
        message=notify_msg,
        category=outcome,
        link=f"/hr/cpda/{cpda.id}",
    )

    return cpda


@transaction.atomic
def settle_cpda_claim(
    *,
    cpda_id: int,
    passed_amount: Decimal,
    voucher_no: str,
    remarks: str,
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> CpdaRequest:
    """Accountant verifies financial correctness, settles claim, and updates CPDA balance (BR-HR-022, BR-HR-035)."""
    cpda = CpdaRequest.objects.select_for_update().filter(id=cpda_id).first()
    if not cpda:
        raise NotFoundError("CPDA request not found.")

    if cpda.status != ClaimStatus.APPROVED.value:
        raise BadRequestError("Only approved CPDA claims can be settled.")

    try:
        validate_financial_settlement(passed_amount=passed_amount, reference_id=voucher_no)
    except Exception as e:
        raise BadRequestError(str(e)) from e

    cpda.passed_amount = passed_amount
    cpda.disbursement_status = PaymentStatus.PAID.value
    cpda.status = ClaimStatus.SETTLED.value
    cpda.disbursement_details = {
        "passed_amount": str(passed_amount),
        "voucher_no": voucher_no,
        "accountant_id": actor_id,
        "accountant_name": actor_username,
        "disbursed_at": timezone.now().isoformat(),
        "remarks": remarks,
    }

    # Deduct CPDA balance from employee service record
    service_rec = EmployeeServiceRecord.objects.select_for_update().get(user_id=cpda.user_id)
    service_rec.cpda_balance = max(Decimal("0.00"), service_rec.cpda_balance - passed_amount)
    service_rec.save()

    hist = list(cpda.approval_history or [])
    hist.append({
        "action": "settled",
        "actor_id": actor_id,
        "actor_username": actor_username,
        "role": actor_role,
        "passed_amount": str(passed_amount),
        "voucher": voucher_no,
        "timestamp": timezone.now().isoformat(),
    })
    cpda.approval_history = hist
    cpda.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="settle_cpda_claim",
        entity_type="cpda_request",
        entity_id=cpda.id,
        details={"passed_amount": str(passed_amount), "voucher": voucher_no},
    )

    send_hr_notification(
        user_id=cpda.user_id,
        title="CPDA Claim Disbursed",
        message=f"Your CPDA claim has been settled for INR {passed_amount}. Voucher: {voucher_no}.",
        category="approval",
        link=f"/hr/cpda/{cpda.id}",
    )

    return cpda
