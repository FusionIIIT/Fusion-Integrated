from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class OAPApplication(TimeStampedModel, UserScopedModel):
    """An application for OAP services."""

    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user_id = models.IntegerField(unique=True)
    application_date = models.DateField()
    application_details = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    submitted_by = models.ForeignKey(
        UserScopedModel, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="oap_applications_submitted"
    )
    reviewed_by = models.ForeignKey(
        UserScopedModel, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="oap_applications_reviewed"
    )

    class Meta:
        db_table = "oap_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="application_user_status_idx"),
        ]

    def __str__(self) -> str:
        return f"OAP Application u{self.user_id} {self.status}"


class OAPServiceRequest(TimeStampedModel, UserScopedModel):
    """A request for OAP services."""

    STATUS = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    application = models.ForeignKey(OAPApplication, on_delete=models.CASCADE, related_name="service_requests")
    service_type = models.CharField(max_length=100)
    service_details = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    requested_by = models.ForeignKey(
        UserScopedModel, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="oap_service_requests_requested"
    )
    assigned_to = models.ForeignKey(
        UserScopedModel, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="oap_service_requests_assigned"
    )

    class Meta:
        db_table = "oap_service_request"
        indexes = [
            models.Index(fields=["application", "status"], name="request_application_status_idx"),
        ]

    def __str__(self) -> str:
        return f"OAP Service Request {self.id} {self.status}"


class OAPServiceOutcome(TimeStampedModel, UserScopedModel):
    """The outcome of an OAP service request."""

    service_request = models.OneToOneField(OAPServiceRequest, on_delete=models.CASCADE, related_name="outcome")
    outcome_details = models.JSONField()
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        UserScopedModel, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="oap_service_outcomes_completed"
    )

    class Meta:
        db_table = "oap_service_outcome"
        indexes = [
            models.Index(fields=["service_request"], name="outcome_service_request_idx"),
        ]

    def __str__(self) -> str:
        return f"OAP Service Outcome {self.id}"
