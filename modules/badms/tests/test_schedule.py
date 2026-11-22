"""Tests for periodic background tasks, scheduler catch-up, and alert SLAs.
"""
from datetime import UTC, datetime, timedelta

import pytest

from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    UserStorageQuota,
)
from modules.badms.tasks import (
    check_backup_failure_sla,
    evaluate_and_dispatch_due_backups,
    monitor_storage_thresholds,
    purge_expired_archives,
)

pytestmark = pytest.mark.django_db


def test_evaluate_and_dispatch_due_backups():
    now = datetime.now(UTC)
    active_sched = BackupSchedule.objects.create(
        name="Nightly Core",
        scope_type="global",
        dataset_name="core_db",
        cron_expression="0 2 * * *",
        is_active=True,
        created_by_user_id=1,
        effective_from=now - timedelta(days=1),
    )
    inactive_sched = BackupSchedule.objects.create(
        name="Inactive Schedule",
        scope_type="local",
        dataset_name="aux_db",
        cron_expression="0 3 * * 0",
        is_active=False,
        created_by_user_id=1,
        effective_from=now - timedelta(days=1),
    )

    res = evaluate_and_dispatch_due_backups()
    assert res["dispatched"] >= 1

    active_sched.refresh_from_db()
    assert active_sched.last_run_at is not None

    # Verify backup record was created
    bkup = BackupRecord.objects.filter(dataset_name="core_db").first()
    assert bkup is not None
    assert bkup.backup_type == "scheduled"

    # Inactive schedule was untouched
    inactive_sched.refresh_from_db()
    assert inactive_sched.last_run_at is None


def test_monitor_storage_thresholds():
    user_id = 9001
    quota = UserStorageQuota.objects.create(
        user_id=user_id,
        allocated_quota_bytes=1000,
        used_storage_bytes=1200,  # Exceeds quota
        is_full=False,
    )

    res = monitor_storage_thresholds()
    assert res["updated"] >= 1

    quota.refresh_from_db()
    assert quota.is_full is True


def test_check_backup_failure_sla():
    # Unalerted backup failure
    bkup = BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="prod_database",
        status=BackupRecord.STATUS_FAILURE,
        error_message="Network partition timeout",
        consecutive_failure_count=3,
        alert_sent=False,
    )

    res = check_backup_failure_sla()
    assert res["alerted"] >= 1

    bkup.refresh_from_db()
    assert bkup.alert_sent is True

    # Verify alert audit event
    audit = AuditEvent.objects.filter(event_type="backup_failure_alert_sent", target_id=bkup.id).first()
    assert audit is not None


def test_purge_expired_archives():
    ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="archive1.tar",
        file_type="archive",
        file_size_bytes=1000,
        file_storage_path="/arch/archive1.tar",
        status="classified_non_sensitive",
        retention_policy_ref="inst-retention-5y",
    )

    res = purge_expired_archives()
    assert res["flagged_for_review"] >= 1
