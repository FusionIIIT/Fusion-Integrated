"""Services implementing transactional logic and complete business workflows (CW-EL-01 to 04).
Model 2 (Qwen 14B) implementation.
"""
from datetime import date
from math import isfinite

from django.core.exceptions import ValidationError
from django.db import transaction

from modules.leave.domain import rules
from modules.leave.models import (
    AcademicVacationPeriod,
    HolidayCalendar,
    HolidayCalendarEntry,
    HolidayCalendarRelease,
    LeaveAccount,
    LeaveHierarchyConfig,
    LeavePolicyConfig,
    LeaveRequest,
    LeaveSLASettings,
    LeaveTransitionAudit,
)
from modules.leave.services.attendance_sync import enqueue_resumption_sync

_BASELINE_ENTITLEMENTS = {
    rules.CAT_CL: 8.0,
    rules.CAT_RH: 2.0,
    rules.CAT_SCL: 15.0,
    rules.CAT_EL: 30.0,
    rules.CAT_COL: 20.0,
    rules.CAT_VL: 60.0,
}


def _initial_leave_balance(category: str, employee_type: str) -> float:
    """Return the configured or baseline annual entitlement for a new account."""
    if category == rules.CAT_VL and employee_type != "faculty":
        return 0.0

    configured = LeavePolicyConfig.objects.filter(category=category).values_list(
        "annual_entitlement", flat=True
    ).first()
    if configured is not None:
        return configured

    if category == rules.CAT_EL and employee_type == "faculty":
        return 0.0
    return _BASELINE_ENTITLEMENTS.get(category, 0.0)


def _policy_continuous_count(category: str) -> bool:
    configured = LeavePolicyConfig.objects.filter(category=category).values_list(
        "is_continuous_count", flat=True
    ).first()
    if configured is not None:
        return configured
    return category in (rules.CAT_EL, rules.CAT_COL, rules.CAT_VL)


def effective_holiday_dates() -> set[date]:
    """Use staged-release data once published; retain legacy rows until then."""
    release = HolidayCalendarRelease.objects.filter(is_current=True).first()
    if release:
        return set(release.entries.values_list("date", flat=True))
    return set(HolidayCalendar.objects.filter(is_published=True).values_list("date", flat=True))


@transaction.atomic
def save_policy_config(category: str, values: dict) -> LeavePolicyConfig:
    if category not in rules.ALL_CATEGORIES:
        raise ValidationError("Unsupported leave category.")
    allowed = {
        "annual_entitlement", "allows_half_day", "allows_carry_forward",
        "is_continuous_count", "requires_substitute_default", "requires_medical_proof",
    }
    if not values or values.keys() - allowed:
        raise ValidationError("Policy values contain unsupported fields.")
    entitlement = values.get("annual_entitlement")
    if entitlement is not None and (not isfinite(entitlement) or entitlement < 0):
        raise ValidationError("Annual entitlement must be finite and non-negative.")
    config, _ = LeavePolicyConfig.objects.get_or_create(
        category=category,
        defaults={
            "allows_half_day": category == rules.CAT_CL,
            "is_continuous_count": category in (rules.CAT_EL, rules.CAT_COL, rules.CAT_VL),
        },
    )
    for field, value in values.items():
        setattr(config, field, value)
    config.save()
    return config


@transaction.atomic
def save_sla_config(task_code: str, values: dict) -> LeaveSLASettings:
    allowed = {"reminder_hours", "escalation_hours", "escalation_authority"}
    if not task_code.strip() or not values or values.keys() - allowed:
        raise ValidationError("Task code and supported SLA fields are required.")
    for field in ("reminder_hours", "escalation_hours"):
        if field in values and (
            isinstance(values[field], bool)
            or not isinstance(values[field], int)
            or values[field] < 0
        ):
            raise ValidationError(f"{field} must be a non-negative integer.")
    if "escalation_authority" in values and not values["escalation_authority"].strip():
        raise ValidationError("Escalation authority cannot be blank.")
    settings, _ = LeaveSLASettings.objects.get_or_create(task_code=task_code.strip())
    for field, value in values.items():
        setattr(settings, field, value)
    settings.save()
    return settings


