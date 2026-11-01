"""Permission gates for PHC API endpoints."""
from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal

__all__ = [
    "HasPermission",
    "IsAuthenticatedPrincipal",
]
