"""Adversarial tests: tamper attempts, malicious requests, and regression defense."""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.superadmin.domain.exceptions import (
    ImmutableRecordError,
    InvalidStateTransitionError,
    ReversibilityExpiredError,
)
from modules.superadmin.models import AuditLogRecord, UserAccountRecord
from modules.superadmin.services.user_archive import restore_archived_user

pytestmark = pytest.mark.django_db


def test_def_sa_01_regression_status_committed_before_raise_on_expired_window():
    """DEF-SA-01: When restoration is attempted on an expired reversibility window,
    the user must transition to ARCHIVED_PERMANENT and that transition MUST be committed
    to the database even though a refusal/ConflictError is raised to the caller.
    """
    now = timezone.now()
    user = UserAccountRecord.objects.create(
        user_id=9101,
        institute_id="24BCS9101",
        email="u9101@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=95),
        reversibility_expires_at=now - timedelta(days=5),  # EXPIRED
    )

    with pytest.raises((ConflictError, ReversibilityExpiredError)):
        restore_archived_user(actor_user_id=1, user_id=9101, reason="Late restoration attempt")

    # The user status MUST be ARCHIVED_PERMANENT in the database (not rolled back to ARCHIVED_REVERSIBLE)
    user.refresh_from_db()
    assert user.activation_status == "ARCHIVED_PERMANENT"


def test_cannot_restore_permanently_archived_user():
    user = UserAccountRecord.objects.create(
        user_id=9102,
        institute_id="24BCS9102",
        email="u9102@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_PERMANENT",
    )

    with pytest.raises((ConflictError, InvalidStateTransitionError)):
        restore_archived_user(actor_user_id=1, user_id=9102, reason="Attempt restore")

    user.refresh_from_db()
    assert user.activation_status == "ARCHIVED_PERMANENT"


def test_duplicate_institute_id_rejected_by_db():
    UserAccountRecord.objects.create(
        user_id=9103,
        institute_id="UNIQUE_INST_01",
        email="inst01@iiitdmj.ac.in",
        user_type="STUDENT",
    )

    with pytest.raises(IntegrityError):
        UserAccountRecord.objects.create(
            user_id=9104,
            institute_id="UNIQUE_INST_01",  # duplicate
            email="inst02@iiitdmj.ac.in",
            user_type="STUDENT",
        )


def test_direct_audit_log_deletion_blocked():
    log = AuditLogRecord.objects.create(
        event_type="SYS_CONFIG",
        actor_user_id=1,
        target_entity="SYS",
        target_id="0",
        action_details={},
    )

    with pytest.raises(ImmutableRecordError):
        log.delete()
