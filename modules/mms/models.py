"""MMS-owned operational records. IAM identities are stored as scalar IDs."""

from django.db import models

MMS_ROLE_CHOICES = [("caretaker", "Caretaker"), ("warden", "Warden")]


class RoleSlot(models.Model):
    """A lock target that serializes assignments for each exclusive role."""

    role = models.CharField(max_length=16, choices=MMS_ROLE_CHOICES, unique=True)

    def __str__(self):
        return f"RoleSlot ({self.pk})"


class RoleAssignment(models.Model):
    role = models.CharField(max_length=16, choices=MMS_ROLE_CHOICES)
    user_id = models.BigIntegerField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    recorded_by_user_id = models.BigIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gt=models.F("starts_at")),
                name="mms_role_dates_valid",
            )
        ]
        indexes = [
            models.Index(fields=["role", "starts_at", "ends_at"], name="mms_role_active_idx")
        ]

    def __str__(self):
        return f"RoleAssignment ({self.pk})"


class RegistrationWindow(models.Model):
    cycle = models.CharField(max_length=80, unique=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    created_by_user_id = models.BigIntegerField()

    def __str__(self):
        return f"RegistrationWindow ({self.pk})"


class StudentRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REGISTERED = "registered", "Registered"
        DEREGISTERED = "deregistered", "Deregistered"
        REJECTED = "rejected", "Rejected"

    user_id = models.BigIntegerField(db_index=True)
    cycle = models.CharField(max_length=80, db_index=True)
    request_type = models.CharField(
        max_length=16, choices=[("register", "Register"), ("deregister", "Deregister")]
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    decided_by_user_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user_id", "cycle", "-submitted_at"], name="mms_reg_user_cycle_idx"
            )
        ]

    def __str__(self):
        return f"StudentRegistration ({self.pk})"


class MenuItem(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    week_start = models.DateField(db_index=True)
    day = models.PositiveSmallIntegerField(choices=Day.choices)
    meal = models.CharField(
        max_length=12,
        choices=[("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")],
    )
    item = models.CharField(max_length=160)
    updated_by_user_id = models.BigIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MenuItem ({self.pk})"


class RebateRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Reason(models.TextChoices):
        MEDICAL = "medical", "Medical"
        INSTITUTE_LEAVE = "institute_leave", "Institute leave"
        FAMILY_FUNCTION = "family_function", "Family function"
        OTHER = "other", "Other"

    user_id = models.BigIntegerField(db_index=True)
    reason = models.CharField(max_length=24, choices=Reason.choices)
    explanation = models.CharField(max_length=500, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user_id", "start_date", "end_date"], name="mms_rebate_overlap_idx"
            )
        ]

    def __str__(self):
        return f"RebateRequest ({self.pk})"


class VacationSurvey(models.Model):
    title = models.CharField(max_length=160)
    vacation_start = models.DateField()
    vacation_end = models.DateField()
    response_deadline = models.DateTimeField()
    created_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"VacationSurvey ({self.pk})"


class VacationResponse(models.Model):
    survey = models.ForeignKey(VacationSurvey, on_delete=models.CASCADE, related_name="responses")
    user_id = models.BigIntegerField(db_index=True)
    # NULL means unanswered; an empty string would hide the pending lifecycle.
    response = models.CharField(  # noqa: DJ001
        max_length=3, choices=[("yes", "Yes"), ("no", "No")], null=True, blank=True
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    defaulted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["survey", "user_id"], name="mms_vacation_one_response")
        ]

    def __str__(self):
        return f"VacationResponse ({self.pk})"


class SpecialFoodRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SERVED = "served", "Served"
        CANCELLED = "cancelled", "Cancelled"

    user_id = models.BigIntegerField(db_index=True)
    requested_date = models.DateField()
    description = models.CharField(max_length=500)
    charge = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decision_deadline = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"SpecialFoodRequest ({self.pk})"


class Feedback(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    text = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback ({self.pk})"


class Announcement(models.Model):
    owner_role = models.CharField(max_length=12, choices=MMS_ROLE_CHOICES)
    title = models.CharField(max_length=160)
    body = models.TextField(max_length=4000)
    created_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement ({self.pk})"
