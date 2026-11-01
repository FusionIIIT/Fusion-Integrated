"""ELM services - core leave processing business logic."""

from collections.abc import Sequence

from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveCategory,
    EmployeeLeaveBalance,
    SubstituteNomination,
)
from core.db.mixins import TimeStampedModel


def get_leave_category(code: str) -> LeaveCategory:
    """Retrieve a leave category by its code."""
    from django.db.models import get_object_or_404
    return get_object_or_404(LeaveCategory, code=code)


def can_apply_leave(user_id: int, leave_category_code: str,
                  requested_start, requested_end) -> dict:
    """Validate whether an employee can apply for the requested leave."""
    from modules.elm.models import LeaveApplication

    lc = get_leave_category(leave_category_code)

    # Check balance
    balance, _ = EmployeeLeaveBalance.objects.get_or_create(
        user_id=user_id, leave_category=lc,
        defaults={"remaining_days": lc.entitlement_days,
                  "used_days": 0},
    )
    requested_days = (requested_end - requested_start).days

    if balance.remaining_days < requested_days:
        return {"allowed": False,
                "reason": f"Insufficient {lc.code} balance: "
                          f"{balance.remaining_days} remaining, "
                          f"{requested_days} requested"}

    # Check for overlapping pending/approved leave
    overlapping = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=["submitted", "unit_head_review", "recommended", "sanctioned"],
    ).exclude(
        requested_end__lt=models.F("requested_start")
    ).exclude(
        requested_start__gt=models.F("requested_end")
    ).count()

    if overlapping > 0:
        return {"allowed": False,
                "reason": f"Employee has overlapping pending/approved leave"}

    return {"allowed": True, "reason": "Eligible for leave application"}


def submit_leave_application(user_id: int, leave_category_code: str,
                            requested_start, requested_end,
                            purpose: str, halftype: str = "",
                            station_leave: bool = False) -> LeaveApplication:
    """Create and submit a new leave application."""
    lc = get_leave_category(leave_category_code)

    # Ensure balance record exists
    balance, _ = EmployeeLeaveBalance.objects.get_or_create(
        user_id=user_id, leave_category=lc,
        defaults={"remaining_days": lc.entitlement_days,
                  "used_days": 0},
    )

    from django.db import models
    application = LeaveApplication.objects.create(
        user_id=user_id,
        leave_category=lc,
        requested_start=requested_start,
        requested_end=requested_end,
        purpose=purpose,
        halftype=halftype,
        station_leave=station_leave,
        status="submitted",
    )

    # Create initial transition audit record
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status="",
        to_status="submitted",
        actor_user_id=user_id,
        actor_label="Employee",
        reason=purpose,
    )

    # Deduct from balance
    balance.used_days = models.F("used_days") + (
        (requested_end - requested_start).days if lc.continuous_counting else 0)
    balance.remaining_days = models.F("remaining_days") - (
        (requested_end - requested_start).days if lc.continuous_counting else 0)
    balance.save(update_fields=["used_days", "remaining_days"])

    return application


def process_unit_head_review(application: LeaveApplication,
                           recommended: bool,
                           actor_user_id: int,
                           actor_label: str) -> LeaveApplication:
    """Process the Unit Head's review recommendation."""
    if recommended:
        new_status = "recommended"
    else:
        new_status = "not_recommended"

    application.status = new_status
    application.save(update_fields=["status"])

    # Create transition audit record
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status="submitted",
        to_status=new_status,
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        reason="Unit Head %s %s leave" % (("recommends" if recommended else "does not recommend"),
                                          application.leave_category.code),
    )

    return application


def approve_leave_application(application: LeaveApplication,
                              next_role: str,
                              actor_user_id: int,
                              actor_label: str) -> LeaveApplication:
    """Approve a leave application and route it to the next authority."""
    application.status = "sanctioned"
    application.save(update_fields=["status"])

    # Create transition audit record
    from_status = "recommended" if application.status == "sanctioned" else "not_recommended"
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status=from_status,
        to_status="sanctioned",
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        reason="%s sanctions %s leave" % (next_role, application.leave_category.code),
    )

    # Update leave balance
    from modules.elm.models import EmployeeLeaveBalance
    lc = application.leave_category
    balance, created = EmployeeLeaveBalance.objects.get_or_create(
        user_id=application.user_id, leave_category=lc,
        defaults={"remaining_days": lc.entitlement_days,
                  "used_days": 0},
    )
    delta = (application.requested_end - application.requested_start).days
    balance.used_days = models.F("used_days") - delta
    balance.remaining_days = models.F("remaining_days") + delta
    balance.save(update_fields=["used_days", "remaining_days"])

    return application


def withdraw_leave_application(application: LeaveApplication,
                              withdrawn_by_user_id: int) -> LeaveApplication:
    """Withdraw a pending leave application."""
    application.status = "withdrawn"
    application.save(update_fields=["status"])

    # Create transition audit record
    LeaveApplicationTransition.objects.create(
        application=application,
        from_status="",
        to_status="withdrawn",
        actor_user_id=withdrawn_by_user_id,
        actor_label="Withdrawn by employee",
        reason="Employee withdrew the leave request",
    )

    # Restore balance days
    from modules.elm.models import EmployeeLeaveBalance
    lc = application.leave_category
    balance, _ = EmployeeLeaveBalance.objects.get_or_create(
        user_id=application.user_id, leave_category=lc,
        defaults={"remaining_days": lc.entitlement_days,
                  "used_days": 0},
    )
    delta = (application.requested_end - application.requested_start).days
    balance.remaining_days = models.F("remaining_days") + delta
    balance.used_days = models.F("used_days") - delta
    balance.save(update_fields=["used_days", "remaining_days"])

    return application