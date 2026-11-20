"""A write-only variant of the platform throttle, for views that also serve reads."""
from rest_framework.permissions import SAFE_METHODS

from core.api.throttling import PrincipalScopedThrottle


class WriteThrottle(PrincipalScopedThrottle):
    """Counts and limits only unsafe methods, so a list page is never throttled."""

    def allow_request(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().allow_request(request, view)
