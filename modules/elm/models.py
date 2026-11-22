import uuid

from django.core.validators import MinValueValidator
from django.db import models


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveState(models.TextChoices):
    DRAFT = "Draft", "Draft"
    AWAITING_SUBSTITUTE = "Awaiting Substitute Response", "Awaiting Substitute Response"
    AWAITING_DIRECTOR = "Awaiting Director Self-Sanction", "Awaiting Director Self-Sanction"
    AWAITING_UNIT_HEAD = "Awaiting Unit Head Review", "Awaiting Unit Head Review"
    AWAITING_ESTABLISHMENT = "Awaiting Establishment Routing", "Awaiting Establishment Routing"
    APPLICANT_ACTION = "Applicant Action Required", "Applicant Action Required"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    AWAITING_FINAL = "Awaiting Final Sanction Decision", "Awaiting Final Sanction Decision"
    WITHDRAWN = "Withdrawn", "Withdrawn"


class Employee(models.Model):
    user = models.OneToOneField(
        "directory.UserRef",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="elm_employee",
    )
    eid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=120, blank=True)
    is_faculty = models.BooleanField(default=False)
    is_director = models.BooleanField(default=False)
    unit = models.ForeignKey(
        "Unit", on_delete=models.PROTECT, null=True, blank=True, related_name="employees"
    )

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=200, unique=True)
    head = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="headed_units"
    )

    def __str__(self):
        return self.name


class HierarchyConfiguration(models.Model):
    establishment_configured = models.BooleanField(default=False)
    establishment_role = models.CharField(max_length=120, blank=True)
    establishment_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="establishment_configurations",
    )
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return (
            self.establishment_role if self.establishment_configured else "Direct sanction routing"
        )


class SanctioningAuthorityRule(models.Model):
    applicant = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="authority_rules"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices, blank=True)
    authority = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="sanctioning_assignments"
    )
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category or 'All categories'}: {self.authority_id}"


class LeavePolicy(models.Model):
    name = models.CharField(max_length=200)
    cl_days = models.DecimalField(max_digits=5, decimal_places=1, default=8)
    rh_days = models.DecimalField(max_digits=5, decimal_places=1, default=2)
    scl_days = models.DecimalField(max_digits=5, decimal_places=1, default=15)
    el_days = models.DecimalField(max_digits=5, decimal_places=1, default=30)
    col_days = models.DecimalField(max_digits=5, decimal_places=1, default=20)
    vl_days = models.DecimalField(max_digits=5, decimal_places=1, default=60)
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class HolidayCalendar(models.Model):
    name = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "year"], name="elm_calendar_name_year")
        ]

    def __str__(self):
        return f"{self.name} ({self.year})"


class HolidayDate(models.Model):
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="dates")
    date = models.DateField()
    is_restricted_holiday = models.BooleanField(default=False)
    is_vacation_period = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="elm_calendar_date")
        ]

    def __str__(self):
        return str(self.date)


class LeaveApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="leave_applications"
    )
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    num_days = models.DecimalField(
        max_digits=5, decimal_places=1, validators=[MinValueValidator(0.5)]
    )
    first_half = models.BooleanField(default=False)
    second_half = models.BooleanField(default=False)
    substitute = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="substitute_assignments",
    )
    unit_head = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="unit_head_reviews"
    )
    sanctioning_authority = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sanctioning_reviews",
    )
    state = models.CharField(max_length=50, choices=LeaveState.choices, default=LeaveState.DRAFT)
    unit_head_recommendation = models.CharField(
        max_length=20,
        default="",
        blank=True,
        choices=[("Recommended", "Recommended"), ("Not Recommended", "Not Recommended")],
    )
    station_leave_details = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category} {self.start_date}-{self.end_date}: {self.state}"


class LeaveUsage(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_usage")
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    year = models.PositiveSmallIntegerField()
    used_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "category", "year"], name="elm_usage_employee_category_year"
            )
        ]

    def __str__(self):
        return f"{self.employee_id} {self.category} {self.year}: {self.used_days}"


class SubstituteResponse(models.Model):
    application = models.OneToOneField(
        LeaveApplication, on_delete=models.CASCADE, related_name="substitute_response"
    )
    substitute = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="substitute_responses"
    )
    response = models.CharField(
        max_length=8,
        choices=[("Accepted", "Accepted"), ("Declined", "Declined")],
        blank=True,
        default="",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.application_id}: {self.response or 'Pending'}"


class AssignmentNotification(models.Model):
    recipient = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="elm_notifications"
    )
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.kind}: {self.recipient_id}"
