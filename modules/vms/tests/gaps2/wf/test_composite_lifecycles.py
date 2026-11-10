"""Composite workflow chains CW-VMS-01, CW-VMS-02 and CW-VMS-05 through the real services."""
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from core.api.exceptions import ConflictError
from modules.vms.models import ExtensionRequest, VisitLog, VisitPass, VisitRequest
from modules.vms.services import (
    approval,
    checkout,
    extensions,
    registration,
    scheduler_work,
    termination,
    walkin,
)
from modules.vms.services import gate as gsvc
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.registration.conftest import payload
from modules.vms.tests.gaps.visit.conftest import walkin_data

from .conftest import HOST_ID

pytestmark = pytest.mark.django_db


def _data(**over):
    d = payload(**over)
    from django.utils.dateparse import parse_datetime
    for k in ("scheduled_start", "scheduled_end"):
        if isinstance(d[k], str):
            d[k] = parse_datetime(d[k])
    return d


def _enter(security, gate, vp):
    res = gsvc.validate_and_check_in(security_actor=security,
                                     credential={"qr_token": vp.qr_token}, gate_id=gate.pk)
    assert res.outcome == gsvc.CHECKED_IN
    return res


def _status(vr):
    return VisitRequest.objects.get(pk=vr.pk).status


def test_cw_vms_01_rejected_then_resubmit_then_approved_to_completed(security, host, gate):
    """CW-VMS-01: BW-02 (rejected) -> re-submit -> BW-01 (approved, gate in, gate out, completed)."""
    me = f.make_visitor(id_doc_type="", id_doc_number="", full_name="", email="ravi@example.com")
    first = registration.submit(session_visitor=me, data=_data())
    assert first.status == "pending"
    vr, vp = approval.decide(host_actor=host, request_id=first.pk, decision="reject",
                             note="Out of office")
    assert vr.status == "rejected" and vp is None
    assert not VisitPass.objects.exists()

    second = registration.submit(session_visitor=me, data=_data())
    assert second.pk != first.pk and second.status == "pending"
    vr, vp = approval.decide(host_actor=host, request_id=second.pk, decision="approve")
    assert vr.status == "approved" and vp.pass_type == "PRE_REGISTERED"
    assert _status(first) == "rejected"

    with freeze_time(vp.valid_from + timedelta(minutes=10)):
        _enter(security, gate, vp)
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=gate.pk)
    assert _status(second) == "completed"


def test_cw_vms_01_expired_then_resubmit_then_approved_to_completed(security, host, gate):
    """CW-VMS-01: BW-03 (approval timeout -> expired) -> re-submit -> approved -> completed."""
    me = f.make_visitor(id_doc_type="", id_doc_number="", full_name="", email="ravi@example.com")
    first = registration.submit(session_visitor=me, data=_data())
    assert scheduler_work.expire_pending(now=timezone.now() + timedelta(days=3)) >= 1
    assert _status(first) == "expired"
    with pytest.raises(ConflictError):
        approval.decide(host_actor=host, request_id=first.pk, decision="approve")

    second = registration.submit(session_visitor=me, data=_data())
    assert second.status == "pending"
    _, vp = approval.decide(host_actor=host, request_id=second.pk, decision="approve")
    with freeze_time(vp.valid_from + timedelta(minutes=10)):
        _enter(security, gate, vp)
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=gate.pk)
    assert _status(second) == "completed"


def test_cw_vms_02_walkin_host_approved_extended_checked_out(security, host, gate):
    """CW-VMS-02: BW-06 walk-in host-approved -> on-site -> extension (cross-cutting) -> exit."""
    vr = walkin.register(security_actor=security, data=walkin_data(), host_user_id=HOST_ID)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    assert vp.pass_type == "WALK_IN" and _status(vr) == "approved"
    _enter(security, gate, vp)
    new_end = vp.valid_until + timedelta(hours=1)
    ext = extensions.request_extension(requester=host, request_id=vr.pk, new_end=new_end,
                                       reason="Meeting overran")
    vp.refresh_from_db()
    assert ext.status == "approved" and vp.valid_until == new_end
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=gate.pk)
    assert _status(vr) == "completed"


def test_cw_vms_02_walkin_contingency_then_admin_terminates_and_exits(security, admin, gate):
    """CW-VMS-02: BW-07 contingency-approved walk-in -> on-site -> terminated -> exit completed."""
    vr = walkin.register(security_actor=security, data=walkin_data(host_available=False),
                         host_user_id=HOST_ID)
    _, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    _enter(security, gate, vp)
    termination.terminate(actor=admin, pass_id=vp.pk, reason="policy breach")
    vp.refresh_from_db()
    assert not vp.is_active and _status(vr) == "approved"
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=gate.pk)
    assert _status(vr) == "completed"


def test_cw_vms_02_walkin_host_rejected_has_no_pass(security, host, gate):
    """CW-VMS-02: BW-08 host-rejected walk-in ends Rejected with no pass to enter on."""
    vr = walkin.register(security_actor=security, data=walkin_data(), host_user_id=HOST_ID)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "reject", note="Not expected")
    assert vp is None and _status(vr) == "rejected" and not vr.passes.exists()


def _onsite_walkin_pass(security, host, gate):
    vr = walkin.register(security_actor=security, data=walkin_data(), host_user_id=HOST_ID)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    _enter(security, gate, vp)
    return vr, vp


def test_cw_vms_05_extend_then_terminate(security, host, admin, gate):
    """CW-VMS-05: BW-23 admin-approved extension beyond the cap, then BW-18 admin
    termination while on-site, then BW-18 R2 physical exit -> completed."""
    vr, vp = _onsite_walkin_pass(security, host, gate)
    start = vr.scheduled_start
    ext = extensions.request_extension(requester=host, request_id=vr.pk,
                                       new_end=start + timedelta(hours=12), reason="Audit")
    assert ext.status == "pending"
    extensions.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="approve")
    vp.refresh_from_db()
    assert vp.valid_until == start + timedelta(hours=12)
    assert ExtensionRequest.objects.get(pk=ext.pk).status == "approved"

    termination.terminate(actor=admin, pass_id=vp.pk, reason="policy breach")
    vp.refresh_from_db()
    assert not vp.is_active and _status(vr) == "approved"        # on-site pending exit
    assert VisitLog.objects.filter(visit_pass=vp, event="terminated").exists()
    with pytest.raises(ConflictError):
        termination.terminate(actor=admin, pass_id=vp.pk, reason="again")
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=gate.pk)
    assert _status(vr) == "completed"


def test_cw_vms_05_extend_then_host_terminate_before_checkin(security, host):
    """CW-VMS-05: extension on a not-yet-entered pass, then BW-15 host termination ends the visit."""
    vr = walkin.register(security_actor=security, data=walkin_data(), host_user_id=HOST_ID)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    new_end = vp.valid_until + timedelta(hours=1)
    ext = extensions.request_extension(requester=host, request_id=vr.pk, new_end=new_end)
    assert ext.status == "approved"
    termination.terminate(actor=host, pass_id=vp.pk, reason="breach")
    vp.refresh_from_db()
    assert not vp.is_active and _status(vr) == "completed"
