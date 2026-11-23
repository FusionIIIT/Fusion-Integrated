from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel

from .base import payload_constraint


class MaterialSection(TimeStampedModel):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    kind = models.CharField(max_length=6, choices=[("MODULE", "Module"), ("WEEK", "Week")])
    label = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=("MODULE", "WEEK")), name="lms_section_kind_valid"
            )
        ]


class Material(TimeStampedModel):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    section = models.ForeignKey(
        "lms.MaterialSection", null=True, blank=True, on_delete=models.PROTECT
    )
    title = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=4)
    text = models.TextField(blank=True)
    url = models.URLField(max_length=2000, blank=True)
    stored_file = models.ForeignKey("lms.StoredFile", null=True, on_delete=models.PROTECT)
    order = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=10, default="DRAFT")
    release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    author_user_id = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=payload_constraint("NOTE"), name="lms_material_payload"
            ),
            models.CheckConstraint(
                condition=Q(state__in=("DRAFT", "SCHEDULED", "PUBLISHED")),
                name="lms_material_state_valid",
            ),
            models.CheckConstraint(
                condition=~Q(state="SCHEDULED") | Q(release_at__isnull=False),
                name="lms_material_scheduled_time",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "state", "order"), name="lms_material_scope"),
            models.Index(fields=("state", "release_at"), name="lms_material_due"),
        ]
