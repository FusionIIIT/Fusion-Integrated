from django.apps import AppConfig


class IamConfig(AppConfig):
    name = "iam"
    verbose_name = "Identity & Access"

    def ready(self) -> None:
        # ERP tables are unmanaged, so tests need them built; a no-op otherwise.
        from iam.testing import install_for_tests

        install_for_tests()
