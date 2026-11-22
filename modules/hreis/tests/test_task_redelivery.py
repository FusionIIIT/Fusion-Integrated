"""Celery entrypoints and the merged schedule preserve exactly-once persisted effects."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from time import sleep
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone

from modules.hreis import tasks
from modules.hreis.models import (
    ApprovalRouteStep,
    HRPolicyVersion,
    HRRequest,
    Notification,
    OutboxEvent,
)

pytestmark = pytest.mark.django_db(transaction=True)


def pending():
    now = timezone.now()
    policy = HRPolicyVersion.objects.create(
        family="leave",
        version=1,
        effective_from=now - timedelta(days=1),
        parameters={
            "conditions": {
                "pending_reminder_after_hours": 1,
                "reminder_recipients": {"Registrar": [200]},
            }
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    row = HRRequest.objects.create(
        user_id=10, family="leave", state="pending_authority", policy_version=policy
    )
    ApprovalRouteStep.objects.create(
        request=row, position=0, designation="Registrar", policy_version_label="synthetic"
    )
    HRRequest.objects.filter(pk=row.pk).update(updated_at=now - timedelta(hours=2))


@pytest.mark.parametrize("entrypoint", ["generate", "deliver"])
@pytest.mark.parametrize("mode", ["sequential", "concurrent"])
def test_task_entrypoints_are_idempotent_sequentially_and_concurrently(
    stub_iam, user_ref, entrypoint, mode
):
    pending()
    stub_iam(
        None, users={200: replace(user_ref(200, kind="staff"), email="synthetic@example.invalid")}
    )
    if entrypoint == "deliver":
        tasks.generate_notifications.run()
    task = tasks.generate_notifications if entrypoint == "generate" else tasks.deliver_notifications
    gate = Barrier(2)

    def invoke(_index):
        close_old_connections()
        try:
            gate.wait(timeout=15)
            return task.run()
        finally:
            close_old_connections()

    def accepted_mail(*args, **kwargs):
        if mode == "concurrent":
            sleep(0.15)
        return 1

    with patch("modules.hreis.services.notifications.send_mail", side_effect=accepted_mail) as mail:
        if mode == "concurrent":
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(invoke, (0, 1)))
        else:
            results = [task.run(), task.run()]
    assert Notification.objects.count() == OutboxEvent.objects.count() == 1
    metric = "pending" if entrypoint == "generate" else "sent"
    assert sum(result[metric] for result in results) == 1
    assert mail.call_count == int(entrypoint == "deliver")
    assert OutboxEvent.objects.filter(dispatched_at__isnull=False).count() == int(
        entrypoint == "deliver"
    )


def test_configured_entries_are_present_in_the_actual_merged_celery_schedule(monkeypatch):
    from config import celery as configuration
    from modules.hreis import schedule

    try:
        with monkeypatch.context() as environment:
            environment.setenv("HREIS_REMINDER_POLL_MINUTES", "5")
            environment.setenv("HREIS_DELIVERY_POLL_MINUTES", "10")
            importlib.reload(schedule)
            importlib.reload(configuration)
            for name, entry in schedule.BEAT_SCHEDULE.items():
                assert configuration.app.conf.beat_schedule[name] == entry
                assert configuration.app.conf.task_routes[entry["task"]] == {
                    "queue": "notifications"
                }
            assert len(schedule.BEAT_SCHEDULE) == 2
    finally:
        importlib.reload(schedule)
        importlib.reload(configuration)
