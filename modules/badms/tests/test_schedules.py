"""Tests for BADMS Backup Schedules & Policies (Phase 8)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    BackupFrequency,
    BackupSchedule,
    BackupScope,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


def test_sysadmin_can_create_local_dataset_schedule(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE, p.BACKUP_VIEW),
    )

    payload = {
        "name": "Daily Student Records Backup",
        "schedule_type": "local",
        "target_dataset": "student_records",
        "frequency": "daily",
        "execution_time": "02:30:00",
        "repository_path": "/var/backups/badms/local",
    }
    res = client.post("/api/v1/badms/schedules/", payload, format="json")
    assert res.status_code == 201, res.data
    assert res.data["name"] == "Daily Student Records Backup"
    assert res.data["schedule_type"] == "local"
    assert res.data["target_dataset"] == "student_records"


def test_superadmin_can_create_global_schedule(stub_iam):
    client = _client(
        stub_iam,
        user_id=1,
        kind="staff",
        active_role="Super Admin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE, p.POLICY_MANAGE),
    )

    payload = {
        "name": "Global ERP Nightly Backup",
        "schedule_type": "global",
        "target_dataset": "all",
        "frequency": "daily",
        "execution_time": "01:00:00",
        "repository_path": "/var/backups/badms/global",
    }
    res = client.post("/api/v1/badms/schedules/", payload, format="json")
    assert res.status_code == 201, res.data
    assert res.data["schedule_type"] == "global"


def test_non_superadmin_cannot_create_global_schedule(stub_iam):
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE, p.BACKUP_VIEW),  # Missing p.POLICY_MANAGE
    )

    payload = {
        "name": "Unauthorized Global",
        "schedule_type": "global",
        "target_dataset": "all",
        "frequency": "daily",
        "execution_time": "01:00:00",
        "repository_path": "/var/backups/badms",
    }
    res = client.post("/api/v1/badms/schedules/", payload, format="json")
    assert res.status_code == 403
    assert "Super Admin" in res.data.get("detail", "") or "permission" in str(res.data)


def test_local_schedule_overrides_global_schedule(stub_iam):
    # Setup global schedule
    global_sched = BackupSchedule.objects.create(
        name="Global Daily",
        schedule_type=BackupScope.GLOBAL,
        target_dataset="all",
        frequency=BackupFrequency.DAILY,
        execution_time="01:00:00",
        repository_path="/var/backups/badms/global",
        is_active=True,
    )
    # Setup local schedule for 'finance'
    local_sched = BackupSchedule.objects.create(
        name="Local Finance Daily",
        schedule_type=BackupScope.LOCAL,
        target_dataset="finance",
        frequency=BackupFrequency.DAILY,
        execution_time="03:00:00",
        repository_path="/var/backups/badms/local",
        is_active=True,
    )

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_VIEW,),
    )

    # 1. Finance dataset -> local schedule overrides global
    res_finance = client.get("/api/v1/badms/schedules/effective/?dataset=finance")
    assert res_finance.status_code == 200
    assert res_finance.data["has_effective_schedule"] is True
    assert res_finance.data["precedence_rule"] == "local_override"
    assert res_finance.data["effective_schedule"]["id"] == local_sched.pk

    # 2. Other dataset (e.g. 'library') -> global schedule applies
    res_library = client.get("/api/v1/badms/schedules/effective/?dataset=library")
    assert res_library.status_code == 200
    assert res_library.data["has_effective_schedule"] is True
    assert res_library.data["precedence_rule"] == "global_default"
    assert res_library.data["effective_schedule"]["id"] == global_sched.pk


def test_invalid_schedule_rejected_without_changing_effective_schedule(stub_iam):
    # Setup an initial valid local schedule
    valid_sched = BackupSchedule.objects.create(
        name="Valid Local",
        schedule_type=BackupScope.LOCAL,
        target_dataset="admissions",
        frequency=BackupFrequency.DAILY,
        execution_time="02:00:00",
        repository_path="/var/backups/badms",
        is_active=True,
    )

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE, p.BACKUP_VIEW),
    )

    # Attempt to post an invalid schedule (invalid relative repository path)
    invalid_payload = {
        "name": "Invalid Schedule",
        "schedule_type": "local",
        "target_dataset": "admissions",
        "frequency": "daily",
        "execution_time": "02:00:00",
        "repository_path": "relative/path/forbidden",
    }
    res = client.post("/api/v1/badms/schedules/", invalid_payload, format="json")
    assert res.status_code == 400
    assert res.data["code"] == "invalid_configuration"

    # Effective schedule for 'admissions' remains untouched
    eff_res = client.get("/api/v1/badms/schedules/effective/?dataset=admissions")
    assert eff_res.data["effective_schedule"]["id"] == valid_sched.pk


def test_run_scheduled_backup_execution(stub_iam):
    sched = BackupSchedule.objects.create(
        name="Scheduled Nightly",
        schedule_type=BackupScope.LOCAL,
        target_dataset="all",
        frequency=BackupFrequency.DAILY,
        execution_time="02:00:00",
        repository_path="/var/backups/badms",
        is_active=True,
    )

    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.BACKUP_MANAGE,),
    )

    res = client.post(f"/api/v1/badms/schedules/{sched.pk}/run/")
    assert res.status_code == 200
    assert res.data["status"] == "completed"
    assert res.data["metadata"]["schedule_id"] == sched.pk
