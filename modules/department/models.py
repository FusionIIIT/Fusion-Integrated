"""Department-owned records. IAM identities are referenced by integer ID only."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class DepartmentScopedModel(TimeStampedModel):
    department_code = models.CharField(max_length=120, db_index=True)

    class Meta:
        abstract = True


class Announcement(DepartmentScopedModel):
    title = models.CharField(max_length=180)
    body = models.TextField(max_length=5000)
    target_roles = models.JSONField(default=list, blank=True)
    target_programmes = models.JSONField(default=list, blank=True)
    target_academic_years = models.JSONField(default=list, blank=True)
    created_by_user_id = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=12,
        choices=(("active", "Active"), ("hidden", "Hidden"),
                 ("deleted", "Deleted")),
        default="active",
        db_index=True,
    )

    class Meta:
        db_table = "department_announcement"
        ordering = ["-created_at"]


class InventoryItem(DepartmentScopedModel):
    name = models.CharField(max_length=140)
    description = models.CharField(max_length=500, blank=True)
    quantity = models.IntegerField(default=0)

    class Meta:
        db_table = "department_inventory_item"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["department_code", "name"],
                                    name="dept_inventory_name_unique"),
        ]


class StockRequest(DepartmentScopedModel):
    STATUS = (
        ("pending_hod_approval", "Pending HOD Approval"),
        ("approved_for_issuance", "Approved for Issuance"),
        ("rejected", "Rejected"),
        ("issued", "Issued"),
    )

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="requests")
    faculty_user_id = models.PositiveBigIntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=32, choices=STATUS,
                              default="pending_hod_approval", db_index=True)
    decision_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "department_stock_request"
        ordering = ["-created_at"]


class StockMovement(DepartmentScopedModel):
    MOVEMENT = (("insertion", "Stock inserted"), ("issue", "Stock issued"))

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="movements")
    request = models.ForeignKey(StockRequest, null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name="movements")
    movement = models.CharField(max_length=12, choices=MOVEMENT)
    quantity = models.PositiveIntegerField()
    actor_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "department_stock_movement"
        ordering = ["-created_at"]


class Feedback(DepartmentScopedModel):
    STATUS = (("new", "New"), ("under_review", "Under Review"),
              ("resolved", "Resolved"), ("closed", "Closed"))

    submitter_user_id = models.PositiveBigIntegerField(db_index=True)
    body = models.TextField(max_length=5000)
    category = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="new",
                              db_index=True)
    initial_reviewed_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    initial_reviewed_at = models.DateTimeField(null=True, blank=True)
    handled_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "department_feedback"
        ordering = ["-created_at"]


class ResourceProfile(DepartmentScopedModel):
    name = models.CharField(max_length=140)
    description = models.CharField(max_length=1000, blank=True)
    location = models.CharField(max_length=180, blank=True)
    equipment = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "department_resource_profile"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["department_code", "name"],
                                    name="dept_resource_name_unique"),
        ]


class TimetableEntry(DepartmentScopedModel):
    programme = models.CharField(max_length=80, blank=True)
    academic_year = models.CharField(max_length=24, blank=True)
    course = models.CharField(max_length=120)
    day = models.PositiveSmallIntegerField()  # Monday = 1, Sunday = 7
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    room = models.CharField(max_length=100)
    updated_by_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "department_timetable_entry"
        ordering = ["day", "starts_at"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=models.F("starts_at")),
                                   name="dept_timetable_time_order"),
        ]


class DepartmentDetails(DepartmentScopedModel):
    general = models.JSONField(default=dict, blank=True)
    official = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "department_details"
        constraints = [
            models.UniqueConstraint(fields=["department_code"],
                                    name="dept_details_code_unique"),
        ]


class DepartmentChange(DepartmentScopedModel):
    STATUS = (("pending_hod_approval", "Pending HOD Approval"),
              ("approved", "Approved"), ("rejected", "Rejected"))

    field_name = models.CharField(max_length=80)
    proposed_value = models.JSONField()
    status = models.CharField(max_length=24, choices=STATUS,
                              default="pending_hod_approval", db_index=True)
    proposed_by_user_id = models.PositiveBigIntegerField()
    decided_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "department_change"
        ordering = ["-created_at"]
