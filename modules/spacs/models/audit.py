"""Immutable, tamper-resistant system audit log for SPACS.

Enforces:
- CFR-SPACS-016 (Audit Trail)
- AFR-SPACS-049 (Audit records for significant SPACS actions)
- AFR-SPACS-050 / BR-SPACS-021 (Protect audit records from ordinary modification)
- UC-SPACS-021 (View SPACS Audit Trail)
"""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import models


class SpacsAuditLog(models.Model):
    """Immutable audit record.

    Protected against in-place edits and row deletions at the ORM level.
    """

    action = models.CharField(max_length=80, editable=False, db_index=True)
    entity_type = models.CharField(max_length=40, editable=False, db_index=True)
    entity_id = models.CharField(max_length=60, editable=False, db_index=True)
    actor_user_id = models.IntegerField(null=True, blank=True, editable=False, db_index=True)
    actor_role = models.CharField(max_length=60, blank=True, editable=False)
    details = models.JSONField(default=dict, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)

    class Meta:
        db_table = "spacs_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="spacs_audit_entity_idx"),
            models.Index(fields=["actor_user_id", "created_at"], name="spacs_audit_actor_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("SPACS audit records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("SPACS audit records cannot be deleted.")

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.action} on {self.entity_type}#{self.entity_id} by u{self.actor_user_id}"
