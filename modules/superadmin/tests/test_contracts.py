"""Cross-module contract tests for superadmin."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.superadmin.contracts import (
    get_active_system_policies,
    get_archived_user_statuses,
    get_purged_dataset_statuses,
)
from modules.superadmin.models.archival import ArchivedUserRecord, HistoricalDataArchive
from modules.superadmin.models.config import SystemPolicyParameter

pytestmark = pytest.mark.django_db


def test_get_archived_user_statuses():
    ArchivedUserRecord.objects.create(
        user_id=8801,
        institute_id="2020BCS001",
        username="u8801",
        email="u8801@iiitdmj.ac.in",
        user_kind="student",
        status="reversible",
        archived_at=timezone.now(),
        reversible_until=timezone.now() + timedelta(days=30),
        authorized_by=1,
        archival_reason="Graduated.",
    )

    statuses = get_archived_user_statuses([8801, 8899])
    assert statuses[8801] is not None
    assert statuses[8801].status == "reversible"
    assert statuses[8899] is None


def test_get_archived_user_statuses_empty():
    assert get_archived_user_statuses([]) == {}


def test_get_active_system_policies():
    SystemPolicyParameter.objects.create(
        key="archival.reversibility_window_days",
        value="30",
        version=1,
        effective_from=timezone.now(),
        effective_to=None,
        updated_by=1,
    )

    policies = get_active_system_policies(["archival.reversibility_window_days", "nonexistent.key"])
    assert policies["archival.reversibility_window_days"].value == "30"
    assert "nonexistent.key" not in policies


def test_get_active_system_policies_empty():
    assert get_active_system_policies([]) == {}


def test_get_purged_dataset_statuses():
    today = date.today()
    HistoricalDataArchive.objects.create(
        dataset_category="placement",
        title="Batch 2018",
        date_range_start=today - timedelta(days=1000),
        date_range_end=today - timedelta(days=600),
        record_count=100,
        backup_file_path="/backups/2018.tar.gz",
        backup_checksum="chk18",
        retention_expires_at=today - timedelta(days=10),
        is_purged=True,
        archived_by=1,
    )
    HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Batch 2022",
        date_range_start=today - timedelta(days=500),
        date_range_end=today - timedelta(days=100),
        record_count=200,
        backup_file_path="/backups/2022.tar.gz",
        backup_checksum="chk22",
        retention_expires_at=today + timedelta(days=300),
        is_purged=False,
        archived_by=1,
    )

    statuses = get_purged_dataset_statuses(["placement", "academics", "unknown_category"])
    assert statuses["placement"] is True
    assert statuses["academics"] is False
    assert statuses["unknown_category"] is False


def test_get_purged_dataset_statuses_empty():
    assert get_purged_dataset_statuses([]) == {}
