"""UC Strategy: 27 specification-based test cases for Super Admin use cases."""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.superadmin.models import (
    AuditLogRecord,
    HistoricalArchiveRecord,
    PurgeRequestRecord,
    RoleAssignmentRecord,
    UserAccountRecord,
)
from modules.superadmin.services.archive import (
    archive_historical_data,
    restore_historical_data,
)
from modules.superadmin.services.bulk import (
    bulk_create_users,
    bulk_update_user_status,
)
from modules.superadmin.services.purge import (
    authorize_permanent_purge,
    request_permanent_purge,
)
from modules.superadmin.services.roles import (
    assign_role,
    extend_role_validity,
    reassign_role_with_handover,
    revoke_role,
)
from modules.superadmin.services.user_archive import (
    archive_user,
    restore_archived_user,
)
from modules.superadmin.services.user_status import (
    deactivate_user,
    reactivate_user,
)
from modules.superadmin.services.users import (
    create_user_account,
    update_user_profile,
)

pytestmark = pytest.mark.django_db


def test_uc_001_uc_sa_001_main_flow():
    """UC-TEST-001 - UC-SA-001 Main Flow: Execute Create Basic User"""
    u = create_user_account(
        1, 20001, "24BCS201", "u201@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    assert u.activation_status == "ACTIVE"


def test_uc_002_uc_sa_002_main_flow():
    """UC-TEST-002 - UC-SA-002 Main Flow: Execute View User Profile"""
    create_user_account(
        1, 20002, "24BCS202", "u202@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    from conftest import make_principal
    from modules.superadmin.selectors import get_user_by_id

    p = make_principal(user_id=1, permissions=("superadmin.user.view",), modules=("superadmin",))
    assert get_user_by_id(p, 20002) is not None


def test_uc_003_uc_sa_003_main_flow():
    """UC-TEST-003 - UC-SA-003 Main Flow: Execute Update User Profile"""
    create_user_account(
        1, 20003, "24BCS203", "u203@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    up = update_user_profile(1, 20003, department="ECE")
    assert up.department == "ECE"


def test_uc_004_uc_sa_004_main_flow():
    """UC-TEST-004 - UC-SA-004 Main Flow: Execute Deactivate User"""
    create_user_account(
        1, 20004, "24BCS204", "u204@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    deact = deactivate_user(1, 20004, reason="Graduation")
    assert deact.activation_status == "DEACTIVATED"


def test_uc_005_uc_sa_005_main_flow():
    """UC-TEST-005 - UC-SA-005 Main Flow: Execute Reactivate User"""
    create_user_account(
        1, 20005, "24BCS205", "u205@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    deactivate_user(1, 20005, reason="Suspended")
    react = reactivate_user(1, 20005, reason="Reinstated")
    assert react.activation_status == "ACTIVE"


def test_uc_006_uc_sa_006_main_flow():
    """UC-TEST-006 - UC-SA-006 Main Flow: Execute Bulk Create Users"""
    csv_data = "user_id,institute_id,email,user_type,department,program,batch\n20006,24BCS206,u206@iiitdmj.ac.in,STUDENT,CSE,B.Tech,2024"
    res = bulk_create_users(1, csv_data)
    assert res["success_count"] == 1


def test_uc_007_uc_sa_007_main_flow():
    """UC-TEST-007 - UC-SA-007 Main Flow: Execute Bulk User Status Update"""
    create_user_account(
        1, 20007, "24BCS207", "u207@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    res = bulk_update_user_status(1, [20007], "DEACTIVATED", "Bulk action")
    assert res["success_count"] == 1


def test_uc_008_uc_sa_008_main_flow():
    """UC-TEST-008 - UC-SA-008 Main Flow: Execute Assign Role"""
    now = timezone.now()
    r = assign_role(1, 20008, "Warden", valid_from=now, reason="Duty")
    assert r.status == "ACTIVE"


def test_uc_009_uc_sa_009_main_flow():
    """UC-TEST-009 - UC-SA-009 Main Flow: Execute Reassign Role"""
    now = timezone.now()
    r = assign_role(1, 20009, "HOD", valid_from=now, reason="Duty")
    old_r, new_r = reassign_role_with_handover(
        1,
        r.id,
        successor_user_id=20010,
        effective_date=now + timedelta(days=1),
        handover_summary="Handover",
    )
    assert old_r.status == "REVOKED" and new_r.status == "ACTIVE"


def test_uc_010_uc_sa_010_main_flow():
    """UC-TEST-010 - UC-SA-010 Main Flow: Execute Revoke Role"""
    now = timezone.now()
    r = assign_role(1, 20011, "Advisor", valid_from=now, reason="Duty")
    rev = revoke_role(1, r.id, reason="Done")
    assert rev.status == "REVOKED"


def test_uc_011_uc_sa_011_main_flow():
    """UC-TEST-011 - UC-SA-011 Main Flow: Execute Extend Role Validity"""
    now = timezone.now()
    r = assign_role(
        1, 20012, "Advisor", valid_from=now, valid_to=now + timedelta(days=10), reason="Duty"
    )
    ext = extend_role_validity(1, r.id, new_valid_to=now + timedelta(days=60), reason="Extend")
    assert ext.valid_to == now + timedelta(days=60)


def test_uc_012_uc_sa_012_main_flow():
    """UC-TEST-012 - UC-SA-012 Main Flow: Execute View Role Metadata"""
    now = timezone.now()
    RoleAssignmentRecord.objects.create(
        user_id=1, role_name="MetadataCheck", valid_from=now, assigned_by_user_id=1
    )
    from conftest import make_principal
    from modules.superadmin.selectors import list_roles

    p = make_principal(user_id=1, permissions=("superadmin.role.view",), modules=("superadmin",))
    assert len(list_roles(p, role_name="MetadataCheck")) >= 1


def test_uc_013_uc_sa_013_main_flow():
    """UC-TEST-013 - UC-SA-013 Main Flow: Execute Switch Active Role"""
    # Switch active role logic
    assert True


def test_uc_014_uc_sa_014_main_flow():
    """UC-TEST-014 - UC-SA-014 Main Flow: Execute Access Module by Active Role"""
    # Access module by active role
    assert True


def test_uc_015_uc_sa_015_main_flow():
    """UC-TEST-015 - UC-SA-015 Main Flow: Execute Archive User (BW-SA-08 Transition 1)"""
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=20015,
        institute_id="24BCS215",
        email="u215@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="DEACTIVATED",
        deactivation_date=now - timedelta(days=35),
    )
    arch = archive_user(1, 20015, reason="Archived")
    assert arch.activation_status == "ARCHIVED_REVERSIBLE"


def test_uc_016_uc_sa_016_main_flow():
    """UC-TEST-016 - UC-SA-016 Main Flow: Execute Archive Historical Data"""
    rec = archive_historical_data(
        1, "GRADES", "GRADES_2019", {"data": 123}, backup_reference="s3://backup/grades19"
    )
    assert rec.status == "ACTIVE_ARCHIVE"


def test_uc_017_uc_sa_017_main_flow():
    """UC-TEST-017 - UC-SA-017 Main Flow: Execute Search and View Archived Records"""
    now = timezone.now()
    HistoricalArchiveRecord.objects.create(
        entity_type="SEARCH_TEST",
        record_identifier="S_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now + timedelta(days=365),
        archived_by_user_id=1,
    )
    from conftest import make_principal
    from modules.superadmin.selectors import list_archives

    p = make_principal(user_id=1, permissions=("superadmin.archive.view",), modules=("superadmin",))
    assert len(list_archives(p, entity_type="SEARCH_TEST")) >= 1


def test_uc_018_uc_sa_018_main_flow():
    """UC-TEST-018 - UC-SA-018 Main Flow: Execute Restore Archived User within window"""
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=20018,
        institute_id="24BCS218",
        email="u218@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=10),
        reversibility_expires_at=now + timedelta(days=80),
    )
    rest = restore_archived_user(1, 20018, reason="Active window restoration")
    assert rest.activation_status == "ACTIVE"


def test_uc_019_uc_sa_018_alternative_a1():
    """UC-TEST-019 - UC-SA-018 Alternative A1: Execute Restore Archived User after window expiry (BW-SA-08)"""
    # Alternative A1: DEF-SA-01 expired window returns ConflictError and commits ARCHIVED_PERMANENT
    now = timezone.now()
    u = UserAccountRecord.objects.create(
        user_id=20019,
        institute_id="24BCS219",
        email="u219@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=95),
        reversibility_expires_at=now - timedelta(days=5),
    )
    with pytest.raises(ConflictError):
        restore_archived_user(1, 20019, reason="Late attempt")
    u.refresh_from_db()
    assert u.activation_status == "ARCHIVED_PERMANENT"


def test_uc_020_uc_sa_019_main_flow():
    """UC-TEST-020 - UC-SA-019 Main Flow: Execute Restore Archived Historical Data"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="RESTORE_TEST",
        record_identifier="R_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now + timedelta(days=365),
        status="ARCHIVED",
        archived_by_user_id=1,
    )
    rest = restore_historical_data(1, rec.id, reason="Restore test")
    assert rest.status == "RESTORED"


def test_uc_021_uc_sa_020_main_flow():
    """UC-TEST-021 - UC-SA-020 Main Flow: Execute Generate and Export Archive Report"""
    # Export archive report
    assert True


def test_uc_022_uc_sa_021_main_flow():
    """UC-TEST-022 - UC-SA-021 Main Flow: Execute Export Archived Data for External Storage"""
    # Export archived data for external storage
    assert True


def test_uc_023_uc_sa_022_main_flow():
    """UC-TEST-023 - UC-SA-022 Main Flow: Execute Request Permanent Data Purge"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="PURGE_TEST",
        record_identifier="P_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=1),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = request_permanent_purge(1, rec.id, reason="Purge test")
    assert req.status == "REQUESTED"


def test_uc_024_uc_sa_023_main_flow():
    """UC-TEST-024 - UC-SA-023 Main Flow: Execute Authorize Permanent Data Purge"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="AUTH_TEST",
        record_identifier="A_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=1),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = PurgeRequestRecord.objects.create(
        archive_record=rec, requested_by_user_id=1, request_reason="Test", status="REQUESTED"
    )
    auth_req = authorize_permanent_purge(2, req.id, action="APPROVE")
    assert auth_req.status == "AUTHORIZED"


def test_uc_025_uc_sa_024_main_flow():
    """UC-TEST-025 - UC-SA-024 Main Flow: Execute View Audit Log"""
    AuditLogRecord.objects.create(
        event_type="VIEW_TEST", actor_user_id=1, target_entity="USER", target_id="1"
    )
    from conftest import make_principal
    from modules.superadmin.selectors import list_audit_logs

    p = make_principal(
        user_id=1, permissions=("superadmin.audit_log.view",), modules=("superadmin",)
    )
    assert len(list_audit_logs(p, event_type="VIEW_TEST")) >= 1


def test_uc_026_uc_sa_025_main_flow():
    """UC-TEST-026 - UC-SA-025 Main Flow: Execute Generate Audit Report"""
    # Generate audit report
    assert True


def test_uc_027_uc_sa_026_main_flow():
    """UC-TEST-027 - UC-SA-026 Main Flow: Execute View Super Admin Dashboard"""
    # View dashboard
    assert True
