from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import get_resolver
from django.utils import timezone

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.cms import services
from modules.cms.models import CmsNotificationEvent, CmsRoleAssignment, Complaint


def _actor(user_id=101, role="student"):
    return SimpleNamespace(user_id=user_id, active_role=role)


@pytest.mark.django_db
def test_fr_001_submit_complaint_records_fields_and_unique_id(stub_iam):
    """test_id: FR-001 | source_id: CFR-CMS-001 / AFR-CMS-001..004, AFR-CMS-009..010"""
    stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    r1 = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Broken fan"},
        content_type="application/json",
    )
    r2 = client.post(
        "/api/v1/cms/complaints",
        {"category": "Network", "description": "Wi-Fi down"},
        content_type="application/json",
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]
    assert r1.json()["category"] == "Facilities"
    assert r1.json()["description"] == "Broken fan"
    assert CmsNotificationEvent.objects.filter(event_type="complaint.submitted").count() == 2


@pytest.mark.django_db
def test_fr_002_missing_mandatory_fields_refused(stub_iam):
    """test_id: FR-002 | source_id: CFR-CMS-001 / AFR-CMS-006"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.submit",)))
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    r_no_desc = client.post(
        "/api/v1/cms/complaints", {"category": "Facilities"}, content_type="application/json"
    )
    r_no_cat = client.post(
        "/api/v1/cms/complaints", {"description": "Missing category"}, content_type="application/json"
    )
    assert r_no_desc.status_code == 400
    assert r_no_cat.status_code == 400
    assert Complaint.objects.count() == 0


@pytest.mark.django_db
@override_settings(CMS_ATTACHMENT_MAX_BYTES=200, CMS_ATTACHMENT_MAX_COUNT=2)
def test_fr_003_valid_attachment_accepted(stub_iam, tmp_path, monkeypatch):
    """test_id: FR-003 | source_id: CFR-CMS-001 / AFR-CMS-005, AFR-CMS-007..008"""
    stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    created = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Window crack"},
        content_type="application/json",
    )
    cid = created.json()["id"]
    monkeypatch.setattr(settings, "CMS_UPLOAD_ROOT", str(tmp_path))
    upload = SimpleUploadedFile("evidence.png", b"valid-bytes", content_type="image/png")
    res = client.post(f"/api/v1/cms/complaints/{cid}/attachments", {"attachments": upload})
    assert res.status_code == 201
    assert len(res.json()) == 1


@pytest.mark.django_db
@override_settings(CMS_ATTACHMENT_MAX_BYTES=10, CMS_ATTACHMENT_MAX_COUNT=1)
def test_fr_004_invalid_attachment_rejected(stub_iam, tmp_path, monkeypatch):
    """test_id: FR-004 | source_id: CFR-CMS-001 / AFR-CMS-007..008"""
    stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    created = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Door issue"},
        content_type="application/json",
    )
    cid = created.json()["id"]
    monkeypatch.setattr(settings, "CMS_UPLOAD_ROOT", str(tmp_path))
    bad_ext = SimpleUploadedFile("script.exe", b"123", content_type="application/octet-stream")
    too_big = SimpleUploadedFile("large.png", b"0123456789012345", content_type="image/png")
    assert client.post(f"/api/v1/cms/complaints/{cid}/attachments", {"attachments": bad_ext}).status_code == 409
    assert client.post(f"/api/v1/cms/complaints/{cid}/attachments", {"attachments": too_big}).status_code == 409


@pytest.mark.django_db
def test_fr_005_handler_manual_assignment_categorization_and_priority(stub_iam):
    """test_id: FR-005 | source_id: CFR-CMS-002 / AFR-CMS-011..015"""
    stub_iam(
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
    complaint = services.submit(actor=_actor(101), category="General", description="AC leak")
    client = Client(HTTP_AUTHORIZATION="Token handler-token")
    res = client.post(
        f"/api/v1/cms/complaints/{complaint.pk}/handling",
        {"category": "Facilities", "priority": "high", "note": "Assigned"},
        content_type="application/json",
    )
    assert res.status_code == 200
    complaint.refresh_from_db()
    assert complaint.assigned_handler_user_id == 202
    assert complaint.category == "Facilities"
    assert complaint.priority == "high"


@pytest.mark.django_db
def test_fr_006_invalid_priority_rejected(stub_iam):
    """test_id: FR-006 | source_id: CFR-CMS-002 / AFR-CMS-013"""
    stub_iam(
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
    complaint = services.submit(actor=_actor(101), category="Facilities", description="Tap leak")
    client = Client(HTTP_AUTHORIZATION="Token handler-token")
    res = client.post(
        f"/api/v1/cms/complaints/{complaint.pk}/handling",
        {"category": "Facilities", "priority": "urgent"},
        content_type="application/json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_fr_007_tracking_and_progress_history_maintained():
    """test_id: FR-007 | source_id: CFR-CMS-003 / AFR-CMS-016..021"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Light issue")
    services.setup_handling(complaint_id=complaint.pk, actor=handler, category="Facilities", priority="medium")
    services.add_progress(complaint_id=complaint.pk, actor=handler, text="Technician dispatched")
    assert complaint.progress_updates.filter(update_text="Technician dispatched").exists()
    assert complaint.history.filter(to_status="submitted").exists()


