"""Service layer orchestrating ELM leave operations, validations, extensions, resumptions, and SLAs."""
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone

from modules.elm.models import (
    LeavePolicyConfig,
    HolidayCalendar,
    AcademicVacationPeriod,
    LeaveBalance,
    LeaveRequest,
    LeaveActionHistory,
    LeaveExtension,
    LeaveResumption,
    OfflineSanctionRecord,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadRecommendation,
)
from modules.elm.domain.calculations import (
    calculate_leave_days,
    calculate_vl_to_el_conversion,
)
from modules.elm.domain.validation import (
    ValidationError,
    validate_category_eligibility,
    validate_restricted_holiday,
    validate_vacation_period,
    validate_no_overlap,
    validate_substitute,
)
from modules.elm.domain.state_machine import (
    determine_initial_status,
    process_substitute_action,
    process_unit_head_action,
    process_sanction_action,
    can_withdraw,
    can_request_cancellation,
    can_request_extension,
    can_submit_resumption,
)
from modules.elm.selectors.leaves import (
    get_published_rh_dates,
    get_closed_holiday_dates,
    get_active_vacation_intervals,
    get_active_user_leaves,
)


def get_or_create_policy() -> LeavePolicyConfig:
    cfg, _ = LeavePolicyConfig.objects.get_or_create(id=1)
    return cfg


@transaction.atomic
def initialize_user_balances(user_id: int, employee_kind: str, year: int) -> list[LeaveBalance]:
    """Initialize annual leave entitlements for an employee (BR-EL-002..009)."""
    cfg = get_or_create_policy()
    balances = []

    # CL: 8 days
    cl, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=LeaveCategory.CASUAL_LEAVE,
        defaults={"credited": cfg.cl_entitlement}
    )
    balances.append(cl)

    # RH: 2 days
    rh, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=LeaveCategory.RESTRICTED_HOLIDAY,
        defaults={"credited": cfg.rh_entitlement}
    )
    balances.append(rh)

    # SCL: 15 days
    scl, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=LeaveCategory.SPECIAL_CASUAL_LEAVE,
        defaults={"credited": cfg.scl_entitlement}
    )
    balances.append(scl)

    # COL: 20 days
    col, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=LeaveCategory.COMMUTED_LEAVE,
        defaults={"credited": cfg.col_entitlement}
    )
    balances.append(col)

    if employee_kind == "faculty":
        # Faculty gets 60 VL; EL comes from VL rollover
        vl, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, category=LeaveCategory.VACATION_LEAVE,
            defaults={"credited": cfg.vl_faculty_entitlement}
        )
        el, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, category=LeaveCategory.EARNED_LEAVE,
            defaults={"credited": 0.0}
        )
        balances.extend([vl, el])
    else:
        # Non-faculty gets 30 EL directly
        el, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, category=LeaveCategory.EARNED_LEAVE,
            defaults={"credited": cfg.el_non_faculty_entitlement}
        )
        balances.append(el)

    return balances


