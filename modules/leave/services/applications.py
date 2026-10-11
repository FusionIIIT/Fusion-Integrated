from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from fusion_auth.client import IamUnavailable
from modules.leave import contracts
from modules.leave.domain.counting import count_days
from modules.leave.domain.workflow import (
    APPROVED,
    CANCELLATION,
    CL,
    COL,
    EL,
    EXTENDED,
    EXTENSION,
    LEAVE_TYPES,
    NEW,
    PENDING_STATES,
    RH,
    VL,
    InvalidTransition,
    is_higher_sanction,
    resolve,
)
from modules.leave.models import (
    AuthorityRoute,
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveDecision,
    LeavePolicy,
    ResumptionRecord,
    SubstituteResponse,
)
from modules.leave.services import accounts, notifications
from modules.leave.services.errors import DependencyUnavailable


def _profile(user_id: int):
    try:
        person = contracts.get_employees([user_id]).get(user_id)
    except IamUnavailable as exc:
        raise DependencyUnavailable("IAM employee directory is unavailable.") from exc
    if person is None:
        raise ValidationError("The applicant or substitute is not an active employee.")
    return person


def _policy(leave_type: str) -> LeavePolicy:
    try:
        return accounts.policy_for(leave_type)
    except ObjectDoesNotExist as exc:
        raise ValidationError(f"No current policy is configured for {leave_type}.") from exc


def _current_holidays(start: date, end: date) -> set[date]:
    calendar = HolidayCalendar.objects.filter(is_published=True, is_current=True).first()
    if calendar is None:
        return set()
    return set(HolidayDate.objects.filter(
        calendar=calendar, date__range=(start, end)).values_list("date", flat=True))


def _route(person, leave_type: str, principal) -> dict:
    if principal.active_role == "Director":
        return {"unit_head_user_id": None, "establishment_required": False,
                "establishment_user_id": None, "final_authority_user_id": principal.user_id}
    if not person.organizational_unit:
        raise ValidationError("The employee's organizational unit is unavailable.")
    try:
        route = AuthorityRoute.objects.get(
            unit_key=person.organizational_unit, leave_type=leave_type)
    except AuthorityRoute.DoesNotExist as exc:
        raise ValidationError(
            f"No authority route is configured for {person.organizational_unit} and {leave_type}.") from exc
    if is_higher_sanction(leave_type) and route.final_authority_user_id is None:
        raise ValidationError("The authority route has no final sanctioning authority.")
    if route.establishment_required and route.establishment_user_id is None:
        raise ValidationError("The configured Establishment step has no assignee.")
    return {
        "unit_head_user_id": route.unit_head_user_id,
        "establishment_required": route.establishment_required,
        "establishment_user_id": route.establishment_user_id,
        "final_authority_user_id": route.final_authority_user_id,
    }


def _validate_substitute(*, applicant_id: int, substitute_id: int | None,
                         start: date, end: date) -> None:
    if substitute_id is None:
        raise ValidationError("A substitute is required by the current policy.")
    if substitute_id == applicant_id:
        raise ValidationError("The applicant cannot be their own substitute.")
    _profile(substitute_id)
    overlaps = LeaveApplication.objects.filter(
        applicant_user_id=substitute_id, start_date__lte=end, end_date__gte=start,
        status__in=(*PENDING_STATES, APPROVED),
    ).exists()
    if overlaps:
        raise ValidationError("The nominated substitute has overlapping leave.")


def _validate_dates(leave_type: str, start: date, end: date, half_day: str,
                    policy: LeavePolicy) -> Decimal:
    if start > end:
        raise ValidationError("The end date must not precede the start date.")
    if half_day and (leave_type != CL or start != end or half_day not in {"first", "second"}):
        raise ValidationError("Half-day selection is valid only for one-day CL.")
    holidays = _current_holidays(start, end)
    if leave_type == RH:
        if start != end:
            raise ValidationError("An RH request must select one restricted holiday.")
        applicable = HolidayDate.objects.filter(
            calendar__is_published=True, calendar__is_current=True,
            date=start, is_restricted_holiday=True).exists()
        if not applicable:
            raise ValidationError("The selected date is not an applicable published RH.")
    if leave_type == VL:
        try:
            periods = contracts.academic_vacation_periods(start, end)
        except contracts.ExternalDependencyUnavailable as exc:
            raise DependencyUnavailable(
                "Vacation periods require a configured Academic Calendar provider.") from exc
        if not any(period_start <= start and period_end >= end
                   for period_start, period_end in periods):
            raise ValidationError("The requested VL period is outside an applicable vacation.")
    return count_days(leave_type, start, end, frozenset(holidays), bool(half_day))


