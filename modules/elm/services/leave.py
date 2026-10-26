from django.db import transaction

from modules.elm.domain.errors import (
    ApplicationNotFound,
    InsufficientBalance,
    InvalidLeaveRange,
    NoBalanceRecord,
    NotPending,
    SelfReviewNotAllowed,
)
from modules.elm.domain.leave_days import count_leave_days
from modules.elm.models import LeaveAction, LeaveApplication, LeaveBalance


def _days_for(start, end, part_of_day):
    try:
        days = count_leave_days(start, end, part_of_day)
    except ValueError as exc:
        raise InvalidLeaveRange(str(exc)) from exc
    if days <= 0:
        raise InvalidLeaveRange("The request contains no working days.")
    return days


def _check_available(balance, days):
    if balance.entitled_days - balance.used_days < days:
        raise InsufficientBalance("Not enough leave balance for this request.")


def apply_for_leave(user_id, data):
    days = _days_for(data["start_date"], data["end_date"], data["part_of_day"])
    balance = LeaveBalance.objects.filter(
        user_id=user_id,
        year=data["start_date"].year,
        category=data["category"],
    ).first()
    if balance is None:
        raise NoBalanceRecord("No leave balance exists for this category and year.")
    _check_available(balance, days)
    with transaction.atomic():
        obj = LeaveApplication.objects.create(user_id=user_id, **data)
        LeaveAction.objects.create(
            application=obj, actor_user_id=user_id, action="submitted"
        )
    return obj


@transaction.atomic
def decide_leave(application_id, reviewer_id, decision, note=""):
    obj = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id)
        .first()
    )
    if obj is None:
        raise ApplicationNotFound("Leave request not found.")
    if obj.user_id == reviewer_id:
        raise SelfReviewNotAllowed("You cannot review your own request.")
    if obj.status != "pending":
        raise NotPending("This request is no longer pending.")

    if decision == "approve":
        days = _days_for(obj.start_date, obj.end_date, obj.part_of_day)
        balance = (
            LeaveBalance.objects.select_for_update()
            .filter(
                user_id=obj.user_id,
                year=obj.start_date.year,
                category=obj.category,
            )
            .first()
        )
        if balance is None:
            raise NoBalanceRecord("No leave balance exists for this request.")
        _check_available(balance, days)
        balance.used_days += days
        balance.save(update_fields=["used_days"])

    obj.status = "approved" if decision == "approve" else "rejected"
    obj.decision_note = note
    obj.save(update_fields=["status", "decision_note"])
    LeaveAction.objects.create(
        application=obj, actor_user_id=reviewer_id, action=decision, note=note
    )
    return obj
