import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveRequest
from modules.elm.sla import process_sla


class Command(BaseCommand):
    help = "Process pending leave requests for SLA compliance"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        pending_requests = (
            LeaveRequest.objects.filter(status="PENDING").values_list("pk", flat=True).iterator()
        )
        events = 0
        errors = []

        for pk in pending_requests:
            try:
                result = process_sla(pk, now=now)
                events += len(result)
            except ValidationError as exc:
                errors.append({"request": pk, "error": str(exc.detail)})

        self.stdout.write(json.dumps({"events": events, "exceptions": errors}))
