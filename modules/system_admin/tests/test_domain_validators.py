"""Unit tests for System Administrator domain validators and policies.

Pure Python tests: no DB, no network, runs in milliseconds.
Tests:
  - validate_institute_id (BR-SA-001)
  - validate_institute_email (BR-SA-002)
  - validate_user_type_required_data (BR-SA-003)
  - validate_role_eligibility (BR-SA-010)
  - validate_singular_occupancy (BR-SA-007)
  - validate_role_dating (BR-SA-008)
  - validate_revocation_notice (BR-SA-014)
  - validate_bulk_size (BR-SA-030)
  - validate_configuration_key (BR-SA-035)
  - assess_user_archival_eligibility (BR-SA-004)
  - calculate_reversible_deadline (BR-SA-005, ISS-SA-004)
  - is_historical_data_purge_eligible (BR-SA-021)
  - check_password_complexity (BR-SA-027)
  - is_failed_login_alert_triggered (BR-SA-024)
  - is_session_expired
  - is_password_rotation_due (BR-SA-031)
"""
from datetime import date, datetime, timedelta
import pytest

from modules.system_admin.domain import (
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DEFAULT_PERMITTED_CONFIG_KEYS,
    DomainError,
    IdentityValidationError,
    IneligibleRoleUserTypeError,
    SingularRoleOccupiedError,
    UserCreationSpec,
    assess_user_archival_eligibility,
    calculate_reversible_deadline,
    check_password_complexity,
    is_failed_login_alert_triggered,
    is_historical_data_purge_eligible,
    is_password_rotation_due,
    is_session_expired,
    validate_bulk_size,
    validate_configuration_key,
    validate_institute_email,
    validate_institute_id,
    validate_revocation_notice,
    validate_role_dating,
    validate_role_eligibility,
    validate_singular_occupancy,
    validate_user_type_required_data,
)


# =============================================================================
# 1. Identity & Creation Validators (BR-SA-001..003)
# =============================================================================

class TestIdentityValidators:
    def test_validate_institute_id_valid(self):
        valid_ids = ["21BCS001", "FAC/2020/01", "PF-1002", "STU_1234", "DEAN123"]
        for i_id in valid_ids:
            validate_institute_id(i_id)  # Should not raise

    def test_validate_institute_id_invalid(self):
        invalid_ids = ["", "   ", "AB", "A" * 21, "ID@INST", "ID#123", "ID$456"]
        for i_id in invalid_ids:
            with pytest.raises(IdentityValidationError):
                validate_institute_id(i_id)

    def test_validate_institute_email_valid(self):
        valid_emails = [
            "student@iiitdmj.ac.in",
            "prof.smith@iiitdmj.ac.in",
            "admin@subdomain.iiitdmj.ac.in",
            "user123+tag@iiitdmj.ac.in",
        ]
        for email in valid_emails:
            validate_institute_email(email)  # Should not raise

    def test_validate_institute_email_invalid(self):
        invalid_emails = [
            "",
            "   ",
            "user@gmail.com",
            "user@iiit.ac.in",
            "user@iiitdmj.com",
            "not-an-email",
            "@iiitdmj.ac.in",
        ]
        for email in invalid_emails:
            with pytest.raises(IdentityValidationError):
                validate_institute_email(email)

    def test_validate_user_type_required_data_student(self):
        # Valid student
        spec = UserCreationSpec(
            user_kind="student",
            name="Alice Smith",
            institute_email="alice@iiitdmj.ac.in",
            institute_id="21BCS001",
            contact_number="9876543210",
            programme="B.Tech",
            discipline="CSE",
            batch_year=2021,
        )
        validate_user_type_required_data(spec)

        # Missing programme
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="student",
                    name="Alice",
                    institute_email="alice@iiitdmj.ac.in",
                    institute_id="21BCS001",
                    contact_number="9876543210",
                    batch_year=2021,
                )
            )
        assert "programme" in str(exc.value)

        # Missing batch_year
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="student",
                    name="Alice",
                    institute_email="alice@iiitdmj.ac.in",
                    institute_id="21BCS001",
                    contact_number="9876543210",
                    programme="B.Tech",
                )
            )
        assert "batch year" in str(exc.value)

    def test_validate_user_type_required_data_faculty_and_staff(self):
        # Valid faculty
        fac_spec = UserCreationSpec(
            user_kind="faculty",
            name="Dr. Bob",
            institute_email="bob@iiitdmj.ac.in",
            institute_id="FAC001",
            contact_number="9876543211",
            department="CSE",
            employee_id="EMP-101",
        )
        validate_user_type_required_data(fac_spec)

        # Missing department
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="faculty",
                    name="Dr. Bob",
                    institute_email="bob@iiitdmj.ac.in",
                    institute_id="FAC001",
                    contact_number="9876543211",
                    employee_id="EMP-101",
                )
            )
        assert "department" in str(exc.value)

        # Missing employee_id
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="staff",
                    name="Charlie",
                    institute_email="charlie@iiitdmj.ac.in",
                    institute_id="STAFF001",
                    contact_number="9876543212",
                    department="Admin",
                )
            )
        assert "employee ID" in str(exc.value)

    def test_validate_user_type_required_data_invalid_user_kind(self):
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="guest",
                    name="Guest",
                    institute_email="guest@iiitdmj.ac.in",
                    institute_id="GUEST001",
                    contact_number="9876543213",
                )
            )
        assert "Unknown user kind" in str(exc.value)

    def test_validate_user_type_required_data_empty_name(self):
        with pytest.raises(IdentityValidationError) as exc:
            validate_user_type_required_data(
                UserCreationSpec(
                    user_kind="student",
                    name="   ",
                    institute_email="student@iiitdmj.ac.in",
                    institute_id="21BCS002",
                    contact_number="9876543210",
                    programme="B.Tech",
                    batch_year=2021,
                )
            )
        assert "Full name is required" in str(exc.value)


