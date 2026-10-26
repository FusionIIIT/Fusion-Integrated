
"""Authorization helpers for Employee Leave Management."""

from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    """Require an authenticated actor with at least one ELM permission."""
    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)

    if check is None or not any(check(code) for code in codes):
        raise PermissionDeniedError(
            f"This action requires one of: {', '.join(codes)}.",
            code="permission_denied",
        )
