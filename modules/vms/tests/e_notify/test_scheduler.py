"""Reminder and expiry (UC-037, UC-040, BR-062, BW-VMS-03)."""
from datetime import timedelta

import pytest
from freezegun import freeze_time

from modules.vms.models import AuditLog, Notification, VisitRequest
from modules.vms.services import delivery, scheduler_work
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db

T0 = "2026-06-01 09:00:00+00:00"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    class U:
        email = "host@example.com"
    monkeypatch.setattr(delivery.directory, "get_users", lambda ids: {i: U() for i in ids})


def _setup(timeout=24, reminder=12, **req):
    from django.utils import timezone
    f.make_published_policy(version=1, approval_timeout_hours=timeout,
                            reminder_after_hours=reminder,
                            published_at=timezone.now() - timedelta(days=1))
    return f.make_visit_request(**req)


def test_br_062_pending_expires_after_timeout():
    with freeze_time(T0):
        req = _setup()
    with freeze_time("2026-06-02 08:59:00+00:00"):
        assert scheduler_work.expire_pending() == 0
    with freeze_time("2026-06-02 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 1
    req.refresh_from_db()
    assert req.status == "expired"
    log = AuditLog.objects.get(action="vms.request.expired")
    assert log.actor_role == "system" and log.actor_user_id is None
    topics = Notification.objects.filter(topic="request.expired")
    assert topics.filter(recipient_visitor=req.visitor).count() == 2
    assert topics.filter(recipient_user_id=req.host_user_id).count() == 2


def test_expiry_idempotent():
    with freeze_time(T0):
        _setup()
    with freeze_time("2026-06-03 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 1
        assert scheduler_work.expire_pending() == 0
    assert Notification.objects.filter(topic="request.expired").count() == 4
    assert AuditLog.objects.filter(action="vms.request.expired").count() == 1


def test_expiry_uses_policy_snapshot_not_current():
    from django.utils import timezone
    with freeze_time(T0):
        req = _setup(timeout=24, reminder=12)
        # A later publication halves the timeout; the request keeps its own policy.
        f.make_published_policy(version=2, approval_timeout_hours=2, reminder_after_hours=1,
                                published_at=timezone.now() + timedelta(hours=1))
    with freeze_time("2026-06-01 20:00:00+00:00"):
        assert scheduler_work.expire_pending() == 0
    req.refresh_from_db()
    assert req.status == "pending"


def test_explicit_expires_at_wins():
    with freeze_time(T0):
        from django.utils import timezone
        req = _setup(expires_at=timezone.now() + timedelta(hours=3))
    with freeze_time("2026-06-01 12:00:00+00:00"):
        assert scheduler_work.expire_pending() == 1
    req.refresh_from_db()
    assert req.status == "expired"


def test_only_waiting_requests_expire():
    with freeze_time(T0):
        a = _setup(status="approved")
        b = f.make_visit_request(status="awaiting_admin", source="walk_in")
    with freeze_time("2026-06-09 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 0
    a.refresh_from_db(), b.refresh_from_db()
    assert (a.status, b.status) == ("approved", "awaiting_admin")


def test_urgent_request_awaiting_admin_expires():     # service request e-1
    with freeze_time(T0):
        req = _setup(status="awaiting_admin", is_urgent=True)
    with freeze_time("2026-06-01 20:00:00+00:00"):
        assert scheduler_work.expire_pending() == 0     # inside the 24 h window
    with freeze_time("2026-06-02 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 1
        assert scheduler_work.expire_pending() == 0     # idempotent
    req.refresh_from_db()
    assert req.status == "expired" and req.decided_at is not None
    assert Notification.objects.filter(topic="request.expired").count() == 4


def test_reminder_sent_once():
    with freeze_time(T0):
        req = _setup()
    with freeze_time("2026-06-01 20:59:00+00:00"):
        assert scheduler_work.send_reminders() == 0
    with freeze_time("2026-06-01 21:00:00+00:00"):
        assert scheduler_work.send_reminders() == 1
        assert scheduler_work.send_reminders() == 0
    req.refresh_from_db()
    assert req.reminded_at is not None
    assert Notification.objects.filter(topic="request.reminder",
                                       recipient_user_id=req.host_user_id).count() == 2


def test_no_reminder_for_decided_request():
    with freeze_time(T0):
        _setup(status="approved")
    with freeze_time("2026-06-01 22:00:00+00:00"):
        assert scheduler_work.send_reminders() == 0


def test_bw_vms_03_timeline():
    """Submit -> +12 h reminder -> +24 h expired."""
    with freeze_time(T0):
        req = _setup()
        scheduler_work.expire_pending()
        scheduler_work.send_reminders()
        delivery.deliver_pending()
        assert VisitRequest.objects.get(pk=req.pk).status == "pending"
        assert not Notification.objects.filter(topic__startswith="request.").exists()
    with freeze_time("2026-06-01 21:00:00+00:00"):
        scheduler_work.expire_pending()
        scheduler_work.send_reminders()
        delivery.deliver_pending()
        req.refresh_from_db()
        assert req.status == "pending" and req.reminded_at
        assert Notification.objects.filter(topic="request.reminder", status="sent").count() == 2
        assert not Notification.objects.filter(topic="request.expired").exists()
    with freeze_time("2026-06-02 09:00:00+00:00"):
        scheduler_work.expire_pending()
        scheduler_work.send_reminders()
        delivery.deliver_pending()
        req.refresh_from_db()
        assert req.status == "expired"
        assert Notification.objects.filter(topic="request.reminder").count() == 2
        assert Notification.objects.filter(topic="request.expired", status="sent").count() == 4
        assert AuditLog.objects.filter(action="vms.request.expired",
                                       entity_id=str(req.pk)).count() == 1


def test_beat_schedule_merged_by_p0_schedule():
    from modules.vms import schedule
    beat = {v["task"]: v["schedule"] for v in schedule.BEAT_SCHEDULE.values()}
    assert beat["vms.deliver_notifications"] == 60.0
    assert beat["vms.send_reminders"] == 300.0 and beat["vms.expire_pending"] == 300.0
    assert schedule.TASK_ROUTES["vms.deliver_notifications"] == {"queue": "notifications"}


def test_tasks_run_and_are_registered():
    from modules.vms.jobs import notifications as jobs
    f.make_notification()
    assert "sent=1" in jobs.deliver_notifications()
    assert jobs.send_reminders() == 0 and jobs.expire_pending() == 0
