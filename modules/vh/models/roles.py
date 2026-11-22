# Operational role holder records and transfers for VHMS.
from django.db import models
from django.db.models import Index, Q, UniqueConstraint

from core.db.mixins import TimeStampedModel


class OperationalRoleHolder(TimeStampedModel):
    # Tracks the active Caretaker and VH In-Charge and enforces single active role holder.
    role_name = models.CharField(
        max_length=30,
        choices=[("caretaker", "Caretaker"), ("incharge", "VH In-Charge")],
        db_index=True,
    )
    user_id = models.IntegerField(db_index=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_operational_role_holder"
        indexes = [
            Index(fields=["role_name", "is_active"], name="vh_role_active_idx"),
        ]
        constraints = [
            UniqueConstraint(
                fields=["role_name"],
                condition=Q(is_active=True),
                name="vh_unique_active_op_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role_name}: user_id {self.user_id} (active={self.is_active})"
