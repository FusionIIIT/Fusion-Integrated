"""Privilege Escalation and Route Authorization Tests.
Ensures roles cannot execute actions outside their granted permissions.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, **session_kwargs):
    stub_iam(make_session(**session_kwargs))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_student_cannot_execute_gate_check_in(stub_iam):
    """Students only have vms.visit.create; attempting gate scan must yield 403."""
    student_client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("vms",),
        permissions=("vms.visit.create",),
        roles=("student",),
    )
    res = student_client.post(
        "/api/v1/vms/gate/check-in/", data={"qr_code_hash": "dummy"}, format="json"
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_guard_cannot_approve_visits(stub_iam):
    """Guards have vms.gate.scan; attempting host approval must yield 403."""
    guard_client = _auth_client(
        stub_iam,
        user_id=2001,
        modules=("vms",),
        permissions=("vms.gate.scan",),
        roles=("security_guard",),
    )
    res = guard_client.post("/api/v1/vms/visits/1/approve/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_regular_user_cannot_trigger_emergency_muster(stub_iam):
    """Non-admins attempting emergency muster must yield 403."""
    client = _auth_client(
        stub_iam,
        user_id=3001,
        modules=("vms",),
        permissions=("vms.visit.create", "vms.visit.approve"),
    )
    res = client.post("/api/v1/vms/emergency/muster/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_guard_cannot_add_to_blacklist(stub_iam):
    """Guards cannot modify the security blacklist without vms.security.admin."""
    client = _auth_client(
        stub_iam,
        user_id=2001,
        modules=("vms",),
        permissions=("vms.gate.scan",),
    )
    res = client.post(
        "/api/v1/vms/security/blacklist/",
        data={"id_type": "aadhaar", "id_number": "123", "full_name": "Test", "reason": "Test"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
