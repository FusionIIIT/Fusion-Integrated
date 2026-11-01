import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import IamSession


@pytest.mark.django_db
def test_complaint_submission_requires_module_and_permission(stub_iam):
    client = APIClient()
    response = client.post("/api/v1/complaints/", {
        "category": "Facilities", "description": "A broken light",
    }, format="json")

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_complaint_submission_requires_create_permission(stub_iam):
    stub_iam(make_session(user_id=123, modules=("complaints",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.post("/api/v1/complaints/", {
        "category": "Facilities", "description": "A broken light",
    }, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_complaint_submission_requires_module_grant(stub_iam):
    stub_iam(make_session(user_id=123,
                          permissions=("complaints.complaint.create",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.post("/api/v1/complaints/", {
        "category": "Facilities", "description": "A broken light",
    }, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_submit_returns_reference_and_records_confirmation(stub_iam):
    from modules.complaints.models import Complaint, ComplaintNotification

    stub_iam(make_session(user_id=123,
                          permissions=("complaints.complaint.create",),
                          modules=("complaints",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.post("/api/v1/complaints/", {
        "category": "Facilities", "description": "A broken light",
    }, format="json")

    assert response.status_code == 201
    assert response.data["complaint_id"]
    assert response.data["submitted_at"]
    assert Complaint.objects.count() == 1
    assert ComplaintNotification.objects.get().status == "pending"


@pytest.mark.django_db
def test_submission_stores_uploaded_attachment(stub_iam, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from modules.complaints.models import ComplaintAttachment

    settings.COMPLAINT_ATTACHMENT_ROOT = str(tmp_path)
    settings.COMPLAINT_ATTACHMENT_CONTENT_TYPES = ("application/pdf",)
    settings.COMPLAINT_ATTACHMENT_MAX_BYTES = 1000
    stub_iam(IamSession(
        user_id=123, username="u123", display_name="User 123", kind="student",
        email="person@example.test", active_role="student", roles=("student",),
        permissions=frozenset({"complaints.complaint.create"}), modules=("complaints",),
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    upload = SimpleUploadedFile("evidence.pdf", b"sample evidence",
                                content_type="application/pdf")
    response = client.post("/api/v1/complaints/", {
        "category": "Facilities", "description": "A broken light",
        "attachments": [upload],
    }, format="multipart")

    assert response.status_code == 201
    attachment = ComplaintAttachment.objects.get()
    stored = (tmp_path / attachment.storage_key[:2] /
              attachment.storage_key[2:4] / attachment.storage_key)
    assert stored.read_bytes() == b"sample evidence"
    assert len(attachment.sha256) == 64


@pytest.mark.django_db
def test_confirmation_notification_is_delivered(stub_iam, settings, monkeypatch):
    from modules.complaints.models import Complaint, ComplaintNotification
    from modules.complaints.services import deliver_pending

    settings.DEFAULT_FROM_EMAIL = "noreply@example.test"
    settings.COMPLAINT_NOTIFICATION_MAX_ATTEMPTS = 3
    complaint = Complaint.objects.create(
        complainant_user_id=123, category="Facilities", description="A broken light",
    )
    notification = ComplaintNotification.objects.create(
        complaint=complaint, recipient_user_id=123,
        recipient_email="person@example.test",
    )
    sent = []
    monkeypatch.setattr("modules.complaints.services.send_mail",
                        lambda **kwargs: sent.append(kwargs) or 1)

    result = deliver_pending()
    notification.refresh_from_db()

    assert result["sent"] == 1
    assert notification.status == "sent"
    assert notification.sent_at is not None
    assert sent[0]["recipient_list"] == ["person@example.test"]
