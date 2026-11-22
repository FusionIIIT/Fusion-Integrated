"""Query counts for BADMS list endpoints to verify lack of N+1 queries."""

from datetime import date, time

from django.test import override_settings
from django.utils import timezone
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import ArchiveRequest, BackupRun, BackupSchedule, RestorationRequest
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam):
    UserRef.objects.update_or_create(
        user_id=9001,
        defaults={
            "username": "sysadmin-budget",
            "display_name": "Sysadmin Budget",
            "kind": "staff",
            "email": "sysadmin@example.test",
            "department": "IT",
            "is_active": True,
        },
    )
    session = make_session(
        user_id=9001,
        kind="staff",
        active_role="System Administrator (SysAdmin)",
        roles=("System Administrator (SysAdmin)",),
        permissions=frozenset({
            "badms.archive.view_self",
            "badms.archive.classify",
            "badms.backup.view",
            "badms.restore.view_self",
            "badms.schedule_local.manage",
            "badms.audit.view",
        }),
        modules=("badms",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-budget")
    return client


@pytest.fixture
def sample_data():
    now = timezone.now()
    for i in range(5):
        ArchiveRequest.objects.create(
            user_id=9001,
            department="IT",
            requester_email="sysadmin@example.test",
            file_name=f"file{i}.zip",
            file_date=date(2026, 1, 1),
            owners=["SysAdmin"],
            file_type="application/zip",
            reason=f"Archival {i}",
            attachment_key=f"badms/file{i}.zip",
            attachment_size_bytes=1000 * (i + 1),
            status="Sensitive Archive Encrypted",
            classification="Routine",
        )
        BackupRun.objects.create(
            trigger="manual",
            status="success",
            dataset=f"fusionlab_{i}",
            actor_user_id=9001,
            started_at=now,
        )
        BackupSchedule.objects.create(
            scope="local",
            dataset=f"dataset_{i}",
            frequency="daily",
            scheduled_time=time(2, i),
            timezone="UTC",
            enabled=True,
            updated_by=9001,
        )


@override_settings(DEBUG=True)
@pytest.mark.parametrize(
    ("path", "budget"),
    [
        ("/api/v1/badms/archive_requests", 4),
        ("/api/v1/badms/backup_runs", 4),
        ("/api/v1/badms/schedules", 4),
    ],
)
def test_badms_list_endpoints_within_budget(stub_iam, sample_data, django_assert_max_num_queries, path, budget):
    client = _client(stub_iam)
    with django_assert_max_num_queries(budget):
        assert client.get(path).status_code == 200
