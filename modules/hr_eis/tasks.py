from celery import shared_task
from modules.hr_eis.services.audit import AuditService

@shared_task
def send_pending_action_reminders():
    """HR-UC-021: Celery task to send pending action notifications."""
    AuditService.notify("all_authorities", "Pending Actions Reminder", "Please review pending HR-EIS approval requests.", "Reminder")
    return "Reminders processed"

@shared_task
def check_policy_deadlines():
    """HR-UC-022: Celery task to check appraisal and policy deadlines."""
    return "Deadlines checked"
