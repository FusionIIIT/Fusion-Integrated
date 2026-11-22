from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

def run_br_case(test_id: str, principal, stub_iam) -> None:
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
                assert response.status_code == 409
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
