"""Fixtures for lane B: a gate, a security officer scoped to it, an admin, a live pass."""
from datetime import timedelta

import pytest
from django.utils import timezone

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
    """Security officer 3001 whose role covers only `gate`."""
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


def cred(vp):
    return {"qr_token": vp.qr_token}


def blacklist(visitor, severity="high"):
    from modules.vms.models import BlacklistVersion
    version = f.make_blacklist_version(status=BlacklistVersion.Status.PUBLISHED,
                                       published_at=timezone.now())
    return f.make_blacklist_entry(version=version, id_doc_number=visitor.id_doc_number,
                                  severity=severity)
