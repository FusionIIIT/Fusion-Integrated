from django.apps import AppConfig


class ELMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.elm"
    label = "elm"
    verbose_name = "Employee Leave Management"
