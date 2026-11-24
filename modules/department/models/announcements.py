from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.department.domain.rules import AUDIENCE_ROLES


class Announcement(TimeStampedModel):
    ACTIVE, HIDDEN, DELETED = "active", "hidden", "deleted"
    STATUS = [(ACTIVE, "Active"), (HIDDEN, "Hidden"), (DELETED, "Deleted")]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="announcements"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    audience_role = models.CharField(max_length=12, choices=[(r, r) for r in AUDIENCE_ROLES])
    programme = models.CharField(max_length=40, blank=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=STATUS, default=ACTIVE)
    author_id = models.IntegerField()
    published_at = models.DateTimeField()
    edited_by = models.IntegerField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_announcement"
        constraints = [
            models.CheckConstraint(
                condition=~Q(title="") & ~Q(body=""), name="dept_ann_has_content"
            ),
            models.CheckConstraint(
                condition=Q(audience_role__in=AUDIENCE_ROLES), name="dept_ann_audience_known"
            ),
        ]
        indexes = [models.Index(fields=["department", "status", "-id"], name="dept_ann_feed_idx")]
