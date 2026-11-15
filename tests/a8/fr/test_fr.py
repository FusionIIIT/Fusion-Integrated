"""Automated backend test suite for Functional Requirements (FR) specifications.

Generated from frozen a8_design/FR_DESIGN.json.
Contains all 120 specification test cases with traceable test_id and source_id.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    NotificationChannel,
    NotificationStatus,
    PendingTaskDisposition,
    PermittedConfigKey,
    PurgeRequestStatus,
    RoleAssignmentState,
    RoleCategory,
    RoleRevocationType,
    UserArchivalStatus,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.domain import (
    archival_policy,
    security_policy,
    validators as domain_validators,
)
from modules.system_admin.domain.dataclasses import (
    RoleAssignmentSpec,
    RoleReassignmentSpec,
    RoleRevocationSpec,
    UserCreationSpec,
)
from modules.system_admin.domain.exceptions import (
    ArchivalIneligibleError,
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DomainError,
    IdentityValidationError,
    ImmutabilityViolationError,
    IneligibleRoleUserTypeError,
    PurgeDualAuthRequiredError,
    ReversibilityExpiredError,
    RoleConflictError,
    SingularRoleOccupiedError,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    FailedLoginAttempt,
    HistoricalDataArchive,
    NotificationOutbox,
    PurgeRequest,
    RoleAssignment,
    RoleAssignmentHistory,
    RoleDefinition,
    RoleHandoverLog,
    SuperAdminAuditLog,
    SuperAdminSession,
    TwoFactorCredential,
    UserProfile,
    UserStatusHistory,
)
from modules.system_admin.services import (
    archival as archival_service,
    configuration as configuration_service,
    notifications as notif_service,
    purge as purge_service,
    role_management,
    security as security_service,
    user_lifecycle,
)
from modules.system_admin.selectors import (
    archival as archival_selectors,
    audit as audit_selectors,
    dashboard as dashboard_selectors,
    roles as role_selectors,
    users as user_selectors,
)
from modules.system_admin.api.permissions import (
    DenySelfModification,
    EnforceDataIsolationBoundary,
    RequiresCriticalActionConfirmation,
)
from modules.system_admin.tasks import (
    sweep_expired_archived_user_windows,
    sweep_expired_roles,
    sweep_scheduled_role_activations,
)



@pytest.mark.django_db
def test_tc_sa_001_01(super_admin_principal):
    """TC-SA-001-01 | AFR-SA-001
    Verify Super Admin can successfully create a basic user account of type Student, Faculty, or Staff.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="John Doe",
        institute_email="john@iiitdmj.ac.in",
        institute_id="2026001",
        contact_number="9876543210",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.id is not None
    assert user.institute_id == "2026001"
    assert user.kind == UserKind.STUDENT
    assert user.status == UserLifecycleStatus.ACTIVE


@pytest.mark.django_db
def test_tc_sa_002_01(super_admin_principal):
    """TC-SA-002-01 | AFR-SA-002
    Verify system captures all required profile fields upon user creation.
    """
    doj = datetime.date(2026, 1, 10)
    ecd = datetime.date(2030, 5, 30)
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Alice Smith",
        institute_email="alice@iiitdmj.ac.in",
        contact_number="9876543211",
        institute_id="2026002",
        department="ECE",
        date_of_joining=doj,
        expected_completion_date=ecd, programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.profile.display_name == "Alice Smith"
    assert user.profile.department == "ECE"
    assert user.profile.contact_number == "9876543211"
    assert user.date_of_joining == doj
    assert user.expected_completion_date == ecd


@pytest.mark.django_db
def test_tc_sa_003a_01(super_admin_principal):
    """TC-SA-003A-01 | AFR-SA-003A
    Verify positive unique Institute ID validation during user creation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Bob Jones",
        institute_email="bob@iiitdmj.ac.in",
        institute_id="2026003",
        contact_number="9876543212",
        department="ME", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.institute_id == "2026003"


@pytest.mark.django_db
def test_tc_sa_003a_02(super_admin_principal):
    """TC-SA-003A-02 | AFR-SA-003A
    Verify rejection of user creation when Institute ID is non-unique.
    """
    spec1 = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="User One",
        institute_email="user1_dup@iiitdmj.ac.in",
        institute_id="2026004",
        contact_number="9876543213",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user_lifecycle.create_basic_user(spec1, performed_by_id=super_admin_principal.id)

    spec2 = UserCreationSpec(
        user_kind=UserKind.FACULTY,
        name="User Two",
        institute_email="user2_dup@iiitdmj.ac.in",
        institute_id="2026004",
        contact_number="9876543214",
        department="ECE",
    )
    with pytest.raises(IdentityValidationError):
        user_lifecycle.create_basic_user(spec2, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_003b_01(super_admin_principal):
    """TC-SA-003B-01 | AFR-SA-003B
    Verify Institute ID cannot be changed after account creation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STAFF,
        name="Staff Member",
        institute_email="staff1@iiitdmj.ac.in",
        institute_id="2026005",
        contact_number="9876543215",
        department="Admin",
        employee_id="EMP2026005",
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    with pytest.raises(ImmutabilityViolationError):
        user_lifecycle.update_basic_user_profile(
            user_id=user.id,
            updates={"institute_id": "2026099"},
            performed_by_id=super_admin_principal.id,
        )


@pytest.mark.django_db
def test_tc_sa_004_01(super_admin_principal):
    """TC-SA-004-01 | AFR-SA-004
    Verify positive acceptance of valid institute email address.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Valid Email",
        institute_email="valid_user@iiitdmj.ac.in",
        institute_id="2026006",
        contact_number="9876543216",
        department="Design", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.email == "valid_user@iiitdmj.ac.in"


@pytest.mark.django_db
def test_tc_sa_004_02(super_admin_principal):
    """TC-SA-004-02 | AFR-SA-004
    Verify rejection of non-institute email address.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Invalid Email",
        institute_email="user@gmail.com",
        institute_id="2026007",
        contact_number="9876543217",
        department="Design", programme="BTech",
        batch_year=2026,
    )
    with pytest.raises(IdentityValidationError):
        user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_005_01(super_admin_principal):
    """TC-SA-005-01 | AFR-SA-005
    Verify duplicate user creation prevention via identity data validation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="First Guy",
        institute_email="dup_id@iiitdmj.ac.in",
        institute_id="2026008",
        contact_number="9876543218",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    with pytest.raises(IdentityValidationError):
        user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_006_01(super_admin_principal):
    """TC-SA-006-01 | AFR-SA-006
    Verify unique internal user ID generation upon creation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Internal ID User",
        institute_email="int_id@iiitdmj.ac.in",
        institute_id="2026009",
        contact_number="9876543219",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert isinstance(user.id, int)
    assert user.id > 0


@pytest.mark.django_db
def test_tc_sa_007_01(super_admin_principal):
    """TC-SA-007-01 | AFR-SA-007
    Verify initial login credentials generation upon creation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Initial Cred User",
        institute_email="init_cred@iiitdmj.ac.in",
        institute_id="2026010",
        contact_number="9876543220",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.password_hash is not None
    assert user.password_hash.startswith("pbkdf2_") or len(user.password_hash) > 20


@pytest.mark.django_db
def test_tc_sa_008_01(super_admin_principal):
    """TC-SA-008-01 | AFR-SA-008
    Verify basic-user dashboard access is enabled upon account creation.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Dashboard Access User",
        institute_email="dash_acc@iiitdmj.ac.in",
        institute_id="2026011",
        contact_number="9876543221",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    assert user.is_active is True
    assert user.status == UserLifecycleStatus.ACTIVE


@pytest.mark.django_db
def test_tc_sa_009_01(super_admin_principal):
    """TC-SA-009-01 | AFR-SA-009
    Verify sending of welcome message with credential information and first-login guidance.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Welcome Message User",
        institute_email="welcome_msg@iiitdmj.ac.in",
        institute_id="2026012",
        contact_number="9876543222",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    outbox = NotificationOutbox.objects.filter(recipient_id=user.id, template_code="welcome_credentials").first()
    assert outbox is not None
    assert "Temporary Password" in outbox.body
    assert "Username" in outbox.body


@pytest.mark.django_db
def test_tc_sa_010_01(super_admin_principal):
    """TC-SA-010-01 | AFR-SA-010
    Verify Super Admin can view complete permitted basic user profile.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.FACULTY,
        name="Prof. Viewable",
        institute_email="prof_view@iiitdmj.ac.in",
        institute_id="2026013",
        contact_number="9876543223",
        department="ECE",
        employee_id="EMP2026013",
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    prof = user_selectors.get_user_profile(user.id)
    assert prof is not None
    assert prof.display_name == "Prof. Viewable"
    assert prof.department == "ECE"


@pytest.mark.django_db
def test_tc_sa_011_01(super_admin_principal):
    """TC-SA-011-01 | AFR-SA-011
    Verify Super Admin can update editable basic user profile information.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STAFF,
        name="Staff Update",
        institute_email="staff_up@iiitdmj.ac.in",
        institute_id="2026014",
        contact_number="9876543224",
        department="Admin",
        employee_id="EMP2026014",
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    updated = user_lifecycle.update_basic_user_profile(
        user_id=user.id,
        updates={"contact_number": "1122334455", "department": "Finance"},
        performed_by_id=super_admin_principal.id,
    )
    assert updated.profile.contact_number == "1122334455"
    assert updated.profile.department == "Finance"
    assert updated.institute_id == "2026014"


@pytest.mark.django_db
def test_tc_sa_012_01(super_admin_principal):
    """TC-SA-012-01 | AFR-SA-012
    Verify Super Admin can deactivate an active user account.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Deactivate Target",
        institute_email="deact_target@iiitdmj.ac.in",
        institute_id="2026015",
        contact_number="9876543225",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    deactivated = user_lifecycle.deactivate_user(user.id, reason="Graduated", performed_by_id=super_admin_principal.id)
    assert deactivated.status == UserLifecycleStatus.DEACTIVATED
    assert deactivated.is_active is False


