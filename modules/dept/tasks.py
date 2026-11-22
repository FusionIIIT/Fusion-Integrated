"""Celery tasks for the Department module."""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.dept.tasks")


@shared_task(
    name="dept.evaluate_role_transitions",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def evaluate_role_transitions_task() -> str:
    """Evaluate role assignments: activate scheduled tenures and expire ended tenures."""
    from modules.dept.services.roles import evaluate_role_transitions

    count = evaluate_role_transitions()
    log.info("dept.evaluate_role_transitions count=%d", count)
    return f"Processed {count} transitions"
