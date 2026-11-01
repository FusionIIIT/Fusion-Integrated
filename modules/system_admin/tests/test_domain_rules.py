"""Unit tests for System Admin pure Python domain layer.

Zero database or Django dependency — runs in milliseconds with unittest.
"""
from datetime import date, datetime, timedelta
import unittest

from modules.system_admin.domain import (
    ActiveRoleInvalidError,
    ArchivedUserPermanentError,
    AuditLogArchivalProhibitedError,
    BasicUserType,
    BulkLimitExceededError,
    CriticalOperationReauthRequiredError,
    DualAuthorizationRequiredError,
    DuplicateInstituteIdError,
    HistoricalDataArchivalIneligibleError,
    InstituteIdImmutableError,
    InvalidInstituteEmailError,
    InvalidNoticePeriodError,
    InvalidRoleDatesError,
    MissingUserTypeDataError,
    OperationalContentAccessForbiddenError,
    PendingTaskDisposition,
    PermittedConfigBoundaryError,
    PurgeRequestStatus,
    PurgeRetentionNotElapsedError,
    RoleAssignmentStatus,
    RoleConflictError,
    RoleIncompatibleUserTypeError,
    SingularRoleOccupancyError,
    SuperAdminSelfModificationForbiddenError,
    SystemAdminDomainError,
    UserArchivalIneligibleError,
    UserStatus,
    validate_active_role_selection,
    validate_archived_user_reversibility,
    validate_bulk_operation_limit,
    validate_critical_operation_reauth,
    validate_historical_data_archival_eligibility,
    validate_institute_email,
    validate_institute_id_immutability,
    validate_institute_id_uniqueness,
    validate_no_self_super_admin_modification,
    validate_permanent_purge_eligibility,
    validate_permitted_system_configuration,
    validate_purge_authorization,
    validate_purge_request,
    validate_role_assignment_transition,
    validate_role_conflicts,
    validate_role_dates,
    validate_role_extension,
    validate_role_revocation,
    validate_role_user_type_eligibility,
    validate_singular_role_occupancy,
    validate_strong_password,
    validate_super_admin_data_isolation,
    validate_user_archival_eligibility,
    validate_user_transition,
    validate_user_type_required_data,
)


