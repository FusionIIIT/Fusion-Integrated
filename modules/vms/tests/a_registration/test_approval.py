"""Host decision, bulk decision and the Admin urgent exception."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import AuditLog, Notification, VisitPass
from modules.vms.services import approval
from modules.vms.tests import factories as f
from modules.vms.tests.a_registration.conftest import HOST_ID

pytestmark = pytest.mark.django_db


def _pending(**kw):
    kw.setdefault("host_user_id", HOST_ID)
    kw.setdefault("source", "pre_registered")
    kw.setdefault("expires_at", timezone.now() + timedelta(hours=24))
    return f.make_visit_request(status="pending", **kw)


def test_br_052_pass_only_after_host_approval(host):
    vr = _pending()
    assert not VisitPass.objects.exists()
    r, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve",
                            note="ok")
    assert r.status == "approved" and vp.pass_type == "PRE_REGISTERED" and vp.is_active
    assert r.decided_at and r.decision_note == "ok"
    topics = set(Notification.objects.values_list("topic", flat=True))
    assert {"request.approved", "pass.issued"} <= topics
    assert AuditLog.objects.filter(action="vms.request.approved").exists()


def test_reject_requires_a_reason_and_issues_no_pass(host):
    vr = _pending()
    with pytest.raises(BadRequestError) as e:
        approval.decide(host_actor=host, request_id=vr.pk, decision="reject")
    assert e.value.code == "reason_required"
    r, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="reject",
                            note="busy")
    assert r.status == "rejected" and vp is None and not VisitPass.objects.exists()
    assert Notification.objects.filter(topic="request.rejected").exists()


def test_br_193_pass_capped_to_policy(host):
    start = timezone.now() + timedelta(days=1)
    vr = _pending(scheduled_start=start, scheduled_end=start + timedelta(hours=20))
    _, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    assert vp.valid_until - vp.valid_from == timedelta(hours=8)


def test_only_assigned_host_can_decide_404(host):
    vr = _pending(host_user_id=2002)
    with pytest.raises(NotFoundError):
        approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    vr.refresh_from_db()
    assert vr.status == "pending"


def test_non_host_cannot_decide():
    vr = _pending()
    student = f.make_actor(kind="student", user_id=HOST_ID)
    with pytest.raises(PermissionDeniedError):
        approval.decide(host_actor=student, request_id=vr.pk, decision="approve")


def test_double_decision_conflict(host):
    vr = _pending()
    approval.decide(host_actor=host, request_id=vr.pk, decision="reject", note="no")
    with pytest.raises(ConflictError):
        approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    assert VisitPass.objects.count() == 0


def test_expired_request_cannot_be_decided(host):
    vr = _pending(expires_at=timezone.now() - timedelta(minutes=1))
    with pytest.raises(ConflictError) as e:
        approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    assert e.value.code == "request_expired"


def test_zone_restriction_must_be_a_subset(host):
    z1, z2, z3 = f.make_zone(), f.make_zone(), f.make_zone()
    vr = _pending()
    vr.requested_zones.set([z1, z2])
    with pytest.raises(BadRequestError):
        approval.decide(host_actor=host, request_id=vr.pk, decision="approve", zones=[z3])
    _, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve",
                            zones=[z1])
    assert set(vp.allowed_zones.values_list("pk", flat=True)) == {z1.pk}


def test_window_can_narrow_but_never_widen(host):
    start = timezone.now() + timedelta(days=1)
    vr = _pending(scheduled_start=start, scheduled_end=start + timedelta(hours=4))
    with pytest.raises(BadRequestError):
        approval.decide(host_actor=host, request_id=vr.pk, decision="approve",
                        window={"end": start + timedelta(hours=5)})
    _, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve",
                            window={"start": start + timedelta(hours=1),
                                    "end": start + timedelta(hours=3)})
    assert (vp.valid_from, vp.valid_until) == (start + timedelta(hours=1),
                                               start + timedelta(hours=3))


def test_bulk_decide_is_per_id_independent(host):
    a, b = _pending(), _pending()
    other = _pending(host_user_id=2002)
    approval.decide(host_actor=host, request_id=b.pk, decision="reject", note="x")
    res = approval.bulk_decide(host_actor=host, ids=[a.pk, b.pk, other.pk, 99999],
                               decision="approve")
    by_id = {r["id"]: r for r in res}
    assert by_id[a.pk]["ok"] and by_id[a.pk]["status"] == "approved"
    assert by_id[b.pk] == {**by_id[b.pk], "ok": False, "error": "not_pending"}
    assert by_id[other.pk]["error"] == "not_found" and not by_id[99999]["ok"]


# --- urgent (UC-035, BW-22) ---------------------------------------------------------------

def _urgent():
    return f.make_visit_request(status="awaiting_admin", is_urgent=True,
                                urgent_decision="pending", host_user_id=HOST_ID,
                                source="pre_registered")


def test_urgent_approve_goes_to_pending_host_approval(admin):
    vr = _urgent()
    r = approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert (r.status, r.urgent_decision, r.urgent_decided_by_user_id) == (
        "pending", "approved", 4001)
    assert r.expires_at is not None and not VisitPass.objects.exists()
    assert Notification.objects.filter(topic="request.submitted",
                                       recipient_user_id=HOST_ID).exists()


def test_urgent_reject_needs_reason(admin):
    vr = _urgent()
    with pytest.raises(BadRequestError):
        approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="reject")
    r = approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="reject",
                               note="not justified")
    assert r.status == "rejected" and r.urgent_decision == "rejected"


def test_urgent_requires_admin_role_and_awaiting_state(admin):
    vr = _urgent()
    nobody = f.make_actor(kind="staff", user_id=4999, permissions=["vms.urgent.decide"])
    with pytest.raises(PermissionDeniedError):
        approval.decide_urgent(admin_actor=nobody, request_id=vr.pk, decision="approve")
    approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="approve")
    with pytest.raises(ConflictError):
        approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="approve")


def test_urgent_ignores_walk_in_contingency(admin):
    wi = f.make_visit_request(status="awaiting_admin", source="walk_in")
    with pytest.raises(NotFoundError):
        approval.decide_urgent(admin_actor=admin, request_id=wi.pk, decision="approve")
