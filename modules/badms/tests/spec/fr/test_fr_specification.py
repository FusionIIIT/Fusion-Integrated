"""Executable coverage of the frozen BADMS functional-requirement design."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.domain import schedules as schedule_domain
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RetentionPolicy,
    UserStorageQuota,
)
from modules.badms.services import archival, backups, restoration, schedules, storage
from modules.badms.tasks import (
    evaluate_and_dispatch_due_backups,
    monitor_storage_thresholds,
)

pytestmark = pytest.mark.django_db


@dataclass
class Actor:
    user_id: int
    active_role: str = "student"
    department: str = "CSE"
    roles: tuple[str, ...] = ()


def _client(stub_iam, **kwargs):
    stub_iam(make_session(**kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fr-spec")
    return client


def _user(user_id=1001, department="CSE"):
    return Actor(user_id=user_id, department=department)


def _hod(user_id=5001, department="CSE"):
    return Actor(user_id=user_id, active_role="HOD", department=department)


def _sysadmin(user_id=6001):
    return Actor(user_id=user_id, active_role="SysAdmin", department="Central")


def _security(user_id=7001):
    return Actor(user_id=user_id, active_role="IT Security", department="Central")


def _archival_request(
    *,
    requester_id=1001,
    department="CSE",
    status="submitted",
    classification="Routine",
):
    return ArchivalRequest.objects.create(
        requester_user_id=requester_id,
        department=department,
        file_name="research.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="FR specification fixture",
        file_storage_path="/archive/research.tar",
        initial_classification=classification,
        authoritative_classification=classification if status != "submitted" else "",
        status=status,
    )


def _submitted_archival(actor=None, *, classification="Routine"):
    return archival.submit_archival_request(
        actor=actor or _user(),
        file_name="research.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="FR specification fixture",
        file_storage_path="/archive/research.tar",
        initial_classification=classification,
    )


def _approved_archival(*, classification="Routine"):
    request = _submitted_archival(classification=classification)
    return archival.decide_archival_request(_hod(), request.id, "approve", "Reviewed")


def _full_quota(user_id=1001):
    return UserStorageQuota.objects.create(
        user_id=user_id,
        allocated_quota_bytes=1000,
        used_storage_bytes=1000,
        is_full=True,
    )


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_002", "AFR-BA-002", id="FR_AFR_BA_002__AFR_BA_002"),
        pytest.param("FR_AFR_BA_003", "AFR-BA-003", id="FR_AFR_BA_003__AFR_BA_003"),
    ],
)
def test_manual_backup_artifacts_and_outcomes(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    record = backups.trigger_manual_backup(_sysadmin(), "fr_manual_db")

    assert record.status == BackupRecord.STATUS_SUCCESS, (test_id, source_id)
    assert record.started_at is not None
    assert record.completed_at is not None
    assert record.file_path.endswith(".dump")
    assert record.file_size_bytes > 0
    assert len(record.checksum_sha256) == 64
    assert AuditEvent.objects.filter(
        event_type="manual_backup_created", target_model="BackupRecord", target_id=record.id
    ).exists()



@pytest.mark.skip(
    reason="NOT_AUTOMATED: manual backup has no failure-injection seam or observable failure path."
)
def test_fr_cfr_ba_001_cfr_ba_001_manual_backup_end_to_end():
    """FR_CFR_BA_001; source_id: CFR-BA-001 — primary end-to-end behaviour."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: successful backup outcome communication is not recorded or exposed."
)
def test_fr_afr_ba_004_afr_ba_004_backup_outcome_communication():
    """FR_AFR_BA_004; source_id: AFR-BA-004 — explicit requirement."""


def test_fr_afr_ba_001_afr_ba_001_manual_backup_roles(stub_iam):
    """FR_AFR_BA_001; source_id: AFR-BA-001 — explicit requirement."""
    for user_id, role in ((6001, "SysAdmin"), (1, "Super Admin")):
        client = _client(
            stub_iam,
            user_id=user_id,
            roles=(role,),
            active_role=role,
            modules=("badms",),
            permissions=("badms.backup.manage",),
        )
        response = client.post("/api/v1/badms/backups/manual/", {"dataset_name": role})
        assert response.status_code == 201


