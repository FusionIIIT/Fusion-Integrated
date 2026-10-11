"""Services implementing transactional logic and complete business workflows (CW-EL-01 to 04).
Model 2 (Qwen 14B) implementation.
"""
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from modules.leave.models import (
    LeaveRequest, LeaveAccount, LeaveTransitionAudit,
    HolidayCalendar, AcademicVacationPeriod, LeavePolicyConfig
)
from modules.leave.domain import rules


@transaction.atomic
def submit_leave_request(
    applicant_id: str,
    applicant_role: str,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    is_half_day: bool = False,
    half_day_type: str = None,
    is_station_leave: bool = False,
    station_destination: str = None,
    station_address: str = None,
    substitute_id: str = None,
    unit_head_id: str = None,
    sanctioning_authority_id: str = None,
) -> LeaveRequest:
    """EL-UC-001 / CW-EL-01: Apply for Leave with complete validation & routing."""
    if start_date > end_date:
        raise ValidationError("Start date cannot succeed end date.")

    if category not in rules.ALL_CATEGORIES:
        raise ValidationError(f"Category {category} is not supported in ELM baseline (BR-EL-001).")

    # Restricted Holiday calendar check (BR-EL-003, BR-EL-031)
    if category == rules.CAT_RH:
        rh_exists = HolidayCalendar.objects.filter(
            date=start_date, is_restricted_holiday=True, is_published=True
        ).exists()
        if not rh_exists or start_date != end_date:
            raise ValidationError("RH request must correspond to an applicable published RH date (BR-EL-003).")

    # Faculty VL Academic Calendar check (BR-EL-006)
    if category == rules.CAT_VL:
        in_vacation = AcademicVacationPeriod.objects.filter(
            start_date__lte=start_date, end_date__gte=end_date
        ).exists()
        if not in_vacation:
            raise ValidationError("Faculty VL may only be availed during a scheduled vacation period (BR-EL-006).")

    # Station Leave coupling (BR-EL-013)
    if is_station_leave and not station_destination:
        raise ValidationError("Station leave destination is required when station leave is requested.")

    # Substitute validation (BR-EL-014)
    has_substitute = bool(substitute_id)
    if has_substitute:
        if substitute_id == applicant_id:
            raise ValidationError("Self-nomination for substitute is strictly prohibited (BR-EL-014).")

        sub_leave_active = LeaveRequest.objects.filter(
            applicant_id=substitute_id,
            status__in=[rules.ST_APPROVED, rules.ST_AWAITING_UNIT_HEAD, rules.ST_AWAITING_SANCTION],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if sub_leave_active:
            raise ValidationError("Nominated substitute has active or pending leave during this interval (BR-EL-014).")

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
            raise ValidationError("Impermissible overlap with an active or pending leave request (BR-EL-012).")

    # Calculate chargeable days (BR-EL-010, BR-EL-011)
    holidays = set(HolidayCalendar.objects.filter(is_published=True).values_list("date", flat=True))
    chargeable = rules.calculate_days(category, start_date, end_date, is_half_day, holidays)

    # Entitlement / Balance validation (BR-EL-002, 004, 005, 009)
    account, _ = LeaveAccount.objects.get_or_create(
        user_id=applicant_id, category=category, year=start_date.year,
        defaults={"balance": 0.0, "employee_type": "faculty" if applicant_role == "faculty" else "staff"}
    )
    if account.balance < chargeable:
        raise ValidationError(f"Insufficient leave balance for {category}. Available: {account.balance}, Requested: {chargeable}")

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
def nominate_replacement_substitute(request_id: int, applicant_id: str, replacement_id: str) -> LeaveRequest:
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

    from_state = req.status

    if req.category in (rules.CAT_CL, rules.CAT_RH):
        # Unit Head final authority for CL/RH (BR-EL-016)
        if action == "APPROVE":
            req.status = rules.ST_APPROVED
            acc = LeaveAccount.objects.get(user_id=req.applicant_id, category=req.category, year=req.start_date.year)
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
            req.unit_head_recommendation = "RECOMMENDED" if action == "RECOMMEND" else "NOT_RECOMMENDED"
            req.status = rules.ST_AWAITING_ESTABLISHMENT if establishment_configured else rules.ST_AWAITING_SANCTION
        else:
            raise ValidationError("Higher-sanction leave requires RECOMMEND or NOT_RECOMMEND.")

    req.save()
    LeaveTransitionAudit.objects.create(
        request=req, actor_id=unit_head_id, action=f"UH_{action}",
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def route_establishment(request_id: int, establishment_user_id: str, remarks: str = "") -> LeaveRequest:
    """EL-UC-004: Establishment processing verification & forwarding."""
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    if req.status != rules.ST_AWAITING_ESTABLISHMENT:
        raise ValidationError("Request not awaiting Establishment routing.")

    from_state = req.status
    req.establishment_user_id = establishment_user_id
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

    from_state = req.status
    if approve:
        req.status = rules.ST_APPROVED
        acc = LeaveAccount.objects.get(user_id=req.applicant_id, category=req.category, year=req.start_date.year)
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
        from_state=from_state, to_state=rules.ST_WITHDRAWN, remarks="Pending request withdrawn immediately."
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
        raise ValidationError("Cannot cancel leave that has already started (BR-EL-023). Use resumption instead.")

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
        acc = LeaveAccount.objects.get(user_id=req.applicant_id, category=req.category, year=req.start_date.year)
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

    from_state = req.status
    actual_date = req.actual_resumption_date
    approved_end = req.end_date

    if actual_date == approved_end:
        # Normal resumption: no period or balance adjustment (AFR-EL-021.5)
        outcome_action = "RESUMPTION_NORMAL"
    elif actual_date < approved_end:
        # Early return: restore unused days (AFR-EL-021.7)
        delta = (approved_end - actual_date).days
        acc = LeaveAccount.objects.get(user_id=req.applicant_id, category=req.category, year=req.start_date.year)
        acc.balance += delta
        acc.save()
        outcome_action = "RESUMPTION_EARLY_ADJUSTED"
    else:
        # Late return: deduct extra days (AFR-EL-021.8)
        delta = (actual_date - approved_end).days
        acc = LeaveAccount.objects.get(user_id=req.applicant_id, category=req.category, year=req.start_date.year)
        acc.balance -= delta
        acc.save()
        outcome_action = "RESUMPTION_LATE_ADJUSTED"

    req.status = rules.ST_APPROVED  # Leave remains Approved, no generic closed state (AFR-EL-021.10)
    req.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=authority_id, action=outcome_action,
        from_state=from_state, to_state=req.status, remarks=remarks
    )
    return req


@transaction.atomic
def sync_offline_sanctioned_leave(
    admin_id: str,
    applicant_id: str,
    employee_type: str,
    category: str,
    start_date: date,
    end_date: date,
    chargeable_days: float,
    reference_evidence: str
) -> LeaveRequest:
    """EL-UC-016 (CFR-EL-027, BR-EL-029): Retrospective synchronization of offline leave."""
    req = LeaveRequest.objects.create(
        applicant_id=applicant_id,
        applicant_role="faculty" if employee_type == "faculty" else "staff",
        category=category,
        start_date=start_date,
        end_date=end_date,
        chargeable_days=chargeable_days,
        purpose="Offline sanctioned leave record synchronization",
        status=rules.ST_APPROVED,
        is_offline_sync=True,
        offline_sanction_reference=reference_evidence,
    )

    acc, _ = LeaveAccount.objects.get_or_create(
        user_id=applicant_id, category=category, year=start_date.year,
        defaults={"balance": 0.0, "employee_type": employee_type}
    )
    acc.balance -= chargeable_days
    acc.save()

    LeaveTransitionAudit.objects.create(
        request=req, actor_id=admin_id, action="SYNC_OFFLINE_RECORD",
        from_state="OFFLINE", to_state=rules.ST_APPROVED, remarks=reference_evidence
    )
    return req
