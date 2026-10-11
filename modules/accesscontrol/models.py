"""The module registry — what modules exist and where they live in the UI.

A module is a ROW here, not a boolean column keyed by a designation name as in
the legacy ModuleAccess table, so adding one is an insert rather than a schema
migration and renaming a role cannot silently break access. Who may enter is
IAM's decision and arrives in the token.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class Module(TimeStampedModel):
    STATUS = [("planned", "Planned"), ("active", "Active"),
              ("deprecated", "Deprecated")]

    code = models.CharField(max_length=48, unique=True)      # placement_cell
    label = models.CharField(max_length=80)                  # "Placement Cell"
    icon = models.CharField(max_length=48, default="FaCircle")
    base_path = models.CharField(max_length=80)              # /placement
    nav_section = models.CharField(max_length=48, default="Modules")
    sort_order = models.PositiveSmallIntegerField(default=100)
    status = models.CharField(max_length=16, choices=STATUS, default="planned")

    class Meta:
        db_table = "accesscontrol_module"
        ordering = ["nav_section", "sort_order", "label"]

    def __str__(self) -> str:
        return self.code


class NavItem(TimeStampedModel):
    """A link inside a module. Hidden unless the caller holds
    `required_permission`, so two roles can share a module and still see
    different menus."""

    module = models.ForeignKey(Module, on_delete=models.CASCADE,
                               related_name="nav_items")
    code = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=80)
    icon = models.CharField(max_length=48, default="FaCircle")
    to = models.CharField(max_length=160)
    required_permission = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "accesscontrol_nav_item"
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.code


class LeaveType(TimeStampedModel):
    """Represents different types of leaves available."""
    code = models.CharField(max_length=48, unique=True)
    label = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "accesscontrol_leave_type"
        ordering = ["label"]

    def __str__(self) -> str:
        return self.label


class LeaveBalance(TimeStampedModel):
    """Represents the balance of leaves for a user."""
    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "accesscontrol_leave_balance"
        unique_together = ("user", "leave_type")
        ordering = ["user", "leave_type"]

    def __str__(self) -> str:
        return f"{self.user} - {self.leave_type}"


class LeaveApplication(TimeStampedModel):
    """Represents a leave application made by a user."""
    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending")
    reason = models.TextField()

    class Meta:
        db_table = "accesscontrol_leave_application"
        ordering = ["user", "start_date"]

    def __str__(self) -> str:
        return f"{self.user} - {self.leave_type} - {self.start_date} to {self.end_date}"


class SubstituteNominee(TimeStampedModel):
    """Represents a substitute nominee for a leave application."""
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending")

    class Meta:
        db_table = "accesscontrol_substitute_nominee"
        unique_together = ("leave_application", "user")
        ordering = ["leave_application", "user"]

    def __str__(self) -> str:
        return f"{self.leave_application} - {self.user}"
