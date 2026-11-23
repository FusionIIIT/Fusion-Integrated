from threading import Barrier, Thread

import pytest
from django.db import close_old_connections

from config.celery import app
from modules.phc.models import Notification, NotificationOutbox
from modules.phc.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.phc.tasks import deliver_notifications

pytestmark = pytest.mark.django_db


def test_phc_br_11_schedule_is_merged_and_notification_delivery_is_idempotent():
    assert BEAT_SCHEDULE.keys() <= app.conf.beat_schedule.keys()
    assert app.conf.task_routes["phc.deliver_notifications"] == TASK_ROUTES[
        "phc.deliver_notifications"]
    outbox = NotificationOutbox.objects.create(
        event_key="requisition:77:approved", recipient_user_id=1001,
        event_type="requisition_decision",
        payload={"target_type": "inventory_requisition", "target_id": 77,
                 "state": "approved"})

    first = deliver_notifications.run()
    second = deliver_notifications.run()
    outbox.refresh_from_db()

    assert first == 1
    assert second == 0
    assert outbox.delivered_at is not None
    assert Notification.objects.filter(outbox=outbox).count() == 1


@pytest.mark.django_db(transaction=True)
def test_phc_br_11_concurrent_notification_delivery_creates_one_notification():
    outbox = NotificationOutbox.objects.create(
        event_key="requisition:78:rejected", recipient_user_id=1001,
        event_type="requisition_decision",
        payload={"target_type": "inventory_requisition", "target_id": 78,
                 "state": "rejected"})
    barrier = Barrier(2)
    results = []

    def deliver():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            results.append(deliver_notifications.run())
        finally:
            close_old_connections()

    threads = [Thread(target=deliver) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == [0, 1]
    assert Notification.objects.filter(outbox=outbox).count() == 1
