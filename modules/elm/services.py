from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveHistory,
    LeaveStatus,
    LeaveType,
)

# Standard Annual Entitlements (BR-EL-001 through BR-EL-009)
# Staff: CL=8, RH=2, SCL=15, EL=30, COL=20 (No VL)
# Faculty: CL=8, RH=2, SCL=15, VL=60, COL=20 (EL is credited via VL conversion or special credit)
STAFF_ENTITLEMENTS = {
    LeaveType.CL: Decimal("8.0"),
    LeaveType.RH: Decimal("2.0"),
    LeaveType.SCL: Decimal("15.0"),
    LeaveType.EL: Decimal("30.0"),
    LeaveType.COL: Decimal("20.0"),
}

FACULTY_ENTITLEMENTS = {
    LeaveType.CL: Decimal("8.0"),
    LeaveType.RH: Decimal("2.0"),
    LeaveType.SCL: Decimal("15.0"),
    LeaveType.VL: Decimal("60.0"),
    LeaveType.COL: Decimal("20.0"),
    LeaveType.EL: Decimal("0.0"),  # Faculty EL starts at 0 or unavailed VL conversion
}

MAX_EL_ACCUMULATION = Decimal("300.0")  # Ceiling for EL carry-forward


def log_history(
    application: LeaveApplication,
    actor_id: str,
    from_status: str,
    to_status: str,
    action: str,
    remarks: str = "",
) -> LeaveHistory:
    return LeaveHistory.objects.create(
        application=application,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        action=action,
        remarks=remarks,
    )


def init_employee_balances(employee_id: str, is_faculty: bool = False, year: Optional[int] = None) -> list[LeaveBalance]:
    if year is None:
        year = timezone.now().year

    entitlements = FACULTY_ENTITLEMENTS if is_faculty else STAFF_ENTITLEMENTS
    balances = list(LeaveBalance.objects.filter(employee_id=employee_id, year=year))
    existing_types = {b.leave_type for b in balances}

    for ltype, default_days in entitlements.items():
        if ltype not in existing_types:
            b = LeaveBalance.objects.create(
                employee_id=employee_id,
                is_faculty=is_faculty,
                year=year,
                leave_type=ltype,
                total_allocated=default_days,
                carried_forward=Decimal("0.0"),
                used_days=Decimal("0.0"),
                lapsed_days=Decimal("0.0"),
                converted_days=Decimal("0.0"),
            )
            balances.append(b)

    return sorted(balances, key=lambda x: x.leave_type)


