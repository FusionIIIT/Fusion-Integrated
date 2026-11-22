from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone

from conftest import make_session
from modules.cms import services
from modules.cms.models import CmsRoleAssignment, Complaint
from modules.cms.services import submit


@pytest.mark.django_db
def test_user_submission_and_owner_scoped_complaint_access(stub_iam):
    fake = stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    response = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "The corridor light is out."},
        content_type="application/json",
    )
    assert response.status_code == 201
    complaint_id = response.json()["id"]
    assert response.json()["status"] == "submitted"
    assert response.json()["history"][0]["to_status"] == "submitted"

    response = client.get("/api/v1/cms/complaints/mine")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [complaint_id]

    fake.session = make_session(user_id=404, modules=("cms",), permissions=("cms.complaint.track",))
    assert client.get(f"/api/v1/cms/complaints/{complaint_id}").status_code == 404
    assert client.get("/api/v1/cms/complaints/mine").json()["results"] == []


@pytest.mark.django_db
def test_module_gate_is_required_even_with_action_permission(stub_iam):
    stub_iam(session=make_session(user_id=101, modules=(), permissions=("cms.complaint.track",)))
    response = Client(HTTP_AUTHORIZATION="Token user-token").get("/api/v1/cms/complaints/mine")
    assert response.status_code == 403


@pytest.mark.django_db
def test_submission_requires_category_and_description(stub_iam):
    stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit",),
        )
    )
    response = Client(HTTP_AUTHORIZATION="Token user-token").post(
        "/api/v1/cms/complaints", {"category": "Facilities"}, content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert Complaint.objects.count() == 0


@pytest.mark.django_db
def test_handler_role_appointment_and_permission_both_gate_assignment(stub_iam):
    fake = stub_iam(
        session=make_session(
            user_id=202,
            modules=("cms",),
            kind="staff",
            roles=("complaint_handler",),
            active_role="complaint_handler",
            permissions=("cms.complaint.assign",),
        )
    )
    CmsRoleAssignment.objects.create(
        role="handler",
        user_id=202,
        starts_at=timezone.now() - timedelta(hours=1),
        ends_at=timezone.now() + timedelta(hours=2),
        is_active=True,
        assigned_by_user_id=1,
    )
    complaint = submit(
        actor=SimpleNamespace(user_id=101, active_role="student"),
        category="Facilities",
        description="Broken window",
    )
    client = Client(HTTP_AUTHORIZATION="Token handler-token")
    response = client.post(
        f"/api/v1/cms/complaints/{complaint.pk}/handling",
        {"category": "Facilities", "priority": "high", "note": "Assigned to office"},
        content_type="application/json",
    )
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert complaint.assigned_handler_user_id == 202
    assert complaint.priority == "high"

    fake.session = make_session(
        user_id=303,
        modules=("cms",),
        kind="staff",
        roles=("complaint_handler",),
        active_role="complaint_handler",
        permissions=("cms.complaint.assign",),
    )
    denied = client.post(
        f"/api/v1/cms/complaints/{complaint.pk}/handling",
        {"category": "Facilities", "priority": "low"},
        content_type="application/json",
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_handler_lists_escalations_feedback_announcements_and_csv_reports(stub_iam):
    handler_id = 202
    CmsRoleAssignment.objects.create(
        role="handler",
        user_id=handler_id,
        starts_at=timezone.now() - timedelta(hours=1),
        ends_at=timezone.now() + timedelta(hours=2),
        is_active=True,
        assigned_by_user_id=1,
    )
    CmsRoleAssignment.objects.create(
        role="supervisor",
        user_id=handler_id,
        starts_at=timezone.now() - timedelta(hours=1),
        ends_at=timezone.now() + timedelta(hours=2),
        is_active=True,
        assigned_by_user_id=1,
    )
    fake = stub_iam(
        session=make_session(
            user_id=handler_id,
            modules=("cms",),
            kind="staff",
            roles=("complaint_handler",),
            active_role="complaint_handler",
            permissions=(
                "cms.escalation.monitor",
                "cms.complaint.view",
                "cms.feedback.review",
                "cms.announcement.view",
                "cms.announcement.publish",
                "cms.report.view",
            ),
        )
    )
    handler = SimpleNamespace(user_id=handler_id, active_role="complaint_handler")
    owner = SimpleNamespace(user_id=101, active_role="student")
    escalated = submit(actor=owner, category="Facilities", description="Broken lift")
    services.setup_handling(
        complaint_id=escalated.pk, actor=handler, category="Facilities", priority="high"
    )
    services.escalate(complaint_id=escalated.pk, actor=handler, kind="manual")

    complaint = submit(actor=owner, category="Access", description="Door access")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Access", priority="medium"
    )
    services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Repaired"
    )
    services.submit_feedback(complaint_id=complaint.pk, actor=owner, text="Thanks")

    client = Client(HTTP_AUTHORIZATION="Token handler-token")
    worklist_response = client.get("/api/v1/cms/complaints?category=Facilities")
    assert worklist_response.status_code == 200
    assert [row["id"] for row in worklist_response.json()["results"]] == [escalated.pk]
    escalation_response = client.get("/api/v1/cms/escalations")
    assert escalation_response.status_code == 200
    assert [row["id"] for row in escalation_response.json()["results"]] == [escalated.pk]
    feedback_response = client.get("/api/v1/cms/feedback")
    assert feedback_response.status_code == 200
    assert len(feedback_response.json()["results"]) == 1

    announcement_response = client.post(
        "/api/v1/cms/announcements",
        {"title": "Service update", "body": "Lift service restored", "notify_users": True},
        content_type="application/json",
    )
    assert announcement_response.status_code == 201
    assert client.get("/api/v1/cms/announcements").json()["results"][0]["title"] == "Service update"

    csv_response = client.get("/api/v1/cms/reports?export=csv&category=Facilities")
    assert csv_response.status_code == 200, csv_response.json()
    assert csv_response["Content-Type"].startswith("text/csv")
    assert b"Facilities" in csv_response.content
    assert b"Access" not in csv_response.content
    summary = client.get("/api/v1/cms/reports")
    assert summary.status_code == 200
    assert summary.json()["total"] == 2

    fake.session = make_session(
        user_id=99,
        modules=("cms",),
        kind="operator",
        roles=("system_admin",),
        active_role="system_admin",
        permissions=("cms.report.view", "cms.role.manage"),
    )
    admin_summary = Client(HTTP_AUTHORIZATION="Token handler-token").get("/api/v1/cms/reports")
    assert admin_summary.status_code == 200


