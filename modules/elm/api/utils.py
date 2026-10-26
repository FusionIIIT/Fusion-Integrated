"""Utility helpers for ELM API views and serializers."""
from __future__ import annotations


def get_caller_id(request) -> int | None:
    """Extract canonical user ID from the request principal or authenticated user.

    Returns None if the request is unauthenticated or has no identifiable actor.
    Never falls back to a default user ID to prevent unauthorized attribution.
    """
    if not request:
        return None

    principal = getattr(request, "principal", None)
    if principal is not None:
        uid = getattr(principal, "user_id", None)
        if uid is not None and isinstance(uid, (int, str)):
            try:
                return int(uid)
            except (ValueError, TypeError):
                pass

    user = getattr(request, "user", None)
    if user is not None:
        # If request.user is a Principal instance
        uid = getattr(user, "user_id", None)
        if uid is not None and isinstance(uid, (int, str)):
            try:
                return int(uid)
            except (ValueError, TypeError):
                pass

        # If request.user is a Django User instance (e.g. in test client)
        if getattr(user, "is_authenticated", False):
            pk = getattr(user, "pk", None) or getattr(user, "id", None)
            if pk is not None and isinstance(pk, (int, str)):
                try:
                    return int(pk)
                except (ValueError, TypeError):
                    pass

    return None
