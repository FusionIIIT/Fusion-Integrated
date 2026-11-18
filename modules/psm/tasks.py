from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from modules.psm import models as m
from modules.psm.domain.rules import TERMINAL


@shared_task(name="psm.run_reports")
def run_reports():
    from modules.psm.reporting import run_due_reports

    return run_due_reports()


@shared_task(name="psm.monitor_sla")
def monitor_sla():
    count = 0
    for pk in m.Indent.objects.exclude(status__in=["draft", *TERMINAL]).values_list(
        "pk", flat=True
    ):
        with transaction.atomic():
            obj = m.Indent.objects.select_for_update().get(pk=pk)
            if obj.status not in (
                "submitted",
                "modified",
                "stock_reserved",
                "external_required",
                "awaiting_approval",
            ):
                continue
            now = timezone.now()
            for event, key in (
                ("sla_reminder", "sla_reminder_hours"),
                ("sla_escalation", "sla_escalation_hours"),
            ):
                hours = obj.policy_snapshot.get(key)
                if hours is None or now < obj.updated_at + timedelta(hours=float(hours)):
                    continue
                recipients = {obj.requestor_id}
                recipients.update(
                    m.Membership.objects.filter(
                        role__in=["ps_admin", "final_authority"]
                    ).values_list("user_id", flat=True)
                )
                recipients.update(
                    m.Membership.objects.filter(
                        department=obj.department, role__in=["department_admin", "department_head"]
                    ).values_list("user_id", flat=True)
                )
                emitted = False
                for uid in recipients:
                    _, created = m.Notification.objects.get_or_create(
                        deduplication_key=(
                            f"{obj.pk}:{obj.version}:{obj.approval_step}:{obj.status}:{event}:{uid}"
                        ),
                        defaults={
                            "user_id": uid,
                            "indent": obj,
                            "event": event,
                            "message": (f"{obj.item}: {event.replace('_', ' ')} "
                                        f"(priority {obj.priority})"),
                        },
                    )
                    emitted |= created
                if emitted:
                    m.Audit.objects.create(
                        actor_id=0,
                        department=obj.department,
                        entity="indent",
                        object_id=obj.pk,
                        action=event,
                        snapshot={"status": obj.status},
                    )
                    count += 1
    return count
