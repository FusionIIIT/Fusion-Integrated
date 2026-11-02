"""VisitLog.detail carries the structured facts that `reason` used to encode."""
import pytest

from modules.vms.services import gate as svc
from modules.vms.tests import factories as f
from modules.vms.tests.b_gate.conftest import cred
from modules.vms.tests.b_gate.test_gate_service import JUSTIFICATION, denied_log, go

pytestmark = pytest.mark.django_db


def test_denial_stores_every_failure_code(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    log = go(sec, gate, cred(vpass)).log
    assert log.detail["failures"] == log.reason.split(",")
    assert "pass_inactive" in log.detail["failures"] and log.detail["manual"] is False


def test_plain_check_in_has_no_override_flags(sec, gate, vpass):
    log = go(sec, gate, cred(vpass)).log
    assert log.detail == {"vip_override": False}


def test_override_check_in_is_flagged(sec, gate, vpass, admin):
    denial = denied_log(sec, gate, vpass)
    res = svc.override(admin_actor=admin, denial_log_id=denial.pk, justification=JUSTIFICATION)
    assert res.log.detail["override"] is True and res.log.detail["denial_log_id"] == denial.pk


def test_manual_entry_is_flagged(sec, gate, vpass):
    res = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_in",
                                  reason="reader broken", gate_id=gate.pk)
    assert res.log.detail["manual"] is True and res.log.detail["manual_reason"] == "reader broken"
    out = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_out",
                                  reason="reader broken", gate_id=gate.pk)
    assert out.log.detail["manual"] is True


def test_vip_scope_flag_in_detail(sec, gate, vpass):
    zone = f.make_zone(is_restricted=True)
    vpass.pass_type = "VIP"
    vpass.save()
    f.make_vip_permission(visitor=vpass.visit_request.visitor).zones.add(zone)
    assert go(sec, gate, cred(vpass), zone_id=zone.pk).log.detail["vip_override"] is True
