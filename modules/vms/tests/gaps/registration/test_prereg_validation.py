"""Gap tests: pre-registration validation and exception flows (UC-010, BR-037/038/187/202/203)."""
from datetime import time, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.api.exceptions import BadRequestError, DomainError
from modules.vms.models import AccessPolicy, VisitPass, VisitRequest
from modules.vms.services import passes, registration
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.registration.conftest import HOST_ID, local_slot, payload

pytestmark = pytest.mark.django_db


def _data(**over):
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


def _publish_blacklist(**entry):
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, **entry)
    return v


def _freeze(monkeypatch, fixed):
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)


def test_uc_010_preregister_rejects_blacklisted_visitor_on_phone_only_match(me):
    """VMS-UC-010: phone-only blacklist hit blocks submission."""
    _publish_blacklist(id_doc_number="", phone="9876543210")
    with pytest.raises(BadRequestError) as e:
        _submit(me, id_doc_number="Z9999999")
    assert e.value.code == "visitor_blacklisted"
    assert not VisitRequest.objects.exists()


def test_uc_010_preregister_host_not_found_in_directory_rejected(me):
    """VMS-UC-010: unknown host id gives 400 and no row."""
    with pytest.raises(BadRequestError) as e:
        _submit(me, host_user_id=424242)
    assert e.value.code == "invalid_host"
    assert not VisitRequest.objects.exists()


def test_uc_010_preregister_past_visit_date_rejected(me):
    """VMS-UC-010: visit start in the past is rejected."""
    start, end = local_slot(days=-1)
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=start, scheduled_end=end)
    assert e.value.code == "start_in_past"


def test_uc_010_preregister_zone_not_in_policy_rejected(me):
    """VMS-UC-010: inactive requested zone is rejected."""
    zone = f.make_zone(is_active=False)
    with pytest.raises(BadRequestError) as e:
        _submit(me, requested_zones=[zone])
    assert e.value.code == "invalid_zone"
    assert not VisitRequest.objects.exists()


def test_uc_010_preregister_duplicate_allowed_after_rejection(me):
    """VMS-UC-010: same visitor/host/slot may be re-submitted once prior is rejected."""
    first = _submit(me)
    VisitRequest.objects.filter(pk=first.pk).update(status="rejected")
    second = _submit(me)
    assert second.pk != first.pk and second.status == "pending"


def test_uc_010_preregister_duplicate_allowed_after_expiry(me):
    """VMS-UC-010: expired prior request does not block a resubmission."""
    first = _submit(me)
    VisitRequest.objects.filter(pk=first.pk).update(status="expired")
    assert _submit(me).status == "pending"


def test_br_038_duplicate_check_ignores_other_host(me):
    """VMS-BR-038: same visitor with a different host is not a duplicate."""
    _submit(me)
    vr = _submit(me, host_user_id=2002)
    assert vr.host_user_id == 2002 and VisitRequest.objects.count() == 2


@pytest.mark.xfail(strict=True, reason="BUG: duplicate check matches scheduled_start exactly, "
                   "so a partially overlapping window for the same visitor+host is accepted")
def test_br_038_duplicate_check_overlapping_window_rejected(me):
    """VMS-BR-038: partially overlapping window for same visitor+host rejected."""
    start, end = local_slot(hour=10, hours=2)
    _submit(me, scheduled_start=start, scheduled_end=end)
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=start + timedelta(hours=1),
                scheduled_end=end + timedelta(hours=1))
    assert e.value.code == "duplicate_request"


@pytest.mark.parametrize("field", ["full_name", "phone", "id_doc_type", "id_doc_number",
                                   "purpose"])
def test_br_037_each_mandatory_field_whitespace_rejected(me, field):
    """VMS-BR-037: whitespace-only mandatory field names the field in the error."""
    with pytest.raises(BadRequestError) as e:
        _submit(me, **{field: "   "})
    assert e.value.code == "missing_fields"
    assert field in str(e.value.message)
    assert not VisitRequest.objects.exists()


