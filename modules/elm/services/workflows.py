"""Workflow lifecycle actions: Substitute, Unit Head, Sanction, Cancellation, Extension, Resumption."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.state_machine import LeaveStateMachine
from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory


@transaction.atomic
def respond_substitute(substitute_user_id: int, leave_id: int, accepted: bool) -> LeaveRequest:
    """Substitute accepts or declines responsibility coverage (CW-EL-01, EL-UC-002, BR-EL-015)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id, substitute_user_id=substitute_user_id).first()
    if not req:
        raise ValueError("Substitute request not found.")

    res = LeaveStateMachine.process_substitute_response(
        current_status=req.status,
        accepted=accepted,
        is_director=False,
    )
    if not res.success:
        raise ValueError(res.message)

    old_status = req.status
    req.status = res.new_status.value
    req.substitute_status = "accepted" if accepted else "declined"
    req.save(update_fields=["status", "substitute_status", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=substitute_user_id,
        remarks=f"Substitute {'accepted' if accepted else 'declined'} coverage.",
    )
    return req


@transaction.atomic
def review_unit_head(
    unit_head_user_id: int,
    leave_id: int,
    decision: str,  # approve, reject, recommend, not_recommend
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head review (CW-EL-01, EL-UC-003, BR-EL-016, BR-EL-017)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id).first()
    if not req:
        raise ValueError("Leave request not found.")

    res = LeaveStateMachine.unit_head_review(
        category=req.category,
        decision=decision.lower(),
        has_establishment_step=True,
    )
    if not res.success:
        raise ValueError(res.message)

    old_status = req.status
    req.status = res.new_status.value
    req.unit_head_user_id = unit_head_user_id
    req.unit_head_recommendation = decision.lower()
    req.unit_head_remarks = remarks

    # If CL/RH and approved, deduct balance immediately
    if req.status == "approved":
        req.sanctioned_at = timezone.now()
        _deduct_leave_balance(req)

    req.save()

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=unit_head_user_id,
        remarks=f"Unit Head decided: {decision}. {remarks}".strip(),
    )
    return req


@transaction.atomic
def route_establishment(establishment_user_id: int, leave_id: int, remarks: str = "") -> LeaveRequest:
    """Establishment verifies and routes higher-sanction request (CW-EL-01, EL-UC-004, BR-EL-018)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id).first()
    if not req:
        raise ValueError("Leave request not found.")

    res = LeaveStateMachine.establishment_route()
    old_status = req.status
    req.status = res.new_status.value
    req.establishment_user_id = establishment_user_id
    req.save(update_fields=["status", "establishment_user_id", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=establishment_user_id,
        remarks=f"Establishment routed: {remarks}".strip(),
    )
    return req


@transaction.atomic
def make_sanction_decision(
    authority_user_id: int,
    leave_id: int,
    approve: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Final sanction decision (CW-EL-01, EL-UC-005, BR-EL-019)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id).first()
    if not req:
        raise ValueError("Leave request not found.")

    res = LeaveStateMachine.final_sanction(approve)
    old_status = req.status
    req.status = res.new_status.value
    req.sanctioning_authority_user_id = authority_user_id
    req.final_decision_remarks = remarks

    if approve:
        req.sanctioned_at = timezone.now()
        _deduct_leave_balance(req)

    req.save()

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=authority_user_id,
        remarks=f"Final decision: {'Approved' if approve else 'Rejected'}. {remarks}".strip(),
    )
    return req


@transaction.atomic
def request_cancellation(user_id: int, leave_id: int) -> LeaveRequest:
    """Request pre-start cancellation of approved leave (CW-EL-02, EL-UC-008, BR-EL-023)."""
    req = LeaveRequest.objects.select_for_update().filter(user_id=user_id, pk=leave_id).first()
    if not req:
        raise ValueError("Leave application not found.")

    if date.today() >= req.start_date:
        raise ValueError("Cancellation only allowed before leave start date. Use Resumption instead.")

    res = LeaveStateMachine.request_cancellation(req.status)
    if not res.success:
        raise ValueError(res.message)

    old_status = req.status
    req.status = res.new_status.value
    req.save(update_fields=["status", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=user_id,
        remarks="Cancellation requested by employee.",
    )
    return req


@transaction.atomic
def review_cancellation(actor_user_id: int, leave_id: int, approve: bool) -> LeaveRequest:
    """Review and decide on cancellation request. Restores balance on approval (CW-EL-02)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id).first()
    if not req:
        raise ValueError("Leave request not found.")

    res = LeaveStateMachine.review_cancellation(
        category=req.category,
        approved=approve,
        current_status=req.status,
    )
    if not res.success:
        raise ValueError(res.message)

    old_status = req.status
    req.status = res.new_status.value

    # On approved cancellation, restore deducted balance (BR-EL-023)
    if req.status == "cancelled":
        _refund_leave_balance(req, req.days_calculated, "Cancellation approved - balance restored")

    req.save()

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=actor_user_id,
        remarks=f"Cancellation {'Approved' if approve else 'Rejected'}.",
    )
    return req


