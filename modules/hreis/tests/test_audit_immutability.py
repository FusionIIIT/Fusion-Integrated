"""Tests verifying audit log immutability and compliance reporting (BR-HR-025, AFR-087)."""
from django.core.exceptions import PermissionDenied
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import HrAuditLog

pytestmark = pytest.mark.django_db


def test_audit_log_immutability_on_save():
    log = HrAuditLog.objects.create(
        actor_id=101,
        actor_username="u101",
        actor_role="faculty",
        action="leave_applied",
        entity_type="leave",
        entity_id="1",
        details={"type": "casual"},
        ip_address="127.0.0.1",
    )

    # Attempting to modify existing audit record must raise PermissionDenied
    log.action = "tampered_action"
    with pytest.raises(PermissionDenied, match="immutable"):
        log.save()


def test_audit_log_immutability_on_delete():
    log = HrAuditLog.objects.create(
        actor_id=101,
        actor_username="u101",
        actor_role="faculty",
        action="leave_approved",
        entity_type="leave",
        entity_id="1",
        details={"status": "approved"},
        ip_address="127.0.0.1",
    )

    # Attempting to delete existing audit record must raise PermissionDenied
    with pytest.raises(PermissionDenied, match="cannot be deleted"):
        log.delete()


def test_hr_admin_can_view_audit_logs(stub_iam, user_ref):
    HrAuditLog.objects.create(
        actor_id=101,
        actor_username="u101",
        actor_role="faculty",
        action="cpda_claimed",
        entity_type="cpda",
        entity_id="5",
        details={"amount": 25000.0},
        ip_address="10.0.0.1",
    )

    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            roles=("hr_admin",),
            modules=("hr_eis",),
            permissions=("hr_eis.audit.view",),
        ),
        users={999: user_ref(999, name="HR Manager", kind="staff")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1
    assert rows[0]["action"] == "cpda_claimed"
