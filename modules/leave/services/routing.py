"""Authority resolution (BR-EL-019, BR-EL-020) and workflow tasks."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from modules.leave.domain.eligibility import PolicySnapshot
from modules.leave.domain.state_machine import (
    AWAITING_DIRECTOR_SELF, AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION,
    AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD,
)
from modules.leave.models import LeaveApplication, WorkflowTask


def is_director(actor) -> bool:
    role = (getattr(actor, "active_role", None) or "")
    roles = {r.lower() for r in getattr(actor, "roles", ())}
    return role.lower() == "director" or "director" in roles


def actor_kind(actor, application: LeaveApplication | None = None) -> str:
    if actor is None:
        return "system"
    if is_director(actor):
        return "director"
    role = (getattr(actor, "active_role", None) or "").lower()
    if role in {"leave administrator"}:
        return "leave_admin"
    if role in {"deputy registrar (estt.)", "deputy registrar (estt)"}:
        return "establishment"
    if role in {"dean", "registrar"}:
        return "sanctioning_authority"
    if role in {"unit head", "hod"} or role.startswith("hod"):
        return "unit_head"
    if application is not None and getattr(actor, "user_id", None) == application.substitute_user_id:
        return "substitute"
    if application is not None and getattr(actor, "user_id", None) == application.user_id:
        return "employee"
    check = getattr(actor, "has_permission", None)
    if check and check("leave.application.approve"):
        if role.startswith("hod") or "head" in role:
            return "unit_head"
        return "sanctioning_authority"
    if check and check("leave.application.review"):
        return "unit_head"
    return "employee"


def next_status_after_submit(application: LeaveApplication,
                             policy: PolicySnapshot) -> str:
    if application.requires_substitute and application.substitute_status != "accepted":
        return AWAITING_SUBSTITUTE
    if application.applicant_is_director:
        return AWAITING_DIRECTOR_SELF
    return AWAITING_UNIT_HEAD


def after_unit_head(application: LeaveApplication, policy: PolicySnapshot) -> str:
    from modules.leave.domain.state_machine import is_higher_sanction, is_unit_head_final

    if is_unit_head_final(application.category):
        raise RuntimeError("CL/RH do not continue past Unit Head.")
    if is_higher_sanction(application.category) and policy.establishment_step_enabled:
        return AWAITING_ESTABLISHMENT
    return AWAITING_FINAL_SANCTION


def close_open_tasks(application: LeaveApplication) -> None:
    WorkflowTask.objects.filter(application=application, status="pending").update(
        status="cancelled")


def supersede_open_tasks(application: LeaveApplication) -> None:
    WorkflowTask.objects.filter(application=application, status="pending").update(
        status="superseded")


def open_task(application: LeaveApplication, kind: str, *,
              assignee_user_id: int | None, assignee_role: str,
              policy: PolicySnapshot) -> WorkflowTask:
    now = timezone.now()
    return WorkflowTask.objects.create(
        application=application, kind=kind, status="pending",
        assignee_user_id=assignee_user_id, assignee_role=assignee_role,
        sla_controlled=True,
        reminder_at=now + timedelta(hours=policy.sla_reminder_hours),
        escalate_at=now + timedelta(hours=policy.sla_escalation_hours),
    )


def open_routing_task(application: LeaveApplication, policy: PolicySnapshot) -> None:
    status = application.status
    if status == AWAITING_SUBSTITUTE:
        open_task(application, "substitute",
                  assignee_user_id=application.substitute_user_id,
                  assignee_role="Substitute", policy=policy)
    elif status == AWAITING_UNIT_HEAD:
        open_task(application, "unit_head", assignee_user_id=None,
                  assignee_role="Unit Head", policy=policy)
    elif status == AWAITING_ESTABLISHMENT:
        open_task(application, "establishment", assignee_user_id=None,
                  assignee_role="Deputy Registrar (Estt.)", policy=policy)
    elif status == AWAITING_FINAL_SANCTION:
        open_task(application, "final_sanction", assignee_user_id=None,
                  assignee_role="Sanctioning Authority", policy=policy)
    elif status == AWAITING_DIRECTOR_SELF:
        open_task(application, "director_self", assignee_user_id=application.user_id,
                  assignee_role="Director", policy=policy)
