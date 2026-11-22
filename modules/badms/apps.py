from django.apps import AppConfig


class BadmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.badms"
    label = "badms"
    verbose_name = "Backup and Database Archive Management System"
