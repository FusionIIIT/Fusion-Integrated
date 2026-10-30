from core.api.exceptions import PermissionDeniedError


def require(principal, *codes: str) -> None:
    """Enforce fine-grained permission codes."""
    if principal is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")

    check = getattr(principal, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied",
        )
