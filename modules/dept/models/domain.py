from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class Department(TimeStampedModel):
    code = models.CharField(max_length=48, primary_key=True)
    name = models.CharField(max_length=120)
    general_info = models.JSONField(default=dict, blank=True)
    official_info = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "dept_department"


class Announcement(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    author_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField()
    target_roles = models.JSONField(default=list)
    programme = models.CharField(max_length=80, blank=True)
    academic_year = models.CharField(max_length=16, blank=True)
    published = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dept_announcement"
        indexes = [
            models.Index(fields=["department", "published", "hidden"], name="dept_ann_visible_idx")
        ]


class InventoryItem(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    on_hand = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "dept_inventory_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(reserved__lte=F("on_hand")), name="dept_item_res_le_onhand"
            ),
        ]
        indexes = [models.Index(fields=["department", "active", "name"], name="dept_item_list_idx")]


class StockRequest(TimeStampedModel):
    STATUS = [
        (x, x.replace("_", " ").title())
        for x in ("pending", "approved", "rejected", "issued", "cancelled")
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    requester_user_id = models.IntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending", db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "dept_stock_request"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="dept_request_positive_qty")
        ]
        indexes = [
            models.Index(fields=["department", "status", "created_at"], name="dept_req_queue_idx")
        ]


class StockMovement(TimeStampedModel):
    KIND = [(x, x.title()) for x in ("insert", "reserve", "release", "issue")]
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    request = models.ForeignKey(StockRequest, null=True, blank=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=KIND)
    quantity = models.PositiveIntegerField()
    actor_user_id = models.IntegerField()
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "dept_stock_movement"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="dept_movement_positive_qty")
        ]
        indexes = [
            models.Index(fields=["department", "item", "created_at"], name="dept_move_audit_idx")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Stock movements are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Stock movements are immutable.")


class Feedback(TimeStampedModel):
    STATUS = [
        (x, x.replace("_", " ").title()) for x in ("new", "under_review", "resolved", "closed")
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    submitter_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField()
    category = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="new", db_index=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dept_feedback"
        indexes = [
            models.Index(
                fields=["department", "status", "created_at"], name="dept_feedback_queue_idx"
            )
        ]


class UserProfile(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    user_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=16)
    programme = models.CharField(max_length=80, blank=True)
    discipline = models.CharField(max_length=80, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "dept_user_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["department", "user_id"], name="dept_profile_user_unique"
            )
        ]


class TimetableSlot(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    cohort = models.CharField(max_length=80)
    resource = models.CharField(max_length=80)
    weekday = models.PositiveSmallIntegerField()
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    instructor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "dept_timetable_slot"
        constraints = [
            models.CheckConstraint(
                condition=Q(weekday__gte=1, weekday__lte=7), name="dept_slot_weekday_valid"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="dept_slot_time_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["department", "weekday", "starts_at"], name="dept_slot_list_idx")
        ]


class LabResource(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    details = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "dept_lab_resource"
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="dept_resource_name_unique")
        ]


class DepartmentChange(TimeStampedModel):
    STATUS = [(x, x.title()) for x in ("pending", "approved", "rejected")]
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    proposed_by_user_id = models.IntegerField()
    proposed = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dept_department_change"
        indexes = [
            models.Index(
                fields=["department", "status", "created_at"], name="dept_change_queue_idx"
            )
        ]


class Notification(TimeStampedModel):
    recipient_user_id = models.IntegerField(db_index=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    event = models.CharField(max_length=64)
    subject = models.CharField(max_length=180)
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    email_attempts = models.PositiveSmallIntegerField(default=0)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "dept_notification"
        indexes = [
            models.Index(
                fields=["recipient_user_id", "read_at", "created_at"], name="dept_notify_inbox_idx"
            )
        ]
