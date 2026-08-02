"""Throttling that understands this platform's principals.

DRF's `ScopedRateThrottle` identifies a caller by `request.user.pk`; there is
no Django user here, so it turns every throttled endpoint into a 500. Identity
is derived explicitly instead, and the three pools get separate buckets so a
recruiter cannot exhaust a student's allowance.
"""
from rest_framework.throttling import ScopedRateThrottle


class PrincipalScopedThrottle(ScopedRateThrottle):
    """`throttle_scope` on a view, keyed by whoever is actually calling."""

    def get_cache_key(self, request, view):
        if not self.rate:
            return None

        principal = getattr(request, "principal", None)
        if principal is not None:
            if getattr(principal, "kind", None) == "recruiter":
                # Namespaced so a recruiter id can never collide with a user id.
                ident = f"recruiter:{principal.account_id}"
            else:
                ident = f"user:{principal.user_id}"
        else:
            ident = f"ip:{self.get_ident(request)}"

        return self.cache_format % {"scope": self.scope, "ident": ident}
