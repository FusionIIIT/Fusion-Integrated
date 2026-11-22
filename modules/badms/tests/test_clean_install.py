from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from fusion_auth.client import IamSession
from modules.accesscontrol.models import Module
from modules.badms.models import BackupRun

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True)
def test_migrated_seeded_and_granted_module_accepts_first_action(monkeypatch):
    call_command("seed_modules", stdout=StringIO())
    assert Module.objects.get(code="badms").status == "active"

    session = IamSession(
        user_id=4101,
        username="student-test",
        display_name="Student Test",
        kind="student",
        active_role="student",
        roles=("student",),
        permissions=frozenset({"badms.backup.view", "badms.backup.run_manual"}),
        modules=("badms",),
    )

    class FakeIamClient:
        def resolve_session(self, *, auth_token=None, cookies=None):
            assert auth_token == "clean-install-test-token"
            return session

    monkeypatch.setattr("fusion_auth.authentication.get_client", FakeIamClient)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token clean-install-test-token")

    response = client.get("/api/v1/badms/backup_runs")

    assert response.status_code == 200
    assert response.data["results"] == []
    assert BackupRun.objects.count() == 0
