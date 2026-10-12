"""Which buttons this actor may see on this file (display only).

Each action's endpoint re-checks its own permission and identity — this
module authorises nothing, it just keeps the UI from offering a click that
would 403. Same doctrine as the scoping selectors.
"""
from __future__ import annotations

from modules.leave.domain import states as st
from modules.leave.domain.categories import (
    EXTENDABLE_CATEGORIES,
    RESUMABLE_CATEGORIES,
)
from modules.leave.models import LeaveRequest, LeaveResumption


def allowed_actions(request: LeaveRequest, actor) -> list[str]:
    uid = getattr(actor, "user_id", None)
    if uid is None:
        return ["history", "print"]

    is_applicant = request.user_id == uid
    actions: list[str] = []

    if is_applicant and request.status in st.PENDING:
        actions.append("withdraw")
    # The file, not the viewer: a declined substitute parks it with the
    # applicant, and everyone looking at it sees what it now waits for.
    if request.status == st.APPLICANT_ACTION:
        actions.append("nominate_substitute")
    if (is_applicant and request.status == st.APPROVED
            and request.kind == LeaveRequest.NEW):
        actions.append("cancel")
        if request.category in EXTENDABLE_CATEGORIES:
            actions.append("extend")
        if (request.category in RESUMABLE_CATEGORIES
                and not request.resumptions
                       .filter(status=LeaveResumption.PENDING).exists()):
            actions.append("resumption")

    if (request.substitute_user_id == uid
            and request.status == st.AWAITING_SUBSTITUTE):
        actions.append("respond_substitute")
    if (request.unit_head_user_id == uid
            and request.status == st.AWAITING_UH_REVIEW):
        actions.append("review")
    if (request.establishment_user_id == uid
            and request.status == st.AWAITING_ESTABLISHMENT):
        actions.append("route")
    if request.status == st.AWAITING_DIRECTOR and is_applicant:
        actions.append("sanction")
    elif (request.status == st.AWAITING_FINAL
          and request.authority_user_id == uid):
        actions.append("sanction")

    pending_resumption = (request.resumptions
                          .filter(status=LeaveResumption.PENDING).first())
    if (pending_resumption is not None
            and uid in (request.authority_user_id, request.unit_head_user_id)):
        actions.append("review_resumption")

    actions += ["history", "print"]
    return actions