# =============================================================================
# 2. Role Assignment & Revocation Validators (BR-SA-007..014)
# =============================================================================

class TestRoleValidators:
    def test_validate_role_eligibility(self):
        allowed = ("faculty", "staff")
        validate_role_eligibility("hod_cse", "faculty", allowed)  # ok
        validate_role_eligibility("registrar", "staff", allowed)  # ok

        with pytest.raises(IneligibleRoleUserTypeError) as exc:
            validate_role_eligibility("hod_cse", "student", allowed)
        assert exc.value.role_code == "hod_cse"
        assert exc.value.user_kind == "student"
        assert exc.value.allowed_kinds == allowed

    def test_validate_singular_occupancy(self):
        # No current holder -> ok
        validate_singular_occupancy("dean_academics", "institute", None, 42)
        # Same holder -> ok
        validate_singular_occupancy("dean_academics", "institute", 42, 42)

        # Different holder -> raises SingularRoleOccupiedError
        with pytest.raises(SingularRoleOccupiedError) as exc:
            validate_singular_occupancy("dean_academics", "institute", 10, 42)
        assert exc.value.role_code == "dean_academics"
        assert exc.value.scope == "institute"
        assert exc.value.current_holder_id == 10

    def test_validate_role_dating(self):
        start = date(2026, 11, 1)
        end = date(2026, 12, 1)

        # Valid time-bound
        validate_role_dating(start, is_time_bound=True, end_date=end)

        # Valid non-time-bound
        validate_role_dating(start, is_time_bound=False, end_date=None)

        # Missing start date
        with pytest.raises(DomainError) as exc:
            validate_role_dating(None, is_time_bound=False, end_date=None)  # type: ignore
        assert exc.value.code == "missing_start_date"

        # Time-bound missing end date
        with pytest.raises(DomainError) as exc:
            validate_role_dating(start, is_time_bound=True, end_date=None)
        assert exc.value.code == "missing_end_date"

        # End date <= start date
        with pytest.raises(DomainError) as exc:
            validate_role_dating(start, is_time_bound=True, end_date=start)
        assert exc.value.code == "invalid_date_range"

        with pytest.raises(DomainError) as exc:
            validate_role_dating(start, is_time_bound=True, end_date=date(2026, 10, 31))
        assert exc.value.code == "invalid_date_range"

    def test_validate_revocation_notice(self):
        notice = date(2026, 11, 2)
        valid_effective = date(2026, 11, 3)  # +1 day
        invalid_effective = date(2026, 11, 2)  # same day

        # Standard revocation with >= 1 day notice
        validate_revocation_notice(is_emergency=False, notice_date=notice, effective_date=valid_effective)

        # Standard revocation with insufficient notice
        with pytest.raises(DomainError) as exc:
            validate_revocation_notice(is_emergency=False, notice_date=notice, effective_date=invalid_effective)
        assert exc.value.code == "insufficient_revocation_notice"

        # Emergency revocation allows immediate effective date
        validate_revocation_notice(is_emergency=True, notice_date=notice, effective_date=notice)


# =============================================================================
# 3. Operational & Configuration Validators (BR-SA-030, BR-SA-035)
# =============================================================================

class TestOperationalValidators:
    def test_validate_bulk_size(self):
        validate_bulk_size(1, 1000)
        validate_bulk_size(500, 1000)
        validate_bulk_size(1000, 1000)

        # Empty
        with pytest.raises(DomainError) as exc:
            validate_bulk_size(0, 1000)
        assert exc.value.code == "bulk_empty"

        with pytest.raises(DomainError) as exc:
            validate_bulk_size(-5, 1000)
        assert exc.value.code == "bulk_empty"

        # Limit exceeded
        with pytest.raises(BulkLimitExceededError) as exc:
            validate_bulk_size(1001, 1000)
        assert exc.value.count == 1001
        assert exc.value.max_limit == 1000

    def test_validate_configuration_key(self):
        permitted = DEFAULT_PERMITTED_CONFIG_KEYS
        validate_configuration_key("password.min_length", permitted)
        validate_configuration_key("bulk.max_records", permitted)

        with pytest.raises(ConfigurationBoundaryViolationError) as exc:
            validate_configuration_key("database.master_password", permitted)
        assert exc.value.attempted_param == "database.master_password"


