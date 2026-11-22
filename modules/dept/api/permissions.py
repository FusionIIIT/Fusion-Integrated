"""Permission classes and shortcuts for Department API views."""

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal

MODULE_GRANT = HasModuleGrant("dept")

__all__ = [
    "MODULE_GRANT",
    "HasPermission",
    "IsAuthenticatedPrincipal",
]
