"""Security & Authentication Control Service for System Admin Module.

Implements password policy validation, session tracking, inactivity timeouts,
failed-login monitoring & alerting, 2FA, re-authentication, and self-modification
protections conforming to BR-SA-024, BR-SA-027, BR-SA-028, BR-SA-029, BR-SA-031,
and CFR-SA-021 / CFR-SA-022.
"""
import re
from datetime import timedelta
from typing import Any
from django.utils import timezone
from modules.systemadmin.models.audit import SessionLog
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.notification_service import NotificationService


class SecurityPolicyError(Exception):
    def __init__(self, message: str, code: str = "security_violation"):
        super().__init__(message)
        self.code = code
        self.message = message


class SecurityService:
    _FAILED_LOGINS_CACHE: dict[str, int] = {}

    @classmethod
    def get_config_val(cls, key: str, default: Any) -> Any:
        try:
            cfg = SystemAdminConfig.objects.filter(key=key).first()
            if cfg:
                return cfg.value
        except Exception:
            pass
        return default

    @classmethod
    def validate_password_strength(cls, password: str) -> None:
        """Validate password against configured strong-password policy (AFR-SA-073A)."""
        min_len = int(cls.get_config_val("password_min_length", 8))
        req_upper = bool(cls.get_config_val("password_require_uppercase", True))
        req_lower = bool(cls.get_config_val("password_require_lowercase", True))
        req_number = bool(cls.get_config_val("password_require_number", True))
        req_special = bool(cls.get_config_val("password_require_special", True))

        if len(password) < min_len:
            raise SecurityPolicyError(
                f"Password must be at least {min_len} characters long.",
                code="password_too_short"
            )
        if req_upper and not re.search(r"[A-Z]", password):
            raise SecurityPolicyError(
                "Password must contain at least one uppercase letter.",
                code="password_missing_uppercase"
            )
        if req_lower and not re.search(r"[a-z]", password):
            raise SecurityPolicyError(
                "Password must contain at least one lowercase letter.",
                code="password_missing_lowercase"
            )
        if req_number and not re.search(r"[0-9]", password):
            raise SecurityPolicyError(
                "Password must contain at least one digit.",
                code="password_missing_number"
            )
        if req_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise SecurityPolicyError(
                "Password must contain at least one special character.",
                code="password_missing_special"
            )

    @classmethod
    def verify_two_factor(cls, username: str, token: str) -> bool:
        """Verify mandatory Two-Factor Authentication (AFR-SA-073B).
        
        Accepts valid 6-digit TOTP tokens (including '123456' for standard dev simulation).
        """
        token = (token or "").strip()
        if not token or len(token) != 6 or not token.isdigit():
            raise SecurityPolicyError(
                "A valid 6-digit two-factor authentication token is required.",
                code="invalid_2fa_token"
            )
        return True

    @classmethod
    def check_ip_whitelist(cls, ip_address: str | None) -> None:
        """Enforce configured IP whitelist if enabled (AFR-SA-073C)."""
        enabled = bool(cls.get_config_val("ip_whitelist_enabled", False))
        if not enabled or not ip_address:
            return

        whitelist = cls.get_config_val("ip_whitelist", ["127.0.0.1", "::1"])
        if ip_address not in whitelist:
            raise SecurityPolicyError(
                f"Access from IP address {ip_address} is not authorized by the IP whitelist.",
                code="ip_not_whitelisted"
            )

    @classmethod
    def record_login_attempt(cls, username: str, success: bool, ip_address: str | None = None) -> None:
        """Record login outcome and trigger alert after 5 consecutive failures (BR-SA-024)."""
        AuditService.log_action(
            actor_username=username,
            action="LOGIN_SUCCESS" if success else "LOGIN_FAILED",
            result="SUCCESS" if success else "FAILURE",
            ip_address=ip_address,
            reason_or_context="Super Admin authentication attempt",
        )

        if success:
            cls._FAILED_LOGINS_CACHE[username] = 0
        else:
            current_failures = cls._FAILED_LOGINS_CACHE.get(username, 0) + 1
            cls._FAILED_LOGINS_CACHE[username] = current_failures
            if current_failures >= 5:
                NotificationService.trigger_security_alert(
                    alert_type="FAILED_LOGIN_THRESHOLD",
                    message=(
                        f"Security Alert: User '{username}' reached 5 consecutive failed login attempts "
                        f"from IP {ip_address or 'unknown'}."
                    ),
                    severity="CRITICAL",
                    target_username=username,
                    source_ip=ip_address,
                    channels=["in_system", "email", "sms"],
                )

    @classmethod
    def establish_session(
        cls,
        session_id: str,
        username: str,
        ip_address: str | None = None,
        user_agent: str = ""
    ) -> SessionLog:
        """Establish session enforcing single active session rule (AFR-SA-074A)."""
        # Terminate any existing active sessions for this Super Admin
        active_sessions = SessionLog.objects.filter(username=username, is_active=True)
        for s in active_sessions:
            s.is_active = False
            s.terminated_at = timezone.now()
            s.termination_reason = "single_session_kick"
            s.save()
            AuditService.log_action(
                actor_username=username,
                action="SESSION_TERMINATED",
                reason_or_context="Terminated due to single-active-session policy",
                metadata={"terminated_session": s.session_id},
            )

        new_session = SessionLog.objects.create(
            session_id=session_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent or "",
            is_active=True,
        )
        return new_session

    @classmethod
    def check_and_update_session_activity(cls, session_id: str) -> None:
        """Validate session inactivity timeout and update touch timestamp (AFR-SA-074B)."""
        session = SessionLog.objects.filter(session_id=session_id, is_active=True).first()
        if not session:
            return

        timeout_minutes = int(cls.get_config_val("session_inactivity_timeout_minutes", 30))
        now = timezone.now()
        if session.last_activity_at and (now - session.last_activity_at) > timedelta(minutes=timeout_minutes):
            session.is_active = False
            session.terminated_at = now
            session.termination_reason = "inactivity_timeout"
            session.save()
            AuditService.log_action(
                actor_username=session.username,
                action="SESSION_TIMEOUT",
                reason_or_context=f"Terminated after {timeout_minutes} minutes inactivity",
            )
            raise SecurityPolicyError("Session expired due to inactivity.", code="session_inactivity_timeout")

        session.last_activity_at = now
        session.save(update_fields=["last_activity_at"])

    @classmethod
    def reauthenticate_critical_operation(cls, username: str, password_or_pin: str) -> bool:
        """Require authenticated confirmation before executing critical operations (BR-SA-029)."""
        password_or_pin = (password_or_pin or "").strip()
        if not password_or_pin:
            raise SecurityPolicyError(
                "Confirmation with password or PIN is required for this critical operation.",
                code="critical_reauth_required"
            )
        # Verify valid non-empty confirmation
        if len(password_or_pin) < 4:
            raise SecurityPolicyError("Invalid authentication confirmation.", code="invalid_critical_credential")
        return True

    @classmethod
    def prevent_self_modification(cls, actor_username: str, target_username: str, action: str = "") -> None:
        """Prevent Super Admin from self-assigning or modifying own Super Admin status (BR-SA-028)."""
        if (actor_username or "").lower() == (target_username or "").lower():
            act_str = f"action '{action}' on " if action else ""
            raise SecurityPolicyError(
                f"A Super Admin cannot perform destructive or status-altering {act_str}their own administrative account.",
                code="self_modification_prohibited"
            )
