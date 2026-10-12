"""The one choke point every status change goes through."""
from __future__ import annotations

from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LeaveTransition

SYSTEM = None


def move(req: LeaveRequest, *, event: str, actor_kind: str, to: str, actor,
         note: str = "") -> None:
    """Caller holds the row lock. Refuses an illegal edge or a missing permission."""
    frm = req.status if req.pk else sm.NEW
    try:
        t = sm.resolve(frm, event, actor_kind, to)
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(str(exc), code="actor_not_allowed") from exc
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"This request is {frm.replace('_', ' ')} and cannot be changed that way.",
            code="invalid_transition") from exc
    if actor is not SYSTEM and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")
    req.status = to
    req.save()
    LeaveTransition.objects.create(
        request=req, from_status=frm, to_status=to, event=event,
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=getattr(actor, "active_role", "") or "",
        note=note[:500])


def enter_stage(req: LeaveRequest, stage: int) -> str:
    """Point the request at a route step; returns the state that step implies."""
    req.stage = stage
    step = req.route[stage]
    req.current_role = step["role"]
    req.stage_entered_at = timezone.now()
    return sm.STATE_FOR_STEP[step["step"]]
