from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import Leave


# Permission codes. Held by TPO / placement chairman via the IAM.
P_VIEW_ALL = "elm.leave_request.view"
P_MANAGE_LEAVE_REQUESTS = "elm.leave_request.manage"

# Any of these makes someone staff; view_self is the student grant and absent.
STAFF_SCOPE_PERMISSIONS = (
    P_VIEW_ALL,
    "elm.leave_request.review",
)

ALUMNI_ROLE = "alumni"


def _is_recruiter(actor) -> bool:
    return getattr(actor, "kind", None) == "recruiter"


def _own_id(actor) -> int | None:
    """None means no identity to scope by, which resolves to an empty
    queryset. Deny is the only safe reading of "who is asking?" being
    unanswerable."""
    return getattr(actor, "user_id", None)


def _is_alumni(actor) -> bool:
    """Alumni are an IAM role, not a separate pool."""
    return ALUMNI_ROLE in {r.lower() for r in getattr(actor, "roles", ())}


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


is_staff = _is_recruiter


# -- Leaves ------------------------------------------------------------------
def leaves_for(actor) -> QuerySet[Leave]:
    base = Leave.objects.all()
    if _is_recruiter(actor):
        # Their own company's postings in every state, including drafts.
        return base.filter(user_id=actor.user_id)

    if is_staff(actor):
        return base

    if _is_alumni(actor):
        return base.none()                        # PC-BR-020
    if _has(actor, P_VIEW_ALL):
        return base
    own = _own_id(actor)
    return base.filter(user_id=own) if own is not None else base.none()
