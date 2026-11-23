"""SuperAdminAuditLog is immutable: save() with pk blocks, delete() blocks."""

from __future__ import annotations

import pytest

from modules.superadmin.models.audit import SuperAdminAuditLog
from modules.superadmin.services.audit import record_audit_event

pytestmark = pytest.mark.django_db


def test_new_audit_log_saves_successfully():
    entry = record_audit_event(
        actor_id=1,
        actor_username="admin",
        actor_role="super_admin",
        action="archival.user.created",
        target_id="42",
        target_type="user",
        reason="Graduated.",
    )

    assert entry.pk is not None
    assert SuperAdminAuditLog.objects.filter(pk=entry.pk).exists()


def test_audit_log_save_with_pk_raises_permission_error():
    entry = record_audit_event(
        actor_id=1,
        actor_username="admin",
        actor_role="super_admin",
        action="archival.user.created",
        target_id="43",
        target_type="user",
        reason="Test.",
    )
    assert entry.pk is not None

    with pytest.raises(PermissionError, match="immutable"):
        entry.save()


def test_audit_log_delete_raises_permission_error():
    entry = record_audit_event(
        actor_id=1,
        actor_username="admin",
        actor_role="super_admin",
        action="purge.requested",
        target_id="1",
        target_type="purge_request",
        reason="Retention elapsed.",
    )

    with pytest.raises(PermissionError, match="immutable"):
        entry.delete()


def test_audit_log_queryset_delete_raises_permission_error():
    record_audit_event(
        actor_id=2,
        actor_username="ithead",
        actor_role="it_head",
        action="purge.approved",
        target_id="1",
        target_type="purge_request",
        reason="Approved.",
    )

    with pytest.raises(PermissionError, match="immutable"):
        SuperAdminAuditLog.objects.all().delete()


def test_audit_log_records_full_context():
    entry = record_audit_event(
        actor_id=5,
        actor_username="u5",
        actor_role="super_admin",
        action="policy.superseded",
        target_id="archival.reversibility_window_days",
        target_type="policy_parameter",
        result="SUCCESS",
        reason="New institute policy.",
        context_metadata={"key": "archival.reversibility_window_days", "new_value": "45"},
    )

    fetched = SuperAdminAuditLog.objects.get(pk=entry.pk)
    assert fetched.actor_username == "u5"
    assert fetched.action == "policy.superseded"
    assert fetched.context_metadata["new_value"] == "45"
    assert fetched.timestamp is not None
