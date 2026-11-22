"""PMS outbox claims and IAM recipient resolution."""

from types import SimpleNamespace

import pytest

from modules.pms.services import enqueue_notification, send_pending_notifications

pytestmark = pytest.mark.django_db


def test_user_notifications_resolve_real_email_and_are_not_redelivered(monkeypatch):
    enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:test:directory-delivery",
        subject="Deliver to IAM user",
        body="Hello",
        recipient_user_id=1001,
    )
    deliveries = []
    monkeypatch.setattr(
        "modules.pms.services.notifications.directory.get_users",
        lambda user_ids: {1001: SimpleNamespace(email="applicant@example.test")},
    )
    monkeypatch.setattr(
        "modules.pms.services.notifications.send_mail",
        lambda **kwargs: deliveries.append(kwargs),
    )

    assert send_pending_notifications() == 1
    assert send_pending_notifications() == 0
    assert len(deliveries) == 1
    assert deliveries[0]["recipient_list"] == ["applicant@example.test"]