@pytest.mark.skip(
    reason="NOT_AUTOMATED: manual backup has no failure-injection seam or observable failure path."
)
def test_fr_afr_ba_005_afr_ba_005_manual_backup_failure_notification():
    """FR_AFR_BA_005; source_id: AFR-BA-005 — explicit requirement."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_002", "CFR-BA-002", id="FR_CFR_BA_002__CFR_BA_002"),
        pytest.param("FR_AFR_BA_006", "AFR-BA-006", id="FR_AFR_BA_006__AFR_BA_006"),
        pytest.param("FR_AFR_BA_007", "AFR-BA-007", id="FR_AFR_BA_007__AFR_BA_007"),
        pytest.param("FR_AFR_BA_008", "AFR-BA-008", id="FR_AFR_BA_008__AFR_BA_008"),
        pytest.param("FR_AFR_BA_009", "AFR-BA-009", id="FR_AFR_BA_009__AFR_BA_009"),
        pytest.param("FR_AFR_BA_010", "AFR-BA-010", id="FR_AFR_BA_010__AFR_BA_010"),
    ],
)
def test_scheduled_backup_dispatch_artifact_and_log(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    schedule = BackupSchedule.objects.create(
        name="FR due schedule",
        scope_type="global",
        dataset_name="fr_scheduled_db",
        cron_expression="0 2 * * *",
        created_by_user_id=1,
        effective_from=datetime.now(UTC) - timedelta(days=1),
    )

    result = evaluate_and_dispatch_due_backups()
    schedule.refresh_from_db()
    record = BackupRecord.objects.get(dataset_name="fr_scheduled_db")

    assert result["dispatched"] == 1, (test_id, source_id)
    assert schedule.last_run_at is not None
    assert record.backup_type == BackupRecord.TYPE_SCHEDULED
    assert record.status == BackupRecord.STATUS_SUCCESS
    assert record.file_path.endswith(".dump")
    assert record.file_size_bytes > 0
    assert len(record.checksum_sha256) == 64
    assert record.completed_at is not None


def test_fr_afr_ba_011_afr_ba_011_reachable_repository_only():
    """FR_AFR_BA_011; source_id: AFR-BA-011 — explicit requirement."""
    success = backups.execute_scheduled_backup("reachable", repository_reachable=True)
    failure = backups.execute_scheduled_backup("unreachable", repository_reachable=False)

    assert success.status == BackupRecord.STATUS_SUCCESS
    assert failure.status == BackupRecord.STATUS_FAILURE
    assert failure.file_path == ""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_003", "CFR-BA-003", id="FR_CFR_BA_003__CFR_BA_003"),
        pytest.param("FR_AFR_BA_013", "AFR-BA-013", id="FR_AFR_BA_013__AFR_BA_013"),
        pytest.param("FR_AFR_BA_015", "AFR-BA-015", id="FR_AFR_BA_015__AFR_BA_015"),
        pytest.param("FR_AFR_BA_016", "AFR-BA-016", id="FR_AFR_BA_016__AFR_BA_016"),
    ],
)
def test_local_schedule_create_update_and_audit(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    actor = _sysadmin()
    created = schedules.create_backup_schedule(
        actor,
        name="FR local schedule",
        scope_type="local",
        dataset_name="fr_dataset",
        cron_expression="0 2 * * *",
        data_classification_filter="Sensitive,Critical",
    )
    updated = schedules.update_backup_schedule(
        actor,
        created.id,
        cron_expression="0 3 * * *",
        data_classification_filter="Routine",
    )

    assert updated.is_active is True, (test_id, source_id)
    assert updated.cron_expression == "0 3 * * *"
    assert updated.data_classification_filter == "Routine"
    assert AuditEvent.objects.filter(
        event_type="backup_schedule_created", target_id=created.id
    ).exists()
    assert AuditEvent.objects.filter(
        event_type="backup_schedule_updated", target_id=created.id
    ).exists()


def test_fr_afr_ba_012_afr_ba_012_sysadmin_views_schedules(stub_iam):
    """FR_AFR_BA_012; source_id: AFR-BA-012 — explicit requirement."""
    schedules.create_backup_schedule(
        _sysadmin(), "Visible", "local", "viewable", "0 2 * * *"
    )
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.view",),
    )
    response = client.get("/api/v1/badms/schedules/")
    assert response.status_code == 200
    assert response.json()["results"][0]["dataset_name"] == "viewable"


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_014", "AFR-BA-014", id="FR_AFR_BA_014__AFR_BA_014"),
        pytest.param(
            "FR_AFR_BA_014_INVALID_NOT_APPLIED",
            "AFR-BA-014",
            id="FR_AFR_BA_014_INVALID_NOT_APPLIED__AFR_BA_014",
        ),
    ],
)
def test_invalid_or_conflicting_schedule_is_not_applied(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    actor = _sysadmin()
    original = schedules.create_backup_schedule(
        actor, "Original", "local", "no-change", "0 2 * * *"
    )
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.manage",),
    )
    if test_id == "FR_AFR_BA_014":
        response = client.patch(
            f"/api/v1/badms/schedules/local/{original.id}/", {"cron_expression": "invalid"}
        )
    else:
        response = client.post(
            "/api/v1/badms/schedules/local/",
            {
                "name": "Conflicting",
                "dataset_name": "no-change",
                "cron_expression": "0 3 * * *",
            },
        )

    # The implementation exposes malformed input as HTTP 400.  The frozen
    # requirement only requires rejection and no state change, not 422.
    if test_id == "FR_AFR_BA_014":
        assert response.status_code == 400, (test_id, source_id)
    else:
        # A same-scope schedule is currently superseded by the service.  Keep
        # the frozen conflict requirement executable; this is a compliance gap.
        assert response.status_code == 409, (test_id, source_id)
    original.refresh_from_db()
    assert original.cron_expression == "0 2 * * *"
    assert original.is_active is True
    assert BackupSchedule.objects.filter(dataset_name="no-change", is_active=True).count() == 1


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_004", "CFR-BA-004", id="FR_CFR_BA_004__CFR_BA_004"),
        pytest.param("FR_AFR_BA_017", "AFR-BA-017", id="FR_AFR_BA_017__AFR_BA_017"),
        pytest.param("FR_AFR_BA_018", "AFR-BA-018", id="FR_AFR_BA_018__AFR_BA_018"),
    ],
)
def test_backup_history_is_scoped_to_user_or_administrator(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    own = BackupRecord.objects.create(
        backup_type="manual", dataset_name="own", status="success", triggered_by_user_id=1001
    )
    other = BackupRecord.objects.create(
        backup_type="manual", dataset_name="other", status="success", triggered_by_user_id=1002
    )
    user_client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.backup.view",),
    )
    user_response = user_client.get("/api/v1/badms/backups/")
    assert user_response.status_code == 200, (test_id, source_id)
    assert [item["id"] for item in user_response.json()["results"]] == [own.id]

    admin_client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.view",),
    )
    admin_response = admin_client.get("/api/v1/badms/backups/")
    assert admin_response.status_code == 200
    assert {item["id"] for item in admin_response.json()["results"]} == {own.id, other.id}


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_005", "CFR-BA-005", id="FR_CFR_BA_005__CFR_BA_005"),
        pytest.param("FR_AFR_BA_019", "AFR-BA-019", id="FR_AFR_BA_019__AFR_BA_019"),
        pytest.param("FR_AFR_BA_020", "AFR-BA-020", id="FR_AFR_BA_020__AFR_BA_020"),
        pytest.param("FR_AFR_BA_022", "AFR-BA-022", id="FR_AFR_BA_022__AFR_BA_022"),
        pytest.param("FR_AFR_BA_023", "AFR-BA-023", id="FR_AFR_BA_023__AFR_BA_023"),
        pytest.param("FR_AFR_BA_029", "AFR-BA-029", id="FR_AFR_BA_029__AFR_BA_029"),
    ],
)
def test_archival_submission_metadata_default_and_routing(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    actor = _user()
    explicit = _submitted_archival(actor, classification="Critical")
    defaulted = archival.submit_archival_request(
        actor=actor,
        file_name="default.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="Default classification",
        file_storage_path="/archive/default.tar",
        initial_classification="",
    )

    assert explicit.status == ArchivalRequest.STATUS_SUBMITTED, (test_id, source_id)
    assert explicit.file_name == "research.tar"
    assert explicit.file_storage_path == "/archive/research.tar"
    assert explicit.initial_classification == "Critical"
    assert explicit.department == "CSE"
    assert defaulted.initial_classification == "Routine"
    assert AuditEvent.objects.filter(
        event_type="archival_request_submitted", target_id=explicit.id
    ).exists()


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_021", "AFR-BA-021", id="FR_AFR_BA_021__AFR_BA_021"),
        pytest.param(
            "FR_AFR_BA_021_VALIDATION_FAILURE_NO_STATE_CHANGE",
            "AFR-BA-021",
            id="FR_AFR_BA_021_VALIDATION_FAILURE_NO_STATE_CHANGE__AFR_BA_021",
        ),
    ],
)
def test_archival_validation_refusal_does_not_create_request(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.archival.create",),
    )
    before = ArchivalRequest.objects.count()
    response = client.post("/api/v1/badms/archival-requests/", {"file_name": "missing.tar"})

    assert response.status_code == 400, (test_id, source_id)
    assert ArchivalRequest.objects.count() == before


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_006", "CFR-BA-006", id="FR_CFR_BA_006__CFR_BA_006"),
        pytest.param("FR_AFR_BA_025", "AFR-BA-025", id="FR_AFR_BA_025__AFR_BA_025"),
        pytest.param("FR_AFR_BA_026", "AFR-BA-026", id="FR_AFR_BA_026__AFR_BA_026"),
        pytest.param("FR_AFR_BA_027", "AFR-BA-027", id="FR_AFR_BA_027__AFR_BA_027"),
    ],
)
def test_hod_review_records_approval_rejection_and_routing(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    approved = _submitted_archival()
    rejected = _submitted_archival(_user(1002))
    approved = archival.decide_archival_request(_hod(), approved.id, "approve", "Approved")
    rejected = archival.decide_archival_request(_hod(), rejected.id, "reject", "Rejected")

    assert approved.status == ArchivalRequest.STATUS_HOD_APPROVED, (test_id, source_id)
    assert approved.hod_reviewed_by_user_id == 5001
    assert approved.hod_decision_at is not None
    assert approved.hod_remarks == "Approved"
    assert rejected.status == ArchivalRequest.STATUS_REJECTED
    assert rejected.hod_remarks == "Rejected"
    assert AuditEvent.objects.filter(
        event_type="archival_request_hod_approved", target_id=approved.id
    ).exists()


@pytest.mark.skip(
    reason="NOT_AUTOMATED: archival requests do not expose the required policy-review context."
)
def test_fr_afr_ba_024_afr_ba_024_hod_review_context():
    """FR_AFR_BA_024; source_id: AFR-BA-024 — explicit requirement."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_007", "CFR-BA-007", id="FR_CFR_BA_007__CFR_BA_007"),
        pytest.param("FR_AFR_BA_028", "AFR-BA-028", id="FR_AFR_BA_028__AFR_BA_028"),
        pytest.param("FR_AFR_BA_030", "AFR-BA-030", id="FR_AFR_BA_030__AFR_BA_030"),
        pytest.param("FR_AFR_BA_031", "AFR-BA-031", id="FR_AFR_BA_031__AFR_BA_031"),
        pytest.param("FR_AFR_BA_056", "AFR-BA-056", id="FR_AFR_BA_056__AFR_BA_056"),
        pytest.param("FR_CFR_BA_015", "CFR-BA-015", id="FR_CFR_BA_015__CFR_BA_015"),
    ],
)
def test_authoritative_classification_applies_retention_and_sensitive_route(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    configured_days = {"Sensitive": 777, "Critical": 1111, "Routine": 222, "Archival": 3333}
    for classification, retention_days in configured_days.items():
        RetentionPolicy.objects.create(
            name=f"Institute {classification} retention",
            data_classification=classification,
            retention_days=retention_days,
            configured_by_user_id=7001,
        )
    sensitive = archival.classify_archival_request(
        _sysadmin(), _approved_archival(classification="Sensitive").id, "Sensitive"
    )
    classified_requests = []
    for classification in ("Critical", "Routine", "Archival"):
        request = archival.classify_archival_request(
            _sysadmin(), _approved_archival(classification=classification).id, classification
        )
        classified_requests.append(request)

    assert sensitive.status == ArchivalRequest.STATUS_CLASSIFIED_SENSITIVE, (test_id, source_id)
    assert sensitive.authoritative_classification == "Sensitive"
    assert sensitive.retention_policy_ref == "Institute Sensitive retention (777d)"
    assert sensitive.sysadmin_classified_by_user_id == 6001
    assert {request.authoritative_classification for request in classified_requests} == {
        "Critical",
        "Routine",
        "Archival",
    }
    assert all(
        request.retention_policy_ref == (
            f"Institute {request.authoritative_classification} retention "
            f"({configured_days[request.authoritative_classification]}d)"
        )
        for request in classified_requests
    )


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the implementation does not expose encryption-in-transit evidence."
)
def test_fr_cfr_ba_008_cfr_ba_008_sensitive_encryption_in_transit():
    """FR_CFR_BA_008; source_id: CFR-BA-008 — primary end-to-end behaviour."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_032", "AFR-BA-032", id="FR_AFR_BA_032__AFR_BA_032"),
        pytest.param("FR_AFR_BA_033", "AFR-BA-033", id="FR_AFR_BA_033__AFR_BA_033"),
    ],
)
def test_it_security_encryption_creates_recorded_archive(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    classified = archival.classify_archival_request(
        _sysadmin(), _approved_archival(classification="Sensitive").id, "Sensitive"
    )
    encrypted = archival.configure_sensitive_encryption(
        _security(), classified.id, encryption_algorithm="AES-256-GCM"
    )

    assert encrypted.status == ArchivalRequest.STATUS_SENSITIVE_ENCRYPTED, (test_id, source_id)
    assert encrypted.is_encrypted is True
    assert encrypted.encryption_algorithm == "AES-256-GCM"
    assert encrypted.encrypted_by_user_id == 7001
    assert encrypted.encrypted_at is not None
    assert AuditEvent.objects.filter(
        event_type="archival_encryption_configured", target_id=encrypted.id
    ).exists()


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the implementation does not expose encryption-in-transit evidence."
)
def test_fr_afr_ba_034_afr_ba_034_aes_256_at_rest_and_in_transit():
    """FR_AFR_BA_034; source_id: AFR-BA-034 — explicit requirement."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: archival submission and decision notifications are not recorded or exposed."
)
def test_fr_cfr_ba_009_cfr_ba_009_archival_tracking_and_notifications():
    """FR_CFR_BA_009; source_id: CFR-BA-009 — primary end-to-end behaviour."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: archival history is not exposed to the requester."
)
def test_fr_afr_ba_035_afr_ba_035_requester_tracks_archival_status():
    """FR_AFR_BA_035; source_id: AFR-BA-035 — explicit requirement."""
@pytest.mark.skip(
    reason="NOT_AUTOMATED: archival submission and decision notifications are not recorded or exposed."
)
def test_fr_afr_ba_036_afr_ba_036_archival_notifications():
    """FR_AFR_BA_036; source_id: AFR-BA-036 — explicit requirement."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_010", "CFR-BA-010", id="FR_CFR_BA_010__CFR_BA_010"),
        pytest.param("FR_AFR_BA_037", "AFR-BA-037", id="FR_AFR_BA_037__AFR_BA_037"),
        pytest.param("FR_AFR_BA_038", "AFR-BA-038", id="FR_AFR_BA_038__AFR_BA_038"),
        pytest.param("FR_AFR_BA_039", "AFR-BA-039", id="FR_AFR_BA_039__AFR_BA_039"),
    ],
)
def test_super_admin_special_archival_records_outcome_and_audit(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    client = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.archival.manage",),
    )
    response = client.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "file_name": "sensitive-research.tar",
            "file_type": "tar",
            "file_size_bytes": 100,
            "reason": "Offline authority request",
            "file_storage_path": "/secure/sensitive-research.tar",
            "classification": "Sensitive",
        },
    )

    assert response.status_code == 201, (test_id, source_id)
    request = ArchivalRequest.objects.get(id=response.json()["id"])
    assert request.status == ArchivalRequest.STATUS_SPECIAL_ARCHIVED
    assert request.is_special_archival is True
    assert request.authoritative_classification == "Sensitive"
    assert AuditEvent.objects.filter(
        event_type="special_archival_performed", target_id=request.id
    ).exists()


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_011", "CFR-BA-011", id="FR_CFR_BA_011__CFR_BA_011"),
        pytest.param("FR_AFR_BA_040", "AFR-BA-040", id="FR_AFR_BA_040__AFR_BA_040"),
        pytest.param("FR_AFR_BA_041", "AFR-BA-041", id="FR_AFR_BA_041__AFR_BA_041"),
        pytest.param("FR_AFR_BA_042", "AFR-BA-042", id="FR_AFR_BA_042__AFR_BA_042"),
        pytest.param("FR_AFR_BA_043", "AFR-BA-043", id="FR_AFR_BA_043__AFR_BA_043"),
    ],
)
def test_restoration_sensitive_approval_and_standard_path(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    sensitive = _archival_request(
        status="sensitive_archive_encrypted", classification="Sensitive"
    )
    routine = _archival_request(requester_id=1002, status="classified_non_sensitive")
    sensitive_request = restoration.request_data_restoration(
        _user(), sensitive.id, "/restore/sensitive"
    )
    standard_request = restoration.request_data_restoration(
        _user(1002), routine.id, "/restore/routine"
    )
    approved = restoration.approve_sensitive_restoration(_sysadmin(), sensitive_request.id, "approve")
    sensitive_done = restoration.execute_data_restoration(_sysadmin(), approved.id)
    routine_done = restoration.execute_data_restoration(_sysadmin(), standard_request.id)

    assert sensitive_request.status == "sensitive_pending_approval", (test_id, source_id)
    assert sensitive_done.status == "restored"
    assert routine_done.status == "restored"
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.restoration.view",),
    )
    response = client.get("/api/v1/badms/restorations/")
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == sensitive_request.id


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_045", "AFR-BA-045", id="FR_AFR_BA_045__AFR_BA_045"),
        pytest.param("FR_AFR_BA_046", "AFR-BA-046", id="FR_AFR_BA_046__AFR_BA_046"),
        pytest.param("FR_AFR_BA_047", "AFR-BA-047", id="FR_AFR_BA_047__AFR_BA_047"),
        pytest.param("FR_AFR_BA_049", "AFR-BA-049", id="FR_AFR_BA_049__AFR_BA_049"),
    ],
)
def test_storage_extension_submission_review_and_decision(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    quota = _full_quota()
    submitted = storage.submit_storage_extension(_user(), 500, "Research data")
    approved = storage.decide_storage_extension(_hod(), submitted.id, "approve", "Capacity available")

    rejected_quota = _full_quota(1002)
    rejected = storage.submit_storage_extension(_user(1002), 500, "Separate request")
    rejected = storage.decide_storage_extension(_hod(), rejected.id, "reject", "Policy refusal")
    quota.refresh_from_db()
    rejected_quota.refresh_from_db()

    assert submitted.status == "submitted", (test_id, source_id)
    assert submitted.current_usage_bytes == 1000
    assert submitted.current_quota_bytes == 1000
    assert approved.status == "approved"
    assert approved.hod_reviewed_by_user_id == 5001
    assert quota.allocated_quota_bytes == 1500
    assert rejected.status == "rejected"
    assert rejected_quota.allocated_quota_bytes == 1000


@pytest.mark.skip(
    reason="NOT_AUTOMATED: available storage-infrastructure capacity is not modeled or exposed."
)
def test_fr_cfr_ba_012_cfr_ba_012_storage_extension_infrastructure_review():
    """FR_CFR_BA_012; source_id: CFR-BA-012 — primary end-to-end behaviour."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: storage-extension requests have no attachment, infrastructure, or policy-review fields."
)
def test_fr_afr_ba_048_afr_ba_048_storage_review_context():
    """FR_AFR_BA_048; source_id: AFR-BA-048 — explicit requirement."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_013", "CFR-BA-013", id="FR_CFR_BA_013__CFR_BA_013"),
        pytest.param("FR_AFR_BA_051", "AFR-BA-051", id="FR_AFR_BA_051__AFR_BA_051"),
    ],
)
def test_storage_threshold_monitoring_maintains_full_condition(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    full = UserStorageQuota.objects.create(
        user_id=1, allocated_quota_bytes=100, used_storage_bytes=100, is_full=False
    )
    available = UserStorageQuota.objects.create(
        user_id=2, allocated_quota_bytes=100, used_storage_bytes=99, is_full=True
    )
    result = monitor_storage_thresholds()
    full.refresh_from_db()
    available.refresh_from_db()

    assert result["updated"] == 2, (test_id, source_id)
    assert full.is_full is True
    assert available.is_full is False


@pytest.mark.skip(
    reason="NOT_AUTOMATED: available storage-infrastructure capacity is not modeled or exposed."
)
def test_fr_afr_ba_052_afr_ba_052_infrastructure_capacity_validation():
    """FR_AFR_BA_052; source_id: AFR-BA-052 — explicit requirement."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_054", "AFR-BA-054", id="FR_AFR_BA_054__AFR_BA_054"),
        pytest.param("FR_AFR_BA_055", "AFR-BA-055", id="FR_AFR_BA_055__AFR_BA_055"),
    ],
)
def test_global_schedule_and_local_override_precedence(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    client = _client(
        stub_iam,
        user_id=1,
        roles=("Super Admin",),
        active_role="Super Admin",
        modules=("badms",),
        permissions=("badms.backup_policy.manage",),
    )
    response = client.post(
        "/api/v1/badms/schedules/global/",
        {
            "name": "Institution default",
            "dataset_name": "fr_global",
            "cron_expression": "0 1 * * *",
        },
    )
    assert response.status_code == 201, (test_id, source_id)
    global_schedule = response.json()
    local_schedule = {"id": 2, "is_active": True}

    assert schedule_domain.resolve_effective_schedule(None, global_schedule) == global_schedule
    assert schedule_domain.resolve_effective_schedule(local_schedule, global_schedule) == local_schedule


@pytest.mark.skip(
    reason="NOT_AUTOMATED: a global default backup-policy model is not implemented or exposed."
)
def test_fr_cfr_ba_014_cfr_ba_014_global_schedule_and_defaults():
    """FR_CFR_BA_014; source_id: CFR-BA-014 — primary end-to-end behaviour."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: a global default backup-policy model is not implemented or exposed."
)
def test_fr_afr_ba_053_afr_ba_053_global_backup_schedule_and_policy():
    """FR_AFR_BA_053; source_id: AFR-BA-053 — explicit requirement."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: backup creation-status and completion notifications are not recorded or exposed."
)
def test_fr_cfr_ba_016_cfr_ba_016_backup_notification_and_escalation_suite():
    """FR_CFR_BA_016; source_id: CFR-BA-016 — primary end-to-end behaviour."""


@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_AFR_BA_057", "AFR-BA-057", id="FR_AFR_BA_057__AFR_BA_057"),
        pytest.param("FR_AFR_BA_058", "AFR-BA-058", id="FR_AFR_BA_058__AFR_BA_058"),
    ],
)
def test_backup_failure_alert_and_three_failure_escalation(test_id, source_id):
    """FR case and source identifiers are included in this parametrized test name."""
    before = datetime.now(UTC)
    failures = [backups.execute_scheduled_backup("fr_escalation", simulate_failure=True) for _ in range(3)]
    alert = AuditEvent.objects.filter(
        event_type="backup_failure_alert_sent", target_id=failures[0].id
    ).get()
    escalation = AuditEvent.objects.filter(
        event_type="backup_failure_escalated", target_id=failures[-1].id
    ).get()

    assert alert.timestamp >= before, (test_id, source_id)
    assert alert.timestamp - failures[0].completed_at <= timedelta(minutes=5)
    assert failures[-1].consecutive_failure_count == 3
    assert escalation.details["recipient_role"] == "Director of IT"


@pytest.mark.skip(
    reason="NOT_AUTOMATED: storage-extension submission and decision notifications are not recorded or exposed."
)
def test_fr_cfr_ba_017_cfr_ba_017_storage_extension_notifications():
    """FR_CFR_BA_017; source_id: CFR-BA-017 — primary end-to-end behaviour."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: storage-extension submission and decision notifications are not recorded or exposed."
)
def test_fr_afr_ba_060_afr_ba_060_storage_extension_notifications():
    """FR_AFR_BA_060; source_id: AFR-BA-060 — explicit requirement."""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: backup creation-status and completion notifications are not recorded or exposed."
)
def test_fr_afr_ba_059_afr_ba_059_backup_status_completion_notifications():
    """FR_AFR_BA_059; source_id: AFR-BA-059 — explicit requirement."""
