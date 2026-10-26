"""Services for Employee Leave Management (ELM).

All writes, database transactions, domain validation, balance mutations,
and audit trail logging live here.
"""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional
from django.db import transaction
from django.utils import timezone

from modules.leave.domain.calculator import calculate_leave_days
from modules.leave.domain.constants import (
    CATEGORY_POLICY,
    HalfDayOption,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadDecision,
)
from modules.leave.domain.rules import (
    calculate_resumption_adjustment,
    calculate_year_end_transition,
    check_leave_overlap,
    validate_leave_application,
    validate_substitute,
)
from modules.leave.domain.state_machine import (
    can_cancel_pre_start,
    can_extend,
    can_resume,
    can_withdraw,
    get_initial_status,
    transition_on_substitute_response,
    transition_on_unit_head_review,
)
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionLog,
    LeaveBalance,
    LeavePolicyConfig,
    LeaveRequest,
    VacationPeriod,
)
from modules.leave.selectors.leave_requests import (
    get_active_leaves_for_user,
    get_user_leave_request,
)


def ensure_user_balances(user_id: int, year: int, employee_kind: str = "staff") -> None:
    """Ensure an employee has initialized leave balances for the given year."""
    for category, policy in CATEGORY_POLICY.items():
        if category == LeaveCategory.VL and employee_kind != "faculty":
            continue
        entitlement = policy["annual_entitlement"]
        # Check if policy config overrides default
        cfg = LeavePolicyConfig.objects.filter(category=category.value).first()
        if cfg:
            entitlement = cfg.annual_entitlement

        LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year,
            category=category.value,
            defaults={
                "credited": entitlement,
                "availed": Decimal("0.0"),
                "balance": entitlement,
            },
        )


@transaction.atomic
def apply_leave(
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    reason: str,
    employee_kind: str = "staff",
    half_day: Optional[str] = None,
    substitute_user_id: Optional[int] = None,
    station_leave: bool = False,
    station_address: str = "",
    station_contact: str = "",
    station_start_date: Optional[date] = None,
    station_end_date: Optional[date] = None,
    medical_certificate_url: str = "",
    is_director: bool = False,
) -> LeaveRequest:
    """Submit a new leave application with domain validation and audit logging."""
    cat = LeaveCategory(category)
    half = HalfDayOption(half_day) if half_day else HalfDayOption.NONE
    year = start_date.year

    # 1. Ensure balances exist
    ensure_user_balances(user_id, year, employee_kind)
    balance_obj = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, year=year, category=cat.value
    )

    # 2. Compute leave days (BR-EL-010, BR-EL-011)
    closed_holidays = set(
        HolidayCalendar.objects.filter(year=year, published=True, is_restricted=False)
        .values_list("date", flat=True)
    )
    computed_days = calculate_leave_days(
        category=cat,
        start_date=start_date,
        end_date=end_date,
        half_day=half,
        closed_dates=closed_holidays,
    )

    # 3. Calendar & Vacation applicability (BR-EL-003, BR-EL-006, BR-EL-031)
    valid_rh_dates = set(
        HolidayCalendar.objects.filter(year=year, published=True, is_restricted=True)
        .values_list("date", flat=True)
    )
    vacation_periods = [
        (vp.start_date, vp.end_date)
        for vp in VacationPeriod.objects.filter(year=year)
    ]

    # 4. Domain rule validations
    validate_leave_application(
        category=cat,
        start_date=start_date,
        end_date=end_date,
        available_balance=balance_obj.balance,
        computed_days=computed_days,
        employee_kind=employee_kind,
        half_day=half,
        valid_rh_dates=valid_rh_dates,
        vacation_periods=vacation_periods,
        has_medical_certificate=bool(medical_certificate_url),
    )

    # 5. Overlap validation (BR-EL-012)
    existing_leaves = get_active_leaves_for_user(user_id)
    check_leave_overlap(
        existing_leaves=existing_leaves,
        new_start=start_date,
        new_end=end_date,
        new_category=cat,
        new_half_day=half,
    )

    # 6. Substitute validation (BR-EL-014)
    has_substitute = substitute_user_id is not None
    if has_substitute:
        sub_leaves = get_active_leaves_for_user(substitute_user_id)
        validate_substitute(
            applicant_user_id=user_id,
            substitute_user_id=substitute_user_id,
            substitute_leaves=sub_leaves,
            resp_start=start_date,
            resp_end=end_date,
        )

    # 7. Initial status determination (CW-EL-01)
    initial_status = get_initial_status(has_substitute=has_substitute, is_director=is_director)
    sub_status = SubstituteStatus.PENDING if has_substitute else SubstituteStatus.NOT_REQUIRED

    # 8. Create LeaveRequest
    leave_req = LeaveRequest.objects.create(
        user_id=user_id,
        category=cat.value,
        start_date=start_date,
        end_date=end_date,
        half_day=half.value,
        computed_days=computed_days,
        reason=reason,
        status=initial_status.value,
        substitute_user_id=substitute_user_id,
        substitute_status=sub_status.value,
        station_leave=station_leave,
        station_address=station_address,
        station_contact=station_contact,
        station_start_date=station_start_date,
        station_end_date=station_end_date,
        medical_certificate_url=medical_certificate_url,
    )

    # If Director self-sanction, deduct balance immediately
    if initial_status == LeaveStatus.APPROVED:
        balance_obj.availed += computed_days
        balance_obj.balance -= computed_days
        balance_obj.save(update_fields=["availed", "balance", "updated_at"])

    # 9. Audit trail log
    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=user_id,
        action="SUBMIT",
        from_status="NONE",
        to_status=initial_status.value,
        remarks=f"Submitted {computed_days} day(s) of {cat.value}",
    )

    return leave_req


