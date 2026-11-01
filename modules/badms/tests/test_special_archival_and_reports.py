"""Tests for BADMS Special Archival, Audit Logs, and Retention Reporting (Phase 11)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
    BadmsAuditLog,
    SpecialArchivalRecord,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


def test_super_admin_can_perform_special_offline_archival(stub_iam):
    client = _client(
        stub_iam,
        user_id=1,
        kind="staff",
        modules=("badms",),
        permissions=(p.ARCHIVE_SPECIAL, p.AUDIT_VIEW),
        active_role="Super Admin",
    )

    payload = {
        "requester_name": "Prof. R. Sharma",
        "requester_designation": "Dean of Research & Development",
        "dataset_title": "Quantum Cryptography Key Exchange Telemetry 2026",
        "classification": "Sensitive Research Data",
        "offline_media_type": "LTO-8 Ultrium Tape",
        "media_serial_number": "TAPE-QC-2026-009A",
        "storage_vault_location": "Bldg 3 Sub-Basement EMP-Shielded Vault Room 04",
        "notes": "Hand-delivered with chain of custody sign-off.",
    }

    res = client.post("/api/v1/badms/special-archives/", payload, format="json")
    assert res.status_code == 201, res.data

    data = res.data
    assert data["dataset_title"] == payload["dataset_title"]
    assert data["performed_by_user_id"] == 1
    assert data["media_serial_number"] == payload["media_serial_number"]
    assert data["checksum"] != ""

    # Verify audit entry
    audit = BadmsAuditLog.objects.filter(action="badms.archive.special").first()
    assert audit is not None
    assert audit.target_type == "special_archive"
    assert audit.outcome == "success"

    # Verify listing
    get_res = client.get("/api/v1/badms/special-archives/")
    assert get_res.status_code == 200
    assert get_res.data["count"] >= 1


def test_non_super_admin_cannot_perform_special_archival(stub_iam):
    client = _client(
        stub_iam,
        user_id=100,
        kind="staff",
        modules=("badms",),
        permissions=(p.ARCHIVE_CREATE, p.ARCHIVE_VIEW),
        active_role="sysadmin",
    )

    payload = {
        "requester_name": "Dr. Smith",
        "requester_designation": "PI",
        "dataset_title": "Genomics dataset",
        "offline_media_type": "Optical M-DISC",
        "media_serial_number": "DISC-001",
        "storage_vault_location": "Vault A",
    }
    res = client.post("/api/v1/badms/special-archives/", payload, format="json")
    assert res.status_code == 403


def test_special_archival_validation(stub_iam):
    client = _client(
        stub_iam,
        user_id=1,
        kind="staff",
        modules=("badms",),
        permissions=(p.ARCHIVE_SPECIAL,),
        active_role="Super Admin",
    )

    # Missing dataset title
    res = client.post(
        "/api/v1/badms/special-archives/",
        {
            "requester_name": "Prof. Sharma",
            "requester_designation": "Dean",
            "dataset_title": "",
            "offline_media_type": "Tape",
            "media_serial_number": "T123",
            "storage_vault_location": "Vault",
        },
        format="json",
    )
    assert res.status_code == 400


def test_audit_log_endpoint_and_filtering(stub_iam):
    # Create sample audit records
    BadmsAuditLog.objects.create(
        actor_user_id=1,
        actor_role="Super Admin",
        action="badms.archive.special",
        target_type="special_archive",
        target_id="1",
        outcome="success",
        details={"test": "one"},
    )
    BadmsAuditLog.objects.create(
        actor_user_id=2,
        actor_role="sysadmin",
        action="badms.backup.execute",
        target_type="backup",
        target_id="10",
        outcome="failed",
        details={"error": "timeout"},
    )

    client = _client(
        stub_iam,
        user_id=5,
        kind="staff",
        modules=("badms",),
        permissions=(p.AUDIT_VIEW,),
        active_role="it_security",
    )

    res = client.get("/api/v1/badms/audit-logs/")
    assert res.status_code == 200
    assert res.data["count"] >= 2

    # Filter by action
    filtered = client.get("/api/v1/badms/audit-logs/?action=backup")
    assert filtered.status_code == 200
    assert all("backup" in r["action"] for r in filtered.data["results"])


def test_retention_compliance_report(stub_iam):
    # Setup some test archives with classifications
    ArchivalRequest.objects.create(
        user_id=10,
        department="CSE",
        file_name="Code.zip",
        document_date="2026-01-01",
        file_type="zip",
        file_size_bytes=50000,
        reason="Source archive",
        initial_classification=ArchiveClassification.ROUTINE,
        authoritative_classification=ArchiveClassification.ROUTINE,
        status=ArchiveStatus.POLICY_APPLIED,
    )
    ArchivalRequest.objects.create(
        user_id=11,
        department="ECE",
        file_name="ChipLayout.gds",
        document_date="2026-01-01",
        file_type="gds",
        file_size_bytes=150000,
        reason="Patent design",
        initial_classification=ArchiveClassification.SENSITIVE,
        authoritative_classification=ArchiveClassification.SENSITIVE,
        status=ArchiveStatus.ENCRYPTED_ARCHIVE_CREATED,
        is_encrypted=True,
    )

    client = _client(
        stub_iam,
        user_id=20,
        kind="faculty",
        modules=("badms",),
        permissions=(p.REPORT_VIEW,),
        active_role="HOD",
    )

    res = client.get("/api/v1/badms/reports/summary/")
    assert res.status_code == 200, res.data

    data = res.data
    assert "archives" in data
    assert "backups" in data
    assert "restorations" in data
    assert "special_archives" in data
    assert "storage" in data
    assert data["archives"]["total"] >= 2
    assert data["archives"]["compliance_rate_percent"] > 0