@pytest.mark.parametrize(
    ("test_id", "source_id"),
    [
        pytest.param("FR_CFR_BA_018", "CFR-BA-018", id="FR_CFR_BA_018__CFR_BA_018"),
        pytest.param("FR_AFR_BA_061", "AFR-BA-061", id="FR_AFR_BA_061__AFR_BA_061"),
        pytest.param("FR_AFR_BA_062", "AFR-BA-062", id="FR_AFR_BA_062__AFR_BA_062"),
        pytest.param("FR_AFR_BA_063", "AFR-BA-063", id="FR_AFR_BA_063__AFR_BA_063"),
        pytest.param("FR_AFR_BA_064", "AFR-BA-064", id="FR_AFR_BA_064__AFR_BA_064"),
        pytest.param("FR_AFR_BA_065", "AFR-BA-065", id="FR_AFR_BA_065__AFR_BA_065"),
    ],
)
def test_audit_logs_and_operational_views_are_role_scoped(test_id, source_id, stub_iam):
    """FR case and source identifiers are included in this parametrized test name."""
    AuditEvent.objects.bulk_create(
        [
            AuditEvent(
                event_type=event_type,
                actor_user_id=6001,
                actor_role="SysAdmin",
                target_model="BackupRecord",
                target_id=1,
                department="CSE",
                details={"outcome": "success"},
            )
            for event_type in ("user.action", "admin.action", "system.event", "security.event")
        ]
    )
    sysadmin = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.audit.view", "badms.report.view", "badms.backup.view"),
    )
    audit_response = sysadmin.get("/api/v1/badms/audit-logs/")
    backup_response = sysadmin.get("/api/v1/badms/backups/")
    assert audit_response.status_code == 200, (test_id, source_id)
    assert backup_response.status_code == 200
    assert {event["event_type"] for event in audit_response.json()["results"]} == {
        "user.action",
        "admin.action",
        "system.event",
        "security.event",
    }
    assert all(event["timestamp"] and event["actor_user_id"] for event in audit_response.json()["results"])

    security = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.audit.view",),
    )
    assert security.get("/api/v1/badms/audit-logs/security/").status_code == 200

    hod = _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.report.view",),
    )
    assert hod.get("/api/v1/badms/reports/department/?department=CSE").status_code == 200