@transaction.atomic
def apply_for_leave(
    user_id: int,
    employee_kind: str,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    half_day: str = "none",
    is_station_leave: bool = False,
    station_address: str = "",
    station_contact: str = "",
    station_start_date: date | None = None,
    station_end_date: date | None = None,
    substitute_user_id: int | None = None,
    is_director: bool = False,
) -> LeaveRequest:
    """Submit a leave application with complete validations and state transitions."""
    # 1. Category eligibility
    validate_category_eligibility(category, employee_kind)

    # 2. Holiday and calendar validations
    year = start_date.year
    closed_holidays = get_closed_holiday_dates(year)
    if category == LeaveCategory.RESTRICTED_HOLIDAY:
        published_rh = get_published_rh_dates(year)
        validate_restricted_holiday(category, start_date, end_date, published_rh)
    elif category == LeaveCategory.VACATION_LEAVE:
        vacation_intervals = get_active_vacation_intervals()
        validate_vacation_period(category, start_date, end_date, vacation_intervals)

    # 3. Calculate duration
    duration = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        closed_holidays=closed_holidays,
    )
    if duration <= 0:
        raise ValidationError("Calculated leave duration is 0 days.")

    # 4. Check available balance
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=category,
        defaults={"credited": 0.0}
    )
    if balance.available_balance < duration:
        raise ValidationError(
            f"Insufficient {category} balance. Available: {balance.available_balance}, Requested: {duration}"
        )

    # 5. Overlap check for applicant
    existing_leaves = get_active_user_leaves(user_id)
    validate_no_overlap(start_date, end_date, half_day, existing_leaves)

    # 6. Substitute validation
    if substitute_user_id and not is_director:
        sub_leaves = [
            (l[0], l[1]) for l in get_active_user_leaves(substitute_user_id)
        ]
        validate_substitute(user_id, substitute_user_id, start_date, end_date, sub_leaves)
        substitute_status = SubstituteStatus.PENDING
    else:
        substitute_status = SubstituteStatus.NOT_APPLICABLE

    # 7. Initial workflow status (BR-EL-020 Director self-sanction)
    initial_status = determine_initial_status(
        has_substitute=bool(substitute_user_id and not is_director),
        is_director=is_director,
    )

    # 8. Create LeaveRequest
    leave_req = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        duration_days=duration,
        purpose=purpose,
        is_station_leave=is_station_leave,
        station_address=station_address,
        station_contact=station_contact,
        station_start_date=station_start_date,
        station_end_date=station_end_date,
        substitute_user_id=None if is_director else substitute_user_id,
        substitute_status=substitute_status,
        current_status=initial_status,
        final_decision_by_id=user_id if is_director else None,
    )

    # 9. Update balance
    if is_director:
        balance.consumed += duration
    else:
        balance.pending += duration
    balance.save()

    # 10. Audit log
    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=user_id,
        action="director_self_sanction" if is_director else "submit",
        previous_status="",
        new_status=initial_status,
        remarks="Self-sanctioned leave by Director" if is_director else "Leave request submitted",
    )

    return leave_req


@transaction.atomic
def respond_substitute(
    leave_id: int,
    substitute_user_id: int,
    action: str,  # "accept" or "decline"
    remarks: str = "",
) -> LeaveRequest:
    """Substitute accepts or declines responsibility (BR-EL-015, UC-EL-002)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.substitute_user_id != substitute_user_id:
        raise ValidationError("You are not the designated substitute for this request.")

    if leave_req.current_status != LeaveStatus.PENDING_SUBSTITUTE:
        raise ValidationError("This request is not currently awaiting substitute consent.")

    new_sub_status, new_wf_status = process_substitute_action(action)
    prev_status = leave_req.current_status

    leave_req.substitute_status = new_sub_status
    leave_req.current_status = new_wf_status
    leave_req.substitute_remarks = remarks
    leave_req.substitute_acted_at = timezone.now()
    leave_req.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=substitute_user_id,
        action=f"substitute_{action}",
        previous_status=prev_status,
        new_status=new_wf_status,
        remarks=remarks or f"Substitute {action}ed responsibility",
    )
    return leave_req


@transaction.atomic
def review_unit_head(
    leave_id: int,
    actor_id: int,
    action: str,  # "approve", "reject", "recommend", "not_recommend"
    remarks: str = "",
    has_establishment_step: bool = False,
) -> LeaveRequest:
    """Unit Head review / decision (BR-EL-016, BR-EL-017, UC-EL-003)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.current_status != LeaveStatus.PENDING_UNIT_HEAD:
        raise ValidationError("Request is not awaiting Unit Head review.")

    rec, new_status = process_unit_head_action(
        leave_req.category, action, has_establishment_step=has_establishment_step
    )
    prev_status = leave_req.current_status

    leave_req.unit_head_recommendation = rec
    leave_req.unit_head_remarks = remarks
    leave_req.unit_head_acted_at = timezone.now()
    leave_req.current_status = new_status

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id, year=leave_req.start_date.year, category=leave_req.category
    )

    if new_status == LeaveStatus.APPROVED:
        balance.pending = max(0.0, balance.pending - leave_req.duration_days)
        balance.consumed += leave_req.duration_days
        balance.save()
        leave_req.final_decision_by_id = actor_id
    elif new_status == LeaveStatus.REJECTED:
        balance.pending = max(0.0, balance.pending - leave_req.duration_days)
        balance.save()
        leave_req.final_decision_by_id = actor_id

    leave_req.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=actor_id,
        action=f"unit_head_{action}",
        previous_status=prev_status,
        new_status=new_status,
        remarks=remarks,
    )
    return leave_req


