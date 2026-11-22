from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.cms import domain, services
from modules.cms.models import CmsNotificationEvent, CmsRoleAssignment, Complaint


def _actor(user_id=101, role="student"):
    return SimpleNamespace(user_id=user_id, active_role=role)


@pytest.mark.django_db
def test_br_001_submission_timestamp_and_unique_id():
    """test_id: BR-001 | source_id: BR-CMS-001 / BR-CMS-003 / BR-CMS-006"""
    c1 = services.submit(actor=_actor(101), category="Facilities", description="One")
    c2 = services.submit(actor=_actor(101), category="Facilities", description="Two")
    assert c1.pk != c2.pk
    assert c1.created_at is not None


@pytest.mark.django_db
def test_br_002_missing_mandatory_fields_refused(stub_iam):
    """test_id: BR-002 | source_id: BR-CMS-002"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.submit",)))
    res = Client(HTTP_AUTHORIZATION="Token u1").post(
        "/api/v1/cms/complaints", {"category": "Facilities", "description": ""}, content_type="application/json"
    )
    assert res.status_code == 400


@pytest.mark.django_db
@override_settings(CMS_ATTACHMENT_MAX_BYTES=20, CMS_ATTACHMENT_MAX_COUNT=1)
def test_br_003_attachment_constraints_enforced(stub_iam, tmp_path, monkeypatch):
    """test_id: BR-003 | source_id: BR-CMS-004 / BR-CMS-005"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.submit",)))
    client = Client(HTTP_AUTHORIZATION="Token u1")
    cid = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Att"},
        content_type="application/json",
    ).json()["id"]
    monkeypatch.setattr(settings, "CMS_UPLOAD_ROOT", str(tmp_path))
    ok = SimpleUploadedFile("ok.png", b"12345", content_type="image/png")
    bad = SimpleUploadedFile("bad.exe", b"123", content_type="application/octet-stream")
    assert client.post(f"/api/v1/cms/complaints/{cid}/attachments", {"attachments": ok}).status_code == 201
    assert client.post(f"/api/v1/cms/complaints/{cid}/attachments", {"attachments": bad}).status_code == 409


@pytest.mark.django_db
def test_br_004_unassigned_on_submit_then_manual_assignment():
    """test_id: BR-004 | source_id: BR-CMS-007 / BR-CMS-008 / BR-CMS-010"""
    c = services.submit(actor=_actor(101), category="Facilities", description="Manual assign")
    assert c.assigned_handler_user_id is None
    updated = services.setup_handling(
        complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="IT", priority="low"
    )
    assert updated.assigned_handler_user_id == 202
    assert updated.category == "IT"


@pytest.mark.django_db
def test_br_005_priority_values_validated(stub_iam):
    """test_id: BR-005 | source_id: BR-CMS-009 / BR-CMS-010"""
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
    c = services.submit(actor=_actor(101), category="Facilities", description="Prio")
    client = Client(HTTP_AUTHORIZATION="Token h1")
    for p in ("low", "medium", "high"):
        assert (
            client.post(
                f"/api/v1/cms/complaints/{c.pk}/handling",
                {"category": "Facilities", "priority": p},
                content_type="application/json",
            ).status_code
            == 200
        )
    assert (
        client.post(
            f"/api/v1/cms/complaints/{c.pk}/handling",
            {"category": "Facilities", "priority": "critical"},
            content_type="application/json",
        ).status_code
        == 400
    )


def test_br_006_lifecycle_states_and_invalid_transition_rejected():
    """test_id: BR-006 | source_id: BR-CMS-011 / BR-CMS-012"""
    with pytest.raises(domain.InvalidTransition):
        domain.transition("submitted", "closed")


@pytest.mark.django_db
def test_br_007_resolution_requires_details_and_triggers_notification():
    """test_id: BR-007 | source_id: BR-CMS-013 / BR-CMS-015"""
    c = services.submit(actor=_actor(101), category="Facilities", description="Res")
    with pytest.raises(ConflictError):
        services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="")
    res = services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Fixed")
    assert res.notification_events.filter(event_type="complaint.resolved").exists()


