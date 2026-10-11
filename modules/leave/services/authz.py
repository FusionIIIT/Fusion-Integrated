from __future__ import annotations

from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied")