@transaction.atomic
def decide_sanction(
    leave_id: int,
    actor_id: int,
    action: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveRequest:
    """Final Sanctioning Authority decision for higher-sanction leaves (UC-EL-005)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.current_status not in (LeaveStatus.PENDING_SANCTION, LeaveStatus.PENDING_ESTT):
        raise ValidationError("Request is not awaiting final sanction.")

    new_status = process_sanction_action(action)
    prev_status = leave_req.current_status

    leave_req.current_status = new_status
    leave_req.sanction_remarks = remarks
    leave_req.sanction_acted_at = timezone.now()
    leave_req.final_decision_by_id = actor_id

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id, year=leave_req.start_date.year, category=leave_req.category
    )

    if new_status == LeaveStatus.APPROVED:
        balance.pending = max(0.0, balance.pending - leave_req.duration_days)
        balance.consumed += leave_req.duration_days
        balance.save()
    elif new_status == LeaveStatus.REJECTED:
        balance.pending = max(0.0, balance.pending - leave_req.duration_days)
        balance.save()

    leave_req.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=actor_id,
        action=f"sanction_{action}",
        previous_status=prev_status,
        new_status=new_status,
        remarks=remarks,
    )
    return leave_req


@transaction.atomic
def withdraw_leave(leave_id: int, user_id: int, remarks: str = "") -> LeaveRequest:
    """Immediate withdrawal of a pending request before final approval (BR-EL-022, UC-EL-007)."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.user_id != user_id:
        raise ValidationError("You can only withdraw your own leave requests.")

    if not can_withdraw(leave_req.current_status):
        raise ValidationError("Request cannot be withdrawn because it is not currently pending.")

    prev_status = leave_req.current_status
    leave_req.current_status = LeaveStatus.WITHDRAWN
    leave_req.save(update_fields=["current_status"])

    # Restore pending balance
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id, year=leave_req.start_date.year, category=leave_req.category
    )
    balance.pending = max(0.0, balance.pending - leave_req.duration_days)
    balance.save(update_fields=["pending"])

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=user_id,
        action="withdraw",
        previous_status=prev_status,
        new_status=LeaveStatus.WITHDRAWN,
        remarks=remarks or "Withdrawn by employee",
    )
    return leave_req


@transaction.atomic
def request_cancellation(
    leave_id: int, user_id: int, remarks: str = "", today: date | None = None
) -> LeaveRequest:
    """Pre-start cancellation request for an approved leave (BR-EL-023, UC-EL-008)."""
    today = today or date.today()
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.user_id != user_id:
        raise ValidationError("You can only request cancellation for your own leave.")

    if not can_request_cancellation(leave_req.current_status, leave_req.start_date, today):
        raise ValidationError("Approved leave can only be cancelled before its start date.")

    prev_status = leave_req.current_status
    leave_req.current_status = LeaveStatus.CANCELLATION_PENDING
    leave_req.save(update_fields=["current_status"])

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=user_id,
        action="cancellation_request",
        previous_status=prev_status,
        new_status=LeaveStatus.CANCELLATION_PENDING,
        remarks=remarks or "Cancellation requested by employee",
    )
    return leave_req


@transaction.atomic
def decide_cancellation(
    leave_id: int, actor_id: int, action: str, remarks: str = ""
) -> LeaveRequest:
    """Sanctioning decision for cancellation request."""
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.current_status != LeaveStatus.CANCELLATION_PENDING:
        raise ValidationError("Leave is not awaiting cancellation review.")

    prev_status = leave_req.current_status
    if action == "approve":
        leave_req.current_status = LeaveStatus.CANCELLED
        # Restore consumed balance
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=leave_req.user_id, year=leave_req.start_date.year, category=leave_req.category
        )
        balance.consumed = max(0.0, balance.consumed - leave_req.duration_days)
        balance.save(update_fields=["consumed"])
    elif action == "reject":
        leave_req.current_status = LeaveStatus.APPROVED
    else:
        raise ValidationError(f"Invalid cancellation decision: {action}")

    leave_req.save(update_fields=["current_status"])

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=actor_id,
        action=f"cancellation_{action}",
        previous_status=prev_status,
        new_status=leave_req.current_status,
        remarks=remarks,
    )
    return leave_req


