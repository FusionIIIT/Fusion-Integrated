from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

NOT_AUTOMATED = {
    "TC-SA-BR-001-01": "the checkout has no basic-user creation interface enforcing Institute ID uniqueness.",
    "TC-SA-BR-001-02": "the checkout has no basic-user update interface to exercise Institute ID immutability.",
    "TC-SA-BR-002-01": "the checkout has no basic-user create/update interface; a standalone email validator would not exercise the specified account operation.",
    "TC-SA-BR-003-01": "the checkout has no Student account record submission interface.",
    "TC-SA-BR-003-02": "the checkout has no Faculty or Staff account record submission interface.",
    "TC-SA-BR-003-03": "the checkout has no common user account record submission interface.",
    "TC-SA-BR-005-02": "restoration services do not accept or enforce an authorization decision that can be omitted in the specified request.",
    "TC-SA-BR-006-01": "the checkout exposes no role assignment service or persistence model.",
    "TC-SA-BR-007-01": "the checkout exposes no role assignment service or persistence model.",
    "TC-SA-BR-008-01": "the checkout exposes no role assignment service or persistence model.",
    "TC-SA-BR-008-02": "the checkout exposes no role assignment service or persistence model.",
    "TC-SA-BR-008-03": "the checkout exposes no role assignment service or persistence model.",
    "TC-SA-BR-009-01": "the checkout exposes no scheduled role activation mechanism.",
    "TC-SA-BR-009-02": "the checkout exposes no scheduled role expiry mechanism.",
    "TC-SA-BR-009-03": "the checkout exposes no role assignment lifecycle to supersede scheduled end dates.",
    "TC-SA-BR-010-01": "the checkout exposes no role eligibility assignment interface.",
    "TC-SA-BR-010-02": "the checkout exposes no role eligibility assignment interface.",
    "TC-SA-BR-011-01": "the checkout exposes no role compatibility assignment interface.",
    "TC-SA-BR-012-01": "the checkout exposes no role reassignment or pending-work handover interface.",
    "TC-SA-BR-012-02": "the checkout exposes no role reassignment interface.",
    "TC-SA-BR-013-01": "the checkout exposes no prior-holder role audit access interface.",
    "TC-SA-BR-014-01": "the checkout exposes no role revocation scheduling interface.",
    "TC-SA-BR-014-02": "the checkout exposes no role revocation interface.",
    "TC-SA-BR-014-03": "the checkout exposes no role revocation interface.",
    "TC-SA-BR-014-04": "the checkout exposes no role revocation or pending-task disposition interface.",
    "TC-SA-BR-015-01": "the checkout exposes no role validity lifecycle or access grants.",
    "TC-SA-BR-015-02": "the checkout exposes no role lifecycle tied to user deactivation.",
    "TC-SA-BR-016-01": "the checkout exposes no role expiry reminder mechanism.",
    "TC-SA-BR-016-02": "the checkout exposes no role extension interface.",
    "TC-SA-BR-016-03": "the checkout exposes no role extension interface.",
    "TC-SA-BR-017-01": "historical archive creation has no retention-age, transaction, archival-marking, or dependency eligibility interface.",
    "TC-SA-BR-017-02": "historical archive creation has no per-record eligibility, dependency, audit-log exclusion interface.",
    "TC-SA-BR-018-01": "historical archive creation accepts backup metadata but offers no observable backup operation ordering relative to data movement.",
    "TC-SA-BR-018-02": "the checkout exposes no backup execution/failure interface to trigger and verify an aborted archive movement.",
    "TC-SA-BR-019-01": "the checkout has no archival data movement or archive database retention sweep interface.",
    "TC-SA-BR-020-01": "the checkout has no archive read/search interface or module-specific operational data to exercise isolation.",
    "TC-SA-BR-023-01": "the checkout has no role assignment notification flow to measure delivery timing.",
    "TC-SA-BR-023-02": "the checkout has no role revocation notification flow to measure delivery timing.",
    "TC-SA-BR-024-01": "the checkout exposes no authentication login failure event stream or threshold alert mechanism.",
    "TC-SA-BR-024-02": "the checkout exposes no authentication login failure event stream or critical-alert channel configuration.",
    "TC-SA-BR-024-03": "the checkout exposes no critical security alert dispatch mechanism or SMS channel configuration.",
    "TC-SA-BR-025-02": "the checkout has no role assignment history model or expiry flow.",
    "TC-SA-BR-026-01": "the checkout has no Super Admin user/role/activity/archive cross-module access interface.",
    "TC-SA-BR-026-02": "the checkout has no views, reports, archival, or handover interfaces exposing the specified module content.",
    "TC-SA-BR-027-01": "authentication and two-factor enforcement belong to the external IAM and are not implemented in this checkout.",
    "TC-SA-BR-027-02": "the checkout has no Super Admin session management interface.",
    "TC-SA-BR-027-03": "the checkout has no Super Admin inactivity timeout or session activity log interface.",
    "TC-SA-BR-027-04": "IP whitelist login enforcement belongs to the external IAM and is not implemented in this checkout.",
    "TC-SA-BR-028-01": "the checkout exposes no in-module Super Admin status assignment or modification interface.",
    "TC-SA-BR-029-01": "the checkout exposes no critical operation confirmation or reauthentication interface.",
    "TC-SA-BR-029-02": "the checkout exposes no critical operation confirmation or reauthentication interface.",
    "TC-SA-BR-031-01": "password rotation policy and authentication belong to the external IAM and are not implemented here.",
    "TC-SA-BR-032-01": "the checkout has no configured notification channel dispatch interface for general supported events.",
    "TC-SA-BR-032-02": "the checkout exposes no critical-alert SMS dispatch or channel configuration interface.",
    "TC-SA-BR-033-01": "the checkout has no backend event interface for all specified user, role, authentication, archival, and configuration event categories.",
    "TC-SA-BR-034-01": "the checkout exposes no active-role selection or permission evaluation interface.",
    "TC-SA-BR-034-02": "the checkout exposes no active-role selection or permission evaluation interface.",
    "TC-SA-BR-034-03": "the checkout exposes no active-role selection or permission evaluation interface.",
    "TC-SA-BR-035-03": "the permitted configuration service validates key membership but does not implement institutional retention value bounds.",
}


