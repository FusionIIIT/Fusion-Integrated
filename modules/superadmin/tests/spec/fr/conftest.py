from __future__ import annotations

import pytest


def run_case(test_id, sa_principal, it_principal, stub_iam):
    if test_id not in IMPLEMENTED:
        raise AssertionError(f"Unimplemented FR test case: {test_id}")
    from datetime import date, timedelta

    from django.utils import timezone
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.superadmin.domain.constants import PERMITTED_CONFIG_KEYS
    from modules.superadmin.models.archival import (
        ArchivedUserRecord,
        HistoricalDataArchive,
        PurgeRequest,
    )
    from modules.superadmin.models.audit import SuperAdminAuditLog
    from modules.superadmin.models.config import SystemPolicyParameter
    from modules.superadmin.tests.conftest import SA_PERMS

    if test_id == "TC-056":
        from modules.superadmin.services.archival import archive_user

        rec = archive_user(
            sa_principal,
            user_id=120056,
            institute_id="2021BCS056",
            username="fr056",
            email="fr056@iiitdmj.ac.in",
            user_kind="student",
            is_deactivated=True,
            deactivated_at=timezone.now() - timedelta(days=45),
            has_pending_transactions=False,
            archival_reason="Graduated.",
        )
        assert rec.user_id == 120056 and rec.status == "reversible"
    elif test_id == "TC-057":
        stub_iam(
            make_session(
                user_id=sa_principal.user_id,
                kind="staff",
                roles=("super_admin",),
                active_role="super_admin",
                permissions=SA_PERMS,
                modules=("superadmin",),
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        count = ArchivedUserRecord.objects.count()
        response = client.post(
            "/api/v1/superadmin/archival/users/",
            {
                "user_id": 120057,
                "institute_id": "2021BCS057",
                "username": "fr057",
                "email": "fr057@iiitdmj.ac.in",
                "user_kind": "student",
                "is_deactivated": False,
                "has_pending_transactions": False,
                "archival_reason": "Active account.",
            },
            format="json",
        )
        assert response.status_code == 422 and ArchivedUserRecord.objects.count() == count
    elif test_id in {"TC-059", "TC-079", "TC-083"}:
        from modules.superadmin.services.audit import record_audit_event

        stub_iam(
            make_session(
                user_id=sa_principal.user_id,
                kind="staff",
                roles=("super_admin",),
                active_role="super_admin",
                permissions=SA_PERMS,
                modules=("superadmin",),
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        if test_id == "TC-059":
            ArchivedUserRecord.objects.create(
                user_id=120059,
                institute_id="2021BCS059",
                username="fr059",
                email="fr059@iiitdmj.ac.in",
                user_kind="student",
                status="reversible",
                archived_at=timezone.now(),
                reversible_until=timezone.now() + timedelta(days=30),
                authorized_by=sa_principal.user_id,
                archival_reason="Graduated.",
            )
            r = client.get("/api/v1/superadmin/archival/users/")
            assert r.status_code == 200 and any(x["user_id"] == 120059 for x in r.json()["results"])
        elif test_id == "TC-079":
            record_audit_event(
                actor_id=sa_principal.user_id,
                actor_username=sa_principal.username,
                actor_role="super_admin",
                action="fr.audit.visible",
                target_id="120079",
                target_type="fr",
            )
            record_audit_event(
                actor_id=sa_principal.user_id,
                actor_username=sa_principal.username,
                actor_role="super_admin",
                action="fr.audit.hidden",
                target_id="120079",
                target_type="fr",
            )
            r = client.get("/api/v1/superadmin/audit/logs/", {"action": "fr.audit.visible"})
            assert (
                r.status_code == 200
                and any(x["target_id"] == "120079" for x in r.json()["results"])
                and all(x["action"] == "fr.audit.visible" for x in r.json()["results"])
            )
        else:
            r = client.get("/api/v1/superadmin/dashboard/")
            assert (
                r.status_code == 200
                and {
                    "archived_users_reversible",
                    "archived_users_total",
                    "purge_requests_pending",
                    "audit_logs_total",
                }
                <= r.json().keys()
            )
    elif test_id == "TC-061":
        from modules.superadmin.services.archival import restore_archived_user

        ArchivedUserRecord.objects.create(
            user_id=120061,
            institute_id="2021BCS061",
            username="fr061",
            email="fr061@iiitdmj.ac.in",
            user_kind="student",
            status="reversible",
            archived_at=timezone.now(),
            reversible_until=timezone.now() + timedelta(days=30),
            authorized_by=sa_principal.user_id,
            archival_reason="Archived.",
        )
        rec = restore_archived_user(sa_principal, user_id=120061, restoration_reason="Rejoining.")
        assert rec.status == "restored" and rec.restored_by == sa_principal.user_id
    elif test_id == "TC-062":
        rec = ArchivedUserRecord.objects.create(
            user_id=120062,
            institute_id="2021BCS062",
            username="fr062",
            email="fr062@iiitdmj.ac.in",
            user_kind="student",
            status="finalized_permanent",
            archived_at=timezone.now() - timedelta(days=60),
            reversible_until=timezone.now() - timedelta(days=30),
            authorized_by=sa_principal.user_id,
            archival_reason="Expired.",
        )
        stub_iam(
            make_session(
                user_id=sa_principal.user_id,
                kind="staff",
                roles=("super_admin",),
                active_role="super_admin",
                permissions=SA_PERMS,
                modules=("superadmin",),
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        response = client.post(
            "/api/v1/superadmin/archival/users/120062/restore/",
            {"restoration_reason": "Late request."},
            format="json",
        )
        assert response.status_code == 409
        rec.refresh_from_db()
        assert rec.status == "finalized_permanent" and rec.restored_at is None
    elif test_id in {"TC-063", "TC-070"}:
        from modules.superadmin.services.historical_archive import (
            create_historical_archive,
            restore_historical_archive,
        )

        today = date.today()
        args = {
            "dataset_category": "examination",
            "title": "FR historical dataset",
            "date_range_start": today - timedelta(days=400),
            "date_range_end": today - timedelta(days=300),
            "record_count": 12,
            "backup_file_path": "/archive/fr.tar",
            "backup_checksum": "sha256-fr",
            "retention_expires_at": today + timedelta(days=365),
        }
        archive = create_historical_archive(sa_principal, **args)
        if test_id == "TC-063":
            assert archive.pk and archive.date_range_start == args["date_range_start"]
        else:
            restored = restore_historical_archive(sa_principal, archive_id=archive.pk)
            assert restored.is_restored and restored.restored_at is not None
    elif test_id in {"TC-075", "TC-076"}:
        from modules.superadmin.services.purge import (
            create_purge_request,
            decide_purge_request,
            execute_purge,
        )

        today = date.today()
        expired = test_id == "TC-076"
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title="FR purge archive",
            date_range_start=today - timedelta(days=800),
            date_range_end=today - timedelta(days=400),
            record_count=5,
            backup_file_path="/archive/fr.tar",
            backup_checksum="sha256-fr",
            retention_expires_at=today - timedelta(days=1)
            if expired
            else today + timedelta(days=1),
            archived_by=sa_principal.user_id,
        )
        count = PurgeRequest.objects.count()
        if not expired:
            stub_iam(
                make_session(
                    user_id=sa_principal.user_id,
                    kind="staff",
                    roles=("super_admin",),
                    active_role="super_admin",
                    permissions=SA_PERMS,
                    modules=("superadmin",),
                )
            )
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION="Token abc")
            response = client.post(
                "/api/v1/superadmin/purge/requests/",
                {"archive_id": archive.pk, "request_reason": "Retention active."},
                format="json",
            )
            archive.refresh_from_db()
            assert (
                response.status_code == 422
                and PurgeRequest.objects.count() == count
                and not archive.is_purged
            )
        else:
            req = create_purge_request(
                sa_principal, archive_id=archive.pk, request_reason="Retention elapsed."
            )
            approved = decide_purge_request(it_principal, request_id=req.pk, approve=True)
            assert approved.status == "approved" and approved.it_head_id == it_principal.user_id
            done = execute_purge(sa_principal, request_id=req.pk)
            archive.refresh_from_db()
            assert done.status == "purged" and archive.is_purged
    elif test_id == "TC-097":
        from modules.superadmin.domain.exceptions import SelfModificationForbiddenError
        from modules.superadmin.domain.validators import validate_no_self_modification

        with pytest.raises(SelfModificationForbiddenError):
            validate_no_self_modification(sa_principal.user_id, sa_principal.user_id)
    elif test_id in {"TC-098", "TC-099"}:
        from modules.superadmin.services.config import supersede_policy_param

        if test_id == "TC-098":
            for key in PERMITTED_CONFIG_KEYS:
                assert supersede_policy_param(sa_principal, key=key, value="test-value").key == key
            assert SystemPolicyParameter.objects.count() == len(PERMITTED_CONFIG_KEYS)
        else:
            stub_iam(
                make_session(
                    user_id=sa_principal.user_id,
                    kind="staff",
                    roles=("super_admin",),
                    active_role="super_admin",
                    permissions=SA_PERMS,
                    modules=("superadmin",),
                )
            )
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION="Token abc")
            count = SystemPolicyParameter.objects.count()
            response = client.post(
                "/api/v1/superadmin/policies/",
                {"key": "placement.academic_calendar", "value": "changed"},
                format="json",
            )
            assert (
                response.status_code == 422
                and SystemPolicyParameter.objects.count() == count
                and "placement.academic_calendar" not in PERMITTED_CONFIG_KEYS
            )
    elif test_id == "TC-100":
        from modules.superadmin.domain.exceptions import BulkLimitExceededError
        from modules.superadmin.domain.validators import validate_bulk_size

        with pytest.raises(BulkLimitExceededError):
            validate_bulk_size(1001, max_limit=1000)
    elif test_id == "TC-105":
        entry = SuperAdminAuditLog.objects.create(
            actor_id=sa_principal.user_id,
            actor_username=sa_principal.username,
            actor_role="super_admin",
            action="fr.audit.immutable",
            target_id="120105",
            target_type="fr",
        )
        with pytest.raises(PermissionError):
            entry.delete()
        with pytest.raises(PermissionError):
            SuperAdminAuditLog.objects.filter(pk=entry.pk).delete()
        assert SuperAdminAuditLog.objects.filter(pk=entry.pk).exists()


IMPLEMENTED = frozenset(
    {
        "TC-057",
        "TC-059",
        "TC-061",
        "TC-062",
        "TC-063",
        "TC-070",
        "TC-075",
        "TC-076",
        "TC-079",
        "TC-083",
        "TC-097",
        "TC-099",
        "TC-100",
        "TC-105",
    }
)
