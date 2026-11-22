from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from conftest import make_session
from modules.cms import services
from modules.cms.models import CmsNotificationEvent, CmsRoleAssignment, Complaint


def _actor(user_id=101, role="student"):
    return SimpleNamespace(user_id=user_id, active_role=role)


@pytest.mark.django_db
def test_uc_001_submit_complaint_main_flow(stub_iam):
    """test_id: UC-001 | source_id: UC-CMS-001 Main Flow"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.submit",)))
    res = Client(HTTP_AUTHORIZATION="Token u1").post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Broken glass"},
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.json()["status"] == "submitted"


@pytest.mark.django_db
def test_uc_002_submit_complaint_exception_flow(stub_iam):
    """test_id: UC-002 | source_id: UC-CMS-001 Exception Flow"""
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.complaint.submit",)))
    res = Client(HTTP_AUTHORIZATION="Token u1").post(
        "/api/v1/cms/complaints", {"category": ""}, content_type="application/json"
    )
    assert res.status_code == 400
    assert Complaint.objects.count() == 0


@pytest.mark.django_db
def test_uc_003_track_complaint_status_and_history(stub_iam):
    """test_id: UC-003 | source_id: UC-CMS-002 Main Flow"""
    stub_iam(
        session=make_session(
            user_id=101,
            modules=("cms",),
            permissions=("cms.complaint.submit", "cms.complaint.track"),
        )
    )
    client = Client(HTTP_AUTHORIZATION="Token u1")
    created = client.post(
        "/api/v1/cms/complaints",
        {"category": "Facilities", "description": "Track me"},
        content_type="application/json",
    )
    cid = created.json()["id"]
    detail = client.get(f"/api/v1/cms/complaints/{cid}")
    assert detail.status_code == 200
    assert detail.json()["history"][0]["to_status"] == "submitted"


@pytest.mark.django_db
def test_uc_004_review_assigned_complaints(stub_iam):
    """test_id: UC-004 | source_id: UC-CMS-003 Main Flow"""
    stub_iam(
        session=make_session(
            user_id=202,
            modules=("cms",),
            kind="staff",
            roles=("complaint_handler",),
            active_role="complaint_handler",
            permissions=("cms.complaint.view",),
        )
    )
    services.submit(actor=_actor(101), category="Facilities", description="Review item")
    res = Client(HTTP_AUTHORIZATION="Token h1").get("/api/v1/cms/complaints")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


@pytest.mark.django_db
def test_uc_005_assign_categorize_and_prioritize():
    """test_id: UC-005 | source_id: UC-CMS-004 Main Flow"""
    c = services.submit(actor=_actor(101), category="Other", description="Priority check")
    updated = services.setup_handling(
        complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="IT", priority="high"
    )
    assert updated.category == "IT"
    assert updated.priority == "high"


@pytest.mark.django_db
def test_uc_006_update_complaint_progress():
    """test_id: UC-006 | source_id: UC-CMS-005 Main Flow"""
    c = services.submit(actor=_actor(101), category="IT", description="Router reset")
    services.add_progress(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), text="Checked port")
    assert c.progress_updates.filter(update_text="Checked port").exists()


@pytest.mark.django_db
def test_uc_007_resolve_complaint_outcome():
    """test_id: UC-007 | source_id: UC-CMS-006 Alternative A1 (Resolve)"""
    c = services.submit(actor=_actor(101), category="IT", description="Cable")
    res = services.decide_outcome(
        complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Replaced"
    )
    assert res.status == "resolved"


@pytest.mark.django_db
def test_uc_008_reject_complaint_outcome():
    """test_id: UC-008 | source_id: UC-CMS-006 Alternative A2 (Reject)"""
    c = services.submit(actor=_actor(101), category="IT", description="Duplicate")
    res = services.decide_outcome(
        complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="rejected", details="Duplicate ticket"
    )
    assert res.status == "rejected"


@pytest.mark.django_db
def test_uc_009_complainant_closure_verification():
    """test_id: UC-009 | source_id: UC-CMS-007 Main Flow"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="IT", description="Monitor")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Fixed")
    closed = services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    assert closed.status == "closed"


@pytest.mark.django_db
def test_uc_010_request_complaint_reopening():
    """test_id: UC-010 | source_id: UC-CMS-008 Main Flow"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="IT", description="Keyboard")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Swapped")
    services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    req = services.request_reopening(complaint_id=c.pk, actor=owner, reason="Keys sticking again")
    assert req.decision == "pending"


@pytest.mark.django_db
def test_uc_011_submit_feedback():
    """test_id: UC-011 | source_id: UC-CMS-009 Main Flow"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="IT", description="Mouse")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Replaced")
    fb = services.submit_feedback(complaint_id=c.pk, actor=owner, text="Great help")
    assert fb.feedback_text == "Great help"