@transaction.atomic
def submit_resumption(user_id: int, leave_id: int, actual_date: date, remarks: str = "") -> LeaveRequest:
    """Submit resumption of duty after leave (CW-EL-04, EL-UC-010, BR-EL-027)."""
    req = LeaveRequest.objects.select_for_update().filter(user_id=user_id, pk=leave_id, status="approved").first()
    if not req:
        raise ValueError("Approved leave request not found.")

    req.actual_resumption_date = actual_date
    req.resumption_remarks = remarks
    req.status = "resumption_pending"
    req.save(update_fields=["actual_resumption_date", "resumption_remarks", "status", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status="approved",
        to_status="resumption_pending",
        actor_user_id=user_id,
        remarks=f"Resumed on {actual_date}. {remarks}".strip(),
    )
    return req


@transaction.atomic
def review_resumption(authority_user_id: int, leave_id: int) -> LeaveRequest:
    """Review resumption and adjust balance for early or late return (CW-EL-04, BR-EL-028)."""
    req = LeaveRequest.objects.select_for_update().filter(pk=leave_id, status="resumption_pending").first()
    if not req:
        raise ValueError("Resumption request not found.")

    # Calculate difference
    if req.actual_resumption_date and req.actual_resumption_date < req.end_date:
        # Early return: refund excess days
        excess = Decimal(str((req.end_date - req.actual_resumption_date).days))
        _refund_leave_balance(req, excess, "Early resumption balance refund")
    elif req.actual_resumption_date and req.actual_resumption_date > req.end_date:
        # Late return: deduct extra days
        extra = Decimal(str((req.actual_resumption_date - req.end_date).days))
        _deduct_additional_balance(req, extra, "Late resumption extra deduction")

    old_status = req.status
    req.status = "resumed"
    req.save(update_fields=["status", "updated_at"])

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status=old_status,
        to_status=req.status,
        actor_user_id=authority_user_id,
        remarks="Resumption verified and leave record closed.",
    )
    return req


@transaction.atomic
def record_offline_leave(
    admin_user_id: int,
    target_user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    days: Decimal,
    reference_no: str,
    reason: str,
) -> LeaveRequest:
    """Record already-sanctioned offline paper leave (BR-EL-029, EL-UC-016)."""
    req = LeaveRequest.objects.create(
        user_id=target_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        days_calculated=days,
        reason=reason,
        status="approved",
        is_offline_sanctioned=True,
        offline_sanction_reference=reference_no,
        sanctioning_authority_user_id=admin_user_id,
        sanctioned_at=timezone.now(),
    )

    _deduct_leave_balance(req)

    LeaveTransitionHistory.objects.create(
        leave_request=req,
        from_status="draft",
        to_status="approved",
        actor_user_id=admin_user_id,
        remarks=f"Offline sanctioned leave recorded. Ref: {reference_no}",
    )
    return req


# -----------------------------------------------------------------------------
# Internal Balance Adjustment Helpers
# -----------------------------------------------------------------------------
def _deduct_leave_balance(req: LeaveRequest) -> None:
    bal = LeaveBalance.objects.select_for_update().filter(
        user_id=req.user_id, year=req.start_date.year, category=req.category
    ).first()
    if bal:
        bal.availed_balance += req.days_calculated
        bal.save(update_fields=["availed_balance", "updated_at"])

    LeaveAccountTransaction.objects.create(
        user_id=req.user_id,
        year=req.start_date.year,
        category=req.category,
        transaction_type="deduction",
        days=req.days_calculated,
        reference_leave_id=req.id,
        description=f"Approved leave deduction for #{req.id}",
    )


def _refund_leave_balance(req: LeaveRequest, refund_days: Decimal, desc: str) -> None:
    bal = LeaveBalance.objects.select_for_update().filter(
        user_id=req.user_id, year=req.start_date.year, category=req.category
    ).first()
    if bal:
        bal.availed_balance = max(Decimal("0.00"), bal.availed_balance - refund_days)
        bal.save(update_fields=["availed_balance", "updated_at"])

    LeaveAccountTransaction.objects.create(
        user_id=req.user_id,
        year=req.start_date.year,
        category=req.category,
        transaction_type="refund",
        days=refund_days,
        reference_leave_id=req.id,
        description=desc,
    )


def _deduct_additional_balance(req: LeaveRequest, extra_days: Decimal, desc: str) -> None:
    bal = LeaveBalance.objects.select_for_update().filter(
        user_id=req.user_id, year=req.start_date.year, category=req.category
    ).first()
    if bal:
        bal.availed_balance += extra_days
        bal.save(update_fields=["availed_balance", "updated_at"])

    LeaveAccountTransaction.objects.create(
        user_id=req.user_id,
        year=req.start_date.year,
        category=req.category,
        transaction_type="deduction",
        days=extra_days,
        reference_leave_id=req.id,
        description=desc,
    )
