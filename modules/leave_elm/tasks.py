"""Celery tasks for scheduled operations."""
from celery import shared_task
from datetime import date
from modules.leave_elm.services.leave import _process_year_end, _process_sla_task
from modules.leave_elm.models import WorkflowTask

@shared_task
def process_year_end_leave_accounts():
    """Process year-end leave accounts."""
    user_id = 1000  # Admin user ID
    result = _process_year_end(user_id)
    return result

@shared_task
def check_sla_tasks():
    """Check SLA thresholds for pending tasks."""
    tasks = WorkflowTask.objects.filter(status='PENDING')
    for task in tasks:
        _process_sla_task(task.id, 'REMINDER')
        _process_sla_task(task.id, 'ESCALATION')

BEAT_SCHEDULE = [
    {'task': 'check_sla_tasks', 'schedule': 3600.0},  # Every hour
    {'task': 'process_year_end_leave_accounts', 'schedule': 86400.0},  # Daily
]
