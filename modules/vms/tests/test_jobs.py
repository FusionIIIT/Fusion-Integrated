"""Celery wiring for the VMS jobs: the tasks run the services, and the beat schedule names
tasks that really exist (CFR-023/024, BR-101, BR-190, UC-038)."""
import logging
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.jobs import duration
from modules.vms.jobs import muster as muster_job
from modules.vms.models import Alert, AuditLog, EmergencyMuster, VisitLog
from modules.vms.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _on_site_past_end():
    vr = f.make_visit_request(status="approved")
    vp = f.make_visit_pass(visit_request=vr, valid_until=timezone.now() - timedelta(minutes=5))
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN)
    return vp


def test_auto_checkout_task_checks_out_visitors_past_their_pass_end():
    """BR-101 / UC-038: the Celery task, not just the service, completes the visit."""
    vp = _on_site_past_end()
    assert duration.auto_checkout_sweep() == 1
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"
    assert VisitLog.objects.filter(visit_pass=vp, event=VisitLog.Event.AUTO_CHECK_OUT).exists()
    assert duration.auto_checkout_sweep() == 0          # idempotent


def test_expire_unused_passes_task_deactivates_passes_nobody_used():
    """BR-190: an ended pass with no check-in is deactivated and audited as the system."""
    vr = f.make_visit_request(status="approved")
    vp = f.make_visit_pass(visit_request=vr, valid_until=timezone.now() - timedelta(hours=1))
    assert duration.expire_unused_passes() == 1
    vp.refresh_from_db()
    assert vp.is_active is False
    assert AuditLog.objects.filter(action="vms.pass.expired", actor_role="system").exists()
    assert duration.expire_unused_passes() == 0


def test_muster_stale_check_task_alerts_once_and_logs(caplog):
    """A muster open for over 6 hours raises one alert; the task reports the count."""
    with freeze_time(timezone.now() - timedelta(hours=7)):      # triggered_at is auto_now_add
        f.make_emergency_muster(status=EmergencyMuster.Status.OPEN)
    with caplog.at_level(logging.WARNING, logger="fusion.vms.jobs"):
        assert muster_job.muster_stale_check() == 1
    assert "vms.muster.stale alerts=1" in caplog.text
    assert Alert.objects.filter(ref_type="emergency_muster_stale").count() == 1
    assert muster_job.muster_stale_check() == 0


def test_muster_stale_check_task_is_quiet_when_nothing_is_stale(caplog):
    with caplog.at_level(logging.WARNING, logger="fusion.vms.jobs"):
        assert muster_job.muster_stale_check() == 0
    assert "vms.muster.stale" not in caplog.text


def test_beat_schedule_names_registered_tasks_with_sensible_intervals():
    """A typo in a task name would make beat enqueue a task no worker knows."""
    from config.celery import app
    app.loader.import_default_modules()
    registered = set(app.tasks)
    assert {"vms-auto-checkout-sweep", "vms-expire-unused-passes",
            "vms-muster-stale-check"} <= set(BEAT_SCHEDULE)
    for name, entry in BEAT_SCHEDULE.items():
        assert entry["task"] in registered, f"{name} schedules unknown task {entry['task']}"
        assert 0 < float(entry["schedule"]) <= 3600
    assert set(BEAT_SCHEDULE) <= set(app.conf.beat_schedule)
    assert isinstance(TASK_ROUTES, dict)


def test_vms_tasks_use_late_acks_and_time_limits():
    for task in (duration.auto_checkout_sweep, duration.expire_unused_passes,
                 muster_job.muster_stale_check):
        assert task.acks_late is True
        assert task.soft_time_limit and task.time_limit > task.soft_time_limit
