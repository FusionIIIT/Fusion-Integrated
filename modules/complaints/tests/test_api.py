from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.complaints.models import (
    Announcement,
    Complaint,
    ComplaintAttachment,
    Escalation,
    NotificationOutbox,
)
from modules.complaints.services import complaints as service

pytestmark = pytest.mark.django_db

CREATE = "complaints.complaint.create"
VIEW = "complaints.complaint.view"
FEEDBACK = "complaints.feedback.create"
ANNOUNCE_VIEW = "complaints.announcement.view"
ANNOUNCE_PUBLISH = "complaints.announcement.publish"


def as_user(stub_iam, user_id=1001, permissions=(CREATE, VIEW), modules=("complaints",)):
    stub_iam(
        make_session(user_id=user_id, kind="student", modules=modules, permissions=permissions)
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token cms-test")
    return client


def test_submission_requires_idempotency_key(stub_iam):
    client = as_user(stub_iam)
    response = client.post(
        "/api/v1/complaints/complaints",
        {"category": "Facilities", "description": "Broken tap"},
        format="json",
    )
    assert response.status_code == 400
    assert Complaint.objects.count() == 0


def test_submission_records_and_replays_the_same_request(stub_iam):
    client = as_user(stub_iam)
    headers = {"HTTP_IDEMPOTENCY_KEY": "cms-submit-001"}
    body = {"category": "Facilities", "description": "Broken tap"}

    first = client.post("/api/v1/complaints/complaints", body, format="json", **headers)
    replay = client.post("/api/v1/complaints/complaints", body, format="json", **headers)

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.data == first.data
    assert Complaint.objects.count() == 1
    assert NotificationOutbox.objects.count() == 1


def test_idempotency_key_cannot_be_reused_with_different_body(stub_iam):
    client = as_user(stub_iam)
    headers = {"HTTP_IDEMPOTENCY_KEY": "cms-submit-002"}
    client.post(
        "/api/v1/complaints/complaints",
        {"category": "Facilities", "description": "Broken tap"},
        format="json",
        **headers,
    )
    response = client.post(
        "/api/v1/complaints/complaints",
        {"category": "IT", "description": "Cannot log in"},
        format="json",
        **headers,
    )
    assert response.status_code == 409
    assert Complaint.objects.count() == 1


def test_complainant_cannot_read_another_users_complaint(stub_iam):
    complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
    client = as_user(stub_iam)
    response = client.get(f"/api/v1/complaints/complaints/{complaint.reference}")
    assert response.status_code == 404


def test_user_without_module_grant_is_denied(stub_iam):
    client = as_user(stub_iam, modules=())
    response = client.get("/api/v1/complaints/complaints")
    assert response.status_code == 403


def test_complainant_can_read_only_their_complaint(stub_iam):
    mine = service.submit(user_id=1001, category="Facilities", description="Broken tap")
    service.submit(user_id=2002, category="IT", description="Cannot log in")
    client = as_user(stub_iam)
    response = client.get("/api/v1/complaints/complaints")
    assert response.status_code == 200
    assert [row["reference"] for row in response.data["results"]] == [str(mine.reference)]


def test_feedback_is_only_accepted_after_resolution(stub_iam):
    complaint = service.submit(user_id=1001, category="Facilities", description="Broken tap")
    client = as_user(stub_iam, permissions=(VIEW, FEEDBACK))
    response = client.post(
        f"/api/v1/complaints/complaints/{complaint.reference}/feedback",
        {"message": "Thank you"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="cms-feedback-001",
    )
    assert response.status_code == 409


def test_announcement_publishing_requires_permission(stub_iam):
    client = as_user(stub_iam, permissions=(ANNOUNCE_VIEW, ANNOUNCE_PUBLISH))
    response = client.post(
        "/api/v1/complaints/announcements",
        {"title": "Service update", "body": "The portal is available."},
        format="json",
        HTTP_IDEMPOTENCY_KEY="cms-announcement-001",
    )
    assert response.status_code == 201
    assert Announcement.objects.count() == 1


def test_assignment_starts_work_and_assigned_handler_can_update(stub_iam):
    complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
    supervisor = as_user(stub_iam, user_id=8000, permissions=("complaints.complaint.assign",))
    with patch(
        "modules.directory.contracts.get_users",
        return_value={
            3001: SimpleNamespace(kind="staff", is_active=True),
        },
    ):
        response = supervisor.post(
            f"/api/v1/complaints/complaints/{complaint.reference}/assign",
            {"assignee_user_id": 3001, "priority": "high", "category": "Facilities"},
            format="json",
        )
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert (complaint.status, complaint.assigned_to_user_id, complaint.priority) == (
        "in_progress",
        3001,
        "high",
    )
    handler = as_user(stub_iam, user_id=3001, permissions=("complaints.complaint.update",))
    response = handler.post(
        f"/api/v1/complaints/complaints/{complaint.reference}/progress",
        {"details": "Technician inspected the issue."},
        format="json",
    )
    assert response.status_code == 200
    assert complaint.history.filter(event="progress_updated").exists()


def test_approved_reopening_returns_complaint_to_active_handling(monkeypatch):
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda ids: {3001: SimpleNamespace(kind="staff", is_active=True)},
    )
    complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
    service.assign(
        reference=complaint.reference,
        actor_user_id=8000,
        assignee_user_id=3001,
        priority="medium",
        category="Facilities",
    )
    service.resolve(reference=complaint.reference, actor_user_id=3001, details="Fixed")
    service.verify_closure(
        reference=complaint.reference, actor_user_id=2002, actor_kind="complainant"
    )
    reopening = service.request_reopening(
        reference=complaint.reference, user_id=2002, reason="The leak returned"
    )
    service.review_reopening(request_id=reopening.pk, actor_user_id=8001, decision="approved")
    complaint.refresh_from_db()
    assert complaint.status == "in_progress"
    assert complaint.closed_at is None
    assert complaint.history.filter(event="reopened").exists()


def test_generic_sla_policy_creates_one_escalation_and_reminder(monkeypatch):
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda ids: {3001: SimpleNamespace(kind="staff", is_active=True)},
    )
    complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
    service.assign(
        reference=complaint.reference,
        actor_user_id=8000,
        assignee_user_id=3001,
        priority="medium",
        category="Facilities",
    )
    complaint.refresh_from_db()
    now = complaint.sla_due_at - timedelta(hours=22)
    counts = service.process_sla(now=now)
    complaint.refresh_from_db()
    assert counts == {"reminded": 1, "escalated": 0}
    assert complaint.sla_reminded_at == now
    counts = service.process_sla(now=complaint.sla_due_at + timedelta(seconds=1))
    assert counts["escalated"] == 1
    assert Escalation.objects.filter(complaint=complaint, source="sla").count() == 1
    assert service.process_sla(now=complaint.sla_due_at + timedelta(hours=1))["escalated"] == 0


