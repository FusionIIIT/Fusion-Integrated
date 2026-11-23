from django.apps import AppConfig


class LmsConfig(AppConfig):
    name = "modules.lms"
    label = "lms"

    def ready(self):
        from django.core.checks import register

        from core.files.writers import check_private_upload_root

        register(check_private_upload_root)
