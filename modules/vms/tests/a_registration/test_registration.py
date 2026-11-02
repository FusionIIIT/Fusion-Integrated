"""Pre-registration rules (UC-010)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.vms.models import (
    Alert,
    AuditLog,
    Notification,
    PreAuthorization,
    VisitPass,
    VisitRequest,
)
from modules.vms.services import registration
from modules.vms.tests import factories as f
from modules.vms.tests.a_registration.conftest import BASE, HOST_ID, local_slot, payload

pytestmark = pytest.mark.django_db


def _data(**over):
    """Service-level data (parsed datetimes)."""
    from django.utils.dateparse import parse_datetime
    d = payload(**over)
    for k in ("scheduled_start", "scheduled_end"):
        if isinstance(d[k], str):
            d[k] = parse_datetime(d[k])
    return d


def _submit(visitor, **over):
    return registration.submit(session_visitor=visitor, data=_data(**over))


@pytest.fixture
def me():
    return f.make_visitor(id_doc_type="", id_doc_number="", full_name="",
                          email="ravi@example.com")


def test_standard_submission_is_pending_with_audit_and_host_notice(me):
    vr = _submit(me)
    assert (vr.status, vr.source, vr.host_user_id) == ("pending", "pre_registered", HOST_ID)
    assert vr.expires_at > timezone.now() and vr.created_by_visitor == me
    me.refresh_from_db()
    assert vr.visitor == me and me.id_doc_number == "P1234567"   # login row completed
    assert AuditLog.objects.filter(action="vms.request.submitted",
                                   entity_id=str(vr.pk)).exists()
    n = Notification.objects.filter(topic="request.submitted").first()
    assert n.recipient_user_id == HOST_ID
    assert not VisitPass.objects.exists()


@pytest.mark.parametrize("field", ["full_name", "phone", "id_doc_type", "id_doc_number",
                                   "purpose", "host_user_id", "scheduled_start"])
def test_br_037_missing_field_rejected(me, field):
    with pytest.raises(BadRequestError) as e:
        _submit(me, **{field: ""})
    assert e.value.code == "missing_fields"
    assert not VisitRequest.objects.exists()


def test_br_186_unsupported_doc_type(me):
    with pytest.raises(BadRequestError) as e:
        _submit(me, id_doc_type="library_card")
    assert e.value.code == "unsupported_id_doc_type"


def test_br_186_malformed_doc_number(me):
    with pytest.raises(BadRequestError) as e:
        _submit(me, id_doc_number="!!")
    assert e.value.code == "invalid_id_document"


def test_end_before_start_rejected(me):
    start, end = local_slot()
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=end, scheduled_end=start)
    assert e.value.code == "invalid_window"


def test_host_must_be_faculty_or_staff(me):
    for bad in (2900, 99999):
        with pytest.raises(BadRequestError) as e:
            _submit(me, host_user_id=bad)
        assert e.value.code == "invalid_host"


def test_outside_visiting_hours_rejected(me):
    start, end = local_slot(hour=22, hours=1)
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=start, scheduled_end=end)
    assert e.value.code == "outside_visiting_hours"


def test_br_038_duplicate_pending_rejected(me):
    _submit(me)
    with pytest.raises(BadRequestError) as e:
        _submit(me)
    assert e.value.code == "duplicate_request"
    assert VisitRequest.objects.count() == 1


def test_br_051_blacklisted_rejected_and_alerted(me):
    f.make_role_assignment(user_id=3001, role="security")
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567")
    with pytest.raises(BadRequestError) as e:
        _submit(me)
    assert e.value.code == "visitor_blacklisted"
    assert not VisitRequest.objects.exists()
    alert = Alert.objects.get(kind="blacklist_hit")
    assert alert.status == "open"
    assert Notification.objects.filter(topic="alert.blacklist_hit",
                                       recipient_user_id=3001).exists()
    assert AuditLog.objects.filter(action="vms.request.blacklist_rejected").exists()


def test_advance_window_routes_to_urgent(me, monkeypatch):
    """BR-202/203: inside the advance window a same-day visit goes to an Admin."""
    fixed = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)
    f.make_role_assignment(user_id=4001, role="admin")
    start = fixed + timedelta(hours=1)
    vr = _submit(me, scheduled_start=start, scheduled_end=start + timedelta(hours=1))
    assert vr.status == "awaiting_admin" and vr.is_urgent
    assert Notification.objects.filter(topic="request.urgent", recipient_user_id=4001).exists()
    assert not Notification.objects.filter(topic="request.submitted").exists()


def test_advance_window_violated_and_not_same_day_is_rejected(me, monkeypatch):
    fixed = timezone.localtime().replace(hour=19, minute=0, second=0, microsecond=0)
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)
    nxt = (fixed + timedelta(days=1)).replace(hour=8, minute=30)   # 13.5 h ahead: ok
    assert _submit(me, scheduled_start=nxt, scheduled_end=nxt + timedelta(hours=1)).status \
        == "pending"
    # Policy forbids urgent: same-day inside the window is rejected.
    from modules.vms.models import AccessPolicy
    AccessPolicy.objects.update(allow_same_day_urgent=False)
    fixed2 = fixed.replace(hour=9)
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed2)
    soon = fixed2 + timedelta(hours=1)
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=soon, scheduled_end=soon + timedelta(hours=1),
                purpose="again")
    assert e.value.code == "advance_window"


def test_vip_skips_host(me):
    vip_visitor = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                                 full_name="Ravi Kumar")
    f.make_vip_permission(visitor=vip_visitor)
    vr = _submit(me)
    assert vr.source == "vip" and vr.status == "approved"
    vp = vr.passes.get()
    assert vp.pass_type == "VIP"
    assert not Notification.objects.filter(topic="request.submitted").exists()
    assert Notification.objects.filter(topic="pass.issued").exists()


def test_vip_outside_its_scope_is_a_normal_request(me):
    vip_visitor = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                                 full_name="Ravi Kumar")
    f.make_vip_permission(visitor=vip_visitor, valid_until=timezone.now() + timedelta(hours=1))
    assert _submit(me).status == "pending"       # D-16: window outside the override


def test_vip_does_not_bypass_the_blacklist(me):
    vip_visitor = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567")
    f.make_vip_permission(visitor=vip_visitor)
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567")
    with pytest.raises(BadRequestError):
        _submit(me)


def test_preauth_use_count_and_expiry(me):
    person = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                            full_name="Ravi Kumar")
    pa = f.make_pre_authorization(visitor=person, host_user_id=HOST_ID, max_visits=1)
    vr = _submit(me)
    assert vr.source == "pre_authorized" and vr.status == "approved"
    assert vr.passes.get().pass_type == "PRE_REGISTERED"
    pa.refresh_from_db()
    assert pa.used_visits == 1
    # exhausted -> next visit is a normal request
    start, end = local_slot(days=2)
    assert _submit(me, scheduled_start=start, scheduled_end=end).status == "pending"
    # expired grant is ignored
    PreAuthorization.objects.update(used_visits=0, valid_until=timezone.now() - timedelta(1))
    start, end = local_slot(days=3)
    assert _submit(me, scheduled_start=start, scheduled_end=end).status == "pending"


def test_revoked_or_other_hosts_preauth_does_not_apply(me):
    person = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567")
    f.make_pre_authorization(visitor=person, host_user_id=2002)
    f.make_pre_authorization(visitor=person, host_user_id=HOST_ID,
                             revoked_at=timezone.now())
    assert _submit(me).status == "pending"


def test_br_129_old_request_keeps_old_policy(me):
    vr = _submit(me)
    from modules.vms.models import AccessPolicy
    AccessPolicy.objects.filter(version=1).update(published_at=timezone.now() - timedelta(1))
    f.make_published_policy(version=2, max_visit_hours=1,
                            published_at=timezone.now() + timedelta(minutes=1))
    from modules.vms.services import approval
    host = f.make_actor(kind="staff", user_id=HOST_ID)
    _, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    assert (vp.valid_until - vp.valid_from) == timedelta(hours=2)   # v1 cap (8h), not v2 (1h)
    vr2 = _submit(me, purpose="new", scheduled_start=local_slot(days=2)[0],
                  scheduled_end=local_slot(days=2)[1])
    assert vr2.status == "pending"


def test_one_person_keeps_one_visitor_record(me):
    _submit(me)
    other = f.make_visitor(id_doc_type="", id_doc_number="", full_name="", email="x@y.com")
    start, end = local_slot(days=2)
    vr = registration.submit(session_visitor=other, data=_data(
        scheduled_start=start, scheduled_end=end))
    assert vr.visitor == me and vr.created_by_visitor == other


# --- API ------------------------------------------------------------------------------------

def test_api_pending_is_201_urgent_is_202(visitor_api, monkeypatch):
    client, _ = visitor_api()
    r = client.post(BASE + "visitor/pre-registrations", payload(), format="json")
    assert r.status_code == 201 and r.json()["status"] == "pending"
    fixed = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)
    start = fixed + timedelta(hours=1)
    r = client.post(BASE + "visitor/pre-registrations", payload(
        scheduled_start=start.isoformat(), scheduled_end=(start + timedelta(hours=1)).isoformat(),
        purpose="urgent"), format="json")
    assert r.status_code == 202 and r.json()["status"] == "awaiting_admin"


def test_api_missing_field_is_400(visitor_api):
    client, _ = visitor_api()
    body = payload()
    del body["purpose"]
    r = client.post(BASE + "visitor/pre-registrations", body, format="json")
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_fields"
