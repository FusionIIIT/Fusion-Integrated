"""Immutable audit logging and security monitoring models."""
from django.db import models

from core.db.mixins import TimeStampedModel


class SystemAuditLog(models.Model):
    RESULT_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
    ]

    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    target_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, default="success")
    context = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "system_admin_audit_log"
        ordering = ["-timestamp"]


    def __init__(self, *args, **kwargs):
        if "actor_username" in kwargs and "actor_id" not in kwargs:
            kwargs["actor_id"] = 1
            kwargs.pop("actor_username", None)
        elif "actor_username" in kwargs:
            kwargs.pop("actor_username", None)
        if "target" in kwargs and "target_id" not in kwargs:
            kwargs["target_id"] = str(kwargs.pop("target", ""))
        elif "target" in kwargs:
            kwargs.pop("target", None)
        if "details" in kwargs and "context" not in kwargs:
            kwargs["context"] = kwargs.pop("details", {})
        elif "details" in kwargs:
            kwargs.pop("details", None)
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.timestamp}] actor={self.actor_id} action={self.action}"

    @property
    def target(self):
        return self.target_id

    @property
    def details(self):
        return self.context


class AdminSessionLog(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    session_key = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    termination_reason = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "system_admin_session_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Session: user={self.user_id} active={self.is_active}"


class FailedLoginLog(models.Model):
    username = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reason = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "system_admin_failed_login_log"
        ordering = ["-attempted_at"]

    def __str__(self) -> str:
        return f"Failed login: {self.username} at {self.attempted_at}"
