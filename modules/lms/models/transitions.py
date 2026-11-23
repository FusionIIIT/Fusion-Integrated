from django.db import models
from django.db.models import Q

from .base import AppendOnly


class ContentTransitionLog(AppendOnly):
    material = models.ForeignKey("lms.Material", null=True, on_delete=models.PROTECT)
    assignment = models.ForeignKey("lms.Assignment", null=True, on_delete=models.PROTECT)
    actor_user_id = models.IntegerField(null=True)
    actor_role = models.CharField(max_length=8)
    event = models.CharField(max_length=8)
    old_state = models.CharField(max_length=10)
    new_state = models.CharField(max_length=10)
    old_release_at = models.DateTimeField(null=True)
    new_release_at = models.DateTimeField(null=True)
    changed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(material__isnull=False, assignment__isnull=True)
                    | Q(material__isnull=True, assignment__isnull=False)
                ),
                name="lms_transition_one_subject",
            )
        ]

    def __str__(self):
        return f"Content transition {self.pk}"