@transaction.atomic
def save_hierarchy_config(department: str, applicant_role: str, category: str,
                          values: dict) -> LeaveHierarchyConfig:
    if not department.strip() or not applicant_role.strip() or category not in rules.ALL_CATEGORIES:
        raise ValidationError("Department, applicant role, and valid category are required.")
    if applicant_role == "director":
        raise ValidationError("Director self-sanction does not use ordinary routing configuration.")
    allowed = {"unit_head_id", "establishment_user_id", "sanctioning_authority_id"}
    if not values or values.keys() - allowed:
        raise ValidationError("Hierarchy values contain unsupported fields.")
    route, _ = LeaveHierarchyConfig.objects.get_or_create(
        department=department.strip(), applicant_role=applicant_role.strip(), category=category
    )
    for field, value in values.items():
        setattr(route, field, value)
    if not route.unit_head_id:
        raise ValidationError("A Unit Head is required for a configured route.")
    if category not in (rules.CAT_CL, rules.CAT_RH) and not route.sanctioning_authority_id:
        raise ValidationError("A sanctioning authority is required for this leave category.")
    route.save()
    return route


def _validate_calendar_entries(entries: list[dict]) -> None:
    if not entries:
        raise ValidationError("A calendar must contain at least one date entry.")
    dates = [entry["date"] for entry in entries]
    if len(dates) != len(set(dates)):
        raise ValidationError("A calendar cannot contain duplicate dates.")
    if any(not entry["title"].strip() for entry in entries):
        raise ValidationError("Calendar entry titles cannot be blank.")


@transaction.atomic
def stage_holiday_calendar(
    name: str, created_by: str, entries: list[dict]
) -> HolidayCalendarRelease:
    if not name.strip():
        raise ValidationError("Calendar name is required.")
    _validate_calendar_entries(entries)
    release = HolidayCalendarRelease.objects.create(
        name=name.strip(), created_by=str(created_by)
    )
    HolidayCalendarEntry.objects.bulk_create([
        HolidayCalendarEntry(
            release=release, date=entry["date"], title=entry["title"].strip(),
            is_restricted_holiday=entry.get("is_restricted_holiday", False),
        ) for entry in entries
    ])
    return release


@transaction.atomic
def revise_holiday_calendar(
    release_id: int, name: str, entries: list[dict]
) -> HolidayCalendarRelease:
    release = HolidayCalendarRelease.objects.select_for_update().get(pk=release_id)
    if release.is_current or release.published_at is not None:
        raise ValidationError("A published calendar cannot be revised; stage a replacement.")
    if not name.strip():
        raise ValidationError("Calendar name is required.")
    _validate_calendar_entries(entries)
    release.entries.all().delete()
    HolidayCalendarEntry.objects.bulk_create([
        HolidayCalendarEntry(
            release=release, date=entry["date"], title=entry["title"].strip(),
            is_restricted_holiday=entry.get("is_restricted_holiday", False),
        ) for entry in entries
    ])
    release.name = name.strip()
    release.save(update_fields=("name",))
    return release


@transaction.atomic
def publish_holiday_calendar(release_id: int) -> HolidayCalendarRelease:
    release = HolidayCalendarRelease.objects.select_for_update().get(pk=release_id)
    if not release.entries.exists():
        raise ValidationError("An empty calendar cannot be published.")
    HolidayCalendarRelease.objects.filter(is_current=True).update(is_current=False)
    release.is_current = True
    from django.utils import timezone
    release.published_at = timezone.now()
    release.save(update_fields=("is_current", "published_at"))
    return release


