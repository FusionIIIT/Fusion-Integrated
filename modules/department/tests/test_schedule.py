"""Beat entries, tasks run twice, commands and readiness (Steps 5.9, 7.5)."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from config.celery import app
from fusion_auth.client import UserRef
from modules.department.contracts import get_headships
from modules.department.models import Department, DepartmentNotification, RoleTenure
from modules.department.registry import readiness
from modules.department.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.department.services import notifications
from modules.department.tasks import apply_role_transitions, deliver_notifications


def test_every_beat_entry_is_merged_into_the_app_schedule():
    for name, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[name] == entry
        assert entry["task"] in app.tasks
        assert 0 < entry["options"]["expires"] < entry["schedule"]


def test_the_two_recurring_jobs_are_scheduled_and_routed():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "department.deliver_notifications",
        "department.apply_role_transitions",
    }
    for task, route in TASK_ROUTES.items():
        assert app.conf.task_routes[task] == route
        assert route["queue"] in {"default", "notifications", "reports", "ingest"}


@pytest.mark.django_db
def test_role_transition_task_twice_in_a_row_takes_effect_once(world):
    # UC-DEPT-022
    RoleTenure.objects.update(transition_applied_at=None)
    assert apply_role_transitions() == 4
    assert apply_role_transitions() == 0
    assert DepartmentNotification.objects.filter(topic="role.effective").count() == 4


@pytest.mark.django_db
def test_a_future_tenure_is_not_applied_early(world):
    start = timezone.now() + timedelta(days=2)
    RoleTenure.objects.create(
        department=world["CSE"],
        role="hod",
        user_id=7,
        valid_from=start,
        valid_to=start + timedelta(days=5),
        assigned_by=1,
    )
    assert apply_role_transitions() == 0


@pytest.mark.django_db
def test_delivery_task_twice_in_a_row_sends_once(world, stub_iam, mailoutbox):
    stub_iam(
        None,
        users={
            9: UserRef(
                user_id=9, username="u9", display_name="P", kind="faculty", email="p@example.test"
            )
        },
    )
    notifications.enqueue(
        topic="feedback.created", recipients=[9, 9, None], key="1", subject="s", body="b"
    )
    assert "sent=1" in deliver_notifications()
    assert "sent=0" in deliver_notifications()
    assert len(mailoutbox) == 1 and mailoutbox[0].to == ["p@example.test"]


@pytest.mark.django_db
def test_delivery_without_an_address_retries_then_fails(world, stub_iam, settings):
    settings.NOTIFY_MAX_ATTEMPTS = 2
    stub_iam(None, users={})
    notifications.enqueue(topic="feedback.created", recipients=[9], key="1", subject="s", body="b")
    assert "failed=1" in str(notifications.deliver_pending())
    row = DepartmentNotification.objects.get()
    assert row.status == "pending" and row.attempts == 1 and "no email" in row.last_error
    notifications.deliver_pending()
    assert DepartmentNotification.objects.get().status == "failed"


@pytest.mark.django_db
def test_a_stranded_sending_row_is_reclaimed(world, stub_iam):
    stub_iam(None, users={})
    notifications.enqueue(topic="feedback.created", recipients=[9], key="1", subject="s", body="b")
    DepartmentNotification.objects.update(
        status="sending", claimed_at=timezone.now() - timedelta(hours=1)
    )
    assert notifications.deliver_pending().reclaimed == 1


def test_unknown_topic_is_a_programming_error():
    with pytest.raises(ValueError):
        notifications.enqueue(topic="nope", recipients=[1], key="1", subject="s", body="b")


@pytest.mark.django_db
def test_readiness_names_what_is_missing_then_passes():
    assert readiness() == [
        "No departments exist yet. Run `python manage.py seed_departments` to create them."
    ]
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("check_department_readiness", stderr=err)
    assert "seed_departments" in err.getvalue()
    out = StringIO()
    call_command("seed_departments", stdout=out)
    call_command("seed_departments", stdout=out)
    assert "0 created, 7 total" in out.getvalue()
    assert Department.objects.count() == 7
    out = StringIO()
    call_command("check_department_readiness", stdout=out)
    assert "ready" in out.getvalue()


@pytest.mark.django_db
def test_seeding_never_overwrites_an_approved_name(world):
    Department.objects.filter(code="CSE").update(name="Dept. of CSE")
    call_command("seed_departments", stdout=StringIO())
    assert Department.objects.get(code="CSE").name == "Dept. of CSE"


@pytest.mark.django_db
def test_run_department_tasks_runs_both(world):
    RoleTenure.objects.update(transition_applied_at=None)
    out = StringIO()
    call_command("run_department_tasks", stdout=out)
    assert "Role transitions applied: 4" in out.getvalue()


@pytest.mark.django_db
def test_headship_contract_is_plural_and_follows_the_tenure(world):
    # AFR-DEPT-053
    heads = get_headships(["CSE", "ECE", "SM", "NOPE"])
    assert heads["CSE"].hod_user_id == 3010 and heads["SM"].hod_user_id is None
    assert "NOPE" not in heads