# =========================================================================
# PHASE 2 ENHANCEMENTS: EXTENSION, RESUMPTION, AND SLA ENGINE
# =========================================================================

@transaction.atomic
def apply_leave_extension(
    leave_id: int,
    user_id: int,
    extension_end_date: date,
    reason: str,
    today: date | None = None,
) -> LeaveExtension:
    """Apply for extension of ongoing EL/COL/VL (BR-EL-025, WF-EL-04, UC-EL-009)."""
    today = today or date.today()
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.user_id != user_id:
        raise ValidationError("You can only extend your own leave.")

    if not can_request_extension(leave_req.current_status, leave_req.category, leave_req.start_date, today):
        raise ValidationError("Extension is available only for ongoing EL, COL, or Vacation Leave.")

    if extension_end_date <= leave_req.end_date:
        raise ValidationError("Extension end date must be strictly after the current leave end date.")

    # Incremental start date is end_date + 1 day
    inc_start = leave_req.end_date + timedelta(days=1)
    year = inc_start.year
    closed_holidays = get_closed_holiday_dates(year)

    duration = calculate_leave_days(
        category=leave_req.category,
        start_date=inc_start,
        end_date=extension_end_date,
        closed_holidays=closed_holidays,
    )

    # Check available balance
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id, year=year, category=leave_req.category
    )
    if balance.available_balance < duration:
        raise ValidationError(
            f"Insufficient {leave_req.category} balance for extension. Required: {duration}, Available: {balance.available_balance}"
        )

    ext = LeaveExtension.objects.create(
        leave_request=leave_req,
        start_date=inc_start,
        end_date=extension_end_date,
        duration_days=duration,
        reason=reason,
        status=LeaveExtension.ExtensionStatus.PENDING_UNIT_HEAD,
    )

    # Reserve balance in pending
    balance.pending += duration
    balance.save(update_fields=["pending"])

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=user_id,
        action="extension_request",
        previous_status=leave_req.current_status,
        new_status=leave_req.current_status,
        remarks=f"Extension requested to {extension_end_date} ({duration} additional days)",
    )

    return ext


@transaction.atomic
def review_leave_extension(
    extension_id: int,
    actor_id: int,
    action: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveExtension:
    """Sanctioning decision for leave extension (BR-EL-025)."""
    ext = LeaveExtension.objects.select_for_update().get(id=extension_id)
    leave_req = ext.leave_request
    year = ext.start_date.year

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id, year=year, category=leave_req.category
    )

    if action == "approve":
        ext.status = LeaveExtension.ExtensionStatus.APPROVED
        # Post incremental days to original leave and move pending -> consumed
        balance.pending = max(0.0, balance.pending - ext.duration_days)
        balance.consumed += ext.duration_days
        balance.save()

        leave_req.end_date = ext.end_date
        leave_req.duration_days += ext.duration_days
        leave_req.save(update_fields=["end_date", "duration_days"])
    elif action == "reject":
        ext.status = LeaveExtension.ExtensionStatus.REJECTED
        # Release pending reservation
        balance.pending = max(0.0, balance.pending - ext.duration_days)
        balance.save(update_fields=["pending"])
    else:
        raise ValidationError(f"Invalid extension decision: {action}")

    ext.remarks = remarks
    ext.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=actor_id,
        action=f"extension_{action}",
        previous_status=leave_req.current_status,
        new_status=leave_req.current_status,
        remarks=remarks or f"Extension {action}ed",
    )
    return ext


