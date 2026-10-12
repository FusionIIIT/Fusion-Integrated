"""Translating domain exceptions into the shared error envelope.

The domain layer is pure Python and must stay free of DRF (importlinter),
so it raises its own `ValidationError` / state-machine exceptions. This is
the seam: every public service call that can trip a rule is wrapped in
`validated`, and every path into the state machine goes through
`resolve_or_raise` — the same shape placement uses, for the same reason.
"""
from __future__ import annotations

from functools import wraps

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.domain import states as st
from modules.leave.domain.validation import ValidationError as RuleRefused


def validated(fn):
    """Domain rule refusals become 400s with the rule's machine-readable
    code, so the client can tell 'insufficient balance' from 'overlap'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RuleRefused as exc:
            raise BadRequestError(exc.message, code=exc.code) from exc
    return wrapper


def resolve_or_raise(frm: str, to: str, actor_kind: str) -> st.Transition:
    """`states.resolve` with its errors translated. Every path into the
    state machine must use this, or an illegal move surfaces as a 500."""
    try:
        return st.resolve(frm, to, actor_kind)
    except st.InvalidTransition as exc:
        raise ConflictError(
            f"A leave request cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
            details=[{"from": exc.frm, "to": exc.to,
                      "allowed": st.allowed_targets(exc.frm, actor_kind)}],
        ) from exc
    except st.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": exc.frm, "to": exc.to,
                      "actor": exc.actor_kind}],
        ) from exc
