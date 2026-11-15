"""Pure Python security policies and validations for modules.system_admin.

Enforces Super Admin password complexity, failed login alerting,
session inactivity expiration, and password rotation interval checks.
Free of external dependencies (strictly NO Django, DRF, or Celery).
Traceability: BR-SA-024, BR-SA-027, BR-SA-031.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Tuple


def check_password_complexity(password: str, min_length: int = 12) -> Tuple[bool, str]:
    """BR-SA-027: Strong password validation."""
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must include at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must include at least one special character."
    return True, ""


def is_failed_login_alert_triggered(consecutive_failures: int, threshold: int = 5) -> bool:
    """BR-SA-024: Trigger security alert after threshold consecutive failures."""
    return consecutive_failures >= threshold


def is_session_expired(last_active_at: datetime, timeout_minutes: int, now: datetime) -> bool:
    """BR-SA-027: Enforce inactivity timeout."""
    return (now - last_active_at) > timedelta(minutes=timeout_minutes)


def is_password_rotation_due(last_changed_at: datetime, rotation_days: int, now: datetime) -> bool:
    """BR-SA-031: Check if password rotation interval has elapsed."""
    return (now - last_changed_at) > timedelta(days=rotation_days)
