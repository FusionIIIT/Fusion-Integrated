"""Targeted tests to exercise remaining branches and uncovered routines in modules.placement."""
import uuid
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from fusion_auth.principal import Principal
from modules.placement import tasks
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    NotificationOutbox,
    PlacementPolicy,
    PlacementRegistration,
)
from modules.placement.selectors import applications as app_selectors
from modules.placement.services import announcements as ann_service
from modules.placement.services import interviews as int_service


def _actor(uid=101, role="placement_officer", perms=()):
    return Principal(
        user_id=uid, username=f"user{uid}", display_name=f"User {uid}",
        kind="student" if role == "student" else "employee",
        active_role=role, roles=(role,) if role else (),
        permissions=frozenset(perms), modules=("placement",),
    )


@pytest.fixture
def base_setup(db):
    pol, _ = PlacementPolicy.objects.get_or_create(season="2026-27")
    comp, _ = Company.objects.get_or_create(name="TechCorp", slug="tech-corp", status="active")
    now = timezone.now()
    posting = JobPosting.objects.create(
        company=comp, title="Software Engineer", placement_year="2026-27",
        status="published", created_by_user_id=1, description="Dev role",
        closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now
    )
    reg = PlacementRegistration.objects.create(user_id=1001, policy=pol, status="registered")
    app = Application.objects.create(posting=posting, user_id=1001, status="applied")
    return pol, comp, posting, reg, app


@pytest.mark.django_db
def test_selectors_visible_applications_and_postings(base_setup):
    _pol, comp, posting, _reg, app = base_setup

    # 1. Without placement_cell.application.view permission -> filtered by user_id
    student = _actor(uid=1001, role="student", perms=[])
    qs_apps = app_selectors.visible_applications(student)
    assert qs_apps.filter(pk=app.pk).exists()

    other_student = _actor(uid=1002, role="student", perms=[])
    assert not app_selectors.visible_applications(other_student).filter(pk=app.pk).exists()

    # With staff permission
    officer = _actor(uid=2001, role="officer", perms=["placement_cell.application.view"])
    assert app_selectors.visible_applications(officer).filter(pk=app.pk).exists()

    # 2. visible_postings
    draft_posting = JobPosting.objects.create(
        company=comp, title="Intern", placement_year="2026-27",
        status="draft", created_by_user_id=1
    )
    # student sees only published
    assert app_selectors.visible_postings(student).filter(pk=posting.pk).exists()
    assert not app_selectors.visible_postings(student).filter(pk=draft_posting.pk).exists()

    # staff with permission sees drafts too
    staff = _actor(uid=2001, role="officer", perms=["placement_cell.job_posting.view"])
    assert app_selectors.visible_postings(staff).filter(pk=draft_posting.pk).exists()


@pytest.mark.django_db
def test_management_command_send_notifications(capsys):
    # Status report
    call_command("send_notifications", status=True)
    out = capsys.readouterr().out
    assert "pending" in out

    # Enqueue a row and drain
    NotificationOutbox.objects.create(
        topic="test.topic", recipient_email="student@inst.ac.in",
        subject="Hello", body="Test email", status="pending",
        dedupe_key=f"key-{uuid.uuid4()}"
    )
    call_command("send_notifications", limit=10)
    out = capsys.readouterr().out
    assert "sent" in out or "queue drained" in out

    # Retry failed
    NotificationOutbox.objects.create(
        topic="test.fail", recipient_email="fail@inst.ac.in",
        subject="Fail", body="Fail", status="failed", attempts=3,
        dedupe_key=f"key-{uuid.uuid4()}"
    )
    call_command("send_notifications", retry_failed=True)
    out = capsys.readouterr().out
    assert "Re-queued" in out


@pytest.mark.django_db
def test_announcements_service_lifecycle():
    actor = _actor(uid=10, role="placement_officer", perms=["placement_cell.announcement.publish"])

    ann = ann_service.publish(
        actor=actor, title="Placement Drive Starting",
        body="Drive begins next week.", topic="general", audience="students"
    )
    assert ann.pk is not None
    assert ann.title == "Placement Drive Starting"

    # Withdraw announcement
    withdrawn = ann_service.withdraw(
        announcement_id=ann.pk, actor=actor, reason="Rescheduled due to exams"
    )
    assert withdrawn.is_withdrawn is True
    assert withdrawn.withdrawn_reason == "Rescheduled due to exams"


@pytest.mark.django_db
def test_tasks_scheduled_workers(base_setup):
    _pol, _comp, _posting, _reg, _app = base_setup

    # Deliver notifications task
    tasks.deliver_notifications(limit=5)

    # Expire overdue offers task
    tasks.expire_overdue_offers()

    # Rebuild stats tasks
    tasks.rebuild_stats(season="2026-27")
    tasks.rebuild_active_stats()


@pytest.mark.django_db
def test_interviews_service_schedule_round(base_setup):
    _pol, _comp, posting, _reg, _app = base_setup
    officer = _actor(uid=10, role="placement_officer", perms=["placement_cell.interview.schedule"])

    now = timezone.now()
    round_obj = int_service.schedule_round(
        posting_id=posting.pk, actor=officer, mode="online",
        starts_at=now + timedelta(days=2), meeting_url="https://meet.google.com/abc-xyz",
        kind="technical"
    )
    assert round_obj.pk is not None
    assert round_obj.mode == "online"

    # Offline round
    round_off = int_service.schedule_round(
        posting_id=posting.pk, actor=officer, mode="offline",
        starts_at=now + timedelta(days=3), venue="L-101",
        kind="hr"
    )
    assert round_off.pk is not None
    assert round_off.venue == "L-101"
