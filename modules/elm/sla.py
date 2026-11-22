from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import LeaveEvent, LeavePolicy, LeaveRequest


def process_sla(pk, now=None):
    if now is None:
        now = timezone.now()
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().filter(pk=pk).first()
        if not req or req.status != "PENDING":
            return []

        assignment = (
            req.events.filter(action="TASK_ASSIGNED").order_by("-created_at", "-id").first()
        )
        if not assignment:
            return []

        if req.substitute_status == "DECLINED":
            return []
        recipient = assignment.details.get("recipient")
        if not isinstance(recipient, int) or recipient <= 0:
            return []

        policies = LeavePolicy.objects.filter(type=req.leave_type).distinct()
        if not policies.exists():
            reminder_hours = 24
            escalation_hours = 48
        else:
            if policies.count() > 1:
                raise ValidationError("Duplicate LeavePolicy entries found")
            policy = policies.first()
            reminder_hours = policy.reminder_hours
            escalation_hours = policy.escalation_hours

        if reminder_hours <= 0 or escalation_hours <= 0:
            raise ValidationError("Invalid thresholds")

        if escalation_hours <= reminder_hours:
            raise ValidationError("Escalation hours must be greater than reminder hours")

        age = (now - assignment.created_at).total_seconds() / 3600
        created_events = []

        if age >= reminder_hours:
            action = "SLA_REMINDER"
            if not req.events.filter(action=action, details__assignment_id=assignment.pk).exists():
                details = {
                    "assignment_id": assignment.pk,
                    "recipient": recipient,
                    "step": req.step,
                }
                LeaveEvent.objects.create(
                    request=req, employee=req.employee, action=action, details=details
                )
                created_events.append(action)

        if age >= escalation_hours:
            action = "SLA_ESCALATED"
            if not req.events.filter(action=action, details__assignment_id=assignment.pk).exists():
                req.route[-1] if req.route else None
                escalated_recipient = None

                if req.status == "PENDING":
                    if req.substitute_status == "PENDING" and recipient == req.substitute:
                        escalated_recipient = req.route[0] if req.route else None
                    elif recipient in req.route and recipient != req.route[-1]:
                        escalated_recipient = req.route[-1]
                else:
                    if recipient in req.route and recipient != req.route[-1]:
                        escalated_recipient = req.route[-1]

                if escalated_recipient is not None:
                    details = {
                        "assignment_id": assignment.pk,
                        "recipient": escalated_recipient,
                        "step": req.step,
                    }
                    LeaveEvent.objects.create(
                        request=req, employee=req.employee, action=action, details=details
                    )
                    created_events.append(action)

        return created_events
