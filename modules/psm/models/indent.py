# Purchase indents, version snapshots, transitions, and internal issues (CFR-PSM-001..005).
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.psm.domain import state_machine as sm


class Indent(TimeStampedModel, UserScopedModel):
    PRIORITY = [("normal", "Normal"), ("high", "High"), ("critical", "Critical")]
    METHOD = [
        ("", "Undecided"),
        ("internal", "Internal Stock"),
        ("direct", "Direct Purchase"),
        ("tender", "Tender"),
    ]
    STATUS = [(s, s.replace("_", " ").title()) for s in sm.INDENT_STATES]

    indent_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    department = models.CharField(max_length=64)
    item = models.ForeignKey(
        "StockItem", on_delete=models.PROTECT, null=True, blank=True, related_name="indents"
    )
    item_description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField()
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2)
    justification = models.TextField()
    priority = models.CharField(max_length=16, choices=PRIORITY, default="normal")
    status = models.CharField(max_length=32, choices=STATUS, default=sm.DRAFT)
    procurement_method = models.CharField(max_length=16, choices=METHOD, default="", blank=True)
    is_duplicate_flagged = models.BooleanField(default=False)
    duplicate_of_indent_id = models.IntegerField(null=True, blank=True)
    duplicate_reviewed = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)
    current_stage_since = models.DateTimeField(null=True, blank=True)
    sla_reminded_at = models.DateTimeField(null=True, blank=True)
    sla_escalated_at = models.DateTimeField(null=True, blank=True)
    repeated_from_indent_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    policy = models.ForeignKey(
        "PsmPolicy", on_delete=models.PROTECT, null=True, blank=True, related_name="indents"
    )

    class Meta:
        db_table = "psm_indent"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0) & Q(estimated_cost__gt=0),
                name="psm_indent_qty_cost_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["department", "status", "-created_at"], name="psm_indent_dept_status_idx"
            ),
            models.Index(fields=["user_id", "-created_at"], name="psm_indent_user_recent_idx"),
            models.Index(
                fields=["status", "priority", "current_stage_since"],
                name="psm_indent_queue_sla_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.indent_number or f'draft#{self.pk}'} ({self.status})"


class IndentVersion(models.Model):
    """Append-only indent snapshot saved on submission and every modification (AFR-PSM-010)."""

    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    actor_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_indent_version"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["indent", "version"], name="psm_indent_version_unique"),
        ]

    def __str__(self) -> str:
        return f"indent#{self.indent_id} v{self.version}"


class IndentTransition(models.Model):
    """Append-only audit trail of indent state changes (BR-PSM-021)."""

    indent = models.ForeignKey(Indent, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_indent_transition"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["indent", "-created_at"], name="psm_indent_trans_idx"),
        ]

    def __str__(self) -> str:
        return f"indent#{self.indent_id} {self.from_status}->{self.to_status}"


class InternalIssue(TimeStampedModel):
    STATUS = [
        ("approved", "Approved"),
        ("picking_scheduled", "Picking Scheduled"),
        ("dispatched", "Dispatched"),
        ("grn_recorded", "GRN Recorded"),
        ("completed", "Completed"),
    ]

    indent = models.OneToOneField(Indent, on_delete=models.PROTECT, related_name="internal_issue")
    location = models.ForeignKey(
        "StockLocation", on_delete=models.PROTECT, related_name="internal_issues"
    )
    reservation = models.ForeignKey(
        "StockReservation", on_delete=models.PROTECT, related_name="internal_issues"
    )
    picking_scheduled_at = models.DateTimeField(null=True, blank=True)
    dispatch_scheduled_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatched_by_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="approved")

    class Meta:
        db_table = "psm_internal_issue"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_internal_issue_status_idx"),
        ]
