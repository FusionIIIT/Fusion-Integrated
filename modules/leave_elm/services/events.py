from django.db import models
from django.utils import timezone
from modules.leave_elm.domain.policy import LEAVE_CATEGORY_NAMES, LEAVE_POLICY_DEFAULTS
from django.core.mail import send_mail
from datetime import timedelta
from modules.leave_elm.models import LeaveBalance, LeavePolicy, LeaveTask, LeaveNotification


def year_end_rollover():
    # Logic to calculate new leave balance for each user based on policy defaults
    current_year = timezone.now().year
    policies = LeavePolicy.objects.all()
    for policy in policies:
        category_defaults = LEAVE_POLICY_DEFAULTS.get(policy.name)
        if category_defaults is None:
            continue
        for leave_category in LEAVE_CATEGORY_NAMES:
            balance = LeaveBalance.objects.filter(leave_category__name=leave_category).aggregate(total_balance=models.Sum('balance'))['total_balance'] or 0
            new_balance = balance + (category_defaults - balance / 12) * 12
            LeaveBalance.objects.update_or_create(
                leave_category__name=leave_category,
                defaults={'balance': new_balance}
            )


def process_task_sla():
    # Logic to check and notify pending tasks that are approaching SLA thresholds
    threshold_days = {
        'Reminder': 60,
        'Escalation': 120
    }
    now = timezone.now()
    for task in LeaveTask.objects.filter(status='Pending'):
        reminder_threshold = threshold_days.get(task.task_type, 30)
        escalation_threshold = threshold_days.get(task.task_type, 90)
        if now > task.reminder_threshold and not task.notification_sent:
            send_mail(
                subject=f'Leave Task Reminder: {task.leave_application.id} - {task.task_type}',
                message=f"""Reminder: Your leave task is due on {task.reminder_threshold.strftime('%Y-%m-%d')}.
Please update the status of your leave application.""",
                from_email='noreply@yourdomain.com',
                recipient_list=[task.leave_application.user.email],
                fail_silently=False
            )
            task.notification_sent = True
            task.save()
        elif now > task.escalation_threshold and not task.escalated:
            send_mail(
                subject=f'Leave Task Escalation: {task.leave_application.id} - {task.task_type}',
                message=f"""Escalation: Your leave task has exceeded its SLA of {task.escalation_threshold.days} days.
Please escalate the issue to a higher authority.""",
                from_email='noreply@yourdomain.com',
                recipient_list=[task.leave_application.user.email],
                fail_silently=False
            )
            task.escalated = True
            task.save()