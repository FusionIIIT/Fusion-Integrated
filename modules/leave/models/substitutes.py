from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class SubstituteRequest(TimeStampedModel, UserScopedModel):
    application = models.ForeignKey("leave.LeaveApplication", on_delete=models.CASCADE, related_name="substitute_requests")
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, default="pending", choices=[
        ("pending", "Pending Consent"),
        ("accepted", "Accepted"),
        ("declined", "Declined")
    ])
    responsibilities = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_request"
        indexes = [
            models.Index(fields=["substitute_user_id"]),
            models.Index(fields=["status"])
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"substitute_req#{self.pk} app#{self.application_id} to u{self.substitute_user_id} ({self.status})"