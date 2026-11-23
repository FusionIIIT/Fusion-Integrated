"""Dual-authorization purge: self-approval blocked at domain and DB level."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.superadmin.domain.constants import (
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_EXPIRED,
    PURGE_STATUS_PENDING_IT_HEAD,
    PURGE_STATUS_PURGED,
    PURGE_STATUS_REJECTED,
)
from modules.superadmin.models.archival import HistoricalDataArchive, PurgeRequest
from modules.superadmin.services.purge import (
    create_purge_request,
    decide_purge_request,
    execute_purge,
    expire_purge_requests_sweep,
)

pytestmark = pytest.mark.django_db


def _archive(offset_days=400, is_purged=False):
    # Retention expired archive — eligible for purge
    today = date.today()
    return HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Batch 2019 Final Transcripts",
        date_range_start=today - timedelta(days=offset_days + 365),
        date_range_end=today - timedelta(days=offset_days),
        record_count=250,
        backup_file_path="/backups/2019.tar.gz",
        backup_checksum="abc123",
        retention_expires_at=today - timedelta(days=10),
        is_purged=is_purged,
        archived_by=1,
    )


# -- create_purge_request --------------------------------------------------


def test_create_purge_request_succeeds_for_eligible_archive(sa_principal):
    archive = _archive()
    req = create_purge_request(
        sa_principal,
        archive_id=archive.pk,
        request_reason="Retention period fully elapsed.",
    )

    assert req.status == PURGE_STATUS_PENDING_IT_HEAD
    assert req.requested_by == sa_principal.user_id


def test_create_purge_request_blocked_before_retention_elapses(sa_principal):
    # Archive whose retention has NOT elapsed
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Current Batch",
        date_range_start=today - timedelta(days=100),
        date_range_end=today - timedelta(days=10),
        record_count=10,
        backup_file_path="/backups/current.tar.gz",
        backup_checksum="xyz789",
        retention_expires_at=today + timedelta(days=365),
        archived_by=1,
    )

    with pytest.raises(DomainError):
        create_purge_request(
            sa_principal,
            archive_id=archive.pk,
            request_reason="Attempting early purge.",
        )


def test_duplicate_pending_purge_raises_conflict(sa_principal):
    archive = _archive()
    create_purge_request(sa_principal, archive_id=archive.pk, request_reason="First.")

    with pytest.raises(ConflictError):
        create_purge_request(sa_principal, archive_id=archive.pk, request_reason="Duplicate.")


# -- decide_purge_request: self-approval -----------------------------------


def test_it_head_cannot_approve_their_own_purge_request(it_principal, sa_principal):
    # IT Head creates a request (they are both initiator and approver — blocked)
    archive = _archive()
    # Make the request come from the IT Head's uid
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=it_principal.user_id,
        request_reason="IT Head self-initiated request.",
    )

    with pytest.raises(ConflictError, match=r"self_approval_forbidden|independent IT Head"):
        decide_purge_request(it_principal, request_id=req.pk, approve=True)


def test_sa_cannot_approve_purge_as_it_head(sa_principal):
    # Super admin does not hold purge.change — cannot approve
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=99,
        request_reason="Need approval.",
    )
    # Transition requires it_head role; sa_principal has wrong role for approval
    with pytest.raises((DomainError, ConflictError)):
        decide_purge_request(sa_principal, request_id=req.pk, approve=True)


# -- decide and execute full happy path ------------------------------------


def test_it_head_approves_then_sa_executes_purge(sa_principal, it_principal):
    archive = _archive()
    req = create_purge_request(
        sa_principal, archive_id=archive.pk, request_reason="Retention lapsed."
    )

    approved = decide_purge_request(it_principal, request_id=req.pk, approve=True)
    assert approved.status == PURGE_STATUS_APPROVED

    executed = execute_purge(sa_principal, request_id=approved.pk)
    assert executed.status == PURGE_STATUS_PURGED

    archive.refresh_from_db()
    assert archive.is_purged is True


def test_it_head_can_reject_purge_request(sa_principal, it_principal):
    archive = _archive()
    req = create_purge_request(
        sa_principal, archive_id=archive.pk, request_reason="Retention lapsed."
    )

    rejected = decide_purge_request(
        it_principal, request_id=req.pk, approve=False, comments="Requires further review."
    )
    assert rejected.status == PURGE_STATUS_REJECTED


# -- DB-level constraint: distinct actors ----------------------------------


def test_db_constraint_blocks_same_actor_as_requester_and_approver(sa_principal):
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=sa_principal.user_id,
        request_reason="Test constraint.",
    )
    with pytest.raises(IntegrityError):
        req.it_head_id = sa_principal.user_id
        req.save(update_fields=["it_head_id"])


# -- expire_purge_requests_sweep -------------------------------------------


def test_sweep_expires_stale_pending_requests(sa_principal):
    archive = _archive()
    # Stale request (created 100 hours ago, TTL is 72h)
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=sa_principal.user_id,
        request_reason="Old request.",
    )
    # Backdate the requested_at
    PurgeRequest.objects.filter(pk=req.pk).update(
        requested_at=timezone.now() - timedelta(hours=100)
    )

    count = expire_purge_requests_sweep()

    assert count == 1
    req.refresh_from_db()
    assert req.status == PURGE_STATUS_EXPIRED


def test_sweep_does_not_expire_fresh_requests(sa_principal):
    archive = _archive()
    PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=sa_principal.user_id,
        request_reason="Fresh request.",
    )

    count = expire_purge_requests_sweep()

    assert count == 0
