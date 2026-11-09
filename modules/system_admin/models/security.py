"""Security tracking models: active sessions, failed logins, and 2FA credentials."""
from django.db import models

from core.db.mixins import TimeStampedModel


class SuperAdminSession(TimeStampedModel):
    """Enforces single active Super Admin session policy (CFR-SA-021, BR-SA-027)."""

    session_token_hash = models.CharField(max_length=64, primary_key=True)
    admin_user_id = models.IntegerField(db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    login_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    termination_reason = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "system_admin_session"

    def __str__(self):
        return f"Session: Admin {self.admin_user_id} [{'active' if self.is_active else 'terminated'}]"


class FailedLoginAttempt(models.Model):
    """Tracks failed Super Admin logins for consecutive threshold alerts (BR-SA-024)."""

    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField()
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    failure_reason = models.CharField(max_length=64)
    consecutive_failure_count = models.PositiveSmallIntegerField(default=1)
    alert_triggered = models.BooleanField(default=False)

    class Meta:
        db_table = "system_admin_failed_login_attempt"
        ordering = ["-attempted_at"]

    def __str__(self):
        return f"FailedLogin: {self.username} from {self.ip_address} (count={self.consecutive_failure_count})"


class TwoFactorCredential(TimeStampedModel):
    """Stores TOTP secret and backup recovery credentials."""

    admin_user_id = models.IntegerField(primary_key=True)
    totp_secret_encrypted = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    backup_codes_hashes = models.JSONField(default=list)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_2fa_credential"

    def __str__(self):
        return f"2FA Credential: Admin {self.admin_user_id} [{'enabled' if self.is_enabled else 'disabled'}]"