@pytest.mark.parametrize("doc_type", ["passport", "aadhaar", "driving_licence", "voter_id"])
def test_br_187_every_supported_document_type_accepted(me, doc_type):
    """VMS-BR-187: each supported ID type with a well-formed number passes."""
    vr = _submit(me, id_doc_type=doc_type, id_doc_number="AB1234567")
    assert vr.status == "pending" and vr.visitor.id_doc_type == doc_type


def test_br_203_urgent_only_for_same_day_visit(me, monkeypatch):
    """VMS-BR-203: a not-same-day request inside the advance window is rejected, not urgent."""
    AccessPolicy.objects.update(visiting_hours_start=time(0, 0), visiting_hours_end=time(23, 59))
    fixed = timezone.localtime().replace(hour=23, minute=30, second=0, microsecond=0)
    _freeze(monkeypatch, fixed)
    start = fixed + timedelta(hours=1)          # 00:30 next day, 1 h ahead (< 2 h window)
    with pytest.raises(BadRequestError) as e:
        _submit(me, scheduled_start=start, scheduled_end=start + timedelta(minutes=30))
    assert e.value.code in ("advance_window", "outside_visiting_hours")


def test_br_202_advance_window_exact_boundary_accepted_and_one_minute_over_urgent(
        me, monkeypatch):
    """VMS-BR-202: exactly the window ahead is standard; one minute short routes to urgent."""
    fixed = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    _freeze(monkeypatch, fixed)
    f.make_role_assignment(user_id=4001, role="admin")
    ok = fixed + timedelta(hours=2)
    assert _submit(me, scheduled_start=ok,
                   scheduled_end=ok + timedelta(hours=1)).status == "pending"
    short = fixed + timedelta(hours=2) - timedelta(minutes=1)
    vr = _submit(me, scheduled_start=short, scheduled_end=short + timedelta(hours=1),
                 purpose="second")
    assert vr.status == "awaiting_admin" and vr.is_urgent


def test_br_211_pass_type_set_per_origin(me):
    """VMS-BR-211: pre-registered, VIP and pre-authorised origins carry the right pass type."""
    from modules.vms.services import approval
    vr = _submit(me)
    host = f.make_actor(kind="staff", user_id=HOST_ID)
    _, vp = approval.decide(host_actor=host, request_id=vr.pk, decision="approve")
    assert vp.pass_type == VisitPass.PassType.PRE_REGISTERED

    person = f.make_visitor(id_doc_type="passport", id_doc_number="V1234567",
                            full_name="V Person")
    f.make_vip_permission(visitor=person)
    vip_vr = _submit(me, id_doc_number="V1234567", purpose="vip")
    assert vip_vr.passes.get().pass_type == VisitPass.PassType.VIP

    pa_person = f.make_visitor(id_doc_type="passport", id_doc_number="Q1234567",
                               full_name="Q Person")
    f.make_pre_authorization(visitor=pa_person, host_user_id=HOST_ID)
    pa_vr = _submit(me, id_doc_number="Q1234567", purpose="pa")
    assert pa_vr.passes.get().pass_type == VisitPass.PassType.PRE_REGISTERED


@pytest.mark.xfail(strict=True, reason="BUG: passes.issue_pass has no pass_type domain check; "
                   "an unknown type surfaces as a raw DB IntegrityError, not a validation error")
def test_br_211_pass_type_outside_domain_rejected():
    """VMS-BR-211: issuing a pass with an unknown type raises a validation error."""
    vr = f.make_visit_request(status="approved")
    with pytest.raises(DomainError):
        passes.issue_pass(request=vr, pass_type="BOGUS", issued_by=HOST_ID)


def test_br_211_pass_type_outside_domain_not_persisted():
    """VMS-BR-211: an unknown pass type never produces a pass row."""
    vr = f.make_visit_request(status="approved")
    with pytest.raises((DomainError, IntegrityError, ValueError)):
        passes.issue_pass(request=vr, pass_type="BOGUS", issued_by=HOST_ID)
    assert not VisitPass.objects.filter(visit_request=vr).exists()