@transaction.atomic
def respond_substitute(
    substitute_user_id: int,
    request_id: int,
    accepted: bool,
    remarks: str = "",
    is_director: bool = False,
) -> LeaveRequest:
    """Substitute accepts or declines responsibility (BR-EL-015)."""
    leave_req = LeaveRequest.objects.select_for_update().get(
        id=request_id, substitute_user_id=substitute_user_id
    )
    from_status = LeaveStatus(leave_req.status)
    sub_resp = SubstituteStatus.ACCEPTED if accepted else SubstituteStatus.DECLINED

    to_status = transition_on_substitute_response(
        current_status=from_status,
        substitute_response=sub_resp,
        is_director=is_director,
    )

    leave_req.substitute_status = sub_resp.value
    leave_req.substitute_remarks = remarks
    leave_req.status = to_status.value
    leave_req.save()

    # If Director self-sanctioned on substitute acceptance, deduct balance
    if to_status == LeaveStatus.APPROVED:
        bal = LeaveBalance.objects.select_for_update().get(
            user_id=leave_req.user_id,
            year=leave_req.start_date.year,
            category=leave_req.category,
        )
        bal.availed += leave_req.computed_days
        bal.balance -= leave_req.computed_days
        bal.save(update_fields=["availed", "balance", "updated_at"])

    action_label = "SUBSTITUTE_ACCEPT" if accepted else "SUBSTITUTE_DECLINE"
    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=substitute_user_id,
        action=action_label,
        from_status=from_status.value,
        to_status=to_status.value,
        remarks=remarks,
    )
    return leave_req


@transaction.atomic
def replace_substitute(
    applicant_user_id: int,
    request_id: int,
    new_substitute_user_id: int,
) -> LeaveRequest:
    """Nominate replacement substitute after decline (EL-UC-019)."""
    leave_req = LeaveRequest.objects.select_for_update().get(
        id=request_id, user_id=applicant_user_id
    )
    if leave_req.status != LeaveStatus.SUBSTITUTE_DECLINED.value:
        raise ValueError(f"Cannot replace substitute from status {leave_req.status}")

    # Validate new substitute
    sub_leaves = get_active_leaves_for_user(new_substitute_user_id)
    validate_substitute(
        applicant_user_id=applicant_user_id,
        substitute_user_id=new_substitute_user_id,
        substitute_leaves=sub_leaves,
        resp_start=leave_req.start_date,
        resp_end=leave_req.end_date,
    )

    from_status = leave_req.status
    leave_req.substitute_user_id = new_substitute_user_id
    leave_req.substitute_status = SubstituteStatus.PENDING.value
    leave_req.substitute_remarks = ""
    leave_req.status = LeaveStatus.PENDING_SUBSTITUTE.value
    leave_req.save()

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=applicant_user_id,
        action="SUBSTITUTE_REPLACE",
        from_status=from_status,
        to_status=LeaveStatus.PENDING_SUBSTITUTE.value,
        remarks=f"Nominated replacement substitute (User {new_substitute_user_id})",
    )
    return leave_req


