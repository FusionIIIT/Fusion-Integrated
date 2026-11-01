"""Integration and service tests for System Admin module.

Tests all service operations and database invariants.
"""
from datetime import date, datetime, timedelta
from django.test import TestCase
from django.utils import timezone

from modules.system_admin.domain import (
    ArchivedUserPermanentError,
    AuditLogArchivalProhibitedError,
    BasicUserType,
    BulkLimitExceededError,
    DuplicateInstituteIdError,
    InstituteIdImmutableError,
    InvalidNoticePeriodError,
    InvalidRoleDatesError,
    PermittedConfigBoundaryError,
    PurgeRetentionNotElapsedError,
    RoleConflictError,
    RoleIncompatibleUserTypeError,
    SingularRoleOccupancyError,
    SuperAdminSelfModificationForbiddenError,
    UserArchivalIneligibleError,
)
from modules.system_admin.models import (
    ArchivedRecord,
    AuditLog,
    BasicUser,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
    SuperAdminSession,
    SystemConfiguration,
)
from modules.system_admin.services import (
    activate_scheduled_roles,
    archive_historical_data,
    archive_user,
    assign_role,
    authenticate_super_admin,
    authorize_permanent_purge,
    bulk_create_users,
    bulk_status_update,
    create_basic_user,
    deactivate_user,
    reactivate_user,
    expire_time_bound_roles,
    extend_role_validity,
    finalize_non_restorable_archived_users,
    get_all_configurations,
    reassign_role,
    record_audit_event,
    record_failed_login,
    request_permanent_purge,
    restore_archived_user,
    restore_historical_data,
    revoke_role,
    send_role_expiry_reminders,
    switch_active_role,
    terminate_session,
    update_configuration,
    update_user_profile,
)


