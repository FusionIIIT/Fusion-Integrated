from django.apps import AppConfig


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.leave"
    verbose_name = "Employee Leave Management"

    def ready(self):
        try:
            import modules.leave.signals  # noqa: F401
        except ImportError:
            pass


