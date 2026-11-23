# Celery schedule, idempotent tasks, management commands, and contracts tests (Step 5.9).
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from config.celery import app
from conftest import make_principal
from modules.psm import contracts, registry, tasks
from modules.psm.models import Indent, PsmNotification, ReportGenerationLog, ReportSchedule
from modules.psm.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.psm.services import indents, policy, reports

pytestmark = pytest.mark.django_db


def test_all_psm_beat_entries_are_merged_and_registered():
    for key, entry in BEAT_SCHEDULE.items():
        assert key in app.conf.beat_schedule
        assert entry["task"] in app.tasks
        assert entry["options"]["expires"] > 0
    served = {"default", "notifications", "reports", "ingest"}
    for task_name, route in TASK_ROUTES.items():
        assert route["queue"] in served, task_name


def test_sla_task_is_idempotent_on_double_run():
    # BR-PSM-014, AFR-PSM-027, AFR-PSM-028, AFR-PSM-085
    policy.seed_default_policy()
    p_emp = make_principal(user_id=7001, kind="faculty", active_role="faculty", roles=("faculty",))
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="UPS",
        quantity=1,
        estimated_cost=Decimal("5000.00"),
        justification="Backup",
    )
    Indent.objects.filter(pk=ind.pk).update(
        current_stage_since=timezone.now() - timedelta(hours=30)
    )
    first = tasks.check_approval_slas()
    second = tasks.check_approval_slas()
    assert first == {"reminded": 1, "escalated": 0}
    assert second == {"reminded": 0, "escalated": 0}
    # Advance past escalation window -> escalates once.
    Indent.objects.filter(pk=ind.pk).update(
        current_stage_since=timezone.now() - timedelta(hours=55)
    )
    third = tasks.check_approval_slas()
    fourth = tasks.check_approval_slas()
    assert third == {"reminded": 0, "escalated": 1}
    assert fourth == {"reminded": 0, "escalated": 0}


def test_scheduled_report_task_is_idempotent_and_blocks_revoked_role():
    # PSM-UC-035, CFR-PSM-017, AFR-PSM-080, AFR-PSM-082, BR-PSM-024
    policy.seed_default_policy()
    p_ps = make_principal(
        user_id=7002,
        kind="staff",
        active_role="ps_admin",
        roles=("ps_admin",),
        permissions=tuple(registry.ROLE_GRANTS["ps_admin"]),
    )
    sched = reports.create_schedule(
        actor=p_ps, name="Weekly Ops", report_type="operational", cadence="weekly"
    )
    ReportSchedule.objects.filter(pk=sched.pk).update(
        next_run_at=timezone.now() - timedelta(minutes=5)
    )
    assert tasks.run_scheduled_reports() == 1
    assert tasks.run_scheduled_reports() == 0
    assert (
        ReportGenerationLog.objects.filter(
            schedule=sched, trigger_type="scheduled", status="succeeded"
        ).count()
        == 1
    )

    # Role lacking financial report permission gets blocked and logged.
    bad = ReportSchedule.objects.create(
        name="Blocked Fin",
        report_type="financial",
        cadence="daily",
        is_active=True,
        created_by_user_id=7003,
        created_by_role="faculty",
        next_run_at=timezone.now() - timedelta(minutes=1),
    )
    assert tasks.run_scheduled_reports() == 0
    assert ReportGenerationLog.objects.filter(schedule=bad, status="blocked").count() == 1


def test_notification_delivery_task_is_idempotent():
    # BR-PSM-006, AFR-PSM-083, AFR-PSM-084, AFR-PSM-086
    policy.seed_default_policy()
    p_emp = make_principal(user_id=7004, kind="faculty", active_role="faculty", roles=("faculty",))
    indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Mouse",
        quantity=2,
        estimated_cost=Decimal("800.00"),
        justification="Office",
    )
    assert tasks.deliver_notifications() >= 1
    assert tasks.deliver_notifications() == 0
    assert PsmNotification.objects.filter(status="pending").count() == 0


def test_management_commands_and_contracts():
    # Step 4.8, Step 7.5, Step 3.6
    out = io.StringIO()
    with pytest.raises(CommandError):
        call_command("psm_readiness", stdout=out, stderr=out)
    call_command("seed_psm_policy", stdout=out)
    call_command("psm_readiness", stdout=out)
    call_command("run_psm_sla_sweep", stdout=out)
    call_command("run_psm_scheduled_reports", stdout=out)
    call_command("deliver_psm_notifications", stdout=out)
    assert contracts.get_indent_summaries([]) == {}
    assert contracts.get_pending_receipt_obligations([]) == {}
    summaries = contracts.get_indent_summaries([7001])
    assert 7001 in summaries and summaries[7001].open_count == 0


def test_due_schedule_failure_logs_failed_and_never_records_success(monkeypatch):
    # PSM-UC-035 Alternative A2: generation failure logs failed status without recording success.
    from modules.psm.models import PsmAuditLog
    from modules.psm.selectors import reports as report_sel

    policy.seed_default_policy()
    p_ps = make_principal(
        user_id=7010,
        kind="staff",
        active_role="ps_admin",
        roles=("ps_admin",),
        permissions=tuple(registry.ROLE_GRANTS["ps_admin"]),
    )
    sched = reports.create_schedule(
        actor=p_ps, name="Failing Ops", report_type="operational", cadence="daily"
    )
    ReportSchedule.objects.filter(pk=sched.pk).update(
        next_run_at=timezone.now() - timedelta(minutes=5)
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("Simulated report query failure")

    monkeypatch.setattr(report_sel, "build_report_rows", _boom)
    assert reports.run_due_schedules() == 0
    sched.refresh_from_db()
    assert sched.last_run_at is None
    assert (
        ReportGenerationLog.objects.filter(
            schedule=sched, trigger_type="scheduled", status="succeeded"
        ).count()
        == 0
    )
    failed = ReportGenerationLog.objects.filter(
        schedule=sched, trigger_type="scheduled", status="failed"
    ).first()
    assert failed is not None
    assert "Simulated report query failure" in failed.error_message
    assert PsmAuditLog.objects.filter(
        action="report.schedule_failed", target_type="report_schedule", target_id=sched.pk
    ).exists()
    assert PsmNotification.objects.filter(
        recipient_user_id=7010, topic="report.schedule_failed"
    ).exists()
