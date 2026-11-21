"""Archival service: archive, restore, and sweep — happy paths and guards."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    ARCHIVAL_STATUS_RESTORED,
    ARCHIVAL_STATUS_REVERSIBLE,
    CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
)
from modules.superadmin.models.archival import ArchivedUserRecord
from modules.superadmin.models.config import SystemPolicyParameter
from modules.superadmin.services.archival import (
    archive_user,
    expire_reversibility_sweep,
    restore_archived_user,
)

pytestmark = pytest.mark.django_db

UID = 42
INST = "2021BCS042"
EMAIL = "u42@iiitdmj.ac.in"


def _base_kwargs():
    return {
        "user_id": UID,
        "institute_id": INST,
        "username": "u42",
        "email": EMAIL,
        "user_kind": "student",
        "is_deactivated": True,
        "deactivated_at": timezone.now() - timedelta(days=60),
        "has_pending_transactions": False,
        "archival_reason": "Graduated, no pending dues.",
    }


# -- archive_user ----------------------------------------------------------


def test_archive_user_creates_a_reversible_record(sa_principal):
    record = archive_user(sa_principal, **_base_kwargs())

    assert record.status == ARCHIVAL_STATUS_REVERSIBLE
    assert record.user_id == UID
    assert record.reversible_until > record.archived_at


def test_archive_user_requires_deactivation(sa_principal):
    kwargs = _base_kwargs()
    kwargs["is_deactivated"] = False
    kwargs["deactivated_at"] = None

    with pytest.raises(DomainError):
        archive_user(sa_principal, **kwargs)


def test_archive_user_requires_min_deactivation_period(sa_principal):
    kwargs = _base_kwargs()
    kwargs["deactivated_at"] = timezone.now() - timedelta(days=5)

    with pytest.raises(DomainError):
        archive_user(sa_principal, **kwargs)


def test_archive_user_rejects_pending_transactions(sa_principal):
    kwargs = _base_kwargs()
    kwargs["has_pending_transactions"] = True

    with pytest.raises(DomainError):
        archive_user(sa_principal, **kwargs)


def test_archive_user_conflicts_if_already_archived(sa_principal):
    archive_user(sa_principal, **_base_kwargs())

    with pytest.raises(ConflictError, match="already archived"):
        archive_user(sa_principal, **_base_kwargs())


def test_archive_user_rejects_invalid_institute_email(sa_principal):
    kwargs = _base_kwargs()
    kwargs["email"] = "not-an-iiitdmj-address@gmail.com"

    with pytest.raises(DomainError):
        archive_user(sa_principal, **kwargs)


# -- restore_archived_user -------------------------------------------------


def test_restore_within_window_succeeds(sa_principal):
    archive_user(sa_principal, **_base_kwargs())

    record = restore_archived_user(
        sa_principal, user_id=UID, restoration_reason="Rejoining programme."
    )

    assert record.status == ARCHIVAL_STATUS_RESTORED
    assert record.restored_at is not None
    assert record.restored_by == sa_principal.user_id


def test_restore_after_window_expires_raises(sa_principal):
    record = ArchivedUserRecord.objects.create(
        user_id=UID + 1,
        institute_id=INST,
        username="u43",
        email=EMAIL,
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=60),
        reversible_until=timezone.now() - timedelta(days=1),
        authorized_by=sa_principal.user_id,
        archival_reason="Graduated.",
    )

    with pytest.raises(ConflictError, match=r"reversibility period expired|reversibility_expired"):
        restore_archived_user(
            sa_principal, user_id=record.user_id, restoration_reason="Late request."
        )


# -- expire_reversibility_sweep --------------------------------------------


def test_sweep_finalizes_expired_reversible_records(sa_principal):
    # One record past its window
    ArchivedUserRecord.objects.create(
        user_id=200,
        institute_id="2020BCS200",
        username="u200",
        email="u200@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=90),
        reversible_until=timezone.now() - timedelta(days=10),
        authorized_by=1,
        archival_reason="Old graduate.",
    )
    # One still within window (must NOT be swept)
    ArchivedUserRecord.objects.create(
        user_id=201,
        institute_id="2021BCS201",
        username="u201",
        email="u201@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=1,
        archival_reason="Recent archival.",
    )

    count = expire_reversibility_sweep()

    assert count == 1
    assert ArchivedUserRecord.objects.get(user_id=200).status == ARCHIVAL_STATUS_FINALIZED_PERMANENT
    assert ArchivedUserRecord.objects.get(user_id=201).status == ARCHIVAL_STATUS_REVERSIBLE


def test_sweep_with_no_expired_records_returns_zero():
    count = expire_reversibility_sweep()
    assert count == 0


def test_sweep_uses_policy_window_when_seeded(sa_principal):
    # Seed a 7-day policy window (custom)
    SystemPolicyParameter.objects.create(
        key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
        value="7",
        version=1,
        effective_from=timezone.now() - timedelta(days=1),
        effective_to=None,
        description="Test short window.",
        updated_by=1,
    )
    # This user was archived 10 days ago with reversible_until 7 days ago — expired
    ArchivedUserRecord.objects.create(
        user_id=300,
        institute_id="2020BCS300",
        username="u300",
        email="u300@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=10),
        reversible_until=timezone.now() - timedelta(days=3),
        authorized_by=1,
        archival_reason="Old.",
    )

    count = expire_reversibility_sweep()

    assert count == 1
