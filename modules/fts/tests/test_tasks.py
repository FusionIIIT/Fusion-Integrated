"""Tests for FTS Celery tasks and management commands."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.fts.models import FTSFile
from modules.fts.tasks import cleanup_discarded_drafts

pytestmark = pytest.mark.django_db


def test_cleanup_discarded_drafts_task():
    # File discarded long ago
    old_time = timezone.now() - timedelta(days=40)
    f_old = FTSFile.objects.create(
        file_id="FTS-2026-OLDDRAFT",
        subject="Old Discarded Draft",
        creator_id=101,
        owner_id=101,
        current_holder_id=101,
        status="discarded",
    )
    FTSFile.objects.filter(id=f_old.id).update(updated_at=old_time)

    # File discarded recently
    f_new = FTSFile.objects.create(
        file_id="FTS-2026-NEWDRAFT",
        subject="Recent Discarded Draft",
        creator_id=101,
        owner_id=101,
        current_holder_id=101,
        status="discarded",
    )

    msg = cleanup_discarded_drafts()
    assert "Purged 1" in msg
    assert not FTSFile.objects.filter(id=f_old.id).exists()
    assert FTSFile.objects.filter(id=f_new.id).exists()


def test_management_commands(capsys):
    call_command("fts_readiness")
    captured = capsys.readouterr()
    assert "FTS is healthy and ready." in captured.out

    call_command("run_fts_cleanup")
    captured2 = capsys.readouterr()
    assert "Draft cleanup executed:" in captured2.out
