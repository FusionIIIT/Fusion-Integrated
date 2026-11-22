from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from core.db.mixins import TimeStampedModel


class CitationType(models.TextChoices):
    PATENT = "patent", "Patent Document"
    JOURNAL = "journal", "Academic Journal Article"
    CONFERENCE = "conference", "Conference Proceeding"
    NPL = "npl", "Non-Patent Literature / Book"
    WEBSITE = "website", "Web Article / Technical Report"


class CoInventor(TimeStampedModel):
    """Co-inventor associated with a patent application with percentage contribution."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="inventors",
    )
    user_id = models.IntegerField(db_index=True)
    inventor_name = models.CharField(max_length=256)
    affiliation = models.CharField(max_length=256, blank=True, default="")
    contribution_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    agreement_signed = models.BooleanField(default=False)
    agreement_signed_at = models.DateTimeField(null=True, blank=True)
    signature_hash = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "pms_coinventor"
        constraints = [
            UniqueConstraint(fields=["application", "user_id"], name="pms_unique_app_inventor"),
            CheckConstraint(
                check=Q(contribution_percentage__gte=0) & Q(contribution_percentage__lte=100),
                name="pms_inventor_contrib_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.inventor_name} ({self.contribution_percentage}%)"


class PriorArtReference(TimeStampedModel):
    """Prior art citation attached to support novelty and patentability."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="prior_art_references",
    )
    title = models.CharField(max_length=512)
    citation_type = models.CharField(
        max_length=32,
        choices=CitationType.choices,
        default=CitationType.PATENT,
    )
    publication_number_or_doi = models.CharField(max_length=128, blank=True, default="")
    relevance_summary = models.TextField()
    attached_file_drive_link = models.URLField(max_length=1024, blank=True, default="")

    class Meta:
        db_table = "pms_prior_art_reference"

    def __str__(self) -> str:
        return f"{self.citation_type}: {self.title[:50]}"
