"""Basic leave validation and account updates."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.leave_elm.models import (
    ApprovalRecord,
    ExtensionRecord,
    HolidayCalendar,
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveBalanceTransaction,
    LeaveCategory,
    PolicyConfiguration,
)

CONTINUOUS_CODES = {"EL", "COL", "VL"}
ACTIVE_STATUSES = {
    "awaiting_substitute",
    "awaiting_unit_head",
    "awaiting_establishment",
    "awaiting_sanction",
    "awaiting_self_sanction",
    "applicant_action_required",
    "approved",
}


def _calendar_days(start, end):
    if end < start:
        raise ValidationError("The end date must not precede the start date.")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _calendar_dates(year, field):
    calendars = HolidayCalendar.objects.filter(year=year, is_published=True)
    result = set()
    for calendar in calendars:
        for entry in getattr(calendar, field) or []:
            value = entry.get("date") if isinstance(entry, dict) else entry
            try:
                result.add(date.fromisoformat(value))
            except (TypeError, ValueError):
                continue
    return result


def _vacation_period_contains(period, starts_on, ends_on):
    try:
        period_start = date.fromisoformat(period["starts_on"])
        period_end = date.fromisoformat(period["ends_on"])
    except (KeyError, TypeError, ValueError):
        return False
    return period_start <= starts_on and period_end >= ends_on


def chargeable_days_by_year(category, start, end, half_day="full"):
    days = _calendar_days(start, end)
    if half_day != "full":
        if category.code != "CL" or start != end:
            raise ValidationError("Half-day leave is supported only for single-day CL.")
        return {start.year: Decimal("0.5")}
    if category.code == "RH":
        restricted_days = _calendar_dates(start.year, "restricted_holidays")
        if len(days) != 1 or start not in restricted_days:
            raise ValidationError("RH must be requested for a date in the published RH calendar.")
        return {start.year: Decimal("1")}
    if category.code in CONTINUOUS_CODES:
        counts = {}
        for day in days:
            counts[day.year] = counts.get(day.year, 0) + 1
        return {year: Decimal(count) for year, count in counts.items()}

    closed_days = set()
    for year in {day.year for day in days}:
        closed_days.update(_calendar_dates(year, "holidays"))
    counts = {}
    for day in days:
        if day.weekday() < 5 and day not in closed_days:
            counts[day.year] = counts.get(day.year, 0) + 1
    return {year: Decimal(count) for year, count in counts.items()}


def chargeable_days(category, start, end, half_day="full"):
    return sum(chargeable_days_by_year(category, start, end, half_day).values(), Decimal("0"))


def validate_application(*, user_id, category, starts_on, ends_on, half_day, applicant_role=""):
    if not category.is_active:
        raise ValidationError("This leave category is not active.")
    if category.code == "VL":
        if _role_key(applicant_role) != "faculty":
            raise ValidationError("Vacation Leave is available to faculty only.")
        periods = (
            PolicyConfiguration.objects.filter(
                category__isnull=True, key="academic_vacation_periods"
            )
            .values_list("value", flat=True)
            .first()
        )
        if not isinstance(periods, list) or not any(
            isinstance(period, dict) and _vacation_period_contains(period, starts_on, ends_on)
            for period in periods
        ):
            raise ValidationError(
                "The requested VL period is not in the configured Academic Calendar."
            )
    allocations = chargeable_days_by_year(category, starts_on, ends_on, half_day)
    amount = sum(allocations.values(), Decimal("0"))
    if amount <= 0:
        raise ValidationError("The requested period contains no chargeable leave days.")

    for existing in LeaveApplication.objects.filter(
        user_id=user_id, status__in=ACTIVE_STATUSES, starts_on__lte=ends_on, ends_on__gte=starts_on
    ):
        same_day_cl_halves = (
            category.code == "CL"
            and existing.category.code == "CL"
            and starts_on == ends_on == existing.starts_on == existing.ends_on
            and half_day != "full"
            and existing.half_day != "full"
            and half_day != existing.half_day
        )
        if not same_day_cl_halves:
            raise ValidationError("The requested period overlaps another active leave.")

    pending_statuses = {
        "awaiting_substitute",
        "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_sanction",
        "awaiting_self_sanction",
        "applicant_action_required",
    }
    for year, requested in allocations.items():
        balance = (
            LeaveBalance.objects.select_for_update()
            .filter(user_id=user_id, category=category, year=year)
            .first()
        )
        pending_days = Decimal("0")
        pending = LeaveApplication.objects.filter(
            user_id=user_id,
            category=category,
            status__in=pending_statuses,
            starts_on__lte=date(year, 12, 31),
            ends_on__gte=date(year, 1, 1),
        )
        for existing in pending:
            saved = existing.requested_days_by_year or {}
            pending_days += Decimal(str(saved.get(str(year), "0")))
        pending_extensions = ExtensionRecord.objects.filter(
            requested_by_user_id=user_id,
            application__category=category,
            status__in={
                "pending",
                "awaiting_substitute",
                "awaiting_establishment",
                "awaiting_sanction",
                "applicant_action_required",
            },
        )
        for extension in pending_extensions:
            saved = extension.additional_days_by_year or {}
            pending_days += Decimal(str(saved.get(str(year), "0")))
        if balance is None or balance.closing_balance - pending_days < requested:
            raise ValidationError("Insufficient available leave balance.")
    return amount


@transaction.atomic
def submit_application(*, user_id, **data):
    try:
        category = LeaveCategory.objects.get(pk=data.pop("category_id"), is_active=True)
    except LeaveCategory.DoesNotExist as exc:
        raise ValidationError("Select an active leave category.") from exc
    applicant_role = data.pop("applicant_role", "")
    amount = validate_application(
        user_id=user_id,
        category=category,
        starts_on=data["starts_on"],
        ends_on=data["ends_on"],
        half_day=data["half_day"],
        applicant_role=applicant_role,
    )
    allocations = chargeable_days_by_year(
        category, data["starts_on"], data["ends_on"], data["half_day"]
    )
    substitute_id = data.get("substitute_user_id")
    if substitute_id == user_id:
        raise ValidationError("You cannot nominate yourself as substitute.")
    if data["station_leave"] and not data["station_destination"].strip():
        raise ValidationError("A destination is required for Station Leave.")
    if (
        substitute_id
        and LeaveApplication.objects.filter(
            user_id=substitute_id,
            status__in=ACTIVE_STATUSES,
            starts_on__lte=data["ends_on"],
            ends_on__gte=data["starts_on"],
        ).exists()
    ):
        raise ValidationError("The nominated substitute has overlapping leave.")
    is_director = _role_key(applicant_role) == "director"
    if is_director and not substitute_id:
        status = "awaiting_self_sanction"
        assigned_role = "director"
    elif substitute_id:
        status = "awaiting_substitute"
        assigned_role = ""
    else:
        status = "awaiting_unit_head"
        assigned_role = "unit_head"
    application = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        requested_days=amount,
        requested_days_by_year={str(year): str(value) for year, value in allocations.items()},
        status=status,
        applicant_role=applicant_role,
        assigned_role=assigned_role,
        submitted_at=timezone.now(),
        **data,
    )
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status="draft",
        to_status=status,
        actor_user_id=user_id,
        actor_label="Employee",
    )
    if substitute_id:
        from modules.leave_elm.models import Substitute

        Substitute.objects.create(
            application=application, user_id=user_id, substitute_user_id=substitute_id
        )
    return application


def _role_key(value):
    return "".join(character for character in (value or "").lower() if character.isalnum())


def _actor_role_keys(actor):
    roles = set(getattr(actor, "roles", ()) or ())
    active_role = getattr(actor, "active_role", None)
    if active_role:
        roles.add(active_role)
    return {_role_key(role) for role in roles}


def actor_has_assigned_role(actor, assigned_role):
    return _role_key(assigned_role) in _actor_role_keys(actor)


def _routing_configuration(category):
    row = PolicyConfiguration.objects.filter(category=category, key="hierarchy").first()
    if row is None:
        row = PolicyConfiguration.objects.filter(category__isnull=True, key="hierarchy").first()
    config = row.value if row and isinstance(row.value, dict) else {}
    category_config = config.get(category.code, config)
    return category_config if isinstance(category_config, dict) else {}


def routing_configuration(category):
    return _routing_configuration(category)


def next_sanctioning_role(category):
    roles = _routing_configuration(category).get("sanctioning_roles")
    if isinstance(roles, str):
        roles = [roles]
    if not roles:
        raise ValidationError("No sanctioning authority is configured for this leave category.")
    return roles[0]


def apply_balance_delta(
    *, user_id, category, allocations, application=None, transaction_type, note=""
):
    """Apply signed balance deltas by year and record each account transaction."""
    for year, raw_amount in allocations.items():
        amount = Decimal(str(raw_amount))
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=user_id, category=category, year=int(year)
        )
        balance.closing_balance += amount
        if amount < 0:
            balance.used += -amount
        else:
            balance.used -= amount
        if balance.closing_balance < 0:
            raise ValidationError("The leave balance is insufficient for this adjustment.")
        balance.save(update_fields=["used", "closing_balance", "updated_at"])
        LeaveBalanceTransaction.objects.create(
            balance=balance,
            application=application,
            transaction_type=transaction_type,
            amount=amount,
            note=note,
        )


@transaction.atomic
def review_application(*, application, actor, outcome, comments=""):
    if application.status not in {
        "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_sanction",
        "awaiting_self_sanction",
    }:
        raise ValidationError("This application is not awaiting a decision.")
    category = application.category
    old_status = application.status
    actor_roles = _actor_role_keys(actor)
    assigned_role = application.assigned_role or "unit_head"
    if _role_key(assigned_role) not in actor_roles:
        raise ValidationError("This request is assigned to another role.")
    if category.code in {"CL", "RH"}:
        if old_status not in {"awaiting_unit_head", "awaiting_self_sanction"}:
            raise ValidationError("CL/RH decisions belong to the Unit Head or Director.")
        if outcome not in {"approved", "rejected"}:
            raise ValidationError("CL/RH review must be a final decision.")
    elif old_status == "awaiting_unit_head":
        if outcome not in {"recommended", "not_recommended"}:
            raise ValidationError("Unit Head must record a recommendation.")
    elif old_status == "awaiting_establishment":
        raise ValidationError("Establishment must use the route action, not a sanction decision.")
    elif outcome not in {"approved", "rejected"}:
        raise ValidationError("Final authority must approve or reject.")

    route = _routing_configuration(category)
    if old_status in {"awaiting_sanction", "awaiting_self_sanction"}:
        if old_status == "awaiting_self_sanction":
            allowed_roles = ["director"]
        else:
            allowed_roles = route.get("sanctioning_roles")
        if not allowed_roles:
            raise ValidationError("No sanctioning authority is configured for this leave category.")
        if isinstance(allowed_roles, str):
            allowed_roles = [allowed_roles]
        if not actor_roles.intersection({_role_key(role) for role in allowed_roles}):
            raise ValidationError("You are not the configured sanctioning authority.")

    ApprovalRecord.objects.create(
        application=application,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        outcome=outcome,
        comments=comments,
    )
    if outcome in {"recommended", "not_recommended"}:
        establishment_role = route.get("establishment_role")
        if establishment_role:
            application.status = "awaiting_establishment"
            application.assigned_role = establishment_role
        else:
            application.status = "awaiting_sanction"
            application.assigned_role = next_sanctioning_role(category)
    else:
        application.status = outcome
        application.assigned_role = ""
    application.save(update_fields=["status", "assigned_role", "updated_at"])
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status=old_status,
        to_status=application.status,
        actor_user_id=actor.user_id,
        actor_label=actor.active_role or "",
        reason=comments,
    )
    if application.status == "approved":
        allocations = {
            year: -Decimal(amount) for year, amount in application.requested_days_by_year.items()
        }
        apply_balance_delta(
            user_id=application.user_id,
            category=category,
            allocations=allocations,
            application=application,
            transaction_type="deduction",
            note="Approved leave",
        )
    return application
