"""Executable domain/API-contract checks selected from the UC design."""
import pytest

from modules.badms.domain import state_machine as sm


@pytest.mark.django_db
def test_uc_001_manual_backup_success_is_recorded(principal_factory):
    """UC-001 / BA-UC-001 Main Success, A1, E1."""
    from modules.badms.models import BackupOperation, BadmsAuditLog
    from modules.badms.services.operations import trigger_manual_backup

    actor = principal_factory(user_id=201, permissions={"badms.backup.trigger"})
    operation = trigger_manual_backup(actor=actor, dataset_code="registry")
    assert BackupOperation.objects.get(pk=operation.pk).status == "success"
    assert operation.started_at is not None and operation.completed_at is not None
    assert BadmsAuditLog.objects.filter(entity_id=operation.pk, action="manual_backup_triggered").exists()


@pytest.mark.django_db
def test_uc_001_manual_backup_denies_actor_without_permission(principal_factory):
    """UC-001 / BA-UC-001 Exception E1."""
    from core.api.exceptions import PermissionDeniedError
    from modules.badms.services.operations import trigger_manual_backup

    with pytest.raises(PermissionDeniedError):
        trigger_manual_backup(actor=principal_factory(user_id=202))


@pytest.mark.django_db
def test_uc_002_secure_archival_sensitive_approval_encryption_flow(principal_factory):
    """UC-002 / BA-UC-002 Main Success; BA-UC-003 approve/reject; BA-UC-004/005."""
    from modules.badms.services.operations import (
        hod_review_archival,
        it_security_configure_encryption,
        submit_archival_request,
        sysadmin_classify_archival,
    )

    requester = principal_factory(user_id=203)
    request = submit_archival_request(
        actor=requester,
        department="CSE",
        file_name="research.bin",
        file_type="application/octet-stream",
        file_size_bytes=100,
        reason="Archive research data",
        initial_classification=sm.TIER_SENSITIVE,
    )
    approved = hod_review_archival(
        actor=principal_factory(user_id=204, permissions={"badms.department.review"}),
        request_id=request.pk,
        action="approve",
    )
    classified = sysadmin_classify_archival(
        actor=principal_factory(user_id=205, permissions={"badms.archival.classify_authoritative"}),
        request_id=approved.pk,
        authoritative_classification=sm.TIER_SENSITIVE,
    )
    assert classified.status == sm.ARCHIVAL_CLASSIFIED
    completed = it_security_configure_encryption(
        actor=principal_factory(user_id=206, permissions={"badms.security.manage"}),
        request_id=classified.pk,
    )
    assert completed.status == sm.ARCHIVAL_COMPLETED
    assert completed.is_encrypted is True
    assert completed.encryption_algorithm == "AES-256"


@pytest.mark.django_db
def test_uc_002_secure_archival_rejection_ends_request(principal_factory):
    """UC-002 / BA-UC-003 Alternative rejection flow."""
    from modules.badms.services.operations import hod_review_archival, submit_archival_request

    request = submit_archival_request(
        actor=principal_factory(user_id=207),
        department="CSE",
        file_name="denied.txt",
        file_type="text/plain",
        file_size_bytes=5,
        reason="Test rejection",
    )
    rejected = hod_review_archival(
        actor=principal_factory(user_id=208, permissions={"badms.department.review"}),
        request_id=request.pk,
        action="reject",
    )
    assert rejected.status == sm.ARCHIVAL_HOD_REJECTED


@pytest.mark.django_db
@pytest.mark.parametrize("action,expected", [("approve", sm.STORAGE_APPROVED), ("reject", sm.STORAGE_REJECTED)])
def test_uc_003_storage_extension_request_and_hod_decision(principal_factory, action, expected):
    """UC-003 / BA-UC-007 Main Success; BA-UC-008 approve/reject."""
    from modules.badms.models import StorageQuota
    from modules.badms.services.operations import hod_review_storage_extension, submit_storage_extension

    user = principal_factory(user_id=209)
    StorageQuota.objects.create(user_id=user.user_id, allocated_mb=5120, used_mb=5120)
    request = submit_storage_extension(
        actor=user, department="CSE", requested_additional_mb=1024, reason="Project storage"
    )
    assert request.status == sm.STORAGE_SUBMITTED
    result = hod_review_storage_extension(
        actor=principal_factory(user_id=210, permissions={"badms.department.review"}),
        request_id=request.pk,
        action=action,
    )
    assert result.status == expected


