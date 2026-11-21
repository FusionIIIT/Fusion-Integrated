"""Concurrent notification enqueueing creates only one outbox effect."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from modules.pms.models import PmsNotificationOutbox
from modules.pms.services import enqueue_notification


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_notification_enqueue_creates_one_outbox_row():
    barrier = Barrier(2)

    def enqueue_at_same_time():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return enqueue_notification(
                topic="application.submitted",
                dedupe_key="pms:concurrency:one-notification",
                subject="Application submitted",
                body="A test application was submitted.",
                recipient_email="applicant@example.test",
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: enqueue_at_same_time(), range(2)))

    assert sum(result is not None for result in results) == 1
    assert PmsNotificationOutbox.objects.filter(
        dedupe_key="pms:concurrency:one-notification"
    ).count() == 1
