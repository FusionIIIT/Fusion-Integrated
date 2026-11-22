"""Per-identity rate limiting for every HR-EIS mutation, independent of URL."""

from core.api.throttling import PrincipalScopedThrottle


class HREISWriteThrottleMixin:
    throttle_scope = "hreis_write"

    def get_throttles(self):
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return []
        return [PrincipalScopedThrottle()]
