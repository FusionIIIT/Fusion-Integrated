from __future__ import annotations

from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveRequest, SubstituteAssignment, LeaveActionHistory, LeaveBalance
from modules.elm.domain.rules import count_leave_days, validate_station_leave, can_substitute, intervals_overlap


@transaction.atomic
def apply_for_leave(
    *,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    half_day: str | None = None,
    purpose: str,
    is_station_leave: bool = False,
    destination: str = "",
    emergency_contact: str = "",
    substitute_id: int | None = None,
    closed_dates: set[date] | None = None,
) -> LeaveRequest:
    # 1. Calculate leave days
    leave_days = count_leave_days(category, start_date, end_date, half_day=half_day, closed_dates=closed_dates)

    # 2. BR-EL-013: Validate station leave
    if not validate_station_leave(is_station_leave, destination, emergency_contact):
        raise DomainError("Station leave requires valid destination and emergency contact details.")

    # 3. BR-EL-014: Validate substitute
    if substitute_id is not None:
        if not can_substitute(user_id, substitute_id):
            raise DomainError("Applicant cannot nominate themselves as substitute.")

    # 4. BR-EL-012: Check non-overlap with active leave requests
    existing_requests = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=["submitted", "awaiting_substitute", "under_review", "recommended", "sanctioned"],
    )
    for req in existing_requests:
        if intervals_overlap(start_date, end_date, half_day, req.start_date, req.end_date, req.half_day):
            raise ConflictError("Requested period overlaps with an existing leave request.")

    # 5. Check leave balance
    year = start_date.year
    balance_obj = LeaveBalance.objects.filter(user_id=user_id, category=category, year=year).first()
    if not balance_obj:
        raise NotFoundError(f"No leave balance found for category '{category}' in year {year}.")
    if balance_obj.balance < leave_days:
        raise DomainError(f"Insufficient balance: requested {leave_days}, available {balance_obj.balance}.")

    # 6. Initial state machine routing
    status = "awaiting_substitute" if substitute_id else "under_review"

    leave_request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        leave_days=leave_days,
        purpose=purpose,
        status=status,
        is_station_leave=is_station_leave,
        destination=destination,
        emergency_contact=emergency_contact,
        substitute_id=substitute_id,
    )

    if substitute_id:
        SubstituteAssignment.objects.create(
            leave_request=leave_request,
            substitute_id=substitute_id,
            status="pending",
        )

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=user_id,
        action="submitted",
        comments="Leave application submitted.",
    )

    return leave_request


@transaction.atomic
def respond_substitute(*, substitute_id: int, request_id: int, action: str, remarks: str = "") -> SubstituteAssignment:
    if action not in ["accept", "decline"]:
        raise DomainError("Action must be 'accept' or 'decline'.")

    substitute_assignment = SubstituteAssignment.objects.filter(
        substitute_id=substitute_id,
        leave_request_id=request_id,
        status="pending",
    ).first()
    if not substitute_assignment:
        raise NotFoundError("Pending substitute request not found for this user.")

    leave_request = substitute_assignment.leave_request
    if action == "accept":
        substitute_assignment.status = "accepted"
        leave_request.status = "under_review"
    else:
        substitute_assignment.status = "declined"
        leave_request.status = "awaiting_substitute"

    substitute_assignment.remarks = remarks
    substitute_assignment.responded_at = timezone.now()
    substitute_assignment.save()
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=substitute_id,
        action=f"substitute_{action}ed",
        comments=remarks,
    )

    return substitute_assignment


@transaction.atomic
def review_leave_request(*, reviewer_id: int, request_id: int, action: str, reason: str = "") -> LeaveRequest:
    if action not in ["approve", "reject", "recommend"]:
        raise DomainError("Action must be 'approve', 'reject', or 'recommend'.")

    leave_request = LeaveRequest.objects.filter(id=request_id).first()
    if not leave_request:
        raise NotFoundError(f"Leave request {request_id} not found.")

    if action == "approve":
        # Final approval applies directly to CL/RH
        leave_request.status = "sanctioned"
        leave_request.save()

        # Deduct balance
        balance_obj = LeaveBalance.objects.get(
            user_id=leave_request.user_id,
            category=leave_request.category,
            year=leave_request.start_date.year,
        )
        balance_obj.balance -= leave_request.leave_days
        balance_obj.availed += leave_request.leave_days
        balance_obj.save()

    elif action == "recommend":
        # Higher sanction leave recommendation
        leave_request.status = "recommended"
        leave_request.save()

    elif action == "reject":
        leave_request.status = "rejected"
        leave_request.rejection_reason = reason
        leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=reviewer_id,
        action=action,
        comments=reason,
    )

    return leave_request


