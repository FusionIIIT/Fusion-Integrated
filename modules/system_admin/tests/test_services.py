"""Services integration tests: transactional workflows and domain enforcement."""
from datetime import date, timedelta

import pytest

from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    DuplicateUserError,
    PurgeDualAuthError,
    SingularRoleOccupancyError,
)
from modules.system_admin.models.archive import ArchivedUserRecord
from modules.system_admin.models.audit import SystemAuditLog
from modules.system_admin.models.configuration import SystemParameter
from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount
from modules.system_admin.services.archive_service import (
    archive_user,
    authorize_permanent_purge,
    request_permanent_purge,
    restore_archived_user,
)
from modules.system_admin.services.audit_service import (
    record_admin_session,
    record_audit_event,
    record_failed_login,
)
from modules.system_admin.services.configuration_service import update_system_parameters
from modules.system_admin.services.role_service import (
    assign_role,
    extend_role_validity,
    process_role_expiries,
    reassign_role,
    revoke_role,
)
from modules.system_admin.services.user_service import (
    bulk_create_users,
    create_basic_user,
    deactivate_user,
    reactivate_user,
    update_user_profile,
)

pytestmark = pytest.mark.django_db


# ---- User Service Tests ----
def test_create_basic_user_success():
    user = create_basic_user(
        institute_id="2024BCS101",
        username="ranjith_test",
        email="ranjith.test@iiitdmj.ac.in",
        user_type="student",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2024,
        name="Ranjith Test",
        actor_id=1,
    )
    assert user.user_id is not None
    assert user.status == "active"
    assert UserAccount.objects.filter(username="ranjith_test").exists()

    # Check audit log
    audit = SystemAuditLog.objects.filter(target_id=str(user.user_id)).first()
    assert audit is not None
    assert audit.action == "system_admin.user.add"


def test_create_user_duplicate_rejected():
    create_basic_user(
        institute_id="2024BCS102",
        username="dup_user",
        email="dup@iiitdmj.ac.in",
        user_type="student",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2024,
    )
    with pytest.raises(DuplicateUserError):
        create_basic_user(
            institute_id="2024BCS102",
            username="other_username",
            email="other@iiitdmj.ac.in",
            user_type="student",
            programme="B.Tech",
            discipline="CSE",
            batch_year=2024,
        )


def test_update_user_profile_immutable_institute_id():
    user = create_basic_user(
        institute_id="FAC999",
        username="prof_immut",
        email="prof@iiitdmj.ac.in",
        user_type="faculty",
        department="ECE",
    )
    # Valid update
    updated = update_user_profile(user_id=user.user_id, data={"name": "Prof Updated"})
    assert updated.name == "Prof Updated"

    # Attempt to change institute_id
    with pytest.raises(DomainValidationError, match="immutable and cannot be modified"):
        update_user_profile(user_id=user.user_id, data={"institute_id": "NEW_FAC999"})


def test_deactivate_and_reactivate_user():
    user = create_basic_user(
        institute_id="2024BCS103",
        username="lifecycle_user",
        email="life@iiitdmj.ac.in",
        user_type="student",
        programme="B.Tech",
        discipline="ME",
        batch_year=2024,
    )
    # Deactivate
    deactivated = deactivate_user(user_id=user.user_id, reason="Graduation")
    assert deactivated.status == "deactivated"
    assert deactivated.deactivated_at is not None

    # Reactivate
    reactivated = reactivate_user(user_id=user.user_id, reason="Enrolled in M.Tech")
    assert reactivated.status == "active"
    assert reactivated.deactivated_at is None


def test_bulk_create_users():
    records = [
        {
            "institute_id": f"2024BCS20{i}",
            "username": f"bulk_user_{i}",
            "email": f"bulk{i}@iiitdmj.ac.in",
            "user_type": "student",
            "programme": "B.Tech",
            "discipline": "CSE",
            "batch_year": 2024,
        }
        for i in range(5)
    ]
    res = bulk_create_users(rows=records)
    assert res["created_count"] == 5
    assert res["error_count"] == 0


# ---- Role Service Tests ----
def test_assign_role_immediate_and_singular():
    user = create_basic_user(
        institute_id="FAC201",
        username="hod_candidate",
        email="hod.cand@iiitdmj.ac.in",
        user_type="faculty",
        department="CSE",
    )
    today = date.today()
    assignment = assign_role(
        role_code="hod_cse",
        user_id=user.user_id,
        start_date=today,
        end_date=today + timedelta(days=365),
        is_singular=True,
        reason="Appointed HOD",
    )
    assert assignment.status == "active"

    # Attempt second singular holder
    user2 = create_basic_user(
        institute_id="FAC202",
        username="hod_candidate2",
        email="hod.cand2@iiitdmj.ac.in",
        user_type="faculty",
        department="CSE",
    )
    with pytest.raises(SingularRoleOccupancyError):
        assign_role(
            role_code="hod_cse",
            user_id=user2.user_id,
            start_date=today,
            end_date=today + timedelta(days=365),
            is_singular=True,
            reason="Second HOD appointment attempt",
        )


