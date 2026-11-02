"""DRF auth for ERP users (students / faculty / staff) and for peer services.

Three pools, none of which may be mistaken for another:

    api.authentication.CookieTokenAuthentication   operators, in system_db
    IamTokenAuthentication                         ERP people, `Token` scheme
    IamServiceAuthentication                       services, `Service` scheme

Separate schemes, so all three can sit on one view unambiguously and a service
credential can never resolve to a person — which is what keeps /me
un-reachable by a machine.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from iam.models import IamServiceToken
from iam.services import resolve_token

COOKIE_NAME = "iam_token"


class IamPrincipal:
    """Not a Django user — there is no Django user for these people."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, token):
        self.token = token
        self.erp_user_id = token.erp_user_id
        self.username = token.username

    def __str__(self) -> str:
        return f"{self.username}({self.erp_user_id})"


class IamTokenAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        raw = None
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Service "):
            # Explicitly a machine's credential. Decline rather than fall
            # through to the cookie, so the answer does not depend on which
            # order the two classes happen to be listed in.
            return None
        if header.startswith(self.keyword + " "):
            raw = header[len(self.keyword) + 1:].strip()
        raw = raw or request.COOKIES.get(COOKIE_NAME)
        if not raw:
            return None

        token = resolve_token(raw)
        if token is None:
            raise AuthenticationFailed("Invalid or expired session.")
        return (IamPrincipal(token), raw)

    def authenticate_header(self, request):
        return self.keyword


class ServicePrincipal:
    """A peer service. Holds no identity, no roles and no permissions —
    everything it may do is decided by which views accept this class."""

    is_authenticated = True
    is_anonymous = False
    erp_user_id = None
    username = None

    def __init__(self, token: IamServiceToken):
        self.token = token
        self.service_name = token.name

    def __str__(self) -> str:
        return f"service:{self.service_name}"


class IamServiceAuthentication(BaseAuthentication):
    """`Authorization: Service fsvc_...`

    A distinct scheme rather than reusing `Token` on purpose. Sharing one
    scheme would mean guessing which pool a credential belongs to, and a wrong
    guess in either direction is a security bug: a service token that resolves
    to a person, or a user session that inherits machine reach.
    """

    keyword = "Service"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(self.keyword + " "):
            return None                       # not ours; let the next class try
        raw = header[len(self.keyword) + 1:].strip()

        token = IamServiceToken.resolve(raw)
        if token is None:
            raise AuthenticationFailed("Invalid or revoked service credential.")
        token.touch()
        return (ServicePrincipal(token), raw)

    def authenticate_header(self, request):
        return self.keyword
