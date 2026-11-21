"""Per-identity rate limiting for every HR-EIS mutation, independent of URL.

Read-only requests are not throttled by this mixin. Authorization precedes
throttle evaluation in DRF, and no action bypasses the IAM permission checks.
"""
from rest_framework.throttling import SimpleRateThrottle


class HREISWriteThrottle(SimpleRateThrottle):
    scope = "hreis_write"
    rate = "60/min"

    def get_cache_key(self, request, view):
        principal = getattr(request, "user", None)
        user_id = getattr(principal, "user_id", None)
        identity = (
            f"iam:{user_id}"
            if isinstance(user_id, int) and user_id > 0
            else f"ip:{self.get_ident(request)}"
        )
        return self.cache_format % {"scope": self.scope, "ident": identity}


class HREISWriteThrottleMixin:
    throttle_scope = "hreis_write"

    def get_throttles(self):
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            return []
        return [HREISWriteThrottle()]