@pytest.mark.skip(
    reason="NOT_AUTOMATED: security-policy enforcement is not implemented or exposed."
)
def test_fr_afr_ba_067_afr_ba_067_it_security_security_policy():
    """FR_AFR_BA_067; source_id: AFR-BA-067 — explicit requirement."""
def test_fr_afr_ba_001_deny_unauthorized_afr_ba_001_refusal(stub_iam):
    """FR_AFR_BA_001_DENY_UNAUTHORIZED; source_id: AFR-BA-001 — actor outside SysAdmin and Super Admin roles."""
    client = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.backup.view",),
    )
    before = BackupRecord.objects.count()
    response = client.post("/api/v1/badms/backups/manual/", {"dataset_name": "forbidden"})

    assert response.status_code == 403
    assert BackupRecord.objects.count() == before


def test_fr_afr_ba_026_cross_department_afr_ba_026_refusal(stub_iam):
    """FR_AFR_BA_026_CROSS_DEPARTMENT; source_id: AFR-BA-026 — HoD outside requester department."""
    request = _archival_request(department="CSE")
    client = _client(
        stub_iam,
        user_id=5002,
        roles=("HOD (ECE)",),
        active_role="HOD (ECE)",
        modules=("badms",),
        permissions=("badms.archival.approve",),
    )
    response = client.post(
        f"/api/v1/badms/archival-requests/{request.id}/decide/", {"decision": "approve"}
    )

    assert response.status_code == 404
    request.refresh_from_db()
    assert request.status == "submitted"
    assert request.hod_reviewed_by_user_id is None