@transaction.atomic
def withdraw_leave_request(*, user_id: int, request_id: int) -> LeaveRequest:
    leave_request = LeaveRequest.objects.filter(id=request_id, user_id=user_id).first()
    if not leave_request:
        raise NotFoundError("Leave request not found or not owned by user.")

    if leave_request.status not in ["submitted", "awaiting_substitute", "under_review", "recommended"]:
        raise DomainError("Cannot withdraw request that has already been sanctioned, rejected, or completed.")

    leave_request.status = "withdrawn"
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=user_id,
        action="withdrawn",
        comments="Withdrawn by applicant.",
    )

    return leave_request


@transaction.atomic
def cancel_approved_leave(*, user_id: int, request_id: int, today_date: date) -> LeaveRequest:
    leave_request = LeaveRequest.objects.filter(id=request_id, user_id=user_id).first()
    if not leave_request:
        raise NotFoundError("Leave request not found or not owned by user.")

    if leave_request.status != "sanctioned":
        raise DomainError("Only sanctioned leave can be cancelled.")

    if today_date >= leave_request.start_date:
        raise DomainError("Cannot cancel leave that has already started.")

    # Restore balance
    balance_obj = LeaveBalance.objects.get(
        user_id=leave_request.user_id,
        category=leave_request.category,
        year=leave_request.start_date.year,
    )
    balance_obj.balance += leave_request.leave_days
    balance_obj.availed -= leave_request.leave_days
    balance_obj.save()

    leave_request.status = "cancelled"
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=user_id,
        action="cancelled",
        comments="Cancelled by applicant before start date.",
    )

    return leave_request


@transaction.atomic
def extend_leave(
    *,
    user_id: int,
    request_id: int,
    new_end_date: date,
    reason: str = "",
    closed_dates: set[date] | None = None,
) -> LeaveRequest:
    """CFR-EL-020 & BR-EL-025: Extend ongoing EL/COL/VL posting incremental days."""
    leave_request = LeaveRequest.objects.filter(id=request_id, user_id=user_id).first()
    if not leave_request:
        raise NotFoundError("Leave request not found or not owned by user.")

    if leave_request.status != "sanctioned":
        raise DomainError("Only sanctioned leave may be extended.")

    if leave_request.category not in ["EL", "COL", "VL"]:
        raise DomainError("Extensions only permitted for ongoing EL, COL, or VL.")

    if new_end_date <= leave_request.end_date:
        raise DomainError("Extension new end date must be after original end date.")

    # Calculate incremental days
    inc_start = leave_request.end_date + timezone.timedelta(days=1)
    incremental_days = count_leave_days(
        leave_request.category,
        inc_start,
        new_end_date,
        closed_dates=closed_dates,
    )

    balance_obj = LeaveBalance.objects.get(
        user_id=user_id,
        category=leave_request.category,
        year=leave_request.start_date.year,
    )
    if balance_obj.balance < incremental_days:
        raise DomainError(f"Insufficient balance for extension: needed {incremental_days}, have {balance_obj.balance}.")

    # Deduct incremental balance and update leave
    balance_obj.balance -= incremental_days
    balance_obj.availed += incremental_days
    balance_obj.save()

    leave_request.end_date = new_end_date
    leave_request.leave_days += incremental_days
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=user_id,
        action="extended",
        comments=f"Extended to {new_end_date} (+{incremental_days} days). {reason}".strip(),
    )

    return leave_request


@transaction.atomic
def execute_year_end_processing(*, user_id: int, year: int) -> dict[str, Decimal]:
    """CFR-EL-028 & BR-EL-007, BR-EL-008: Year-end processing and VL-to-EL conversion."""
    from modules.elm.domain.rules import calculate_vl_to_el_conversion, ENTITLEMENTS

    vl_balance = LeaveBalance.objects.filter(user_id=user_id, category="VL", year=year).first()
    el_balance = LeaveBalance.objects.filter(user_id=user_id, category="EL", year=year).first()

    unutilized_vl = vl_balance.balance if vl_balance else Decimal("0.00")
    current_el = el_balance.balance if el_balance else Decimal("0.00")

    credited_el, forfeited_vl, new_el_bal = calculate_vl_to_el_conversion(
        unutilized_vl=unutilized_vl,
        current_el=current_el,
    )

    # Next year balances
    next_year = year + 1

    # Carry forward EL (with credited converted VL) + new annual grant
    LeaveBalance.objects.update_or_create(
        user_id=user_id,
        category="EL",
        year=next_year,
        defaults={
            "credited": new_el_bal + ENTITLEMENTS["EL"],
            "availed": Decimal("0.00"),
            "balance": new_el_bal + ENTITLEMENTS["EL"],
        },
    )

    # Reset fresh VL for next year (VL itself never carries forward as VL)
    LeaveBalance.objects.update_or_create(
        user_id=user_id,
        category="VL",
        year=next_year,
        defaults={
            "credited": ENTITLEMENTS["VL"],
            "availed": Decimal("0.00"),
            "balance": ENTITLEMENTS["VL"],
        },
    )

    # CL and RH lapse at year end, fresh entitlement created
    for cat in ["CL", "RH"]:
        LeaveBalance.objects.update_or_create(
            user_id=user_id,
            category=cat,
            year=next_year,
            defaults={
                "credited": ENTITLEMENTS[cat],
                "availed": Decimal("0.00"),
                "balance": ENTITLEMENTS[cat],
            },
        )

    return {
        "credited_el_from_vl": credited_el,
        "forfeited_vl": forfeited_vl,
        "carried_forward_el": new_el_bal,
    }


