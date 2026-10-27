"""Employee Leave Management pilot persistence; IAM keeps authoritative identities."""

from django.db import models

CATEGORIES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]


class EmployeeLeaveProfile(models.Model):
    user_id = models.PositiveIntegerField(unique=True)
    category = models.CharField(max_length=10, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    designation = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=255)
    unit_head_user_id = models.PositiveIntegerField(null=True, blank=True)
    sanction_authority_user_id = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"ELM employee {self.user_id}"


class LeaveBalance(models.Model):
    employee_id = models.PositiveIntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    allotted = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_id", "year", "category"], name="elm_unique_balance"
            )
        ]

    def __str__(self):
        return f"{self.employee_id} {self.year} {self.category}"


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=8, choices=[("RH", "Restricted Holiday"), ("CLOSED", "Closed holiday")]
    )
    published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.date} {self.name}"


class LeaveApplication(models.Model):
    employee_id = models.PositiveIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=6,
        choices=[("NONE", "Full day"), ("FIRST", "First half"), ("SECOND", "Second half")],
        default="NONE",
    )
    duration = models.DecimalField(max_digits=7, decimal_places=1)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_location = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=12,
        choices=[
            ("PENDING", "Pending"),
            ("RECOMMENDED", "Under higher sanction"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("WITHDRAWN", "Withdrawn"),
        ],
        default="PENDING",
    )
    unit_head_id = models.PositiveIntegerField()
    sanction_authority_id = models.PositiveIntegerField(null=True, blank=True)
    recommendation = models.CharField(max_length=24, blank=True)
    approver_id = models.PositiveIntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ELM application {self.pk}: {self.employee_id}"


class LeaveEvent(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.PROTECT, related_name="events"
    )
    actor_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ELM event {self.pk}: {self.action}"
