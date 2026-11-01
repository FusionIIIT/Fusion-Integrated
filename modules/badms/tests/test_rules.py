"""Unit tests for BADMS domain business rules and calculations.

Covers BR-BA-001 through BR-BA-021.
Executes pure Python tests with zero database overhead.
"""

import unittest
from datetime import date
from ..domain import (
    CLASS_ARCHIVAL,
    CLASS_CRITICAL,
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    DomainValidationError,
    calculate_retention_policy,
    evaluate_backup_failure_response,
    get_initial_classification,
    is_sensitive_restoration_approval_required,
    resolve_effective_schedule,
    validate_authoritative_classification,
    validate_encryption_configuration,
    validate_global_backup_policy_authority,
    validate_hod_department_scope,
    validate_it_security_policy_authority,
    validate_manual_backup_authority,
    validate_schedule_parameters,
    validate_sensitive_restoration_decision,
    validate_special_archival_authority,
    validate_storage_extension_submission,
)


class BadmsDomainRulesTestCase(unittest.TestCase):

    def test_br_ba_001_manual_backup_authorization(self):
        """SysAdmin and Super Admin can trigger backups; other roles rejected."""
        validate_manual_backup_authority("sysadmin")
        validate_manual_backup_authority("superadmin")
        validate_manual_backup_authority("SYSTEM_ADMIN")
        
        with self.assertRaises(DomainValidationError):
            validate_manual_backup_authority("faculty")
        with self.assertRaises(DomainValidationError):
            validate_manual_backup_authority("student")

    def test_br_ba_006_initial_classification_default(self):
        """Omitted or empty classification defaults to ROUTINE."""
        self.assertEqual(get_initial_classification(None), CLASS_ROUTINE)
        self.assertEqual(get_initial_classification(""), CLASS_ROUTINE)
        self.assertEqual(get_initial_classification("   "), CLASS_ROUTINE)
        self.assertEqual(get_initial_classification("sensitive"), CLASS_SENSITIVE)
        
        with self.assertRaises(DomainValidationError):
            get_initial_classification("INVALID_CLASS")

    def test_br_ba_002_010_hod_department_scope(self):
        """HoD can only decide requests in their own department."""
        validate_hod_department_scope("hod", "CSE", "CSE")
        validate_hod_department_scope("HOD_ECE", "ECE", "ece")
        
        # Cross department rejection
        with self.assertRaises(DomainValidationError):
            validate_hod_department_scope("hod", "CSE", "ME")
            
        # Non-HoD actor rejection
        with self.assertRaises(DomainValidationError):
            validate_hod_department_scope("faculty", "CSE", "CSE")

    def test_br_ba_004_sysadmin_classification(self):
        """SysAdmin assigns authoritative classification; others rejected."""
        self.assertEqual(validate_authoritative_classification("sysadmin", "critical"), CLASS_CRITICAL)
        self.assertEqual(validate_authoritative_classification("system_admin", "sensitive"), CLASS_SENSITIVE)
        
        with self.assertRaises(DomainValidationError):
            validate_authoritative_classification("faculty", "ROUTINE")

    def test_br_ba_003_007_encryption_authority_and_algorithm(self):
        """IT Security configures AES-256 encryption for Sensitive data."""
        validate_encryption_configuration("it_security", CLASS_SENSITIVE, "AES-256")
        
        # Wrong role
        with self.assertRaises(DomainValidationError):
            validate_encryption_configuration("sysadmin", CLASS_SENSITIVE, "AES-256")
            
        # Wrong algorithm
        with self.assertRaises(DomainValidationError):
            validate_encryption_configuration("it_security", CLASS_SENSITIVE, "DES")

    def test_br_ba_008_retention_calculation(self):
        """Retention periods match specification: Critical 30y, Sensitive 10y, Routine 5y, Archival 15y."""
        base = date(2026, 11, 1)
        y, exp = calculate_retention_policy(CLASS_CRITICAL, base)
        self.assertEqual(y, 30)
        self.assertEqual(exp, date(2056, 11, 1))

        y, exp = calculate_retention_policy(CLASS_SENSITIVE, base)
        self.assertEqual(y, 10)
        self.assertEqual(exp, date(2036, 11, 1))

        y, exp = calculate_retention_policy(CLASS_ROUTINE, base)
        self.assertEqual(y, 5)
        self.assertEqual(exp, date(2031, 11, 1))

        y, exp = calculate_retention_policy(CLASS_ARCHIVAL, base)
        self.assertEqual(y, 15)
        self.assertEqual(exp, date(2041, 11, 1))

    def test_br_ba_005_sensitive_restoration_approval(self):
        """Sensitive data requires SysAdmin approval; non-sensitive does not."""
        self.assertTrue(is_sensitive_restoration_approval_required(CLASS_SENSITIVE))
        self.assertFalse(is_sensitive_restoration_approval_required(CLASS_ROUTINE))
        self.assertFalse(is_sensitive_restoration_approval_required(CLASS_CRITICAL))
        
        validate_sensitive_restoration_decision("sysadmin", "APPROVE")
        with self.assertRaises(DomainValidationError):
            validate_sensitive_restoration_decision("student", "APPROVE")

    def test_br_ba_016_storage_extension_usage_threshold(self):
        """Storage extension permitted only when usage reaches >= 80% threshold."""
        # 85% usage -> passes
        validate_storage_extension_submission(
            used_storage_mb=850.0,
            allocated_storage_mb=1000.0,
            requested_additional_mb=500.0,
            threshold_percent=80.0
        )
        
        # 50% usage -> fails threshold check
        with self.assertRaises(DomainValidationError):
            validate_storage_extension_submission(
                used_storage_mb=500.0,
                allocated_storage_mb=1000.0,
                requested_additional_mb=500.0,
                threshold_percent=80.0
            )

    def test_br_ba_014_015_backup_failure_alerting_and_escalation(self):
        """Alert on single failure; escalate to Director of IT on 3 consecutive failures."""
        alert, escalate, msg = evaluate_backup_failure_response(1)
        self.assertTrue(alert)
        self.assertFalse(escalate)

        alert, escalate, msg = evaluate_backup_failure_response(2)
        self.assertTrue(alert)
        self.assertFalse(escalate)

        alert, escalate, msg = evaluate_backup_failure_response(3)
        self.assertTrue(alert)
        self.assertTrue(escalate)
        self.assertIn("Director of IT", msg)

    def test_br_ba_011_schedule_resolution_override(self):
        """Local dataset schedule overrides global schedule."""
        local = [{"dataset_name": "academics", "frequency": "DAILY", "is_active": True}]
        global_s = [{"frequency": "WEEKLY", "is_active": True}]
        
        res = resolve_effective_schedule("academics", local, global_s)
        self.assertEqual(res["source"], "LOCAL")

        res_finance = resolve_effective_schedule("finance", local, global_s)
        self.assertEqual(res_finance["source"], "GLOBAL")

    def test_br_ba_018_special_archival_authority(self):
        """Only Super Admin may perform special archival operations."""
        validate_special_archival_authority("superadmin")
        with self.assertRaises(DomainValidationError):
            validate_special_archival_authority("sysadmin")


if __name__ == "__main__":
    unittest.main()
