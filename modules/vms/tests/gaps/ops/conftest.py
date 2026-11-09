"""Fixtures for the ops gap tests (copied from e_notify, f_monitor, g_events, h_reports)."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.api import csrf
from fusion_auth.client import IamSession
from modules.vms import auth
from modules.vms.models import RoleAssignment, VisitLog
from modules.vms.tests import factories as f

SEC, ADMIN, HOST = 3001, 4001, 2001
SEC_PERMS = ("vms.monitor.view", "vms.muster.trigger", "vms.muster.rollcall")
ADMIN_PERMS = (*SEC_PERMS, "vms.report.export")
EVENT_PERMS = ("vms.event.manage", "vms.pass.terminate", "vms.monitor.view")
GATE_PERMS = ("vms.gate.operate", "vms.gate.sync", "vms.monitor.view")
HEADER = "name,phone,email,id_doc_type,id_doc_number,slot_start,slot_end\n"
RAW = "visitor-raw-token"


@pytest.fixture
def api_as(stub_iam):
    """Same pattern as tests/conftest.py `api_as`."""
    def _make(anonymous=False, user_id=2001, permissions=(), kind="staff", email="",
              modules=("vms",)):
        if anonymous:
            stub_iam(None)
            return APIClient()
        stub_iam(IamSession(
            user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
            kind=kind, active_role=kind, roles=(kind,),
            permissions=frozenset(permissions), modules=tuple(modules), email=email))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client
    return _make


@pytest.fixture
def policy(db):
    f.make_published_policy(version=1)


@pytest.fixture(autouse=True)
def _directory(monkeypatch):
    from modules.vms.services import delivery, monitor, muster, reports

    def fake(ids):
        return {u: SimpleNamespace(user_id=u, display_name=f"Host {u}", department="Physics",
                                   email=f"u{u}@example.com") for u in ids}
    monkeypatch.setattr(monitor, "_directory_users", fake)
    monkeypatch.setattr(muster, "_directory_users", fake)
    monkeypatch.setattr(reports, "_directory_users", fake)
    monkeypatch.setattr(delivery.directory, "get_users", fake)


@pytest.fixture
def visitor_client():
    visitor = f.make_visitor()
    f.make_visitor_session(visitor=visitor, token_hash=auth.hash_token(RAW),
                           verified_at=timezone.now())
    c = APIClient()
    c.cookies[auth.COOKIE_NAME] = RAW
    c.credentials(HTTP_X_CSRF_TOKEN=csrf.token_for(RAW))
    return c, visitor


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
    now = timezone.now()
    vr = f.make_visit_request(status="approved", host_user_id=host)
    kw = {"valid_from": now - timedelta(hours=1), "valid_until": now + timedelta(hours=3)}
    kw.update(pass_kw)
    vp = f.make_visit_pass(visit_request=vr, **kw)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN, zone=zone)
    return vp


@pytest.fixture
def ev_admin(db):
    f.make_role_assignment(user_id=ADMIN, role=RoleAssignment.Role.ADMIN)
    return f.make_actor("staff", permissions=EVENT_PERMS, user_id=ADMIN)


@pytest.fixture
def gate(db):
    return f.make_gate()


@pytest.fixture
def guard(gate):
    f.make_role_assignment(user_id=SEC, role=RoleAssignment.Role.SECURITY,
                           scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate.pk)
    return f.make_actor("staff", permissions=GATE_PERMS, user_id=SEC)


@pytest.fixture
def event(ev_admin, gate):
    from modules.vms.services import bulk_events
    now = timezone.now()
    return bulk_events.create_event(
        admin_actor=ev_admin, name="Open Day", organizer="Dept of CS",
        valid_from=now - timedelta(hours=1), valid_until=now + timedelta(hours=6),
        zone_ids=[gate.zone_id], fast_lane=True, walkin_rate_limit=2)


def csv_rows(n, prefix="A"):
    lines = [HEADER.strip()]
    lines.extend(f"Guest {i},9{i:09d},g{i}@example.com,passport,{prefix}{i:06d},,"
                 for i in range(n))
    return "\n".join(lines) + "\n"