class SystemAdminServiceTests(TestCase):

    def setUp(self):
        # Create standard test roles
        self.role_placement = RoleDefinition.objects.create(
            code="placement_coordinator",
            name="Placement Coordinator",
            module_association="placement_cell",
            allowed_user_types=["student", "faculty"],
            is_singular=False,
            default_validity_days=365,
            permissions=["placement_cell.job_posting.view"],
        )
        self.role_dean = RoleDefinition.objects.create(
            code="dean_academics",
            name="Dean of Academic Affairs",
            module_association="academics",
            allowed_user_types=["faculty"],
            is_singular=True,  # Singular role
            default_validity_days=730,
            permissions=["academics.curriculum.manage"],
            conflict_role_codes=["dean_students"],
        )
        self.role_dean_students = RoleDefinition.objects.create(
            code="dean_students",
            name="Dean of Student Affairs",
            module_association="students",
            allowed_user_types=["faculty"],
            is_singular=True,
            permissions=["students.welfare.manage"],
            conflict_role_codes=["dean_academics"],
        )

    # 1. User Management Tests (UC-SA-001..005)
    def test_create_basic_user_student(self):
        user = create_basic_user(
            institute_id="2024CS01",
            user_type="student",
            email="student01@iiitdmj.ac.in",
            first_name="Rohan",
            last_name="Sharma",
            programme="B.Tech",
            discipline="CSE",
            batch_year=2024,
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(user.institute_id, "2024CS01")
        self.assertEqual(user.status, "active")
        self.assertTrue(user.dashboard_access_enabled)
        # Check audit entry created
        self.assertTrue(
            AuditLog.objects.filter(action="user.create", target_id=str(user.user_id)).exists()
        )

    def test_create_user_duplicate_institute_id_rejected(self):
        create_basic_user(
            institute_id="2024CS02",
            user_type="student",
            email="student02@iiitdmj.ac.in",
            first_name="Pooja",
            last_name="Patel",
            programme="B.Tech",
            discipline="ECE",
            batch_year=2024,
        )
        with self.assertRaises(DuplicateInstituteIdError):
            create_basic_user(
                institute_id="2024CS02",
                user_type="student",
                email="student02_dup@iiitdmj.ac.in",
                first_name="Another",
                last_name="User",
                programme="B.Tech",
                discipline="ECE",
                batch_year=2024,
            )

    def test_update_user_profile_immutability(self):
        user = create_basic_user(
            institute_id="FAC001",
            user_type="faculty",
            email="fac01@iiitdmj.ac.in",
            first_name="Dr. Anil",
            last_name="Kumar",
            department="CSE",
            employee_id="EMP001",
        )
        # Update permitted fields
        updated = update_user_profile(
            user_id=user.user_id,
            actor_user_id=1,
            actor_username="super_admin",
            fields_to_update={"first_name": "Prof. Anil", "contact_number": "9988776655"},
        )
        self.assertEqual(updated.first_name, "Prof. Anil")
        self.assertEqual(updated.contact_number, "9988776655")

        # Attempt to modify Institute ID must be rejected (BR-SA-001)
        with self.assertRaises(InstituteIdImmutableError):
            update_user_profile(
                user_id=user.user_id,
                actor_user_id=1,
                actor_username="super_admin",
                fields_to_update={"institute_id": "FAC002"},
            )

    def test_deactivate_and_reactivate_user(self):
        user = create_basic_user(
            institute_id="2024CS03",
            user_type="student",
            email="student03@iiitdmj.ac.in",
            first_name="Vikram",
            last_name="Singh",
            programme="B.Tech",
            batch_year=2024,
        )
        # Assign role
        assign_role(
            user_id=user.user_id,
            role_code="placement_coordinator",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=100),
            actor_user_id=1,
        )

        # Deactivate user
        deactivated = deactivate_user(
            user_id=user.user_id,
            actor_user_id=1,
            actor_username="super_admin",
            reason="Semester break leave",
        )
        self.assertEqual(deactivated.status, "deactivated")
        self.assertFalse(deactivated.dashboard_access_enabled)

        # Auto-revocation of assigned roles on user deactivation (BR-SA-015)
        self.assertTrue(
            RoleAssignment.objects.filter(user_id=user.user_id, status="revoked").exists()
        )

        # Reactivate user (BW-SA-06)
        reactivated = reactivate_user(
            user_id=user.user_id,
            actor_user_id=1,
            actor_username="super_admin",
            reason="Returned from leave",
        )
        self.assertEqual(reactivated.status, "active")
        self.assertTrue(reactivated.dashboard_access_enabled)

    # 2. Bulk Operations Tests (UC-SA-006, UC-SA-007, BR-SA-030)
    def test_bulk_create_users(self):
        records = [
            {
                "institute_id": f"2024CS1{i:02d}",
                "user_type": "student",
                "email": f"student1{i:02d}@iiitdmj.ac.in",
                "first_name": f"Student{i}",
                "last_name": "Test",
                "programme": "B.Tech",
                "batch_year": 2024,
            }
            for i in range(5)
        ]
        log = bulk_create_users(
            records=records,
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(log.total_records, 5)
        self.assertEqual(log.successful_records, 5)
        self.assertEqual(log.failed_records, 0)

    def test_bulk_create_exceeding_1000_limit_rejected(self):
        records = [{"dummy": i} for i in range(1001)]
        with self.assertRaises(BulkLimitExceededError):
            bulk_create_users(
                records=records,
                actor_user_id=1,
                actor_username="super_admin",
            )

    # 3. Role Lifecycle Tests (UC-SA-008..011, BR-SA-007, BR-SA-010, BR-SA-011)
    def test_assign_singular_role_occupancy(self):
        faculty1 = create_basic_user(
            institute_id="FAC002",
            user_type="faculty",
            email="fac02@iiitdmj.ac.in",
            first_name="Dr. Suresh",
            last_name="Rao",
            department="ECE",
            employee_id="EMP002",
        )
        faculty2 = create_basic_user(
            institute_id="FAC003",
            user_type="faculty",
            email="fac03@iiitdmj.ac.in",
            first_name="Dr. Rajesh",
            last_name="Iyer",
            department="CSE",
            employee_id="EMP003",
        )

        # First assignment succeeds
        assign_role(
            user_id=faculty1.user_id,
            role_code="dean_academics",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            scope_type="institute",
            actor_user_id=1,
        )

        # Second assignment for same singular role & scope must fail (BR-SA-007)
        with self.assertRaises(SingularRoleOccupancyError):
            assign_role(
                user_id=faculty2.user_id,
                role_code="dean_academics",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                scope_type="institute",
                actor_user_id=1,
            )

    def test_assign_role_incompatible_user_type_rejected(self):
        student = create_basic_user(
            institute_id="2024CS04",
            user_type="student",
            email="student04@iiitdmj.ac.in",
            first_name="Kavita",
            last_name="Roy",
            programme="B.Tech",
            batch_year=2024,
        )
        # Dean Academics only allowed for Faculty (BR-SA-010)
        with self.assertRaises(RoleIncompatibleUserTypeError):
            assign_role(
                user_id=student.user_id,
                role_code="dean_academics",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                actor_user_id=1,
            )

    def test_assign_role_conflicts(self):
        faculty = create_basic_user(
            institute_id="FAC004",
            user_type="faculty",
            email="fac04@iiitdmj.ac.in",
            first_name="Dr. Meera",
            last_name="Nair",
            department="ME",
            employee_id="EMP004",
        )
        # Assign Dean Academics
        assign_role(
            user_id=faculty.user_id,
            role_code="dean_academics",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            actor_user_id=1,
        )
        # Assign conflicting Dean Students role must be rejected (BR-SA-011)
        with self.assertRaises(RoleConflictError):
            assign_role(
                user_id=faculty.user_id,
                role_code="dean_students",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                actor_user_id=1,
            )

    def test_reassign_role_handover_and_audit_access(self):
        fac1 = create_basic_user(
            institute_id="FAC005",
            user_type="faculty",
            email="fac05@iiitdmj.ac.in",
            first_name="Dr. Tarun",
            last_name="Gupta",
            department="CSE",
            employee_id="EMP005",
        )
        fac2 = create_basic_user(
            institute_id="FAC006",
            user_type="faculty",
            email="fac06@iiitdmj.ac.in",
            first_name="Dr. Varun",
            last_name="Jain",
            department="CSE",
            employee_id="EMP006",
        )

        initial = assign_role(
            user_id=fac1.user_id,
            role_code="dean_academics",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            actor_user_id=1,
        )

        old_a, new_a = reassign_role(
            current_assignment_id=initial.id,
            new_user_id=fac2.user_id,
            effective_date=date.today(),
            reason="Term rotation",
            actor_user_id=1,
            actor_username="super_admin",
            audit_access_days=30,
        )

        self.assertEqual(old_a.status, "reassigned")
        self.assertIsNotNone(old_a.previous_holder_audit_until)  # BR-SA-013
        self.assertEqual(new_a.status, "active")
        self.assertEqual(new_a.user_id, fac2.user_id)

    def test_revoke_role_standard_notice(self):
        fac = create_basic_user(
            institute_id="FAC007",
            user_type="faculty",
            email="fac07@iiitdmj.ac.in",
            first_name="Dr. Priya",
            last_name="Sen",
            department="NS",
            employee_id="EMP007",
        )
        assignment = assign_role(
            user_id=fac.user_id,
            role_code="placement_coordinator",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            actor_user_id=1,
        )

        # Standard revocation with same-day notice fails (BR-SA-014)
        with self.assertRaises(InvalidNoticePeriodError):
            revoke_role(
                assignment_id=assignment.id,
                effective_date=date.today(),
                reason="Regular resignation",
                pending_task_disposition="close",
                is_emergency=False,
            )

        # Emergency revocation succeeds immediately
        revoked = revoke_role(
            assignment_id=assignment.id,
            effective_date=date.today(),
            reason="Emergency resignation",
            pending_task_disposition="transfer",
            is_emergency=True,
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(revoked.status, "revoked")

    def test_extend_role_validity(self):
        student = create_basic_user(
            institute_id="2024CS05",
            user_type="student",
            email="student05@iiitdmj.ac.in",
            first_name="Rohit",
            last_name="Aggarwal",
            programme="B.Tech",
            batch_year=2024,
        )
        d1 = date.today() + timedelta(days=30)
        assignment = assign_role(
            user_id=student.user_id,
            role_code="placement_coordinator",
            start_date=date.today(),
            end_date=d1,
            actor_user_id=1,
        )

        # Extend with earlier end date fails (BR-SA-016)
        with self.assertRaises(InvalidRoleDatesError):
            extend_role_validity(
                assignment_id=assignment.id,
                new_end_date=date.today() + timedelta(days=10),
                reason="Invalid date",
                actor_user_id=1,
                actor_username="super_admin",
            )

        # Valid extension
        d2 = date.today() + timedelta(days=90)
        extended = extend_role_validity(
            assignment_id=assignment.id,
            new_end_date=d2,
            reason="Placement drive extension",
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(extended.end_date, d2)

    def test_switch_active_role(self):
        student = create_basic_user(
            institute_id="2024CS06",
            user_type="student",
            email="student06@iiitdmj.ac.in",
            first_name="Manish",
            last_name="Goyal",
            programme="B.Tech",
            batch_year=2024,
        )
        assign_role(
            user_id=student.user_id,
            role_code="placement_coordinator",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            actor_user_id=1,
        )

        # Valid active role switch
        context = switch_active_role(student.user_id, "placement_coordinator")
        self.assertEqual(context["active_role"], "placement_coordinator")
        self.assertIn("placement_cell.job_posting.view", context["permissions"])

    # 4. Archival & Purge Tests (UC-SA-015, 018, 021, 022, 023, 031)
    def test_user_archival_and_reversibility_window(self):
        user = create_basic_user(
            institute_id="2024CS07",
            user_type="student",
            email="student07@iiitdmj.ac.in",
            first_name="Alok",
            last_name="Mishra",
            programme="B.Tech",
            batch_year=2024,
        )
        # Active user cannot be archived directly (BR-SA-004)
        with self.assertRaises(UserArchivalIneligibleError):
            archive_user(user_id=user.user_id, actor_user_id=1)

        # Deactivate user
        deactivate_user(
            user_id=user.user_id,
            actor_user_id=1,
            actor_username="super_admin",
            reason="Graduated",
        )

        # If deactivated less than 30 days -> fails
        with self.assertRaises(UserArchivalIneligibleError):
            archive_user(user_id=user.user_id, min_deactivation_days=30, actor_user_id=1)

        # Deactivated 35 days ago -> eligible
        user.refresh_from_db()
        user.deactivated_at = timezone.now() - timedelta(days=35)
        user.save()

        archived_u, archive_rec = archive_user(
            user_id=user.user_id,
            retention_years=7,
            reversible_window_days=180,
            reason="Alumni archival",
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(archived_u.status, "archived")
        self.assertIsNotNone(archived_u.reversible_until)

        # Restore within reversible window succeeds (BW-SA-07)
        restored = restore_archived_user(
            user_id=user.user_id,
            reason="Enrolled in M.Tech",
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(restored.status, "active")

    def test_iss_sa_004_permanent_non_restorable_after_window_expiry(self):
        """ISS-SA-004 decision test: post-reversible-window restoration is strictly rejected."""
        user = create_basic_user(
            institute_id="2024CS08",
            user_type="student",
            email="student08@iiitdmj.ac.in",
            first_name="Deepak",
            last_name="Chopra",
            programme="B.Tech",
            batch_year=2024,
        )
        user.status = "deactivated"
        user.deactivated_at = timezone.now() - timedelta(days=60)
        user.save()

        archived_u, _ = archive_user(
            user_id=user.user_id,
            reversible_window_days=180,
            actor_user_id=1,
        )

        # Simulate passage of 200 days (> 180 reversible window)
        archived_u.archived_at = timezone.now() - timedelta(days=200)
        archived_u.reversible_until = timezone.now() - timedelta(days=20)
        archived_u.save()

        # Automated finalization task marks permanently non-restorable (BW-SA-08)
        finalized_count = finalize_non_restorable_archived_users()
        self.assertGreaterEqual(finalized_count, 1)

        archived_u.refresh_from_db()
        self.assertTrue(archived_u.is_permanently_archived)

        # Restoration attempt MUST be rejected (BR-SA-005, ISS-SA-004)
        with self.assertRaises(ArchivedUserPermanentError):
            restore_archived_user(
                user_id=archived_u.user_id,
                reason="Late attempt",
                actor_user_id=1,
                actor_username="super_admin",
            )

    def test_permanent_purge_dual_authorization(self):
        """CW-SA-01 / BW-SA-01 / BW-SA-02: Permanent Purge Dual Authorization."""
        # Create an archive record whose retention has expired
        past_retention = date.today() - timedelta(days=10)
        archive_rec = ArchivedRecord.objects.create(
            category="transient_course_data",
            identifier="CS101_2015",
            data_payload={"term": "2015"},
            retention_until=past_retention,
            backup_reference="bkp_2015",
            archived_by_user_id=1,
            status="archived",
        )

        # Request purge by Super Admin
        purge_req = request_permanent_purge(
            archive_id=archive_rec.id,
            reason="Retention period expired",
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(purge_req.status, "pending_it_head")

        # Authorize purge by IT Head (BW-SA-01)
        authorized = authorize_permanent_purge(
            purge_request_id=purge_req.id,
            decision="approve",
            it_head_user_id=2,
            it_head_username="it_head",
        )
        self.assertEqual(authorized.status, "approved")

        archive_rec.refresh_from_db()
        self.assertEqual(archive_rec.status, "purged")

    # 5. Audit Log Immutability Tests (BR-SA-025, BR-SA-033)
    def test_audit_log_immutability(self):
        log = record_audit_event(
            actor_user_id=1,
            actor_username="super_admin",
            action="system.test",
            reason="Testing immutability",
        )
        # Attempt to modify audit log fails
        with self.assertRaises(RuntimeError):
            log.reason = "Modified reason"
            log.save()

        # Attempt to delete audit log fails
        with self.assertRaises(RuntimeError):
            log.delete()

    # 6. System Configuration Boundary Tests (BR-SA-035)
    def test_system_configuration_boundary(self):
        # Permitted key succeeds
        cfg = update_configuration(
            key="password_rotation_days",
            value=60,
            actor_user_id=1,
            actor_username="super_admin",
        )
        self.assertEqual(cfg.value, 60)

        # Non-permitted key must be rejected (BR-SA-035)
        with self.assertRaises(PermittedConfigBoundaryError):
            update_configuration(
                key="academic_calendar_schedule",
                value={"semester": "Autumn 2026"},
                actor_user_id=1,
                actor_username="super_admin",
            )
