"""Celery entrypoints match hreis.schedule and can be called manually."""

from celery import shared_task

from modules.hreis.services import notifications


@shared_task(name="hreis.generate_notifications")
def generate_notifications():
    return {
        "pending": notifications.create_pending_action_reminders(),
        "policy": notifications.create_policy_deadline_notifications(),
    }


@shared_task(name="hreis.deliver_notifications")
def deliver_notifications():
    sent, failed = notifications.deliver_pending_notifications()
    return {"sent": sent, "failed": failed}