@transaction.atomic
def submit_duty_resumption(
    leave_id: int,
    user_id: int,
    actual_resumption_date: date,
    today: date | None = None,
) -> LeaveResumption:
    """Employee declares actual return to duty after EL/COL/VL (BR-EL-027, WF-EL-05, UC-EL-010)."""
    today = today or date.today()
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.user_id != user_id:
        raise ValidationError("You can only declare resumption for your own leave.")

    if not can_submit_resumption(leave_req.current_status, leave_req.category, leave_req.start_date, today):
        raise ValidationError("Duty resumption applies only to ongoing or approved EL, COL, or VL.")

    # Determine resumption type
    if actual_resumption_date == leave_req.end_date:
        res_type = LeaveResumption.ResumptionType.NORMAL
    elif actual_resumption_date < leave_req.end_date:
        res_type = LeaveResumption.ResumptionType.EARLY
    else:
        res_type = LeaveResumption.ResumptionType.LATE

    # Recalculate duration from start_date to actual_resumption_date
    year = leave_req.start_date.year
    closed_holidays = get_closed_holiday_dates(year)
    adjusted_duration = calculate_leave_days(
        category=leave_req.category,
        start_date=leave_req.start_date,
        end_date=actual_resumption_date,
        closed_holidays=closed_holidays,
    )

    resumption, _ = LeaveResumption.objects.update_or_create(
        leave_request=leave_req,
        defaults={
            "expected_date": leave_req.end_date,
            "actual_resumption_date": actual_resumption_date,
            "resumption_type": res_type,
            "adjusted_duration_days": adjusted_duration,
            "status": LeaveResumption.ResumptionStatus.SUBMITTED,
        },
    )

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=user_id,
        action="resumption_declared",
        previous_status=leave_req.current_status,
        new_status=leave_req.current_status,
        remarks=f"Duty resumed on {actual_resumption_date} ({res_type})",
    )
    return resumption


@transaction.atomic
def review_duty_resumption(
    resumption_id: int,
    reviewer_id: int,
    remarks: str = "",
) -> LeaveResumption:
    """Sanctioning Authority reviews resumption and adjusts balance (BR-EL-028)."""
    resumption = LeaveResumption.objects.select_for_update().get(id=resumption_id)
    leave_req = resumption.leave_request
    year = leave_req.start_date.year

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=leave_req.user_id, year=year, category=leave_req.category
    )

    duration_diff = resumption.adjusted_duration_days - leave_req.duration_days

    if resumption.resumption_type == LeaveResumption.ResumptionType.EARLY:
        # Early resumption: return was earlier, so consumed days are reduced and restored
        balance.consumed = max(0.0, balance.consumed + duration_diff)  # duration_diff is negative
    elif resumption.resumption_type == LeaveResumption.ResumptionType.LATE:
        # Late resumption: return was later, additional days deducted
        balance.consumed += duration_diff
    # For NORMAL, duration_diff is 0, no adjustment

    balance.save(update_fields=["consumed"])

    leave_req.end_date = resumption.actual_resumption_date
    leave_req.duration_days = resumption.adjusted_duration_days
    leave_req.save(update_fields=["end_date", "duration_days"])

    resumption.status = LeaveResumption.ResumptionStatus.REVIEWED
    resumption.reviewer_id = reviewer_id
    resumption.reviewer_remarks = remarks
    resumption.reviewed_at = timezone.now()
    resumption.save()

    LeaveActionHistory.objects.create(
        leave_request=leave_req,
        actor_id=reviewer_id,
        action="resumption_reviewed",
        previous_status=leave_req.current_status,
        new_status=leave_req.current_status,
        remarks=remarks or f"Resumption approved. Duration updated to {resumption.adjusted_duration_days}d",
    )
    return resumption