def test_reassign_role():
    today = date.today()
    u1 = create_basic_user(
        institute_id="FAC203", username="u1", email="u1@iiitdmj.ac.in", user_type="faculty", department="CSE"
    )
    u2 = create_basic_user(
        institute_id="FAC204", username="u2", email="u2@iiitdmj.ac.in", user_type="faculty", department="CSE"
    )
    role = assign_role(
        role_code="dean_students",
        user_id=u1.user_id,
        start_date=today,
        end_date=today + timedelta(days=365),
        is_singular=True,
        reason="Initial appointment",
    )

    old_r, new_r = reassign_role(
        role_assignment_id=role.id,
        new_user_id=u2.user_id,
        effective_date=today,
        reason="Transfer of duties",
    )
    assert old_r.status == "revoked"
    assert new_r.status == "active"
    assert new_r.user_id == u2.user_id


def test_revoke_and_extend_role():
    today = date.today()
    user = create_basic_user(
        institute_id="STF101", username="stf1", email="stf1@iiitdmj.ac.in", user_type="staff", department="Admin"
    )
    role = assign_role(
        role_code="internal_auditor",
        user_id=user.user_id,
        start_date=today,
        end_date=today + timedelta(days=180),
        reason="Audit duty",
    )
    # Extend
    extended = extend_role_validity(
        role_assignment_id=role.id,
        new_end_date=today + timedelta(days=360),
        reason="Extension approved",
    )
    assert extended.end_date == today + timedelta(days=360)

    # Revoke
    revoked = revoke_role(role_assignment_id=role.id, reason="Completed assignment")
    assert revoked.status == "revoked"


def test_process_role_expiries():
    yesterday = date.today() - timedelta(days=1)
    user = create_basic_user(
        institute_id="STU555", username="stu555", email="stu555@iiitdmj.ac.in", user_type="student", programme="B.Tech", discipline="CSE", batch_year=2024
    )
    RoleAssignment.objects.create(
        role_code="club_coordinator",
        user_id=user.user_id,
        status="active",
        start_date=yesterday - timedelta(days=100),
        end_date=yesterday,
        assigned_by=1,
    )
    count = process_role_expiries()
    assert count >= 1
    expired = RoleAssignment.objects.filter(user_id=user.user_id).first()
    assert expired.status == "expired"


# ---- Archival and Purge Tests ----
def test_archive_and_restore_user():
    user = create_basic_user(
        institute_id="2024BCS901",
        username="arch_user",
        email="arch@iiitdmj.ac.in",
        user_type="student",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2024,
    )
    deactivate_user(user_id=user.user_id, reason="Withdrawn")

    # Archive
    arch_record = archive_user(user_id=user.user_id, reason="Completed degree")
    assert arch_record.user_id == user.user_id
    user.refresh_from_db()
    assert user.status == "archived"

    # Restore
    restored = restore_archived_user(user_id=user.user_id, reason="Readmitted")
    assert restored.status == "active"
    assert not ArchivedUserRecord.objects.filter(user_id=user.user_id).exists()


def test_dual_auth_purge_flow():
    # Step 1: Request purge
    purge_req = request_permanent_purge(
        dataset_identifier="students_batch_2015",
        retention_years=8.0,
        reason="Retention period of 7 years elapsed",
        actor_id=1,
    )
    assert purge_req.status == "pending_it_head"

    # Step 2: Same actor cannot authorize (Dual Auth Violation)
    with pytest.raises(PurgeDualAuthError, match="Dual authorization violation"):
        authorize_permanent_purge(
            purge_request_id=purge_req.id,
            approve=True,
            it_head_user_id=1,  # Same as requested_by!
        )

    # Legitimate authorization by IT Head (user_id=99)
    authorized = authorize_permanent_purge(
        purge_request_id=purge_req.id,
        approve=True,
        it_head_user_id=99,
        remarks="Approved after verification",
    )
    assert authorized.status == "purged"
    assert authorized.it_head_user_id == 99


# ---- Configuration and Audit Tests ----
def test_update_system_parameters_and_audit():
    params = {
        "max_login_attempts": "5",
        "session_timeout_minutes": "45",
        "password_min_length": "12",
    }
    updated = update_system_parameters(params=params, actor_id=1)
    assert updated["max_login_attempts"] == "5"

    param_obj = SystemParameter.objects.get(key="max_login_attempts")
    assert param_obj.value == "5"

    # Audit log check
    audit = SystemAuditLog.objects.filter(action="system_admin.config.change").first()
    assert audit is not None


def test_audit_service_records():
    evt = record_audit_event(
        actor_id=10,
        action="test.service.event",
        target_id="target-10",
        ip_address="127.0.0.1",
        result="success",
        context={"k": "v"},
    )
    assert evt.id is not None
    assert evt.action == "test.service.event"

    fail = record_failed_login(
        username="attacker",
        ip_address="127.0.0.1",
        reason="Bad pwd",
    )
    assert fail.id is not None
    assert fail.username == "attacker"

    sess = record_admin_session(
        user_id=10,
        session_key="sess-test-key-12345",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    assert sess.id is not None
    assert sess.is_active is True
