from django.db import models
from django.utils.translation import gettext as _

class LeaveRequest(models.Model):
    user_id = models.IntegerField()
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under review"),
        ("shortlisted", "Shortlisted"),
        ("interview_scheduled", "Interview scheduled"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("auto_withdrawn", "Withdrawn automatically"),
        ("offer_issued", "Offer issued"),
        ("offer_accepted", "Offer accepted"),
        ("offer_declined", "Offer declined"),
        ("offer_expired", "Offer expired"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["user_id", "created_at"]
        indexes = [
            models.Index(fields=["user_id"], name="leave_request_user_idx"),
            models.Index(fields=["status"], name="leave_request_status_idx"),
        ]

    def __str__(self):
        return f"LeaveRequest {self.id} for user {self.user_id}"

    class LeaveType(models.TextChoices):
        FULL_DAY = "FD", _("Full Day")
        HALF_DAY = "HD", _("Half Day")

    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, choices=LeaveType.choices)
