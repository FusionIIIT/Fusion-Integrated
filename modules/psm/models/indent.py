from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.psm.models.item import ItemMaster


class IndentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    PENDING_DEPT_APPROVAL = "PENDING_DEPT_APPROVAL", "Pending Department Approval"
    PENDING_PS_REVIEW = "PENDING_PS_REVIEW", "Pending PS Review"
    PENDING_DIRECTOR_APPROVAL = "PENDING_DIRECTOR_APPROVAL", "Pending Director Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    FULFILLED = "FULFILLED", "Fulfilled"


class IndentPriority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    EMERGENCY = "EMERGENCY", "Emergency"


class Indent(TimeStampedModel, UserScopedModel):
    """Purchase Indent raised by an employee (user_id)."""

    indent_number = models.CharField(max_length=64, unique=True)
    department_code = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    purpose = models.TextField()
    priority = models.CharField(
        max_length=32,
        choices=IndentPriority.choices,
        default=IndentPriority.NORMAL,
    )
    estimated_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=32,
        choices=IndentStatus.choices,
        default=IndentStatus.DRAFT,
        db_index=True,
    )
    current_approver_role = models.CharField(max_length=64, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "psm_indent"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estimated_total__gte=0),
                name="psm_indent_estimated_total_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(status__in=IndentStatus.values),
                name="psm_indent_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.indent_number} - {self.title} [{self.status}]"


class IndentItem(TimeStampedModel):
    indent = models.ForeignKey(
        Indent,
        related_name="items",
        on_delete=models.CASCADE,
    )
    item_master = models.ForeignKey(
        ItemMaster,
        related_name="indent_items",
        on_delete=models.PROTECT,
    )
    quantity_requested = models.PositiveIntegerField()
    estimated_unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    specifications = models.TextField(blank=True)

    class Meta:
        db_table = "psm_indent_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_requested__gt=0),
                name="psm_indent_item_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(estimated_unit_cost__gte=0),
                name="psm_indent_item_cost_non_negative",
            ),
        ]

    @property
    def total_cost(self) -> Decimal:
        return Decimal(self.quantity_requested) * self.estimated_unit_cost