@transaction.atomic
def submit_leave_request(
    applicant_id: str,
    applicant_role: str,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    is_half_day: bool = False,
    half_day_type: str | None = None,
    is_station_leave: bool = False,
    station_destination: str | None = None,
    station_address: str | None = None,
    substitute_id: str | None = None,
    unit_head_id: str | None = None,
    sanctioning_authority_id: str | None = None,
    department: str = "CSE",
    employee_type: str | None = None,
) -> LeaveRequest:
    """EL-UC-001 / CW-EL-01: Apply for Leave with complete validation & routing."""
    if start_date > end_date:
        raise ValidationError("Start date cannot succeed end date.")

    if category not in rules.ALL_CATEGORIES:
        raise ValidationError(f"Category {category} is not supported in ELM baseline (BR-EL-001).")

    # Resolve routes from current admin configuration, never applicant payload.
    route = None
    if applicant_role != "director":
        route = LeaveHierarchyConfig.objects.filter(
            department=department, applicant_role=applicant_role, category=category
        ).first()
        if route is None:
            raise ValidationError(
                "No current hierarchy route is configured for this department, role, and category."
            )
        unit_head_id = route.unit_head_id
        sanctioning_authority_id = route.sanctioning_authority_id

    # Restricted Holiday calendar check (BR-EL-003, BR-EL-031)
    if category == rules.CAT_RH:
        release = HolidayCalendarRelease.objects.filter(is_current=True).first()
        rh_exists = (
            release.entries.filter(date=start_date, is_restricted_holiday=True).exists()
            if release else HolidayCalendar.objects.filter(
                date=start_date, is_restricted_holiday=True, is_published=True
            ).exists()
        )
        if not rh_exists or start_date != end_date:
            raise ValidationError(
                "RH request must correspond to an applicable published RH date (BR-EL-003)."
            )

    # Faculty VL Academic Calendar check (BR-EL-006)
    if category == rules.CAT_VL:
        in_vacation = AcademicVacationPeriod.objects.filter(
            start_date__lte=start_date, end_date__gte=end_date
        ).exists()
        if not in_vacation:
            raise ValidationError(
                "Faculty VL may only be availed during a scheduled vacation period (BR-EL-006)."
            )

    policy = LeavePolicyConfig.objects.filter(category=category).first()
    half_day_allowed = policy.allows_half_day if policy else category == rules.CAT_CL
    if is_half_day and (category != rules.CAT_CL or not half_day_allowed):
        raise ValidationError("Half-day leave is not allowed by the current policy.")

    # Station Leave coupling (BR-EL-013)
    if is_station_leave and not station_destination:
        raise ValidationError(
            "Station leave destination is required when station leave is requested."
        )

    # Substitute validation (BR-EL-014)
    requires_substitute = policy.requires_substitute_default if policy else False
    has_substitute = bool(substitute_id)
    if requires_substitute and not has_substitute:
        raise ValidationError("A substitute is required by the current leave policy.")
    if has_substitute:
        if substitute_id == applicant_id:
            raise ValidationError(
                "Self-nomination for substitute is strictly prohibited (BR-EL-014)."
            )

        sub_leave_active = LeaveRequest.objects.filter(
            applicant_id=substitute_id,
            status__in=[rules.ST_APPROVED, rules.ST_AWAITING_UNIT_HEAD, rules.ST_AWAITING_SANCTION],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if sub_leave_active:
            raise ValidationError(
                "Nominated substitute has active or pending leave during this interval (BR-EL-014)."
            )

    # Overlap validation with CL half-day exception (BR-EL-012)
    existing_requests = LeaveRequest.objects.filter(
        applicant_id=applicant_id,
        status__in=[
            rules.ST_APPROVED, rules.ST_AWAITING_UNIT_HEAD, rules.ST_AWAITING_SANCTION,
            rules.ST_AWAITING_SUBSTITUTE, rules.ST_AWAITING_DIRECTOR_SELF_SANCTION
        ]
    )
    for req in existing_requests:
        if rules.check_applicant_overlap(
            start_date, end_date, is_half_day, half_day_type,
            req.start_date, req.end_date, req.is_half_day, req.half_day_type
        ):
            raise ValidationError(
                "Impermissible overlap with an active or pending leave request (BR-EL-012)."
            )

    # Calculate chargeable days (BR-EL-010, BR-EL-011)
    holidays = effective_holiday_dates()
    chargeable = rules.calculate_days(
        category, start_date, end_date, is_half_day, holidays,
        is_continuous_count=_policy_continuous_count(category),
    )

    # Entitlement / Balance validation (BR-EL-002, 004, 005, 009)
    employee_type = employee_type or ("faculty" if applicant_role == "faculty" else "staff")
    if employee_type not in ("faculty", "staff"):
        raise ValidationError("Employee type must be faculty or staff.")
    account, _ = LeaveAccount.objects.get_or_create(
        user_id=applicant_id, category=category, year=start_date.year,
        defaults={
            "balance": _initial_leave_balance(category, employee_type),
            "employee_type": employee_type,
        },
    )
    if account.balance < chargeable:
        raise ValidationError(
            f"Insufficient leave balance for {category}. Available: {account.balance}, "
            f"Requested: {chargeable}"
        )

    # Determine initial state
    if has_substitute:
        init_state = rules.ST_AWAITING_SUBSTITUTE
    elif applicant_role == "director":
        init_state = rules.ST_AWAITING_DIRECTOR_SELF_SANCTION
    else:
        init_state = rules.ST_AWAITING_UNIT_HEAD

    req = LeaveRequest.objects.create(
        applicant_id=applicant_id,
        applicant_role=applicant_role,
        category=category,
        start_date=start_date,
        end_date=end_date,
        chargeable_days=chargeable,
        purpose=purpose,
        is_half_day=is_half_day,
        half_day_type=half_day_type,
        is_station_leave=is_station_leave,
        station_destination=station_destination,
        station_address=station_address,
        requires_substitute=has_substitute,
        substitute_id=substitute_id,
        substitute_status="PENDING" if has_substitute else "NOT_REQUIRED",
        unit_head_id=unit_head_id,
        sanctioning_authority_id=sanctioning_authority_id,
        establishment_user_id=route.establishment_user_id if route else None,
        routing_config=route,
        department=department,
        status=init_state,
    )

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=applicant_id, action="SUBMIT",
        from_state=rules.ST_DRAFT, to_state=init_state, remarks="Leave application submitted."
    )
    return req


