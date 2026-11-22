"""Backend implementations for the frozen UC design cases."""

from datetime import date, timedelta

import pytest
from django.utils import timezone


def run_case(test_id, sa_principal, it_principal, stub_iam):
    """Execute a case where this frozen checkout exposes the specified behavior."""
    from modules.superadmin.models.archival import (
        ArchivedUserRecord,
        HistoricalDataArchive,
        PurgeRequest,
    )
    from modules.superadmin.models.audit import SuperAdminAuditLog
    from modules.superadmin.models.config import SystemPolicyParameter

    def superadmin_client():
        from rest_framework.test import APIClient

        from conftest import make_session
        from modules.superadmin.tests.conftest import SA_PERMS

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
        client.credentials(HTTP_AUTHORIZATION="Token uc-spec")
        return client

    def ithead_client():
        from rest_framework.test import APIClient

        from conftest import make_session
        from modules.superadmin.tests.conftest import IT_PERMS

        stub_iam(
            make_session(
                user_id=it_principal.user_id,
                kind="staff",
                roles=("it_head",),
                active_role="it_head",
                permissions=IT_PERMS,
                modules=("superadmin",),
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token uc-spec")
        return client

    if test_id == "TC-052":
        from modules.superadmin.services.archival import archive_user

        now = timezone.now()
        record = archive_user(
            sa_principal,
            user_id=230052,
            institute_id="2026BCS052",
            username="uc052",
            email="uc052@iiitdmj.ac.in",
            user_kind="student",
            is_deactivated=True,
            deactivated_at=now - timedelta(days=45),
            has_pending_transactions=False,
            archival_reason="Completed studies.",
        )
        assert record.status == "reversible"
        assert SuperAdminAuditLog.objects.filter(
            target_id="230052", action="archival.user.created"
        ).exists()
        from modules.superadmin.models.notifications import NotificationOutbox

        assert NotificationOutbox.objects.filter(recipient_id=230052).exists()
    elif test_id == "TC-054":
        before = ArchivedUserRecord.objects.count()
        response = superadmin_client().post(
            "/api/v1/superadmin/archival/users/",
            {
                "user_id": 230054,
                "institute_id": "2026BCS054",
                "username": "uc054",
                "email": "uc054@iiitdmj.ac.in",
                "user_kind": "student",
                "is_deactivated": False,
                "deactivated_at": None,
                "has_pending_transactions": False,
                "archival_reason": "Not eligible.",
            },
            format="json",
        )
        assert response.status_code == 422
        assert ArchivedUserRecord.objects.count() == before
    elif test_id == "TC-056":
        from modules.superadmin.services.historical_archive import create_historical_archive

        today = date.today()
        archive = create_historical_archive(
            sa_principal,
            dataset_category="examination",
            title="UC historical archive",
            date_range_start=today - timedelta(days=400),
            date_range_end=today - timedelta(days=300),
            record_count=12,
            backup_file_path="/archive/uc.tar",
            backup_checksum="sha256-uc-056",
            retention_expires_at=today + timedelta(days=365),
        )
        assert archive.pk and archive.backup_checksum == "sha256-uc-056"
        assert SuperAdminAuditLog.objects.filter(target_id=str(archive.pk)).exists()
    elif test_id in {"TC-060", "TC-061"}:
        client = superadmin_client()
        if test_id == "TC-060":
            ArchivedUserRecord.objects.create(
                user_id=230060,
                institute_id="2026BCS060",
                username="uc060",
                email="uc060@iiitdmj.ac.in",
                user_kind="student",
                status="reversible",
                archived_at=timezone.now(),
                reversible_until=timezone.now() + timedelta(days=30),
                authorized_by=sa_principal.user_id,
                archival_reason="Archived for lookup.",
            )
            response = client.get(
                "/api/v1/superadmin/archival/users/", {"search": "uc060"}
            )
            assert response.status_code == 200
            assert any(item["user_id"] == 230060 for item in response.json()["results"])
        else:
            response = client.get(
                "/api/v1/superadmin/archival/users/", {"search": "no-such-uc-user"}
            )
            assert response.status_code == 200 and response.json()["results"] == []
    elif test_id == "TC-063":
        from modules.superadmin.services.archival import restore_archived_user

        ArchivedUserRecord.objects.create(
            user_id=230063,
            institute_id="2026BCS063",
            username="uc063",
            email="uc063@iiitdmj.ac.in",
            user_kind="student",
            status="reversible",
            archived_at=timezone.now(),
            reversible_until=timezone.now() + timedelta(days=30),
            authorized_by=sa_principal.user_id,
            archival_reason="Archived.",
        )
        record = restore_archived_user(
            sa_principal, user_id=230063, restoration_reason="Eligible restoration."
        )
        assert record.status == "restored" and record.restored_by == sa_principal.user_id
    elif test_id == "TC-066":
        record = ArchivedUserRecord.objects.create(
            user_id=230066,
            institute_id="2026BCS066",
            username="uc066",
            email="uc066@iiitdmj.ac.in",
            user_kind="student",
            status="reversible",
            archived_at=timezone.now() - timedelta(days=60),
            reversible_until=timezone.now() - timedelta(days=1),
            authorized_by=sa_principal.user_id,
            archival_reason="Archived.",
        )
        before = ArchivedUserRecord.objects.count()
        response = superadmin_client().post(
            f"/api/v1/superadmin/archival/users/{record.user_id}/restore/",
            {"restoration_reason": "Too late."},
            format="json",
        )
        assert response.status_code == 409
        record.refresh_from_db()
        assert record.status == "reversible" and record.restored_at is None
        assert ArchivedUserRecord.objects.count() == before
    elif test_id == "TC-078":
        today = date.today()
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title="UC retained archive",
            date_range_start=today - timedelta(days=100),
            date_range_end=today - timedelta(days=10),
            record_count=5,
            backup_file_path="/archive/uc-retained.tar",
            backup_checksum="sha256-uc-078",
            retention_expires_at=today + timedelta(days=30),
            archived_by=sa_principal.user_id,
        )
        before = PurgeRequest.objects.count()
        response = superadmin_client().post(
            "/api/v1/superadmin/purge/requests/",
            {"archive_id": archive.pk, "request_reason": "Too early."},
            format="json",
        )
        assert response.status_code == 422
        archive.refresh_from_db()
        assert PurgeRequest.objects.count() == before and not archive.is_purged
    elif test_id == "TC-067":
        from modules.superadmin.services.historical_archive import (
            create_historical_archive,
            restore_historical_archive,
        )

        today = date.today()
        archive = create_historical_archive(
            sa_principal,
            dataset_category="examination",
            title="UC restore archive",
            date_range_start=today - timedelta(days=400),
            date_range_end=today - timedelta(days=300),
            record_count=5,
            backup_file_path="/archive/uc-restore.tar",
            backup_checksum="sha256-uc-067",
            retention_expires_at=today + timedelta(days=10),
        )
        restored = restore_historical_archive(sa_principal, archive_id=archive.pk)
        assert restored.is_restored and restored.restored_at is not None
    elif test_id == "TC-076":
        from modules.superadmin.services.purge import create_purge_request

        today = date.today()
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title="UC purge request",
            date_range_start=today - timedelta(days=800),
            date_range_end=today - timedelta(days=400),
            record_count=5,
            backup_file_path="/archive/uc-purge.tar",
            backup_checksum="sha256-uc-076",
            retention_expires_at=today - timedelta(days=1),
            archived_by=sa_principal.user_id,
        )
        request = create_purge_request(
            sa_principal, archive_id=archive.pk, request_reason="Retention elapsed."
        )
        assert request.status == "pending_it_head"
        assert request.requested_by == sa_principal.user_id and not archive.is_purged
    elif test_id == "TC-079":
        from modules.superadmin.services.purge import create_purge_request, decide_purge_request

        today = date.today()
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title="UC authorizable archive",
            date_range_start=today - timedelta(days=800),
            date_range_end=today - timedelta(days=400),
            record_count=5,
            backup_file_path="/archive/uc-auth.tar",
            backup_checksum="sha256-uc-079",
            retention_expires_at=today - timedelta(days=1),
            archived_by=sa_principal.user_id,
        )
        request = create_purge_request(
            sa_principal, archive_id=archive.pk, request_reason="Retention elapsed."
        )
        decided = decide_purge_request(
            it_principal, request_id=request.pk, approve=True, comments="Approved."
        )
        assert decided.status == "approved" and decided.it_head_id == it_principal.user_id
    elif test_id == "TC-081":
        from modules.superadmin.services.purge import create_purge_request, decide_purge_request

        today = date.today()
        archive = HistoricalDataArchive.objects.create(
            dataset_category="examination",
            title="UC decided archive",
            date_range_start=today - timedelta(days=800),
            date_range_end=today - timedelta(days=400),
            record_count=5,
            backup_file_path="/archive/uc-decided.tar",
            backup_checksum="sha256-uc-081",
            retention_expires_at=today - timedelta(days=1),
            archived_by=sa_principal.user_id,
        )
        request = create_purge_request(
            sa_principal, archive_id=archive.pk, request_reason="Retention elapsed."
        )
        decide_purge_request(it_principal, request_id=request.pk, approve=True)
        before_audit_count = SuperAdminAuditLog.objects.count()
        response = ithead_client().post(
            f"/api/v1/superadmin/purge/requests/{request.pk}/decision/",
            {"approve": True, "comments": "Duplicate decision."},
            format="json",
        )
        assert response.status_code == 409
        request.refresh_from_db()
        assert request.status == "approved"
        assert SuperAdminAuditLog.objects.count() == before_audit_count
    elif test_id == "TC-082":
        from modules.superadmin.services.audit import record_audit_event

        record_audit_event(
            actor_id=sa_principal.user_id,
            actor_username=sa_principal.username,
            actor_role="super_admin",
            action="uc.audit.visible",
            target_id="230082",
            target_type="user",
        )
        response = superadmin_client().get(
            "/api/v1/superadmin/audit/logs/", {"action": "uc.audit.visible"}
        )
        assert response.status_code == 200
        assert any(
            item["action"] == "uc.audit.visible"
            for item in response.json()["results"]
        )
    elif test_id == "TC-083":
        response = superadmin_client().get(
            "/api/v1/superadmin/audit/logs/", {"action": "uc.no_matching_entry"}
        )
        assert response.status_code == 200 and response.json()["results"] == []
    elif test_id == "TC-085":
        from modules.superadmin.services.audit import record_audit_event

        record_audit_event(
            actor_id=sa_principal.user_id,
            actor_username=sa_principal.username,
            actor_role="super_admin",
            action="uc.audit.exportable",
            target_id="230085",
            target_type="user",
        )
        response = superadmin_client().get("/api/v1/superadmin/audit/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "uc.audit.exportable" in response.content.decode()
    elif test_id == "TC-088":
        response = superadmin_client().get("/api/v1/superadmin/dashboard/")
        assert response.status_code == 200
        assert {"archived_users_reversible", "archived_users_total", "audit_logs_total"} <= response.json().keys()
    elif test_id == "TC-091":
        from modules.superadmin.domain.constants import PERMITTED_CONFIG_KEYS
        from modules.superadmin.services.config import supersede_policy_param

        key = sorted(PERMITTED_CONFIG_KEYS)[0]
        updated = supersede_policy_param(sa_principal, key=key, value="uc-spec-value")
        assert updated.key == key and updated.value == "uc-spec-value"
        assert SuperAdminAuditLog.objects.filter(target_id=key).exists()
    elif test_id == "TC-093":
        before = SystemPolicyParameter.objects.count()
        response = superadmin_client().post(
            "/api/v1/superadmin/policies/",
            {"key": "placement.academic_calendar", "value": "changed"},
            format="json",
        )
        assert response.status_code == 422
        assert SystemPolicyParameter.objects.count() == before
    elif test_id == "TC-104":
        from modules.superadmin.services.archival import expire_reversibility_sweep

        record = ArchivedUserRecord.objects.create(
            user_id=230104,
            institute_id="2026BCS104",
            username="uc104",
            email="uc104@iiitdmj.ac.in",
            user_kind="student",
            status="reversible",
            archived_at=timezone.now() - timedelta(days=60),
            reversible_until=timezone.now() - timedelta(days=1),
            authorized_by=sa_principal.user_id,
            archival_reason="Archived.",
        )
        assert expire_reversibility_sweep() == 1
        record.refresh_from_db()
        assert record.status == "finalized_permanent" and record.finalized_permanent_at
    elif test_id == "TC-105":
        from modules.superadmin.services.archival import expire_reversibility_sweep

        record = ArchivedUserRecord.objects.create(
            user_id=230105,
            institute_id="2026BCS105",
            username="uc105",
            email="uc105@iiitdmj.ac.in",
            user_kind="student",
            status="restored",
            archived_at=timezone.now() - timedelta(days=60),
            reversible_until=timezone.now() - timedelta(days=1),
            authorized_by=sa_principal.user_id,
            archival_reason="Archived.",
            restored_at=timezone.now() - timedelta(days=2),
            restored_by=sa_principal.user_id,
        )
        assert expire_reversibility_sweep() == 0
        record.refresh_from_db()
        assert record.status == "restored" and record.finalized_permanent_at is None
    else:
        raise AssertionError(f"Unimplemented UC test case: {test_id}")
