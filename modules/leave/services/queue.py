"""The decisions a task offers, so the screen never offers an illegal one."""
from __future__ import annotations

from modules.leave.domain import categories as cat
from modules.leave.domain import sla
from modules.leave.domain import state_machine as sm
from modules.leave.models import Task


def actions_for(task: Task) -> list[str]:
    if task.status != Task.OPEN:
        return []
    if task.step == sla.RESUMPTION_REVIEW:
        return ["review"]
    req = task.request
    category = req.parent.category if req.parent_id else req.category
    if task.step == sm.UNIT_HEAD:
        if cat.get(category).unit_head_final and req.kind != sm.EXTENSION:
            return ["approve", "reject"]
        return ["recommend", "not_recommend"]
    if task.step == sm.ESTABLISHMENT:
        return ["forward"]
    if task.step in (sm.AUTHORITY, sm.DIRECTOR):
        return ["approve", "reject"]
    return []
