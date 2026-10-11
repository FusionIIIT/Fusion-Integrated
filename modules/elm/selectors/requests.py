"""Request and record selectors."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import (
    HolidayCalendar,
    LeaveRecord,
    LeaveRequest,
    Resumption,
)


def my_requests(user_id: int) -> QuerySet[LeaveRequest]:
    """Every request a person submitted, newest first."""
    return LeaveRequest.objects.filter(user_id=user_id)


def request_for_user(request_id: int,
                     user_id: int) -> LeaveRequest | None:
    """One of the caller's own requests, or ``None`` — the
    caller must not learn that someone else's request exists."""
    try:
        return LeaveRequest.objects.get(id=request_id, user_id=user_id)
    except LeaveRequest.DoesNotExist:
        return None


def request_for_participant(request_id: int,
                            user_id: int) -> LeaveRequest | None:
    """A request the caller submitted *or* has a live task on."""
    own = request_for_user(request_id, user_id)
    if own is not None:
        return own
    try:
        return LeaveRequest.objects.get(
            id=request_id,
            tasks__assignee_user_id=user_id,
            tasks__status="pending",
        )
    except LeaveRequest.DoesNotExist:
        return None


def records_for(user_id: int, *, may_view_all: bool = False,
                unit_code: str | None = None) -> QuerySet[LeaveRecord]:
    """Leave records in the caller's scope.

    A person always sees their own records; a holder of
    ``elm.records.view`` sees the whole book (or just their unit
    when the caller passes ``unit_code``).
    """
    if may_view_all:
        qs = LeaveRecord.objects.all()
        if unit_code:
            qs = qs.filter(
                user_id__in=_unit_member_ids(unit_code))
        return qs
    return LeaveRecord.objects.filter(user_id=user_id)


def _unit_member_ids(unit_code: str) -> QuerySet:
    from modules.elm.models import EmployeeProfile

    return EmployeeProfile.objects.filter(
        unit_code=unit_code, is_active=True).values_list(
            "user_id", flat=True)


def resumptions_for_record(record_id: int) -> QuerySet[Resumption]:
    return Resumption.objects.filter(record_id=record_id)


def effective_calendar() -> HolidayCalendar | None:
    """The currently effective published calendar — the latest
    published row governs until a replacement is published
    (BR-EL-031)."""
    return HolidayCalendar.objects.filter(
        published_at__isnull=False).order_by(
            "-published_at", "-year").first()


def closed_dates() -> set:
    """Closed dates in the effective calendar, for non-continuous
    counting (CL/SCL/RH skip them)."""
    calendar = effective_calendar()
    if calendar is None:
        return set()
    return set(
        calendar.holidays.filter(closed=True).values_list(
            "date", flat=True))
