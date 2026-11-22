"""Fixtures for gate gap tests (pattern copied from b_gate/conftest.py and tests/conftest.py)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from fusion_auth.client import IamSession
from modules.vms.models import RoleAssignment
from modules.vms.tests import factories as f

SECURITY_PERMS = ["vms.gate.operate", "vms.gate.escalate", "vms.gate.sync",
                  "vms.monitor.view"]
ADMIN_PERMS = ["vms.gate.override", "vms.zone.elevate", "vms.gate.operate",
               "vms.monitor.view"]


@pytest.fixture(autouse=True)
def _published_policy(db):
    f.make_published_policy(version=1)


@pytest.fixture
def gate(db):
    return f.make_gate()


@pytest.fixture
def sec(gate):
    f.make_role_assignment(user_id=3001, role=RoleAssignment.Role.SECURITY,
                           scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate.pk)
    return f.make_actor(user_id=3001, permissions=SECURITY_PERMS)


@pytest.fixture
def admin(db):
    f.make_role_assignment(user_id=4001, role=RoleAssignment.Role.ADMIN)
    return f.make_actor(user_id=4001, permissions=ADMIN_PERMS)


@pytest.fixture
def vpass(db):
    now = timezone.now()
    vr = f.make_visit_request(status="approved")
    return f.make_visit_pass(visit_request=vr, valid_from=now - timedelta(hours=1),
                             valid_until=now + timedelta(hours=2))


@pytest.fixture
def api_as(stub_iam):
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


def cred(vp):
    return {"qr_token": vp.qr_token}


def blacklist(visitor, severity="high"):
    from modules.vms.models import BlacklistVersion
    version = f.make_blacklist_version(status=BlacklistVersion.Status.PUBLISHED,
                                       published_at=timezone.now())
    return f.make_blacklist_entry(version=version, id_doc_number=visitor.id_doc_number,
                                  severity=severity)