# =============================================================================
# 4. Archival & Retention Policy Tests (BR-SA-004..005, BR-SA-021)
# =============================================================================

class TestArchivalPolicy:
    now = datetime(2026, 11, 2, 12, 0, 0)

    def test_assess_user_archival_eligibility_not_deactivated(self):
        verdict = assess_user_archival_eligibility(
            is_deactivated=False,
            deactivated_at=None,
            has_pending_transactions=False,
            min_deactivation_days=30,
            now=self.now,
        )
        assert verdict.is_eligible is False
        assert "deactivated" in verdict.reason

    def test_assess_user_archival_eligibility_pending_transactions(self):
        deactivated_at = self.now - timedelta(days=45)
        verdict = assess_user_archival_eligibility(
            is_deactivated=True,
            deactivated_at=deactivated_at,
            has_pending_transactions=True,
            min_deactivation_days=30,
            now=self.now,
        )
        assert verdict.is_eligible is False
        assert verdict.has_pending_transactions is True
        assert "pending workflow transactions" in verdict.reason

    def test_assess_user_archival_eligibility_insufficient_elapsed_days(self):
        deactivated_at = self.now - timedelta(days=20)
        verdict = assess_user_archival_eligibility(
            is_deactivated=True,
            deactivated_at=deactivated_at,
            has_pending_transactions=False,
            min_deactivation_days=30,
            now=self.now,
        )
        assert verdict.is_eligible is False
        assert verdict.deactivation_days_elapsed == 20
        assert "less than required 30 days" in verdict.reason

    def test_assess_user_archival_eligibility_eligible(self):
        deactivated_at = self.now - timedelta(days=35)
        verdict = assess_user_archival_eligibility(
            is_deactivated=True,
            deactivated_at=deactivated_at,
            has_pending_transactions=False,
            min_deactivation_days=30,
            now=self.now,
        )
        assert verdict.is_eligible is True
        assert verdict.deactivation_days_elapsed == 35

    def test_calculate_reversible_deadline(self):
        archived_at = datetime(2026, 11, 2, 10, 0, 0)
        deadline = calculate_reversible_deadline(archived_at, reversible_window_days=90)
        assert deadline == archived_at + timedelta(days=90)

    def test_is_historical_data_purge_eligible(self):
        archived_date = date(2016, 5, 1)
        retention_years = 10  # cutoff is 2026-05-01

        assert is_historical_data_purge_eligible(archived_date, retention_years, date(2026, 5, 1)) is True
        assert is_historical_data_purge_eligible(archived_date, retention_years, date(2026, 5, 2)) is True
        assert is_historical_data_purge_eligible(archived_date, retention_years, date(2026, 4, 30)) is False

    def test_is_historical_data_purge_eligible_leap_year(self):
        archived_leap = date(2020, 2, 29)
        retention_years = 5  # 2025 is not a leap year -> cutoff 2025-02-28
        assert is_historical_data_purge_eligible(archived_leap, retention_years, date(2025, 2, 28)) is True
        assert is_historical_data_purge_eligible(archived_leap, retention_years, date(2025, 2, 27)) is False


# =============================================================================
# 5. Security Policy Tests (BR-SA-024, BR-SA-027, BR-SA-031)
# =============================================================================

class TestSecurityPolicy:
    def test_check_password_complexity(self):
        # Valid strong password
        ok, msg = check_password_complexity("Admin@Pass1234")
        assert ok is True
        assert msg == ""

        # Too short (< 12)
        ok, msg = check_password_complexity("Admin@123")
        assert ok is False
        assert "at least 12 characters" in msg

        # Missing uppercase
        ok, msg = check_password_complexity("admin@pass1234")
        assert ok is False
        assert "uppercase" in msg

        # Missing lowercase
        ok, msg = check_password_complexity("ADMIN@PASS1234")
        assert ok is False
        assert "lowercase" in msg

        # Missing digit
        ok, msg = check_password_complexity("Admin@Password")
        assert ok is False
        assert "digit" in msg

        # Missing special character
        ok, msg = check_password_complexity("AdminPassword123")
        assert ok is False
        assert "special character" in msg

    def test_is_failed_login_alert_triggered(self):
        assert is_failed_login_alert_triggered(4, threshold=5) is False
        assert is_failed_login_alert_triggered(5, threshold=5) is True
        assert is_failed_login_alert_triggered(6, threshold=5) is True

    def test_is_session_expired(self):
        now = datetime(2026, 11, 2, 12, 30, 0)
        active_recent = now - timedelta(minutes=10)
        active_stale = now - timedelta(minutes=31)

        assert is_session_expired(active_recent, timeout_minutes=30, now=now) is False
        assert is_session_expired(active_stale, timeout_minutes=30, now=now) is True

    def test_is_password_rotation_due(self):
        now = datetime(2026, 11, 2, 12, 0, 0)
        recent_change = now - timedelta(days=60)
        old_change = now - timedelta(days=91)

        assert is_password_rotation_due(recent_change, rotation_days=90, now=now) is False
        assert is_password_rotation_due(old_change, rotation_days=90, now=now) is True
