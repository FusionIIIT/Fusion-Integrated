"""VMS Asynchronous Tasks."""

from celery import shared_task
from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.models.visits import Visit


@shared_task(name="vms.check_overstays")
def check_overstays() -> int:
    """Enforce BR-045: Checks on-site visitors past their pass expiry time."""
    now = timezone.now()
    overstayed = Visit.objects.filter(status="on_site", valid_to__lt=now)
    count = 0
    for v in overstayed:
        _alert, created = GateAlert.objects.get_or_create(
            alert_type="overstay",
            visit_id=v.id,
            status="open",
            defaults={
                "severity": "warning",
                "message": (
                    f"Visitor {v.visitor.first_name} {v.visitor.last_name} "
                    f"({v.pass_number}) has exceeded authorized departure time ({v.valid_to})."
                ),
                "visitor_id": v.visitor.id,
            },
        )
        if created:
            count += 1
    return count


@shared_task(name="vms.expire_stale_visits")
def expire_stale_visits() -> int:
    """Expires requested/approved passes whose valid_to date has elapsed."""
    now = timezone.now()
    stale = Visit.objects.filter(status__in=["requested", "approved"], valid_to__lt=now)
    return stale.update(status="expired")
