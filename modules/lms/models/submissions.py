from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

from .base import payload_constraint


class Submission(UserScopedModel, TimeStampedModel):
    assignment = models.ForeignKey("lms.Assignment", on_delete=models.PROTECT)
    kind = models.CharField(max_length=4)
    text = models.TextField(blank=True)
    url = models.URLField(max_length=2000, blank=True)
    stored_file = models.ForeignKey("lms.StoredFile", null=True, on_delete=models.PROTECT)
    submitted_at = models.DateTimeField()
    policy_version = models.CharField(max_length=32, default="A9-LMS-BP-0.2")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("assignment", "user_id"), name="lms_submission_assignment_user_uniq"
            ),
            models.CheckConstraint(
                condition=payload_constraint("TEXT"), name="lms_submission_payload"
            ),
        ]
