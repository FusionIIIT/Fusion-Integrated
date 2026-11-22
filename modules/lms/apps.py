from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.lms"
    label = "lms"
    verbose_name = "LMS (Course Management)"
