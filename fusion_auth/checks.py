"""Startup checks for the session cookie.

The collision below is invisible in development — the console and the platform
run on different ports, and browsers ignore the port when matching cookies.
"""
from django.conf import settings
from django.core.checks import Warning  # noqa: A004

COOKIE_COLLIDES = "fusion.auth.W001"

#: What Fusion_System_Administrator sets, at path "/", by default.
CONSOLE_COOKIE_NAME = "auth_token"


def check_auth_cookie_name(app_configs, **kwargs):
    """Two services setting one cookie name on one hostname overwrite each
    other, so each login silently signs the other out."""
    if settings.IAM_AUTH_COOKIE_NAME != CONSOLE_COOKIE_NAME:
        return []
    return [Warning(
        f"IAM_AUTH_COOKIE_NAME is {CONSOLE_COOKIE_NAME!r}, the same name the "
        f"sysadmin console sets at path '/'.",
        hint="Served from one hostname, whichever is logged into last "
             "overwrites the other's cookie. Set IAM_AUTH_COOKIE_NAME to "
             "something else — fusion_session — and scope the console's to "
             "its own path with AUTH_COOKIE_PATH=/sysadmin/.",
        id=COOKIE_COLLIDES,
    )]
