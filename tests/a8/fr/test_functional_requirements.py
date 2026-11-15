"""Specification tests for the FR strategy. Test and source IDs are frozen in design JSON."""
import pytest

from core.api.exceptions import PermissionDeniedError
from modules.badms.domain import state_machine as sm


@pytest.mark.django_db
def test_fr_001_afr_001_manual_backup_requires_authorized_actor(principal_factory):
    """FR-001 / AFR-BA-001: manual backup requires badms.backup.trigger."""
    from modules.badms.services.operations import trigger_manual_backup

    unauthorized = principal_factory(user_id=101)
    with pytest.raises(PermissionDeniedError):
        trigger_manual_backup(actor=unauthorized)

    authorized = principal_factory(user_id=102, permissions={"badms.backup.trigger"})
    operation = trigger_manual_backup(actor=authorized, dataset_code="academic")
    assert operation.initiated_by_user_id == authorized.user_id
    assert operation.dataset_code == "academic"


@pytest.mark.django_db
def test_fr_002_afrs_002_003_004_manual_backup_records_result(principal_factory):
    """FR-002 / AFR-BA-002, AFR-BA-003, AFR-BA-004."""
    from modules.badms.services.operations import trigger_manual_backup

    actor = principal_factory(user_id=103, permissions={"badms.backup.trigger"})
    operation = trigger_manual_backup(actor=actor, dataset_code="registry")
    assert operation.started_at is not None
    assert operation.completed_at is not None
    assert operation.dump_location
    assert operation.status == "success"


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no backup execution/failure adapter exists to exercise AFR-BA-005"
)
def test_fr_003_afr_005_backup_failure_alert():
    """FR-003 / AFR-BA-005: failure should be recorded and alert SysAdmin."""
    # Candidate gap: current manual operation service has no failure/alert branch.
    assert "alert" in __import__("modules.badms.services.operations", fromlist=["x"]).__doc__.lower()


@pytest.mark.django_db
def test_fr_004_afr_043_user_can_track_restoration_status(principal_factory):
    """FR-004 / AFR-BA-043: restoration status is persisted."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request

    owner = principal_factory(user_id=104)
    archived = SecureArchivalRequest.objects.create(
        user_id=owner.user_id,
        department="CSE",
        file_name="archive.tar",
        file_type="application/x-tar",
        file_size_bytes=12,
        reason="Project restoration",
        authoritative_classification=sm.TIER_ROUTINE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    request = submit_restoration_request(
        actor=owner, archival_request_id=archived.pk, reason="Recover project"
    )
    request.refresh_from_db()
    assert request.status == sm.RESTORATION_COMPLETED


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no batch storage-threshold monitoring operation exists for AFR-BA-051"
)
def test_fr_005_afr_051_storage_thresholds_are_monitored_for_all_users():
    """FR-005 / AFR-BA-051: storage usage/allocation are tracked per user."""
    pytest.skip("NOT_AUTOMATED: the module has no storage-threshold monitoring operation")
