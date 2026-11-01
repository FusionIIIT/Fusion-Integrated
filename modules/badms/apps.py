"""App configuration for BADMS."""

from django.apps import AppConfig


class BadmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.badms"
    verbose_name = "Backup & Archival Management System"
