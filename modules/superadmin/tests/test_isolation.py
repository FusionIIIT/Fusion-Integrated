"""Tests for Super Admin data scoping, isolation, and audit log immutability."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.domain.exceptions import ImmutableRecordError
from modules.superadmin.models import AuditLogRecord, UserAccountRecord
from modules.superadmin.selectors.scoping import get_scoped_or_404

pytestmark = pytest.mark.django_db


def test_scoping_missing_record_yields_404_never_403(stub_iam):
    stub_iam(
        make_session(
            user_id=1001,
            kind="staff",
            permissions=("superadmin.user.view",),
            modules=("superadmin",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-123")

    # Accessing nonexistent user returns 404 (NotFoundError), never 403
    res = client.get("/api/v1/superadmin/users/999999/")
    assert res.status_code == 404


def test_scoped_or_404_selector_helper():
    u = UserAccountRecord.objects.create(
        user_id=7001,
        institute_id="24BCS701",
        email="u7001@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ACTIVE",
    )
    # Finding existing returns instance
    found = get_scoped_or_404(UserAccountRecord, user_id=7001)
    assert found.id == u.id

    # Missing raises NotFoundError
    with pytest.raises(Exception) as exc_info:
        get_scoped_or_404(UserAccountRecord, user_id=999999)
    assert "not found" in str(exc_info.value).lower()


def test_audit_log_record_immutability():
    log = AuditLogRecord.objects.create(
        event_type="SECURITY_EVENT",
        actor_user_id=1,
        target_entity="USER",
        target_id="100",
        action_details={"note": "original"},
    )

    # Attempting to update existing audit log MUST raise ImmutableRecordError
    log.action_details = {"note": "tampered"}
    with pytest.raises(ImmutableRecordError, match="Audit log records are append-only"):
        log.save()

    # Attempting to delete existing audit log MUST raise ImmutableRecordError
    with pytest.raises(ImmutableRecordError, match="Audit log records cannot be deleted"):
        log.delete()