def test_disabling_verification_closes_after_resolution(monkeypatch):
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda ids: {3001: SimpleNamespace(kind="staff", is_active=True)},
    )
    with override_settings(CMS_REQUIRE_CLOSURE_VERIFICATION=False):
        complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
        service.assign(
            reference=complaint.reference,
            actor_user_id=8000,
            assignee_user_id=3001,
            priority="medium",
            category="Facilities",
        )
        service.resolve(reference=complaint.reference, actor_user_id=3001, details="Fixed")
        complaint.refresh_from_db()
        assert complaint.status == "closed"
        assert complaint.history.filter(event="closed_without_verification").exists()


def test_attachment_checks_file_signature_and_stores_private_file(tmp_path):
    complaint = service.submit(user_id=2002, category="Facilities", description="Broken tap")
    with override_settings(
        PLACEMENT_UPLOAD_ROOT=str(tmp_path),
        CMS_ATTACHMENT_MAX_BYTES=1024,
        CMS_ATTACHMENT_MAX_COUNT=5,
        CMS_ATTACHMENT_ALLOWED_TYPES=("application/pdf", "image/jpeg", "image/png"),
    ):
        row = service.attach_file(
            reference=complaint.reference,
            user_id=2002,
            uploaded_file=SimpleUploadedFile("proof.pdf", b"%PDF-1.7 evidence"),
        )
        from core.files.storage import path_for

        assert row.content_type == "application/pdf"
        assert path_for(row.storage_key).read_bytes() == b"%PDF-1.7 evidence"
        with pytest.raises(service.InvalidSubmission):
            service.attach_file(
                reference=complaint.reference,
                user_id=2002,
                uploaded_file=SimpleUploadedFile("fake.pdf", b"not a pdf"),
            )


def test_submission_accepts_attachments_and_replays_same_multipart_request(stub_iam, tmp_path):
    client = as_user(stub_iam)
    with override_settings(PLACEMENT_UPLOAD_ROOT=str(tmp_path)):

        def post():
            return client.post(
                "/api/v1/complaints/complaints",
                {
                    "category": "Facilities",
                    "description": "Broken tap",
                    "attachments": [SimpleUploadedFile("proof.pdf", b"%PDF-1.7 proof")],
                },
                format="multipart",
                HTTP_IDEMPOTENCY_KEY="cms-submit-file-001",
            )

        first = post()
        replay = post()
    assert first.status_code == replay.status_code == 201
    assert replay.data == first.data
    assert ComplaintAttachment.objects.count() == 1
    assert Complaint.objects.count() == 1