@pytest.mark.django_db
def test_admin_can_assign_and_reassign_cms_role(stub_iam, monkeypatch):
    from modules.directory import contracts
    from modules.directory.models import UserRef

    monkeypatch.setattr(contracts, "ensure_users_cached", lambda user_ids: None)
    UserRef.objects.create(user_id=505, username="staff505", display_name="Staff 505", kind="staff")
    UserRef.objects.create(user_id=506, username="staff506", display_name="Staff 506", kind="staff")
    stub_iam(
        session=make_session(
            user_id=1,
            modules=("cms",),
            kind="operator",
            roles=("system_admin",),
            active_role="system_admin",
            permissions=("cms.role.manage",),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token admin-token")
    start = (timezone.now() - timedelta(minutes=1)).isoformat()
    end = (timezone.now() + timedelta(days=14)).isoformat()
    for user_id in (505, 506):
        response = client.post(
            "/api/v1/cms/roles",
            {"role": "handler", "user_id": user_id, "starts_at": start, "ends_at": end},
            content_type="application/json",
        )
        assert response.status_code == 201, response.json()
    active = CmsRoleAssignment.objects.filter(role="handler", is_active=True)
    assert list(active.values_list("user_id", flat=True)) == [506]


@pytest.mark.django_db
@override_settings(CMS_ATTACHMENT_MAX_BYTES=100, CMS_ATTACHMENT_MAX_COUNT=1)
def test_attachment_upload_validates_type_and_downloads_only_through_api(
    stub_iam, tmp_path, monkeypatch
):
    from django.conf import settings

    user_id = 101
    stub_iam(
        session=make_session(
            user_id=user_id,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    created = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Door hinge"},
        content_type="application/json",
    )
    complaint_id = created.json()["id"]
    monkeypatch.setattr(settings, "CMS_UPLOAD_ROOT", str(tmp_path))
    upload = SimpleUploadedFile("photo.png", b"image-bytes", content_type="image/png")
    response = client.post(
        f"/api/v1/cms/complaints/{complaint_id}/attachments", {"attachments": upload}
    )
    assert response.status_code == 201
    attachment_id = response.json()[0]["id"]
    download = client.get(f"/api/v1/cms/attachments/{attachment_id}/download")
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == b"image-bytes"

    invalid = SimpleUploadedFile("payload.exe", b"bad", content_type="application/octet-stream")
    rejected = client.post(
        f"/api/v1/cms/complaints/{complaint_id}/attachments", {"attachments": invalid}
    )
    assert rejected.status_code == 409
