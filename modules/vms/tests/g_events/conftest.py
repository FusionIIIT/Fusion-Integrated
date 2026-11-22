"""Lane G fixtures: an Admin with event rights, a gate guard, an active event."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import BlacklistVersion, RoleAssignment
from modules.vms.tests import factories as f

ADMIN_ID, SEC_ID = 4001, 3001
ADMIN_PERMS = ("vms.event.manage", "vms.pass.terminate", "vms.monitor.view")
SEC_PERMS = ("vms.gate.operate", "vms.gate.sync", "vms.monitor.view")
HEADER = "name,phone,email,id_doc_type,id_doc_number,slot_start,slot_end\n"


@pytest.fixture(autouse=True)
def _policy(db):
    f.make_published_policy(version=1)


@pytest.fixture
def admin(db):
    f.make_role_assignment(user_id=ADMIN_ID, role=RoleAssignment.Role.ADMIN)
    return f.make_actor("staff", permissions=ADMIN_PERMS, user_id=ADMIN_ID)


@pytest.fixture
def gate(db):
    return f.make_gate()


@pytest.fixture
def sec(gate):
    f.make_role_assignment(user_id=SEC_ID, role=RoleAssignment.Role.SECURITY,
                           scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate.pk)
    return f.make_actor("staff", permissions=SEC_PERMS, user_id=SEC_ID)


@pytest.fixture
def window():
    now = timezone.now()
    return now - timedelta(hours=1), now + timedelta(hours=6)


@pytest.fixture
def event(admin, gate, window):
    from modules.vms.services import bulk_events
    return bulk_events.create_event(
        admin_actor=admin, name="Open Day", organizer="Dept of CS", valid_from=window[0],
        valid_until=window[1], zone_ids=[gate.zone_id], fast_lane=True, walkin_rate_limit=2)


def csv_rows(n, prefix="A", **extra):
    """CSV text with n valid rows (unique document numbers)."""
    lines = [HEADER.strip()]
    lines.extend(f"Guest {i},9{i:09d},g{i}@example.com,passport,{prefix}{i:06d},,"
                 for i in range(n))
    return "\n".join(lines) + "\n"


def blacklist_doc(doc_number, severity="high"):
    version = f.make_blacklist_version(status=BlacklistVersion.Status.PUBLISHED,
                                       published_at=timezone.now())
    return f.make_blacklist_entry(version=version, id_doc_number=doc_number, severity=severity)
