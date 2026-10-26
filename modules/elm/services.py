"""Business services for Employee Leave Management (ELM).

Implements calculations, overlap prevention, concurrency-safe balance updates,
workflow state transitions, and idempotent rollover operations adhering to
BR-EL-001..023, CFR-EL-002..025, and CW-EL-01..04.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .domain import state_machine as sm
from .models import (
    Holiday,
    HolidayCalendar,
    LeaveActionHistory,
    LeaveBalance,
    LeaveRequest,
    YearEndProcessingLog,
)


# --- Category Quota & Configuration (BR-EL-001..009) ---
UNIT_HEAD_FINAL_CATEGORIES = frozenset({"cl", "rh"})
HIGHER_SANCTION_CATEGORIES = frozenset({"scl", "el", "col", "vl"})
CONTINUOUS_COUNTING_CATEGORIES = frozenset({"el", "col", "vl"})
WORKING_DAY_CATEGORIES = frozenset({"cl", "scl", "rh"})


def get_default_annual_quota(category: str, is_faculty: bool = False) -> Decimal:
    """Return the specified annual base quota per category (BR-EL-002..009)."""
    quotas: dict[str, Decimal] = {
        "cl": Decimal("8.0"),
        "rh": Decimal("2.0"),
        "scl": Decimal("15.0"),  # Annual statutory ceiling (BR-EL-004)
        "col": Decimal("20.0"),
        "el": Decimal("0.0") if is_faculty else Decimal("30.0"),
        "vl": Decimal("60.0") if is_faculty else Decimal("0.0"),
    }
    return quotas.get(category, Decimal("0.0"))


# --- Concurrency-Safe Balance Retrieval & Creation ---
def get_or_create_locked_balance(
    user_id: int, category: str, year: int, is_faculty: bool = False
) -> LeaveBalance:
    """Fetch and row-lock LeaveBalance in PostgreSQL, isolating concurrent creation in an inner savepoint."""
    default_credited = get_default_annual_quota(category, is_faculty)

    for _ in range(3):
        try:
            return LeaveBalance.objects.select_for_update().get(
                user_id=user_id, category=category, year=year
            )
        except LeaveBalance.DoesNotExist:
            try:
                with transaction.atomic():
                    LeaveBalance.objects.create(
                        user_id=user_id,
                        category=category,
                        year=year,
                        credited=default_credited,
                        carried_forward=Decimal("0.0"),
                        converted_in=Decimal("0.0"),
                        availed=Decimal("0.0"),
                        pending=Decimal("0.0"),
                        converted_out=Decimal("0.0"),
                    )
            except IntegrityError:
                # Concurrent worker created the row first; loop and lock
                continue

            return LeaveBalance.objects.select_for_update().get(
                user_id=user_id, category=category, year=year
            )

    return LeaveBalance.objects.select_for_update().get(
        user_id=user_id, category=category, year=year
    )


# --- Day Counting Logic (BR-EL-010, BR-EL-011, BR-EL-031) ---
def calculate_leave_days(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half_day: bool = False,
    half_day_type: str | None = None,
    closed_holidays: set[datetime.date] | None = None,
) -> Decimal:
    """Calculate effective leave days according to category rules and published calendar."""
    if start_date > end_date:
        raise ValidationError("start_date cannot be after end_date.")

    # Half-day rule (BR-EL-010)
    if half_day:
        if category != "cl":
            raise ValidationError("Half-day requests are only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise ValidationError("Half-day CL must be a single-day request (start_date must equal end_date).")
        if half_day_type not in ("first_half", "second_half"):
            raise ValidationError("Half-day CL requires specifying 'first_half' or 'second_half'.")
        return Decimal("0.5")

    # Continuous counting (BR-EL-011): EL, COL, VL
    if category in CONTINUOUS_COUNTING_CATEGORIES:
        return Decimal((end_date - start_date).days + 1)

    # Restricted Holiday (RH) rule (BR-EL-003, AFR-EL-005.2)
    if category == "rh":
        if start_date != end_date:
            raise ValidationError("Restricted Holiday (RH) must be requested as a single day.")
        # Check published calendar (fail-closed if missing or not an RH)
        try:
            is_valid_rh = Holiday.objects.filter(
                calendar__year=start_date.year,
                calendar__is_published=True,
                date=start_date,
                is_rh=True,
            ).exists()
        except Exception:
            is_valid_rh = False
        if not is_valid_rh:
            raise ValidationError(
                f"Date {start_date} is not listed as an active Restricted Holiday in the published calendar."
            )
        return Decimal("1.0")

    # Working-day counting (BR-EL-011): CL, SCL
    if closed_holidays is None:
        try:
            closed_holidays = set(
                Holiday.objects.filter(
                    calendar__year=start_date.year,
                    calendar__is_published=True,
                    is_closed=True,
                ).values_list("date", flat=True)
            )
        except Exception:
            closed_holidays = set()

    current = start_date
    working_days = 0
    one_day = datetime.timedelta(days=1)

    while current <= end_date:
        # Exclude Saturdays (5) and Sundays (6)
        if current.weekday() not in (5, 6) and current not in closed_holidays:
            working_days += 1
        current += one_day

    return Decimal(str(working_days))


# --- Overlap Prevention (BR-EL-012) ---
def validate_no_overlap(
    user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half_day: bool = False,
    half_day_type: str | None = None,
    exclude_request_id: int | None = None,
) -> None:
    """Ensure no impermissible overlap with active in-flight or approved requests (BR-EL-012)."""
    active_requests = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=sm.ACTIVE_OVERLAP_BLOCKING_STATES,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_request_id:
        active_requests = active_requests.exclude(pk=exclude_request_id)

    for req in active_requests:
        # Same-date complementary half-day CL exception (BR-EL-012)
        if (
            category == "cl"
            and req.category == "cl"
            and half_day
            and req.half_day
            and start_date == end_date == req.start_date == req.end_date
            and half_day_type in ("first_half", "second_half")
            and req.half_day_type in ("first_half", "second_half")
            and half_day_type != req.half_day_type
        ):
            continue  # Permitted non-overlapping halves on same date

        raise ValidationError(
            f"Requested period ({start_date} to {end_date}) overlaps with existing {req.get_status_display()} "
            f"request #{req.id} ({req.start_date} to {req.end_date})."
        )


# --- Leave Application Submission (EL-UC-001) ---
@transaction.atomic
def submit_leave_request(
    applicant_user_id: int,
    data: dict[str, Any],
    is_faculty: bool = False,
    is_director: bool = False,
) -> LeaveRequest:
    """Validate and submit a new leave application with atomic balance reservation."""
    category = data["category"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    half_day = data.get("half_day", False)
    half_day_type = data.get("half_day_type")
    substitute_id = data.get("substitute_id")
    year = start_date.year

    # 1. Day calculation & Category Validation
    leave_days = calculate_leave_days(category, start_date, end_date, half_day, half_day_type)
    if leave_days <= Decimal("0.0"):
        raise ValidationError("Calculated leave duration is 0 days. Select working dates.")

    # 2. Overlap validation (BR-EL-012)
    validate_no_overlap(applicant_user_id, category, start_date, end_date, half_day, half_day_type)

    # 3. Substitute validation (BR-EL-014)
    if substitute_id:
        if substitute_id == applicant_user_id:
            raise ValidationError("Applicant cannot nominate themselves as their own substitute.")
        # Check substitute has no overlapping active leave
        validate_no_overlap(substitute_id, category, start_date, end_date)

    # 4. Atomic balance reservation & Ceiling check (BR-EL-004)
    balance = get_or_create_locked_balance(applicant_user_id, category, year, is_faculty)

    # SCL statutory ceiling check (BR-EL-004: max 15 days in calendar year)
    if category == "scl":
        if balance.availed + balance.pending + leave_days > Decimal("15.0"):
            raise ValidationError(
                f"SCL annual ceiling of 15.0 days exceeded. (Availed: {balance.availed}, Pending: {balance.pending}, Requested: {leave_days})"
            )

    if balance.available < leave_days:
        raise ValidationError(
            f"Insufficient leave balance for {category.upper()}. Available: {balance.available}, Requested: {leave_days}"
        )

    # Reserve balance in pending bucket
    balance.pending += leave_days
    balance.save(update_fields=["pending", "updated_at"])

    # 5. Determine initial workflow status
    if substitute_id:
        initial_status = sm.PENDING_SUBSTITUTE
        substitute_status = "pending"
    elif is_director:
        initial_status = sm.AWAITING_DIRECTOR_SANCTION
        substitute_status = "none"
    else:
        initial_status = sm.PENDING_UNIT_HEAD
        substitute_status = "none"

    req = LeaveRequest.objects.create(
        user_id=applicant_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_type=half_day_type,
        leave_days=leave_days,
        reason=data.get("reason", ""),
        is_station_leave=data.get("is_station_leave", False),
        station_address=data.get("station_address", ""),
        station_start_date=data.get("station_start_date"),
        station_end_date=data.get("station_end_date"),
        substitute_id=substitute_id,
        substitute_status=substitute_status,
        status=initial_status,
    )

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=applicant_user_id,
        action="submit",
        from_status=sm.DRAFT,
        to_status=initial_status,
        remarks="Leave request submitted.",
    )

    return req


# --- Substitute Workflow (EL-UC-002, EL-UC-019) ---
@transaction.atomic
def respond_substitute(
    leave_request_id: int, substitute_user_id: int, accept: bool, remarks: str = ""
) -> LeaveRequest:
    """Process substitute response to coverage request."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.substitute_id != substitute_user_id:
        raise PermissionDenied("Only the nominated substitute may respond to this responsibility request.")

    if req.status != sm.PENDING_SUBSTITUTE:
        raise sm.InvalidTransition(req.status, "any", "Request is not awaiting substitute response.")

    from_status = req.status
    if accept:
        to_status = sm.PENDING_UNIT_HEAD
        req.substitute_status = "accepted"
    else:
        to_status = sm.SUBSTITUTE_DECLINED
        req.substitute_status = "declined"

    req.substitute_remarks = remarks
    req.status = to_status
    req.save(update_fields=["status", "substitute_status", "substitute_remarks", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=substitute_user_id,
        action="substitute_accept" if accept else "substitute_decline",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


@transaction.atomic
def nominate_replacement_substitute(
    leave_request_id: int, applicant_user_id: int, new_substitute_id: int, remarks: str = ""
) -> LeaveRequest:
    """Applicant nominates a replacement substitute after a decline (EL-UC-019)."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id != applicant_user_id:
        raise PermissionDenied("Only the applicant may nominate a replacement substitute.")

    if req.status != sm.SUBSTITUTE_DECLINED:
        raise sm.InvalidTransition(req.status, sm.PENDING_SUBSTITUTE, "Replacement only permitted after decline.")

    if new_substitute_id == applicant_user_id:
        raise ValidationError("Applicant cannot nominate themselves as their own substitute.")

    validate_no_overlap(new_substitute_id, req.category, req.start_date, req.end_date)

    from_status = req.status
    req.substitute_id = new_substitute_id
    req.substitute_status = "pending"
    req.status = sm.PENDING_SUBSTITUTE
    req.save(update_fields=["substitute_id", "substitute_status", "status", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=applicant_user_id,
        action="nominate_replacement_substitute",
        from_status=from_status,
        to_status=sm.PENDING_SUBSTITUTE,
        remarks=remarks or f"Nominated replacement substitute #{new_substitute_id}",
    )
    return req


# --- Unit Head Review (EL-UC-003, BR-EL-016..018) ---
@transaction.atomic
def review_unit_head(
    leave_request_id: int,
    unit_head_user_id: int,
    decision: str,  # 'approve', 'reject', 'recommended', 'not_recommended'
    remarks: str = "",
) -> LeaveRequest:
    """Review leave request at Unit Head stage."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id == unit_head_user_id:
        raise PermissionDenied("Unit Head cannot review or approve their own leave request (BR-EL-036).")

    if req.status not in (sm.PENDING_UNIT_HEAD, sm.SUBMITTED_LEGACY):
        raise sm.InvalidTransition(req.status, decision, "Request is not awaiting Unit Head review.")

    from_status = req.status
    year = req.start_date.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, category=req.category, year=year
    )

    # CL and RH: Unit Head is final decision authority (BR-EL-016)
    if req.category in UNIT_HEAD_FINAL_CATEGORIES:
        if decision == "approve":
            to_status = sm.APPROVED
            # Commit balance: pending -> availed
            balance.pending -= req.leave_days
            balance.availed += req.leave_days
            balance.save(update_fields=["pending", "availed", "updated_at"])
        elif decision == "reject":
            to_status = sm.REJECTED
            # Release pending balance
            balance.pending -= req.leave_days
            balance.save(update_fields=["pending", "updated_at"])
        else:
            raise ValidationError("Unit Head must approve or reject CL/RH requests.")
    # Higher sanction categories: Unit Head records recommendation (BR-EL-017)
    else:
        if decision not in ("recommended", "not_recommended"):
            raise ValidationError("Unit Head must record 'recommended' or 'not_recommended' for higher-sanction leave.")
        to_status = sm.PENDING_SANCTION
        req.unit_head_recommendation = decision

    req.unit_head_remarks = remarks
    req.status = to_status
    req.save(update_fields=["status", "unit_head_recommendation", "unit_head_remarks", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=unit_head_user_id,
        action=f"unit_head_{decision}",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


# --- Sanctioning Authority Decision (EL-UC-005, BR-EL-018, BR-EL-020) ---
@transaction.atomic
def sanction_leave_request(
    leave_request_id: int,
    authority_user_id: int,
    approve: bool,
    remarks: str = "",
    is_director: bool = False,
) -> LeaveRequest:
    """Final sanction decision for higher-sanction categories or Director self-sanction."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)

    # Director self-sanction exception (BR-EL-020)
    if req.status == sm.AWAITING_DIRECTOR_SANCTION:
        if not is_director or req.user_id != authority_user_id:
            raise PermissionDenied("Only the Director may execute self-sanction on this request.")
    else:
        if req.user_id == authority_user_id:
            raise PermissionDenied("Sanctioning Authority cannot approve their own leave request.")
        if req.status != sm.PENDING_SANCTION:
            raise sm.InvalidTransition(req.status, "sanction", "Request is not awaiting final sanction.")

    from_status = req.status
    year = req.start_date.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, category=req.category, year=year
    )

    if approve:
        to_status = sm.APPROVED
        balance.pending -= req.leave_days
        balance.availed += req.leave_days
    else:
        to_status = sm.REJECTED
        balance.pending -= req.leave_days

    balance.save(update_fields=["pending", "availed", "updated_at"])

    req.status = to_status
    req.sanctioning_remarks = remarks
    req.save(update_fields=["status", "sanctioning_remarks", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=authority_user_id,
        action="sanction_approve" if approve else "sanction_reject",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


# --- Immediate Withdrawal of In-Flight Request (EL-UC-007, BR-EL-022) ---
@transaction.atomic
def withdraw_leave_request(
    leave_request_id: int, applicant_user_id: int, remarks: str = ""
) -> LeaveRequest:
    """Applicant immediately terminates in-flight pending request before approval."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id != applicant_user_id:
        raise PermissionDenied("Only the applicant may withdraw their pending request.")

    if req.status not in sm.IN_FLIGHT_PENDING:
        raise sm.InvalidTransition(
            req.status, sm.WITHDRAWN, "Withdrawal is only permitted for in-flight requests before final approval."
        )

    from_status = req.status
    year = req.start_date.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, category=req.category, year=year
    )

    # Release pending balance reservation
    if req.leave_days:
        balance.pending -= req.leave_days
        balance.save(update_fields=["pending", "updated_at"])

    req.status = sm.WITHDRAWN
    req.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=applicant_user_id,
        action="withdraw",
        from_status=from_status,
        to_status=sm.WITHDRAWN,
        remarks=remarks or "Withdrawn by applicant.",
    )
    return req


# --- Approved Leave Cancellation (EL-UC-008, CW-EL-02, BR-EL-023) ---
@transaction.atomic
def request_cancellation(
    leave_request_id: int, applicant_user_id: int, remarks: str = ""
) -> LeaveRequest:
    """Applicant requests cancellation of approved leave before its start date (BR-EL-023)."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id != applicant_user_id:
        raise PermissionDenied("Only the applicant may request cancellation of approved leave.")

    if req.status != sm.APPROVED:
        raise sm.InvalidTransition(req.status, sm.CANCELLATION_PENDING_UNIT_HEAD, "Only approved leave can be cancelled.")

    today = datetime.date.today()
    if today >= req.start_date:
        raise ValidationError("Pre-start cancellation is unavailable once leave has started (BR-EL-023).")

    from_status = req.status
    to_status = sm.CANCELLATION_PENDING_UNIT_HEAD
    req.status = to_status
    req.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=applicant_user_id,
        action="request_cancellation",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


@transaction.atomic
def review_cancellation_unit_head(
    leave_request_id: int, unit_head_user_id: int, decision: str, remarks: str = ""
) -> LeaveRequest:
    """Unit Head reviews approved leave cancellation."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id == unit_head_user_id:
        raise PermissionDenied("Unit Head cannot review cancellation of their own leave.")

    if req.status != sm.CANCELLATION_PENDING_UNIT_HEAD:
        raise sm.InvalidTransition(req.status, decision, "Request is not awaiting Unit Head cancellation review.")

    from_status = req.status
    year = req.start_date.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, category=req.category, year=year
    )

    if req.category in UNIT_HEAD_FINAL_CATEGORIES:
        if decision == "approve":
            to_status = sm.CANCELLED
            # Restore deducted balance (availed -> 0)
            if req.leave_days:
                balance.availed -= req.leave_days
                balance.save(update_fields=["availed", "updated_at"])
        elif decision == "reject":
            to_status = sm.APPROVED  # Revert to approved, balance remains availed
        else:
            raise ValidationError("Unit Head must approve or reject CL/RH cancellation.")
    else:
        if decision not in ("recommended", "not_recommended"):
            raise ValidationError("Unit Head must record recommendation for higher-sanction cancellation.")
        to_status = sm.CANCELLATION_PENDING_SANCTION

    req.status = to_status
    req.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=unit_head_user_id,
        action=f"cancellation_unit_head_{decision}",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


