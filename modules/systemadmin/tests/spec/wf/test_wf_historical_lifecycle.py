"""WF Test Suite 4: Historical Data Archival and Restoration Lifecycle (BW-SA-09)."""

from datetime import date

import pytest

from modules.systemadmin.services.archival_service import ArchivalError, ArchivalService

pytestmark = pytest.mark.django_db

# --- BW-SA-09: Historical Data Archive and Restore ---


def test_wf_022_historical_data_archive_and_restore_path():
    """TEST_WF_022 | BW-SA-09: Verify historical data archive and restore basis path: operational data -> archived with backup -> restored with approval."""
    # Step 1: Archive historical data with mandatory backup
    archived = ArchivalService.archive_historical_data(
        category="examination_results_2017",
        date_range_start=date(2017, 1, 1),
        date_range_end=date(2017, 12, 31),
        record_count=600,
        storage_size_kb=8400,
        backup_reference="BKP-EXAM-2017-FINAL",
    )
    assert archived.status == "archived"
    assert archived.backup_reference == "BKP-EXAM-2017-FINAL"

    # Step 2: Restore historical data to active system with administrative approval
    restored = ArchivalService.restore_historical_data(
        data_id=archived.id,
        approval_ref="SENATE-APPROVAL-2026-HIST",
    )
    assert restored.status == "restored"
    assert restored.restoration_approval_ref == "SENATE-APPROVAL-2026-HIST"


def test_wf_023_historical_archival_guard_inverted_date_range():
    """TEST_WF_023 | BW-SA-09: Verify historical archival guard condition: invalid date range rejects archival transition."""
    with pytest.raises(ArchivalError):
        ArchivalService.archive_historical_data(
            category="finance_audit_bad_dates",
            date_range_start=date(2025, 1, 1),
            date_range_end=date(2024, 1, 1),  # Inverted range
        )


def test_wf_024_historical_restoration_guard_missing_approval():
    """TEST_WF_024 | BW-SA-09: Verify historical restoration guard condition: missing approval reference rejects restoration transition."""
    archived = ArchivalService.archive_historical_data(
        category="placement_records_2016",
        date_range_start=date(2016, 1, 1),
        date_range_end=date(2016, 12, 31),
    )
    with pytest.raises(ArchivalError):
        ArchivalService.restore_historical_data(
            data_id=archived.id,
            approval_ref="",  # Empty approval reference
        )