@transaction.atomic
def process_substitute_response(request_id: int, substitute_id: str, accept: bool) -> LeaveRequest:
    """EL-UC-002 (BW-EL-02, BW-EL-03, BW-EL-05, BW-EL-08): Handle substitute response."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.substitute_id != substitute_id or req.status != rules.ST_AWAITING_SUBSTITUTE:
        raise ValidationError("Request is not awaiting substitute response from this user.")

    from_state = req.status
    if accept:
        req.substitute_status = "ACCEPTED"
        if req.applicant_role == "director":
            req.status = rules.ST_AWAITING_DIRECTOR_SELF_SANCTION
        else:
            req.status = rules.ST_AWAITING_UNIT_HEAD
    else:
        req.substitute_status = "DECLINED"
        req.status = rules.ST_APPLICANT_ACTION_REQUIRED

    req.save()
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=substitute_id,
        action="SUBSTITUTE_ACCEPT" if accept else "SUBSTITUTE_DECLINE",
        from_state=from_state, to_state=req.status
    )
    return req


@transaction.atomic
def nominate_replacement_substitute(
    request_id: int, applicant_id: str, replacement_id: str
) -> LeaveRequest:
    """EL-UC-019 (BW-EL-03, BW-EL-06, BW-EL-09): Replacement nominee after decline."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id or req.status != rules.ST_APPLICANT_ACTION_REQUIRED:
        raise ValidationError("Action not permitted in current state.")

    if replacement_id == applicant_id:
        raise ValidationError("Cannot nominate self as replacement substitute.")

    req.substitute_id = replacement_id
    req.substitute_status = "PENDING"
    req.status = rules.ST_AWAITING_SUBSTITUTE
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=applicant_id, action="NOMINATE_REPLACEMENT",
        from_state=rules.ST_APPLICANT_ACTION_REQUIRED, to_state=req.status
    )
    return req


