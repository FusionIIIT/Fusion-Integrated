from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import CalendarVersion, LeavePolicy


@transaction.atomic
def create_policy(**data):
    return LeavePolicy.objects.create(**data)


@transaction.atomic
def publish_policy(*, policy_id, actor):
    policy = LeavePolicy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        raise NotFoundError("Policy not found.")
    if not policy.parameters or not policy.hierarchy:
        raise ConflictError(
            "Policy parameters and hierarchy must be configured before publication."
        )
    overlap = (
        LeavePolicy.objects.filter(
            published_at__isnull=False, name=policy.name, effective_from__lte=policy.effective_from
        )
        .exclude(pk=policy.pk)
        .filter(effective_to__isnull=True)
    )
    if overlap.exists():
        raise ConflictError(
            (
                "An open-ended published policy version already exists; "
                "close it before publishing the replacement."
            ),
            code="policy_version_overlap",
        )
    policy.published_at = timezone.now()
    policy.published_by_user_id = actor.user_id
    policy.save(update_fields=["published_at", "published_by_user_id", "updated_at"])
    return policy


@transaction.atomic
def create_calendar(**data):
    return CalendarVersion.objects.create(**data)


@transaction.atomic
def publish_calendar(*, calendar_id, actor):
    calendar = CalendarVersion.objects.select_for_update().filter(pk=calendar_id).first()
    if calendar is None:
        raise NotFoundError("Calendar version not found.")
    for value in calendar.restricted_holidays or []:
        if not isinstance(value, str):
            raise ConflictError(
                "Restricted holiday dates must be ISO-8601 date strings.",
                code="calendar_format_invalid",
            )
    for period in calendar.vacation_periods or []:
        if (
            not isinstance(period, dict)
            or not period.get("start")
            or not period.get("end")
            or period["end"] < period["start"]
        ):
            raise ConflictError(
                "Vacation periods require ISO start/end dates in ascending order.",
                code="calendar_format_invalid",
            )
    calendar.published_at = timezone.now()
    calendar.published_by_user_id = actor.user_id
    calendar.save(update_fields=["published_at", "published_by_user_id", "updated_at"])
    return calendar
