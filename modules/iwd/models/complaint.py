from django.db import models
from django.db.models import Q


class Complaint(models.Model):
    """Primary IWD maintenance complaint record."""

    CATEGORY_CHOICES = [
        ("civil", "Civil Maintenance"),
        ("electrical", "Electrical Maintenance"),
    ]
    URGENCY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("emergency", "Emergency"),
    ]

    complaint_id = models.CharField(max_length=32, unique=True, db_index=True)
    complainant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=255)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    remarks = models.TextField(blank=True, default="")
    status = models.CharField(max_length=50, default="submitted", db_index=True)
    assigned_engineer_id = models.IntegerField(null=True, blank=True, db_index=True)

    is_urgent_escalated = models.BooleanField(default=False)
    urgent_escalated_at = models.DateTimeField(null=True, blank=True)
    urgent_escalated_to = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_complaint"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(category__in=["civil", "electrical"]),
                name="iwd_valid_complaint_category",
            ),
            models.CheckConstraint(
                check=Q(urgency__in=["low", "medium", "high", "emergency"]),
                name="iwd_valid_complaint_urgency",
            ),
        ]

    def __str__(self):
        return f"{self.complaint_id} ({self.status})"


class RepairAssessment(models.Model):
    """Technical repair assessment completed by assigned engineer."""

    complaint = models.OneToOneField(
        Complaint, on_delete=models.CASCADE, related_name="assessment"
    )
    engineer_id = models.IntegerField()
    assessment_details = models.TextField()
    is_site_visit_complete = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iwd_repair_assessment"