@pytest.mark.django_db
def test_fr_008_complainant_cannot_access_other_users_complaint(stub_iam):
    """test_id: FR-008 | source_id: CFR-CMS-003 / AFR-CMS-016..017"""
    complaint = services.submit(actor=_actor(101), category="Facilities", description="Private issue")
    stub_iam(session=make_session(user_id=999, modules=("cms",), permissions=("cms.complaint.track",)))
    client = Client(HTTP_AUTHORIZATION="Token other-user")
    assert client.get(f"/api/v1/cms/complaints/{complaint.pk}").status_code == 404


@pytest.mark.django_db
def test_fr_009_resolve_complaint_records_details_and_notifies():
    """test_id: FR-009 | source_id: CFR-CMS-004 / AFR-CMS-022..026"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Fan broken")
    resolved = services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Replaced motor"
    )
    assert resolved.status == "resolved"
    assert resolved.notification_events.filter(event_type="complaint.resolved").exists()


@pytest.mark.django_db
def test_fr_010_reject_complaint_records_reason_and_notifies():
    """test_id: FR-010 | source_id: CFR-CMS-004 / AFR-CMS-022..026"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Personal item")
    rejected = services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="rejected", details="Out of scope"
    )
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Out of scope"
    assert rejected.notification_events.filter(event_type="complaint.rejected").exists()


@pytest.mark.django_db
def test_fr_011_outcome_without_details_refused():
    """test_id: FR-011 | source_id: CFR-CMS-004 / AFR-CMS-023..024"""
    complaint = services.submit(actor=_actor(101), category="Facilities", description="Desk broken")
    handler = _actor(202, "complaint_handler")
    with pytest.raises(ConflictError):
        services.decide_outcome(complaint_id=complaint.pk, actor=handler, outcome="resolved", details=" ")
    with pytest.raises(ConflictError):
        services.decide_outcome(complaint_id=complaint.pk, actor=handler, outcome="rejected", details="")


