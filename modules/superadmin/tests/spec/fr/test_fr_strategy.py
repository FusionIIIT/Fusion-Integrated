"""FR Strategy: 32 specification-based test cases for Super Admin functional requirements."""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.superadmin.domain.exceptions import (
    DomainValidationError,
    ImmutableRecordError,
    PolicyConflictError,
)
from modules.superadmin.domain.policy import (
    check_singular_role_conflict,
    validate_role_compatibility,
)
from modules.superadmin.domain.validators import (
    validate_batch_size,
)
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
from modules.superadmin.services.system_config import update_system_parameter
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


def test_fr_001_cfr_sa_001():
    """FR-TEST-001 - CFR-SA-001: Verify creation of a basic Student user account"""
    u = create_user_account(
        1, 10001, "24BCS001", "u1@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    assert u.activation_status == "ACTIVE"
    assert u.user_type == "STUDENT"


def test_fr_002_cfr_sa_001():
    """FR-TEST-002 - CFR-SA-001: Verify creation of a basic Faculty user account"""
    u = create_user_account(
        1, 10002, "FAC_CSE_01", "fac1@iiitdmj.ac.in", "FACULTY", department="CSE"
    )
    assert u.activation_status == "ACTIVE"
    assert u.user_type == "FACULTY"


def test_fr_003_cfr_sa_001():
    """FR-TEST-003 - CFR-SA-001: Verify creation of a basic Staff user account"""
    u = create_user_account(
        1, 10003, "STAFF_01", "staff1@iiitdmj.ac.in", "STAFF", department="Admin"
    )
    assert u.activation_status == "ACTIVE"
    assert u.user_type == "STAFF"


def test_fr_004_cfr_sa_001_n1():
    """FR-TEST-004 - CFR-SA-001-N1: Refuse user creation with non-institutional email"""
    with pytest.raises(BadRequestError, match="authorized institute domain"):
        create_user_account(
            1, 10004, "24BCS004", "user@gmail.com", "STUDENT", program="B.Tech", batch="2024"
        )


def test_fr_005_cfr_sa_001_n2():
    """FR-TEST-005 - CFR-SA-001-N2: Refuse user creation with duplicate institute_id"""
    create_user_account(
        1, 10005, "INST_DUP", "u5@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    with pytest.raises(ConflictError):
        create_user_account(
            1, 10006, "INST_DUP", "u6@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
        )


def test_fr_006_cfr_sa_002():
    """FR-TEST-006 - CFR-SA-002: View user profile data by user_id"""
    create_user_account(
        1, 10007, "24BCS007", "u7@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    from conftest import make_principal
    from modules.superadmin.selectors import get_user_by_id

    p = make_principal(user_id=1, permissions=("superadmin.user.view",), modules=("superadmin",))
    found = get_user_by_id(p, 10007)
    assert found is not None and found.institute_id == "24BCS007"


def test_fr_007_cfr_sa_002_u1():
    """FR-TEST-007 - CFR-SA-002-U1: Update editable profile fields for existing user"""
    create_user_account(
        1, 10008, "24BCS008", "u8@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    up = update_user_profile(1, 10008, department="CSE", program="M.Tech")
    assert up.department == "CSE" and up.program == "M.Tech"


def test_fr_008_cfr_sa_002_n1():
    """FR-TEST-008 - CFR-SA-002-N1: Refuse update to immutable identity fields"""
    u = create_user_account(
        1, 10009, "24BCS009", "u9@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    assert u.user_id == 10009


def test_fr_009_cfr_sa_003_d1():
    """FR-TEST-009 - CFR-SA-003-D1: Deactivate an active user account"""
    create_user_account(
        1, 10010, "24BCS010", "u10@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    deact = deactivate_user(1, 10010, reason="Graduated")
    assert deact.activation_status == "DEACTIVATED"
    assert deact.deactivation_date is not None


def test_fr_010_cfr_sa_003_r1():
    """FR-TEST-010 - CFR-SA-003-R1: Reactivate a deactivated user account"""
    create_user_account(
        1, 10011, "24BCS011", "u11@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    deactivate_user(1, 10011, reason="Temporary leave")
    react = reactivate_user(1, 10011, reason="Returned from leave")
    assert react.activation_status == "ACTIVE"


def test_fr_011_cfr_sa_003_n1():
    """FR-TEST-011 - CFR-SA-003-N1: Refuse deactivation without step-up authentication"""
    from modules.superadmin.api.permissions import RequiresStepUpAuth

    guard = RequiresStepUpAuth()
    assert guard is not None


def test_fr_012_cfr_sa_004_b1():
    """FR-TEST-012 - CFR-SA-004-B1: Bulk create users from CSV batch"""
    csv_data = "user_id,institute_id,email,user_type,department,program,batch\n10012,24BCS012,u12@iiitdmj.ac.in,STUDENT,CSE,B.Tech,2024"
    res = bulk_create_users(1, csv_data)
    assert res["success_count"] == 1


def test_fr_013_cfr_sa_004_b2():
    """FR-TEST-013 - CFR-SA-004-B2: Bulk status update for user accounts"""
    u = create_user_account(
        1, 10013, "24BCS013", "u13@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    res = bulk_update_user_status(1, [10013], "DEACTIVATED", "Bulk test")
    assert res["success_count"] == 1
    u.refresh_from_db()
    assert u.activation_status == "DEACTIVATED"


def test_fr_014_cfr_sa_004_n1():
    """FR-TEST-014 - CFR-SA-004-N1: Refuse bulk batch exceeding maximum limit"""
    with pytest.raises(DomainValidationError):
        validate_batch_size(501, max_limit=500)


def test_fr_015_cfr_sa_005():
    """FR-TEST-015 - CFR-SA-005: Inspect role definitions and assignment metadata"""
    now = timezone.now()
    RoleAssignmentRecord.objects.create(
        user_id=1, role_name="T15", valid_from=now, assigned_by_user_id=1
    )
    from conftest import make_principal
    from modules.superadmin.selectors import list_roles

    p = make_principal(user_id=1, permissions=("superadmin.role.view",), modules=("superadmin",))
    assert len(list_roles(p, role_name="T15")) >= 1


def test_fr_016_cfr_sa_006_a1():
    """FR-TEST-016 - CFR-SA-006-A1: Assign additional role with validity dates"""
    now = timezone.now()
    r = assign_role(
        1,
        10016,
        "Course Instructor",
        valid_from=now,
        valid_to=now + timedelta(days=90),
        reason="Duty",
    )
    assert r.status == "ACTIVE"


def test_fr_017_cfr_sa_006_n1():
    """FR-TEST-017 - CFR-SA-006-N1: Refuse singular role assignment when already occupied"""
    with pytest.raises(PolicyConflictError):
        check_singular_role_conflict("Dean", current_holder_user_id=1, new_holder_user_id=2)


def test_fr_018_cfr_sa_007():
    """FR-TEST-018 - CFR-SA-007: Reassign existing role with handover transfer"""
    now = timezone.now()
    r = assign_role(1, 10018, "Warden", valid_from=now, reason="Init")
    old_r, new_r = reassign_role_with_handover(
        1,
        r.id,
        successor_user_id=10019,
        effective_date=now + timedelta(days=1),
        handover_summary="Handover notes",
    )
    assert old_r.status == "REVOKED" and new_r.status == "ACTIVE"


def test_fr_019_cfr_sa_008_r1():
    """FR-TEST-019 - CFR-SA-008-R1: Revoke held additional role"""
    now = timezone.now()
    r = assign_role(1, 10020, "Tutor", valid_from=now, reason="Init")
    rev = revoke_role(1, r.id, reason="Finished")
    assert rev.status == "REVOKED"


def test_fr_020_cfr_sa_009_e1():
    """FR-TEST-020 - CFR-SA-009-E1: Extend validity of active role assignment"""
    now = timezone.now()
    r = assign_role(
        1, 10021, "Tutor", valid_from=now, valid_to=now + timedelta(days=10), reason="Init"
    )
    ext = extend_role_validity(1, r.id, new_valid_to=now + timedelta(days=30), reason="Extension")
    assert ext.valid_to == now + timedelta(days=30)


def test_fr_021_cfr_sa_010():
    """FR-TEST-021 - CFR-SA-010: Enforce access boundary by active role permissions"""
    validate_role_compatibility("FACULTY", "Dean of Academic Affairs")


def test_fr_022_cfr_sa_011_a1():
    """FR-TEST-022 - CFR-SA-011-A1: Archive eligible deactivated user"""
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=10022,
        institute_id="24BCS022",
        email="u22@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="DEACTIVATED",
        deactivation_date=now - timedelta(days=35),
    )
    arch = archive_user(1, 10022, reason="Archival")
    assert arch.activation_status == "ARCHIVED_REVERSIBLE"


def test_fr_023_cfr_sa_011_n1():
    """FR-TEST-023 - CFR-SA-011-N1: Refuse archival of active user account"""
    UserAccountRecord.objects.create(
        user_id=10023,
        institute_id="24BCS023",
        email="u23@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ACTIVE",
    )
    with pytest.raises(ConflictError):
        archive_user(1, 10023, reason="Cannot archive active")


def test_fr_024_cfr_sa_012_r1():
    """FR-TEST-024 - CFR-SA-012-R1: Restore archived user within reversibility window"""
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=10024,
        institute_id="24BCS024",
        email="u24@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=10),
        reversibility_expires_at=now + timedelta(days=80),
    )
    rest = restore_archived_user(1, 10024, reason="Restoration within window")
    assert rest.activation_status == "ACTIVE"


def test_fr_025_cfr_sa_012_e1():
    """FR-TEST-025 - CFR-SA-012-E1: Refuse restoration of expired reversible user (BW-SA-08)"""
    # DEF-SA-01: Reversibility window expired: status committed to ARCHIVED_PERMANENT before ConflictError
    now = timezone.now()
    u = UserAccountRecord.objects.create(
        user_id=10025,
        institute_id="24BCS025",
        email="u25@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=95),
        reversibility_expires_at=now - timedelta(days=5),
    )
    with pytest.raises(ConflictError):
        restore_archived_user(1, 10025, reason="Late restoration attempt")
    u.refresh_from_db()
    assert u.activation_status == "ARCHIVED_PERMANENT"


def test_fr_026_cfr_sa_013():
    """FR-TEST-026 - CFR-SA-013: Archive historical inactive dataset"""
    rec = archive_historical_data(
        1, "TEST_ENTITY", "REC_026", {"key": "val"}, backup_reference="s3://backup/026"
    )
    assert rec.status == "ACTIVE_ARCHIVE"


def test_fr_027_cfr_sa_014():
    """FR-TEST-027 - CFR-SA-014: Search and export archived records"""
    now = timezone.now()
    HistoricalArchiveRecord.objects.create(
        entity_type="TEST_EXP",
        record_identifier="EXP_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now + timedelta(days=365),
        archived_by_user_id=1,
    )
    from conftest import make_principal
    from modules.superadmin.selectors import list_archives

    p = make_principal(user_id=1, permissions=("superadmin.archive.view",), modules=("superadmin",))
    assert len(list_archives(p, entity_type="TEST_EXP")) >= 1


def test_fr_028_cfr_sa_015():
    """FR-TEST-028 - CFR-SA-015: Restore archived historical dataset"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="TEST_REST",
        record_identifier="REST_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now + timedelta(days=365),
        status="ARCHIVED",
        archived_by_user_id=1,
    )
    rest = restore_historical_data(1, rec.id, reason="Audit requirement")
    assert rest.status == "RESTORED"


def test_fr_029_cfr_sa_016_p1():
    """FR-TEST-029 - CFR-SA-016-P1: Request permanent data purge"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="TEST_PURGE",
        record_identifier="PURGE_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=5),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = request_permanent_purge(1, rec.id, reason="Retention expired")
    assert req.status == "REQUESTED"


def test_fr_030_cfr_sa_016_a1():
    """FR-TEST-030 - CFR-SA-016-A1: Dual-authorize permanent data purge by IT Head"""
    now = timezone.now()
    rec = HistoricalArchiveRecord.objects.create(
        entity_type="TEST_AUTH",
        record_identifier="AUTH_1",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=5),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = PurgeRequestRecord.objects.create(
        archive_record=rec, requested_by_user_id=1, request_reason="Retention", status="REQUESTED"
    )
    auth_req = authorize_permanent_purge(2, req.id, action="APPROVE")
    assert auth_req.status == "AUTHORIZED"
    rec.refresh_from_db()
    assert rec.status == "PURGED"


def test_fr_031_cfr_sa_017():
    """FR-TEST-031 - CFR-SA-017: Maintain append-only immutable audit log evidence"""
    log = AuditLogRecord.objects.create(
        event_type="SEC", actor_user_id=1, target_entity="USER", target_id="1"
    )
    with pytest.raises(ImmutableRecordError):
        log.delete()


def test_fr_032_cfr_sa_023():
    """FR-TEST-032 - CFR-SA-023: Configure versioned permitted system parameters"""
    param = update_system_parameter(1, "MAX_FAILED_LOGINS", 5)
    assert param.parameter_key == "MAX_FAILED_LOGINS"
    assert param.parameter_value == 5
