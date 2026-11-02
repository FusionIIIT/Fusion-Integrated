from django.apps import AppConfig


class GymkhanaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.gymkhana"
    label = "gymkhana"
    verbose_name = "Gymkhana"

    def ready(self):
        from django.core.checks import register

        from modules.gymkhana.checks import check_upload_root

        register(check_upload_root)
