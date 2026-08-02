"""DRF authentication against Fusion_System_Administrator.

Accepts either the httpOnly cookie the SPA carries, or an
`Authorization: Token ...` header for scripts and service calls. Both are
resolved by asking IAM who the holder is — this service never checks a
password and never reads a user table.
"""
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.api import csrf
from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.principal import Principal


class IamSessionAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        # Forwarded as a header, not by replaying our cookie: the IAM names
        # its cookie differently.
        token = self._token_from(request)
        # Only a cookie is ambient, so only a cookie needs the CSRF check.
        from_cookie = token is None
        token = token or request.COOKIES.get(settings.IAM_AUTH_COOKIE_NAME)
        if not token:
            return None                       # anonymous; permissions decide

        try:
            session = get_client().resolve_session(auth_token=token)
        except IamUnavailable as exc:
            # Fail closed, but say why — a 503 is honest, a 401 would send the
            # user to re-login for a problem that is not theirs.
            raise AuthenticationFailed(
                f"Identity service unavailable: {exc}"
            ) from exc

        if session is None:
            raise AuthenticationFailed("Invalid or expired credentials.")

        if from_cookie:
            csrf.require(request, token)

        principal = Principal.from_session(session)
        request.principal = principal
        return (principal, token)

    def _token_from(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith(self.keyword + " "):
            return header[len(self.keyword) + 1:].strip()
        return None

    def authenticate_header(self, request):
        return self.keyword
