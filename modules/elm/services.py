from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import (
    AssignmentNotification,
    Employee,
    HierarchyConfiguration,
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveCategory,
    LeavePolicy,
    LeaveState,
    LeaveUsage,
    SanctioningAuthorityRule,
    SubstituteResponse,
)

DEFAULT_LIMITS = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),
    "COL": Decimal("20"),
    "VL": Decimal("60"),
}
HIGHER = {"SCL", "EL", "COL", "VL"}


def current_hierarchy():
    return HierarchyConfiguration.objects.filter(is_current=True).order_by("-id").first()


def establishment_allowed(principal, hierarchy):
    return bool(
        principal
        and hierarchy
        and hierarchy.establishment_configured
        and hierarchy.establishment_role
        and hierarchy.establishment_role in principal.roles
        and (
            not hierarchy.establishment_employee_id
            or hierarchy.establishment_employee.user_id == principal.user_id
        )
    )


def _current_limit(category):
    policy = LeavePolicy.objects.filter(is_current=True).order_by("-id").first()
    return getattr(policy, f"{category.lower()}_days") if policy else DEFAULT_LIMITS[category]


def _effective_calendar(year):
    return (
        HolidayCalendar.objects.filter(year=year, is_published=True)
        .order_by(F("published_at").desc(nulls_last=True), "-id")
        .first()
    )


def _validate_dates(start_date, end_date):
    if start_date > end_date:
        raise ValidationError("Start date must not be after end date")


def _calculate_days(category, start_date, end_date, first_half, second_half):
    if first_half or second_half:
        if category != "CL" or start_date != end_date or first_half == second_half:
            raise ValidationError("Half-day leave must be one CL half on one date")
        return Decimal("0.5")
    return Decimal((end_date - start_date).days + 1)


def _validate_applicability(applicant, category, start_date, end_date):
    if category == "EL" and applicant.is_faculty:
        raise ValidationError("EL is available to non-faculty employees")
    if category == "VL" and not applicant.is_faculty:
        raise ValidationError("VL is available to faculty employees")
    if category not in {"RH", "VL"}:
        return
    field = "is_restricted_holiday" if category == "RH" else "is_vacation_period"
    calendars = [_effective_calendar(year) for year in range(start_date.year, end_date.year + 1)]
    dates = HolidayDate.objects.filter(
        calendar__in=[calendar for calendar in calendars if calendar],
        date__range=(start_date, end_date),
        **{field: True},
    )
    if dates.values("date").distinct().count() != (end_date - start_date).days + 1:
        raise ValidationError(
            "Dates must be applicable published Restricted Holidays"
            if category == "RH"
            else "VL must be within a published vacation period"
        )


