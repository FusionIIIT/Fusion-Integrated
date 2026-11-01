"""Licensing requests, appeals, pre-filing withdrawals, and prior art models."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.pms.models.applications import PatentApplication


class LicensingRequest(TimeStampedModel, UserScopedModel):
    """Licensing or technology transfer proposal (UC-PMS-020, 021, BR-PMS-088, 091)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="licensing_requests"
    )
    licensee_name = models.CharField(max_length=255)
    licensee_contact = models.CharField(max_length=255)
    proposed_terms = models.TextField()
    financial_terms = models.TextField(blank=True)
    status = models.CharField(
        max_length=50, default="submitted", db_index=True
    )  # submitted, under_review, approved, rejected
    review_notes = models.TextField(blank=True)
    reviewed_by_director_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "pms_licensing_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Licensing with {self.licensee_name} for App {self.application_id}"


class PatentAppeal(TimeStampedModel, UserScopedModel):
    """Applicant appeal against application rejection (UC-PMS-022, BR-PMS-092, 093, 094)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="appeals"
    )
    grounds = models.TextField()
    justification = models.TextField()
    status = models.CharField(max_length=50, default="appeal_submitted", db_index=True)
    filed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_patent_appeal"
        ordering = ["-filed_at"]

    def __str__(self) -> str:
        return f"Appeal on App {self.application_id} ({self.status})"


class AppealDecision(TimeStampedModel):
    """Director decision on rejection appeal (UC-PMS-023, BR-PMS-095, BW-PMS-03, 04, 05)."""

    appeal = models.OneToOneField(PatentAppeal, on_delete=models.CASCADE, related_name="decision")
    director_user_id = models.IntegerField(db_index=True)
    outcome = models.CharField(
        max_length=50, db_index=True
    )  # uphold_rejection, remand_for_amendment, modify_decision
    justification = models.TextField()
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_appeal_decision"
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return f"Outcome {self.outcome} for Appeal {self.appeal_id}"


class ApplicationWithdrawal(TimeStampedModel, UserScopedModel):
    """Record of pre-filing application withdrawal (UC-PMS-006, BW-PMS-16, BR-PMS-067..070)."""

    application = models.OneToOneField(
        PatentApplication, on_delete=models.CASCADE, related_name="withdrawal_record"
    )
    reason = models.TextField()
    co_inventors_notified = models.BooleanField(default=True)
    withdrawn_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_application_withdrawal"
        ordering = ["-withdrawn_at"]

    def __str__(self) -> str:
        return f"Withdrawal of App {self.application_id}"


class PriorArtSearchRecord(TimeStampedModel, UserScopedModel):
    """Log of prior art search session (UC-PMS-004, BR-PMS-141)."""

    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="prior_art_searches",
        null=True,
        blank=True,
    )
    query_string = models.CharField(max_length=500)
    databases_searched = models.CharField(
        max_length=255, default="Indian Patent Database, Google Patents, Espacenet"
    )
    results_count = models.IntegerField(default=0)
    session_notes = models.TextField(blank=True)

    class Meta:
        db_table = "pms_prior_art_search"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Search '{self.query_string}' by User {self.user_id}"


class PriorArtAttachment(TimeStampedModel):
    """Specific prior art reference attached to an application (UC-PMS-004)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="prior_art_attachments"
    )
    title = models.CharField(max_length=300)
    authors_or_inventors = models.CharField(max_length=300, blank=True)
    publication_or_patent_no = models.CharField(max_length=100)
    publication_date = models.DateField(null=True, blank=True)
    url_or_doi = models.URLField(max_length=500, blank=True)
    relevance_summary = models.TextField()
    attached_by_user_id = models.IntegerField()

    class Meta:
        db_table = "pms_prior_art_attachment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.publication_or_patent_no}: {self.title}"
