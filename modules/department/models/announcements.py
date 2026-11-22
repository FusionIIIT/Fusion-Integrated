from django.core.exceptions import ValidationError
from django.db import models

from core.db.mixins import TimeStampedModel


class Announcement(TimeStampedModel):
    """A department announcement with an explicitly targeted audience."""

    title = models.CharField(max_length=200)
    body = models.TextField()

    # Audience targeting. The permitted values and matching rules will be
    # enforced by the service layer using the authoritative user context.
    target_roles = models.JSONField(default=list)
    target_programs = models.JSONField(default=list)
    target_academic_years = models.JSONField(default=list)

    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    published_by_role = models.CharField(max_length=60, blank=True)

    is_hidden = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "department_announcement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["published_at", "is_hidden"],
                name="dept_ann_pub_hidden_idx",
            ),
        ]

    def clean(self):
        super().clean()

        for field_name in (
            "target_roles",
            "target_programs",
            "target_academic_years",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, list):
                raise ValidationError({
                    field_name: "This field must contain a list."
                })

            if any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValidationError({
                    field_name: "Each target must be a non-empty string."
                })

        if self.published_at is not None:
            if not self.title.strip():
                raise ValidationError({
                    "title": "A published announcement must have a title."
                })

            if not self.body.strip():
                raise ValidationError({
                    "body": "A published announcement must have content."
                })

            if not self.target_roles:
                raise ValidationError({
                    "target_roles": (
                        "A published announcement must specify target roles."
                    )
                })

            if not self.target_programs:
                raise ValidationError({
                    "target_programs": (
                        "A published announcement must specify target programs."
                    )
                })

            if not self.target_academic_years:
                raise ValidationError({
                    "target_academic_years": (
                        "A published announcement must specify target academic years."
                    )
                })

    @property
    def is_active(self):
        """Whether the announcement is published and not hidden or deleted."""
        return (
            self.published_at is not None
            and not self.is_hidden
            and self.deleted_at is None
        )