@pytest.mark.django_db
def test_uc_012_review_submitted_feedback(stub_iam):
    """test_id: UC-012 | source_id: UC-CMS-010 Main Flow"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="IT", description="Printer")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Toner refilled")
    services.submit_feedback(complaint_id=c.pk, actor=owner, text="Works well")
    stub_iam(session=make_session(user_id=202, modules=("cms",), permissions=("cms.feedback.review",)))
    res = Client(HTTP_AUTHORIZATION="Token h1").get("/api/v1/cms/feedback")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


@pytest.mark.django_db
def test_uc_013_manually_escalate_complaint():
    """test_id: UC-013 | source_id: UC-CMS-011 Main Flow"""
    c = services.submit(actor=_actor(101), category="IT", description="Server down")
    esc = services.escalate(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), kind="manual")
    assert esc.escalation_kind == "manual"


@pytest.mark.django_db
def test_uc_014_monitor_escalated_complaints(stub_iam):
    """test_id: UC-014 | source_id: UC-CMS-012 Main Flow"""
    c = services.submit(actor=_actor(101), category="IT", description="Outage")
    services.escalate(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), kind="manual")
    stub_iam(session=make_session(user_id=303, modules=("cms",), permissions=("cms.escalation.monitor",)))
    res = Client(HTTP_AUTHORIZATION="Token s1").get("/api/v1/cms/escalations")
    assert res.status_code == 200
    assert [r["id"] for r in res.json()["results"]] == [c.pk]


@pytest.mark.django_db
def test_uc_015_publish_announcement():
    """test_id: UC-015 | source_id: UC-CMS-013 Main Flow"""
    ann = services.publish_announcement(
        actor=_actor(202, "complaint_handler"), title="Notice", body="Portal maintenance", notify_users=True
    )
    assert ann.is_published


@pytest.mark.django_db
def test_uc_016_view_announcements(stub_iam):
    """test_id: UC-016 | source_id: UC-CMS-014 Main Flow"""
    services.publish_announcement(
        actor=_actor(202, "complaint_handler"), title="Public Notice", body="Info", notify_users=False
    )
    stub_iam(session=make_session(user_id=101, modules=("cms",), permissions=("cms.announcement.view",)))
    res = Client(HTTP_AUTHORIZATION="Token u1").get("/api/v1/cms/announcements")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


@pytest.mark.django_db
def test_uc_017_reports_and_summaries(stub_iam):
    """test_id: UC-017 | source_id: UC-CMS-015 / UC-CMS-016 / UC-CMS-017 Main Flow"""
    services.submit(actor=_actor(101), category="Facilities", description="Report sample")
    stub_iam(session=make_session(user_id=202, modules=("cms",), permissions=("cms.report.view",)))
    res = Client(HTTP_AUTHORIZATION="Token h1").get("/api/v1/cms/reports")
    assert res.status_code == 200
    assert res.json()["total"] == 1


@pytest.mark.django_db
def test_uc_018_manage_cms_roles(stub_iam, monkeypatch):
    """test_id: UC-018 | source_id: UC-CMS-018 Main Flow"""
    from modules.directory import contracts
    from modules.directory.models import UserRef

    monkeypatch.setattr(contracts, "ensure_users_cached", lambda user_ids: None)
    UserRef.objects.create(user_id=701, username="u701", display_name="User 701", kind="staff")
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
        {"role": "handler", "user_id": 701, "starts_at": start, "ends_at": end},
        content_type="application/json",
    )
    assert res.status_code == 201
    assert CmsRoleAssignment.objects.filter(role="handler", user_id=701, is_active=True).exists()


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="supervisor")
def test_uc_019_supervisor_closure_verification():
    """test_id: UC-019 | source_id: UC-CMS-019 Main Flow"""
    owner = _actor(101)
    c = services.submit(actor=owner, category="Facilities", description="Door")
    services.decide_outcome(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), outcome="resolved", details="Fixed")
    closed = services.verify_closure(complaint_id=c.pk, actor=_actor(303, "complaint_supervisor"), verifier="supervisor")
    assert closed.status == "closed"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant", CMS_REOPENED_STATUS="submitted")
def test_uc_020_review_reopening_approve_and_deny():
    """test_id: UC-020 | source_id: UC-CMS-020 Main Flow & Alternative (Approve / Deny)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    sup = _actor(303, "complaint_supervisor")

    c1 = services.submit(actor=owner, category="Facilities", description="One")
    services.decide_outcome(complaint_id=c1.pk, actor=handler, outcome="resolved", details="Done")
    services.verify_closure(complaint_id=c1.pk, actor=owner, verifier="complainant")
    r1 = services.request_reopening(complaint_id=c1.pk, actor=owner, reason="Not fixed")
    services.review_reopening(request_id=r1.pk, actor=sup, decision="approved", note="Approved")
    c1.refresh_from_db()
    assert c1.status == "submitted"

    c2 = services.submit(actor=owner, category="Facilities", description="Two")
    services.decide_outcome(complaint_id=c2.pk, actor=handler, outcome="resolved", details="Done")
    services.verify_closure(complaint_id=c2.pk, actor=owner, verifier="complainant")
    r2 = services.request_reopening(complaint_id=c2.pk, actor=owner, reason="Invalid")
    services.review_reopening(request_id=r2.pk, actor=sup, decision="denied", note="Denied")
    c2.refresh_from_db()
    assert c2.status == "closed"


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=2, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_uc_021_trigger_pre_breach_sla_reminder():
    """test_id: UC-021 | source_id: UC-CMS-021 Main Flow"""
    c = services.submit(actor=_actor(101), category="Facilities", description="SLA reminder")
    services.setup_handling(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="Facilities", priority="high")
    now = timezone.now()
    Complaint.objects.filter(pk=c.pk).update(sla_due_at=now + timedelta(hours=1))
    assert services.process_sla(now)["reminded"] == 1
    assert CmsNotificationEvent.objects.filter(event_type="complaint.sla_reminder").count() == 1


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=2, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_uc_022_auto_escalate_on_sla_breach():
    """test_id: UC-022 | source_id: UC-CMS-022 Main Flow"""
    c = services.submit(actor=_actor(101), category="Facilities", description="SLA breach")
    services.setup_handling(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="Facilities", priority="high")
    now = timezone.now()
    Complaint.objects.filter(pk=c.pk).update(sla_due_at=now - timedelta(minutes=1))
    assert services.process_sla(now)["escalated"] == 1
    c.refresh_from_db()
    assert c.escalation_kind == "automatic"