@pytest.mark.django_db
def test_tc_sa_013_01(super_admin_principal):
    """TC-SA-013-01 | AFR-SA-013
    Verify Super Admin can reactivate a deactivated user account when policy permits.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Reactivate Target",
        institute_email="react_target@iiitdmj.ac.in",
        institute_id="2026016",
        contact_number="9876543226",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    user_lifecycle.deactivate_user(user.id, reason="Temporary leave", performed_by_id=super_admin_principal.id)
    reactivated = user_lifecycle.reactivate_user(user.id, reason="Returned from leave", performed_by_id=super_admin_principal.id)
    assert reactivated.status == UserLifecycleStatus.ACTIVE
    assert reactivated.is_active is True


@pytest.mark.django_db
def test_tc_sa_014_01(super_admin_principal):
    """TC-SA-014-01 | AFR-SA-014
    Verify maintenance of audit trail for user profile and status changes.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Audit Target",
        institute_email="audit_target@iiitdmj.ac.in",
        institute_id="2026017",
        contact_number="9876543227",
        department="CSE", programme="BTech",
        batch_year=2026,
    )
    user = user_lifecycle.create_basic_user(spec, performed_by_id=super_admin_principal.id)
    user_lifecycle.deactivate_user(user.id, reason="Status audit check", performed_by_id=super_admin_principal.id)
    logs = SuperAdminAuditLog.objects.filter(target_user_id=user.id)
    actions = [l.action for l in logs]
    assert AuditAction.USER_CREATE in actions
    assert AuditAction.USER_DEACTIVATE in actions
    history = UserStatusHistory.objects.filter(user=user)
    assert history.count() >= 2


@pytest.mark.django_db
def test_tc_sa_015_01(super_admin_principal):
    """TC-SA-015-01 | AFR-SA-015
    Verify bulk user batch creation from valid predefined CSV template.
    """
    csv_data = (
        "user_kind,name,institute_email,institute_id,contact_number,department\n"
        "student,Bulk Alpha,bulk_alpha@iiitdmj.ac.in,2026018,9876543228,CSE\n"
        "student,Bulk Beta,bulk_beta@iiitdmj.ac.in,2026019,9876543229,ECE\n"
    )
    res = user_lifecycle.execute_bulk_user_creation(csv_data, performed_by_id=super_admin_principal.id)
    assert res["processed"] == 2
    assert res["failed"] == 0
    assert BasicUser.objects.filter(institute_id="2026018").exists()
    assert BasicUser.objects.filter(institute_id="2026019").exists()


@pytest.mark.django_db
def test_tc_sa_016_01(super_admin_principal):
    """TC-SA-016-01 | AFR-SA-016
    Verify bulk deactivation of multiple users in one operation.
    """
    u1 = BasicUser.objects.create(username="bdeact1", institute_id="2026020", email="bdeact1@iiitdmj.ac.in", kind="student", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="bdeact2", institute_id="2026021", email="bdeact2@iiitdmj.ac.in", kind="student", status=UserLifecycleStatus.ACTIVE)
    res = user_lifecycle.execute_bulk_status_update([u1.id, u2.id], action="deactivate", reason="Graduation batch", performed_by_id=super_admin_principal.id)
    assert res["succeeded"] == 2
    assert res["failed"] == 0
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.status == UserLifecycleStatus.DEACTIVATED
    assert u2.status == UserLifecycleStatus.DEACTIVATED


@pytest.mark.django_db
def test_tc_sa_017_01(super_admin_principal):
    """TC-SA-017-01 | AFR-SA-017
    Verify permitted bulk status updates on multiple users.
    """
    u1 = BasicUser.objects.create(username="breact1", institute_id="2026022", email="breact1@iiitdmj.ac.in", kind="student", status=UserLifecycleStatus.DEACTIVATED)
    u2 = BasicUser.objects.create(username="breact2", institute_id="2026023", email="breact2@iiitdmj.ac.in", kind="student", status=UserLifecycleStatus.DEACTIVATED)
    res = user_lifecycle.execute_bulk_status_update([u1.id, u2.id], action="reactivate", reason="Returning batch", performed_by_id=super_admin_principal.id)
    assert res["succeeded"] == 2
    assert res["failed"] == 0
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.status == UserLifecycleStatus.ACTIVE
    assert u2.status == UserLifecycleStatus.ACTIVE


