"""Database models for MMS module."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class MessRoleAssignment(TimeStampedModel):
    """Tracks time-bound assignments of Mess Caretaker and Mess Warden roles (BR-MMS-002..007)."""
    ROLE_CHOICES = [
        ("mess_caretaker", "Mess Caretaker"),
        ("mess_warden", "Mess Warden"),
    ]

    role_name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    assigned_user_id = models.IntegerField(db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_role_assignment"
        ordering = ["-created_at"]


class MessRegistrationWindow(TimeStampedModel):
    """Registration window opened by Caretaker at cycle start (BR-MMS-008, 009)."""
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    opened_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_registration_window"
        ordering = ["-created_at"]


class MessRegistration(TimeStampedModel, UserScopedModel):
    """Student registration request and status (CFR-MMS-004, BR-MMS-009, 010)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    window = models.ForeignKey(
        MessRegistrationWindow,
        on_delete=models.CASCADE,
        related_name="registrations",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    reason = models.TextField(blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_registration"
        ordering = ["-created_at"]


class MessDeregistration(TimeStampedModel, UserScopedModel):
    """Student deregistration with next-day effective date (CFR-MMS-005, BR-MMS-012, 013)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    registration = models.ForeignKey(
        MessRegistration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deregistrations",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    reason = models.TextField()
    effective_date = models.DateField(null=True, blank=True)
    is_active_deregistration = models.BooleanField(default=False)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_deregistration"
        ordering = ["-created_at"]


class MessMenu(TimeStampedModel):
    """Weekly mess menu day-wise and meal-wise (BR-MMS-014, 015, 038, 039)."""
    DAY_CHOICES = [
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
    ]
    MEAL_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
    ]

    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    items = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_menu"
        unique_together = [("day_of_week", "meal_type")]


class MessRebate(TimeStampedModel, UserScopedModel):
    """Student rebate request and adjustment records (CFR-MMS-011, BR-MMS-021..025)."""
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")

    original_start_date = models.DateField(null=True, blank=True)
    original_end_date = models.DateField(null=True, blank=True)
    modified_by_caretaker = models.BooleanField(default=False)

    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_rebate"
        ordering = ["-created_at"]


class VacationFoodSurvey(TimeStampedModel):
    """Vacation food continuity survey created by Caretaker (CFR-MMS-012, BR-MMS-026, 027)."""
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    title = models.CharField(max_length=255)
    vacation_start_date = models.DateField()
    vacation_end_date = models.DateField()
    response_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_vacation_survey"
        ordering = ["-created_at"]


class VacationFoodResponse(TimeStampedModel, UserScopedModel):
    """Student response to vacation survey (BR-MMS-027, 041)."""
    survey = models.ForeignKey(
        VacationFoodSurvey, on_delete=models.CASCADE, related_name="responses"
    )
    requires_food = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_vacation_response"
        unique_together = [("survey", "user_id")]


class SpecialFoodRequest(TimeStampedModel, UserScopedModel):
    """Special food request lifecycle (CFR-MMS-013, BR-MMS-028..031)."""
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
    ]

    requested_date = models.DateField()
    meal_type = models.CharField(max_length=20)
    food_details = models.TextField()
    reason = models.TextField()
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    is_default_rejected = models.BooleanField(default=False)

    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_special_food"
        ordering = ["-created_at"]


class MessBill(TimeStampedModel, UserScopedModel):
    """Monthly calendar billing computation and publication (CFR-MMS-009, BR-MMS-016..019, 040)."""
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("generated", "Generated"),
        ("published", "Published"),
    ]

    billing_month = models.DateField()  # e.g. 2026-05-01
    base_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    rebate_discount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    special_food_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="generated")

    generated_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_bill"
        unique_together = [("billing_month", "user_id")]
        ordering = ["-billing_month"]


class MessAnnouncement(TimeStampedModel):
    """Announcements published by Caretaker or Warden (BR-MMS-032, 033)."""
    title = models.CharField(max_length=255)
    content = models.TextField()
    published_by_user_id = models.IntegerField()
    published_by_role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mms_announcement"
        ordering = ["-created_at"]


class MessFeedback(TimeStampedModel, UserScopedModel):
    """Student text feedback for supervisory and operational review (BR-MMS-020)."""
    description = models.TextField()
    category = models.CharField(max_length=50, blank=True, default="general")

    class Meta:
        db_table = "mms_feedback"
        ordering = ["-created_at"]


class MmsNotification(TimeStampedModel):
    """System-generated email notification trigger log (BR-MMS-035)."""
    recipient_user_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "mms_notification"
        ordering = ["-created_at"]
