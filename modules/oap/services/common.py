"""Write authority, stated once. Every write path calls these helpers."""

from __future__ import annotations

from contextlib import contextmanager

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.oap.domain.errors import IllegalTransition, RuleViolation
from modules.oap.models import OapEvent


def need(principal, code: str) -> None:
    if principal is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")
    if not principal.has_permission(code):
        raise PermissionDeniedError(f"This action needs {code}.", code="permission_denied")


def need_role(principal, role: str) -> None:
    if principal.active_role != role:
        raise PermissionDeniedError(
            f"Switch your active role to {role} to do this.", code="wrong_role"
        )


@contextmanager
def domain_guard():
    try:
        yield
    except (IllegalTransition, RuleViolation) as exc:
        raise ConflictError(str(exc), code="not_allowed_in_current_state") from exc


def record(
    aggregate: str, aggregate_id: int, from_state: str, to_state: str, actor_user_id: int | None
) -> None:
    OapEvent.objects.create(
        aggregate=aggregate,
        aggregate_id=aggregate_id,
        from_state=from_state,
        to_state=to_state,
        actor_user_id=actor_user_id,
    )


def locked(qs, pk: int, message: str = "Not found."):
    """The row, locked for this transaction, or 404 when it is out of scope."""
    obj = qs.select_for_update().filter(pk=pk).first()
    if obj is None:
        raise NotFoundError(message, code="not_found")
    return obj


def bad_request(message: str, code: str) -> BadRequestError:
    return BadRequestError(message, code=code)
