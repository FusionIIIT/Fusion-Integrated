from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication


class AuditImmutable(Exception):
    """Raised when code tries to change or delete an audit record (BR-PMS-122)."""


class PatentAuditLog(TimeStampedModel):
    """Immutable record of a PMS action: user, action, application, previous and new state
    (PMS-AFR-207..212, BR-PMS-121, BR-PMS-122). The details hold the facts the action
    recorded, e.g. a withdrawal reason or filing confirmation."""

    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    action_type = models.CharField(max_length=64, db_index=True)
    previous_state = models.CharField(max_length=32, blank=True, default="")
    new_state = models.CharField(max_length=32, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "patents_audit_log"
        ordering = ("id",)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutable("Audit records are immutable; record a new entry.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutable("Audit records are immutable and cannot be deleted.")