@transaction.atomic
def review_unit_head(
    request_id: int,
    unit_head_id: str,
    action: str,  # 'APPROVE', 'REJECT', 'RECOMMEND', 'NOT_RECOMMEND'
    remarks: str = "",
    establishment_configured: bool = False
) -> LeaveRequest:
    """EL-UC-003: Review leave at Unit Head stage."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status != rules.ST_AWAITING_UNIT_HEAD:
        raise ValidationError("Request not in Awaiting Unit Head Review state.")
    if req.routing_config_id is None or req.unit_head_id != str(unit_head_id):
        raise ValidationError("Request is not assigned to this Unit Head.")

    from_state = req.status

    if req.category in (rules.CAT_CL, rules.CAT_RH):
        # Unit Head final authority for CL/RH (BR-EL-016)
        if action == "APPROVE":
            req.status = rules.ST_APPROVED
            acc = LeaveAccount.objects.get(
                user_id=req.applicant_id, category=req.category, year=req.start_date.year
            )
            acc.balance -= req.chargeable_days
            acc.save()
        elif action == "REJECT":
            req.status = rules.ST_REJECTED
            req.final_decision_notes = remarks
        else:
            raise ValidationError("CL and RH require APPROVE or REJECT.")
    else:
        # SCL, EL, COL, VL Unit Head recommendation (BR-EL-017, BR-EL-018)
        if action in ("RECOMMEND", "NOT_RECOMMEND"):
            req.unit_head_recommendation = (
                "RECOMMENDED" if action == "RECOMMEND" else "NOT_RECOMMENDED"
            )
            req.status = (
                rules.ST_AWAITING_ESTABLISHMENT
                if req.establishment_user_id else rules.ST_AWAITING_SANCTION
            )
        else:
            raise ValidationError("Higher-sanction leave requires RECOMMEND or NOT_RECOMMEND.")

    req.save()
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=unit_head_id, action=f"UH_{action}",
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def route_establishment(
    request_id: int, establishment_user_id: str, remarks: str = ""
) -> LeaveRequest:
    """EL-UC-004: Establishment processing verification & forwarding."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status != rules.ST_AWAITING_ESTABLISHMENT:
        raise ValidationError("Request not awaiting Establishment routing.")
    if req.routing_config_id is None or req.establishment_user_id != str(establishment_user_id):
        raise ValidationError("Request is not assigned to this Establishment officer.")

    from_state = req.status
    req.status = rules.ST_AWAITING_SANCTION
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=establishment_user_id, action="ESTABLISHMENT_FORWARD",
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def sanction_decision(
    request_id: int,
    sanctioning_id: str,
    approve: bool,
    remarks: str = ""
) -> LeaveRequest:
    """EL-UC-005: Final Sanctioning Decision (Dean, Registrar, Director)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status not in (rules.ST_AWAITING_SANCTION, rules.ST_AWAITING_DIRECTOR_SELF_SANCTION):
        raise ValidationError("Request not awaiting sanction decision.")
    director_self_sanction = (
        req.status == rules.ST_AWAITING_DIRECTOR_SELF_SANCTION
        and req.applicant_role == "director"
        and req.applicant_id == str(sanctioning_id)
    )
    if (
        not director_self_sanction
        and (req.routing_config_id is None
             or req.sanctioning_authority_id != str(sanctioning_id))
    ):
        raise ValidationError("Request is not assigned to this sanctioning authority.")

    from_state = req.status
    if approve:
        req.status = rules.ST_APPROVED
        acc = LeaveAccount.objects.get(
            user_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        acc.balance -= req.chargeable_days
        acc.save()
    else:
        req.status = rules.ST_REJECTED
        req.final_decision_notes = remarks

    req.save()
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=sanctioning_id,
        action="FINAL_APPROVE" if approve else "FINAL_REJECT",
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def withdraw_request(request_id: int, applicant_id: str) -> LeaveRequest:
    """EL-UC-007 (BR-EL-022, BR-EL-034): Immediate pending withdrawal before final approval."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise ValidationError("Unauthorized.")
    if req.status in (rules.ST_APPROVED, rules.ST_REJECTED, rules.ST_WITHDRAWN, rules.ST_CANCELLED):
        raise ValidationError("Cannot withdraw finalized or approved leave.")

    from_state = req.status
    req.status = rules.ST_WITHDRAWN
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=applicant_id, action="WITHDRAW",
        from_state=from_state, to_state=rules.ST_WITHDRAWN,
        remarks="Pending request withdrawn immediately.",
    )
    return req


