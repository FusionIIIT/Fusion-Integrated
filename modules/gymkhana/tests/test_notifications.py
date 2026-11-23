"""AFR-GYM-013, AFR-GYM-015 and AFR-GYM-025: the right students, once each."""
import datetime
import threading

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.gymkhana.domain.constants import NOTIFICATION_FAILED, NOTIFICATION_SENT
from modules.gymkhana.models import ClubMembership, GymkhanaNotification, VenueBooking
from modules.gymkhana.services import notifications
from modules.gymkhana.tasks import deliver_notifications
from modules.gymkhana.tests.support import (
    API,
    COUNCILLOR,
    HEAD,
    OTHER_STUDENT,
    STUDENT,
    make_club,
    new_poll,
    people,
    sign_in,
    slot,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def club():
    people()
    club = make_club()
    ClubMembership.objects.create(club=club, student_id=STUDENT, status="confirmed")
    ClubMembership.objects.create(club=club, student_id=OTHER_STUDENT, status="open")
    return club


def recipients():
    return sorted(address for m in mail.outbox for address in m.to)


def test_afr_gym_013_a_session_reaches_confirmed_members_only(stub_iam, club):
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    assert deliver_notifications() == 1
    assert recipients() == [f"u{STUDENT}@example.invalid"]
    assert "Hall 1" in mail.outbox[0].body


def test_afr_gym_015_an_event_reaches_confirmed_members_only(stub_iam, club):
    body = slot(club, name="Tech Talk", faculty_councillor_id=COUNCILLOR)
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/event/", body, format="json")
    assert deliver_notifications() == 1
    assert mail.outbox[0].subject == "New event: Tech Talk"


def directory_of(fake, *pages):
    """The IAM's cohort listing, one page per call, remembering what was asked."""
    asked, remaining = [], list(pages)

    def page(**filters):
        asked.append(filters)
        return remaining.pop(0)

    fake.academic_directory = page
    return asked


def test_afr_gym_025_a_poll_reaches_every_page_of_its_target_group(stub_iam, club):
    client = sign_in(stub_iam, HEAD)
    client.post(f"{API}/polls/", new_poll(club), format="json")
    fake = stub_iam()
    asked = directory_of(
        fake,
        {"count": 2, "results": [{"user_id": STUDENT, "cpi": 9}]},
        {"count": 2, "results": [{"user_id": HEAD, "cpi": 8}]},
    )
    assert deliver_notifications() == 2
    assert [(a["batch_year"], a["discipline"], a["offset"]) for a in asked] == [
        ("2024", "CSE", 0), ("2024", "CSE", 1)]
    assert recipients() == [f"u{HEAD}@example.invalid", f"u{STUDENT}@example.invalid"]


def test_br_gym_013_all_branches_asks_for_no_branch_filter(stub_iam, club):
    body = new_poll(club, target_groups=[{"batch": "2024", "branch": "all"}])
    sign_in(stub_iam, HEAD).post(f"{API}/polls/", body, format="json")
    asked = directory_of(stub_iam(), {"count": 0, "results": []})
    deliver_notifications()
    assert asked[0]["batch_year"] == "2024"
    assert "discipline" not in asked[0]


def test_nothing_is_announced_for_a_refused_booking(stub_iam, club):
    client = sign_in(stub_iam, HEAD)
    client.post(f"{API}/bookings/session/", slot(club), format="json")
    client.post(f"{API}/bookings/session/", slot(club), format="json")
    assert VenueBooking.objects.count() == GymkhanaNotification.objects.count() == 1


def test_a_failure_to_queue_undoes_the_booking(stub_iam, club, monkeypatch):
    """UC-GYM-002 exception flow: no successful booking is recorded."""
    def broken(booking):
        raise RuntimeError("queue down")

    monkeypatch.setattr("modules.gymkhana.services.bookings.announce_booking", broken)
    response = sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    assert response.status_code == 500
    assert not VenueBooking.objects.exists()


def test_delivery_twice_in_a_row_sends_once(stub_iam, club):
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    assert [deliver_notifications(), deliver_notifications()] == [1, 0]
    assert len(mail.outbox) == 1


def test_a_mail_failure_is_retried_later_then_given_up(stub_iam, club, monkeypatch, settings):
    settings.NOTIFY_MAX_ATTEMPTS = 2

    def refuse(**kwargs):
        raise OSError("mail server down")

    monkeypatch.setattr(notifications, "send_mail", refuse)
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    deliver_notifications()
    row = GymkhanaNotification.objects.get(recipient_user_id=STUDENT)
    assert (row.attempts, row.status) == (1, "pending")
    assert "mail server down" in row.last_error
    deliver_notifications()
    row.refresh_from_db()
    assert row.attempts == 1, "retried before its wait was over"
    GymkhanaNotification.objects.filter(pk=row.pk).update(
        updated_at=timezone.now() - datetime.timedelta(minutes=5))
    deliver_notifications()
    row.refresh_from_db()
    assert row.status == NOTIFICATION_FAILED


def test_an_unreachable_directory_leaves_the_announcement_queued(stub_iam, club):
    sign_in(stub_iam, HEAD).post(f"{API}/polls/", new_poll(club), format="json")
    fake = stub_iam()
    fake.directory_error = IamUnavailable("down")
    assert deliver_notifications() == 0
    row = GymkhanaNotification.objects.get()
    assert (row.status, row.attempts) == ("pending", 1)


def test_a_recipient_without_an_address_is_recorded_not_sent(stub_iam, club):
    from modules.directory.models import UserRef

    UserRef.objects.filter(user_id=STUDENT).update(email="")
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    assert deliver_notifications() == 0
    row = GymkhanaNotification.objects.get(recipient_user_id=STUDENT)
    assert "No email address" in row.last_error


def test_a_row_stranded_by_a_dead_worker_is_sent_again(stub_iam, club):
    row = GymkhanaNotification.objects.create(
        topic="session.booked", dedupe_key="k", recipient_user_id=STUDENT, subject="s", body="b",
        status="sending", claimed_at=timezone.now() - datetime.timedelta(hours=1))
    assert deliver_notifications() == 1
    row.refresh_from_db()
    assert row.status == NOTIFICATION_SENT


@pytest.mark.django_db(transaction=True)
def test_two_workers_at_once_send_one_message(stub_iam):
    people()
    club = make_club()
    ClubMembership.objects.create(club=club, student_id=STUDENT, status="confirmed")
    sign_in(stub_iam, HEAD).post(f"{API}/bookings/session/", slot(club), format="json")
    barrier, sent = threading.Barrier(4), []

    def work():
        try:
            barrier.wait()
            sent.append(deliver_notifications())
        finally:
            connection.close()

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(sent) <= 1
    deliver_notifications()
    assert len(mail.outbox) == 1