@transaction.atomic
def submit_resumption_of_duty(
    *,
    user_id: int,
    request_id: int,
    actual_resumption_date: date,
    details: str = "",
) -> LeaveRequest:
    """CFR-EL-021 & EL-UC-010 / CW-EL-04: Submit Resumption of Duty."""
    leave_request = LeaveRequest.objects.filter(id=request_id, user_id=user_id).first()
    if not leave_request:
        raise NotFoundError("Leave request not found or not owned by user.")

    if leave_request.status != "sanctioned":
        raise DomainError("Resumption can only be submitted for sanctioned leave.")

    leave_request.resumption_date = actual_resumption_date
    leave_request.resumption_status = "pending"
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=user_id,
        action="resumption_submitted",
        comments=f"Actual resumption on {actual_resumption_date}. {details}".strip(),
    )

    return leave_request


@transaction.atomic
def review_resumption(
    *,
    reviewer_id: int,
    request_id: int,
    review_remarks: str = "",
    closed_dates: set[date] | None = None,
) -> LeaveRequest:
    """CFR-EL-021 & EL-UC-011, BR-EL-027, BR-EL-028: Normal, early, and late resumption outcome."""
    leave_request = LeaveRequest.objects.filter(id=request_id).first()
    if not leave_request or leave_request.resumption_status != "pending":
        raise NotFoundError("Leave request not found or has no pending resumption.")

    actual_resumption = leave_request.resumption_date
    expected_resumption = leave_request.end_date + timezone.timedelta(days=1)

    if actual_resumption < expected_resumption:
        # Early resumption: actual leave ended earlier than expected
        actual_end_date = actual_resumption - timezone.timedelta(days=1)
        if actual_end_date >= leave_request.start_date:
            actual_days = count_leave_days(
                leave_request.category,
                leave_request.start_date,
                actual_end_date,
                half_day=leave_request.half_day,
                closed_dates=closed_dates,
            )
            days_saved = leave_request.leave_days - actual_days
            if days_saved > 0:
                # Restore balance for unused days
                balance_obj = LeaveBalance.objects.get(
                    user_id=leave_request.user_id,
                    category=leave_request.category,
                    year=leave_request.start_date.year,
                )
                balance_obj.balance += days_saved
                balance_obj.availed -= days_saved
                balance_obj.save()
                leave_request.leave_days = actual_days
                leave_request.end_date = actual_end_date

    elif actual_resumption > expected_resumption:
        # Late resumption: actual leave extended beyond expected
        actual_end_date = actual_resumption - timezone.timedelta(days=1)
        actual_days = count_leave_days(
            leave_request.category,
            leave_request.start_date,
            actual_end_date,
            half_day=leave_request.half_day,
            closed_dates=closed_dates,
        )
        excess_days = actual_days - leave_request.leave_days
        if excess_days > 0:
            balance_obj = LeaveBalance.objects.get(
                user_id=leave_request.user_id,
                category=leave_request.category,
                year=leave_request.start_date.year,
            )
            balance_obj.balance -= excess_days
            balance_obj.availed += excess_days
            balance_obj.save()
            leave_request.leave_days = actual_days
            leave_request.end_date = actual_end_date

    leave_request.resumption_status = "completed"
    leave_request.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_request,
        actor_id=reviewer_id,
        action="resumption_reviewed",
        comments=review_remarks or "Resumption verified and leave adjusted.",
    )

    return leave_request


@transaction.atomic
def record_offline_sanctioned_leave(
    *,
    admin_id: int,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    sanction_reference: str,
    closed_dates: set[date] | None = None,
) -> LeaveRequest:
    """CFR-EL-027, EL-UC-016 & BR-EL-029: Record already-sanctioned offline leave."""
    leave_days = count_leave_days(category, start_date, end_date, closed_dates=closed_dates)

    balance_obj = LeaveBalance.objects.filter(
        user_id=user_id,
        category=category,
        year=start_date.year,
    ).first()
    if not balance_obj:
        raise NotFoundError("Leave balance not found for this user.")

    # Deduct balance immediately
    balance_obj.balance -= leave_days
    balance_obj.availed += leave_days
    balance_obj.save()

    req = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        leave_days=leave_days,
        purpose=purpose,
        status="sanctioned",
        is_offline_recorded=True,
        offline_reference=sanction_reference,
    )

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=admin_id,
        action="offline_recorded",
        comments=f"Offline sanctioned leave recorded. Ref: {sanction_reference}",
    )

    return req