def _check_overlap(user_id: int, leave_type: str, start: date, end: date,
                   half_day: str = "") -> None:
    rows = LeaveApplication.objects.filter(
        applicant_user_id=user_id, request_kind__in=[NEW, EXTENSION],
        start_date__lte=end, end_date__gte=start,
        status__in=(*PENDING_STATES, APPROVED, EXTENDED),
    )
    for row in rows:
        if (leave_type == CL and row.leave_type == CL and start == end
                and row.start_date == row.end_date == start and half_day
                and row.half_day_period and half_day != row.half_day_period):
            continue
        raise ValidationError("The requested period overlaps active pending or approved leave.")


def _task_user(application: LeaveApplication) -> int | None:
    state = application.status
    if "substitute_response" in state:
        return application.substitute_user_id
    if "unit_head_review" in state:
        return application.unit_head_user_id
    if "establishment" in state:
        return application.establishment_user_id
    if "final_sanction" in state or "director_self" in state:
        return application.final_authority_user_id
    return None


def _queue_task_notification(application: LeaveApplication) -> None:
    recipient = _task_user(application)
    if recipient is None:
        return
    notifications.enqueue(
        topic="action_assigned",
        dedupe_key=f"assignment:{application.pk}:{application.status}",
        recipient_user_id=recipient,
        subject="Employee Leave Management task assigned",
        body=f"Leave request {application.pk} is awaiting your action ({application.status}).",
    )


def _transition(application: LeaveApplication, *, event: str, principal,
                outcome: str = "", note: str = "") -> LeaveApplication:
    application = LeaveApplication.objects.select_for_update().get(pk=application.pk)
    kind = application.request_kind
    actor_name = "employee"
    if event in {"accept_substitute", "decline_substitute"}:
        actor_name = "substitute"
    elif event.startswith("unit_head"):
        actor_name = "unit_head"
    elif event == "route":
        actor_name = "establishment"
    elif event in {"sanction", "review_resumption"}:
        actor_name = "sanctioning_authority"
    elif event == "director_sanction":
        actor_name = "director"
    try:
        transition = resolve(kind, application.status, event, outcome)
    except InvalidTransition as exc:
        raise ValidationError(str(exc)) from exc
    if transition.actor != actor_name:
        raise ValidationError("The requested action does not match the workflow actor.")
    if not principal.has_permission(transition.permission):
        raise PermissionDenied("The active IAM role lacks the required leave permission.")
    if actor_name == "employee" and application.applicant_user_id != principal.user_id:
        raise NotFound()
    assigned = {
        "substitute": application.substitute_user_id,
        "unit_head": application.unit_head_user_id,
        "establishment": application.establishment_user_id,
        "sanctioning_authority": application.final_authority_user_id,
        "director": application.final_authority_user_id,
    }.get(actor_name)
    if actor_name != "employee" and assigned != principal.user_id:
        raise NotFound()
    if actor_name == "substitute":
        response = "accept" if event == "accept_substitute" else "decline"
        SubstituteResponse.objects.create(
            application=application, substitute_user_id=principal.user_id,
            response=response,
        )
    if event == "unit_head_recommendation":
        application.recommendation = note or "Recommended"
    old_status = application.status
    application.status = transition.destination
    if ((application.request_kind == NEW and application.status == APPROVED)
            or (application.request_kind == EXTENSION and application.status == EXTENDED)):
        available = accounts.lock_balance(
            application.applicant_user_id, application.leave_type,
            application.start_date.year,
        )
        if available < application.requested_days:
            raise ValidationError("The available leave balance is insufficient for sanction.")
    application.task_assigned_at = timezone.now()
    if application.status not in PENDING_STATES:
        application.decided_at = timezone.now()
    application.save(update_fields=["status", "recommendation", "task_assigned_at",
                                    "decided_at", "updated_at"])
    LeaveDecision.objects.create(
        application=application, event=event, from_status=old_status,
        to_status=application.status, actor_user_id=principal.user_id,
        actor_kind=actor_name, outcome=outcome, note=note,
    )
    if application.request_kind == CANCELLATION and application.status == "cancelled":
        original = application.original_application
        if original:
            accounts.post(
                user_id=original.applicant_user_id, leave_type=original.leave_type,
                year=original.start_date.year, amount=original.requested_days,
                transaction_type="cancellation_reversal",
                source_key=f"cancellation:{application.pk}:restore",
                application=application, actor_user_id=principal.user_id,
            )
            original.status = "cancelled"
            original.save(update_fields=["status", "updated_at"])
    elif application.request_kind == NEW and application.status == APPROVED:
        accounts.post(
            user_id=application.applicant_user_id, leave_type=application.leave_type,
            year=application.start_date.year, amount=-application.requested_days,
            transaction_type="leave_approved", source_key=f"approved:{application.pk}",
            application=application, actor_user_id=principal.user_id,
        )
    elif application.request_kind == EXTENSION and application.status == EXTENDED:
        original = application.original_application
        accounts.post(
            user_id=application.applicant_user_id, leave_type=application.leave_type,
            year=application.start_date.year, amount=-application.requested_days,
            transaction_type="extension_approved", source_key=f"extension:{application.pk}",
            application=application, actor_user_id=principal.user_id,
        )
        if original:
            original.end_date = application.end_date
            original.requested_days += application.requested_days
            original.save(update_fields=["end_date", "requested_days", "updated_at"])
    _queue_task_notification(application)
    return application


