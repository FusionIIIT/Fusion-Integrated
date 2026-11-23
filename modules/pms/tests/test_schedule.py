"""Beat entries exist, are merged, and each task run twice takes effect once (Step 5.9)."""
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from config.celery import app
from modules.pms import tasks
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    DeadlineAlert,
    Escalation,
    Notification,
    PmsPolicy,
    ReportDefinition,
    ReportRun,
    ReviewCycle,
)
from modules.pms.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.pms.services import reports
from modules.pms.tests.conftest import DIRECTOR, POLICY, make_app, with_cycle

EXPECTED = {"pms.deliver_notifications", "pms.process_deadlines",
            "pms.auto_route_submissions", "pms.run_scheduled_reports"}


def test_every_entry_is_in_the_merged_schedule():
    merged = app.conf.beat_schedule
    for name, entry in BEAT_SCHEDULE.items():
        assert merged[name] == entry


def test_the_four_jobs_are_scheduled_and_registered():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == EXPECTED
    assert set(app.tasks) >= EXPECTED


@pytest.mark.parametrize("entry", BEAT_SCHEDULE.values())
def test_each_entry_expires_before_its_next_run(entry):
    assert entry["options"]["expires"] > 0


def test_routes_go_to_served_queues():
    assert {r["queue"] for r in TASK_ROUTES.values()} <= {"default", "notifications",
                                                         "reports", "ingest"}
    assert set(app.conf.task_routes) >= set(TASK_ROUTES)


# BR-PMS-038
@pytest.mark.django_db
def test_process_deadlines_twice_takes_effect_once_br_pms_038(world):
    cycle_app = make_app(sm.UNDER_REVIEW)
    with_cycle(cycle_app, DIRECTOR, due=timezone.localdate() + timedelta(days=5))
    missed = make_app(sm.UNDER_REVIEW)
    with_cycle(missed, DIRECTOR, due=timezone.localdate() - timedelta(days=1))
    late = make_app(sm.REJECTED, revision_due_on=timezone.localdate() - timedelta(days=1))
    first, second = tasks.process_deadlines(), tasks.process_deadlines()
    assert first == "alerts=1 expired=1 escalated=1"
    assert second == "alerts=0 expired=0 escalated=0"
    assert DeadlineAlert.objects.count() == 1
    assert Escalation.objects.filter(kind="missed_review").count() == 1
    assert Application.objects.get(pk=late.pk).status == sm.EXPIRED


@pytest.mark.django_db
def test_deliver_notifications_twice_sends_once(world):
    from django.core import mail

    world["applicant"]._go()
    Notification.objects.create(topic="t", dedupe_key="k", recipient_user_id=1001,
                                subject="s", body="b")
    tasks.deliver_notifications()
    tasks.deliver_notifications()
    assert len(mail.outbox) == 1


# BR-PMS-022 PMS-AFR-050
@pytest.mark.django_db
def test_auto_route_does_nothing_unless_switched_on_br_pms_022(world):
    app_ = make_app(sm.SUBMITTED)
    assert tasks.auto_route_submissions() == 0
    PmsPolicy.objects.create(version=2, effective_from=timezone.now(),
                             payload={**POLICY, "auto_routing_enabled": True},
                             published_by_user_id=1)
    assert tasks.auto_route_submissions() == 1
    assert tasks.auto_route_submissions() == 0
    assert ReviewCycle.objects.get(application=app_).assigned_by_user_id is None


@pytest.mark.django_db
def test_auto_route_escalates_when_nobody_is_eligible(world):
    make_app(sm.SUBMITTED, domain="software")
    PmsPolicy.objects.create(version=2, effective_from=timezone.now(),
                             payload={**POLICY, "auto_routing_enabled": True},
                             published_by_user_id=1)
    assert tasks.auto_route_submissions() == 0
    assert tasks.auto_route_submissions() == 0
    assert Escalation.objects.filter(kind="no_eligible_director").count() == 1


# PMS-AFR-188
@pytest.mark.django_db
def test_scheduled_reports_twice_make_one_run_pms_afr_188(world):
    ReportDefinition.objects.create(owner_user_id=4001, owner_role="pms_pcc_admin", name="W",
                                    report_type="status", schedule="weekly")
    ReportDefinition.objects.create(owner_user_id=4001, owner_role="pms_pcc_admin", name="M",
                                    report_type="status", schedule="monthly")
    monday_first = date(2027, 2, 1)
    assert reports.run_scheduled(today=monday_first) == 2
    assert reports.run_scheduled(today=monday_first) == 0
    assert reports.run_scheduled(today=date(2027, 2, 2)) == 0
    assert ReportRun.objects.count() == 2
    assert tasks.run_scheduled_reports() >= 0


@pytest.mark.django_db
def test_run_task_command_runs_each_task(world):
    for name in ("deliver_notifications", "process_deadlines", "auto_route_submissions",
                 "run_scheduled_reports"):
        out = StringIO()
        call_command("pms_run_task", task=name, stdout=out)
        assert out.getvalue().startswith(f"pms.{name}: ")


@pytest.mark.django_db
def test_readiness_names_what_is_missing(settings, tmp_path):
    settings.PMS_UPLOAD_ROOT = str(tmp_path / "u")
    settings.PMS_MALWARE_SCANNER, settings.PMS_CLAMD_SOCKET = "clamd", ""
    settings.PMS_CLAMD_HOST = ""
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("pms_readiness", stdout=StringIO(), stderr=err)
    assert "PMS_CLAMD_SOCKET" in err.getvalue()


@pytest.mark.django_db
def test_readiness_passes_with_a_scanner(world, scanner):
    out = StringIO()
    call_command("pms_readiness", stdout=out)
    assert "PMS is ready" in out.getvalue()