@transaction.atomic
def request_cancellation_before_start(request_id: int, applicant_id: str) -> LeaveRequest:
    """EL-UC-008 / CW-EL-02 (BR-EL-023): Pre-start cancellation request."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id:
        raise ValidationError("Unauthorized.")
    if req.status != rules.ST_APPROVED:
        raise ValidationError("Only approved leave can be cancelled.")
    if req.start_date <= date.today():
        raise ValidationError(
            "Cannot cancel leave that has already started (BR-EL-023). Use resumption instead."
        )

    from_state = req.status
    req.status = rules.ST_CANCELLATION_PENDING_UH
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=applicant_id, action="REQUEST_CANCELLATION",
        from_state=from_state, to_state=req.status
    )
    return req


@transaction.atomic
def decide_cancellation(
    request_id: int,
    authority_id: str,
    approve: bool,
    remarks: str = ""
) -> LeaveRequest:
    """Final decision for cancellation request (CW-EL-02, BR-EL-023)."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    from_state = req.status

    if approve:
        req.status = rules.ST_CANCELLED
        # Restore deducted balance (AFR-EL-019.5)
        acc = LeaveAccount.objects.get(
            user_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        acc.balance += req.chargeable_days
        acc.save()
    else:
        req.status = rules.ST_APPROVED  # Original approval preserved unchanged (AFR-EL-019.6)

    req.save()
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=authority_id,
        action="CANCEL_APPROVE" if approve else "CANCEL_REJECT",
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def submit_resumption(
    request_id: int,
    applicant_id: str,
    actual_date: date,
    notes: str = ""
) -> LeaveRequest:
    """EL-UC-010 / CW-EL-04 (BR-EL-027): Submit return to duty declaration."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.applicant_id != applicant_id or req.status != rules.ST_APPROVED:
        raise ValidationError("Invalid request for duty resumption.")
    if req.category not in (rules.CAT_EL, rules.CAT_COL, rules.CAT_VL):
        raise ValidationError("Resumption review applies only to EL, COL, and VL (BR-EL-027).")

    from_state = req.status
    req.actual_resumption_date = actual_date
    req.resumption_notes = notes
    req.status = rules.ST_RESUMPTION_PENDING
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=applicant_id, action="SUBMIT_RESUMPTION",
        from_state=from_state, to_state=req.status, remarks=notes
    )
    return req


@transaction.atomic
def review_resumption(
    request_id: int,
    authority_id: str,
    remarks: str = ""
) -> LeaveRequest:
    """EL-UC-011 / CW-EL-04 (BR-EL-028): Sanctioning authority reviews resumption."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status != rules.ST_RESUMPTION_PENDING:
        raise ValidationError("Request not in resumption review pending state.")
    if req.routing_config_id is None or req.sanctioning_authority_id != str(authority_id):
        raise ValidationError("Request is not assigned to this sanctioning authority.")

    from_state = req.status
    actual_date = req.actual_resumption_date
    approved_end = req.end_date

    if actual_date == approved_end:
        # Normal resumption: no period or balance adjustment (AFR-EL-021.5)
        outcome_action = "RESUMPTION_NORMAL"
    elif actual_date < approved_end:
        # Early return: restore unused days (AFR-EL-021.7)
        delta = (approved_end - actual_date).days
        acc = LeaveAccount.objects.get(
            user_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        acc.balance += delta
        acc.save()
        req.end_date = actual_date
        outcome_action = "RESUMPTION_EARLY_ADJUSTED"
    else:
        # Late return: deduct extra days (AFR-EL-021.8)
        delta = (actual_date - approved_end).days
        acc = LeaveAccount.objects.get(
            user_id=req.applicant_id, category=req.category, year=req.start_date.year
        )
        acc.balance -= delta
        acc.save()
        req.end_date = actual_date
        outcome_action = "RESUMPTION_LATE_ADJUSTED"

    # Leave remains Approved; the specification has no generic closed state.
    req.status = rules.ST_APPROVED
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=authority_id, action=outcome_action,
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    enqueue_resumption_sync(req, outcome_action, approved_end)
    return req


@transaction.atomic
def sync_offline_sanctioned_leave(
    admin_id: str, applicant_id: str, employee_type: str, category: str,
    start_date: date, end_date: date, chargeable_days: float,
    reference_evidence: str, unavailable_reason: str,
) -> LeaveRequest:
    """Compatibility name; server-calculates chargeable days and validates evidence."""
    return synchronize_offline_sanctioned_leave(
        admin_id=admin_id, applicant_id=applicant_id, employee_type=employee_type,
        category=category, start_date=start_date, end_date=end_date,
        reference_evidence=reference_evidence, unavailable_reason=unavailable_reason,
    )


@transaction.atomic
def synchronize_offline_sanctioned_leave(
    admin_id: str, applicant_id: str, employee_type: str, category: str,
    start_date: date, end_date: date, reference_evidence: str,
    unavailable_reason: str,
) -> LeaveRequest:
    """Record verified-by-operator offline sanction without another workflow."""
    if not applicant_id.strip() or not reference_evidence.strip() or not unavailable_reason.strip():
        raise ValidationError(
            "Employee, sanction evidence, and ELM-unavailable reason are required."
        )
    if employee_type not in ("faculty", "staff") or category not in rules.ALL_CATEGORIES:
        raise ValidationError("Employee type or leave category is invalid.")
    if start_date > end_date:
        raise ValidationError("Start date cannot succeed end date.")
    if LeaveRequest.objects.filter(
        applicant_id=applicant_id, is_offline_sync=True,
        offline_sanction_reference=reference_evidence.strip(),
    ).exists():
        raise ValidationError("This offline sanction reference has already been synchronized.")
    if category == rules.CAT_RH:
        release = HolidayCalendarRelease.objects.filter(is_current=True).first()
        valid_rh = (release.entries.filter(
            date=start_date, is_restricted_holiday=True
        ).exists() if release else HolidayCalendar.objects.filter(
            date=start_date, is_restricted_holiday=True, is_published=True
        ).exists())
        if start_date != end_date or not valid_rh:
            raise ValidationError("RH synchronization must match a published RH date.")
    if category == rules.CAT_VL:
        if employee_type != "faculty":
            raise ValidationError("VL synchronization is only valid for faculty.")
        if not AcademicVacationPeriod.objects.filter(
            start_date__lte=start_date, end_date__gte=end_date
        ).exists():
            raise ValidationError("Faculty VL must fall within a scheduled vacation period.")
    chargeable = rules.calculate_days(
        category, start_date, end_date, published_holidays=effective_holiday_dates(),
        is_continuous_count=_policy_continuous_count(category),
    )
    if chargeable <= 0:
        raise ValidationError("The offline leave interval has no chargeable days.")
    conflicting = LeaveRequest.objects.filter(
        applicant_id=applicant_id,
        status__in=[rules.ST_APPROVED, rules.ST_AWAITING_UNIT_HEAD,
                    rules.ST_AWAITING_SANCTION, rules.ST_AWAITING_SUBSTITUTE,
                    rules.ST_AWAITING_DIRECTOR_SELF_SANCTION],
        start_date__lte=end_date, end_date__gte=start_date,
    ).exists()
    if conflicting:
        raise ValidationError(
            "Offline leave overlaps an existing approved or pending leave record."
        )
    acc, _ = LeaveAccount.objects.select_for_update().get_or_create(
        user_id=applicant_id, category=category, year=start_date.year,
        defaults={"balance": _initial_leave_balance(category, employee_type),
                  "employee_type": employee_type},
    )
    if acc.employee_type != employee_type:
        raise ValidationError("Offline employee type conflicts with the existing leave account.")
    if acc.balance < chargeable:
        raise ValidationError("Offline leave exceeds the available leave balance.")
    req = LeaveRequest.objects.create(
        applicant_id=applicant_id, applicant_role=employee_type, category=category,
        start_date=start_date, end_date=end_date, chargeable_days=chargeable,
        purpose="Offline sanctioned leave synchronization", status=rules.ST_APPROVED,
        is_offline_sync=True, offline_sanction_reference=reference_evidence.strip(),
        offline_unavailable_reason=unavailable_reason.strip(),
    )
    acc.balance -= chargeable
    acc.save(update_fields=("balance", "updated_at"))
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=str(admin_id), action="SYNC_OFFLINE_RECORD",
        from_state="OFFLINE", to_state=rules.ST_APPROVED, remarks=reference_evidence.strip(),
    )
    return req


@transaction.atomic
def maintain_leave_record(
    request_id: int, actor_id: str, changes: dict, reason: str
) -> LeaveRequest:
    """Correct descriptive record fields only; this path cannot change sanction."""
    allowed = {
        "purpose", "department", "station_destination", "station_address", "resumption_notes"
    }
    if not reason.strip() or not changes or changes.keys() - allowed:
        raise ValidationError("Provide an audit reason and only permitted descriptive fields.")
    req = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if req.status not in (rules.ST_APPROVED, rules.ST_REJECTED) and not req.is_offline_sync:
        raise ValidationError("Only completed leave records can be maintained.")
    for field, value in changes.items():
        if not isinstance(value, str):
            raise ValidationError("Corrected record values must be text.")
        setattr(req, field, value)
    req.save(update_fields=(*changes.keys(), "updated_at"))
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=str(actor_id), action="ADMIN_RECORD_CORRECTION",
        from_state=req.status, to_state=req.status, remarks=reason.strip(),
    )
    return req