def run_br_case(test_id: str, principal, stub_iam) -> None:
    if test_id in NOT_AUTOMATED:
        pytest.skip(f"NOT_AUTOMATED: {NOT_AUTOMATED[test_id]}")

    if test_id == "TC-SA-BR-004-01":
        from modules.superadmin.models.archival import ArchivedUserRecord
        from modules.superadmin.services.archival import archive_user

        record = archive_user(
            principal,
            user_id=910401,
            institute_id="I100",
            username="br004eligible",
            email="br004eligible@iiitdmj.ac.in",
            user_kind="student",
            is_deactivated=True,
            deactivated_at=timezone.now() - timedelta(days=31),
            has_pending_transactions=False,
            archival_reason="BR eligibility case.",
        )
        assert record.status == "reversible"
        assert ArchivedUserRecord.objects.filter(pk=record.pk).exists()
    elif test_id == "TC-SA-BR-004-02":
        from modules.superadmin.models.archival import ArchivedUserRecord
        from modules.superadmin.tests.conftest import _sa_client

        initial_count = ArchivedUserRecord.objects.count()
        response = _sa_client(stub_iam, uid=principal.user_id).post(
            "/api/v1/superadmin/archival/users/",
            {
                "user_id": 910402,
                "institute_id": "I101",
                "username": "br004ineligible",
                "email": "br004ineligible@iiitdmj.ac.in",
                "user_kind": "student",
                "is_deactivated": True,
                "deactivated_at": (timezone.now() - timedelta(days=31)).isoformat(),
                "has_pending_transactions": True,
                "archival_reason": "Pending transaction.",
            },
            format="json",
        )
        assert response.status_code == 422
        assert ArchivedUserRecord.objects.count() == initial_count
        assert not ArchivedUserRecord.objects.filter(user_id=910402).exists()
    elif test_id in {"TC-SA-BR-005-01", "TC-SA-BR-005-03"}:
        from modules.superadmin.models.archival import ArchivedUserRecord
        from modules.superadmin.services.archival import restore_archived_user

        expired = test_id == "TC-SA-BR-005-03"
        now = timezone.now()
        record = ArchivedUserRecord.objects.create(
            user_id=910500 + int(expired),
            institute_id="I105",
            username="br005expired" if expired else "br005valid",
            email="br005@iiitdmj.ac.in",
            user_kind="student",
            status="finalized_permanent" if expired else "reversible",
            archived_at=now - timedelta(days=60 if expired else 5),
            reversible_until=now - timedelta(days=1) if expired else now + timedelta(days=25),
            authorized_by=principal.user_id,
            archival_reason="BR restoration case.",
        )
        if expired:
            from modules.superadmin.tests.conftest import _sa_client

            response = _sa_client(stub_iam, uid=principal.user_id).post(
                f"/api/v1/superadmin/archival/users/{record.user_id}/restore/",
                {"restoration_reason": "Authorized request."},
                format="json",
            )
            assert response.status_code == 409
            record.refresh_from_db()
            assert record.status == "finalized_permanent"
            assert record.restored_at is None
        else:
            restored = restore_archived_user(
                principal, user_id=record.user_id, restoration_reason="Authorized request."
            )
            assert restored.status == "restored"
            assert restored.restored_by == principal.user_id
    elif test_id in {"TC-SA-BR-021-01", "TC-SA-BR-021-02", "TC-SA-BR-022-01", "TC-SA-BR-022-02"}:
        from modules.superadmin.models.archival import HistoricalDataArchive, PurgeRequest
        from modules.superadmin.services.purge import (
            create_purge_request,
            decide_purge_request,
            execute_purge,
        )
        from modules.superadmin.tests.conftest import _sa_client

        retention_active = test_id == "TC-SA-BR-021-01"
        no_approval = test_id == "TC-SA-BR-022-02"
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title=f"BR {test_id}",
            date_range_start=date.today() - timedelta(days=800),
            date_range_end=date.today() - timedelta(days=400),
            record_count=3,
            backup_file_path="/archive/br.tar",
            backup_checksum="sha256-br",
            retention_expires_at=(
                date.today() + timedelta(days=20)
                if retention_active
                else date.today() - timedelta(days=1)
            ),
            archived_by=principal.user_id,
        )
        if retention_active:
            initial_requests = PurgeRequest.objects.count()
            response = _sa_client(stub_iam, uid=principal.user_id).post(
                "/api/v1/superadmin/purge/requests/",
                {"archive_id": archive.pk, "request_reason": "Retention active."},
                format="json",
            )
            assert response.status_code == 422
            archive.refresh_from_db()
            assert PurgeRequest.objects.count() == initial_requests
            assert not archive.is_purged
        else:
            request = create_purge_request(
                principal, archive_id=archive.pk, request_reason="Retention elapsed."
            )
            if no_approval:
                response = _sa_client(stub_iam, uid=principal.user_id).post(
                    f"/api/v1/superadmin/purge/requests/{request.pk}/execute/",
                    {},
                    format="json",
                )
                assert response.status_code == 422
                archive.refresh_from_db()
                assert not archive.is_purged
                assert archive.pk is not None
            else:
                approved = decide_purge_request(
                    _it_head_principal(), request_id=request.pk, approve=True
                )
                assert approved.status == "approved"
                purged = execute_purge(principal, request_id=request.pk)
                archive.refresh_from_db()
                assert purged.status == "purged"
                assert archive.is_purged
    elif test_id == "TC-SA-BR-025-01":
        from modules.superadmin.models.audit import SuperAdminAuditLog

        entry = SuperAdminAuditLog.objects.create(
            actor_id=principal.user_id,
            actor_username=principal.username,
            actor_role="super_admin",
            action="br.audit.immutable",
            target_id="910525",
            target_type="br",
        )
        with pytest.raises(PermissionError):
            entry.delete()
        with pytest.raises(PermissionError):
            SuperAdminAuditLog.objects.filter(pk=entry.pk).delete()
        assert SuperAdminAuditLog.objects.filter(pk=entry.pk).exists()
    elif test_id in {"TC-SA-BR-030-01", "TC-SA-BR-030-02"}:
        from modules.superadmin.domain.exceptions import BulkLimitExceededError
        from modules.superadmin.domain.validators import validate_bulk_size

        if test_id == "TC-SA-BR-030-01":
            validate_bulk_size(1000, max_limit=1000)
        else:
            with pytest.raises(BulkLimitExceededError):
                validate_bulk_size(1001, max_limit=1000)
    elif test_id == "TC-SA-BR-035-01":
        from modules.superadmin.domain.constants import (
            CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS,
            PERMITTED_CONFIG_KEYS,
        )
        from modules.superadmin.services.config import supersede_policy_param

        assert CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS in PERMITTED_CONFIG_KEYS
        setting = supersede_policy_param(
            principal, key=CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS, value="30"
        )
        assert setting.key == CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS
        assert setting.value == "30"
    elif test_id == "TC-SA-BR-035-02":
        from modules.superadmin.domain.constants import PERMITTED_CONFIG_KEYS
        from modules.superadmin.models.config import SystemPolicyParameter
        from modules.superadmin.tests.conftest import _sa_client

        initial_count = SystemPolicyParameter.objects.count()
        response = _sa_client(stub_iam, uid=principal.user_id).post(
            "/api/v1/superadmin/policy/parameters/",
            {"key": "placement.academic_calendar", "value": "changed"},
            format="json",
        )
        assert response.status_code == 422
        assert SystemPolicyParameter.objects.count() == initial_count
        assert "placement.academic_calendar" not in PERMITTED_CONFIG_KEYS
    else:
        raise AssertionError(f"No implementation or skip reason declared for {test_id}.")


def _it_head_principal():
    from conftest import make_principal
    from modules.superadmin.tests.conftest import IT_PERMS

    return make_principal(
        user_id=200,
        kind="staff",
        roles=("it_head",),
        active_role="it_head",
        permissions=IT_PERMS,
        modules=("superadmin",),
    )
