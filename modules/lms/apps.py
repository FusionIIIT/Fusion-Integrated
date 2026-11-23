from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.lms"
    verbose_name = "Course Management"

    def ready(self):
        from django.core.checks import register

        from core.files.checks import check_upload_root

        register(check_upload_root)
