from django.apps import AppConfig


class SystemAdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.systemadmin"
    verbose_name = "System Admin Control Plane"
