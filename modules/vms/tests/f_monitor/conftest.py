"""Fixtures for lane F: on-site visitors, a security officer, an admin, a fake directory."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.vms.models import VisitLog
from modules.vms.tests import factories as f

SEC, ADMIN, HOST = 3001, 4001, 2001
MONITOR_PERMS = ("vms.monitor.view",)
SEC_PERMS = ("vms.monitor.view", "vms.muster.trigger", "vms.muster.rollcall")
ADMIN_PERMS = ("vms.monitor.view", "vms.muster.trigger", "vms.muster.rollcall",
               "vms.report.export")


@pytest.fixture(autouse=True)
def _policy(db):
    f.make_published_policy(version=1)


@pytest.fixture(autouse=True)
def directory(monkeypatch):
    """Fake campus directory: hosts are in department 'Physics'."""
    from modules.vms.services import monitor, muster

    def fake(user_ids):
        return {u: SimpleNamespace(user_id=u, display_name=f"Host {u}", department="Physics")
                for u in user_ids}
    monkeypatch.setattr(monitor, "_directory_users", fake)
    monkeypatch.setattr(muster, "_directory_users", fake)


@pytest.fixture
def security():
    f.make_role_assignment(user_id=SEC, role="security")
    return f.make_actor("staff", permissions=SEC_PERMS, user_id=SEC)


@pytest.fixture
def admin():
    f.make_role_assignment(user_id=ADMIN, role="admin")
    return f.make_actor("staff", permissions=ADMIN_PERMS, user_id=ADMIN)


@pytest.fixture
def zone(db):
    return f.make_zone()


def put_on_site(zone=None, host=HOST, **pass_kw):
    """An approved request with a pass and a check-in (optionally in `zone`)."""
    now = timezone.now()
    vr = f.make_visit_request(status="approved", host_user_id=host)
    kw = {"valid_from": now - timedelta(hours=1), "valid_until": now + timedelta(hours=3)}
    kw.update(pass_kw)
    vp = f.make_visit_pass(visit_request=vr, **kw)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN, zone=zone)
    return vp


def zone_event(vp, zone, event="zone_allowed", reason=""):
    return f.make_visit_log(visit_pass=vp, event=event, zone=zone, reason=reason)


def check_out(vp):
    return f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_OUT)
