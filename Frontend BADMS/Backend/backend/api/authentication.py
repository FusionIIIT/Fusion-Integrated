from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """Token authentication where tokens expire after ``settings.TOKEN_TTL_HOURS``.

    DRF's stock token never expires, so a leaked token is valid forever. Here an
    expired token is deleted and rejected, giving a leaked/stale token a bounded
    lifetime and forcing a fresh login. Each login issues a new token (see
    ``backend.urls.LoginView``), so active use keeps working within the window.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        ttl_hours = getattr(settings, "TOKEN_TTL_HOURS", 12)
        if timezone.now() - token.created > timedelta(hours=ttl_hours):
            token.delete()
            raise AuthenticationFailed("Token has expired. Please log in again.")
        return user, token


class CookieTokenAuthentication(ExpiringTokenAuthentication):
    """Read the token from the httpOnly auth cookie, falling back to the
    ``Authorization: Token <key>`` header for API clients / scripts / tests.
    """

    def authenticate(self, request):
        key = request.COOKIES.get(getattr(settings, "AUTH_COOKIE_NAME", "auth_token"))
        if key:
            return self.authenticate_credentials(key)
        return super().authenticate(request)