@transaction.atomic
def review_unit_head(
    unit_head_user_id: int,
    request_id: int,
    decision: str,
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head reviews leave application (BR-EL-016, BR-EL-017)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id)
    from_status = LeaveStatus(leave_req.status)
    unit_decision = UnitHeadDecision(decision)

    to_status = transition_on_unit_head_review(
        current_status=from_status,
        category=leave_req.category,
        decision=unit_decision,
    )

    leave_req.unit_head_user_id = unit_head_user_id
    leave_req.unit_head_recommendation = unit_decision.value
    leave_req.unit_head_remarks = remarks
    leave_req.status = to_status.value
    leave_req.save()

    # Deduct balance if final approval on CL/RH
    if to_status == LeaveStatus.APPROVED and from_status == LeaveStatus.PENDING_UNIT_HEAD:
        bal = LeaveBalance.objects.select_for_update().get(
            user_id=leave_req.user_id,
            year=leave_req.start_date.year,
            category=leave_req.category,
        )
        bal.availed += leave_req.computed_days
        bal.balance -= leave_req.computed_days
        bal.save(update_fields=["availed", "balance", "updated_at"])

    # If cancellation was approved at Unit Head level
    if to_status == LeaveStatus.CANCELLED and from_status == LeaveStatus.CANCEL_REQUESTED:
        bal = LeaveBalance.objects.select_for_update().get(
            user_id=leave_req.user_id,
            year=leave_req.start_date.year,
            category=leave_req.category,
        )
        bal.availed -= leave_req.computed_days
        bal.balance += leave_req.computed_days
        bal.save(update_fields=["availed", "balance", "updated_at"])

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=unit_head_user_id,
        action=f"UNIT_HEAD_{unit_decision.value}",
        from_status=from_status.value,
        to_status=to_status.value,
        remarks=remarks,
    )
    return leave_req


@transaction.atomic
def decide_sanction(
    sanctioning_user_id: int,
    request_id: int,
    approved: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Final Sanctioning Authority decision for higher sanction leave (BR-EL-018)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id)
    from_status = LeaveStatus(leave_req.status)

    is_cancellation = (from_status == LeaveStatus.CANCEL_REQUESTED)
    if is_cancellation:
        to_status = LeaveStatus.CANCELLED if approved else LeaveStatus.APPROVED
    else:
        if from_status != LeaveStatus.PENDING_SANCTION:
            raise ValueError(f"Cannot make sanction decision from status {from_status.value}")
        to_status = LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED

    leave_req.sanctioning_authority_user_id = sanctioning_user_id
    leave_req.sanction_remarks = remarks
    leave_req.status = to_status.value
    leave_req.save()

    bal = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id,
        year=leave_req.start_date.year,
        category=leave_req.category,
    )

    if not is_cancellation and to_status == LeaveStatus.APPROVED:
        # Deduct balance on approval
        bal.availed += leave_req.computed_days
        bal.balance -= leave_req.computed_days
        bal.save(update_fields=["availed", "balance", "updated_at"])
    elif is_cancellation and to_status == LeaveStatus.CANCELLED:
        # Restore balance on cancellation approval
        bal.availed -= leave_req.computed_days
        bal.balance += leave_req.computed_days
        bal.save(update_fields=["availed", "balance", "updated_at"])

    action_label = "SANCTION_APPROVE" if approved else "SANCTION_REJECT"
    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=sanctioning_user_id,
        action=action_label,
        from_status=from_status.value,
        to_status=to_status.value,
        remarks=remarks,
    )
    return leave_req


@transaction.atomic
def withdraw_leave(user_id: int, request_id: int, reason: str = "") -> LeaveRequest:
    """Immediately withdraw a pending leave request before final approval (BR-EL-022)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id, user_id=user_id)
    from_status = LeaveStatus(leave_req.status)

    if not can_withdraw(from_status):
        raise ValueError(f"Leave request cannot be withdrawn from status {from_status.value}")

    leave_req.status = LeaveStatus.WITHDRAWN.value
    leave_req.save(update_fields=["status", "updated_at"])

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=user_id,
        action="WITHDRAW",
        from_status=from_status.value,
        to_status=LeaveStatus.WITHDRAWN.value,
        remarks=reason,
    )
    return leave_req


@transaction.atomic
def request_cancellation(user_id: int, request_id: int, cancellation_reason: str) -> LeaveRequest:
    """Request pre-start cancellation of an approved leave (BR-EL-023)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id, user_id=user_id)
    from_status = LeaveStatus(leave_req.status)
    today = timezone.localdate()

    if not can_cancel_pre_start(from_status, leave_req.start_date, today):
        raise ValueError("Cancellation can only be requested for approved leave before the start date.")

    leave_req.status = LeaveStatus.CANCEL_REQUESTED.value
    leave_req.cancellation_reason = cancellation_reason
    leave_req.save(update_fields=["status", "cancellation_reason", "updated_at"])

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=user_id,
        action="CANCEL_REQUEST",
        from_status=from_status.value,
        to_status=LeaveStatus.CANCEL_REQUESTED.value,
        remarks=cancellation_reason,
    )
    return leave_req