@transaction.atomic
def submit_leave(principal, data: dict) -> LeaveApplication:
    leave_type = data.get("leave_type", "")
    if leave_type not in LEAVE_TYPES:
        raise ValidationError({"leave_type": "Choose a supported leave category."})
    start, end = data.get("start_date"), data.get("end_date")
    if not start or not end:
        raise ValidationError("Start and end dates are required.")
    policy = _policy(leave_type)
    person = _profile(principal.user_id)
    if policy.applies_to == "faculty" and person.kind != "faculty":
        raise ValidationError("This leave category is limited to faculty.")
    if policy.applies_to == "staff" and person.kind != "staff":
        raise ValidationError("This leave category is limited to staff.")
    half_day = data.get("half_day_period", "")
    days = _validate_dates(leave_type, start, end, half_day, policy)
    if policy.medical_evidence_required and not data.get("medical_evidence_reference"):
        raise ValidationError("Supporting medical evidence is required by the current policy.")
    if data.get("station_leave") and not data.get("station_leave_details"):
        raise ValidationError("Station Leave details are required when applicable.")
    _check_overlap(principal.user_id, leave_type, start, end, half_day)
    if policy.substitute_required:
        _validate_substitute(
            applicant_id=principal.user_id, substitute_id=data.get("substitute_user_id"),
            start=start, end=end)
    route = _route(person, leave_type, principal)
    accounts.ensure_annual_credit(
        user_id=principal.user_id, leave_type=leave_type, year=start.year,
        employee_kind=person.kind)
    available = accounts.balance(principal.user_id, leave_type, start.year)
    if available < days:
        raise ValidationError("The available leave balance is insufficient.")
    application = LeaveApplication.objects.create(
        applicant_user_id=principal.user_id, request_kind=NEW, leave_type=leave_type,
        start_date=start, end_date=end, requested_days=days, half_day_period=half_day,
        purpose=data.get("purpose", "").strip(), station_leave=data.get("station_leave", False),
        station_leave_details=data.get("station_leave_details", ""),
        medical_evidence_reference=data.get("medical_evidence_reference", ""),
        organizational_unit=person.organizational_unit,
        substitute_required=policy.substitute_required,
        substitute_user_id=data.get("substitute_user_id"), **route,
    )
    outcome = ("substitute_required" if policy.substitute_required else
               "no_substitute_director" if principal.active_role == "Director" else
               "no_substitute_not_director")
    application.submitted_at = timezone.now()
    application.save(update_fields=["submitted_at", "updated_at"])
    _transition(application, event="submit", principal=principal, outcome=outcome)
    return application


@transaction.atomic
def request_cancellation(principal, original: LeaveApplication) -> LeaveApplication:
    if original.applicant_user_id != principal.user_id:
        raise NotFound()
    if original.status != APPROVED or original.start_date <= timezone.localdate():
        raise ValidationError("Approved leave can be cancelled only before its start date.")
    child = LeaveApplication.objects.create(
        applicant_user_id=original.applicant_user_id, request_kind=CANCELLATION,
        original_application=original, leave_type=original.leave_type,
        start_date=original.start_date, end_date=original.end_date,
        requested_days=original.requested_days, purpose="Cancellation request",
        organizational_unit=original.organizational_unit,
        unit_head_user_id=original.unit_head_user_id,
        establishment_required=original.establishment_required,
        establishment_user_id=original.establishment_user_id,
        final_authority_user_id=original.final_authority_user_id,
        status=APPROVED,
    )
    policy = _policy(original.leave_type)
    outcome = "eligible"
    _transition(child, event="request_cancellation", principal=principal, outcome=outcome)
    child.substitute_required = False
    child.save(update_fields=["substitute_required", "updated_at"])
    return child


