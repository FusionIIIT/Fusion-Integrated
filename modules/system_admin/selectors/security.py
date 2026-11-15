"""Security, sessions, and failed logins selectors for system_admin."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.utils import timezone

from modules.system_admin.models import (
    FailedLoginAttempt,
    SuperAdminSession,
    TwoFactorCredential,
)


def get_active_admin_session(admin_user_id: int) -> Optional[SuperAdminSession]:
    """Retrieve active session for admin user (BR-SA-027 single session rule)."""
    return (
        SuperAdminSession.objects.filter(
            admin_user_id=admin_user_id,
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-login_at")
        .first()
    )


def get_session_by_token_hash(token_hash: str) -> Optional[SuperAdminSession]:
    """Lookup session by SHA-256 token hash."""
    if not token_hash:
        return None
    return SuperAdminSession.objects.filter(session_token_hash=token_hash).first()


def get_consecutive_failed_logins(username: str, window_minutes: int = 30) -> int:
    """Count failed logins in time window (BR-SA-024)."""
    if not username:
        return 0
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    return FailedLoginAttempt.objects.filter(
        username=username.strip(),
        attempted_at__gte=cutoff,
    ).count()


def get_two_factor_credential(admin_user_id: int) -> Optional[TwoFactorCredential]:
    """Retrieve 2FA credential record for admin."""
    return TwoFactorCredential.objects.filter(admin_user_id=admin_user_id).first()
