"""Create one-time in-app reminders and escalation notifications for pending tasks."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.elm.models import ELMNotification, LeaveEvent, WorkflowTask

PROCESS_PERMISSION = "elm.system.process"


class Command(BaseCommand):
    help = "Notify assigned users and escalation contacts for overdue pending ELM tasks."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        reminded = escalated = 0
        rows = (
            WorkflowTask.objects.select_for_update(of=("self",))
            .filter(status="pending")
            .select_related("request")
        )
        for task in rows:
            if task.request_id is None:
                continue
            if task.reminder_after_hours and task.reminded_at is None:
                due = task.assigned_at + timedelta(hours=task.reminder_after_hours)
                if due <= now:
                    ELMNotification.objects.create(
                        user_id=task.assigned_to_user_id,
                        request=task.request,
                        kind="sla_reminder",
                        title="Leave task needs attention",
                        body="Your assigned leave task is still pending.",
                        payload={"task_id": task.pk, "due_at": due.isoformat()},
                    )
                    task.reminded_at = now
                    LeaveEvent.objects.create(
                        request=task.request,
                        from_status=task.request.status,
                        to_status=task.request.status,
                        event_type="sla_reminder",
                        data={"task_id": task.pk, "assigned_to_user_id": task.assigned_to_user_id},
                    )
                    reminded += 1
            if (
                task.escalation_after_hours
                and task.escalated_at is None
                and task.escalation_user_id
            ):
                due = task.assigned_at + timedelta(hours=task.escalation_after_hours)
                if due <= now:
                    ELMNotification.objects.create(
                        user_id=task.escalation_user_id,
                        request=task.request,
                        kind="sla_escalation",
                        title="Leave task escalated",
                        body="An assigned leave task is overdue.",
                        payload={
                            "task_id": task.pk,
                            "assigned_to_user_id": task.assigned_to_user_id,
                            "due_at": due.isoformat(),
                        },
                    )
                    task.escalated_at = now
                    LeaveEvent.objects.create(
                        request=task.request,
                        from_status=task.request.status,
                        to_status=task.request.status,
                        event_type="sla_escalated",
                        data={"task_id": task.pk, "escalation_user_id": task.escalation_user_id},
                    )
                    escalated += 1
            if task.reminded_at or task.escalated_at:
                task.save(update_fields=["reminded_at", "escalated_at", "updated_at"])
        self.stdout.write(f"Created {reminded} reminder(s) and {escalated} escalation(s).")
