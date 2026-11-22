from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class ReviewStage(models.TextChoices):
    PRELIMINARY_SCRUTINY = "preliminary_scrutiny", "Preliminary Technical Scrutiny"
    DIRECTOR_REVIEW = "director_review", "Director / Dean Evaluation"
    COMMITTEE_REVIEW = "committee_review", "Institutional IPR Committee Review"
    APPEAL_REVIEW = "appeal_review", "Appellate Review"


class ReviewVerdict(models.TextChoices):
    RECOMMEND_APPROVAL = "recommend_approval", "Recommend Approval for Filing"
    RECOMMEND_REVISION = "recommend_revision", "Recommend Revision / Clarification"
    RECOMMEND_REJECTION = "recommend_rejection", "Recommend Institutional Rejection"


class InternalReview(TimeStampedModel):
    """Institutional technical evaluation, novelty scoring, and recommendation."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer_user_id = models.IntegerField(db_index=True)
    review_stage = models.CharField(
        max_length=32,
        choices=ReviewStage.choices,
        default=ReviewStage.PRELIMINARY_SCRUTINY,
    )
    verdict = models.CharField(max_length=32, choices=ReviewVerdict.choices)
    comments = models.TextField()
    novelty_score = models.IntegerField(default=5)
    inventive_step_score = models.IntegerField(default=5)
    commercial_viability_score = models.IntegerField(default=5)

    class Meta:
        db_table = "pms_internal_review"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=Q(novelty_score__gte=1) & Q(novelty_score__lte=10),
                name="pms_novelty_score_range",
            ),
            CheckConstraint(
                check=Q(inventive_step_score__gte=1) & Q(inventive_step_score__lte=10),
                name="pms_inventive_score_range",
            ),
            CheckConstraint(
                check=Q(commercial_viability_score__gte=1) & Q(commercial_viability_score__lte=10),
                name="pms_commercial_score_range",
            ),
        ]

    def __str__(self) -> str:
        return f"Review by {self.reviewer_user_id}: {self.verdict}"