@pytest.mark.django_db
def test_br_008_rejection_requires_reason_and_triggers_notification():
    """test_id: BR-008 | source_id: BR-CMS-014 / BR-CMS-015"""
    c = services.submit(actor=_actor(101), category="Facilities", description="Rej")
    with pytest.raises(ConflictError):
        services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="rejected", details=" ")
    rej = services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="rejected", details="Invalid")
    assert rej.notification_events.filter(event_type="complaint.rejected").exists()


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="supervisor")
def test_br_009_closure_verification_enforces_configured_verifier():
    """test_id: BR-009 | source_id: BR-CMS-016 / BR-CMS-017"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="Facilities", description="Close")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Done")
    with pytest.raises(ConflictError):
        services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    closed = services.verify_closure(complaint_id=c.pk, actor=_actor(303, "complaint_supervisor"), verifier="supervisor")
    assert closed.status == "closed"


@pytest.mark.django_db
def test_br_010_reopening_only_allowed_for_closed_complaint():
    """test_id: BR-010 | source_id: BR-CMS-018"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="Facilities", description="Not closed")
    with pytest.raises(ConflictError):
        services.request_reopening(complaint_id=c.pk, actor=owner, reason="Open complaint")


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant", CMS_REOPENED_STATUS="in_progress")
def test_br_011_supervisor_decides_reopening_and_records_decision():
    """test_id: BR-011 | source_id: BR-CMS-019 / BR-CMS-020 / BR-CMS-021"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="Facilities", description="Reopen audit")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Done")
    services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    req = services.request_reopening(complaint_id=c.pk, actor=owner, reason="Again")
    dec = services.review_reopening(request_id=req.pk, actor=_actor(303, "complaint_supervisor"), decision="approved", note="OK")
    assert dec.decision == "approved"


@pytest.mark.django_db
def test_br_012_feedback_only_after_resolution_or_closure():
    """test_id: BR-012 | source_id: BR-CMS-022 / BR-CMS-023"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="Facilities", description="Early feedback")
    with pytest.raises(ConflictError):
        services.submit_feedback(complaint_id=c.pk, actor=owner, text="Too early")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Done")
    fb = services.submit_feedback(complaint_id=c.pk, actor=owner, text="Good")
    assert fb.feedback_text == "Good"


@pytest.mark.django_db
def test_br_013_manual_escalation_only_for_unresolved_complaints():
    """test_id: BR-013 | source_id: BR-CMS-024 / BR-CMS-025"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    c = services.submit(actor=owner, category="Facilities", description="Escalate")
    esc = services.escalate(complaint_id=c.pk, actor=handler, kind="manual")
    assert esc.escalation_kind == "manual"
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Done")
    services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    with pytest.raises(ConflictError):
        services.escalate(complaint_id=c.pk, actor=handler, kind="manual")


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=2, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_br_014_sla_reminder_and_escalation_idempotent():
    """test_id: BR-014 | source_id: BR-CMS-026 / BR-CMS-027 / BR-CMS-028 / BR-CMS-029"""
    c = services.submit(actor=_actor(101), category="Facilities", description="SLA")
    services.setup_handling(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="Facilities", priority="high")
    now = timezone.now()
    Complaint.objects.filter(pk=c.pk).update(sla_due_at=now - timedelta(minutes=1))
    assert services.process_sla(now)["escalated"] == 1
    assert services.process_sla(now)["escalated"] == 0


@pytest.mark.django_db
def test_br_015_only_authorized_roles_publish_announcements(stub_iam):
    """test_id: BR-015 | source_id: BR-CMS-030 / BR-CMS-031"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.announcement.view",)))
    assert (
        Client(HTTP_AUTHORIZATION="Token u1")
        .post("/api/v1/cms/announcements", {"title": "No", "body": "No"}, content_type="application/json")
        .status_code
        == 403
    )
    ann = services.publish_announcement(
        actor=_actor(202, "complaint_handler"), title="Yes", body="Yes", notify_users=True
    )
    assert ann.is_published


@pytest.mark.django_db
def test_br_016_reports_gated_and_notifications_internal(stub_iam):
    """test_id: BR-016 | source_id: BR-CMS-032 / BR-CMS-033 / BR-CMS-034"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.track",)))
    assert Client(HTTP_AUTHORIZATION="Token u1").get("/api/v1/cms/reports").status_code == 403
    services.submit(actor=_actor(101), category="Facilities", description="Notify")
    assert CmsNotificationEvent.objects.filter(event_type="complaint.submitted").exists()


@pytest.mark.django_db
def test_br_017_single_active_role_holder_and_role_validation(stub_iam):
    """test_id: BR-017 | source_id: BR-CMS-035 / BR-CMS-036 / BR-CMS-037 / BR-CMS-038"""
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
    start = (timezone.now() - timedelta(minutes=1)).isoformat()
    end = (timezone.now() + timedelta(days=5)).isoformat()
    res = Client(HTTP_AUTHORIZATION="Token a1").post(
        "/api/v1/cms/roles",
        {"role": "hr_manager", "user_id": 505, "starts_at": start, "ends_at": end},
        content_type="application/json",
    )
    assert res.status_code == 400


def test_br_018_no_cross_module_foreign_keys():
    """test_id: BR-018 | source_id: BR-CMS-039 / BR-CMS-040 / BR-CMS-041"""
    cms_models = apps.get_app_config("cms").get_models()
    for model in cms_models:
        for field in model._meta.get_fields():
            if getattr(field, "remote_field", None) and field.remote_field.model:
                assert field.remote_field.model._meta.app_label == "cms"
