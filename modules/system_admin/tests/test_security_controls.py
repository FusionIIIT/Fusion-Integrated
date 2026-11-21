"""Verification tests for security controls: complexity, session timeout, failed login lockout.

Traceability: CFR-SA-021, AFR-SA-073A..074C, BR-SA-024, BR-SA-027, BR-SA-031.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from modules.system_admin.domain import security_policy
from modules.system_admin.services import security as security_service


def test_password_complexity_rules():
    """BR-SA-027: Password complexity requires length >= 12, upper, lower, digit, special."""
    # Too short (< 12)
    valid, msg = security_policy.check_password_complexity("Short1!")
    assert valid is False
    assert "at least 12" in msg

    # Missing uppercase
    valid, msg = security_policy.check_password_complexity("alllowercase123!@#")
    assert valid is False
    assert "uppercase" in msg

    # Missing lowercase
    valid, msg = security_policy.check_password_complexity("ALLLOWERCASE123!@#")
    assert valid is False
    assert "lowercase" in msg

    # Missing digit
    valid, msg = security_policy.check_password_complexity("NoDigitsHereSpecial!@#")
    assert valid is False
    assert "digit" in msg

    # Missing special char
    valid, msg = security_policy.check_password_complexity("NoSpecialChars12345")
    assert valid is False
    assert "special character" in msg

    # Valid strong password
    valid, msg = security_policy.check_password_complexity("SuperAdminSecure2026!#")
    assert valid is True
    assert msg == ""


def test_failed_login_alerting_threshold():
    """BR-SA-024: Trigger alert after threshold consecutive failed logins."""
    assert security_policy.is_failed_login_alert_triggered(4, threshold=5) is False
    assert security_policy.is_failed_login_alert_triggered(5, threshold=5) is True
    assert security_policy.is_failed_login_alert_triggered(6, threshold=5) is True


def test_session_inactivity_expiration():
    """BR-SA-027: Session expires when inactivity exceeds timeout_minutes."""
    now = datetime.datetime(2026, 6, 1, 12, 0, 0)
    last_active_recent = now - datetime.timedelta(minutes=10)
    last_active_old = now - datetime.timedelta(minutes=31)

    assert security_policy.is_session_expired(last_active_recent, timeout_minutes=30, now=now) is False
    assert security_policy.is_session_expired(last_active_old, timeout_minutes=30, now=now) is True


def test_password_rotation_interval():
    """BR-SA-031: Password rotation due check."""
    now = datetime.datetime(2026, 6, 1, 12, 0, 0)
    changed_recently = now - datetime.timedelta(days=45)
    changed_long_ago = now - datetime.timedelta(days=91)

    assert security_policy.is_password_rotation_due(changed_recently, rotation_days=90, now=now) is False
    assert security_policy.is_password_rotation_due(changed_long_ago, rotation_days=90, now=now) is True


def test_token_hashing_consistency():
    """Token hashing is deterministic SHA-256."""
    t1 = "raw_super_admin_bearer_token"
    h1 = security_service.hash_token(t1)
    h2 = security_service.hash_token(t1)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string length
