"""Shared model helpers for rows that are written once and never changed."""
from __future__ import annotations

from django.db import models


class AppendOnlyError(Exception):
    """Raised when code tries to change or delete a history row."""


class AppendOnly(models.Model):
    """History rows: a correction is a new row, never an edit."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError(f"{type(self).__name__} rows are never changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError(f"{type(self).__name__} rows are never deleted.")


def choices(values) -> list[tuple[str, str]]:
    return [(v, v.replace("_", " ").capitalize()) for v in values]
