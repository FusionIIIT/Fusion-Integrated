"""Fixtures for the composite-workflow chains (CW-VMS-01/02/05)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.directory.contracts import UserDTO
from modules.vms.tests import factories as f

HOST_ID, SEC_ID, ADMIN_ID = 2001, 3001, 3002


@pytest.fixture(autouse=True)
def _env(monkeypatch, db):
    f.make_published_policy(version=1, max_visit_hours=8)

    def fake_get_users(ids):
        return {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"User {i}",
                           kind="staff") for i in ids if i == HOST_ID}
    monkeypatch.setattr("modules.directory.contracts.get_users", fake_get_users)


@pytest.fixture
def gate():
    return f.make_gate()


@pytest.fixture
def security():
    f.make_role_assignment(user_id=SEC_ID, role="security")
    return f.make_actor("staff", user_id=SEC_ID, permissions=(
        "vms.walkin.register", "vms.gate.operate", "vms.monitor.view"))


@pytest.fixture
def host():
    return f.make_actor("staff", user_id=HOST_ID, permissions=(
        "vms.request.decide", "vms.pass.terminate", "vms.request.view_assigned"))


@pytest.fixture
def admin():
    now = timezone.now()
    f.make_role_assignment(user_id=ADMIN_ID, role="admin",
                           starts_at=now - timedelta(days=365), ends_at=now + timedelta(days=365))
    return f.make_actor("staff", user_id=ADMIN_ID, permissions=(
        "vms.walkin.contingency_decide", "vms.pass.terminate", "vms.extension.decide"))
