"""The outbox drain (AFR-GYM-013, AFR-GYM-015, AFR-GYM-025): once, even twice at once."""
import threading
from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.gymkhana.models import NotificationOutbox, Poll, PollTarget
from modules.gymkhana.services import notifications as n
from modules.gymkhana.tasks import deliver_notifications
from modules.gymkhana.tests.conftest import COORD, PLAIN, make_club, people

API = "/api/v1/gymkhana"


@pytest.fixture
def fake(stub_iam):
    return stub_iam(users=people())


def queue_one(uid=PLAIN, key="k1"):
    return n.enqueue(topic=n.SESSION_BOOKED, dedupe_key=key, subject="s", body="b",
                     recipient_user_id=uid)


@pytest.mark.django_db
def test_a_pending_row_is_sent_once_when_run_twice(fake):
    queue_one()
    deliver_notifications()
    deliver_notifications()
    assert len(mail.outbox) == 1
    assert NotificationOutbox.objects.get().status == "sent"


@pytest.mark.django_db
def test_a_duplicate_key_is_queued_once():
    assert queue_one() is not None
    assert queue_one() is None
    assert NotificationOutbox.objects.count() == 1


@pytest.mark.django_db
def test_unknown_topic_and_missing_recipient_are_programming_errors():
    with pytest.raises(ValueError):
        n.enqueue(topic="x", dedupe_key="a", subject="s", body="b", recipient_user_id=1)
    with pytest.raises(ValueError):
        n.enqueue(topic=n.POLL_CREATED, dedupe_key="a", subject="s", body="b")
    with pytest.raises(ValueError):
        n.enqueue_to_users(topic="x", key="a", subject="s", body="b", user_ids=[1])


@pytest.mark.django_db(transaction=True)
def test_two_drains_at_once_send_once(fake):
    for i in range(5):
        queue_one(key=f"k{i}")
    barrier = threading.Barrier(2)

    def run():
        barrier.wait()
        try:
            n.deliver_pending()
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(mail.outbox) == 5


@pytest.mark.django_db
def test_no_address_fails_and_gives_up_after_the_attempt_cap(fake):
    row = queue_one(uid=424242)
    for _ in range(n.MAX_ATTEMPTS):
        NotificationOutbox.objects.filter(pk=row.pk).update(
            updated_at=timezone.now() - timedelta(days=1))
        n.deliver_pending()
    row.refresh_from_db()
    assert row.status == "failed" and row.attempts == n.MAX_ATTEMPTS


@pytest.mark.django_db
def test_a_backoff_defers_a_recently_failed_row(fake):
    row = queue_one()
    NotificationOutbox.objects.filter(pk=row.pk).update(attempts=2)
    assert n.deliver_pending().deferred == 1


@pytest.mark.django_db
def test_a_mail_failure_is_recorded_and_retried(fake):
    queue_one()
    with mock.patch("modules.gymkhana.services.notifications.send_mail",
                    side_effect=OSError("smtp down")):
        assert n.deliver_pending().failed == 1
    row = NotificationOutbox.objects.get()
    assert row.status == "pending" and "smtp down" in row.last_error


@pytest.mark.django_db
def test_a_stranded_claim_is_returned_to_the_queue(fake):
    row = queue_one()
    NotificationOutbox.objects.filter(pk=row.pk).update(
        status="sending", claimed_at=timezone.now() - timedelta(hours=1))
    n.deliver_pending()
    assert NotificationOutbox.objects.get().status == "sent"


@pytest.mark.django_db
def test_a_claim_lost_to_another_worker_is_deferred(fake):
    queue_one()
    with mock.patch.object(n, "_claim", return_value=False):
        assert n.deliver_pending().deferred == 1


def _poll():
    club = make_club()
    poll = Poll.objects.create(club=club, title="t", description="d",
                               expires_on=timezone.localdate(), created_by_user_id=COORD)
    PollTarget.objects.create(poll=poll, batch_year=2023, discipline="CSE")
    PollTarget.objects.create(poll=poll, batch_year=2024, discipline="")
    n.enqueue(topic=n.POLL_CREATED, dedupe_key=f"poll.created:{poll.pk}", subject="s",
              body="b", is_broadcast=True, payload={"poll_id": poll.pk})
    return poll


@pytest.mark.django_db
def test_br_gym_013_a_poll_broadcast_reaches_its_cohorts_once(fake):
    poll = _poll()
    fake.directory = {"count": 2, "results": [{"user_id": PLAIN}, {"user_id": 1003}]}
    n.deliver_pending()
    n.deliver_pending()
    rows = NotificationOutbox.objects.filter(is_broadcast=False)
    assert sorted(rows.values_list("recipient_user_id", flat=True)) == [1003, PLAIN]
    calls = [dict(c[1]) for c in fake.calls if c[0] == "academic_directory"]
    assert {(c["batch_year"], c["discipline"]) for c in calls} == {(2023, "CSE"), (2024, "")}
    assert NotificationOutbox.objects.get(is_broadcast=True, payload__poll_id=poll.pk) \
        .status == "sent"


@pytest.mark.django_db
def test_a_broadcast_waits_when_the_directory_is_down(fake):
    _poll()
    fake.directory_error = IamUnavailable("down")
    assert n.deliver_pending().failed == 1
    assert NotificationOutbox.objects.get(is_broadcast=True).status == "pending"
    assert not NotificationOutbox.objects.filter(is_broadcast=False).exists()


@pytest.mark.django_db
def test_a_broadcast_claimed_elsewhere_is_left_alone(fake):
    _poll()
    with mock.patch.object(n, "_claim", return_value=False):
        assert n.deliver_pending().deferred >= 1


def test_the_report_reads_as_a_sentence():
    assert str(n.DeliveryReport(sent=2)) == "expanded=0 sent=2 failed=0 deferred=0"