@transaction.atomic
def sanction_cancellation(
    leave_request_id: int, authority_user_id: int, approve: bool, remarks: str = ""
) -> LeaveRequest:
    """Sanctioning Authority makes final decision on higher-sanction cancellation."""
    req = LeaveRequest.objects.select_for_update().get(pk=leave_request_id)
    if req.user_id == authority_user_id:
        raise PermissionDenied("Sanctioning Authority cannot approve cancellation of their own leave.")

    if req.status != sm.CANCELLATION_PENDING_SANCTION:
        raise sm.InvalidTransition(req.status, "sanction_cancellation", "Request is not awaiting final cancellation sanction.")

    from_status = req.status
    year = req.start_date.year
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=req.user_id, category=req.category, year=year
    )

    if approve:
        to_status = sm.CANCELLED
        # Restore deducted balance
        if req.leave_days:
            balance.availed -= req.leave_days
            balance.save(update_fields=["availed", "updated_at"])
    else:
        to_status = sm.APPROVED  # Revert to approved, balance remains availed

    req.status = to_status
    req.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=authority_user_id,
        action="cancellation_sanction_approve" if approve else "cancellation_sanction_reject",
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
    return req


# --- Idempotent Year-End VL to EL Conversion & Rollover (BR-EL-007, BR-EL-008) ---
@transaction.atomic
def process_year_end_vl_conversion(user_id: int, year: int) -> tuple[Decimal, Decimal]:
    """Convert unused faculty VL to EL at 2:1 ratio idempotently (BR-EL-007, BR-EL-008)."""
    # 1. Idempotency guard: check processing log
    existing_log = YearEndProcessingLog.objects.filter(
        user_id=user_id, year=year, process_type="vl_to_el_conversion"
    ).first()
    if existing_log:
        return existing_log.vl_converted, existing_log.el_credited

    vl_balance = get_or_create_locked_balance(user_id, "vl", year, is_faculty=True)
    unused_vl = vl_balance.available
    if unused_vl <= Decimal("0.0"):
        # Zero conversion
        YearEndProcessingLog.objects.create(
            user_id=user_id,
            year=year,
            process_type="vl_to_el_conversion",
            vl_converted=Decimal("0.0"),
            el_credited=Decimal("0.0"),
        )
        return Decimal("0.0"), Decimal("0.0")

    # 2. Calculate 2:1 conversion (including fractions)
    el_to_credit = unused_vl / Decimal("2.0")

    # 3. Close VL in year Y (converted_out)
    vl_balance.converted_out += unused_vl
    vl_balance.save(update_fields=["converted_out", "updated_at"])

    # 4. Credit EL in next year Y+1 (converted_in)
    next_year_el_balance = get_or_create_locked_balance(user_id, "el", year + 1, is_faculty=True)
    next_year_el_balance.converted_in += el_to_credit
    next_year_el_balance.save(update_fields=["converted_in", "updated_at"])

    # 5. Record idempotency log
    YearEndProcessingLog.objects.create(
        user_id=user_id,
        year=year,
        process_type="vl_to_el_conversion",
        vl_converted=unused_vl,
        el_credited=el_to_credit,
    )

    return unused_vl, el_to_credit