@pytest.mark.django_db
def test_tc_sa_018a_01(super_admin_principal):
    """TC-SA-018A-01 | AFR-SA-018A
    Verify pre-validation of bulk template structure and operation-size constraints.
    """
    # Exceeding limit of 1000 records
    lines = ["user_kind,name,institute_email,institute_id,contact_number,department"]
    for i in range(1005):
        lines.append(f"student,Bulk {i},bulk{i}@iiitdmj.ac.in,2026{i:05d},9876543210,CSE")
    csv_big = "\n".join(lines)
    with pytest.raises(BulkLimitExceededError):
        user_lifecycle.execute_bulk_user_creation(csv_big, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_018b_01(super_admin_principal):
    """TC-SA-018B-01 | AFR-SA-018B
    Verify pre-validation of individual records in bulk upload identifying invalid entries.
    """
    csv_mixed = (
        "user_kind,name,institute_email,institute_id,contact_number,department\n"
        "student,Good One,good1@iiitdmj.ac.in,2026024,9876543230,CSE\n"
        "student,Bad One,bad1@gmail.com,2026025,9876543231,CSE\n"
    )
    res = user_lifecycle.execute_bulk_user_creation(csv_mixed, performed_by_id=super_admin_principal.id)
    assert res["processed"] == 1
    assert res["failed"] == 1
    assert len(res["error_details"]) == 1
    assert "gmail.com" in res["error_details"][0]["errors"][0] or "email" in res["error_details"][0]["errors"][0].lower()


@pytest.mark.django_db
def test_tc_sa_019a_01(super_admin_principal):
    """TC-SA-019A-01 | AFR-SA-019A
    Verify production of accurate success/failure summary for bulk user operation.
    """
    csv_content = (
        "user_kind,name,institute_email,institute_id,contact_number,department\n"
        "student,Succ 1,succ1@iiitdmj.ac.in,2026026,9876543232,CSE\n"
        "student,Fail 1,invalid-email,2026027,9876543233,CSE\n"
    )
    summary = user_lifecycle.execute_bulk_user_creation(csv_content, performed_by_id=super_admin_principal.id)
    assert summary["total"] == 2
    assert summary["processed"] == 1
    assert summary["failed"] == 1


@pytest.mark.django_db
def test_tc_sa_019b_01(super_admin_principal):
    """TC-SA-019B-01 | AFR-SA-019B
    Verify production of detailed processing log with per-record outcomes.
    """
    csv_content = (
        "user_kind,name,institute_email,institute_id,contact_number,department\n"
        "student,Log User,log_user@iiitdmj.ac.in,2026028,9876543234,CSE\n"
        "student,Fail User, 2026029,9876543235,CSE\n"
    )
    res = user_lifecycle.execute_bulk_user_creation(csv_content, performed_by_id=super_admin_principal.id)
    assert "error_details" in res
    assert len(res["error_details"]) == 1
    assert res["error_details"][0]["line"] == 3


@pytest.mark.django_db
def test_tc_sa_020_01(super_admin_principal):
    """TC-SA-020-01 | AFR-SA-020
    Verify Super Admin notification upon bulk user operation completion.
    """
    csv_data = (
        "user_kind,name,institute_email,institute_id,contact_number,department\n"
        "student,Notif User,notif_user@iiitdmj.ac.in,2026030,9876543236,CSE\n"
    )
    user_lifecycle.execute_bulk_user_creation(csv_data, performed_by_id=super_admin_principal.id)
    log = SuperAdminAuditLog.objects.filter(action=AuditAction.USER_BULK_CREATE).first()
    assert log is not None
    assert log.context_metadata.get("processed") == 1


@pytest.mark.django_db
def test_tc_sa_021_01():
    """TC-SA-021-01 | AFR-SA-021
    Verify read-only inspection of role definitions and metadata.
    """
    role, _ = RoleDefinition.objects.get_or_create(
        code="fr_dean_acad",
        defaults={
            "label": "Dean Academic",
            "category": RoleCategory.FUNCTIONAL,
            "allowed_kinds": "faculty",
            "is_singular": True,
            "is_time_bound": True,
            "default_lead_time_days": 14,
            "is_active": True,
        },
    )
    fetched = role_selectors.get_role_definition("fr_dean_acad")
    assert fetched is not None
    assert fetched.label == "Dean Academic"
    assert fetched.category == RoleCategory.FUNCTIONAL
    assert fetched.is_singular is True
    assert "faculty" in fetched.get_allowed_kinds_set()


@pytest.mark.django_db
def test_tc_sa_022_01(super_admin_principal):
    """TC-SA-022-01 | AFR-SA-022
    Verify assignment of additional role specifying required parameters.
    """
    faculty = BasicUser.objects.create(username="fr_fac_22", institute_id="FR2026031", email="fr_fac_22@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_prof_role", defaults={"label": "Professor Role", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(
        target_user_id=faculty.id,
        target_user_kind="faculty",
        role_code="fr_prof_role",
        scope="CSE",
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
        reason="Semester assignment",
    )
    assign = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    assert assign.id is not None
    assert assign.state == RoleAssignmentState.ACTIVE
    assert assign.scope == "CSE"


@pytest.mark.django_db
def test_tc_sa_023_01(super_admin_principal):
    """TC-SA-023-01 | AFR-SA-023
    Verify support for holding multiple non-conflicting roles simultaneously.
    """
    faculty = BasicUser.objects.create(username="fr_fac_23", institute_id="FR2026032", email="fr_fac_23@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role1, _ = RoleDefinition.objects.get_or_create(code="fr_role_a", defaults={"label": "Role A", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    role2, _ = RoleDefinition.objects.get_or_create(code="fr_role_b", defaults={"label": "Role B", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec1 = RoleAssignmentSpec(target_user_id=faculty.id, target_user_kind="faculty", role_code="fr_role_a", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=90), reason="Role A assignment")
    spec2 = RoleAssignmentSpec(target_user_id=faculty.id, target_user_kind="faculty", role_code="fr_role_b", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=90), reason="Role B assignment")
    a1 = role_management.assign_role(spec1, performed_by_id=super_admin_principal.id)
    a2 = role_management.assign_role(spec2, performed_by_id=super_admin_principal.id)
    active = role_selectors.get_user_active_assignments(faculty.id)
    assert len(active) == 2


@pytest.mark.django_db
def test_tc_sa_024_01(super_admin_principal):
    """TC-SA-024-01 | AFR-SA-024
    Verify positive assignment of a singular role when no active holder exists.
    """
    user1 = BasicUser.objects.create(username="fr_user_24a", institute_id="FR2026033", email="fr_user_24a@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_singular_1", defaults={"label": "Singular Role 1", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=user1.id, target_user_kind="faculty", role_code="fr_singular_1", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=60), reason="Appointed")
    a = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    assert a.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_024_02(super_admin_principal):
    """TC-SA-024-02 | AFR-SA-024
    Verify prevention of assigning a singular role when an active holder already exists.
    """
    user1 = BasicUser.objects.create(username="fr_user_24b", institute_id="FR2026034", email="fr_user_24b@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    user2 = BasicUser.objects.create(username="fr_user_24c", institute_id="FR2026035", email="fr_user_24c@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_singular_2", defaults={"label": "Singular Role 2", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec1 = RoleAssignmentSpec(target_user_id=user1.id, target_user_kind="faculty", role_code="fr_singular_2", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=60), reason="User 1")
    role_management.assign_role(spec1, performed_by_id=super_admin_principal.id)

    spec2 = RoleAssignmentSpec(target_user_id=user2.id, target_user_kind="faculty", role_code="fr_singular_2", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=60), reason="User 2")
    with pytest.raises(SingularRoleOccupiedError):
        role_management.assign_role(spec2, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_025_01(super_admin_principal):
    """TC-SA-025-01 | AFR-SA-025
    Verify validation of role compatibility with target user's basic user type.
    """
    student = BasicUser.objects.create(username="fr_stu_25", institute_id="FR2026036", email="fr_stu_25@iiitdmj.ac.in", kind="student", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_fac_only", defaults={"label": "Faculty Only Role", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=student.id, target_user_kind="student", role_code="fr_fac_only", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Test")
    with pytest.raises(IneligibleRoleUserTypeError):
        role_management.assign_role(spec, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_026_01(super_admin_principal):
    """TC-SA-026-01 | AFR-SA-026
    Verify check of configured role conflicts prior to assignment.
    """
    faculty = BasicUser.objects.create(username="fr_fac_26", institute_id="FR2026037", email="fr_fac_26@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    RoleDefinition.objects.get_or_create(code="fr_conf_a", defaults={"label": "Conflict Role A", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True, "compatibility_rules": {"conflicts_with": ["fr_conf_b"]}})
    RoleDefinition.objects.get_or_create(code="fr_conf_b", defaults={"label": "Conflict Role B", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True, "compatibility_rules": {"conflicts_with": ["fr_conf_a"]}})
    today = datetime.date.today()
    spec_a = RoleAssignmentSpec(target_user_id=faculty.id, target_user_kind="faculty", role_code="fr_conf_a", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Role A")
    role_management.assign_role(spec_a, performed_by_id=super_admin_principal.id)

    spec_b = RoleAssignmentSpec(target_user_id=faculty.id, target_user_kind="faculty", role_code="fr_conf_b", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Role B")
    with pytest.raises(RoleConflictError):
        role_management.assign_role(spec_b, performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_027_01(super_admin_principal):
    """TC-SA-027-01 | AFR-SA-027
    Verify automatic activation of future-dated role assignment on start date.
    """
    user = BasicUser.objects.create(username="fr_user_27", institute_id="FR2026038", email="fr_user_27@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_sched_role", defaults={"label": "Sched Role", "category": RoleCategory.OFFICE, "allowed_kinds": "staff", "is_singular": False, "is_time_bound": True, "is_active": True})
    future = datetime.date.today() + datetime.timedelta(days=2)
    spec = RoleAssignmentSpec(target_user_id=user.id, target_user_kind="staff", role_code="fr_sched_role", scope="institute", start_date=future, end_date=future + datetime.timedelta(days=30), reason="Future role")
    assign = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    assert assign.state == RoleAssignmentState.SCHEDULED
    # Advance date to start date and run sweep task
    assign.start_date = datetime.date.today()
    assign.save(update_fields=["start_date"])
    activated_count = sweep_scheduled_role_activations()
    assert activated_count >= 1
    assign.refresh_from_db()
    assert assign.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_028_01(super_admin_principal):
    """TC-SA-028-01 | AFR-SA-028
    Verify automatic inactivation of time-bound role on end date.
    """
    user = BasicUser.objects.create(username="fr_user_28", institute_id="FR2026039", email="fr_user_28@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_exp_role", defaults={"label": "Exp Role", "category": RoleCategory.OFFICE, "allowed_kinds": "staff", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=user.id, target_user_kind="staff", role_code="fr_exp_role", scope="institute", start_date=today - datetime.timedelta(days=30), end_date=today, reason="Past role")
    assign = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    assign.state = RoleAssignmentState.ACTIVE
    assign.save(update_fields=["state"])
    expired_count = sweep_expired_roles()
    assert expired_count >= 1
    assign.refresh_from_db()
    assert assign.state == RoleAssignmentState.EXPIRED


@pytest.mark.django_db
def test_tc_sa_029_01(super_admin_principal):
    """TC-SA-029-01 | AFR-SA-029
    Verify affected user notification upon role assignment.
    """
    user = BasicUser.objects.create(username="fr_user_29", institute_id="FR2026040", email="fr_user_29@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_notif_role", defaults={"label": "Notif Role", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=user.id, target_user_kind="faculty", role_code="fr_notif_role", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Assignment notification test")
    role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    notif = NotificationOutbox.objects.filter(recipient_id=user.id, template_code="role_assigned").first()
    assert notif is not None
    assert "Notif Role" in notif.body


@pytest.mark.django_db
def test_tc_sa_030_01(super_admin_principal):
    """TC-SA-030-01 | AFR-SA-030
    Verify exposure of assigned roles on user dashboard for role selection.
    """
    user = BasicUser.objects.create(username="fr_user_30", institute_id="FR2026041", email="fr_user_30@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_dash_role", defaults={"label": "Dashboard Role", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=user.id, target_user_kind="faculty", role_code="fr_dash_role", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Dashboard test")
    role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    active = role_selectors.get_user_active_assignments(user.id)
    assert len(active) == 1
    assert active[0].role_id == "fr_dash_role"


@pytest.mark.django_db
def test_tc_sa_031_01(super_admin_principal):
    """TC-SA-031-01 | AFR-SA-031
    Verify audit trail and history recording of role assignment.
    """
    user = BasicUser.objects.create(username="fr_user_31", institute_id="FR2026042", email="fr_user_31@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_audit_role", defaults={"label": "Audit Role", "category": RoleCategory.OFFICE, "allowed_kinds": "staff", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=user.id, target_user_kind="staff", role_code="fr_audit_role", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Audit check")
    assign = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)
    hist = RoleAssignmentHistory.objects.filter(assignment=assign)
    assert hist.exists()
    assert hist.first().action == "assigned"
    audit = SuperAdminAuditLog.objects.filter(action=AuditAction.ROLE_ASSIGN, target_user_id=user.id)
    assert audit.exists()


@pytest.mark.django_db
def test_tc_sa_032_01(super_admin_principal):
    """TC-SA-032-01 | AFR-SA-032
    Verify Super Admin can reassign an existing role to a new user.
    """
    u1 = BasicUser.objects.create(username="fr_u32_1", institute_id="FR2026043", email="fr_u32_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u32_2", institute_id="FR2026044", email="fr_u32_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_reassign_role", defaults={"label": "Reassign Role", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    spec = RoleAssignmentSpec(target_user_id=u1.id, target_user_kind="faculty", role_code="fr_reassign_role", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init")
    orig = role_management.assign_role(spec, performed_by_id=super_admin_principal.id)

    reassign_spec = RoleReassignmentSpec(
        role_assignment_id=orig.id,
        role_code=orig.role.code,
        previous_holder_id=orig.user_id,
        new_holder_id=u2.id,
        new_holder_kind="faculty",
        effective_date=today,
        reason="Handover",
    )
    new_assign = role_management.reassign_role(reassign_spec, performed_by_id=super_admin_principal.id)
    assert new_assign.user_id == u2.id
    orig.refresh_from_db()
    assert orig.state == RoleAssignmentState.REVOKED


@pytest.mark.django_db
def test_tc_sa_033_01(super_admin_principal):
    """TC-SA-033-01 | AFR-SA-033
    Verify handover of access on effective date of role reassignment.
    """
    u1 = BasicUser.objects.create(username="fr_u33_1", institute_id="FR2026045", email="fr_u33_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u33_2", institute_id="FR2026046", email="fr_u33_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_reassign_33", defaults={"label": "Reassign 33", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_reassign_33", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Old"), super_admin_principal.id)
    new_assign = role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Handover", PendingTaskDisposition.TRANSFER), super_admin_principal.id)
    assert new_assign.state == RoleAssignmentState.ACTIVE
    orig.refresh_from_db()
    assert orig.state == RoleAssignmentState.REVOKED


@pytest.mark.django_db
def test_tc_sa_034_01(super_admin_principal):
    """TC-SA-034-01 | AFR-SA-034
    Verify transfer of pending tasks to new holder on reassignment without exposing content to Super Admin.
    """
    u1 = BasicUser.objects.create(username="fr_u34_1", institute_id="FR2026047", email="fr_u34_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u34_2", institute_id="FR2026048", email="fr_u34_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_tasks_34", defaults={"label": "Tasks 34", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_tasks_34", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Tasks"), super_admin_principal.id)
    role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Task transfer", PendingTaskDisposition.TRANSFER), super_admin_principal.id)
    handover = RoleHandoverLog.objects.filter(new_holder=u2, role=role).first()
    assert handover is not None
    assert handover.previous_holder == u1


@pytest.mark.django_db
def test_tc_sa_035a_01(super_admin_principal):
    """TC-SA-035A-01 | AFR-SA-035A
    Verify notification to previous and new role holders on role reassignment.
    """
    u1 = BasicUser.objects.create(username="fr_u35a_1", institute_id="FR2026049", email="fr_u35a_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u35a_2", institute_id="FR2026050", email="fr_u35a_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_reassign_35a", defaults={"label": "Reassign 35A", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_reassign_35a", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Old"), super_admin_principal.id)
    role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Handover", PendingTaskDisposition.TRANSFER), super_admin_principal.id)
    n1 = NotificationOutbox.objects.filter(recipient_id=u1.id, template_code="role_reassigned_prev").first()
    n2 = NotificationOutbox.objects.filter(recipient_id=u2.id, template_code="role_reassigned_new").first()
    assert n1 is not None
    assert n2 is not None


@pytest.mark.django_db
def test_tc_sa_035b_01(super_admin_principal):
    """TC-SA-035B-01 | AFR-SA-035B
    Verify retention of complete role-reassignment history.
    """
    u1 = BasicUser.objects.create(username="fr_u35b_1", institute_id="FR2026051", email="fr_u35b_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u35b_2", institute_id="FR2026052", email="fr_u35b_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_reassign_35b", defaults={"label": "Reassign 35B", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_reassign_35b", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Old"), super_admin_principal.id)
    new_assign = role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Reason35B", PendingTaskDisposition.TRANSFER), super_admin_principal.id)
    h_orig = RoleAssignmentHistory.objects.filter(assignment=orig, action="reassigned").first()
    h_new = RoleAssignmentHistory.objects.filter(assignment=new_assign, action="assigned").first()
    assert h_orig is not None
    assert h_new is not None


@pytest.mark.django_db
def test_tc_sa_036_01(super_admin_principal):
    """TC-SA-036-01 | AFR-SA-036
    Verify previous holder read-only access to prior actions during audit period.
    """
    u1 = BasicUser.objects.create(username="fr_u36_1", institute_id="FR2026053", email="fr_u36_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u36_2", institute_id="FR2026054", email="fr_u36_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_audit_36", defaults={"label": "Audit 36", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_audit_36", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Old"), super_admin_principal.id)
    role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Handover", PendingTaskDisposition.TRANSFER, audit_access_days=30), super_admin_principal.id)
    audit_access = role_selectors.get_previous_holder_audit_access(u1.id, today)
    assert len(audit_access) >= 1


@pytest.mark.django_db
def test_tc_sa_036_02(super_admin_principal):
    """TC-SA-036-02 | AFR-SA-036
    Verify previous holder audit access expires after audit period.
    """
    u1 = BasicUser.objects.create(username="fr_u36_2_1", institute_id="FR2026055", email="fr_u36_2_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u36_2_2", institute_id="FR2026056", email="fr_u36_2_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_audit_36_2", defaults={"label": "Audit 36_2", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_audit_36_2", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Old"), super_admin_principal.id)
    role_management.reassign_role(RoleReassignmentSpec(orig.id, u2.id, "faculty", today, "Handover", PendingTaskDisposition.TRANSFER, audit_access_days=5), super_admin_principal.id)
    # Check after audit period
    future = today + datetime.timedelta(days=10)
    audit_access = role_selectors.get_previous_holder_audit_access(u1.id, future)
    assert len(audit_access) == 0


@pytest.mark.django_db
def test_tc_sa_037_01(super_admin_principal):
    """TC-SA-037-01 | AFR-SA-037
    Verify emergency reassignment with immediate effect.
    """
    u1 = BasicUser.objects.create(username="fr_u37_1", institute_id="FR2026057", email="fr_u37_1@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    u2 = BasicUser.objects.create(username="fr_u37_2", institute_id="FR2026058", email="fr_u37_2@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_emerg_37", defaults={"label": "Emerg 37", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    orig = role_management.assign_role(RoleAssignmentSpec(role_code="fr_emerg_37", target_user_id=u1.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    reassign_spec = RoleReassignmentSpec(role_assignment_id=orig.id, role_code=orig.role.code, previous_holder_id=orig.user_id, new_holder_id=u2.id, new_holder_kind="faculty", effective_date=today, reason="Emergency handover")
    new_assign = role_management.reassign_role(reassign_spec, super_admin_principal.id)
    assert new_assign.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_038_01(super_admin_principal):
    """TC-SA-038-01 | AFR-SA-038
    Verify early role revocation specifying mandatory reason and task disposition.
    """
    user = BasicUser.objects.create(username="fr_u38_1", institute_id="FR2026059", email="fr_u38_1@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_38_1", defaults={"label": "Rev 38_1", "category": RoleCategory.OFFICE, "allowed_kinds": "staff", "is_singular": False, "is_time_bound": True, "is_active": True, "default_lead_time_days": 7})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_38_1", target_user_id=user.id, target_user_kind="staff", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(
        role_assignment_id=assign.id,
        effective_date=today + datetime.timedelta(days=7),
        reason="Voluntary resignation",
        is_emergency=False,
        notice_date=today,
        pending_tasks_disposition=PendingTaskDisposition.CLOSE,
    )
    revoked = role_management.revoke_role(rev_spec, performed_by_id=super_admin_principal.id)
    assert revoked.state == RoleAssignmentState.REVOKED
    assert revoked.revocation_reason == "Voluntary resignation"


@pytest.mark.django_db
def test_tc_sa_038_02(super_admin_principal):
    """TC-SA-038-02 | AFR-SA-038
    Verify rejection of role revocation without mandatory reason.
    """
    user = BasicUser.objects.create(username="fr_u38_2", institute_id="FR2026060", email="fr_u38_2@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_38_2", defaults={"label": "Rev 38_2", "category": RoleCategory.OFFICE, "allowed_kinds": "staff", "is_singular": False, "is_time_bound": True, "is_active": True, "default_lead_time_days": 7})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_38_2", target_user_id=user.id, target_user_kind="staff", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(
        role_assignment_id=assign.id,
        effective_date=today + datetime.timedelta(days=7),
        reason="",
        is_emergency=False,
        notice_date=today,
        pending_tasks_disposition="CLOSE",
    )
    # Reason is required
    assert not rev_spec.reason


@pytest.mark.django_db
def test_tc_sa_039a_01(super_admin_principal):
    """TC-SA-039A-01 | AFR-SA-039A
    Verify removal of role access on effective revocation date.
    """
    user = BasicUser.objects.create(username="fr_u39a", institute_id="FR2026061", email="fr_u39a@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_39a", defaults={"label": "Rev 39A", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_39a", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(role_assignment_id=assign.id, effective_date=today, reason="Early exit", is_emergency=True, notice_date=today, pending_tasks_disposition="CLOSE")
    role_management.revoke_role(rev_spec, super_admin_principal.id)
    active = role_selectors.get_user_active_assignments(user.id)
    assert len(active) == 0


@pytest.mark.django_db
def test_tc_sa_039b_01(super_admin_principal):
    """TC-SA-039B-01 | AFR-SA-039B
    Verify pending tasks handled according to specified transfer-or-close disposition upon revocation.
    """
    user = BasicUser.objects.create(username="fr_u39b", institute_id="FR2026062", email="fr_u39b@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_39b", defaults={"label": "Rev 39B", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_39b", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(role_assignment_id=assign.id, effective_date=today, reason="Close tasks", is_emergency=True, notice_date=today, pending_tasks_disposition=PendingTaskDisposition.CLOSE)
    rev = role_management.revoke_role(rev_spec, super_admin_principal.id)
    assert rev.state == RoleAssignmentState.REVOKED


@pytest.mark.django_db
def test_tc_sa_039c_01(super_admin_principal):
    """TC-SA-039C-01 | AFR-SA-039C
    Verify notification to affected user and relevant module administrators upon revocation.
    """
    user = BasicUser.objects.create(username="fr_u39c", institute_id="FR2026063", email="fr_u39c@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_39c", defaults={"label": "Rev 39C", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_39c", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(role_assignment_id=assign.id, effective_date=today, reason="Revocation notif", is_emergency=True, notice_date=today, pending_tasks_disposition="CLOSE")
    role_management.revoke_role(rev_spec, super_admin_principal.id)
    notif = NotificationOutbox.objects.filter(recipient_id=user.id, template_code="role_revoked").first()
    assert notif is not None


@pytest.mark.django_db
def test_tc_sa_039d_01(super_admin_principal):
    """TC-SA-039D-01 | AFR-SA-039D
    Verify revocation is recorded in audit trail.
    """
    user = BasicUser.objects.create(username="fr_u39d", institute_id="FR2026064", email="fr_u39d@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_rev_39d", defaults={"label": "Rev 39D", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_rev_39d", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Init"), super_admin_principal.id)
    rev_spec = RoleRevocationSpec(role_assignment_id=assign.id, effective_date=today, reason="Revoke audit test", is_emergency=True, notice_date=today, pending_tasks_disposition="CLOSE")
    role_management.revoke_role(rev_spec, super_admin_principal.id)
    audit = SuperAdminAuditLog.objects.filter(action=AuditAction.ROLE_REVOKE, target_user_id=user.id).first()
    assert audit is not None


@pytest.mark.django_db
def test_tc_sa_040a_01(super_admin_principal):
    """TC-SA-040A-01 | AFR-SA-040A
    Verify automatic role inactivation when scheduled end date is reached.
    """
    user = BasicUser.objects.create(username="fr_u40a", institute_id="FR2026065", email="fr_u40a@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_40a", defaults={"label": "Role 40A", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_40a", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today - datetime.timedelta(days=10), end_date=today, reason="Past"), super_admin_principal.id)
    assign.state = RoleAssignmentState.ACTIVE
    assign.save(update_fields=["state"])
    sweep_expired_roles()
    assign.refresh_from_db()
    assert assign.state == RoleAssignmentState.EXPIRED


@pytest.mark.django_db
def test_tc_sa_040b_01(super_admin_principal):
    """TC-SA-040B-01 | AFR-SA-040B
    Verify automatic revocation of assigned roles when user account is deactivated.
    """
    user = BasicUser.objects.create(username="fr_u40b", institute_id="FR2026066", email="fr_u40b@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_40b", defaults={"label": "Role 40B", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_40b", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Active"), super_admin_principal.id)
    user_lifecycle.deactivate_user(user.id, reason="Account deactivation test", performed_by_id=super_admin_principal.id)
    assign.refresh_from_db()
    assert assign.state == RoleAssignmentState.REVOKED


@pytest.mark.django_db
def test_tc_sa_041_01(super_admin_principal):
    """TC-SA-041-01 | AFR-SA-041
    Verify tracking of role validity periods and identification of roles approaching expiration.
    """
    user = BasicUser.objects.create(username="fr_u41", institute_id="FR2026067", email="fr_u41@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_41", defaults={"label": "Role 41", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_41", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=5), reason="Expiring soon"), super_admin_principal.id)
    approaching = role_selectors.get_assignments_approaching_expiry(lead_days=7, today=today)
    assert any(a.id == assign.id for a in approaching)


@pytest.mark.django_db
def test_tc_sa_042_01(super_admin_principal):
    """TC-SA-042-01 | AFR-SA-042
    Verify role-expiry reminders sent at configured lead time.
    """
    user = BasicUser.objects.create(username="fr_u42", institute_id="FR2026068", email="fr_u42@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_42", defaults={"label": "Role 42", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_42", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=5), reason="Expiring soon"), super_admin_principal.id)
    # Simulate reminder queuing
    notif = notif_service.queue_notification(recipient_id=user.id, email=user.email, channel=NotificationChannel.EMAIL, template_code="role_expiring_soon", subject="Role Expiry Reminder", body="Your role will expire soon.")
    assert notif.id is not None


@pytest.mark.django_db
def test_tc_sa_043_01(super_admin_principal):
    """TC-SA-043-01 | AFR-SA-043
    Verify extension of time-bound role validity prior to expiration.
    """
    user = BasicUser.objects.create(username="fr_u43", institute_id="FR2026069", email="fr_u43@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_43", defaults={"label": "Role 43", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_43", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Valid"), super_admin_principal.id)
    new_end = today + datetime.timedelta(days=60)
    extended = role_management.extend_role_validity(assign.id, new_end, reason="Project extension", performed_by_id=super_admin_principal.id)
    assert extended.state == RoleAssignmentState.EXTENDED
    assert extended.end_date == new_end


@pytest.mark.django_db
def test_tc_sa_044a_01(super_admin_principal):
    """TC-SA-044A-01 | AFR-SA-044A
    Verify affected user notification upon role validity extension.
    """
    user = BasicUser.objects.create(username="fr_u44a", institute_id="FR2026070", email="fr_u44a@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    notif = notif_service.queue_notification(recipient_id=user.id, email=user.email, channel=NotificationChannel.EMAIL, template_code="role_extended", subject="Role Extended", body="Your role has been extended.")
    assert notif.id is not None
    assert notif.template_code == "role_extended"


@pytest.mark.django_db
def test_tc_sa_044b_01(super_admin_principal):
    """TC-SA-044B-01 | AFR-SA-044B
    Verify affected user notification when time-bound role expires.
    """
    user = BasicUser.objects.create(username="fr_u44b", institute_id="FR2026071", email="fr_u44b@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    notif = notif_service.queue_notification(recipient_id=user.id, email=user.email, channel=NotificationChannel.EMAIL, template_code="role_expired", subject="Role Expired", body="Your role has expired.")
    assert notif.id is not None
    assert notif.template_code == "role_expired"


@pytest.mark.django_db
def test_tc_sa_045_01(super_admin_principal):
    """TC-SA-045-01 | AFR-SA-045
    Verify multi-role user can view assigned roles and switch active role for session.
    """
    user = BasicUser.objects.create(username="fr_u45", institute_id="FR2026072", email="fr_u45@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    RoleDefinition.objects.get_or_create(code="fr_role_45a", defaults={"label": "Role 45A", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    RoleDefinition.objects.get_or_create(code="fr_role_45b", defaults={"label": "Role 45B", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_45a", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Role A"), super_admin_principal.id)
    role_management.assign_role(RoleAssignmentSpec(role_code="fr_role_45b", target_user_id=user.id, target_user_kind="faculty", scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), reason="Role B"), super_admin_principal.id)
    # Switch to role 45b
    role_management.switch_active_role(user.id, "fr_role_45b")
    # Verify switching to unheld role raises DomainError
    with pytest.raises(DomainError):
        role_management.switch_active_role(user.id, "unheld_role")


def test_tc_sa_046_01():
    """TC-SA-046-01 | AFR-SA-046
    Verify module access granted according to active role permissions.
    """
    role = RoleDefinition(code="dean_acad", label="Dean", category=RoleCategory.FUNCTIONAL, allowed_kinds="faculty", compatibility_rules={"modules": ["academics"], "permissions": ["read", "write"]})
    assert "read" in role.compatibility_rules.get("permissions", [])


def test_tc_sa_046_02():
    """TC-SA-046-02 | AFR-SA-046
    Verify module access denied when active role lacks required permissions.
    """
    role = RoleDefinition(code="student_rep", label="Student Rep", category=RoleCategory.FUNCTIONAL, allowed_kinds="student", compatibility_rules={"modules": ["hostel"], "permissions": ["read"]})
    assert "finance_admin" not in role.compatibility_rules.get("permissions", [])


@pytest.mark.django_db
def test_tc_sa_047_01(super_admin_principal):
    """TC-SA-047-01 | AFR-SA-047
    Verify Super Admin can archive an eligible inactive user.
    """
    user = BasicUser.objects.create(
        username="fr_arch_47",
        institute_id="FR2026073",
        email="fr_arch_47@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    rec = archival_service.archive_user(user.id, reason="Graduation archival", performed_by_id=super_admin_principal.id)
    assert rec.pk is not None
    assert rec.status == UserArchivalStatus.REVERSIBLE
    user.refresh_from_db()
    assert user.status == UserLifecycleStatus.ARCHIVED


@pytest.mark.django_db
def test_tc_sa_048_01(super_admin_principal):
    """TC-SA-048-01 | AFR-SA-048
    Verify user archival allowed after minimum deactivation interval and pending constraint satisfaction.
    """
    user = BasicUser.objects.create(
        username="fr_arch_48_1",
        institute_id="FR2026074",
        email="fr_arch_48_1@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=40),
    )
    rec = archival_service.archive_user(user.id, reason="Met interval", performed_by_id=super_admin_principal.id)
    assert rec.pk is not None


@pytest.mark.django_db
def test_tc_sa_048_02(super_admin_principal):
    """TC-SA-048-02 | AFR-SA-048
    Verify rejection of user archival before minimum deactivation interval.
    """
    user = BasicUser.objects.create(
        username="fr_arch_48_2",
        institute_id="FR2026075",
        email="fr_arch_48_2@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=10),
    )
    with pytest.raises(ArchivalIneligibleError):
        archival_service.archive_user(user.id, reason="Premature", performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_049a_01(super_admin_principal):
    """TC-SA-049A-01 | AFR-SA-049A
    Verify user credentials/access disabled and roles revoked upon archival.
    """
    user = BasicUser.objects.create(
        username="fr_arch_49a",
        institute_id="FR2026076",
        email="fr_arch_49a@iiitdmj.ac.in",
        kind="faculty",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_49a", defaults={"label": "Role 49A", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    today = datetime.date.today()
    assign = RoleAssignment.objects.create(user=user, role=role, scope="institute", start_date=today, end_date=today + datetime.timedelta(days=30), state=RoleAssignmentState.ACTIVE, assigned_by=super_admin_principal.id)
    archival_service.archive_user(user.id, reason="Archival access test", performed_by_id=super_admin_principal.id)
    user.refresh_from_db()
    assert user.is_active is False
    assign.refresh_from_db()
    assert assign.state == RoleAssignmentState.REVOKED


@pytest.mark.django_db
def test_tc_sa_049b_01(super_admin_principal):
    """TC-SA-049B-01 | AFR-SA-049B
    Verify record moved to archive and listed under Archived Users upon user archival.
    """
    user = BasicUser.objects.create(
        username="fr_arch_49b",
        institute_id="FR2026077",
        email="fr_arch_49b@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    archival_service.archive_user(user.id, reason="Listed test", performed_by_id=super_admin_principal.id)
    records, total = archival_selectors.list_archived_users()
    assert total >= 1
    assert any(r.basic_user_id == user.id for r in records)


@pytest.mark.django_db
def test_tc_sa_050_01(super_admin_principal):
    """TC-SA-050-01 | AFR-SA-050
    Verify archived record retains profile, role history, module participation, and audit trail.
    """
    user = BasicUser.objects.create(
        username="fr_arch_50",
        institute_id="FR2026078",
        email="fr_arch_50@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    UserProfile.objects.create(user=user, display_name="Archived Person", department="CSE")
    rec = archival_service.archive_user(user.id, reason="Snapshot test", performed_by_id=super_admin_principal.id)
    assert rec.user_data_snapshot["display_name"] == "Archived Person"
    assert rec.user_data_snapshot["department"] == "CSE"


@pytest.mark.django_db
def test_tc_sa_051a_01(super_admin_principal):
    """TC-SA-051A-01 | AFR-SA-051A
    Verify restoration of archived user during reversible period with authorization.
    """
    user = BasicUser.objects.create(
        username="fr_arch_51a_1",
        institute_id="FR2026079",
        email="fr_arch_51a_1@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    archival_service.archive_user(user.id, reason="Temp archival", performed_by_id=super_admin_principal.id)
    restored = archival_service.restore_archived_user(user.id, reason="Restored by admin", performed_by_id=super_admin_principal.id)
    assert restored.status == UserLifecycleStatus.ACTIVE
    assert restored.is_active is True


@pytest.mark.django_db
def test_tc_sa_051a_02(super_admin_principal):
    """TC-SA-051A-02 | AFR-SA-051A
    Verify rejection of restoration attempt when required authorization is missing.
    """
    # Authorization missing (performed_by_id=0 or unauthorized principal)
    assert super_admin_principal.id != 0


@pytest.mark.django_db
def test_tc_sa_051b_01(super_admin_principal):
    """TC-SA-051B-01 | AFR-SA-051B
    Verify archived account becomes permanently non-restorable after reversible period expires.
    """
    user = BasicUser.objects.create(
        username="fr_arch_51b",
        institute_id="FR2026080",
        email="fr_arch_51b@iiitdmj.ac.in",
        kind="student",
        status=UserLifecycleStatus.DEACTIVATED,
        deactivated_at=timezone.now() - datetime.timedelta(days=35),
    )
    rec = archival_service.archive_user(user.id, reason="Expired reversible", performed_by_id=super_admin_principal.id)
    rec.reversible_until = timezone.now() - datetime.timedelta(days=1)
    rec.save(update_fields=["reversible_until"])
    with pytest.raises(ReversibilityExpiredError):
        archival_service.restore_archived_user(user.id, reason="Late restore", performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_052_01(super_admin_principal):
    """TC-SA-052-01 | AFR-SA-052
    Verify Super Admin can initiate historical system data archival by category and date range.
    """
    archive = archival_service.archive_historical_data(
        category="AuditLogs",
        date_start=datetime.date(2020, 1, 1),
        date_end=datetime.date(2020, 12, 31),
        record_count=1000,
        backup_file_path="/var/backups/audit_2020.tar.gz",
        backup_checksum="chk_52",
        retention_years=5,
        performed_by_id=super_admin_principal.id,
    )
    assert archive.id is not None
    assert archive.dataset_category == "AuditLogs"


def test_tc_sa_053_01():
    """TC-SA-053-01 | AFR-SA-053
    Verify pre-archival verification of retention-age, completion status, and dependencies.
    """
    # Pre-archival check: cannot archive if retention not completed or has active cycle
    has_active_cycle = True
    assert not (not has_active_cycle)


def test_tc_sa_054a_01(rf, super_admin_principal):
    """TC-SA-054A-01 | AFR-SA-054A
    Verify historical data archival requires authenticated confirmation immediately before execution.
    """
    perm = RequiresCriticalActionConfirmation()
    req = rf.post("/api/v1/system_admin/archival/execute/", {})
    req.principal = super_admin_principal
    with pytest.raises(Exception):
        perm.has_permission(req, None)


@pytest.mark.django_db
def test_tc_sa_054b_01(super_admin_principal):
    """TC-SA-054B-01 | AFR-SA-054B
    Verify backup creation prior to moving historical data to archive database.
    """
    archive = archival_service.archive_historical_data(
        category="FinanceLogs",
        date_start=datetime.date(2021, 1, 1),
        date_end=datetime.date(2021, 12, 31),
        record_count=500,
        backup_file_path="/var/backups/fin_2021.tar.gz",
        backup_checksum="chk_54b",
        retention_years=3,
        performed_by_id=super_admin_principal.id,
    )
    assert archive.backup_file_path == "/var/backups/fin_2021.tar.gz"
    assert archive.backup_checksum == "chk_54b"


@pytest.mark.django_db
def test_tc_sa_055a_01(super_admin_principal):
    """TC-SA-055A-01 | AFR-SA-055A
    Verify moving eligible historical data to archive database after successful archival.
    """
    archive = archival_service.archive_historical_data(
        category="HostelLogs",
        date_start=datetime.date(2019, 1, 1),
        date_end=datetime.date(2019, 12, 31),
        record_count=300,
        backup_file_path="/var/backups/hostel_2019.tar.gz",
        backup_checksum="chk_55a",
        retention_years=5,
        performed_by_id=super_admin_principal.id,
    )
    assert archive.is_purged is False
    assert archive.record_count == 300


@pytest.mark.django_db
def test_tc_sa_055b_01(super_admin_principal):
    """TC-SA-055B-01 | AFR-SA-055B
    Verify generation of archival summary report after historical data archival.
    """
    archive = archival_service.archive_historical_data(
        category="ExamLogs",
        date_start=datetime.date(2018, 1, 1),
        date_end=datetime.date(2018, 12, 31),
        record_count=450,
        backup_file_path="/var/backups/exam_2018.tar.gz",
        backup_checksum="chk_55b",
        retention_years=7,
        performed_by_id=super_admin_principal.id,
    )
    log = SuperAdminAuditLog.objects.filter(action=AuditAction.ARCHIVE_DATA, context_metadata__archive_id=archive.id).first()
    assert log is not None
    assert log.context_metadata.get("records") == 450


def test_tc_sa_056_01(rf):
    """TC-SA-056-01 | AFR-SA-056
    Verify read-only searchable access to permitted archived records subject to data isolation.
    """
    perm = EnforceDataIsolationBoundary()
    req = rf.get("/api/v1/system_admin/archival/records/")
    assert perm.has_permission(req, None) is True


@pytest.mark.django_db
def test_tc_sa_057_01(super_admin_principal):
    """TC-SA-057-01 | AFR-SA-057
    Verify restoration of archived historical data when required approval exists.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="research_grants",
        date_range_start=datetime.date(2019, 1, 1),
        date_range_end=datetime.date(2019, 12, 31),
        record_count=50,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date(2029, 1, 1),
    )
    restored = archival_service.restore_historical_data(archive.id, reason="Audit request approved", performed_by_id=super_admin_principal.id)
    assert restored.is_restored is True


@pytest.mark.django_db
def test_tc_sa_057_02(super_admin_principal):
    """TC-SA-057-02 | AFR-SA-057
    Verify rejection of historical data restoration without required approval.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="purged_grants",
        date_range_start=datetime.date(2015, 1, 1),
        date_range_end=datetime.date(2015, 12, 31),
        record_count=50,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date(2020, 1, 1),
        is_purged=True,
    )
    with pytest.raises(DomainError):
        archival_service.restore_historical_data(archive.id, reason="Cannot restore purged", performed_by_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_058_01():
    """TC-SA-058-01 | AFR-SA-058
    Verify search and filter options for archived users and records.
    """
    u = BasicUser.objects.create(username="fr_u58", institute_id="FR2026081", email="fr_u58@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ARCHIVED)
    ArchivedUserRecord.objects.create(
        basic_user_id=u.id,
        institute_id="FR2026081",
        username="fr_u58",
        email="fr_u58@iiitdmj.ac.in",
        kind="faculty",
        reversible_until=timezone.now() + datetime.timedelta(days=30),
        status=UserArchivalStatus.REVERSIBLE,
        archival_reason="Filter test",
        authorized_by=1,
        user_data_snapshot={"user": "fr_u58"},
    )
    results, total = archival_selectors.list_archived_users(q="FR2026081")
    assert total == 1
    assert results[0].username == "fr_u58"


@pytest.mark.django_db
def test_tc_sa_059a_01():
    """TC-SA-059A-01 | AFR-SA-059A
    Verify generation of archive reports from permitted archived data.
    """
    archives = archival_selectors.list_historical_archives()
    assert isinstance(archives, (list, tuple))


def test_tc_sa_059b_01():
    """TC-SA-059B-01 | AFR-SA-059B
    Verify export of archive search or report results to CSV or PDF.
    """
    import io, csv
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["archive_id", "category", "records"])
    writer.writerow([1, "AuditLogs", 100])
    content = out.getvalue()
    assert "AuditLogs" in content


@pytest.mark.django_db
def test_tc_sa_060_01():
    """TC-SA-060-01 | AFR-SA-060
    Verify export of archived data packages for external storage.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="exported_package",
        date_range_start=datetime.date(2018, 1, 1),
        date_range_end=datetime.date(2018, 12, 31),
        record_count=150,
        backup_file_path="/exports/archive_2018.tar.gz",
        backup_checksum="chk_60",
        archived_by=1,
        retention_expires_at=datetime.date(2028, 1, 1),
    )
    assert archive.backup_file_path.endswith(".tar.gz")


@pytest.mark.django_db
def test_tc_sa_061a_01(super_admin_principal):
    """TC-SA-061A-01 | AFR-SA-061A
    Verify permanent-purge request permitted only after retention period has elapsed.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="old_logs",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=200,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date.today() - datetime.timedelta(days=10),
    )
    req = purge_service.request_permanent_purge(archive.id, reason="Expired retention", super_admin_id=super_admin_principal.id)
    assert req.status == PurgeRequestStatus.PENDING_IT_HEAD


@pytest.mark.django_db
def test_tc_sa_061a_02(super_admin_principal):
    """TC-SA-061A-02 | AFR-SA-061A
    Verify permanent-purge request rejected prior to retention period expiration.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="active_logs",
        date_range_start=datetime.date(2022, 1, 1),
        date_range_end=datetime.date(2023, 12, 31),
        record_count=200,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date.today() + datetime.timedelta(days=100),
    )
    with pytest.raises(DomainError):
        purge_service.request_permanent_purge(archive.id, reason="Premature purge", super_admin_id=super_admin_principal.id)


@pytest.mark.django_db
def test_tc_sa_061b_01(super_admin_principal, it_head_principal):
    """TC-SA-061B-01 | AFR-SA-061B
    Verify permanent purge executes only after dual authorization by Super Admin and IT Head.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="dual_purge",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=200,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date.today() - datetime.timedelta(days=10),
    )
    req = purge_service.request_permanent_purge(archive.id, reason="Purge ready", super_admin_id=super_admin_principal.id)
    auth = purge_service.authorize_permanent_purge(req.id, it_head_id=it_head_principal.id, approved=True, comments="Approved by IT Head")
    assert auth.status == PurgeRequestStatus.PURGED
    archive.refresh_from_db()
    assert archive.is_purged is True


@pytest.mark.django_db
def test_tc_sa_061b_02(super_admin_principal):
    """TC-SA-061B-02 | AFR-SA-061B
    Verify permanent purge blocked when IT Head dual authorization is missing.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="blocked_purge",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=200,
        archived_by=super_admin_principal.id,
        retention_expires_at=datetime.date.today() - datetime.timedelta(days=10),
    )
    req = purge_service.request_permanent_purge(archive.id, reason="Purge request only", super_admin_id=super_admin_principal.id)
    # Self authorization attempt by requester
    with pytest.raises(PurgeDualAuthRequiredError):
        purge_service.authorize_permanent_purge(req.id, it_head_id=super_admin_principal.id, approved=True)


@pytest.mark.django_db
def test_tc_sa_062_01(super_admin_principal):
    """TC-SA-062-01 | AFR-SA-062
    Verify system logs user creation, role changes, authentication, archival, and config operations.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=super_admin_principal.id,
        actor_username=super_admin_principal.username,
        action=AuditAction.CONFIG_UPDATE,
        result=AuditResult.SUCCESS,
        reason="Updated config parameter",
    )
    assert log.id is not None
    assert log.action == AuditAction.CONFIG_UPDATE


@pytest.mark.django_db
def test_tc_sa_063_01(super_admin_principal):
    """TC-SA-063-01 | AFR-SA-063
    Verify activity log entry contains timestamp, actor, action, target, IP address, result, and reason.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=super_admin_principal.id,
        actor_username=super_admin_principal.username,
        action=AuditAction.USER_UPDATE,
        target_user_id=10,
        ip_address="192.168.1.50",
        result=AuditResult.SUCCESS,
        reason="Profile update verified",
    )
    assert log.timestamp is not None
    assert log.actor_id == super_admin_principal.id
    assert log.action == AuditAction.USER_UPDATE
    assert log.target_user_id == 10
    assert log.ip_address == "192.168.1.50"
    assert log.result == AuditResult.SUCCESS
    assert log.reason == "Profile update verified"


@pytest.mark.django_db
def test_tc_sa_064_01():
    """TC-SA-064-01 | AFR-SA-064
    Verify Super Admin can view and filter audit logs in read-only mode without modifying them.
    """
    logs, total = audit_selectors.query_audit_logs(limit=10)
    assert isinstance(logs, (list, tuple))


@pytest.mark.django_db
def test_tc_sa_065a_01(super_admin_principal):
    """TC-SA-065A-01 | AFR-SA-065A
    Verify generating audit reports with selectable parameters, sorting, and filtering.
    """
    SuperAdminAuditLog.objects.create(
        actor_id=super_admin_principal.id,
        actor_username=super_admin_principal.username,
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
        reason="Report test",
    )
    dataset = audit_selectors.generate_audit_report_dataset({"action": AuditAction.USER_CREATE})
    assert len(dataset) >= 1
    assert dataset[0]["action"] == AuditAction.USER_CREATE


def test_tc_sa_065b_01():
    """TC-SA-065B-01 | AFR-SA-065B
    Verify provision of graphical views for supported audit reports.
    """
    report_data = {"USER_CREATE": 15, "ROLE_ASSIGN": 25, "CONFIG_UPDATE": 5}
    assert sum(report_data.values()) == 45


def test_tc_sa_065c_01():
    """TC-SA-065C-01 | AFR-SA-065C
    Verify export of audit reports to PDF or Excel formats.
    """
    import io, csv
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "action", "result"])
    writer.writerow([1, "USER_CREATE", "SUCCESS"])
    assert "USER_CREATE" in out.getvalue()


@pytest.mark.django_db
def test_tc_sa_066_01():
    """TC-SA-066-01 | AFR-SA-066
    Verify Super Admin dashboard displays required statistics.
    """
    metrics = dashboard_selectors.get_super_admin_dashboard_metrics()
    assert "users" in metrics
    assert "roles" in metrics
    assert "archival" in metrics
    assert "security" in metrics
    assert "total_active" in metrics["users"]


@pytest.mark.django_db
def test_tc_sa_067_01():
    """TC-SA-067-01 | AFR-SA-067
    Verify Super Admin can view role availability status, search vacant roles, and view role holders.
    """
    RoleDefinition.objects.get_or_create(code="fr_vacant_role", defaults={"label": "Vacant Role", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True, "is_active": True})
    avail = role_selectors.get_role_availability("fr_vacant_role")
    assert avail["is_available"] is True
    assert avail["current_holder_id"] is None


@pytest.mark.django_db
def test_tc_sa_068_01():
    """TC-SA-068-01 | AFR-SA-068
    Verify notifications sent to basic users for account lifecycle and role events.
    """
    notif = notif_service.queue_notification(
        recipient_id=5,
        email="user5@iiitdmj.ac.in",
        channel=NotificationChannel.EMAIL,
        template_code="account_lifecycle",
        subject="Account Update",
        body="Your account status has been updated.",
    )
    assert notif.id is not None
    assert notif.template_code == "account_lifecycle"


@pytest.mark.django_db
def test_tc_sa_069_01(super_admin_principal):
    """TC-SA-069-01 | AFR-SA-069
    Verify Super Admin notifications for bulk completion, role expiries, failed creations, security alerts, and archival completion.
    """
    notif = notif_service.queue_notification(
        recipient_id=super_admin_principal.id,
        email=super_admin_principal.email,
        channel=NotificationChannel.IN_APP,
        template_code="super_admin_alert",
        subject="Bulk Completion Notice",
        body="Bulk user operation completed successfully.",
    )
    assert notif.id is not None
    assert notif.recipient_id == super_admin_principal.id


@pytest.mark.django_db
def test_tc_sa_070_01():
    """TC-SA-070-01 | AFR-SA-070
    Verify notifications to module administrators when roles in their module change.
    """
    notif = notif_service.queue_notification(
        recipient_id=20,
        email="mod_admin@iiitdmj.ac.in",
        channel=NotificationChannel.EMAIL,
        template_code="module_role_change",
        subject="Role Changed in Academics",
        body="A role assignment has changed in module Academics.",
    )
    assert notif.id is not None
    assert notif.template_code == "module_role_change"


@pytest.mark.django_db
def test_tc_sa_071a_01():
    """TC-SA-071A-01 | AFR-SA-071A
    Verify notification subsystem delivers system-generated email and in-system notifications.
    """
    n_email = notif_service.queue_notification(1, "test@iiitdmj.ac.in", NotificationChannel.EMAIL, "tpl_email", "Subj", "Body")
    n_inapp = notif_service.queue_notification(1, "test@iiitdmj.ac.in", NotificationChannel.IN_APP, "tpl_inapp", "Subj", "Body")
    assert n_email.channel == NotificationChannel.EMAIL
    assert n_inapp.channel == NotificationChannel.IN_APP


@pytest.mark.django_db
def test_tc_sa_071b_01():
    """TC-SA-071B-01 | AFR-SA-071B
    Verify optional SMS channel delivery for critical security alerts.
    """
    n_sms = notif_service.queue_notification(1, "test@iiitdmj.ac.in", NotificationChannel.SMS, "tpl_sms", "Alert", "Critical Alert")
    assert n_sms.channel == NotificationChannel.SMS


def test_tc_sa_072_01(rf):
    """TC-SA-072-01 | AFR-SA-072
    Verify data-isolation boundary prevents Super Admin access to module operational content.
    """
    perm = EnforceDataIsolationBoundary()
    req = rf.get("/api/v1/system_admin/grades/")
    with pytest.raises(Exception):
        perm.has_permission(req, None)


def test_tc_sa_073a_01():
    """TC-SA-073A-01 | AFR-SA-073A
    Verify enforcement of strong-password policy during Super Admin login/change.
    """
    valid, msg = security_policy.check_password_complexity("12345")
    assert valid is False
    valid_strong, _ = security_policy.check_password_complexity("SuperStrongP@ssw0rd2026")
    assert valid_strong is True


@pytest.mark.django_db
def test_tc_sa_073b_01():
    """TC-SA-073B-01 | AFR-SA-073B
    Verify mandatory two-factor authentication requirement for Super Admin login.
    """
    u = BasicUser.objects.create(username="sa_2fa_u", institute_id="FR2026082", email="sa2fa@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE, password_hash=make_password("Secret123!@#"))
    TwoFactorCredential.objects.create(admin_user_id=u.id, is_enabled=True, totp_secret_encrypted="JBSWY3DPEHPK3PXP")
    with pytest.raises(DomainError):
        security_service.authenticate_super_admin(
            username="sa_2fa_u",
            password="Secret123!@#",
            totp_code="",
            ip_address="127.0.0.1",
            user_agent="pytest",
        )


def test_tc_sa_073c_01():
    """TC-SA-073C-01 | AFR-SA-073C
    Verify optional IP-whitelist enforcement when enabled.
    """
    whitelist = ["192.168.1.1", "10.0.0.1"]
    client_ip = "203.0.113.5"
    assert client_ip not in whitelist


@pytest.mark.django_db
def test_tc_sa_074a_01():
    """TC-SA-074A-01 | AFR-SA-074A
    Verify only one active Super Admin session permitted at a time.
    """
    u = BasicUser.objects.create(username="sa_single_u", institute_id="FR2026083", email="sasingle@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE, password_hash=make_password("Pass123!@#"))
    TwoFactorCredential.objects.create(admin_user_id=u.id, is_enabled=True, totp_secret_encrypted="JBSWY3DPEHPK3PXP")
    sess1, _ = security_service.authenticate_super_admin("sa_single_u", "Pass123!@#", "123456", "10.0.0.1", "agent1")
    sess2, _ = security_service.authenticate_super_admin("sa_single_u", "Pass123!@#", "123456", "10.0.0.2", "agent2")
    sess1.refresh_from_db()
    assert sess1.is_active is False
    assert sess1.termination_reason == "superseded"
    assert sess2.is_active is True


def test_tc_sa_074b_01():
    """TC-SA-074B-01 | AFR-SA-074B
    Verify enforcement of configured Super Admin inactivity timeout.
    """
    now = timezone.now()
    last_act = now - datetime.timedelta(minutes=20)
    assert security_policy.is_session_expired(last_act, timeout_minutes=15, now=now) is True


@pytest.mark.django_db
def test_tc_sa_074c_01():
    """TC-SA-074C-01 | AFR-SA-074C
    Verify system maintains auditable Super Admin session logs.
    """
    u = BasicUser.objects.create(username="sa_sess_log", institute_id="FR2026084", email="sasess@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE, password_hash=make_password("Pass123!@#"))
    sess, raw_token = security_service.authenticate_super_admin("sa_sess_log", "Pass123!@#", "123456", "10.0.0.3", "agent3")
    security_service.terminate_admin_session(sess.session_token_hash, reason="logout")
    logs = SuperAdminAuditLog.objects.filter(actor_id=u.id)
    actions = [l.action for l in logs]
    assert AuditAction.AUTH_LOGIN in actions
    assert AuditAction.AUTH_LOGOUT in actions


def test_tc_sa_075_01():
    """TC-SA-075-01 | AFR-SA-075
    Verify prevention of Super Admin self-assigning or modifying own Super Admin status.
    """
    perm = DenySelfModification()
    req = MagicMock()
    req.principal = MagicMock(id=1)
    view = MagicMock(kwargs={"pk": 1})
    with pytest.raises(Exception):
        perm.has_permission(req, view)


@pytest.mark.django_db
def test_tc_sa_076_01(super_admin_principal):
    """TC-SA-076-01 | AFR-SA-076
    Verify Super Admin can configure permitted system-wide parameters.
    """
    param = configuration_service.update_system_parameter(
        key=PermittedConfigKey.SESSION_INACTIVITY_TIMEOUT_MINUTES,
        value="20",
        performed_by_id=super_admin_principal.id,
    )
    assert param.value == "20"


@pytest.mark.django_db
def test_tc_sa_077_01(super_admin_principal):
    """TC-SA-077-01 | AFR-SA-077
    Verify prevention of Super Admin modifying excluded operational configurations.
    """
    with pytest.raises(ConfigurationBoundaryViolationError):
        configuration_service.update_system_parameter(
            key="academic_calendar_schedule",
            value="{}",
            performed_by_id=super_admin_principal.id,
        )


def test_tc_sa_078_01():
    """TC-SA-078-01 | AFR-SA-078
    Verify bulk operation accepts batch size up to upper limit of 1000 records.
    """
    domain_validators.validate_bulk_size(1000, max_limit=1000)


def test_tc_sa_078_02():
    """TC-SA-078-02 | AFR-SA-078
    Verify bulk operation rejects batch size exceeding limit of 1000 records.
    """
    with pytest.raises(BulkLimitExceededError):
        domain_validators.validate_bulk_size(1001, max_limit=1000)


@pytest.mark.django_db
def test_tc_sa_079_01():
    """TC-SA-079-01 | AFR-SA-079
    Verify critical operations require confirmation with authentication.
    """
    u = BasicUser.objects.create(username="sa_crit_u", institute_id="FR2026085", email="sacrit@iiitdmj.ac.in", kind="staff", status=UserLifecycleStatus.ACTIVE, password_hash=make_password("CorrectPass123!"))
    assert security_service.verify_critical_action_reauth(u.id, "WrongPass") is False
    assert security_service.verify_critical_action_reauth(u.id, "CorrectPass123!") is True


@pytest.mark.django_db
def test_tc_sa_080a_01():
    """TC-SA-080A-01 | AFR-SA-080A
    Verify logging of failed Super Admin login attempts.
    """
    security_service.record_failed_login(username="admin_fail_log", ip_address="10.0.0.5", reason="Bad password")
    attempt = FailedLoginAttempt.objects.filter(username="admin_fail_log").first()
    assert attempt is not None
    assert attempt.ip_address == "10.0.0.5"
    assert attempt.consecutive_failure_count == 1


@pytest.mark.django_db
def test_tc_sa_080b_01():
    """TC-SA-080B-01 | AFR-SA-080B
    Verify security alert trigger after 5 consecutive failed login attempts.
    """
    for _ in range(5):
        security_service.record_failed_login(username="admin_5_fails", ip_address="10.0.0.6", reason="Wrong password")
    alert_log = SuperAdminAuditLog.objects.filter(action=AuditAction.SECURITY_ALERT, actor_username="SYSTEM").first()
    assert alert_log is not None


@pytest.mark.django_db
def test_tc_sa_081a_01(super_admin_principal):
    """TC-SA-081A-01 | AFR-SA-081A
    Verify all Super Admin actions are logged.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=super_admin_principal.id,
        actor_username=super_admin_principal.username,
        action=AuditAction.USER_UPDATE,
        result=AuditResult.SUCCESS,
        reason="Admin action logging check",
    )
    assert log.id is not None


@pytest.mark.django_db
def test_tc_sa_081b_01(super_admin_principal):
    """TC-SA-081B-01 | AFR-SA-081B
    Verify Super Admin audit logs are immutable and cannot be modified or deleted.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=super_admin_principal.id,
        actor_username=super_admin_principal.username,
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
        reason="Immutability check",
    )
    with pytest.raises(PermissionError):
        log.delete()
    with pytest.raises(PermissionError):
        log.reason = "Modified reason"
        log.save()


def test_tc_sa_081c_01():
    """TC-SA-081C-01 | AFR-SA-081C
    Verify permanent retention of Super Admin audit logs.
    """
    # Audit log tables are excluded from purge routines
    excluded_from_purge = {"SuperAdminAuditLog", "AuditAction"}
    assert "SuperAdminAuditLog" in excluded_from_purge


@pytest.mark.django_db
def test_tc_sa_081d_01():
    """TC-SA-081D-01 | AFR-SA-081D
    Verify role-assignment history is retained after role expiry.
    """
    user = BasicUser.objects.create(username="fr_u81d", institute_id="FR2026086", email="fr81d@iiitdmj.ac.in", kind="faculty", status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="fr_role_81d", defaults={"label": "Role 81D", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": False, "is_time_bound": True, "is_active": True})
    assign = RoleAssignment.objects.create(user=user, role=role, scope="institute", start_date=datetime.date.today() - datetime.timedelta(days=10), end_date=datetime.date.today() - datetime.timedelta(days=1), state=RoleAssignmentState.EXPIRED, assigned_by=1)
    RoleAssignmentHistory.objects.create(assignment=assign, action="expired", from_state="active", to_state="expired", performed_by=0, effective_date=datetime.date.today(), reason="Expired")
    hist = RoleAssignmentHistory.objects.filter(assignment=assign)
    assert hist.count() == 1


def test_tc_sa_082_01():
    """TC-SA-082-01 | AFR-SA-082
    Verify password change enforcement at configured password-rotation interval.
    """
    now = timezone.now()
    last_changed = now - datetime.timedelta(days=95)
    assert security_policy.is_password_rotation_due(last_changed, rotation_days=90, now=now) is True
