"""
ELM Database Models.
Adapted for Fusion cross-module boundaries with integer user references.
"""

from django.db import models


class LeaveType(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    annual_quota = models.PositiveIntegerField(default=0)
    carry_forward = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(models.Model):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField(default=2026)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        unique_together = ("user_id", "leave_type", "year")

    @property
    def remaining(self):
        return self.credited - self.availed


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("SUBSTITUTE_PENDING", "Pending Substitute Consent"),
        ("RECOMMENDED", "Recommended"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    applicant_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    number_of_days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="SUBMITTED")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leave {self.id} by user {self.applicant_id} ({self.status})"


class SubstituteNomination(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="substitutes")
    substitute_id = models.IntegerField(db_index=True)
    duties_description = models.TextField()
    accepted = models.BooleanField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