class TestDomainRules(unittest.TestCase):

    # BR-SA-001: Institute ID
    def test_institute_id_immutability(self):
        validate_institute_id_immutability("2024CS01", "2024CS01")
        with self.assertRaises(InstituteIdImmutableError):
            validate_institute_id_immutability("2024CS01", "2024CS02")

    def test_institute_id_uniqueness(self):
        existing = {"2024CS01", "FAC001"}
        validate_institute_id_uniqueness("2024CS02", existing)
        with self.assertRaises(DuplicateInstituteIdError):
            validate_institute_id_uniqueness("2024CS01", existing)

    # BR-SA-002: Institute Email
    def test_institute_email_validation(self):
        validate_institute_email("john.doe@iiitdmj.ac.in")
        validate_institute_email("student2024@cse.iiitdmj.ac.in")
        with self.assertRaises(InvalidInstituteEmailError):
            validate_institute_email("john.doe@gmail.com")
        with self.assertRaises(InvalidInstituteEmailError):
            validate_institute_email("notanemail")

    # BR-SA-003: User-Type Required Data
    def test_user_type_required_data(self):
        # Student valid
        validate_user_type_required_data(
            BasicUserType.STUDENT,
            {
                "institute_id": "2024CS01",
                "email": "student@iiitdmj.ac.in",
                "first_name": "Rohan",
                "last_name": "Sharma",
                "programme": "B.Tech",
                "batch_year": 2024,
            },
        )
        # Student missing batch_year
        with self.assertRaises(MissingUserTypeDataError):
            validate_user_type_required_data(
                BasicUserType.STUDENT,
                {
                    "institute_id": "2024CS01",
                    "email": "student@iiitdmj.ac.in",
                    "first_name": "Rohan",
                    "last_name": "Sharma",
                    "programme": "B.Tech",
                },
            )
        # Faculty valid
        validate_user_type_required_data(
            BasicUserType.FACULTY,
            {
                "institute_id": "FAC101",
                "email": "fac@iiitdmj.ac.in",
                "first_name": "Dr. Amit",
                "last_name": "Verma",
                "department": "CSE",
                "employee_id": "EMP101",
            },
        )
        # Faculty missing employee_id
        with self.assertRaises(MissingUserTypeDataError):
            validate_user_type_required_data(
                BasicUserType.FACULTY,
                {
                    "institute_id": "FAC101",
                    "email": "fac@iiitdmj.ac.in",
                    "first_name": "Dr. Amit",
                    "last_name": "Verma",
                    "department": "CSE",
                },
            )

    # BR-SA-004: User Archival Eligibility
    def test_user_archival_eligibility(self):
        now = datetime(2026, 11, 1, 12, 0, 0)
        # 40 days deactivated -> eligible
        deactivated_40_days_ago = now - timedelta(days=40)
        validate_user_archival_eligibility(
            UserStatus.DEACTIVATED, deactivated_40_days_ago, 30, False, now
        )
        # Deactivated only 10 days ago (< 30 days) -> ineligible
        deactivated_10_days_ago = now - timedelta(days=10)
        with self.assertRaises(UserArchivalIneligibleError):
            validate_user_archival_eligibility(
                UserStatus.DEACTIVATED, deactivated_10_days_ago, 30, False, now
            )
        # Pending transactions -> ineligible
        with self.assertRaises(UserArchivalIneligibleError):
            validate_user_archival_eligibility(
                UserStatus.DEACTIVATED, deactivated_40_days_ago, 30, True, now
            )
        # Active user -> ineligible
        with self.assertRaises(UserArchivalIneligibleError):
            validate_user_archival_eligibility(
                UserStatus.ACTIVE, deactivated_40_days_ago, 30, False, now
            )

    # BR-SA-005 & ISS-SA-004: Reversible Window vs Permanent
    def test_archived_user_reversibility(self):
        now = datetime(2026, 11, 1, 12, 0, 0)
        archived_50_days_ago = now - timedelta(days=50)
        # Inside 180-day window
        validate_archived_user_reversibility(archived_50_days_ago, 180, False, now)
        # Outside 180-day window (200 days)
        archived_200_days_ago = now - timedelta(days=200)
        with self.assertRaises(ArchivedUserPermanentError):
            validate_archived_user_reversibility(archived_200_days_ago, 180, False, now)
        # Explicitly marked permanently archived
        with self.assertRaises(ArchivedUserPermanentError):
            validate_archived_user_reversibility(archived_50_days_ago, 180, True, now)

    # BR-SA-007: Singular Role Occupancy
    def test_singular_role_occupancy(self):
        # Non-singular role allows multiple holders
        validate_singular_role_occupancy(False, "CSE", [101, 102], 103)
        # Singular role with no active holder
        validate_singular_role_occupancy(True, "CSE", [], 101)
        # Singular role already held by another user
        with self.assertRaises(SingularRoleOccupancyError):
            validate_singular_role_occupancy(True, "CSE", [101], 102)
        # Singular role held by target user itself (re-check)
        validate_singular_role_occupancy(True, "CSE", [101], 101)

    # BR-SA-008: Role Dating
    def test_role_dating(self):
        d1 = date(2026, 11, 1)
        d2 = date(2026, 12, 1)
        validate_role_dates(d1, d2, True)
        # End date before or equal start date
        with self.assertRaises(InvalidRoleDatesError):
            validate_role_dates(d2, d1, True)
        with self.assertRaises(InvalidRoleDatesError):
            validate_role_dates(d1, d1, True)
        # Missing end date for time-bound role
        with self.assertRaises(InvalidRoleDatesError):
            validate_role_dates(d1, None, True)

    # BR-SA-010: Role User Type Eligibility
    def test_role_user_type_eligibility(self):
        allowed = [BasicUserType.FACULTY, BasicUserType.STAFF]
        validate_role_user_type_eligibility(allowed, BasicUserType.FACULTY)
        with self.assertRaises(RoleIncompatibleUserTypeError):
            validate_role_user_type_eligibility(allowed, BasicUserType.STUDENT)

    # BR-SA-011: Role Conflicts
    def test_role_conflicts(self):
        existing = ["placement_cell_coordinator", "student_gymkhana_head"]
        candidate_conflicts = ["student_gymkhana_head", "dean_students"]
        with self.assertRaises(RoleConflictError):
            validate_role_conflicts(existing, candidate_conflicts)
        validate_role_conflicts(["tpo_member"], ["warden_hostel_3"])

    # BR-SA-014: Role Revocation
    def test_role_revocation(self):
        today = date(2026, 11, 1)
        # Standard revocation with >= 1 day notice
        validate_role_revocation(
            date(2026, 11, 5), False, "Scheduled transition", PendingTaskDisposition.TRANSFER, today
        )
        # Standard revocation same day -> invalid notice
        with self.assertRaises(InvalidNoticePeriodError):
            validate_role_revocation(
                today, False, "Immediate attempt", PendingTaskDisposition.TRANSFER, today
            )
        # Emergency revocation -> allowed same day
        validate_role_revocation(
            today, True, "Disciplinary action", PendingTaskDisposition.CLOSE, today
        )

    # BR-SA-016: Role Extension
    def test_role_extension(self):
        d1 = date(2026, 12, 1)
        d2 = date(2027, 1, 1)
        validate_role_extension(d1, d2, "Term extended by Director")
        with self.assertRaises(InvalidRoleDatesError):
            validate_role_extension(d2, d1, "Invalid date")

    # BR-SA-017 & BR-SA-025: Audit Archival Exclusion
    def test_audit_archival_prohibition(self):
        with self.assertRaises(AuditLogArchivalProhibitedError):
            validate_historical_data_archival_eligibility("audit", False, is_audit_log=True)
        with self.assertRaises(AuditLogArchivalProhibitedError):
            validate_permanent_purge_eligibility(date(2020, 1, 1), date(2026, 1, 1), is_audit_log=True)

    # BR-SA-021: Purge Retention
    def test_purge_retention(self):
        today = date(2026, 11, 1)
        # Retention expired in 2025 -> eligible
        validate_permanent_purge_eligibility(date(2025, 12, 31), today)
        # Retention expires in 2027 -> not eligible
        with self.assertRaises(PurgeRetentionNotElapsedError):
            validate_permanent_purge_eligibility(date(2027, 12, 31), today)

    # BR-SA-022: Purge Dual Authorization State Machine
    def test_purge_dual_authorization(self):
        # Approved path (BW-SA-01)
        res = validate_purge_authorization(PurgeRequestStatus.PENDING_IT_HEAD, True, "approve")
        self.assertEqual(res, PurgeRequestStatus.APPROVED)
        # Rejected path (BW-SA-02)
        res2 = validate_purge_authorization(PurgeRequestStatus.PENDING_IT_HEAD, True, "reject")
        self.assertEqual(res2, PurgeRequestStatus.REJECTED)
        # IT Head authorization missing
        with self.assertRaises(DualAuthorizationRequiredError):
            validate_purge_authorization(PurgeRequestStatus.PENDING_IT_HEAD, False, "approve")

    # BR-SA-026: Data Isolation
    def test_super_admin_data_isolation(self):
        with self.assertRaises(OperationalContentAccessForbiddenError):
            validate_super_admin_data_isolation("academic_grades")
        with self.assertRaises(OperationalContentAccessForbiddenError):
            validate_super_admin_data_isolation("financial_ledger")
        with self.assertRaises(OperationalContentAccessForbiddenError):
            validate_super_admin_data_isolation("medical_records")
        # Allowed control plane resources
        validate_super_admin_data_isolation("user_profile")
        validate_super_admin_data_isolation("role_assignment")
        validate_super_admin_data_isolation("audit_metadata")

    # BR-SA-027: Password Policy
    def test_password_policy(self):
        validate_strong_password("SuperSecret99#")
        with self.assertRaises(SystemAdminDomainError):
            validate_strong_password("short1#")  # < 12
        with self.assertRaises(SystemAdminDomainError):
            validate_strong_password("alllowercase123#")  # no uppercase
        with self.assertRaises(SystemAdminDomainError):
            validate_strong_password("ALLUPPERCASE123#")  # no lowercase
        with self.assertRaises(SystemAdminDomainError):
            validate_strong_password("NoDigitsHere##")  # no digits

    # BR-SA-028: No Self Super Admin Modification
    def test_no_self_modification(self):
        with self.assertRaises(SuperAdminSelfModificationForbiddenError):
            validate_no_self_super_admin_modification(1, 2, "super_admin")
        with self.assertRaises(SuperAdminSelfModificationForbiddenError):
            validate_no_self_super_admin_modification(1, 1, "admin_role")

    # BR-SA-029: Critical Operation Reauth
    def test_critical_operation_reauth(self):
        validate_critical_operation_reauth(True, True, "Archive operation")
        with self.assertRaises(CriticalOperationReauthRequiredError):
            validate_critical_operation_reauth(True, False, "Purge operation")

    # BR-SA-030: Bulk Limit
    def test_bulk_limit(self):
        validate_bulk_operation_limit(1000, 1000)
        with self.assertRaises(BulkLimitExceededError):
            validate_bulk_operation_limit(1001, 1000)
        with self.assertRaises(SystemAdminDomainError):
            validate_bulk_operation_limit(0, 1000)

    # BR-SA-034: Active Role Selection
    def test_active_role_selection(self):
        assigned = ["student", "placement_coordinator"]
        validate_active_role_selection(assigned, "student")
        with self.assertRaises(ActiveRoleInvalidError):
            validate_active_role_selection(assigned, "dean_academics")

    # BR-SA-035: Permitted Configuration Boundary
    def test_permitted_config_boundary(self):
        validate_permitted_system_configuration([
            "password_rotation_days",
            "session_inactivity_timeout_minutes",
            "deactivation_to_archive_days",
        ])
        with self.assertRaises(PermittedConfigBoundaryError):
            validate_permitted_system_configuration(["academic_calendar_schedule"])
        with self.assertRaises(PermittedConfigBoundaryError):
            validate_permitted_system_configuration(["financial_fee_structure"])


if __name__ == "__main__":
    unittest.main()
