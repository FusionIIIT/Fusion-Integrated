from core.api.exceptions import PermissionDeniedError


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")
    if not any(actor.has_permission(code) for code in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.",
            code="permission_denied",
        )
