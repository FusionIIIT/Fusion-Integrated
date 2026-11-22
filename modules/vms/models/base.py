"""Shared helpers for the vms models."""
from django.db import models


def choice_check(field: str, choices, name: str) -> models.CheckConstraint:
    """CheckConstraint restricting `field` to the values of a TextChoices."""
    return models.CheckConstraint(
        condition=models.Q(**{f"{field}__in": [c.value for c in choices]}),
        name=name,
    )


class AppendOnlyError(RuntimeError):
    pass


class AppendOnlyModel(models.Model):
    """Rows are inserted once and never changed or deleted via the ORM
    instance API (VMS audit trail, SRS 3.14). Services must not offer update
    or delete paths. Bulk `QuerySet.update/delete` is not intercepted; it is
    forbidden by convention and covered in review."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError(f"{type(self).__name__} is append-only")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError(f"{type(self).__name__} is append-only")
