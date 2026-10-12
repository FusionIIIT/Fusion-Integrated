"""Role scope, decided in one place (ELM-UC-018)."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import LeaveApplication


def _sees_everything(actor) -> bool:
    return bool(getattr(actor, "has_permission", None) and actor.has_permission("elm.leave_application.view"))


def leave_applications_for(actor) -> QuerySet[LeaveApplication]:
    """Ownership/scope lives here, once per module: a foreign id is absent (404),
    never forbidden (403)."""
    base = LeaveApplication.objects.all()
    if _sees_everything(actor):
        return base
    own = getattr(actor, "user_id", None)
    return base.filter(applicant_id=own) if own is not None else base.none()
