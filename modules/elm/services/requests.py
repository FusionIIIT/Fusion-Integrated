
"""Transactional leave-request workflow service."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LeaveRequestTransition

P_APPLY = "elm.leave.apply"
P_WITHDRAW = "elm.leave.withdraw"
P_APPROVE = "elm.leave.approve"


def _require_permission(actor, permission: str) -> None:
    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)
    if check is None or not check(permission):
        raise PermissionDeniedError(
            f"This action needs {permission}.",
            code="permission_denied",
        )


def _actor_user_id(actor):
    return getattr(actor, "user_id", None)


def _actor_label(actor) -> str:
    return str(getattr(actor, "kind", "user"))[:80]


def _resolve_or_raise(source: str, action: str):
    try:
        return sm.resolve(source, action)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            str(exc),
            code="invalid_transition",
        ) from exc
@transaction.atomic
def transition(
    *,
    request_id: int,
    action: str,
    actor,
    reason: str = "",
    scope=None,
) -> LeaveRequest:
    """Perform one permitted workflow action and audit it atomically."""
    queryset = scope if scope is not None else LeaveRequest.objects.all()
    leave_request = (
        queryset.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if leave_request is None:
        raise NotFoundError("No such leave request.")

    # Keep the rest of the existing function here,
    # starting with: is_owner = ...
    is_owner = leave_request.user_id == _actor_user_id(actor)

    if action in {"submit", "withdraw"}:
        if not is_owner:
            raise PermissionDeniedError(
                "You may only perform this action on your own request.",
                code="request_scope_denied",
            )
        permission = P_APPLY if action == "submit" else P_WITHDRAW
        _require_permission(actor, permission)

    elif action in {"begin_approval", "approve", "reject"}:
        _require_permission(actor, P_APPROVE)
        if is_owner:
            raise PermissionDeniedError(
                "You cannot approve or reject your own leave request.",
                code="self_approval_denied",
            )

    elif action == "cancel":
        if not is_owner:
            raise PermissionDeniedError(
                "You may only cancel your own request.",
                code="request_scope_denied",
            )
        _require_permission(actor, P_WITHDRAW)

    else:
        raise ConflictError(
            f"Unknown leave-request action: {action}.",
            code="unknown_action",
        )

    transition_rule = _resolve_or_raise(leave_request.status, action)

    if action in {"reject", "cancel"} and not (reason or "").strip():
        raise ConflictError(
            "A reason is required for this action.",
            code="reason_required",
        )

    previous_status = leave_request.status
    leave_request.status = transition_rule.target
    update_fields = ["status", "updated_at"]

    if action == "submit":
        leave_request.submitted_at = timezone.now()
        update_fields.append("submitted_at")

    leave_request.save(update_fields=update_fields)

    LeaveRequestTransition.objects.create(
        leave_request=leave_request,
        from_status=previous_status,
        to_status=leave_request.status,
        actor_user_id=_actor_user_id(actor),
        actor_label=_actor_label(actor),
        reason=(reason or "").strip()[:500],
    )

    return leave_request
