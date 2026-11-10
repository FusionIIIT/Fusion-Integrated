"""Gap tests: urgent exception, host decision and pass-view exception flows
(UC-013, UC-035, UC-012, BR-203, BW-VMS-22)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.vms.models import Notification, VisitPass, VisitRequest
from modules.vms.services import approval, registration, scheduler_work
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.registration.conftest import BASE, HOST_ID, payload

pytestmark = pytest.mark.django_db


def _data(**over):
    d = payload(**over)
    for k in ("scheduled_start", "scheduled_end"):
        if isinstance(d[k], str):
            d[k] = parse_datetime(d[k])
    return d


@pytest.fixture
def me():
    return f.make_visitor(id_doc_type="", id_doc_number="", full_name="",
                          email="ravi@example.com")


@pytest.fixture
def host_actor():
    return f.make_actor(kind="staff", user_id=HOST_ID)


@pytest.fixture
def pending(me):
    return registration.submit(session_visitor=me, data=_data())


@pytest.fixture
def urgent(me):
    """An urgent request awaiting an Admin, plus an Admin actor."""
    fixed = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    f.make_role_assignment(user_id=4001, role="admin")
    start = fixed + timedelta(hours=1)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)
        vr = registration.submit(session_visitor=me, data=_data(
            scheduled_start=start, scheduled_end=start + timedelta(hours=1)))
    assert vr.status == "awaiting_admin"
    return vr, f.make_actor(kind="staff", user_id=4001, permissions=["vms.urgent.decide"])


def test_br_203_urgent_host_unavailable_still_requires_admin_then_host(urgent, host_actor):
    """VMS-BR-203: admin approval of an urgent request does not skip host approval."""
    vr, admin = urgent
    after_admin = approval.decide_urgent(admin_actor=admin, request_id=vr.pk,
                                         decision="approve")
    assert after_admin.status == "pending" and not VisitPass.objects.exists()
    _, vp = approval.decide(host_actor=host_actor, request_id=vr.pk, decision="approve")
    vr.refresh_from_db()
    assert vr.status == "approved" and vp is not None


def test_uc_035_urgent_admin_outside_scope_cannot_decide(urgent):
    """VMS-UC-035: a user with no Admin assignment cannot decide an urgent request."""
    vr, _ = urgent
    outsider = f.make_actor(kind="staff", user_id=4999, permissions=["vms.urgent.decide"])
    with pytest.raises(PermissionDeniedError):
        approval.decide_urgent(admin_actor=outsider, request_id=vr.pk, decision="approve")
    vr.refresh_from_db()
    assert vr.status == "awaiting_admin"


def test_uc_035_urgent_approve_notifies_host_and_visitor(urgent):
    """VMS-UC-035: admin approval enqueues notices to host and visitor."""
    vr, admin = urgent
    approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert Notification.objects.filter(topic="request.submitted",
                                       recipient_user_id=HOST_ID).exists()
    assert Notification.objects.filter(topic="request.urgent_approved",
                                       recipient_visitor=vr.visitor).exists()


def test_uc_035_urgent_reject_requires_reason_and_notifies(urgent):
    """VMS-UC-035: urgent rejection needs a reason, ends Rejected, no pass."""
    vr, admin = urgent
    with pytest.raises(Exception) as e:
        approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="reject")
    assert getattr(e.value, "code", "") == "reason_required"
    approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="reject",
                           note="No capacity")
    vr.refresh_from_db()
    assert vr.status == "rejected" and not VisitPass.objects.exists()
    assert Notification.objects.filter(topic="request.rejected",
                                       recipient_visitor=vr.visitor).exists()


def test_uc_035_urgent_decision_twice_conflict(urgent):
    """VMS-UC-035: a second admin decision on the same request is a 409-style conflict."""
    vr, admin = urgent
    approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="approve")
    with pytest.raises(ConflictError) as e:
        approval.decide_urgent(admin_actor=admin, request_id=vr.pk, decision="reject",
                               note="late")
    assert e.value.code == "not_awaiting_admin"


def test_bw_vms_22_bw22_urgent_expiry_when_admin_silent(urgent):
    """BW-VMS-22: an unanswered urgent request past its timeout becomes Expired, no pass."""
    vr, _ = urgent
    n = scheduler_work.expire_pending(now=timezone.now() + timedelta(days=30))
    vr.refresh_from_db()
    assert n == 1 and vr.status == "expired" and not VisitPass.objects.exists()


def test_uc_013_host_approve_notifies_visitor_with_pass_link(pending, host_actor):
    """VMS-UC-013: approval enqueues request.approved and pass.issued to the visitor."""
    approval.decide(host_actor=host_actor, request_id=pending.pk, decision="approve")
    topics = set(Notification.objects.filter(recipient_visitor=pending.visitor)
                 .values_list("topic", flat=True))
    assert {"request.approved", "pass.issued"} <= topics


def test_uc_013_host_reject_notifies_visitor_with_reason(pending, host_actor):
    """VMS-UC-013: rejection notice carries the reason and no pass is created."""
    approval.decide(host_actor=host_actor, request_id=pending.pk, decision="reject",
                    note="Not available")
    rows = Notification.objects.filter(topic="request.rejected",
                                       recipient_visitor=pending.visitor)
    assert rows.exists() and all("Not available" in n.body for n in rows)
    assert not VisitPass.objects.exists()


def test_uc_013_host_approve_blocked_if_visitor_blacklisted_since_submission(
        pending, host_actor):
    """VMS-UC-013: approve after a new blacklist publication fails."""
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567")
    with pytest.raises(DomainError):
        approval.decide(host_actor=host_actor, request_id=pending.pk, decision="approve")
    assert not VisitPass.objects.exists()


@pytest.mark.parametrize("state", ["completed", "rejected",
                                   "expired", "approved"])
def test_uc_013_decision_on_non_pending_request_conflict(pending, host_actor, state):
    """VMS-UC-013: a decision on a non-pending request is a conflict."""
    VisitRequest.objects.filter(pk=pending.pk).update(status=state)
    with pytest.raises(ConflictError) as e:
        approval.decide(host_actor=host_actor, request_id=pending.pk, decision="approve")
    assert e.value.code == "not_pending"


def test_uc_013_decision_by_other_host_is_not_found(pending):
    """VMS-UC-013: a host who does not own the request cannot see it (404)."""
    from core.api.exceptions import NotFoundError
    other = f.make_actor(kind="staff", user_id=2002)
    with pytest.raises(NotFoundError):
        approval.decide(host_actor=other, request_id=pending.pk, decision="approve")


# --- pass view (UC-012) -----------------------------------------------------------------------

def _approved_with_pass(visitor, host_actor):
    vr = registration.submit(session_visitor=visitor, data=_data())
    _, vp = approval.decide(host_actor=host_actor, request_id=vr.pk, decision="approve")
    return vr, vp


def test_uc_012_pass_view_ok_then_denied_when_terminated(visitor_api, me, host_actor):
    """VMS-UC-012: pass endpoint returns 200 while active and 409 once terminated."""
    client, visitor = visitor_api(me)
    vr, vp = _approved_with_pass(visitor, host_actor)
    assert client.get(BASE + f"visitor/requests/{vr.pk}/pass").status_code == 200
    VisitPass.objects.filter(pk=vp.pk).update(terminated_at=timezone.now(), is_active=False)
    r = client.get(BASE + f"visitor/requests/{vr.pk}/pass")
    assert r.status_code == 409 and r.json()["error"]["code"] == "pass_not_available"


def test_uc_012_pass_view_denied_for_expired_pass(visitor_api, me, host_actor):
    """VMS-UC-012: pass endpoint returns 409 once the pass validity has passed."""
    client, visitor = visitor_api(me)
    vr, vp = _approved_with_pass(visitor, host_actor)
    VisitPass.objects.filter(pk=vp.pk).update(valid_until=timezone.now() - timedelta(minutes=1))
    assert client.get(BASE + f"visitor/requests/{vr.pk}/pass").status_code == 409


def test_uc_012_pass_view_denied_for_completed_request(visitor_api, me, host_actor):
    """VMS-UC-012: pass endpoint returns 409 for a completed request."""
    client, visitor = visitor_api(me)
    vr, _ = _approved_with_pass(visitor, host_actor)
    VisitRequest.objects.filter(pk=vr.pk).update(status="completed")
    assert client.get(BASE + f"visitor/requests/{vr.pk}/pass").status_code == 409


def test_uc_012_pass_view_other_visitor_404(visitor_api, me, host_actor):
    """VMS-UC-012: another visitor's request id yields 404."""
    _, owner = visitor_api(me)
    vr, _ = _approved_with_pass(owner, host_actor)
    other_client, _ = visitor_api(f.make_visitor(id_doc_number="", id_doc_type="",
                                                 full_name="", email="other@example.com"))
    assert other_client.get(BASE + f"visitor/requests/{vr.pk}/pass").status_code == 404
