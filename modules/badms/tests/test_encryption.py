"""Tests for BADMS Encryption and Secure Archive Storage (Phase 5)."""
import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.badms.domain import permissions as p
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
    BadmsAuditLog,
    BadmsNotification,
)
from modules.badms.services.encryption import decrypt_bytes, encrypt_bytes
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


@pytest.fixture
def student_user():
    return UserRef.objects.create(
        user_id=1001,
        username="u1001",
        display_name="Student",
        kind="student",
        department="CSE",
        is_active=True,
    )


@pytest.fixture
def sensitive_archive_request(student_user):
    return ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="Genomics_Research.dat",
        document_date="2026-05-20",
        file_type="dat",
        file_size_bytes=524288,
        reason="Sensitive genomic sequence data",
        initial_classification=ArchiveClassification.ROUTINE,
        authoritative_classification=ArchiveClassification.SENSITIVE,
        status=ArchiveStatus.ROUTED_TO_SECURITY,
    )


def test_encrypt_and_decrypt_bytes():
    raw_text = b"CONFIDENTIAL LAB RESEARCH: Sequence ACGT123456789"
    key = "lab-secret-aes256-key-special"

    ciphertext = encrypt_bytes(raw_text, key)
    assert ciphertext != raw_text
    assert len(ciphertext) > 0

    decrypted = decrypt_bytes(ciphertext, key)
    assert decrypted == raw_text


def test_it_security_can_configure_encryption(stub_iam, sensitive_archive_request):
    client = _client(
        stub_iam,
        user_id=777,
        kind="staff",
        active_role="it_security",
        modules=("badms",),
        permissions=(p.ARCHIVE_ENCRYPT,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{sensitive_archive_request.pk}/configure-encryption/",
        {"algorithm": "AES-256-GCM", "key_id": "SEC-KEY-001"},
        format="json",
    )
    assert res.status_code == 200, res.data

    data = res.data
    assert data["status"] == ArchiveStatus.ENCRYPTED_ARCHIVE_CREATED
    assert data["is_encrypted"] is True
    assert data["encryption_algorithm"] == "AES-256-GCM"
    assert data["security_user_id"] == 777
    assert data["security_configured_at"] is not None

    # Verify audit log
    audit = BadmsAuditLog.objects.filter(
        target_id=str(sensitive_archive_request.pk), action="badms.archive.encrypt"
    ).first()
    assert audit is not None
    assert audit.actor_user_id == 777
    assert audit.outcome == "success"
    assert audit.details["algorithm"] == "AES-256-GCM"

    # Verify notifications
    req_notif = BadmsNotification.objects.filter(
        user_id=1001, notification_type="archive_encrypted"
    ).first()
    assert req_notif is not None
    assert "AES-256-GCM" in req_notif.message


def test_cannot_encrypt_unrouted_request(stub_iam, student_user):
    # Request in 'submitted' status
    submitted_req = ArchivalRequest.objects.create(
        user_id=1001,
        department="CSE",
        file_name="Regular_Doc.pdf",
        document_date="2026-05-20",
        file_type="pdf",
        file_size_bytes=1000,
        reason="Not ready for encryption",
        status=ArchiveStatus.SUBMITTED,
    )

    client = _client(
        stub_iam,
        user_id=777,
        kind="staff",
        active_role="it_security",
        modules=("badms",),
        permissions=(p.ARCHIVE_ENCRYPT,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{submitted_req.pk}/configure-encryption/",
        {"algorithm": "AES-256-GCM"},
        format="json",
    )
    assert res.status_code == 400
    assert "expected 'routed_to_security'" in res.data["detail"]


def test_unauthorized_user_cannot_configure_encryption(
    stub_iam, sensitive_archive_request
):
    # SysAdmin without badms.archive.encrypt
    client = _client(
        stub_iam,
        user_id=99,
        kind="staff",
        active_role="sysadmin",
        modules=("badms",),
        permissions=(p.ARCHIVE_CLASSIFY,),
    )

    res = client.post(
        f"/api/v1/badms/archives/{sensitive_archive_request.pk}/configure-encryption/",
        {"algorithm": "AES-256-GCM"},
        format="json",
    )
    assert res.status_code == 403
