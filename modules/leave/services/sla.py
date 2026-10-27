from django.utils import timezone
from .models import LeaveApplication, NotificationType
from ..notifications.services import enqueue_notification

def process_sla_reminders_and_escalations() -> dict:
    reminder_threshold = timezone.now() - timezone.timedelta(hours=48)
    escalation_threshold = timezone.now() - timezone.timedelta(hours=96)

    reminders_issued = 0
    escalations_issued = 0

    pending_applications = LeaveApplication.objects.filter(status='pending')

    for application in pending_applications:
        if application.created_at < reminder_threshold and not application.reminder_sent:
            enqueue_notification(application.employee, NotificationType.REMINDER)
            reminders_issued += 1
            application.reminder_sent = True
            application.save()

        if application.created_at < escalation_threshold and not application.escalation_sent:
            enqueue_notification(application.employee, NotificationType.ESCALATION)
            escalations_issued += 1
            application.escalation_sent = True
            application.save()

    return {
        'reminders_issued': reminders_issued,
        'escalations_issued': escalations_issued,
    }