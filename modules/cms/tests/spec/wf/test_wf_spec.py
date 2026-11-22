from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.test import override_settings
from django.utils import timezone

from modules.cms import services
from modules.cms.models import Complaint


def _actor(user_id=101, role="student"):
    return SimpleNamespace(user_id=user_id, active_role=role)


@pytest.mark.django_db
def test_wf_001_intake_to_resolved():
    """test_id: WF-001 | source_id: BW-CMS-01 / CW-CMS-01 (Intake to Resolved)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    c = services.submit(actor=owner, category="Facilities", description="WF001")
    services.setup_handling(complaint_id=c.pk, actor=handler, category="Facilities", priority="medium")
    services.add_progress(complaint_id=c.pk, actor=handler, text="Working")
    res = services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Resolved")
    assert res.status == "resolved"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant")
def test_wf_002_intake_to_user_verified_closure():
    """test_id: WF-002 | source_id: BW-CMS-02 / CW-CMS-01 (Intake to User-Verified Closure)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    c = services.submit(actor=owner, category="Facilities", description="WF002")
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Resolved")
    closed = services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    assert closed.status == "closed"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="supervisor")
def test_wf_003_intake_to_supervisor_verified_closure():
    """test_id: WF-003 | source_id: BW-CMS-03 / CW-CMS-01 (Intake to Supervisor-Verified Closure)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    sup = _actor(303, "complaint_supervisor")
    c = services.submit(actor=owner, category="Facilities", description="WF003")
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Resolved")
    closed = services.verify_closure(complaint_id=c.pk, actor=sup, verifier="supervisor")
    assert closed.status == "closed"


@pytest.mark.django_db
def test_wf_004_intake_to_rejection():
    """test_id: WF-004 | source_id: BW-CMS-04 / CW-CMS-01 (Intake to Rejection)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    c = services.submit(actor=owner, category="Facilities", description="WF004")
    rej = services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="rejected", details="Rejected")
    assert rej.status == "rejected"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant")
def test_wf_005_reopening_request_denied():
    """test_id: WF-005 | source_id: BW-CMS-05 / CW-CMS-02 (Reopening Request Denied)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    sup = _actor(303, "complaint_supervisor")
    c = services.submit(actor=owner, category="Facilities", description="WF005")
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Resolved")
    services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    req = services.request_reopening(complaint_id=c.pk, actor=owner, reason="Reopen")
    services.review_reopening(request_id=req.pk, actor=sup, decision="denied", note="No")
    c.refresh_from_db()
    assert c.status == "closed"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant", CMS_REOPENED_STATUS="in_progress")
def test_wf_006_reopening_request_approved():
    """test_id: WF-006 | source_id: BW-CMS-06 / CW-CMS-02 (Reopening Request Approved)"""
    owner = _actor(101)
    handler = _actor(202, "complaint_handler")
    sup = _actor(303, "complaint_supervisor")
    c = services.submit(actor=owner, category="Facilities", description="WF006")
    services.decide_outcome(complaint_id=c.pk, actor=handler, outcome="resolved", details="Resolved")
    services.verify_closure(complaint_id=c.pk, actor=owner, verifier="complainant")
    req = services.request_reopening(complaint_id=c.pk, actor=owner, reason="Reopen")
    services.review_reopening(request_id=req.pk, actor=sup, decision="approved", note="Yes")
    c.refresh_from_db()
    assert c.status == "in_progress"


@pytest.mark.django_db
def test_wf_007_manual_escalation_path():
    """test_id: WF-007 | source_id: BW-CMS-07 / CW-CMS-03 (Manual Escalation Path)"""
    c = services.submit(actor=_actor(101), category="Facilities", description="WF007")
    esc = services.escalate(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), kind="manual")
    assert esc.escalation_kind == "manual"


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=2, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_wf_008_automatic_sla_escalation_path():
    """test_id: WF-008 | source_id: BW-CMS-08 / CW-CMS-03 (Automatic SLA Escalation Path)"""
    c = services.submit(actor=_actor(101), category="Facilities", description="WF008")
    services.setup_handling(complaint_id=c.pk, actor=_actor(202, "complaint_handler"), category="Facilities", priority="high")
    now = timezone.now()
    Complaint.objects.filter(pk=c.pk).update(sla_due_at=now - timedelta(minutes=1))
    assert services.process_sla(now)["escalated"] == 1
    c.refresh_from_db()
    assert c.escalation_kind == "automatic"
