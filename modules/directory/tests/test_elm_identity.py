import pytest

from modules.directory import contracts
from modules.directory.models import UserRef
from modules.directory.services import sync

pytestmark = pytest.mark.django_db


def test_contract_preserves_inactive_identity_status(monkeypatch):
    UserRef.objects.create(user_id=700, username="inactive", display_name="Inactive",
                           kind="staff", is_active=False)
    monkeypatch.setattr(contracts, "ensure_users_cached", lambda ids: 0)
    assert contracts.get_users([700])[700].is_active is False


def test_zero_ttl_refreshes_even_when_the_clock_equals_synced_at(settings, monkeypatch):
    settings.DIRECTORY_MAX_AGE_SECONDS = 0
    row = UserRef.objects.create(user_id=701, username="fresh", display_name="Fresh", kind="staff")
    monkeypatch.setattr(sync.timezone, "now", lambda: row.synced_at)
    calls = []

    class Client:
        def get_users(self, ids):
            calls.append(ids)
            return {}

    monkeypatch.setattr(sync, "get_client", Client)
    sync.ensure_users_cached([701])
    assert calls == [[701]]
