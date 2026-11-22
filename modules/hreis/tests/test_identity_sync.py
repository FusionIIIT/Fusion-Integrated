"""Configured identity refresh preserves IAM ownership and immediately enforces current grants."""

from dataclasses import replace

import pytest
from rest_framework.test import APIClient

from modules.directory.contracts import get_users
from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.tests.actors import make_session

pytestmark = pytest.mark.django_db


def test_configured_identity_refresh_updates_projection_and_current_role_gate(
    stub_iam, user_ref, settings
):
    # BR-HR-028 / HR-AFR-092: real directory contracts refresh IAM-owned fields without HR identity writes.
    settings.DIRECTORY_MAX_AGE_SECONDS = 0
    session = make_session(
        user_id=10,
        roles=("faculty",),
        active_role="faculty",
        kind="faculty",
        permissions=("hreis.service_record.view",),
        modules=("hreis",),
    )
    initial = replace(user_ref(10, "Synthetic First", kind="faculty"), department="CSE")
    iam = stub_iam(session, users={10: initial})
    EmployeeServiceRecord.objects.create(
        user_id=10, department="HR-owned snapshot", designation_snapshot="Professor"
    )
    first = get_users([10])[10]
    assert first.display_name == "Synthetic First" and first.department == "CSE"
    iam.users[10] = replace(
        initial, display_name="Synthetic Updated", department="ECE", is_active=False
    )
    refreshed = get_users([10])[10]
    assert (refreshed.display_name, refreshed.department, refreshed.is_active) == (
        "Synthetic Updated",
        "ECE",
        False,
    )
    assert EmployeeServiceRecord.objects.get(user_id=10).department == "HR-owned snapshot"
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    assert client.get("/api/v1/hreis/service-records/me/").status_code == 200
    iam.session = replace(session, permissions=())
    assert client.get("/api/v1/hreis/service-records/me/").status_code == 403
    assert [call for call in iam.calls if call[0] == "get_users"] == [
        ("get_users", (10,)),
        ("get_users", (10,)),
    ]
    assert not any(call[0] in {"set_active_role", "login"} for call in iam.calls)