def test_fr_afr_ba_038_non_super_admin_afr_ba_038_refusal(stub_iam):
    """FR_AFR_BA_038_NON_SUPER_ADMIN_REFUSED; source_id: AFR-BA-038 — actor other than Super Admin."""
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.review",),
    )
    before = ArchivalRequest.objects.filter(is_special_archival=True).count()
    response = client.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "file_name": "forbidden.tar",
            "file_type": "tar",
            "file_size_bytes": 100,
            "reason": "Forbidden",
            "file_storage_path": "/secure/forbidden.tar",
        },
    )

    assert response.status_code == 403
    assert ArchivalRequest.objects.filter(is_special_archival=True).count() == before


def test_fr_afr_ba_041_no_approval_afr_ba_041_refusal(stub_iam):
    """FR_AFR_BA_041_NO_APPROVAL_NO_RESTORE; source_id: AFR-BA-041 — Sensitive restoration before SysAdmin approval."""
    archive = _archival_request(status="sensitive_archive_encrypted", classification="Sensitive")
    request = restoration.request_data_restoration(_user(), archive.id, "/restore/pending")
    client = _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.restoration.restore",),
    )
    response = client.post(f"/api/v1/badms/restorations/{request.id}/execute/", {})

    assert response.status_code == 409
    request.refresh_from_db()
    assert request.status == "sensitive_pending_approval"
    assert request.restored_at is None


@pytest.mark.skip(
    reason="NOT_AUTOMATED: IT Security RBAC permission management is not implemented or exposed."
)
def test_fr_cfr_ba_019_cfr_ba_019_role_separation():
    """FR_CFR_BA_019; source_id: CFR-BA-019 — primary end-to-end behaviour."""
@pytest.mark.skip(
    reason="NOT_AUTOMATED: IT Security RBAC permission management is not implemented or exposed."
)
def test_fr_afr_ba_066_afr_ba_066_it_security_rbac_policy_endpoint():
    """FR_AFR_BA_066; source_id: AFR-BA-066 — explicit requirement."""
def test_fr_afr_ba_068_afr_ba_068_department_and_technical_role_separation(stub_iam):
    """FR_AFR_BA_068; source_id: AFR-BA-068 — explicit requirement."""
    request = _archival_request(department="CSE")
    user = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.archival.create",),
    )
    classify = user.post(
        f"/api/v1/badms/archival-requests/{request.id}/classify/", {"classification": "Sensitive"}
    )
    assert classify.status_code == 403
    request.refresh_from_db()
    assert request.status == "submitted"
