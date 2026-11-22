"""Audit logging and versioned system parameter models."""

from django.db import models

from core.db.mixins import TimeStampedModel


class AuditLogRecord(TimeStampedModel):
    event_type = models.CharField(max_length=128, db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    target_entity = models.CharField(max_length=64, db_index=True)
    target_id = models.CharField(max_length=128, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action_details = models.JSONField(default=dict)
    is_immutable = models.BooleanField(default=True)

    class Meta:
        db_table = "superadmin_audit_log"
        indexes = [
            models.Index(fields=["actor_user_id", "created_at"], name="sa_aud_actor_dt_idx"),
            models.Index(fields=["event_type", "created_at"], name="sa_aud_evt_dt_idx"),
        ]


class SystemParameterPolicy(TimeStampedModel):
    parameter_key = models.CharField(max_length=128, db_index=True)
    parameter_value = models.JSONField(default=dict)
    version = models.IntegerField(default=1)
    effective_from = models.DateTimeField(db_index=True)
    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "superadmin_system_parameter"
        constraints = [
            models.UniqueConstraint(
                fields=["parameter_key", "version"],
                name="sa_sys_param_key_ver_unique",
            ),
        ]