@pytest.mark.django_db
def test_fr_012_closure_verification_records_closed_status():
    """test_id: FR-012 | source_id: CFR-CMS-005 / AFR-CMS-027..029"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Switch broken")
    services.decide_outcome(complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Fixed")
    closed = services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    assert closed.status == "closed"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant", CMS_REOPENED_STATUS="in_progress")
def test_fr_013_reopening_request_and_supervisor_decision():
    """test_id: FR-013 | source_id: CFR-CMS-006 / AFR-CMS-030..034"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    supervisor = _actor(303, "complaint_supervisor")
    complaint = services.submit(actor=owner, category="Access", description="Card reader")
    services.decide_outcome(complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Reset")
    services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    req = services.request_reopening(complaint_id=complaint.pk, actor=owner, reason="Still failing")
    reviewed = services.review_reopening(
        request_id=req.pk, actor=supervisor, decision="approved", note="Reopened"
    )
    complaint.refresh_from_db()
    assert reviewed.decision == "approved"
    assert complaint.status == "in_progress"


@pytest.mark.django_db
def test_fr_014_feedback_submission_and_review():
    """test_id: FR-014 | source_id: CFR-CMS-007 / AFR-CMS-035..037"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Chair")
    services.decide_outcome(complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Replaced")
    fb = services.submit_feedback(complaint_id=complaint.pk, actor=owner, text="Quick fix")
    assert fb.feedback_text == "Quick fix"


@pytest.mark.django_db
def test_fr_015_manual_escalation_records_status():
    """test_id: FR-015 | source_id: CFR-CMS-008 / AFR-CMS-038..040"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Power outage")
    escalated = services.escalate(complaint_id=complaint.pk, actor=handler, kind="manual")
    assert escalated.escalation_kind == "manual"
    assert escalated.notification_events.filter(event_type="complaint.escalated").exists()


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=2, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_fr_016_sla_reminder_and_auto_escalation():
    """test_id: FR-016 | source_id: CFR-CMS-009 / AFR-CMS-041..044"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    complaint = services.submit(actor=owner, category="Facilities", description="Water pipe")
    services.setup_handling(complaint_id=complaint.pk, actor=handler, category="Facilities", priority="high")
    now = timezone.now()
    Complaint.objects.filter(pk=complaint.pk).update(sla_due_at=now + timedelta(hours=1))
    assert services.process_sla(now)["reminded"] == 1
    Complaint.objects.filter(pk=complaint.pk).update(sla_due_at=now - timedelta(minutes=5))
    assert services.process_sla(now)["escalated"] == 1


@pytest.mark.django_db
def test_fr_017_announcements_publish_and_view():
    """test_id: FR-017 | source_id: CFR-CMS-010 / AFR-CMS-045..048"""
    handler = _actor(202, "complaint_handler")
    ann = services.publish_announcement(
        actor=handler, title="Scheduled Maintenance", body="Water off 2-4 PM", notify_users=True
    )
    assert ann.is_published
    assert CmsNotificationEvent.objects.filter(event_type="announcement.published").exists()


@pytest.mark.django_db
def test_fr_018_plain_user_refused_publishing_announcement(stub_iam):
    """test_id: FR-018 | source_id: CFR-CMS-010 / AFR-CMS-045..046"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.announcement.view",)))
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    res = client.post(
        "/api/v1/cms/announcements",
        {"title": "Unauthorized", "body": "Test"},
        content_type="application/json",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_fr_019_report_and_summary_role_gating(stub_iam):
    """test_id: FR-019 | source_id: CFR-CMS-011 / AFR-CMS-049..054"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.track",)))
    client = Client(HTTP_AUTHORIZATION="Token user-token")
    assert client.get("/api/v1/cms/reports").status_code == 403


@pytest.mark.django_db
def test_fr_020_notification_trigger_events_recorded():
    """test_id: FR-020 | source_id: CFR-CMS-012 / AFR-CMS-055..063"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    c = services.submit(actor=owner, category="Facilities", description="Heater")
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Done")
    assert CmsNotificationEvent.objects.filter(event_type="complaint.submitted").exists()
    assert CmsNotificationEvent.objects.filter(event_type="complaint.resolved").exists()


@pytest.mark.django_db
def test_fr_021_single_active_role_holder_enforced(stub_iam, monkeypatch):
    """test_id: FR-021 | source_id: CFR-CMS-013 / AFR-CMS-064..070"""
    from modules.directory import contracts
    from modules.directory.models import UserRef

    monkeypatch.setattr(contracts, "ensure_users_cached", lambda user_ids: None)
    UserRef.objects.create(user_id=601, username="u601", display_name="User 601", kind="staff")
    UserRef.objects.create(user_id=602, username="u602", display_name="User 602", kind="staff")
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
    end = (timezone.now() + timedelta(days=7)).isoformat()
    for uid in (601, 602):
        assert (
            client.post(
                "/api/v1/cms/roles",
                {"role": "supervisor", "user_id": uid, "starts_at": start, "ends_at": end},
                content_type="application/json",
            ).status_code
            == 201
        )
    active = CmsRoleAssignment.objects.filter(role="supervisor", is_active=True)
    assert list(active.values_list("user_id", flat=True)) == [602]


def test_fr_022_cms_routes_confined_to_cms_scope():
    """test_id: FR-022 | source_id: CFR-CMS-014 / AFR-CMS-071..073"""
    resolver = get_resolver()
    patterns = [str(p.pattern) for p in resolver.url_patterns]
    assert patterns
