"""Which permission each workflow step demands, stated once for the services to read."""
from __future__ import annotations

from modules.leave.domain import sla
from modules.leave.domain import state_machine as sm

STEP_PERMISSIONS = {
    sm.SUBSTITUTE: "leave.substitution.review",
    sm.UNIT_HEAD: "leave.request.review",
    sm.ESTABLISHMENT: "leave.request.assign",
    sm.AUTHORITY: "leave.request.approve",
    sm.DIRECTOR: "leave.request.approve",
    sla.RESUMPTION_REVIEW: "leave.resumption.review",
}

#: The events each step may take, so a decision cannot be misrouted to the wrong edge.
STEP_EVENTS = {
    sm.UNIT_HEAD: (sm.UNIT_HEAD_APPROVE, sm.UNIT_HEAD_REJECT, sm.UNIT_HEAD_RECOMMEND),
    sm.ESTABLISHMENT: (sm.ESTABLISHMENT_FORWARD,),
    sm.AUTHORITY: (sm.SANCTION_APPROVE, sm.SANCTION_REJECT),
    sm.DIRECTOR: (sm.SANCTION_APPROVE, sm.SANCTION_REJECT),
}

RECOMMENDED, NOT_RECOMMENDED = "recommended", "not_recommended"
