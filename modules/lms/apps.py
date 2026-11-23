from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.lms"
    verbose_name = "Course Management"

    def ready(self):
        from django.core.checks import register

        from modules.lms.checks import check_lms_upload_root

        register(check_lms_upload_root)