@pytest.mark.django_db
def test_uc_004_non_sensitive_restoration_completes_without_sensitive_review(principal_factory):
    """UC-004 / BA-UC-016, BA-UC-017, BA-UC-018."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request

    actor = principal_factory(user_id=211)
    archive = SecureArchivalRequest.objects.create(
        user_id=actor.user_id,
        department="CSE",
        file_name="routine.zip",
        file_type="application/zip",
        file_size_bytes=10,
        reason="Archived project",
        authoritative_classification=sm.TIER_ROUTINE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    restoration = submit_restoration_request(
        actor=actor, archival_request_id=archive.pk, reason="Recover project"
    )
    assert restoration.status == sm.RESTORATION_COMPLETED
    assert restoration.restored_at is not None


@pytest.mark.django_db
def test_uc_004_sensitive_restoration_requires_sysadmin_decision(principal_factory):
    """UC-004 / BA-UC-017 sensitive approval and rejection outcomes."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request, sysadmin_review_restoration

    actor = principal_factory(user_id=212)
    archive = SecureArchivalRequest.objects.create(
        user_id=actor.user_id,
        department="CSE",
        file_name="sensitive.zip",
        file_type="application/zip",
        file_size_bytes=10,
        reason="Sensitive archive",
        authoritative_classification=sm.TIER_SENSITIVE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    restoration = submit_restoration_request(
        actor=actor, archival_request_id=archive.pk, reason="Recover sensitive data"
    )
    assert restoration.status == sm.RESTORATION_SUBMITTED
    reviewed = sysadmin_review_restoration(
        actor=principal_factory(user_id=213, permissions={"badms.restoration.approve_sensitive"}),
        restoration_id=restoration.pk,
        action="approve",
    )
    assert reviewed.status == sm.RESTORATION_COMPLETED
    assert reviewed.restored_at is not None


@pytest.mark.django_db
def test_uc_002_archival_request_defaults_to_routine_and_audits(principal_factory):
    """UC-002 / BA-UC-002 default archival request path."""
    from modules.badms.models import BadmsAuditLog
    from modules.badms.services.operations import submit_archival_request

    actor = principal_factory(user_id=214)
    request = submit_archival_request(
        actor=actor, department="CSE", file_name="routine.zip", file_type="application/zip",
        file_size_bytes=25, reason="Routine archive",
    )
    assert request.initial_classification == sm.TIER_ROUTINE
    assert request.status == sm.ARCHIVAL_SUBMITTED
    assert BadmsAuditLog.objects.filter(entity_type="archival_request", entity_id=request.pk).exists()


@pytest.mark.django_db
def test_uc_004_non_sensitive_classification_completes_archival(principal_factory):
    """UC-004 / BA-UC-004 non-sensitive classification path."""
    from modules.badms.services.operations import hod_review_archival, submit_archival_request, sysadmin_classify_archival

    request = submit_archival_request(
        actor=principal_factory(user_id=215), department="CSE", file_name="routine.zip",
        file_type="application/zip", file_size_bytes=25, reason="Routine archive",
    )
    approved = hod_review_archival(
        actor=principal_factory(user_id=216, permissions={"badms.department.review"}),
        request_id=request.pk, action="approve",
    )
    completed = sysadmin_classify_archival(
        actor=principal_factory(user_id=217, permissions={"badms.archival.classify_authoritative"}),
        request_id=approved.pk, authoritative_classification=sm.TIER_ROUTINE,
    )
    assert completed.status == sm.ARCHIVAL_COMPLETED
    assert completed.archive_location
    assert completed.retention_until is not None


@pytest.mark.django_db
def test_uc_009_local_schedule_can_be_created_and_updated(principal_factory):
    """UC-009 / BA-UC-009 local backup schedule configuration."""
    from modules.badms.models import BackupSchedule
    from modules.badms.services.operations import configure_schedule

    actor = principal_factory(user_id=218, permissions={"badms.schedule.manage_local"})
    first = configure_schedule(
        actor=actor, scope="local", dataset_code="registry", cron_expression="0 2 * * *", retention_days=30,
    )
    updated = configure_schedule(
        actor=actor, scope="local", dataset_code="registry", cron_expression="0 3 * * *", retention_days=45,
    )
    assert first.pk == updated.pk
    assert BackupSchedule.objects.count() == 1
    assert (updated.cron_expression, updated.retention_days) == ("0 3 * * *", 45)


@pytest.mark.django_db
def test_uc_010_special_archival_records_completed_offline_request(principal_factory):
    """UC-010 / BA-UC-010 authorized special archival operation."""
    from modules.badms.models import BadmsAuditLog
    from modules.badms.services.operations import super_admin_special_archival

    request = super_admin_special_archival(
        actor=principal_factory(user_id=219, permissions={"badms.archival.special"}),
        department="CSE", file_name="offline.zip", file_type="application/zip",
        file_size_bytes=80, reason="Approved offline archival",
    )
    assert request.is_special is True
    assert request.status == sm.ARCHIVAL_SPECIAL_EXECUTED
    assert request.archive_location
    assert BadmsAuditLog.objects.filter(action="special_archival_executed", entity_id=request.pk).exists()


@pytest.mark.django_db
def test_uc_022_storage_quota_is_created_with_default_limits(principal_factory):
    """UC-022 / BA-UC-022 quota status is available for a new user."""
    from modules.badms.models import StorageQuota

    actor = principal_factory(user_id=220, permissions={"badms.storage.request"})
    quota, created = StorageQuota.objects.get_or_create(user_id=actor.user_id)
    assert created
    assert quota.allocated_mb == 5120
    assert quota.used_mb == 0


@pytest.mark.django_db
def test_uc_003_hod_archival_list_is_limited_to_own_department(department_principal):
    """UC-003 / BA-UC-003 department list scope contract."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.selectors.scoping import visible_archival_requests

    SecureArchivalRequest.objects.create(
        user_id=221, department="CSE", file_name="own.zip", file_type="application/zip",
        reason="own department",
    )
    SecureArchivalRequest.objects.create(
        user_id=222, department="ECE", file_name="other.zip", file_type="application/zip",
        reason="other department",
    )
    hod = department_principal(user_id=223, permissions={"badms.department.review"}, department="CSE")
    assert set(visible_archival_requests(hod).values_list("department", flat=True)) == {"CSE"}
