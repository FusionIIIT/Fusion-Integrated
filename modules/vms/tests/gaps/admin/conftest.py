from types import SimpleNamespace

import pytest

from modules.vms.services import roles
from modules.vms.tests import factories as f


@pytest.fixture
def directory(monkeypatch):
    """Fake campus directory: `directory[user_id] = "faculty"` registers a person."""
    people = {}

    def fake(ids):
        return {i: SimpleNamespace(user_id=i, kind=people[i]) for i in ids if i in people}

    monkeypatch.setattr(roles, "_directory_users", fake)
    return people


@pytest.fixture
def super_actor():
    return f.make_actor(kind="staff", permissions=[
        "vms.role.assign", "vms.integration.manage", "vms.vip.manage", "vms.audit.view"])


@pytest.fixture
def admin_actor():
    return f.make_actor(kind="staff", permissions=[
        "vms.policy.manage", "vms.policy.publish", "vms.blacklist.manage",
        "vms.blacklist.publish", "vms.safelist.manage", "vms.zone.manage"])


@pytest.fixture
def published_policy():
    return f.make_published_policy(version=1)