@transaction.atomic
def request_extension(
    user_id: int,
    base_request_id: int,
    extended_end_date: date,
    reason: str,
) -> LeaveRequest:
    """Request extension for ongoing EL, COL, or VL (BR-EL-025)."""
    base_req = LeaveRequest.objects.get(id=base_request_id, user_id=user_id)
    today = timezone.localdate()

    if not can_extend(LeaveStatus(base_req.status), base_req.category, base_req.start_date, base_req.end_date, today):
        raise ValueError("Extension is only available for ongoing approved EL, COL, or VL.")
    if extended_end_date <= base_req.end_date:
        raise ValueError("Extended end date must be after current approved end date.")

    # Calculate incremental additional days
    ext_start = base_req.end_date + timezone.timedelta(days=1)
    closed_holidays = set(
        HolidayCalendar.objects.filter(year=base_req.start_date.year, published=True, is_restricted=False)
        .values_list("date", flat=True)
    )
    incremental_days = calculate_leave_days(
        category=base_req.category,
        start_date=ext_start,
        end_date=extended_end_date,
        closed_dates=closed_holidays,
    )

    bal = LeaveBalance.objects.get(
        user_id=user_id, year=base_req.start_date.year, category=base_req.category
    )
    if incremental_days > bal.balance:
        raise ValueError(f"Insufficient leave balance for extension: {incremental_days} needed, {bal.balance} left.")

    ext_req = LeaveRequest.objects.create(
        user_id=user_id,
        category=base_req.category,
        start_date=ext_start,
        end_date=extended_end_date,
        computed_days=incremental_days,
        reason=f"[Extension of #{base_req.id}] {reason}",
        status=LeaveStatus.PENDING_UNIT_HEAD.value,
        extension_base_request_id=base_req.id,
        extension_days=incremental_days,
        substitute_user_id=base_req.substitute_user_id,
        substitute_status=SubstituteStatus.ACCEPTED.value,
    )

    LeaveActionLog.objects.create(
        leave_request_id=ext_req.id,
        actor_user_id=user_id,
        action="EXTENSION_REQUEST",
        from_status="NONE",
        to_status=LeaveStatus.PENDING_UNIT_HEAD.value,
        remarks=f"Requested {incremental_days} incremental days extension for leave #{base_req.id}",
    )
    return ext_req


@transaction.atomic
def submit_resumption(
    user_id: int,
    request_id: int,
    actual_resumption_date: date,
    remarks: str = "",
) -> LeaveRequest:
    """Submit resumption declaration after returning from EL, COL, or VL (BR-EL-027)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id, user_id=user_id)
    from_status = LeaveStatus(leave_req.status)

    if not can_resume(from_status, leave_req.category):
        raise ValueError("Resumption can only be submitted for approved EL, COL, or VL.")

    leave_req.status = LeaveStatus.RESUMED.value
    leave_req.resumption_date = actual_resumption_date
    leave_req.resumption_remarks = remarks
    leave_req.save(update_fields=["status", "resumption_date", "resumption_remarks", "updated_at"])

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=user_id,
        action="RESUMPTION_SUBMIT",
        from_status=from_status.value,
        to_status=LeaveStatus.RESUMED.value,
        remarks=f"Actual resumption date: {actual_resumption_date}. {remarks}",
    )
    return leave_req


@transaction.atomic
def review_resumption(
    reviewer_user_id: int,
    request_id: int,
    remarks: str = "",
) -> LeaveRequest:
    """Sanctioning Authority reviews resumption and adjusts balance (BR-EL-028)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if leave_req.status != LeaveStatus.RESUMED.value:
        raise ValueError(f"Cannot review resumption from status {leave_req.status}")

    closed_holidays = set(
        HolidayCalendar.objects.filter(year=leave_req.start_date.year, published=True, is_restricted=False)
        .values_list("date", flat=True)
    )

    outcome, actual_days, adjustment = calculate_resumption_adjustment(
        approved_days=leave_req.computed_days,
        approved_start=leave_req.start_date,
        approved_end=leave_req.end_date,
        actual_resumption_date=leave_req.resumption_date,
        category=leave_req.category,
        closed_dates=closed_holidays,
    )

    # Adjust balance if early or late
    bal = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id,
        year=leave_req.start_date.year,
        category=leave_req.category,
    )
    if adjustment != Decimal("0.0"):
        bal.availed += adjustment
        bal.balance -= adjustment
        bal.save(update_fields=["availed", "balance", "updated_at"])

    from_status = leave_req.status
    leave_req.status = LeaveStatus.RESUMPTION_REVIEWED.value
    leave_req.resumption_status = outcome.value
    leave_req.computed_days = actual_days
    leave_req.save()

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=reviewer_user_id,
        action=f"RESUMPTION_REVIEW_{outcome.value}",
        from_status=from_status,
        to_status=LeaveStatus.RESUMPTION_REVIEWED.value,
        remarks=f"{outcome.value} resumption reviewed. Balance adjustment: {adjustment} day(s). {remarks}",
    )
    return leave_req


