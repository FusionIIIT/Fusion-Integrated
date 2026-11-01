"""Attorney panels, assignments, patentability opinions and legal advice."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class AttorneyPanel(TimeStampedModel):
    """Approved panel of patent attorneys (BR-PMS-041)."""

    user_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=200)
    firm_name = models.CharField(max_length=200)
    email = models.EmailField()
    specialization = models.CharField(max_length=200)  # e.g., Software, Biotech, Electronics
    is_active = models.BooleanField(default=True)
    max_workload = models.IntegerField(default=10)
    current_workload = models.IntegerField(default=0)

    class Meta:
        db_table = "pms_attorney_panel"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.firm_name}) - {self.specialization}"


class AttorneyAssignment(TimeStampedModel):
    """Assignment offered to an attorney, awaiting accept/decline (BW-PMS-06, 07)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="attorney_assignments"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField()
    status = models.CharField(
        max_length=50, default="offered", db_index=True
    )  # offered, accepted, declined
    responded_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "pms_attorney_assignment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["attorney_user_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"App {self.application_id} -> Attorney {self.attorney_user_id} ({self.status})"


class PatentabilityAssessment(TimeStampedModel):
    """Attorney legal analysis, patentability opinion and recommendation (BR-PMS-046)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="patentability_assessments"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    recommendation = models.CharField(
        max_length=50, db_index=True
    )  # file_patent, do_not_file, needs_amendment
    novelty_analysis = models.TextField()
    inventive_step_analysis = models.TextField()
    utility_analysis = models.TextField()
    prior_art_summary = models.TextField()
    opinion_text = models.TextField()
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_patentability_assessment"
        ordering = ["-assessed_at"]

    def __str__(self) -> str:
        return f"{self.recommendation} for App {self.application_id}"


class PatentLegalAdvice(TimeStampedModel):
    """Record of legal advice by attorney (CFR-PMS-004, UC-PMS-033)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="legal_advices"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=200)
    advice_text = models.TextField()

    class Meta:
        db_table = "pms_legal_advice"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Advice on App {self.application_id}: {self.topic}"
