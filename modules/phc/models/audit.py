"""Immutable sensitive-data audit trail (CFR-PHC-012, AFR-PHC-037; PHC-BR-09)."""
from django.db import models


class PHCAuditTrail(models.Model):
    """Immutable audit records for sensitive data operations (BR-09).

    Scoped strictly to:
    - Patient records (visit & prescription creation)
    - Inventory levels (manual adjustments)
    - Reimbursement claim status changes
    """
    TARGET_TYPE_CHOICES = [
        ("PATIENT_RECORD", "Patient Record"),
        ("INVENTORY_LEVEL", "Inventory Level"),
        ("REIMBURSEMENT_CLAIM", "Reimbursement Claim"),
    ]

    target_type = models.CharField(max_length=40, choices=TARGET_TYPE_CHOICES, db_index=True)
    target_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=64)
    details = models.TextField(help_text="Immutable JSON or textual description of the action taken")
    actor_user_id = models.IntegerField(db_index=True)
    actor_username = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "phc_audit_trail"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.target_type}] {self.action} on {self.target_id} by {self.actor_username} at {self.created_at}"
