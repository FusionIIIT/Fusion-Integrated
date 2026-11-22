"""Business logic services implementing MMS business rules and workflows."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.mms.domain import state_machine as sm
from modules.mms.models import (
    MessAnnouncement,
    MessBill,
    MessDeregistration,
    MessFeedback,
    MessMenu,
    MessRebate,
    MessRegistration,
    MessRegistrationWindow,
    MessRoleAssignment,
    MmsNotification,
    SpecialFoodRequest,
    VacationFoodResponse,
    VacationFoodSurvey,
)


def _send_notification(
    recipient_user_id: int, event_type: str, title: str, message: str
) -> MmsNotification:
    """Helper to trigger system-generated notification (BR-MMS-035)."""
    return MmsNotification.objects.create(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        title=title,
        message=message,
    )


# --- Role Assignment Services (CFR-MMS-002, 003, BR-MMS-002..007, MMS-UC-001) ---

@transaction.atomic
def assign_mess_role(
    *,
    actor,
    role_name: str,
    employee_user_id: int,
    start_date: date,
    end_date: date,
) -> MessRoleAssignment:
    """BR-MMS-002..007: Mess Admin assigns or reassigns time-bound Caretaker or Warden role.

    Ensures exactly one active Caretaker and exactly one active Warden exist at a time.
    """
    if not actor.has_permission("mms.role.manage"):
        raise PermissionDeniedError("Only Mess Admin can assign or reassign operational roles.")

    if role_name not in sm.ALLOWED_OPERATIONAL_ROLES:
        raise BadRequestError(
            f"Invalid role {role_name!r}. Allowed: {sm.ALLOWED_OPERATIONAL_ROLES}."
        )

    if end_date < start_date:
        raise BadRequestError("Role assignment end date cannot precede start date.")

    # BR-MMS-006: Mid-cycle reassignment immediately deactivates previous active assignment
    MessRoleAssignment.objects.filter(role_name=role_name, is_active=True).update(is_active=False)

    assignment = MessRoleAssignment.objects.create(
        role_name=role_name,
        assigned_user_id=employee_user_id,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        assigned_by_user_id=actor.user_id,
    )
    _send_notification(
        recipient_user_id=employee_user_id,
        event_type="role_assigned",
        title="MMS Role Assignment",
        message=f"You have been assigned the {role_name} role from {start_date} to {end_date}.",
    )
    return assignment


# --- Registration Services (CFR-MMS-004, BR-MMS-008..011, MMS-UC-002..004, BW-MMS-01..02) ---

@transaction.atomic
def open_registration_window(
    *,
    actor,
    academic_year: str,
    semester: str,
    start_date: date,
    end_date: date,
) -> MessRegistrationWindow:
    """BR-MMS-008: Only active Mess Caretaker opens the registration window."""
    if not actor.has_permission("mms.window.manage"):
        raise PermissionDeniedError("Only active Mess Caretaker can open a registration window.")

    if end_date < start_date:
        raise BadRequestError("Window end date cannot precede start date.")

    # Close any currently open windows
    MessRegistrationWindow.objects.filter(status=sm.WINDOW_OPEN).update(status=sm.WINDOW_CLOSED)

    return MessRegistrationWindow.objects.create(
        academic_year=academic_year,
        semester=semester,
        start_date=start_date,
        end_date=end_date,
        status=sm.WINDOW_OPEN,
        opened_by_user_id=actor.user_id,
    )


@transaction.atomic
def submit_registration_request(
    *,
    actor,
    window_id: int | None = None,
    reason: str = "",
) -> MessRegistration:
    """BR-MMS-009: Students submit registration request only while registration window is open."""
    if not actor.has_permission("mms.registration.self"):
        raise PermissionDeniedError("Only students can submit mess registration requests.")

    # Find the active open registration window
    if window_id:
        try:
            window = MessRegistrationWindow.objects.get(pk=window_id, status=sm.WINDOW_OPEN)
        except MessRegistrationWindow.DoesNotExist:
            raise ConflictError("Specified registration window is not open.") from None
    else:
        window = MessRegistrationWindow.objects.filter(status=sm.WINDOW_OPEN).first()
        if not window:
            raise ConflictError("No mess registration window is currently open.")

    # Prevent duplicate active/submitted registrations
    existing = MessRegistration.objects.filter(
        user_id=actor.user_id,
        status__in=[sm.REG_SUBMITTED, sm.REG_APPROVED],
    ).exists()
    if existing:
        raise ConflictError("Student already has a pending or active mess registration.")

    registration = MessRegistration.objects.create(
        user_id=actor.user_id,
        window=window,
        status=sm.REG_SUBMITTED,
        reason=reason,
    )
    _send_notification(
        recipient_user_id=actor.user_id,
        event_type="registration_submitted",
        title="Registration Request Submitted",
        message="Your mess registration request has been submitted for review.",
    )
    return registration


@transaction.atomic
def review_registration_request(
    *,
    actor,
    request_id: int,
    action: str,
    remarks: str = "",
) -> MessRegistration:
    """BR-MMS-010, BW-MMS-01..02: Caretaker approves or rejects registration request."""
    if not actor.has_permission("mms.registration.review"):
        raise PermissionDeniedError("Only active Mess Caretaker can decide registration requests.")

    reg = MessRegistration.objects.select_for_update().get(pk=request_id)
    if reg.status != sm.REG_SUBMITTED:
        raise ConflictError(f"Cannot review registration in status {reg.status!r}.")

    if action == "approve":
        reg.status = sm.REG_APPROVED
    elif action == "reject":
        reg.status = sm.REG_REJECTED
    else:
        raise BadRequestError(f"Invalid review action {action!r}. Expected 'approve' or 'reject'.")

    reg.reviewed_by_user_id = actor.user_id
    reg.remarks = remarks
    reg.reviewed_at = timezone.now()
    reg.save()

    _send_notification(
        recipient_user_id=reg.user_id,
        event_type=f"registration_{reg.status}",
        title=f"Mess Registration {reg.status.capitalize()}",
        message=f"Your mess registration request has been {reg.status}. Remarks: {remarks}",
    )
    return reg


# --- Deregistration Services (CFR-MMS-005, BR-MMS-010..013, MMS-UC-005..006) ---

@transaction.atomic
def submit_deregistration_request(
    *,
    actor,
    reason: str,
) -> MessDeregistration:
    """BR-MMS-012: Students can submit deregistration requests at any time."""
    if not actor.has_permission("mms.deregistration.self"):
        raise PermissionDeniedError("Only students can submit mess deregistration requests.")

    active_reg = MessRegistration.objects.filter(
        user_id=actor.user_id,
        status=sm.REG_APPROVED,
    ).first()
    if not active_reg:
        raise ConflictError("No approved mess registration found for this student.")

    existing_dereg = MessDeregistration.objects.filter(
        user_id=actor.user_id,
        status=sm.DEREG_SUBMITTED,
    ).exists()
    if existing_dereg:
        raise ConflictError("A deregistration request is already pending.")

    dereg = MessDeregistration.objects.create(
        user_id=actor.user_id,
        registration=active_reg,
        status=sm.DEREG_SUBMITTED,
        reason=reason,
    )
    _send_notification(
        recipient_user_id=actor.user_id,
        event_type="deregistration_submitted",
        title="Deregistration Request Submitted",
        message="Your mess deregistration request has been submitted.",
    )
    return dereg


@transaction.atomic
def review_deregistration_request(
    *,
    actor,
    request_id: int,
    action: str,
    remarks: str = "",
) -> MessDeregistration:
    """BR-MMS-010, BR-MMS-013, BW-MMS-03..04: Caretaker approves or rejects deregistration.

    Approved deregistration takes effect from the next calendar day after decision.
    """
    if not actor.has_permission("mms.deregistration.review"):
        raise PermissionDeniedError("Only active Caretaker can decide deregistration requests.")

    dereg = MessDeregistration.objects.select_for_update().get(pk=request_id)
    if dereg.status != sm.DEREG_SUBMITTED:
        raise ConflictError(f"Cannot review deregistration in status {dereg.status!r}.")

    decision_date = timezone.now().date()
    if action == "approve":
        dereg.status = sm.DEREG_APPROVED
        dereg.effective_date = sm.calculate_deregistration_effective_date(decision_date)
    elif action == "reject":
        dereg.status = sm.DEREG_REJECTED
    else:
        raise BadRequestError(f"Invalid review action {action!r}.")

    dereg.reviewed_by_user_id = actor.user_id
    dereg.remarks = remarks
    dereg.reviewed_at = timezone.now()
    dereg.save()

    _send_notification(
        recipient_user_id=dereg.user_id,
        event_type=f"deregistration_{dereg.status}",
        title=f"Mess Deregistration {dereg.status.capitalize()}",
        message=f"Your deregistration was {dereg.status}. Effective date: {dereg.effective_date}",
    )
    return dereg


@transaction.atomic
def activate_approved_deregistration(*, deregistration_id: int) -> MessDeregistration:
    """MMS-UC-027, BR-MMS-013: Event-triggered activation of approved deregistration on next day."""
    dereg = MessDeregistration.objects.select_for_update().get(pk=deregistration_id)
    if dereg.status != sm.DEREG_APPROVED:
        raise ConflictError("Only approved deregistrations can be activated.")

    dereg.is_active_deregistration = True
    dereg.save()
    if dereg.registration:
        dereg.registration.status = "deregistered"
        dereg.registration.save()
    return dereg


# --- Menu Management Services (CFR-MMS-008, BR-MMS-014, 015, 038, 039, MMS-UC-008..009) ---

@transaction.atomic
def publish_or_update_menu(
    *,
    actor,
    day_of_week: str,
    meal_type: str,
    items: list[str],
) -> MessMenu:
    """BR-MMS-014, BR-MMS-039: Caretaker maintains weekly menu day-wise and meal-wise."""
    if not actor.has_permission("mms.menu.manage"):
        raise PermissionDeniedError("Only active Caretaker can publish or update the mess menu.")

    day_of_week = day_of_week.lower()
    meal_type = meal_type.lower()
    if day_of_week not in sm.DAYS_OF_WEEK:
        raise BadRequestError(f"Invalid day_of_week {day_of_week!r}.")
    if meal_type not in sm.MEAL_TYPES:
        raise BadRequestError(f"Invalid meal_type {meal_type!r}.")

    menu, _ = MessMenu.objects.update_or_create(
        day_of_week=day_of_week,
        meal_type=meal_type,
        defaults={
            "items": items,
            "is_active": True,
            "updated_by_user_id": actor.user_id,
        },
    )
    return menu


# --- Rebate Services (CFR-MMS-011, BR-MMS-021..025, MMS-UC-014..015, BW-MMS-05..07) ---

@transaction.atomic
def submit_rebate_request(
    *,
    actor,
    start_date: date,
    end_date: date,
    reason: str,
    submission_date: date | None = None,
) -> MessRebate:
    """BR-MMS-021..024: Student submits rebate request with minimum 3 days and 1-day lead time."""
    if not actor.has_permission("mms.rebate.self"):
        raise PermissionDeniedError("Only students can submit mess rebate requests.")

    sub_date = submission_date or timezone.now().date()
    # BR-MMS-021: Minimum duration rule (>= 3 days)
    duration = sm.validate_rebate_duration(start_date, end_date)
    # BR-MMS-022: Lead time rule (>= 1 day)
    sm.validate_rebate_lead_time(start_date, sub_date)

    # BR-MMS-023: Non-overlap rule
    overlapping = MessRebate.objects.filter(
        user_id=actor.user_id,
        status__in=[sm.REBATE_SUBMITTED, sm.REBATE_APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlapping:
        raise sm.RuleViolation(
            "BR-MMS-023", "Rebate request dates overlap with an existing rebate."
        )

    rebate = MessRebate.objects.create(
        user_id=actor.user_id,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        reason=reason,
        status=sm.REBATE_SUBMITTED,
        original_start_date=start_date,
        original_end_date=end_date,
    )
    _send_notification(
        recipient_user_id=actor.user_id,
        event_type="rebate_submitted",
        title="Rebate Request Submitted",
        message=f"Rebate request for {duration} day(s) from {start_date} to {end_date} submitted.",
    )
    return rebate


@transaction.atomic
def review_rebate_request(
    *,
    actor,
    rebate_id: int,
    action: str,
    modified_start_date: date | None = None,
    modified_end_date: date | None = None,
    remarks: str = "",
) -> MessRebate:
    """BR-MMS-025, BW-MMS-05..07: Caretaker decides rebate; may modify dates before approval."""
    if not actor.has_permission("mms.rebate.review"):
        raise PermissionDeniedError("Only active Mess Caretaker can decide rebate requests.")

    rebate = MessRebate.objects.select_for_update().get(pk=rebate_id)
    if rebate.status != sm.REBATE_SUBMITTED:
        raise ConflictError(f"Cannot review rebate in status {rebate.status!r}.")

    if action == "approve":
        rebate.status = sm.REBATE_APPROVED
        # BR-MMS-025: Date modification before approval (BW-MMS-06)
        if modified_start_date or modified_end_date:
            m_start = modified_start_date or rebate.start_date
            m_end = modified_end_date or rebate.end_date
            sm.validate_rebate_duration(m_start, m_end)
            rebate.start_date = m_start
            rebate.end_date = m_end
            rebate.duration_days = (m_end - m_start).days + 1
            rebate.modified_by_caretaker = True
    elif action == "reject":
        rebate.status = sm.REBATE_REJECTED
    else:
        raise BadRequestError(f"Invalid review action {action!r}.")

    rebate.reviewed_by_user_id = actor.user_id
    rebate.remarks = remarks
    rebate.reviewed_at = timezone.now()
    rebate.save()

    _send_notification(
        recipient_user_id=rebate.user_id,
        event_type=f"rebate_{rebate.status}",
        title=f"Mess Rebate {rebate.status.capitalize()}",
        message=f"Your rebate request has been {rebate.status}.",
    )
    return rebate


# --- Vacation Continuity Services (CFR-MMS-012, BR-MMS-026, 027, 041, MMS-UC-016..018) ---

@transaction.atomic
def create_vacation_survey(
    *,
    actor,
    title: str,
    vacation_start_date: date,
    vacation_end_date: date,
    response_deadline: datetime,
) -> VacationFoodSurvey:
    """BR-MMS-026: Caretaker creates vacation food continuity survey for registered students."""
    if not actor.has_permission("mms.vacation.manage"):
        raise PermissionDeniedError("Only active Mess Caretaker can create vacation surveys.")

    return VacationFoodSurvey.objects.create(
        title=title,
        vacation_start_date=vacation_start_date,
        vacation_end_date=vacation_end_date,
        response_deadline=response_deadline,
        status=sm.SURVEY_OPEN,
        created_by_user_id=actor.user_id,
    )


@transaction.atomic
def respond_to_vacation_survey(
    *,
    actor,
    survey_id: int,
    requires_food: bool,
) -> VacationFoodResponse:
    """BR-MMS-026, BR-MMS-041, BW-MMS-08..09: Registered student responds Yes or No to survey."""
    if not actor.has_permission("mms.vacation.respond"):
        raise PermissionDeniedError("Only students can respond to vacation food surveys.")

    survey = VacationFoodSurvey.objects.get(pk=survey_id)
    if survey.status != sm.SURVEY_OPEN:
        raise ConflictError("Vacation survey is closed.")

    # BR-MMS-026: Only currently registered students can participate
    is_registered = MessRegistration.objects.filter(
        user_id=actor.user_id,
        status=sm.REG_APPROVED,
    ).exists()
    if not is_registered:
        raise sm.RuleViolation(
            "BR-MMS-026", "Only currently registered students can respond to vacation survey."
        )

    response, _ = VacationFoodResponse.objects.update_or_create(
        survey=survey,
        user_id=actor.user_id,
        defaults={
            "requires_food": requires_food,
            "is_default": False,
            "responded_at": timezone.now(),
        },
    )
    return response


@transaction.atomic
def apply_default_vacation_responses(*, survey_id: int) -> int:
    """MMS-UC-028, BR-MMS-027, BW-MMS-10: Default No applied to non-responding students."""
    survey = VacationFoodSurvey.objects.select_for_update().get(pk=survey_id)
    registered_student_ids = MessRegistration.objects.filter(
        status=sm.REG_APPROVED,
    ).values_list("user_id", flat=True).distinct()

    already_responded_ids = set(
        VacationFoodResponse.objects.filter(survey=survey).values_list("user_id", flat=True)
    )

    created_count = 0
    for uid in registered_student_ids:
        if uid not in already_responded_ids:
            VacationFoodResponse.objects.create(
                survey=survey,
                user_id=uid,
                requires_food=False,
                is_default=True,
                responded_at=timezone.now(),
            )
            created_count += 1
    return created_count


# --- Special Food Services (CFR-MMS-013, BR-MMS-028..031, MMS-UC-019..021, BW-MMS-11..15) ---

@transaction.atomic
def submit_special_food_request(
    *,
    actor,
    requested_date: date,
    meal_type: str,
    food_details: str,
    reason: str,
    cost: Decimal = Decimal("50.00"),
    submission_date: date | None = None,
) -> SpecialFoodRequest:
    """BR-MMS-028: Special food request submitted at least one calendar day in advance."""
    if not actor.has_permission("mms.special_food.self"):
        raise PermissionDeniedError("Only students can submit special food requests.")

    sub_date = submission_date or timezone.now().date()
    sm.validate_special_food_lead_time(requested_date, sub_date)

    req = SpecialFoodRequest.objects.create(
        user_id=actor.user_id,
        requested_date=requested_date,
        meal_type=meal_type,
        food_details=food_details,
        reason=reason,
        cost=cost,
        status=sm.SPECIAL_FOOD_REQUESTED,
    )
    _send_notification(
        recipient_user_id=actor.user_id,
        event_type="special_food_requested",
        title="Special Food Request Submitted",
        message=f"Special food request for {requested_date} ({meal_type}) submitted.",
    )
    return req


@transaction.atomic
def review_special_food_request(
    *,
    actor,
    request_id: int,
    action: str,
    remarks: str = "",
) -> SpecialFoodRequest:
    """BR-MMS-031, BW-MMS-11, 13: Caretaker approves or rejects special food request."""
    if not actor.has_permission("mms.special_food.review"):
        raise PermissionDeniedError("Only active Caretaker can decide special food requests.")

    req = SpecialFoodRequest.objects.select_for_update().get(pk=request_id)
    if req.status != sm.SPECIAL_FOOD_REQUESTED:
        raise ConflictError(f"Cannot decide special food request in status {req.status!r}.")

    if action == "approve":
        req.status = sm.SPECIAL_FOOD_APPROVED
    elif action == "reject":
        req.status = sm.SPECIAL_FOOD_REJECTED
    else:
        raise BadRequestError(f"Invalid review action {action!r}.")

    req.reviewed_by_user_id = actor.user_id
    req.reviewed_at = timezone.now()
    req.remarks = remarks
    req.save()

    _send_notification(
        recipient_user_id=req.user_id,
        event_type=f"special_food_{req.status}",
        title=f"Special Food Request {req.status.capitalize()}",
        message=f"Your special food request has been {req.status}.",
    )
    return req


@transaction.atomic
def update_special_food_fulfillment(
    *,
    actor,
    request_id: int,
    status: str,
) -> SpecialFoodRequest:
    """BR-MMS-031, BW-MMS-14, 15: Transition approved special food to Served or Cancelled."""
    if not actor.has_permission("mms.special_food.fulfill"):
        raise PermissionDeniedError("Only active Caretaker can update fulfillment status.")

    req = SpecialFoodRequest.objects.select_for_update().get(pk=request_id)
    new_status = sm.validate_special_food_transition(req.status, status)
    req.status = new_status
    if new_status == sm.SPECIAL_FOOD_SERVED:
        req.served_at = timezone.now()
    elif new_status == sm.SPECIAL_FOOD_CANCELLED:
        req.cancelled_at = timezone.now()
    req.save()
    return req


@transaction.atomic
def default_reject_special_food_request(*, request_id: int) -> SpecialFoodRequest:
    """MMS-UC-029, BR-MMS-029, BW-MMS-12: Default rejection of undecided special food."""
    req = SpecialFoodRequest.objects.select_for_update().get(pk=request_id)
    if req.status == sm.SPECIAL_FOOD_REQUESTED:
        req.status = sm.SPECIAL_FOOD_REJECTED
        req.is_default_rejected = True
        req.reviewed_at = timezone.now()
        req.save()
        _send_notification(
            recipient_user_id=req.user_id,
            event_type="special_food_default_rejected",
            title="Special Food Request Rejected (Timeout)",
            message="Your special food request was rejected because it timed out without decision.",
        )
    return req


# --- Billing Services (CFR-MMS-009, BR-MMS-016..019, 040, MMS-UC-010, 030, BW-MMS-16) ---

@transaction.atomic
def generate_monthly_bills(
    *,
    billing_month: date,
    base_amount: Decimal = Decimal("3000.00"),
    per_day_rebate_rate: Decimal = Decimal("100.00"),
) -> list[MessBill]:
    """MMS-UC-030, BR-MMS-016, 017: Event-triggered batch generation of monthly mess bills."""
    registered_uids = MessRegistration.objects.filter(
        status=sm.REG_APPROVED,
    ).values_list("user_id", flat=True).distinct()

    bills = []
    first_day = billing_month.replace(day=1)
    # Compute last day of month
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1, day=1)
    last_day = next_month - timedelta(days=1)

    for uid in registered_uids:
        # Sum approved special food in billing month (BR-MMS-030)
        special_requests = SpecialFoodRequest.objects.filter(
            user_id=uid,
            status__in=[sm.SPECIAL_FOOD_APPROVED, sm.SPECIAL_FOOD_SERVED],
            requested_date__gte=first_day,
            requested_date__lte=last_day,
        )
        special_total = sum((r.cost for r in special_requests), Decimal("0.00"))

        # Sum approved rebate days in billing month (BR-MMS-019)
        rebates = MessRebate.objects.filter(
            user_id=uid,
            status=sm.REBATE_APPROVED,
            start_date__lte=last_day,
            end_date__gte=first_day,
        )
        total_rebate_days = sum((r.duration_days for r in rebates), 0)
        rebate_total = Decimal(total_rebate_days) * per_day_rebate_rate

        total = sm.calculate_bill_total(base_amount, special_total, rebate_total)

        bill, _ = MessBill.objects.update_or_create(
            billing_month=first_day,
            user_id=uid,
            defaults={
                "base_amount": base_amount,
                "special_food_amount": special_total,
                "rebate_discount": rebate_total,
                "total_amount": total,
                "status": sm.BILL_GENERATED,
                "generated_at": timezone.now(),
            },
        )
        bills.append(bill)
    return bills


@transaction.atomic
def finalize_and_publish_bill(*, actor, bill_id: int) -> MessBill:
    """BR-MMS-018, MMS-UC-010, BW-MMS-16: Caretaker finalizes and publishes monthly mess bill."""
    if not actor.has_permission("mms.bill.manage"):
        raise PermissionDeniedError("Only active Caretaker can finalize and publish mess bills.")

    bill = MessBill.objects.select_for_update().get(pk=bill_id)
    bill.status = sm.BILL_PUBLISHED
    bill.published_at = timezone.now()
    bill.published_by_user_id = actor.user_id
    bill.save()

    month_str = bill.billing_month.strftime("%B %Y")
    _send_notification(
        recipient_user_id=bill.user_id,
        event_type="bill_published",
        title="Mess Bill Published",
        message=f"Your bill for {month_str} has been published. Amount: {bill.total_amount}",
    )
    return bill


# --- Announcements & Feedback (CFR-MMS-010, BR-MMS-020, 032..033, MMS-UC-012, 022) ---

@transaction.atomic
def publish_announcement(
    *,
    actor,
    title: str,
    content: str,
) -> MessAnnouncement:
    """BR-MMS-032: Mess Caretaker or Mess Warden publishes mess announcements."""
    if not actor.has_permission("mms.announcement.publish"):
        raise PermissionDeniedError("Only Mess Caretaker or Warden can publish announcements.")

    return MessAnnouncement.objects.create(
        title=title,
        content=content,
        published_by_user_id=actor.user_id,
        published_by_role=actor.active_role or "mess_staff",
        is_active=True,
    )


@transaction.atomic
def submit_feedback(
    *,
    actor,
    description: str,
    category: str = "general",
) -> MessFeedback:
    """BR-MMS-020, MMS-UC-012: Students submit text feedback."""
    if not actor.has_permission("mms.feedback.submit"):
        raise PermissionDeniedError("Only students can submit mess feedback.")

    return MessFeedback.objects.create(
        user_id=actor.user_id,
        description=description,
        category=category,
    )


# --- Query & Report Services (MMS-UC-007, 009, 011, 013, 023..025, BR-MMS-011, 020) ---

def view_registration_oversight(*, actor):
    """MMS-UC-007, BR-MMS-011: Mess Warden views operational student requests for oversight."""
    if not actor.has_permission("mms.registration.view_oversight"):
        raise PermissionDeniedError("Only Mess Warden can view operational requests for oversight.")
    return list(MessRegistration.objects.all()), list(MessDeregistration.objects.all())


def view_weekly_menu(*, actor):
    """MMS-UC-009, BR-MMS-038: View weekly mess menu."""
    if not actor.has_permission("mms.menu.view"):
        raise PermissionDeniedError("Menu view permission required.")
    return list(MessMenu.objects.filter(is_active=True))


def view_announcements(*, actor):
    """MMS-UC-023, BR-MMS-033: View mess announcements history."""
    if not actor.has_permission("mms.announcement.view"):
        raise PermissionDeniedError("Announcement view permission required.")
    return list(MessAnnouncement.objects.filter(is_active=True))


def view_feedback_entries(*, actor):
    """MMS-UC-013, BR-MMS-020: Caretaker and Warden review student feedback."""
    if not actor.has_permission("mms.feedback.view"):
        raise PermissionDeniedError("Feedback view permission required.")
    return list(MessFeedback.objects.all())


def view_monthly_bills(*, actor):
    """MMS-UC-011, BR-MMS-040: Student views personal bills and outstanding balances."""
    can_self = actor.has_permission("mms.bill.view_self")
    can_manage = actor.has_permission("mms.bill.manage")
    if not can_self and not can_manage:
        raise PermissionDeniedError("Bill view permission required.")
    if can_manage:
        return list(MessBill.objects.all())
    return list(MessBill.objects.filter(user_id=actor.user_id))


def generate_operational_reports(*, actor, report_type: str = "registration_trends"):
    """MMS-UC-025, BR-MMS-034: Caretaker generates operational reports."""
    if not actor.has_permission("mms.report.operational"):
        raise PermissionDeniedError("Only Mess Caretaker can generate operational reports.")
    return {"report_type": report_type, "status": "generated", "generated_by": actor.user_id}


def generate_supervisory_reports(*, actor, report_type: str = "registered_students"):
    """MMS-UC-024, BR-MMS-034: Warden views and searches supervisory reports."""
    if not actor.has_permission("mms.report.supervisory"):
        raise PermissionDeniedError("Only Mess Warden can view supervisory reports.")
    return {"report_type": report_type, "status": "generated", "generated_by": actor.user_id}
