"""Notification delivery (PC-BR-021).

The properties that matter: a broken mail server never fails a business write,
nothing is sent twice however often the worker runs, a permanently-bad address
stops being retried, and a broadcast is one row that fans out at send time.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from conftest import make_session
from fusion_auth.client import UserRef
from modules.placement.models import (
    NotificationOutbox,
    PlacementPolicy,
    PlacementRegistration,
    StudentProfile,
)
from modules.placement.services import notifications

pytestmark = pytest.mark.django_db


def queue(**over):
    body = {
        "topic": "offer.issued", "dedupe_key": "k1", "subject": "Subject",
        "body": "Body", "recipient_email": "a@example.test",
    }
    body.update(over)
    return notifications.enqueue(**body)


class TestDelivery:

    def test_a_pending_row_is_sent_once(self):
        queue()
        assert notifications.deliver_pending().sent == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Subject"

        # Re-running must not re-send. This is the property that makes the
        # worker safe on a cron with overlapping runs.
        assert notifications.deliver_pending().sent == 0
        assert len(mail.outbox) == 1

    def test_the_row_records_when_it_was_sent(self):
        queue()
        notifications.deliver_pending()
        row = NotificationOutbox.objects.get()
        assert row.status == "sent"
        assert row.sent_at is not None
        assert row.attempts == 1

    def test_enqueue_is_idempotent_on_the_dedupe_key(self):
        assert queue() is not None
        assert queue() is None
        assert NotificationOutbox.objects.count() == 1

    def test_an_unknown_topic_is_a_programming_error(self):
        with pytest.raises(ValueError):
            notifications.enqueue(topic="not.a.topic", dedupe_key="x",
                                  subject="s", body="b",
                                  recipient_email="a@b.test")

    def test_a_notification_needs_a_recipient(self):
        with pytest.raises(ValueError):
            notifications.enqueue(topic="offer.issued", dedupe_key="x",
                                  subject="s", body="b")


class TestFailureHandling:

    def test_a_send_failure_is_recorded_and_retried(self, monkeypatch):
        queue()
        monkeypatch.setattr(notifications, "send_mail",
                            lambda **kw: (_ for _ in ()).throw(OSError("smtp down")))
        report = notifications.deliver_pending()
        assert report.failed == 1

        row = NotificationOutbox.objects.get()
        assert row.status == "pending"          # still queued for another go
        assert row.attempts == 1
        assert "smtp down" in row.last_error

    def test_backoff_defers_the_next_attempt(self, monkeypatch):
        queue()
        monkeypatch.setattr(notifications, "send_mail",
                            lambda **kw: (_ for _ in ()).throw(OSError("nope")))
        notifications.deliver_pending()
        # Immediately again: the row is skipped rather than hammered.
        assert notifications.deliver_pending().deferred == 1

    def test_it_gives_up_after_the_attempt_ceiling(self, monkeypatch, settings):
        settings.NOTIFY_MAX_ATTEMPTS = 2
        queue()
        monkeypatch.setattr(notifications, "send_mail",
                            lambda **kw: (_ for _ in ()).throw(OSError("nope")))
        notifications.deliver_pending()
        NotificationOutbox.objects.update(
            updated_at=timezone.now() - timedelta(hours=1))
        notifications.deliver_pending()

        row = NotificationOutbox.objects.get()
        assert row.status == "failed"
        # Parked, not deleted — someone has to be able to see what went wrong.
        assert "nope" in row.last_error

    def test_a_recipient_with_no_address_fails_rather_than_sending_nowhere(self):
        notifications.enqueue(topic="offer.issued", dedupe_key="k",
                              recipient_user_id=999999, subject="s", body="b")
        assert notifications.deliver_pending().failed == 1
        assert len(mail.outbox) == 0

    def test_retry_failed_requeues(self, monkeypatch, settings):
        settings.NOTIFY_MAX_ATTEMPTS = 1
        queue()
        monkeypatch.setattr(notifications, "send_mail",
                            lambda **kw: (_ for _ in ()).throw(OSError("x")))
        notifications.deliver_pending()
        assert NotificationOutbox.objects.get().status == "failed"

        NotificationOutbox.objects.filter(status="failed").update(
            status="pending", attempts=0)
        monkeypatch.undo()
        assert notifications.deliver_pending().sent == 1


class TestAddressResolution:

    def test_an_address_is_resolved_from_the_directory(self, stub_iam):
        stub_iam(make_session(), users={
            4242: UserRef(user_id=4242, username="u4242", display_name="Asha",
                          kind="student", email="asha@iiitdmj.ac.in")})
        notifications.enqueue(topic="offer.issued", dedupe_key="k",
                              recipient_user_id=4242, subject="s", body="b")
        assert notifications.deliver_pending().sent == 1
        assert mail.outbox[0].to == ["asha@iiitdmj.ac.in"]

    def test_the_directory_is_asked_once_for_the_whole_run(self, stub_iam):
        fake = stub_iam(make_session(), users={
            uid: UserRef(user_id=uid, username=f"u{uid}", display_name="X",
                         kind="student", email=f"u{uid}@test.invalid")
            for uid in range(5000, 5010)})
        for uid in range(5000, 5010):
            notifications.enqueue(topic="offer.issued", dedupe_key=f"k{uid}",
                                  recipient_user_id=uid, subject="s", body="b")
        notifications.deliver_pending()
        calls = [c for c in fake.calls if c[0] == "get_users"]
        assert len(calls) == 1, "one batched lookup, not one per notification"


class TestBroadcast:

    def test_a_broadcast_expands_to_the_audience(self):
        policy = PlacementPolicy.objects.create(season="2026-27")
        for uid in (11, 22, 33):
            PlacementRegistration.objects.create(
                policy=policy, user_id=uid, status="registered")
        notifications.enqueue(
            topic="announcement.published", dedupe_key="ann:1",
            recipient_email=notifications.BROADCAST_SENTINEL,
            subject="Drive week", body="Details",
            payload={"broadcast": True, "audience": "registered"})

        report = notifications.deliver_pending()
        assert report.expanded == 3
        per_recipient = NotificationOutbox.objects.exclude(
            recipient_email=notifications.BROADCAST_SENTINEL)
        assert set(per_recipient.values_list("recipient_user_id", flat=True)) \
            == {11, 22, 33}

    def test_expanding_twice_does_not_duplicate(self):
        policy = PlacementPolicy.objects.create(season="2026-27")
        PlacementRegistration.objects.create(policy=policy, user_id=11,
                                             status="registered")
        notifications.enqueue(
            topic="announcement.published", dedupe_key="ann:1",
            recipient_email=notifications.BROADCAST_SENTINEL,
            subject="s", body="b", payload={"audience": "registered"})
        notifications.deliver_pending()
        n = NotificationOutbox.objects.count()
        notifications.deliver_pending()
        assert NotificationOutbox.objects.count() == n

    def test_a_profile_holder_counts_as_a_student_audience(self):
        StudentProfile.objects.create(user_id=77)
        notifications.enqueue(
            topic="posting.published", dedupe_key="p:1",
            recipient_email=notifications.BROADCAST_SENTINEL,
            subject="s", body="b", payload={"audience": "students"})
        assert notifications.deliver_pending().expanded == 1

    def test_an_empty_audience_is_not_an_error(self):
        notifications.enqueue(
            topic="posting.published", dedupe_key="p:1",
            recipient_email=notifications.BROADCAST_SENTINEL,
            subject="s", body="b", payload={"audience": "registered"})
        report = notifications.deliver_pending()
        assert report.expanded == 0
        assert NotificationOutbox.objects.get().status == "sent"


class TestVolumeGuards:

    def test_a_run_is_capped(self, settings):
        settings.NOTIFY_MAX_PER_RUN = 3
        for i in range(10):
            queue(dedupe_key=f"k{i}", recipient_email=f"u{i}@test.invalid")
        assert notifications.deliver_pending().sent == 3
        assert NotificationOutbox.objects.filter(status="pending").count() == 7

    def test_a_recipient_is_not_mailed_more_than_the_daily_cap(self, settings):
        settings.NOTIFY_DAILY_CAP_PER_RECIPIENT = 2
        for i in range(4):
            NotificationOutbox.objects.create(
                topic="offer.issued", dedupe_key=f"k{i}", recipient_user_id=8,
                recipient_email="s@test.invalid", subject="s", body="b")
        report = notifications.deliver_pending()
        assert report.sent == 2
        assert report.skipped_capped == 2
        # Suppressed, not failed: the decision was right, the volume was not.
        assert NotificationOutbox.objects.filter(status="suppressed").count() == 2


class TestConcurrentDrains:
    """Two workers draining at once must not send the same row twice.

    Latent until the beat schedule existed: nothing ran the task, so the drains
    never overlapped. A 60-second beat with a 270-second time limit makes
    overlap the normal case.
    """

    def test_a_row_is_claimed_before_it_is_sent(self):
        """The claim is a conditional UPDATE, so the loser sees zero rows
        affected and skips — rather than both sending and both marking sent."""
        row = notifications.enqueue(
            topic="offer.issued", dedupe_key="race:1",
            recipient_email="a@test.invalid", subject="s", body="b")

        assert notifications._claim(row) is True
        # A second worker holding the same in-memory row loses the race.
        assert notifications._claim(row) is False

        row.refresh_from_db()
        assert row.status == "sending"

    def test_a_claimed_row_is_not_picked_up_by_the_next_pass(self, mailoutbox):
        notifications.enqueue(
            topic="offer.issued", dedupe_key="race:2",
            recipient_email="b@test.invalid", subject="s", body="b")
        NotificationOutbox.objects.update(status="sending",
                                          claimed_at=timezone.now())

        notifications.deliver_pending()

        assert len(mailoutbox) == 0

    def test_a_row_stranded_by_a_dead_worker_is_reclaimed(self, mailoutbox):
        """A worker that dies between claiming and sending must not park the
        notification forever."""
        notifications.enqueue(
            topic="offer.issued", dedupe_key="race:3",
            recipient_email="c@test.invalid", subject="s", body="b")
        stranded = timezone.now() - notifications.CLAIM_TIMEOUT - timedelta(minutes=1)
        NotificationOutbox.objects.update(status="sending", claimed_at=stranded)

        notifications.deliver_pending()

        assert len(mailoutbox) == 1
        assert NotificationOutbox.objects.get().status == "sent"

    def test_a_retryable_failure_returns_the_row_to_the_queue(self, settings):
        """Not left in `sending`, or every transient bounce would wait out the
        reclaim window before being retried."""
        settings.NOTIFY_MAX_ATTEMPTS = 3
        notifications.enqueue(
            topic="offer.issued", dedupe_key="race:4",
            recipient_email="d@test.invalid", subject="s", body="b")

        with patch("modules.placement.services.notifications.send_mail",
                   side_effect=OSError("smtp down")):
            notifications.deliver_pending()

        row = NotificationOutbox.objects.get()
        assert row.status == "pending"
        assert row.claimed_at is None
        assert row.attempts == 1
