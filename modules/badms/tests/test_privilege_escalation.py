"""Write and administrative authority checks across BADMS endpoints."""

from datetime import date
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import ArchiveRequest, RestorationRequest, StorageExtensionRequest
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id=5001, permissions=(), kind="student", role="student", dept="CSE"):
    UserRef.objects.update_or_create(
        user_id=user_id,
        defaults={
            "username": f"user-{user_id}",
            "display_name": f"User {user_id}",
            "kind": kind,
            "email": f"user{user_id}@example.test",
            "department": dept,
            "is_active": True,
        },
    )
    session = make_session(
        user_id=user_id,
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=("badms",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token test-{user_id}")
    return client


@override_settings(DEBUG=True)
def test_unauthorized_users_refused_across_all_actions(stub_iam):
    unprivileged = _client(stub_iam, user_id=5001, permissions=())

    archive = ArchiveRequest.objects.create(
        user_id=101,
        department="CSE",
        requester_email="u101@example.test",
        file_name="doc.pdf",
        file_date=date(2026, 1, 1),
        owners=["User 101"],
        file_type="PDF",
        reason="Test",
        attachment_key="badms/doc.pdf",
        attachment_size_bytes=100,
        status="Submitted",
        classification="Routine",
    )

    resp = unprivileged.post(
        f"/api/v1/badms/archive_requests/{archive.pk}/decision",
        {"approve": True},
        format="json",
    )
    assert resp.status_code == 403

    resp = unprivileged.post(
        f"/api/v1/badms/archive_requests/{archive.pk}/classification",
        {"classification": "Sensitive"},
        format="json",
    )
    assert resp.status_code == 403

    resp = unprivileged.post(
        f"/api/v1/badms/archive_requests/{archive.pk}/encryption",
        {"kms_key_id": "k1", "cipher_suite": "AES-256-GCM"},
        format="json",
    )
    assert resp.status_code == 403

    resp = unprivileged.post("/api/v1/badms/backup_runs", {}, format="json")
    assert resp.status_code == 403

    resp = unprivileged.post(
        "/api/v1/badms/special_archives",
        {"offline_request_reference": "ref", "research_description": "desc"},
        format="multipart",
    )
    assert resp.status_code == 403

    resp = unprivileged.get("/api/v1/badms/reports/department")
    assert resp.status_code == 403

    resp = unprivileged.get("/api/v1/badms/reports/security")
    assert resp.status_code == 403

    resp = unprivileged.put(
        "/api/v1/badms/security_policies",
        {"retention_days": {"Critical": 100}},
        format="json",
    )
    assert resp.status_code == 403