@transaction.atomic
def submit_leave_application(applicant_id: str, data: dict, is_faculty: bool = False, is_director: bool = False) -> LeaveApplication:
    """Submit a new leave application enforcing BR-EL-001 through BR-EL-015, BR-EL-020."""
    start_date = data["start_date"]
    end_date = data["end_date"]
    leave_type = data["leave_type"]
    is_half_day = data.get("is_half_day", False)
    substitute_id = data.get("substitute_id", "").strip()

    if end_date < start_date:
        raise BadRequestError("End date cannot be earlier than start date.")

    # BR-EL-001: Leave category eligibility
    if not is_faculty and leave_type == LeaveType.VL:
        raise BadRequestError("Vacation Leave (VL) is only available to Faculty.")

    # BR-EL-010: Half-day CL rule
    if is_half_day:
        if leave_type != LeaveType.CL:
            raise BadRequestError("Half-day leave option is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise BadRequestError("Half-day leave must be on a single day.")
        total_days = Decimal("0.5")
    else:
        total_days = Decimal((end_date - start_date).days + 1)

    # BR-EL-012: Non-overlap check
    overlapping = LeaveApplication.objects.filter(
        applicant_id=applicant_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exclude(status__in=[LeaveStatus.REJECTED, LeaveStatus.CANCELLED, LeaveStatus.WITHDRAWN]).exists()

    if overlapping:
        raise ConflictError("Leave application dates overlap with an active existing leave request.")

    # BR-EL-013: Station Leave coupling
    requires_station_leave = data.get("requires_station_leave", False)
    station_address = data.get("station_leave_address", "").strip()
    if requires_station_leave and not station_address:
        raise BadRequestError("Outstation address must be specified when station leave is required.")

    # Check leave balance
    year = start_date.year
    init_employee_balances(applicant_id, is_faculty=is_faculty, year=year)
    balance = LeaveBalance.objects.select_for_update().get(
        employee_id=applicant_id, year=year, leave_type=leave_type
    )

    if balance.remaining_days < total_days:
        raise BadRequestError(
            f"Insufficient {leave_type} balance. Requested: {total_days}, Available: {balance.remaining_days}."
        )

    # Determine initial workflow state (WF-EL-01 Steps 2, 3, 4)
    # BR-EL-014, BR-EL-015: Substitute gating
    if substitute_id:
        if substitute_id == applicant_id:
            raise BadRequestError("Applicant cannot nominate themselves as substitute.")
        initial_status = LeaveStatus.AWAITING_SUBSTITUTE
        substitute_status = "PENDING"
    elif is_director:
        # BR-EL-020: Director self-sanction
        initial_status = LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION
        substitute_status = "NONE"
    else:
        # Normal path
        initial_status = LeaveStatus.AWAITING_UNIT_HEAD
        substitute_status = "NONE"

    app = LeaveApplication.objects.create(
        applicant_id=applicant_id,
        is_faculty=is_faculty,
        is_director=is_director,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        is_half_day=is_half_day,
        reason=data.get("reason", "").strip(),
        requires_station_leave=requires_station_leave,
        station_leave_address=station_address,
        station_departure_datetime=data.get("station_departure_datetime"),
        station_arrival_datetime=data.get("station_arrival_datetime"),
        substitute_id=substitute_id,
        substitute_status=substitute_status,
        status=initial_status,
        last_actionable_task_at=timezone.now(),
    )

    log_history(app, applicant_id, LeaveStatus.DRAFT, initial_status, "SUBMIT_APPLICATION", "Leave application submitted.")
    return app


@transaction.atomic
def respond_substitute(application_id: int, substitute_id: str, accept: bool, remarks: str = "") -> LeaveApplication:
    """WF-EL-01 Steps 5-7: Substitute accept/decline gating (BR-EL-015)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, substitute_id=substitute_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found for substitute.")

    if app.status != LeaveStatus.AWAITING_SUBSTITUTE:
        raise BadRequestError(f"Application is in status '{app.status}', not awaiting substitute response.")

    from_status = app.status
    app.substitute_remarks = remarks
    app.substitute_responded_at = timezone.now()

    if accept:
        app.substitute_status = "ACCEPTED"
        if app.is_director:
            app.status = LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION
        else:
            app.status = LeaveStatus.AWAITING_UNIT_HEAD
        action = "SUBSTITUTE_ACCEPT"
    else:
        app.substitute_status = "DECLINED"
        app.status = LeaveStatus.SUBSTITUTE_DECLINED
        action = "SUBSTITUTE_DECLINE"

    app.last_actionable_task_at = timezone.now()
    app.sla_reminder_sent = False
    app.save()

    log_history(app, substitute_id, from_status, app.status, action, remarks)
    return app


@transaction.atomic
def replace_substitute_or_proceed(application_id: int, applicant_id: str, new_substitute_id: str = "") -> LeaveApplication:
    """WF-EL-01 Step 7: When substitute declines, applicant nominates another substitute."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, applicant_id=applicant_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.SUBSTITUTE_DECLINED:
        raise BadRequestError("Application is not in SUBSTITUTE_DECLINED status.")

    from_status = app.status
    if new_substitute_id:
        if new_substitute_id == applicant_id:
            raise BadRequestError("Applicant cannot nominate themselves as substitute.")
        app.substitute_id = new_substitute_id
        app.substitute_status = "PENDING"
        app.status = LeaveStatus.AWAITING_SUBSTITUTE
        action = "REPLACE_SUBSTITUTE"
        remarks = f"Nominated new substitute {new_substitute_id}"
    else:
        app.substitute_id = ""
        app.substitute_status = "NONE"
        app.status = LeaveStatus.AWAITING_UNIT_HEAD
        action = "PROCEED_WITHOUT_SUBSTITUTE"
        remarks = "Proceeded without substitute."

    app.last_actionable_task_at = timezone.now()
    app.save()
    log_history(app, applicant_id, from_status, app.status, action, remarks)
    return app


@transaction.atomic
def unit_head_review(application_id: int, unit_head_id: str, action: str, remarks: str = "") -> LeaveApplication:
    """WF-EL-01 Steps 8-11: Unit Head review (BR-EL-016, BR-EL-017).
    - For CL and RH: Unit Head decision is FINAL (Approved or Rejected).
    - For SCL, EL, COL, VL: Unit Head only RECOMMENDS or REJECTS. If recommended, routes to Sanctioning Authority.
    """
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.AWAITING_UNIT_HEAD:
        raise BadRequestError(f"Application is in status '{app.status}', not awaiting Unit Head review.")

    from_status = app.status
    app.unit_head_id = unit_head_id
    app.unit_head_remarks = remarks
    app.unit_head_reviewed_at = timezone.now()
    now_year = app.start_date.year

    if action == "approve":
        # BR-EL-016: CL and RH final sanction by Unit Head
        if app.leave_type in [LeaveType.CL, LeaveType.RH]:
            balance = LeaveBalance.objects.select_for_update().get(
                employee_id=app.applicant_id, year=now_year, leave_type=app.leave_type
            )
            if balance.remaining_days < app.total_days:
                raise BadRequestError(f"Insufficient {app.leave_type} balance to finalize approval.")
            balance.used_days += app.total_days
            balance.save(update_fields=["used_days"])

            app.status = LeaveStatus.APPROVED
            app.unit_head_recommendation = "APPROVED_FINAL"
            log_action = "UNIT_HEAD_FINAL_APPROVE"
        else:
            raise BadRequestError(
                f"{app.leave_type} requires higher sanctioning authority. Unit Head may only recommend or reject."
            )

    elif action == "recommend":
        # BR-EL-017: SCL, EL, COL, VL recommended to higher sanction
        if app.leave_type in [LeaveType.CL, LeaveType.RH]:
            raise BadRequestError("CL and RH are finalized directly by Unit Head, not recommended to higher sanction.")
        app.status = LeaveStatus.AWAITING_SANCTION
        app.unit_head_recommendation = "RECOMMENDED"
        log_action = "UNIT_HEAD_RECOMMEND"

    elif action == "reject":
        app.status = LeaveStatus.REJECTED
        app.unit_head_recommendation = "REJECTED"
        log_action = "UNIT_HEAD_REJECT"

    else:
        raise BadRequestError("Invalid action. Must be 'approve', 'recommend', or 'reject'.")

    app.last_actionable_task_at = timezone.now()
    app.sla_reminder_sent = False
    app.save()

    log_history(app, unit_head_id, from_status, app.status, log_action, remarks)
    return app


@transaction.atomic
def sanctioning_authority_review(application_id: int, sanctioner_id: str, action: str, remarks: str = "") -> LeaveApplication:
    """WF-EL-01 Steps 13-14: Higher sanction decision for SCL/EL/COL/VL (BR-EL-018, BR-EL-019)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.AWAITING_SANCTION:
        raise BadRequestError(f"Application is in status '{app.status}', not awaiting final sanction.")

    from_status = app.status
    app.sanctioner_id = sanctioner_id
    app.sanction_remarks = remarks
    app.sanctioned_at = timezone.now()
    now_year = app.start_date.year

    if action == "approve":
        balance = LeaveBalance.objects.select_for_update().get(
            employee_id=app.applicant_id, year=now_year, leave_type=app.leave_type
        )
        if balance.remaining_days < app.total_days:
            raise BadRequestError(f"Insufficient {app.leave_type} balance to finalize approval.")
        balance.used_days += app.total_days
        balance.save(update_fields=["used_days"])

        app.status = LeaveStatus.APPROVED
        app.sanction_decision = "APPROVED"
        log_action = "FINAL_SANCTION_APPROVE"

    elif action == "reject":
        app.status = LeaveStatus.REJECTED
        app.sanction_decision = "REJECTED"
        log_action = "FINAL_SANCTION_REJECT"

    else:
        raise BadRequestError("Invalid action. Must be 'approve' or 'reject'.")

    app.save()
    log_history(app, sanctioner_id, from_status, app.status, log_action, remarks)
    return app


@transaction.atomic
def director_self_sanction(application_id: int, director_id: str, action: str, remarks: str = "") -> LeaveApplication:
    """WF-EL-01 Steps 15-16: Director self-sanction (BR-EL-020)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, applicant_id=director_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION:
        raise BadRequestError("Application is not awaiting Director self-sanction.")

    from_status = app.status
    now_year = app.start_date.year

    if action == "approve":
        balance = LeaveBalance.objects.select_for_update().get(
            employee_id=app.applicant_id, year=now_year, leave_type=app.leave_type
        )
        if balance.remaining_days < app.total_days:
            raise BadRequestError("Insufficient balance.")
        balance.used_days += app.total_days
        balance.save(update_fields=["used_days"])

        app.status = LeaveStatus.APPROVED
        app.sanction_decision = "APPROVED"
        app.sanctioner_id = director_id
        app.sanction_remarks = remarks
        app.sanctioned_at = timezone.now()
        log_action = "DIRECTOR_SELF_APPROVE"
    else:
        app.status = LeaveStatus.REJECTED
        app.sanction_decision = "REJECTED"
        log_action = "DIRECTOR_SELF_REJECT"

    app.save()
    log_history(app, director_id, from_status, app.status, log_action, remarks)
    return app


@transaction.atomic
def withdraw_pending_application(application_id: int, applicant_id: str, reason: str = "") -> LeaveApplication:
    """WF-EL-02: Immediate withdrawal of pending request before approval (BR-EL-022)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, applicant_id=applicant_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    allowed_pending = [
        LeaveStatus.AWAITING_SUBSTITUTE,
        LeaveStatus.SUBSTITUTE_DECLINED,
        LeaveStatus.AWAITING_UNIT_HEAD,
        LeaveStatus.AWAITING_SANCTION,
        LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION,
    ]
    if app.status not in allowed_pending:
        raise BadRequestError(f"Cannot withdraw leave in status '{app.status}'. Only pending requests can be withdrawn.")

    from_status = app.status
    app.status = LeaveStatus.WITHDRAWN
    app.save(update_fields=["status", "updated_at"])

    log_history(app, applicant_id, from_status, LeaveStatus.WITHDRAWN, "WITHDRAW_PENDING", reason)
    return app


@transaction.atomic
def cancel_approved_application(application_id: int, applicant_id: str, reason: str = "") -> LeaveApplication:
    """WF-EL-03: Cancellation of approved leave before start, restoring balance (BR-EL-023)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, applicant_id=applicant_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.APPROVED:
        raise BadRequestError(f"Cannot cancel leave in status '{app.status}'. Only approved leave can be cancelled.")

    today = timezone.now().date()
    if app.start_date < today:
        raise BadRequestError("Cannot cancel leave that has already started. Submit resumption or extension instead.")

    from_status = app.status
    balance = LeaveBalance.objects.select_for_update().get(
        employee_id=app.applicant_id, year=app.start_date.year, leave_type=app.leave_type
    )
    balance.used_days = max(Decimal("0.0"), balance.used_days - app.total_days)
    balance.save(update_fields=["used_days"])

    app.status = LeaveStatus.CANCELLED
    app.save(update_fields=["status", "updated_at"])

    log_history(app, applicant_id, from_status, LeaveStatus.CANCELLED, "CANCEL_APPROVED", reason)
    return app


@transaction.atomic
def extend_leave_application(parent_id: int, applicant_id: str, new_end_date: date, reason: str = "") -> LeaveApplication:
    """WF-EL-04: Incremental extension for ongoing EL, COL or VL (BR-EL-025)."""
    try:
        parent = LeaveApplication.objects.select_for_update().get(pk=parent_id, applicant_id=applicant_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Parent leave application not found.")

    if parent.status != LeaveStatus.APPROVED:
        raise BadRequestError("Can only extend an approved leave application.")

    # BR-EL-025: Ongoing extension is permitted only for EL, COL, or VL
    if parent.leave_type not in [LeaveType.EL, LeaveType.COL, LeaveType.VL]:
        raise BadRequestError(f"{parent.leave_type} cannot be extended as ongoing leave. Apply fresh leave instead.")

    if new_end_date <= parent.end_date:
        raise BadRequestError(f"Extension end date ({new_end_date}) must be after current end date ({parent.end_date}).")

    incremental_days = Decimal((new_end_date - parent.end_date).days)
    year = new_end_date.year

    balance = LeaveBalance.objects.select_for_update().get(
        employee_id=applicant_id, year=year, leave_type=parent.leave_type
    )
    if balance.remaining_days < incremental_days:
        raise BadRequestError(f"Insufficient balance for extension of {incremental_days} days.")

    ext_app = LeaveApplication.objects.create(
        applicant_id=applicant_id,
        is_faculty=parent.is_faculty,
        leave_type=parent.leave_type,
        start_date=parent.end_date + timedelta(days=1),
        end_date=new_end_date,
        total_days=incremental_days,
        is_half_day=False,
        reason=f"Extension of Leave #{parent.id}: {reason}".strip(),
        is_extension=True,
        parent_leave=parent,
        status=LeaveStatus.AWAITING_UNIT_HEAD,
        last_actionable_task_at=timezone.now(),
    )

    log_history(ext_app, applicant_id, LeaveStatus.DRAFT, LeaveStatus.AWAITING_UNIT_HEAD, "SUBMIT_EXTENSION", reason)
    return ext_app


@transaction.atomic
def submit_and_verify_resumption(
    application_id: int,
    applicant_id: str,
    actual_resumption_date: date,
    verifier_id: str,
    remarks: str = "",
) -> LeaveApplication:
    """WF-EL-05: Duty resumption and early return balance restoration (BR-EL-027, BR-EL-028)."""
    try:
        app = LeaveApplication.objects.select_for_update().get(pk=application_id, applicant_id=applicant_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.")

    if app.status != LeaveStatus.APPROVED:
        raise BadRequestError("Resumption can only be submitted for approved leaves.")

    if actual_resumption_date < app.start_date:
        raise BadRequestError("Actual resumption date cannot be earlier than leave start date.")

    from_status = app.status
    app.actual_resumption_date = actual_resumption_date
    app.resumption_verified_by = verifier_id
    app.resumption_verified_at = timezone.now()

    # Calculate actual days availed
    if actual_resumption_date <= app.end_date:
        # Early return (BR-EL-028)
        actual_availed = Decimal((actual_resumption_date - app.start_date).days)
        unused_days = max(Decimal("0.0"), app.total_days - actual_availed)
        app.actual_days_availed = actual_availed

        # Restore unused days to balance
        if unused_days > Decimal("0.0"):
            balance = LeaveBalance.objects.select_for_update().get(
                employee_id=app.applicant_id, year=app.start_date.year, leave_type=app.leave_type
            )
            balance.used_days = max(Decimal("0.0"), balance.used_days - unused_days)
            balance.save(update_fields=["used_days"])
            remarks = f"{remarks} (Early return: restored {unused_days} unused days)".strip()
    else:
        # Normal or late return
        app.actual_days_availed = app.total_days

    app.status = LeaveStatus.CLOSED
    app.save()

    log_history(app, verifier_id, from_status, LeaveStatus.CLOSED, "VERIFY_RESUMPTION", remarks)
    return app


@transaction.atomic
def record_offline_leave(admin_id: str, data: dict) -> LeaveApplication:
    """WF-EL-06: Record offline/paper-sanctioned leave into ELM (BR-EL-029)."""
    applicant_id = data["employee_id"]
    leave_type = data["leave_type"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    is_faculty = data.get("is_faculty", False)
    offline_ref = data.get("offline_sanction_ref", "").strip()

    if not offline_ref:
        raise BadRequestError("Offline sanction reference evidence/number is required.")

    total_days = Decimal((end_date - start_date).days + 1)
    year = start_date.year

    init_employee_balances(applicant_id, is_faculty=is_faculty, year=year)
    balance = LeaveBalance.objects.select_for_update().get(
        employee_id=applicant_id, year=year, leave_type=leave_type
    )

    balance.used_days += total_days
    balance.save(update_fields=["used_days"])

    app = LeaveApplication.objects.create(
        applicant_id=applicant_id,
        is_faculty=is_faculty,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=data.get("reason", "Offline sanctioned leave"),
        is_offline_record=True,
        offline_sanction_ref=offline_ref,
        offline_sanction_date=data.get("offline_sanction_date", timezone.now().date()),
        status=LeaveStatus.APPROVED,
        sanction_decision="APPROVED",
        sanctioner_id=admin_id,
        sanction_remarks=f"Recorded from offline paper sanction ref: {offline_ref}",
        sanctioned_at=timezone.now(),
    )

    log_history(app, admin_id, LeaveStatus.DRAFT, LeaveStatus.APPROVED, "RECORD_OFFLINE", f"Offline Ref: {offline_ref}")
    return app


@transaction.atomic
def execute_year_end_processing(year: int) -> dict:
    """WF-EL-07 / SF-EL-001: Scheduled Year-End Leave Processing.
    - Lapses unused CL, RH, and SCL (BR-EL-002 to BR-EL-004).
    - Faculty Vacation Leave (VL) unavailed conversion to EL at 1:2 ratio (BR-EL-007).
    - Carries forward EL and COL up to policy cap into the next year (BR-EL-005, BR-EL-008, BR-EL-009).
    """
    next_year = year + 1
    current_balances = LeaveBalance.objects.select_for_update().filter(year=year)

    employees = {b.employee_id: b.is_faculty for b in current_balances}
    results = {"lapsed": 0, "converted_vl": 0, "carried_forward": 0}

    for emp_id, is_fac in employees.items():
        init_employee_balances(emp_id, is_faculty=is_fac, year=next_year)
        emp_balances = {b.leave_type: b for b in LeaveBalance.objects.select_for_update().filter(employee_id=emp_id, year=year)}
        next_balances = {b.leave_type: b for b in LeaveBalance.objects.select_for_update().filter(employee_id=emp_id, year=next_year)}

        # 1. Lapse CL, RH, SCL
        for ltype in [LeaveType.CL, LeaveType.RH, LeaveType.SCL]:
            if ltype in emp_balances:
                b = emp_balances[ltype]
                rem = b.remaining_days
                if rem > Decimal("0.0"):
                    b.lapsed_days = rem
                    b.save(update_fields=["lapsed_days"])
                    results["lapsed"] += 1

        # 2. Faculty VL to EL conversion (BR-EL-007)
        if is_fac and LeaveType.VL in emp_balances:
            vl_bal = emp_balances[LeaveType.VL]
            unused_vl = vl_bal.remaining_days
            if unused_vl > Decimal("0.0"):
                # Ratio: 1 EL for every 2 unutilized VL days (rounded down to half day)
                converted_el = Decimal(int(unused_vl // 2))
                vl_bal.converted_days = unused_vl
                vl_bal.save(update_fields=["converted_days"])

                if LeaveType.EL in next_balances:
                    el_next = next_balances[LeaveType.EL]
                    el_next.carried_forward = min(MAX_EL_ACCUMULATION, el_next.carried_forward + converted_el)
                    el_next.save(update_fields=["carried_forward"])
                    results["converted_vl"] += 1

        # 3. Staff EL carry forward (BR-EL-005)
        if not is_fac and LeaveType.EL in emp_balances:
            el_bal = emp_balances[LeaveType.EL]
            unused_el = el_bal.remaining_days
            if unused_el > Decimal("0.0") and LeaveType.EL in next_balances:
                el_next = next_balances[LeaveType.EL]
                el_next.carried_forward = min(MAX_EL_ACCUMULATION, el_next.carried_forward + unused_el)
                el_next.save(update_fields=["carried_forward"])
                results["carried_forward"] += 1

        # 4. COL carry forward (BR-EL-009)
        if LeaveType.COL in emp_balances:
            col_bal = emp_balances[LeaveType.COL]
            unused_col = col_bal.remaining_days
            if unused_col > Decimal("0.0") and LeaveType.COL in next_balances:
                col_next = next_balances[LeaveType.COL]
                col_next.carried_forward += unused_col
                col_next.save(update_fields=["carried_forward"])

    return results


@transaction.atomic
def process_sla_checks(reminder_threshold_days: int = 3, escalation_threshold_days: int = 5) -> dict:
    """WF-EL-08 / SF-EL-002: Scheduled SLA Reminder and Escalation processing (BR-EL-032, BR-EL-033)."""
    now = timezone.now()
    pending_statuses = [
        LeaveStatus.AWAITING_SUBSTITUTE,
        LeaveStatus.AWAITING_UNIT_HEAD,
        LeaveStatus.AWAITING_SANCTION,
    ]

    actionable_apps = LeaveApplication.objects.select_for_update().filter(status__in=pending_statuses)
    reminded = 0
    escalated = 0

    for app in actionable_apps:
        pending_duration = now - app.last_actionable_task_at

        # Escalation check
        if pending_duration >= timedelta(days=escalation_threshold_days):
            if not app.sla_escalation_sent:
                app.sla_escalation_sent = True
                app.save(update_fields=["sla_escalation_sent"])
                log_history(
                    app,
                    "SYSTEM_SLA_SCHEDULER",
                    app.status,
                    app.status,
                    "SLA_ESCALATION_TRIGGERED",
                    f"Pending for {pending_duration.days} days exceeding {escalation_threshold_days}-day threshold.",
                )
                escalated += 1

        # Reminder check
        elif pending_duration >= timedelta(days=reminder_threshold_days):
            if not app.sla_reminder_sent:
                app.sla_reminder_sent = True
                app.save(update_fields=["sla_reminder_sent"])
                log_history(
                    app,
                    "SYSTEM_SLA_SCHEDULER",
                    app.status,
                    app.status,
                    "SLA_REMINDER_LOGGED",
                    f"Pending for {pending_duration.days} days exceeding {reminder_threshold_days}-day threshold.",
                )
                reminded += 1

    return {"reminded": reminded, "escalated": escalated}
