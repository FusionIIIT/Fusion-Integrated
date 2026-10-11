from django.db.models import Prefetch, Q

from modules.elm.models import (
    Account, Application, AttendanceOutbox, AuditEntry, EmployeeConfiguration,
    HolidayCalendar, LedgerEntry, Notification, Policy, WorkflowTask,
)


def applications_for(actor):
    # BR-EL-036: administrators see records; employees see own and active-role assignments.
    qs = Application.objects.all()
    if actor is None:
        return qs.none()
    if not actor.has_permission("elm.record.manage"):
        own = Q(user_id=actor.user_id) if actor.has_permission("elm.application.self") else Q(pk__in=[])
        assigned = Q(tasks__user_id=actor.user_id, tasks__role=actor.active_role)
        qs = qs.filter(own | assigned).distinct()
    return qs.prefetch_related(
        Prefetch("history", queryset=AuditEntry.objects.order_by("id")),
        Prefetch("tasks", queryset=WorkflowTask.objects.filter(pending=True)),
    ).order_by("-id")


def tasks_for(actor):
    if actor is None:
        return WorkflowTask.objects.none()
    return WorkflowTask.objects.filter(user_id=actor.user_id, role=actor.active_role,
                                       pending=True).select_related("application").order_by("-id")


def accounts_for(actor):
    return Account.objects.filter(user_id=actor.user_id).order_by("-year")


def entries_for(actor):
    if actor is None:
        return LedgerEntry.objects.none()
    return LedgerEntry.objects.filter(account__user_id=actor.user_id).select_related("account").order_by("-id")


def notifications_for(actor):
    if actor is None:
        return Notification.objects.none()
    return Notification.objects.filter(user_id=actor.user_id).order_by("-id")


def configuration():
    return {"policy": Policy.objects.first(),
            "employees": EmployeeConfiguration.objects.order_by("user_id"),
            "calendars": HolidayCalendar.objects.order_by("-id"),
            "attendance_outbox": AttendanceOutbox.objects.filter(delivered_at=None).order_by("id")}
