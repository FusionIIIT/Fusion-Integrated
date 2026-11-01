from django.apps import AppConfig


class IaaConfig(AppConfig):
    name = "modules.iaa"
    label = "iaa"
    verbose_name = "Institute Accounts and Audits"

    def ready(self):
        from django.core.checks import register

        from modules.iaa.checks import check_iaa_upload_root

        register(check_iaa_upload_root)
