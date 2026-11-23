"""Concurrency tests for dual-auth purge decisions and archival state transitions."""

from __future__ import annotations

import threading
from datetime import date, timedelta

import pytest
from django.db import connection
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, DomainError
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_PENDING_IT_HEAD,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.superadmin.services.archival import restore_archived_user
from modules.superadmin.services.purge import decide_purge_request
from modules.superadmin.tests.conftest import IT_PERMS, SA_PERMS


@pytest.mark.django_db(transaction=True)
def test_concurrency_dual_auth_purge_decision_racing():
    # BR-SA-022, UC-SA-023: Two IT Heads racing to approve the same pending purge request.
    # Exactly one must succeed in transitioning to approved; the second must be rejected with ConflictError/DomainError.
    today = date.today()
    archive = HistoricalDataArchive.objects.create(
        dataset_category="placement",
        title="Concurrent Purge Test",
        date_range_start=today - timedelta(days=900),
        date_range_end=today - timedelta(days=500),
        record_count=100,
        backup_file_path="/backups/c_purge.tar.gz",
        backup_checksum="chksum_concurrent",
        retention_expires_at=today - timedelta(days=10),
        archived_by=1,
    )
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=100,
        request_reason="Racing decision test.",
    )

    barrier = threading.Barrier(2, timeout=10)
    results = []
    failures = []

    def attempt_decision(it_uid: int):
        principal = make_principal(
            user_id=it_uid,
            kind="staff",
            roles=("it_head",),
            active_role="it_head",
            permissions=IT_PERMS,
            modules=("superadmin",),
        )
        try:
            barrier.wait()
            res = decide_purge_request(
                principal, request_id=req.pk, approve=True, comments=f"Approved by {it_uid}"
            )
            results.append(res.status)
        except (ConflictError, DomainError) as exc:
            failures.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=attempt_decision, args=(201,))
    t2 = threading.Thread(target=attempt_decision, args=(202,))

    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    req.refresh_from_db()
    assert req.status == "approved"
    assert len(results) == 1
    assert len(failures) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrency_restore_archived_user_racing():
    # BR-SA-005, UC-SA-018: Two Super Admins racing to restore the same archived user.
    # Exactly one restoration must succeed; the second must raise ConflictError/DomainError.
    user_record = ArchivedUserRecord.objects.create(
        user_id=7701,
        institute_id="2020BCS701",
        username="u7701",
        email="u7701@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=1,
        archival_reason="Graduated.",
    )

    barrier = threading.Barrier(2, timeout=10)
    results = []
    failures = []

    def attempt_restore(sa_uid: int):
        principal = make_principal(
            user_id=sa_uid,
            kind="staff",
            roles=("super_admin",),
            active_role="super_admin",
            permissions=SA_PERMS,
            modules=("superadmin",),
        )
        try:
            barrier.wait()
            res = restore_archived_user(
                principal, user_id=user_record.user_id, restoration_reason="Concurrent test"
            )
            results.append(res.status)
        except (ConflictError, DomainError) as exc:
            failures.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=attempt_restore, args=(101,))
    t2 = threading.Thread(target=attempt_restore, args=(102,))

    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    user_record.refresh_from_db()
    assert user_record.status == "restored"
    assert len(results) == 1
    assert len(failures) == 1
