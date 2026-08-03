from django.apps import AppConfig
from django.core.checks import register


class FusionAuthConfig(AppConfig):
    name = "fusion_auth"

    def ready(self):
        # IAM_AUTH_COOKIE_NAME is this package's setting, so it owns the check.
        from fusion_auth.checks import check_auth_cookie_name

        register(check_auth_cookie_name)