@transaction.atomic
def process_sla_thresholds() -> dict:
    """Event-triggered SLA reminder and escalation sweep (BR-EL-032, BR-EL-033, BR-EL-038, UC-EL-021).

    - If still pending past reminder_days: logs reminder notification.
    - If still pending past escalation_days: escalates to higher authority and logs action.
    """
    cfg = get_or_create_policy()
    now = timezone.now()
    reminder_cutoff = now - timedelta(days=cfg.sla_reminder_days)
    escalation_cutoff = now - timedelta(days=cfg.sla_escalation_days)

    pending_statuses = [
        LeaveStatus.PENDING_SUBSTITUTE,
        LeaveStatus.PENDING_UNIT_HEAD,
        LeaveStatus.PENDING_ESTT,
        LeaveStatus.PENDING_SANCTION,
    ]

    reminded_count = 0
    escalated_count = 0

    pending_leaves = LeaveRequest.objects.filter(current_status__in=pending_statuses)

    for leave in pending_leaves:
        # Check escalation first
        if leave.created_at <= escalation_cutoff:
            if leave.current_status == LeaveStatus.PENDING_UNIT_HEAD:
                leave.current_status = LeaveStatus.PENDING_SANCTION
                leave.current_assignee_role = "director"
                leave.save(update_fields=["current_status", "current_assignee_role"])
                LeaveActionHistory.objects.create(
                    leave_request=leave,
                    actor_id=0,  # System
                    action="sla_escalation",
                    previous_status=LeaveStatus.PENDING_UNIT_HEAD,
                    new_status=LeaveStatus.PENDING_SANCTION,
                    remarks=f"Overdue task escalated past {cfg.sla_escalation_days} days threshold.",
                )
                escalated_count += 1
        elif leave.created_at <= reminder_cutoff:
            LeaveActionHistory.objects.create(
                leave_request=leave,
                actor_id=0,  # System
                action="sla_reminder",
                previous_status=leave.current_status,
                new_status=leave.current_status,
                remarks=f"SLA reminder issued to assignee ({leave.current_status}).",
            )
            reminded_count += 1

    return {
        "reminded_count": reminded_count,
        "escalated_count": escalated_count,
        "total_pending_checked": len(pending_leaves),
    }


@transaction.atomic
def record_offline_leave(
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    offline_reference_no: str,
    sanctioning_authority_name: str,
    sanction_date: date,
    recorded_by_id: int,
    remarks: str = "",
) -> OfflineSanctionRecord:
    """Retrospective offline-sanctioned leave recording (BR-EL-029, UC-EL-016)."""
    year = start_date.year
    closed_holidays = get_closed_holiday_dates(year)
    duration = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        closed_holidays=closed_holidays,
    )

    rec = OfflineSanctionRecord.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        offline_reference_no=offline_reference_no,
        sanctioning_authority_name=sanctioning_authority_name,
        sanction_date=sanction_date,
        recorded_by_id=recorded_by_id,
        remarks=remarks,
    )

    # Balance synchronization without approval progression
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, category=category,
        defaults={"credited": 0.0}
    )
    balance.consumed += duration
    balance.save(update_fields=["consumed"])

    return rec


@transaction.atomic
def process_year_end_rollover(user_id: int, year: int) -> dict:
    """Event-triggered year-end leave balance rollover (BR-EL-002..009, UC-EL-020)."""
    next_year = year + 1
    current_balances = {b.category: b for b in LeaveBalance.objects.filter(user_id=user_id, year=year)}
    cfg = get_or_create_policy()

    # 1. Faculty VL conversion to EL
    vl_bal = current_balances.get(LeaveCategory.VACATION_LEAVE)
    converted_el = 0.0
    if vl_bal:
        unused_vl = max(0.0, vl_bal.credited + vl_bal.carried_forward - vl_bal.consumed)
        converted_el = calculate_vl_to_el_conversion(unused_vl, cfg.vl_to_el_ratio)

    # 2. EL carry forward + VL conversion
    el_bal = current_balances.get(LeaveCategory.EARNED_LEAVE)
    el_carried = (
        max(0.0, el_bal.credited + el_bal.carried_forward - el_bal.consumed) if el_bal else 0.0
    )
    total_next_el_carried = el_carried + converted_el

    next_el, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=next_year, category=LeaveCategory.EARNED_LEAVE,
        defaults={"credited": 0.0}
    )
    next_el.carried_forward = total_next_el_carried
    next_el.save(update_fields=["carried_forward"])

    # 3. COL carry forward
    col_bal = current_balances.get(LeaveCategory.COMMUTED_LEAVE)
    col_carried = (
        max(0.0, col_bal.credited + col_bal.carried_forward - col_bal.consumed) if col_bal else 0.0
    )
    next_col, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=next_year, category=LeaveCategory.COMMUTED_LEAVE,
        defaults={"credited": cfg.col_entitlement}
    )
    next_col.carried_forward = col_carried
    next_col.save(update_fields=["carried_forward"])

    return {
        "user_id": user_id,
        "year": year,
        "next_year": next_year,
        "converted_el_from_vl": converted_el,
        "carried_forward_el": total_next_el_carried,
        "carried_forward_col": col_carried,
    }