# --- Holiday Calendar Publication (EL-UC-015, BR-EL-031, CFR-EL-025) ---
@transaction.atomic
def publish_holiday_calendar(year: int, publisher_user_id: int) -> HolidayCalendar:
    """Publish the holiday calendar for an academic/calendar year."""
    calendar, _ = HolidayCalendar.objects.select_for_update().get_or_create(year=year)
    calendar.is_published = True
    calendar.published_at = timezone.now()
    calendar.published_by = publisher_user_id
    calendar.save(update_fields=["is_published", "published_at", "published_by", "updated_at"])
    return calendar


# --- Offline Sanctioned Leave Synchronization (EL-UC-016, BR-EL-029) ---
@transaction.atomic
def record_offline_sanctioned_leave(
    admin_user_id: int,
    applicant_user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    sanction_reference: str,
    is_faculty: bool = False,
) -> LeaveRequest:
    """Record an already sanctioned offline leave directly into system records (EL-UC-016, BR-EL-029)."""
    if not sanction_reference.strip():
        raise ValidationError("Sanction reference evidence is mandatory for offline records (BR-EL-029).")

    validate_no_overlap(applicant_user_id, category, start_date, end_date)
    leave_days = calculate_leave_days(category, start_date, end_date)

    year = start_date.year
    balance = get_or_create_locked_balance(applicant_user_id, category, year, is_faculty=is_faculty)
    if balance.available < leave_days:
        raise ValidationError(
            f"Insufficient leave balance for offline entry: available {balance.available}, required {leave_days}."
        )

    # Immediately commit to availed (no pending state)
    balance.availed += leave_days
    balance.save(update_fields=["availed", "updated_at"])

    req = LeaveRequest.objects.create(
        user_id=applicant_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        leave_days=leave_days,
        reason=reason,
        status=sm.APPROVED,
        sanctioning_remarks=f"Offline Sanction Reference: {sanction_reference}",
    )

    LeaveActionHistory.objects.create(
        leave_request=req,
        actor_id=admin_user_id,
        action="offline_sanction_record",
        from_status=sm.DRAFT,
        to_status=sm.APPROVED,
        remarks=f"Recorded offline sanctioned leave. Reference: {sanction_reference}",
    )

    return req