@transaction.atomic
def record_offline_leave(
    admin_user_id: int,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    reason: str,
    offline_reference: str,
    employee_kind: str = "staff",
) -> LeaveRequest:
    """Record leave already sanctioned offline by Leave Administrator (BR-EL-029)."""
    cat = LeaveCategory(category)
    year = start_date.year
    ensure_user_balances(user_id, year, employee_kind)

    closed_holidays = set(
        HolidayCalendar.objects.filter(year=year, published=True, is_restricted=False)
        .values_list("date", flat=True)
    )
    computed_days = calculate_leave_days(
        category=cat,
        start_date=start_date,
        end_date=end_date,
        closed_dates=closed_holidays,
    )

    bal = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, year=year, category=cat.value
    )
    bal.availed += computed_days
    bal.balance -= computed_days
    bal.save(update_fields=["availed", "balance", "updated_at"])

    leave_req = LeaveRequest.objects.create(
        user_id=user_id,
        category=cat.value,
        start_date=start_date,
        end_date=end_date,
        computed_days=computed_days,
        reason=reason,
        status=LeaveStatus.APPROVED.value,
        offline_entry=True,
        offline_reference=offline_reference,
    )

    LeaveActionLog.objects.create(
        leave_request_id=leave_req.id,
        actor_user_id=admin_user_id,
        action="OFFLINE_SYNC",
        from_status="NONE",
        to_status=LeaveStatus.APPROVED.value,
        remarks=f"Retrospectively recorded offline sanction (Ref: {offline_reference})",
    )
    return leave_req


@transaction.atomic
def execute_year_end_processing(year: int) -> dict[str, Any]:
    """Execute year-end leave account processing per BR-EL-002..008, EL-UC-020."""
    balances = LeaveBalance.objects.filter(year=year)
    results = {"lapsed": 0, "carried_forward": 0, "vl_converted_to_el": 0}

    # Group balances by user
    user_ids = balances.values_list("user_id", flat=True).distinct()
    next_year = year + 1

    for uid in user_ids:
        user_bals = LeaveBalance.objects.filter(user_id=uid, year=year)
        for bal in user_bals:
            lapsed, carried, converted_el = calculate_year_end_transition(
                category=bal.category, current_balance=bal.balance
            )
            if lapsed > Decimal("0.0"):
                results["lapsed"] += int(lapsed)
            if carried > Decimal("0.0"):
                results["carried_forward"] += int(carried)
            if converted_el > Decimal("0.0"):
                results["vl_converted_to_el"] += int(converted_el)

            # Create or update next year balance with carried / converted amounts
            next_bal, _ = LeaveBalance.objects.get_or_create(
                user_id=uid,
                year=next_year,
                category=bal.category,
                defaults={
                    "credited": Decimal("0.0"),
                    "availed": Decimal("0.0"),
                    "balance": Decimal("0.0"),
                },
            )
            if carried > Decimal("0.0"):
                next_bal.credited += carried
                next_bal.balance += carried
                next_bal.save()

            if converted_el > Decimal("0.0"):
                el_bal, _ = LeaveBalance.objects.get_or_create(
                    user_id=uid,
                    year=next_year,
                    category=LeaveCategory.EL.value,
                    defaults={
                        "credited": Decimal("0.0"),
                        "availed": Decimal("0.0"),
                        "balance": Decimal("0.0"),
                    },
                )
                el_bal.credited += converted_el
                el_bal.balance += converted_el
                el_bal.save()

    return results
