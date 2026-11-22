from django.db import models


class AppendOnlyModel(models.Model):
    """A row that is written once and never changed or deleted (BR-301, BR-503)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(f"{type(self).__name__} rows are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(f"{type(self).__name__} rows are never deleted.")
