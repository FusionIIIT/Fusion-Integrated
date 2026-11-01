from django.db import models

from core.db.mixins import TimeStampedModel


class Feedback(TimeStampedModel):
    """Represents a feedback submission regarding a department."""
    department = models.ForeignKey("department.Department", on_delete=models.PROTECT)
    submitter_user_id = models.IntegerField()
    body = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=[
            ('academic', 'Academic'),
            ('infrastructure', 'Infrastructure'),
            ('administrative', 'Administrative'),
            ('facilities', 'Facilities'),
            ('other', 'Other'),
        ],
        null=True,
        blank=True,
    )
    state = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New'),
            ('under_review', 'Under Review'),
            ('resolved', 'Resolved'),
            ('closed', 'Closed'),
        ],
        default='new',
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    disposed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    disposed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_feedback"
        indexes = [
            models.Index(fields=["department", "state"], name="dept_feedback_state_idx"),
        ]
