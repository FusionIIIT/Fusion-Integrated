"""File Tracking System (FTS) application configuration."""
from django.apps import AppConfig


class FtsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.fts"
    label = "fts"
    verbose_name = "File Tracking System"
