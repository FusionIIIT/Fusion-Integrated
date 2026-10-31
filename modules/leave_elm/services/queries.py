from decimal import Decimal
from django.db.models import Q
from core.api.exceptions import PermissionDeniedError
from modules.leave_elm.domain.policy import LEAVE_CATEGORY_NAMES, LEAVE_POLICY_DEFAULTS
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveCategory, LeaveNotification, LeaveTask, LeaveType

def list_applications(actor, scope='mine'):
    can_review_all = (
        actor.has_permission('leave_elm.application.review')
        or actor.has_permission('leave_elm.application.approve')
        or actor.has_permission('leave_elm.record.manage')
    )
    
    if not (actor.has_permission('leave_elm.application.view_self') or can_review_all):
        raise PermissionDeniedError()
    
    qs = LeaveApplication.objects.select_related('leave_type', 'leave_type__leave_category').order_by('-created_at', '-id')
    
    if scope == 'all' and can_review_all:
        return qs
    
    return qs.filter(user_id=actor.user_id)

def own_balances(actor):
    if not actor.has_permission('leave_elm.application.view_self'):
        raise PermissionDeniedError()
    
    for cat_name in LEAVE_CATEGORY_NAMES:
        cat, _ = LeaveCategory.objects.get_or_create(name=cat_name, defaults={'description': cat_name})
        LeaveType.objects.get_or_create(
            name=cat_name,
            defaults={
                'description': cat_name,
                'leave_category': cat
            }
        )
        
        LeaveBalance.objects.get_or_create(
            user_id=actor.user_id,
            leave_category=cat,
            defaults={'balance': Decimal(str(LEAVE_POLICY_DEFAULTS[cat_name]))}
        )
    
    return LeaveBalance.objects.select_related('leave_category').filter(user_id=actor.user_id).order_by('leave_category__name', 'id')

def assigned_tasks(actor):
    if (
        not (actor.has_permission('leave_elm.task.view') or 
             actor.has_permission('leave_elm.substitute.respond') or 
             actor.has_permission('leave_elm.application.review') or 
             actor.has_permission('leave_elm.application.approve'))
    ):
        raise PermissionDeniedError()
    
    cond = Q(user_id=actor.user_id)
    
    if actor.has_permission('leave_elm.application.review'):
        cond = cond | Q(role='reviewer')
    
    if actor.has_permission('leave_elm.application.approve'):
        cond = cond | Q(role='authority')
    
    return LeaveTask.objects.select_related('leave_application', 'leave_application__leave_type').filter(status='Pending').filter(cond).order_by('-created_at', '-id')

def list_notifications(actor):
    if not actor.has_permission('leave_elm.application.view_self'):
        raise PermissionDeniedError()
    
    return LeaveNotification.objects.select_related('leave_application').filter(user_id=actor.user_id).order_by('-created_at', '-id')
