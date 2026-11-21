from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Department(TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    admin_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.name


class Announcement(TimeStampedModel):
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="announcements"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    academic_year = models.CharField(max_length=20, blank=True, db_index=True)
    programme = models.CharField(max_length=40, blank=True, db_index=True)
    role_target = models.CharField(max_length=40, blank=True, db_index=True)
    is_hidden = models.BooleanField(default=False)
    created_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["department", "-created_at"], name="dept_ann_dept_recent_idx")
        ]


class InventoryItem(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="inventory")
    name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="dept_inventory_unique")
        ]


class StockRequest(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("issued", "Issued"),
    ]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="stock_requests"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="requests")
    requester_user_id = models.IntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=STATUS, default="pending", db_index=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)


class StockMovement(TimeStampedModel):
    TYPE = [("insertion", "Insertion"), ("issue", "Issue")]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="stock_movements"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=16, choices=TYPE)
    quantity = models.IntegerField()
    actor_user_id = models.IntegerField(db_index=True)
    request = models.ForeignKey(
        StockRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )


class Feedback(TimeStampedModel):
    STATUS = [
        ("submitted", "Submitted"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="feedback")
    submitter_user_id = models.IntegerField(db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="submitted", db_index=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
    terminal_at = models.DateTimeField(null=True, blank=True)


class DepartmentProfile(TimeStampedModel, UserScopedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="profiles")
    display_name = models.CharField(max_length=150, blank=True)
    kind = models.CharField(max_length=20, blank=True)
    programme = models.CharField(max_length=40, blank=True)
    discipline = models.CharField(max_length=40, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "user_id"], name="dept_profile_unique")
        ]


class Timetable(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="timetables")
    title = models.CharField(max_length=150)
    academic_year = models.CharField(max_length=20, blank=True, db_index=True)
    programme = models.CharField(max_length=40, blank=True, db_index=True)
    uploaded_by_user_id = models.IntegerField(db_index=True)


class TimetableSlot(TimeStampedModel):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="slots")
    day = models.CharField(max_length=16)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=150)
    faculty_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    room = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")), name="dept_slot_time_order"
            )
        ]


class LabResource(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="resources")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    updated_by_user_id = models.IntegerField(db_index=True)


class DepartmentDetail(TimeStampedModel):
    department = models.OneToOneField(Department, on_delete=models.CASCADE, related_name="detail")
    name = models.CharField(max_length=150, blank=True)
    core_policies = models.TextField(blank=True)
    head_user_id = models.IntegerField(null=True, blank=True, db_index=True)


class DepartmentDetailChange(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="detail_changes"
    )
    field_name = models.CharField(max_length=80)
    proposed_value = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="pending", db_index=True)
    proposed_by_user_id = models.IntegerField(db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class NotificationOutbox(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="notifications"
    )
    event = models.CharField(max_length=120, db_index=True)
    recipient_user_id = models.IntegerField(db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
