from django.db.models import Q
from core.api.exceptions import PermissionDeniedError
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveTask

def list_applications(actor):
    if not actor.has_permission('leave_elm.application.view_self'):
        raise PermissionDeniedError()
    return LeaveApplication.objects.filter(user_id=actor.user_id)


def own_balances(actor):
    if not actor.has_permission('leave_elm.configuration.manage'):
        raise PermissionDeniedError()
    return LeaveBalance.objects.filter(user_id=actor.user_id)


def assigned_tasks(actor):
    if not actor.has_permission('leave_elm.task.view'):
        raise PermissionDeniedError()
    return LeaveTask.objects.filter(leave_application__user_id=actor.user_id)