from django.apps import AppConfig


class FtsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.fts"
    verbose_name = "File Tracking System"