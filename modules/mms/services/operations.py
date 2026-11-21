"""Transactional MMS workflows. Views validate transport; services own rules."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory.models import UserRef
from modules.mms.domain.rules import (
    calculate_bill,
    next_local_midnight,
    validate_rebate,
    validate_special_food,
)
from modules.mms.models import (
    Announcement,
    BillingInput,
    Enrollment,
    Feedback,
    MenuEntry,
    MenuWeek,
    MonthlyBill,
    RebateHistory,
    RebateRequest,
    RegistrationWindow,
    RequestHistory,
    RoleAssignment,
    SpecialFoodHistory,
    SpecialFoodRequest,
    StudentRequest,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.services import notifications, roles

log = logging.getLogger("fusion.mms.operations")


def _record_request(request, status, actor_id=None, note=""):
    RequestHistory.objects.create(request=request, status=status,
                                  actor_user_id=actor_id, note=note)


@transaction.atomic
def open_registration_window(*, actor, cycle: str, opens_at, closes_at):
    roles.require_role(actor, "caretaker")
    if not isinstance(cycle, str) or not cycle.strip() or closes_at <= opens_at:
        raise ConflictError("Cycle and a valid open/close period are required.",
                            code="invalid_registration_window")
    try:
        with transaction.atomic():
            return RegistrationWindow.objects.create(
                cycle=cycle.strip(), opens_at=opens_at, closes_at=closes_at,
                opened_by_user_id=actor.user_id)
    except IntegrityError as exc:
        raise ConflictError("A registration window already exists for this cycle.",
                            code="registration_window_exists") from exc


@transaction.atomic
def request_registration(*, actor, window_id: int):
    now = timezone.now()
    window = RegistrationWindow.objects.select_for_update().filter(
        pk=window_id, opens_at__lte=now, closes_at__gt=now).first()
    if window is None:
        raise ConflictError("Registration is available only during an open window.",
                            code="registration_window_closed")
    if Enrollment.objects.filter(user_id=actor.user_id, deregistered_at__isnull=True).exists():
        raise ConflictError("You are already registered for mess service.",
                            code="already_registered")
    if StudentRequest.objects.filter(
            user_id=actor.user_id, kind="registration", window=window).exists():
        raise ConflictError("A registration request already exists for this cycle.",
                            code="registration_request_exists")
    try:
        with transaction.atomic():
            request = StudentRequest.objects.create(
                user_id=actor.user_id, kind="registration", window=window)
    except IntegrityError as exc:
        raise ConflictError("A registration request already exists for this cycle.",
                            code="registration_request_exists") from exc
    _record_request(request, request.status, actor.user_id)
    notifications.notify_user(
        topic="request.submitted", key=f"request.submit:{request.pk}",
        user_id=actor.user_id, subject="Mess registration request submitted",
        body=f"Your registration request for {window.cycle} is pending review.")
    return request


@transaction.atomic
def request_deregistration(*, actor):
    enrollment = Enrollment.objects.select_for_update().filter(
        user_id=actor.user_id, deregistered_at__isnull=True).first()
    if enrollment is None:
        raise ConflictError("You are not currently registered for mess service.",
                            code="not_registered")
    try:
        with transaction.atomic():
            request = StudentRequest.objects.create(
                user_id=actor.user_id, kind="deregistration")
    except IntegrityError as exc:
        raise ConflictError("A deregistration request is already pending.",
                            code="deregistration_request_exists") from exc
    _record_request(request, request.status, actor.user_id)
    notifications.notify_user(
        topic="request.submitted", key=f"request.submit:{request.pk}",
        user_id=actor.user_id, subject="Mess deregistration request submitted",
        body="Your deregistration request is pending review.")
    return request


@transaction.atomic
def decide_student_request(*, actor, request_id: int, approve: bool):
    roles.require_role(actor, "caretaker")
    request = StudentRequest.objects.select_for_update().filter(pk=request_id).first()
    if request is None:
        raise NotFoundError("No such student request.")
    if request.status != "pending":
        raise ConflictError("This request has already been decided.",
                            code="request_not_pending")
    if request.kind not in {"registration", "deregistration"}:
        raise ConflictError("This request has an unsupported type.",
                            code="invalid_request_kind")
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    if not approve:
        request.status = "rejected"
    elif request.kind == "deregistration":
        request.status = "approved_awaiting_effect"
        request.effective_at = next_local_midnight(
            request.decided_at, timezone.get_current_timezone())
    else:
        request.status = "approved"
        Enrollment.objects.update_or_create(
            user_id=request.user_id,
            defaults={"registered_at": request.decided_at,
                      "deregistered_at": None})
    request.save()
    _record_request(request, request.status, actor.user_id)
    notifications.notify_user(
        topic="request.decided", key=f"request.decide:{request.pk}",
        user_id=request.user_id, subject="Mess request decision",
        body=f"Your {request.kind} request was {request.status.replace('_', ' ')}.")
    return request


@transaction.atomic
def activate_deregistrations(*, now=None) -> int:
    now = now or timezone.now()
    due = list(StudentRequest.objects.select_for_update().filter(
        kind="deregistration", status="approved_awaiting_effect",
        effective_at__lte=now))
    for request in due:
        Enrollment.objects.filter(user_id=request.user_id,
                                  deregistered_at__isnull=True).update(
            deregistered_at=request.effective_at)
        request.status = "effective"
        request.save(update_fields=["status", "updated_at"])
        _record_request(request, request.status)
    return len(due)


@transaction.atomic
def publish_menu(*, actor, week_start, entries):
    roles.require_role(actor, "caretaker")
    if not isinstance(entries, list) or len(entries) != 21:
        raise ConflictError("Provide one entry for each of 7 days and 3 meals.",
                            code="menu_incomplete")
    expected = {(day, meal) for day in range(7)
                for meal in ("breakfast", "lunch", "dinner")}
    if any(not isinstance(item, dict)
           or set(item) != {"day", "meal", "item"}
           or type(item["day"]) is not int
           or not isinstance(item["meal"], str)
           or not isinstance(item["item"], str)
           or not item["item"].strip()
           or len(item["item"]) > 200
           for item in entries):
        raise ConflictError("Every menu entry needs a valid day, meal and item.",
                            code="menu_structure_invalid")
    actual = {(item["day"], item["meal"]) for item in entries}
    if actual != expected:
        raise ConflictError("Menu must include a valid entry for every meal each day.",
                            code="menu_structure_invalid")
    week, _ = MenuWeek.objects.update_or_create(
        week_start=week_start,
        defaults={"updated_by_user_id": actor.user_id,
                  "published_at": timezone.now()})
    week.entries.all().delete()
    MenuEntry.objects.bulk_create([
        MenuEntry(week=week, day=item["day"], meal=item["meal"], item=item["item"])
        for item in entries])
    student_ids = list(UserRef.objects.filter(
        kind="student", is_active=True).values_list("user_id", flat=True))
    notifications.notify_students(
        topic="menu.updated", key=f"menu.updated:{week.pk}:{week.updated_at.isoformat()}",
        user_ids=student_ids, subject="Weekly mess menu updated",
        body=f"The weekly menu for {week_start} has been updated.")
    return week


@transaction.atomic
def submit_rebate(*, actor, reason, explanation, starts_on, ends_on):
    if not isinstance(reason, str) or not isinstance(explanation, str):
        raise ConflictError("A valid rebate reason and explanation are required.",
                            code="invalid_rebate")
    if not Enrollment.objects.select_for_update().filter(
            user_id=actor.user_id, deregistered_at__isnull=True).exists():
        raise ConflictError("Only a currently registered student may request a rebate.",
                            code="not_registered")
    today = timezone.localdate()
    try:
        validate_rebate(reason=reason, explanation=explanation,
                        starts_on=starts_on, ends_on=ends_on, today=today)
    except ValidationError as exc:
        raise ConflictError(str(exc.message_dict if hasattr(exc, "message_dict")
                                else exc.messages), code="invalid_rebate") from exc
    overlaps = RebateRequest.objects.filter(
        user_id=actor.user_id, status__in=["pending", "approved"],
        starts_on__lte=ends_on, ends_on__gte=starts_on).exists()
    if overlaps:
        raise ConflictError("Rebate dates overlap another pending or approved request.",
                            code="rebate_overlap")
    request = RebateRequest.objects.create(
        user_id=actor.user_id, reason=reason, explanation=explanation.strip(),
        starts_on=starts_on, ends_on=ends_on)
    RebateHistory.objects.create(request=request, status=request.status,
                                 actor_user_id=actor.user_id)
    notifications.notify_user(
        topic="rebate.submitted", key=f"rebate.submit:{request.pk}",
        user_id=actor.user_id, subject="Mess rebate request submitted",
        body="Your rebate request is pending review.")
    return request


@transaction.atomic
def decide_rebate(*, actor, request_id, approve, starts_on=None, ends_on=None):
    roles.require_role(actor, "caretaker")
    request = RebateRequest.objects.select_for_update().filter(pk=request_id).first()
    if request is None:
        raise NotFoundError("No such rebate request.")
    if request.status != "pending":
        raise ConflictError("This rebate request has already been decided.",
                            code="request_not_pending")
    if approve and starts_on and ends_on:
        # TODO: ISS-MMS external rebate policy must define permitted date edits.
        # Date modification is permitted only where an external policy permits
        # it; until that policy is represented, do not accept modified dates.
        raise ConflictError("Date modification requires an explicit institutional policy.",
                            code="rebate_date_policy_unconfigured")
    request.status = "approved" if approve else "rejected"
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    request.save()
    RebateHistory.objects.create(request=request, status=request.status,
                                 actor_user_id=actor.user_id)
    notifications.notify_user(
        topic="rebate.decided", key=f"rebate.decide:{request.pk}",
        user_id=request.user_id, subject="Mess rebate request decision",
        body=f"Your rebate request was {request.status}.")
    return request


@transaction.atomic
def create_vacation_survey(*, actor, title, starts_on, ends_on, deadline):
    roles.require_role(actor, "caretaker")
    if (not isinstance(title, str) or not title.strip()
            or starts_on <= timezone.localdate()
            or ends_on < starts_on or deadline <= timezone.now()):
        raise ConflictError("Survey needs a title, valid vacation dates, and a future deadline.",
                            code="invalid_survey")
    survey = VacationSurvey.objects.create(
        title=title.strip(), vacation_starts_on=starts_on, vacation_ends_on=ends_on,
        deadline=deadline, created_by_user_id=actor.user_id)
    student_ids = list(Enrollment.objects.filter(
        deregistered_at__isnull=True).values_list("user_id", flat=True))
    notifications.notify_students(
        topic="vacation.created", key=f"vacation.created:{survey.pk}",
        user_ids=student_ids, subject="Vacation food continuity survey",
        body=f"Please respond to {survey.title} by {deadline}.")
    return survey


@transaction.atomic
def respond_vacation(*, actor, survey_id, response):
    survey = VacationSurvey.objects.select_for_update().filter(
        pk=survey_id, deadline__gt=timezone.now()).first()
    if survey is None:
        raise ConflictError("The vacation survey is closed or unavailable.",
                            code="survey_closed")
    if response not in {"yes", "no"}:
        raise ConflictError("Response must be Yes or No.", code="invalid_response")
    if not Enrollment.objects.filter(user_id=actor.user_id,
                                     deregistered_at__isnull=True).exists():
        raise ConflictError("Vacation surveys are available to registered students only.",
                            code="not_registered")
    row, _ = VacationResponse.objects.update_or_create(
        survey=survey, user_id=actor.user_id,
        defaults={"response": response, "is_default": False,
                  "responded_at": timezone.now()})
    return row


@transaction.atomic
def default_vacation_responses(*, now=None):
    now = now or timezone.now()
    count = 0
    surveys = VacationSurvey.objects.select_for_update().filter(deadline__lte=now)
    for survey in surveys:
        enrolled = Enrollment.objects.filter(deregistered_at__isnull=True)
        existing = VacationResponse.objects.filter(survey=survey).values_list(
            "user_id", flat=True)
        missing = [VacationResponse(
            survey=survey, user_id=uid, response="no", is_default=True)
            for uid in enrolled.exclude(user_id__in=existing).values_list("user_id", flat=True)]
        VacationResponse.objects.bulk_create(missing, ignore_conflicts=True)
        count += len(missing)
    return count


@transaction.atomic
def create_special_food(*, actor, reason, details, requested_for):
    try:
        validate_special_food(requested_for=requested_for, today=timezone.localdate())
    except ValidationError as exc:
        raise ConflictError(str(exc.message_dict if hasattr(exc, "message_dict")
                                else exc.messages), code="invalid_special_food") from exc
    if not isinstance(reason, str) or reason not in {"illness", "personal_event"}:
        raise ConflictError("Reason must be illness or personal event.",
                            code="invalid_special_food_reason")
    if not isinstance(details, str):
        raise ConflictError("Details must be text.", code="invalid_special_food_details")
    request = SpecialFoodRequest.objects.create(
        user_id=actor.user_id, reason=reason, details=details.strip(),
        requested_for=requested_for)
    SpecialFoodHistory.objects.create(request=request, status=request.status,
                                      actor_user_id=actor.user_id)
    notifications.notify_user(
        topic="special_food.submitted", key=f"special.submitted:{request.pk}",
        user_id=actor.user_id, subject="Special food request submitted",
        body="Your request is awaiting Mess Caretaker review.")
    return request


@transaction.atomic
def decide_special_food(*, actor, request_id, approve, charge_amount=None):
    roles.require_role(actor, "caretaker")
    request = SpecialFoodRequest.objects.select_for_update().filter(
        pk=request_id).first()
    if request is None:
        raise NotFoundError("No such special food request.")
    if request.status != "requested":
        raise ConflictError("This request is no longer awaiting a decision.",
                            code="request_not_pending")
    now = timezone.now()
    decision_hours = settings.MMS_SPECIAL_FOOD_DECISION_HOURS
    if decision_hours is not None and decision_hours <= 0:
        raise RuntimeError(
            "MMS_SPECIAL_FOOD_DECISION_HOURS must be a positive institution-provided value.")
    if decision_hours is not None:
        deadline = request.created_at + timedelta(hours=decision_hours)
        if now >= deadline:
            raise ConflictError(
                "The institution-defined decision period has expired; this request "
                "will be rejected by deadline processing.",
                code="special_food_decision_period_expired")
    if approve and charge_amount is None:
        raise ConflictError("A policy-provided charge is required for approval.",
                            code="special_food_charge_required")
    if approve and (
        not charge_amount.is_finite()
        or charge_amount < 0
        or charge_amount > Decimal("9999999.99")
    ):
        raise ConflictError("Charge must be a finite non-negative policy value.",
                            code="invalid_special_food_charge")
    request.status = "approved" if approve else "rejected"
    request.decided_at = now
    request.decided_by_user_id = actor.user_id
    if approve:
        request.charge_amount = charge_amount
    request.save()
    SpecialFoodHistory.objects.create(request=request, status=request.status,
                                      actor_user_id=actor.user_id)
    notifications.notify_user(
        topic="special_food.decided", key=f"special.decide:{request.pk}",
        user_id=request.user_id, subject="Special food request decision",
        body=f"Your special food request was {request.status}.")
    return request


def _reject_special_food_request(request, *, now):
    request.status = "rejected"
    request.decided_at = now
    request.decided_by_user_id = None
    request.save(update_fields=["status", "decided_at", "decided_by_user_id",
                                "updated_at"])
    SpecialFoodHistory.objects.create(request=request, status="rejected",
                                      actor_user_id=None)
    notifications.notify_user(
        topic="special_food.decided", key=f"special.timeout:{request.pk}",
        user_id=request.user_id, subject="Special food request rejected",
        body=("Your request was automatically rejected because no decision "
              "was recorded in time."))


@transaction.atomic
def update_special_fulfillment(*, actor, request_id, status):
    # TODO: ISS-MMS-014 retains the synchronized UC's Caretaker actor because
    # the frozen Problem Statement does not name who records fulfillment.
    roles.require_role(actor, "caretaker")
    request = SpecialFoodRequest.objects.select_for_update().filter(
        pk=request_id).first()
    if request is None:
        raise NotFoundError("No such special food request.")
    if request.status != "approved" or status not in {"served", "cancelled"}:
        raise ConflictError("Only an approved request can become Served or Cancelled.",
                            code="invalid_fulfillment_transition")
    request.status = status
    request.save(update_fields=["status", "updated_at"])
    SpecialFoodHistory.objects.create(request=request, status=status,
                                      actor_user_id=actor.user_id)
    notifications.notify_user(
        topic="special_food.fulfillment",
        key=f"special.fulfillment:{request.pk}:{status}",
        user_id=request.user_id, subject="Special food fulfillment update",
        body=f"Your special food request is now {status}.")
    return request


@transaction.atomic
def reject_expired_special_food(*, now=None, decision_hours=None):
    if decision_hours is None or decision_hours <= 0:
        raise RuntimeError("MMS_SPECIAL_FOOD_DECISION_HOURS must be configured by the institution.")
    now = now or timezone.now()
    deadline = now - timedelta(hours=decision_hours)
    rows = list(SpecialFoodRequest.objects.select_for_update().filter(
        status="requested", created_at__lte=deadline))
    for request in rows:
        _reject_special_food_request(request, now=now)
    return len(rows)


@transaction.atomic
def publish_announcement(*, actor, title, body):
    is_caretaker = roles.is_active_role(actor.user_id, "caretaker")
    is_warden = roles.is_active_role(actor.user_id, "warden")
    if not (is_caretaker or is_warden):
        from core.api.exceptions import PermissionDeniedError
        raise PermissionDeniedError(
            "Only the active Caretaker or Warden may publish announcements.",
            code="active_role_required")
    if (not isinstance(title, str) or not isinstance(body, str)
            or not title.strip() or not body.strip()):
        raise ConflictError("Announcement title and body are required.",
                            code="announcement_content_required")
    row = Announcement.objects.create(
        title=title.strip(), body=body.strip(), published_by_user_id=actor.user_id,
        published_by_role="caretaker" if is_caretaker else "warden",
        published_at=timezone.now())
    student_ids = list(UserRef.objects.filter(
        kind="student", is_active=True).values_list("user_id", flat=True))
    notifications.notify_students(
        topic="announcement.published", key=f"announcement:{row.pk}",
        user_ids=student_ids, subject=row.title, body=row.body[:500])
    return row


@transaction.atomic
def _enrollment_ids_for_month(year, month):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    month_start = timezone.make_aware(datetime.combine(start, time.min))
    month_end = timezone.make_aware(datetime.combine(end, time.min))
    return set(Enrollment.objects.filter(
        registered_at__lt=month_end).filter(
            Q(deregistered_at__isnull=True) | Q(deregistered_at__gt=month_start)
        ).values_list("user_id", flat=True))


def _normalize_billing_inputs(inputs):
    if not isinstance(inputs, list) or not inputs:
        raise ConflictError("Billing inputs are required.", code="invalid_bill_inputs")
    normalized = []
    for item in inputs:
        if not isinstance(item, dict):
            raise ConflictError(
                "Each billing input needs a valid user, rate and served-day count.",
                code="invalid_bill_input")
        user_id = item.get("user_id")
        served_days = item.get("served_days")
        if (isinstance(user_id, bool) or isinstance(served_days, bool)
                or (isinstance(user_id, float) and not user_id.is_integer())
                or (isinstance(served_days, float) and not served_days.is_integer())):
            raise ConflictError(
                "Each billing input needs a valid user, rate and served-day count.",
                code="invalid_bill_input")
        try:
            row = {
                "user_id": int(user_id),
                "daily_rate": Decimal(str(item["daily_rate"])),
                "served_days": int(served_days),
            }
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise ConflictError(
                "Each billing input needs a valid user, rate and served-day count.",
                code="invalid_bill_input") from exc
        rate = row["daily_rate"]
        if not rate.is_finite() or rate < 0 or rate > Decimal("9999999.99"):
            raise ConflictError("Daily rate must be a non-negative amount with two decimals.",
                                code="invalid_bill_input")
        try:
            has_cent_precision = rate.quantize(Decimal("0.01")) == rate
        except ArithmeticError:
            has_cent_precision = False
        if not has_cent_precision:
            raise ConflictError("Daily rate must be a non-negative amount with two decimals.",
                                code="invalid_bill_input")
        normalized.append(row)
    return normalized


@transaction.atomic
def save_billing_inputs(*, actor, year, month, inputs):
    roles.require_role(actor, "caretaker")
    if not 1 <= year <= 9998 or not 1 <= month <= 12:
        raise ConflictError("A valid year and month are required.",
                            code="invalid_billing_period")
    normalized = _normalize_billing_inputs(inputs)
    expected_users = _enrollment_ids_for_month(year, month)
    ids = [row["user_id"] for row in normalized]
    if len(set(ids)) != len(ids) or set(ids) != expected_users:
        raise ConflictError(
            "Provide exactly one input for every student registered during the month.",
            code="incomplete_bill_inputs")
    days_in_month = (date(year + (month == 12), month % 12 + 1, 1)
                     - date(year, month, 1)).days
    for row in normalized:
        if row["daily_rate"] < 0 or not 0 <= row["served_days"] <= days_in_month:
            raise ConflictError("Rate or served-day count is invalid.",
                                code="invalid_bill_input")
        existing = MonthlyBill.objects.filter(
            user_id=row["user_id"], year=year, month=month).first()
        if existing and existing.status != "generated":
            raise ConflictError("Inputs for finalized or published bills are locked.",
                                code="bill_locked")
    BillingInput.objects.filter(year=year, month=month).delete()
    BillingInput.objects.bulk_create([
        BillingInput(**row, year=year, month=month,
                     recorded_by_user_id=actor.user_id)
        for row in normalized
    ])
    return len(normalized)


@transaction.atomic
def generate_bills(*, actor=None, system_event=False, year, month, inputs):
    if actor is not None:
        roles.require_role(actor, "caretaker")
    elif not system_event:
        raise ConflictError("Monthly generation must be triggered by an MMS event.",
                            code="billing_event_required")
    if not 1 <= month <= 12:
        raise ConflictError("Month must be between 1 and 12.", code="invalid_month")
    if not 1 <= year <= 9998:
        raise ConflictError("Year must be between 1 and 9998.",
                            code="invalid_billing_period")
    normalized = _normalize_billing_inputs(inputs)
    user_ids = [item["user_id"] for item in normalized]
    if len(set(user_ids)) != len(user_ids):
        raise ConflictError("A student may appear only once in the billing inputs.",
                            code="duplicate_bill_input")
    start, end = date(year, month, 1), (
        date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1))
    enrollment_ids = _enrollment_ids_for_month(year, month)
    if set(user_ids) != enrollment_ids:
        raise ConflictError(
            "Provide served-day and rate inputs for every student registered during the month.",
            code="incomplete_bill_inputs")
    output = []
    for item in normalized:
        user_id = item["user_id"]
        rate = item["daily_rate"]
        served_days = item["served_days"]
        if rate < 0 or not 0 <= served_days <= (end - start).days:
            raise ConflictError("Rate or served-day count is invalid.",
                                code="invalid_bill_input")
        rebate_days = 0
        for rebate in RebateRequest.objects.filter(
            user_id=user_id, status="approved",
            starts_on__lt=end, ends_on__gte=start):
            rebate_days += (min(rebate.ends_on, end - timedelta(days=1))
                            - max(rebate.starts_on, start)).days + 1
        rebate_deduction = rate * rebate_days
        if SpecialFoodRequest.objects.filter(
                user_id=user_id, status="cancelled",
                requested_for__gte=start, requested_for__lt=end).exists():
            log.warning(
                "mms.billing.student_blocked_cancelled_food user=%s year=%s month=%s",
                user_id, year, month)
            existing_bill = MonthlyBill.objects.select_for_update().filter(
                user_id=user_id, year=year, month=month).first()
            if existing_bill:
                output.append(existing_bill)
            continue
        foods = list(SpecialFoodRequest.objects.filter(
            user_id=user_id, status__in=["approved", "served"],
            requested_for__gte=start, requested_for__lt=end))
        if any(food.charge_amount is None for food in foods):
            log.warning(
                "mms.billing.student_blocked_missing_food_charge user=%s year=%s month=%s",
                user_id, year, month)
            existing_bill = MonthlyBill.objects.select_for_update().filter(
                user_id=user_id, year=year, month=month).first()
            if existing_bill:
                output.append(existing_bill)
            continue
        special_charges = sum((food.charge_amount for food in foods),
                              Decimal("0.00"))
        total = calculate_bill(daily_rate=rate, served_days=served_days,
                               special_food_charges=special_charges,
                               rebate_deduction=rebate_deduction)
        bill = MonthlyBill.objects.select_for_update().filter(
            user_id=user_id, year=year, month=month).first()
        if bill and bill.status != "generated":
            output.append(bill)
            continue
        values = {
            "daily_rate": rate, "served_days": served_days,
            "special_food_charges": special_charges,
            "rebate_deduction": rebate_deduction, "total": total,
        }
        if bill:
            for name, value in values.items():
                setattr(bill, name, value)
            bill.save()
        else:
            bill = MonthlyBill.objects.create(
                user_id=user_id, year=year, month=month, **values)
        output.append(bill)
    return output


def generate_ready_bills(*, today=None) -> int:
    """Run completed calendar months once all external billing facts exist."""
    today = today or timezone.localdate()
    periods = BillingInput.objects.values_list("year", "month").distinct()
    generated = 0
    for year, month in periods:
        if (year, month) >= (today.year, today.month):
            continue
        expected = _enrollment_ids_for_month(year, month)
        rows = list(BillingInput.objects.filter(year=year, month=month))
        if not rows and not expected:
            continue
        if {row.user_id for row in rows} != expected:
            log.warning("mms.billing.inputs_incomplete year=%s month=%s expected=%d supplied=%d",
                        year, month, len(expected), len(rows))
            continue
        existing_ids = set(MonthlyBill.objects.filter(
            year=year, month=month).values_list("user_id", flat=True))
        bills = generate_bills(
            system_event=True, year=year, month=month,
            inputs=[{"user_id": row.user_id, "daily_rate": row.daily_rate,
                     "served_days": row.served_days} for row in rows])
        generated += sum(bill.user_id not in existing_ids for bill in bills)
    return generated


@transaction.atomic
def expire_role_assignments(*, now=None) -> int:
    now = now or timezone.now()
    return RoleAssignment.objects.filter(
        is_current=True, ends_at__lte=now).update(
            is_current=False, updated_at=now)


@transaction.atomic
def finalize_bill(*, actor, bill_id):
    roles.require_role(actor, "caretaker")
    bill = MonthlyBill.objects.select_for_update().filter(pk=bill_id).first()
    if bill is None:
        raise NotFoundError("No such bill.")
    if bill.status != "generated":
        raise ConflictError("Only generated bills can be finalized.",
                            code="bill_not_generated")
    _ensure_bill_has_no_cancelled_food_request(bill)
    bill.status = "finalized"
    bill.finalized_by_user_id = actor.user_id
    bill.finalized_at = timezone.now()
    bill.save()
    return bill


def _ensure_bill_has_no_cancelled_food_request(bill):
    start = date(bill.year, bill.month, 1)
    end = date(bill.year + 1, 1, 1) if bill.month == 12 else date(
        bill.year, bill.month + 1, 1)
    if SpecialFoodRequest.objects.filter(
            user_id=bill.user_id, status="cancelled",
            requested_for__gte=start, requested_for__lt=end).exists():
        raise ConflictError(
            "Billing treatment for a cancelled special-food request needs "
            "institutional clarification.",
            code="special_food_cancellation_policy_unresolved")


@transaction.atomic
def publish_bill(*, actor, bill_id):
    roles.require_role(actor, "caretaker")
    bill = MonthlyBill.objects.select_for_update().filter(pk=bill_id).first()
    if bill is None:
        raise NotFoundError("No such bill.")
    if bill.status != "finalized":
        raise ConflictError("A bill must be finalized before publication.",
                            code="bill_not_finalized")
    _ensure_bill_has_no_cancelled_food_request(bill)
    bill.status = "published"
    bill.published_at = timezone.now()
    bill.save()
    notifications.notify_user(
        topic="bill.published", key=f"bill.published:{bill.pk}",
        user_id=bill.user_id, subject="Monthly mess bill published",
        body=f"Your mess bill for {bill.month:02}/{bill.year} is {bill.total}.")
    return bill


def send_vacation_reminder(*, actor, survey_id):
    roles.require_role(actor, "caretaker")
    survey = VacationSurvey.objects.filter(pk=survey_id, deadline__gt=timezone.now()).first()
    if survey is None:
        raise NotFoundError("No open vacation survey with that id.")
    responded = VacationResponse.objects.filter(
        survey=survey).values_list("user_id", flat=True)
    ids = list(Enrollment.objects.filter(
        deregistered_at__isnull=True).exclude(user_id__in=responded)
        .values_list("user_id", flat=True))
    return notifications.notify_students(
        topic="vacation.reminder",
        key=f"vacation.reminder:{survey.pk}:{timezone.now().isoformat()}",
        user_ids=ids, subject="Vacation food continuity reminder",
        body=f"Please respond to {survey.title} by {survey.deadline}.")


def submit_feedback(*, actor, message):
    if not isinstance(message, str) or not message.strip():
        raise ConflictError("Feedback text is required.", code="feedback_required")
    return Feedback.objects.create(user_id=actor.user_id, message=message.strip())


def balance_for(user_id: int):
    return MonthlyBill.objects.filter(user_id=user_id, status="published").aggregate(
        balance=Sum("total"))["balance"] or Decimal("0.00")
