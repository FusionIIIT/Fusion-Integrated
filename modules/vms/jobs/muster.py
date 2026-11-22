"""Lane F job: flag an emergency muster that has stayed open too long.

Declares the beat entry only; model-touching imports live in the task body.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.vms.jobs")

TASK_ROUTES: dict = {}

BEAT_SCHEDULE = {
    "vms-muster-stale-check": {"task": "vms.muster_stale_check", "schedule": 1800.0},
}


@shared_task(name="vms.muster_stale_check", acks_late=True, soft_time_limit=120, time_limit=150)
def muster_stale_check() -> int:
    from modules.vms.services import muster

    n = muster.stale_check()
    if n:
        log.warning("vms.muster.stale alerts=%d", n)
    return n