def _has_leave_overlap(employee, start_date, end_date, first_half=False, second_half=False):
    active = LeaveApplication.objects.filter(
        applicant=employee,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exclude(state__in=[LeaveState.DRAFT, LeaveState.REJECTED, LeaveState.WITHDRAWN])
    for item in active:
        if not (first_half or second_half):
            return True
        if item.category != "CL" or not (item.first_half or item.second_half):
            return True
        if (first_half and item.first_half) or (second_half and item.second_half):
            return True
    return False


def _validate_entitlement(applicant, category, year, requested):
    usage = LeaveUsage.objects.filter(employee=applicant, category=category, year=year).first()
    used = usage.used_days if usage else Decimal("0")
    if used + requested > _current_limit(category):
        raise ValidationError("Leave entitlement exceeded")


def resolve_sanctioning_authority(application):
    applicant = application.applicant
    rules = SanctioningAuthorityRule.objects.filter(
        Q(applicant=None) | Q(applicant=applicant),
        Q(unit=None) | Q(unit_id=applicant.unit_id),
        designation__in=["", applicant.designation],
        category__in=["", application.category],
        is_current=True,
    ).select_related("authority")
    matching = list(rules)
    if not matching:
        raise ValidationError("No Sanctioning Authority is configured")

    def specificity(rule):
        return sum(
            (
                rule.applicant_id is not None,
                rule.unit_id is not None,
                bool(rule.designation),
                bool(rule.category),
            )
        )

    most_specific = max(specificity(rule) for rule in matching)
    authorities = {
        rule.authority_id: rule.authority for rule in matching if specificity(rule) == most_specific
    }
    if len(authorities) != 1:
        raise ValidationError("Sanctioning Authority configuration is ambiguous")
    return next(iter(authorities.values()))


def _notify(application, recipient, kind):
    if recipient:
        AssignmentNotification.objects.create(
            application=application,
            recipient=recipient,
            kind=kind,
        )


def _notify_current_task(application):
    if application.state == LeaveState.AWAITING_SUBSTITUTE:
        _notify(application, application.substitute, "substitute")
    elif application.state == LeaveState.AWAITING_DIRECTOR:
        _notify(application, application.applicant, "director_self_sanction")
    elif application.state == LeaveState.AWAITING_UNIT_HEAD:
        _notify(application, application.unit_head, "unit_head")
    elif application.state == LeaveState.AWAITING_FINAL:
        _notify(application, application.sanctioning_authority, "sanctioning_authority")
    elif application.state == LeaveState.AWAITING_ESTABLISHMENT:
        hierarchy = current_hierarchy()
        _notify(application, hierarchy.establishment_employee, "establishment")


def _locked_application(application):
    return (
        LeaveApplication.objects.select_for_update(of=("self",))
        .select_related(
            "applicant",
            "applicant__unit",
            "substitute",
            "unit_head",
            "sanctioning_authority",
        )
        .get(pk=application.pk)
    )


def _update_application(application):
    application.refresh_from_db()
    return application


@transaction.atomic
def apply_leave(
    *,
    applicant,
    category,
    start_date,
    end_date,
    substitute=None,
    first_half=False,
    second_half=False,
    station_leave_details=None,
    remarks="",
):
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    applicant = (
        Employee.objects.select_for_update(of=("self",)).select_related("unit").get(pk=applicant.pk)
    )
    if category not in LeaveCategory.values:
        raise ValidationError("Invalid leave category")
    _validate_dates(start_date, end_date)
    days = _calculate_days(category, start_date, end_date, first_half, second_half)
    _validate_applicability(applicant, category, start_date, end_date)
    if substitute and substitute.pk == applicant.pk:
        raise ValidationError("Substitute must be another employee")
    if _has_leave_overlap(applicant, start_date, end_date, first_half, second_half):
        raise ValidationError("Leave overlaps an active application")
    if substitute and _has_leave_overlap(substitute, start_date, end_date):
        raise ValidationError("Substitute has overlapping leave")
    _validate_entitlement(applicant, category, start_date.year, days)
    state = (
        LeaveState.AWAITING_SUBSTITUTE
        if substitute
        else (
            LeaveState.AWAITING_DIRECTOR if applicant.is_director else LeaveState.AWAITING_UNIT_HEAD
        )
    )
    application = LeaveApplication.objects.create(
        applicant=applicant,
        category=category,
        start_date=start_date,
        end_date=end_date,
        num_days=days,
        first_half=first_half,
        second_half=second_half,
        substitute=substitute,
        unit_head=applicant.unit.head if applicant.unit else None,
        state=state,
        station_leave_details=station_leave_details or {},
        remarks=remarks,
    )
    if substitute:
        SubstituteResponse.objects.create(application=application, substitute=substitute)
    _notify_current_task(application)
    return application


@transaction.atomic
def respond_to_substitute(*, application, substitute, accepted):
    locked = _locked_application(application)
    if locked.state != LeaveState.AWAITING_SUBSTITUTE or locked.substitute_id != substitute.pk:
        raise ValidationError("Substitute response is not allowed in this state")
    if not isinstance(accepted, bool):
        raise ValidationError("Accept must be true or false")
    response = locked.substitute_response
    response.response = "Accepted" if accepted else "Declined"
    response.responded_at = timezone.now()
    response.save(update_fields=["response", "responded_at"])
    locked.state = (
        (
            LeaveState.AWAITING_DIRECTOR
            if locked.applicant.is_director
            else LeaveState.AWAITING_UNIT_HEAD
        )
        if accepted
        else LeaveState.APPLICANT_ACTION
    )
    locked.save(update_fields=["state", "updated_at"])
    _notify_current_task(locked)
    return _update_application(application)


def _record_decision(application, decision):
    if decision not in ("Approve", "Reject"):
        raise ValidationError("Decision must be Approve or Reject")
    if decision == "Approve":
        Employee.objects.select_for_update().get(pk=application.applicant_id)
        days = application.num_days
        if application.category in {"EL", "COL", "VL"}:
            days = Decimal((application.end_date - application.start_date).days + 1)
        _validate_entitlement(
            application.applicant, application.category, application.start_date.year, days
        )
        usage, _ = LeaveUsage.objects.select_for_update().get_or_create(
            employee=application.applicant,
            category=application.category,
            year=application.start_date.year,
        )
        usage.used_days += days
        usage.save(update_fields=["used_days"])
    application.state = LeaveState.APPROVED if decision == "Approve" else LeaveState.REJECTED
    application.save(update_fields=["state", "updated_at"])


@transaction.atomic
def review_leave(*, application, unit_head, decision):
    locked = _locked_application(application)
    if locked.state != LeaveState.AWAITING_UNIT_HEAD or locked.unit_head_id != unit_head.pk:
        raise ValidationError("Unit Head review is not allowed in this state")
    if locked.category in ("CL", "RH"):
        _record_decision(locked, decision)
    else:
        if decision not in ("Recommended", "Not Recommended"):
            raise ValidationError("Decision must be Recommended or Not Recommended")
        hierarchy = current_hierarchy()
        locked.unit_head_recommendation = decision
        if hierarchy and hierarchy.establishment_configured:
            locked.state = LeaveState.AWAITING_ESTABLISHMENT
        else:
            locked.sanctioning_authority = resolve_sanctioning_authority(locked)
            locked.state = LeaveState.AWAITING_FINAL
        locked.save(
            update_fields=[
                "state",
                "unit_head_recommendation",
                "sanctioning_authority",
                "updated_at",
            ]
        )
        _notify_current_task(locked)
    return _update_application(application)


@transaction.atomic
def route_establishment(*, application, role):
    hierarchy = current_hierarchy()
    if (
        not hierarchy
        or not hierarchy.establishment_configured
        or not role
        or role != hierarchy.establishment_role
    ):
        raise ValidationError("Establishment role is not authorized")
    locked = _locked_application(application)
    if locked.state != LeaveState.AWAITING_ESTABLISHMENT or locked.category not in HIGHER:
        raise ValidationError("Establishment routing is not allowed in this state")
    locked.sanctioning_authority = resolve_sanctioning_authority(locked)
    locked.state = LeaveState.AWAITING_FINAL
    locked.save(update_fields=["state", "sanctioning_authority", "updated_at"])
    _notify_current_task(locked)
    return _update_application(application)


@transaction.atomic
def make_final_decision(*, application, actor, decision):
    locked = _locked_application(application)
    if locked.state != LeaveState.AWAITING_FINAL or locked.category not in HIGHER:
        raise ValidationError("Final sanction decision is not allowed in this state")
    if locked.sanctioning_authority_id != actor.pk:
        raise ValidationError("Only the resolved Sanctioning Authority can decide")
    _record_decision(locked, decision)
    return _update_application(application)


@transaction.atomic
def make_director_decision(*, application, actor, decision):
    locked = _locked_application(application)
    if locked.state != LeaveState.AWAITING_DIRECTOR:
        raise ValidationError("Director self-sanction is not allowed in this state")
    if not locked.applicant.is_director or locked.applicant_id != actor.pk:
        raise ValidationError("Only the applicant Director can decide")
    _record_decision(locked, decision)
    return _update_application(application)