@transaction.atomic
def request_extension(principal, original: LeaveApplication, end_date: date,
                      purpose: str = "", substitute_user_id: int | None = None) -> LeaveApplication:
    if original.applicant_user_id != principal.user_id:
        raise NotFound()
    if (original.status != APPROVED or original.leave_type not in {EL, COL, VL}
            or not (original.start_date <= timezone.localdate() <= original.end_date)):
        raise ValidationError("Only ongoing EL, COL, or VL may be extended.")
    start = original.end_date + timedelta(days=1)
    person = _profile(principal.user_id)
    policy = _policy(original.leave_type)
    days = _validate_dates(original.leave_type, start, end_date, "", policy)
    _check_overlap(principal.user_id, original.leave_type, start, end_date)
    _validate_substitute(
        applicant_id=principal.user_id,
        substitute_id=substitute_user_id if policy.substitute_required else None,
        start=start, end=end_date,
    ) if policy.substitute_required else None
    accounts.ensure_annual_credit(
        user_id=principal.user_id, leave_type=original.leave_type, year=start.year,
        employee_kind=person.kind)
    if accounts.balance(principal.user_id, original.leave_type, start.year) < days:
        raise ValidationError("The available leave balance is insufficient for the extension.")
    child = LeaveApplication.objects.create(
        applicant_user_id=original.applicant_user_id, request_kind=EXTENSION,
        original_application=original, leave_type=original.leave_type,
        start_date=start, end_date=end_date, requested_days=days, purpose=purpose,
        organizational_unit=original.organizational_unit,
        substitute_required=policy.substitute_required,
        substitute_user_id=substitute_user_id if policy.substitute_required else None,
        unit_head_user_id=original.unit_head_user_id,
        establishment_required=original.establishment_required,
        establishment_user_id=original.establishment_user_id,
        final_authority_user_id=original.final_authority_user_id,
        status=APPROVED,
    )
    outcome = "substitute_required" if policy.substitute_required else "no_substitute"
    child.submitted_at = timezone.now()
    child.save(update_fields=["submitted_at", "updated_at"])
    _transition(child, event="request_extension", principal=principal, outcome=outcome)
    return child


@transaction.atomic
def act_on_application(principal, application: LeaveApplication, *, event: str,
                       outcome: str = "", note: str = "",
                       substitute_user_id: int | None = None) -> LeaveApplication:
    if event == "replace_substitute":
        _validate_substitute(
            applicant_id=application.applicant_user_id,
            substitute_id=substitute_user_id,
            start=application.start_date, end=application.end_date,
        )
        application.substitute_user_id = substitute_user_id
        application.save(update_fields=["substitute_user_id", "updated_at"])
    if event == "unit_head_decision":
        if application.leave_type in {CL, RH}:
            outcome = "cl_rh_approve" if outcome == "approve" else "cl_rh_reject"
        else:
            event = "unit_head_recommendation"
            outcome = "higher_establishment" if application.establishment_required else "higher_direct"
    elif event == "unit_head_cancel":
        if is_higher_sanction(application.leave_type):
            event = "unit_head_recommendation"
            outcome = "higher_establishment" if application.establishment_required else "higher_direct"
        else:
            outcome = "unit_final_approve" if outcome == "approve" else "unit_final_reject"
    elif event in {"sanction", "director_sanction"}:
        outcome = "approve" if outcome == "approve" else "reject"
    return _transition(application, event=event, principal=principal,
                       outcome=outcome, note=note)


@transaction.atomic
def record_resumption(principal, application: LeaveApplication,
                      actual_date: date) -> ResumptionRecord:
    if application.applicant_user_id != principal.user_id:
        raise NotFound()
    if application.leave_type not in {EL, COL, VL} or application.status != APPROVED:
        raise ValidationError("Resumption applies to approved EL, COL, or VL.")
    if actual_date < application.start_date:
        raise ValidationError("Actual resumption cannot precede the approved leave start.")
    record = ResumptionRecord.objects.create(
        application=application, employee_user_id=principal.user_id,
        actual_resumption_date=actual_date,
    )
    return record


@transaction.atomic
def review_resumption(principal, record: ResumptionRecord) -> ResumptionRecord:
    if record.application.final_authority_user_id != principal.user_id:
        raise NotFound()
    if not principal.has_permission("leave.resumption.review"):
        raise PermissionDenied()
    actual = record.actual_resumption_date
    end = record.application.end_date
    event_state = ("resumption_reviewed_no_adjustment" if actual == end else
                   "resumption_reviewed_early_return_synchronized" if actual < end else
                   "resumption_reviewed_late_return_synchronized")
    record.state = event_state
    record.reviewed_by_user_id = principal.user_id
    record.reviewed_at = timezone.now()
    if actual != end:
        try:
            contracts.synchronize_attendance(
                user_id=record.employee_user_id,
                start_date=record.application.start_date, end_date=actual)
            record.synchronization_status = "synchronized"
        except contracts.ExternalDependencyUnavailable as exc:
            record.synchronization_status = "pending_external"
            record.synchronization_error = str(exc)[:300]
    record.save(update_fields=["state", "reviewed_by_user_id", "reviewed_at",
                               "synchronization_status", "synchronization_error"])
    return record
