from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class ThesisSupervisorAssignment(TimeStampedModel):
    student_user_id = models.IntegerField(db_index=True)
    supervisor_user_id = models.IntegerField()
    assigned_by_user_id = models.IntegerField()
    assigned_at = models.DateTimeField()
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_thesis_supervisor_assignment"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_user_id"],
                condition=Q(superseded_at__isnull=True),
                name="oap_one_current_thesis_supervisor",
            ),
        ]


class TAAssignment(TimeStampedModel):
    student_user_id = models.IntegerField(db_index=True)
    course_code = models.CharField(max_length=32, blank=True)
    supervisor_user_id = models.IntegerField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField()
    assigned_at = models.DateTimeField()

    class Meta:
        db_table = "oap_ta_assignment"
        ordering = ["-assigned_at"]
        constraints = [
            models.CheckConstraint(
                condition=(~Q(course_code="") | Q(supervisor_user_id__isnull=False)),
                name="oap_ta_has_course_or_faculty",
            ),
        ]
