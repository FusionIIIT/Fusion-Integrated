"""Lane I jobs (D-11): auto check-out every 5 minutes, unused-pass expiry hourly.
Model-touching imports live inside the task bodies."""
from __future__ import annotations

from celery import shared_task

TASK_ROUTES: dict = {}

BEAT_SCHEDULE = {
    "vms-auto-checkout-sweep": {"task": "vms.auto_checkout_sweep", "schedule": 300.0},
    "vms-expire-unused-passes": {"task": "vms.expire_unused_passes", "schedule": 3600.0},
}

_OPTS = {"acks_late": True, "reject_on_worker_lost": True,
         "soft_time_limit": 270, "time_limit": 300}


@shared_task(name="vms.auto_checkout_sweep", **_OPTS)
def auto_checkout_sweep() -> int:
    from modules.vms.services import autocheckout

    return autocheckout.sweep()


@shared_task(name="vms.expire_unused_passes", **_OPTS)
def expire_unused_passes() -> int:
    from modules.vms.services import autocheckout

    return autocheckout.expire_unused_passes()
