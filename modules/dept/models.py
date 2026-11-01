"""Department tables. Person columns are plain integers (ADR-0013): the user
lives in IAM, never behind a foreign key."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.dept.domain import state_machine as sm


# -- announcements (UC-DEPT-001..003) ---------------------------------------
class Announcement(TimeStampedModel):
    ACTIVE, HIDDEN, DELETED = "active", "hidden", "deleted"
    STATUS = [(ACTIVE, "Active"), (HIDDEN, "Hidden"), (DELETED, "Deleted")]

    title = models.CharField(max_length=200)
    body = models.TextField()
    # Empty list = everyone on that axis (see domain/visibility.py).
    target_roles = models.JSONField(default=list, blank=True)
    target_programmes = models.JSONField(default=list, blank=True)
    target_years = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=8, choices=STATUS, default=ACTIVE)
    published_by_user_id = models.IntegerField()
    published_by_role = models.CharField(max_length=40, blank=True)
    # Soft delete: BR-DEPT-004 says "delete", the audit trail says keep the row.
    moderated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "dept_announcement"
        constraints = [models.CheckConstraint(
            condition=Q(status__in=["active", "hidden", "deleted"]),
            name="dept_announcement_status_valid")]
        indexes = [models.Index(fields=["status", "-created_at"],
                                name="dept_announce_recent_idx")]


# -- stock & inventory (UC-DEPT-004..006) ------------------------------------
class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=60, blank=True)
    unit = models.CharField(max_length=20, default="pcs")
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "dept_inventory_item"
        ordering = ["name"]


class _AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Stock movements are immutable (BR-DEPT-016).")

    def delete(self):
        raise RuntimeError("Stock movements are immutable (BR-DEPT-016).")

    bulk_update = update


class StockMovement(models.Model):
    """BR-DEPT-016: appended on every insertion and issue, never altered."""

    INSERT, ISSUE = "insert", "issue"
    KIND = [(INSERT, "Insertion"), (ISSUE, "Issue")]

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="movements")
    kind = models.CharField(max_length=6, choices=KIND)
    quantity = models.PositiveIntegerField()
    request = models.ForeignKey("dept.StockRequest", null=True, blank=True,
                                on_delete=models.PROTECT,
                                related_name="movements")
    recipient_user_id = models.IntegerField(null=True, blank=True)
    actor_user_id = models.IntegerField()
    at = models.DateTimeField(auto_now_add=True)

    objects = _AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "dept_stock_movement"
        indexes = [models.Index(fields=["item", "-at"],
                                name="dept_movement_item_idx"),
                   models.Index(fields=["recipient_user_id", "-at"],
                                name="dept_movement_recipient_idx")]

    def __str__(self) -> str:
        return f"{self.kind} {self.quantity} x item {self.item_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("Stock movements are immutable (BR-DEPT-016).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Stock movements are immutable (BR-DEPT-016).")


class StockRequest(TimeStampedModel):
    STATUS = [(sm.PENDING_HOD, "Pending HOD approval"),
              (sm.APPROVED, "Approved for issuance"),
              (sm.REJECTED, "Rejected"), (sm.ISSUED, "Issued")]

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="requests")
    requested_by_user_id = models.IntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    purpose = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=STATUS,
                              default=sm.PENDING_HOD)

    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dept_stock_request"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0),
                                   name="dept_stock_request_qty_positive"),
            models.CheckConstraint(
                condition=~Q(status="issued") | Q(issued_at__isnull=False),
                name="dept_stock_request_issued_has_timestamp"),
        ]
        indexes = [models.Index(fields=["status", "-created_at"],
                                name="dept_stockreq_status_idx")]


# -- feedback (UC-DEPT-007/008) ----------------------------------------------
class Feedback(TimeStampedModel):
    STATUS = [(sm.NEW, "New"), (sm.UNDER_REVIEW, "Under review"),
              (sm.RESOLVED, "Resolved"), (sm.CLOSED, "Closed")]

    submitted_by_user_id = models.IntegerField(db_index=True)
    submitted_by_role = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default=sm.NEW)
    resolution_note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "dept_feedback"
        constraints = [models.CheckConstraint(
            condition=Q(status__in=["new", "under_review", "resolved", "closed"]),
            name="dept_feedback_status_valid")]
        indexes = [models.Index(fields=["status", "-created_at"],
                                name="dept_feedback_status_idx")]


class FeedbackEvent(models.Model):
    """Append-only trail of who moved a feedback item and why."""

    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE,
                                 related_name="events")
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    actor_user_id = models.IntegerField()
    note = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dept_feedback_event"
        ordering = ["at", "id"]

    def __str__(self) -> str:
        return f"feedback {self.feedback_id}: {self.from_status} -> {self.to_status}"
