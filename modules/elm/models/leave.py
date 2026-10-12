from django.db import models


LEAVE_TYPES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]
    PART_CHOICES = [("full", "Full day"), ("first_half", "First half"), ("second_half", "Second half")]

    user_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    part_of_day = models.CharField(max_length=12, choices=PART_CHOICES, default="full")
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=200, blank=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    decision_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category} application #{self.pk}"


class LeaveBalance(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=LEAVE_TYPES)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ("user_id", "year", "category")
        ordering = ["year", "category"]

    @property
    def available_days(self):
        return self.entitled_days - self.used_days


class LeaveAction(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="actions")
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=24)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
