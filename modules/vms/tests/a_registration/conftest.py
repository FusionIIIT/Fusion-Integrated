"""Lane A fixtures: a published policy, known hosts, visitor-session clients."""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from core.api import csrf
from modules.directory.contracts import UserDTO
from modules.vms import auth
from modules.vms.tests import factories as f

BASE = "/api/v1/vms/"
HOST_ID = 2001


@pytest.fixture(autouse=True)
def _env(monkeypatch, db):
    cache.clear()
    f.make_published_policy(version=1)
    kinds = {HOST_ID: "staff", 2002: "faculty", 2900: "student"}

    def fake_get_users(ids):
        return {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"User {i}",
                           kind=kinds[i]) for i in ids if i in kinds}
    monkeypatch.setattr("modules.directory.contracts.get_users", fake_get_users)


def local_slot(days=1, hour=10, hours=2):
    """A visit inside visiting hours, `days` ahead (local time)."""
    base = timezone.localtime() + timedelta(days=days)
    start = base.replace(hour=hour, minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=hours)


def payload(**over):
    start, end = local_slot()
    body = {"full_name": "Ravi Kumar", "phone": "9876543210", "email": "ravi@example.com",
            "id_doc_type": "passport", "id_doc_number": "P1234567",
            "host_user_id": HOST_ID, "purpose": "Interview",
            "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()}
    body.update(over)
    return body


def visitor_client(visitor=None):
    """(client, visitor) holding a verified session cookie and CSRF header."""
    visitor = visitor or f.make_visitor(id_doc_number="", id_doc_type="", full_name="",
                                        email="ravi@example.com")
    raw = f"raw-{visitor.pk}-{timezone.now().timestamp()}"
    f.make_visitor_session(visitor=visitor, token_hash=auth.hash_token(raw),
                           verified_at=timezone.now())
    client = APIClient()
    client.cookies[auth.COOKIE_NAME] = raw
    client.credentials(HTTP_X_CSRF_TOKEN=csrf.token_for(raw))
    return client, visitor


@pytest.fixture
def visitor_api():
    return visitor_client


@pytest.fixture
def host():
    from modules.vms.tests.factories import make_actor
    return make_actor(kind="staff", user_id=HOST_ID, permissions=[
        "vms.request.decide", "vms.request.view_assigned", "vms.preauth.manage"])


@pytest.fixture
def admin():
    actor = f.make_actor(kind="staff", user_id=4001, roles=("Registrar",),
                         permissions=["vms.urgent.decide"])
    f.make_role_assignment(user_id=4001, role="admin")
    return actor
