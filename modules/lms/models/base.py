from django.db import models
from django.db.models import Q


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Historical records cannot be updated")

    def delete(self):
        raise ValueError("Historical records cannot be deleted")


class AppendOnly(models.Model):
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Historical records cannot be updated")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Historical records cannot be deleted")


def payload_constraint(text_kind):
    return (
        (Q(kind=text_kind, url="", stored_file__isnull=True) & ~Q(text=""))
        | (Q(kind="LINK", text="", stored_file__isnull=True) & ~Q(url=""))
        | Q(kind="FILE", text="", url="", stored_file__isnull=False)
    )
