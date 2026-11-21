"""The task queue of whoever holds a reviewing role.

The Unit Head sees only their own unit (the directory's department). The
sanctioning roles see every request that has reached them.
"""
from __future__ import annotations

from modules.directory import contracts as directory
from modules.elm.domain import workflow as wf
from modules.elm.models import LeaveApplication

P_REVIEW = "elm.leave.review"
P_ROUTE = "elm.leave.route"
P_SANCTION = "elm.leave.sanction"
P_SELF_SANCTION = "elm.leave.self_sanction"


def department_of(user_id: int) -> str:
    person = directory.get_users([user_id]).get(user_id)
    return person.department if person else ""


def same_unit(reviewer_id: int, applicant_id: int) -> bool:
    """Both must belong to the same, known unit; an unknown unit never matches."""
    people = directory.get_users([reviewer_id, applicant_id])
    reviewer, applicant = people.get(reviewer_id), people.get(applicant_id)
    return bool(reviewer and applicant and reviewer.department
                and reviewer.department == applicant.department)


def tasks_for(principal) -> list[LeaveApplication]:
    states = []
    if principal.has_permission(P_REVIEW):
        states += [wf.AWAITING_UNIT_HEAD, wf.RESUMPTION_PENDING]
    if principal.has_permission(P_ROUTE):
        states.append(wf.AWAITING_ESTABLISHMENT)
    if principal.has_permission(P_SANCTION):
        states.append(wf.AWAITING_FINAL)
    rows = list(LeaveApplication.objects.filter(status__in=states)
                .exclude(user_id=principal.user_id).order_by("waiting_since")[:200])
    if principal.has_permission(P_REVIEW):
        unit = department_of(principal.user_id)
        unit_states = {wf.AWAITING_UNIT_HEAD, wf.RESUMPTION_PENDING}
        people = directory.get_users({r.user_id for r in rows if r.status in unit_states})
        rows = [r for r in rows if r.status not in unit_states
                or (unit and r.user_id in people and people[r.user_id].department == unit)]
    if principal.has_permission(P_SELF_SANCTION):
        rows += list(LeaveApplication.objects.filter(
            user_id=principal.user_id, status=wf.AWAITING_DIRECTOR))
    return rows


def can_view(principal, application: LeaveApplication) -> bool:
    """Who may open one application: the applicant, the substitute, the unit head of the
    applicant's unit, or a holder of a role that handles it. Anyone else gets a 404."""
    if principal.user_id in (application.user_id, application.substitute_user_id):
        return True
    if principal.has_any_permission(P_ROUTE, P_SANCTION, "elm.leave.administer"):
        return True
    return principal.has_permission(P_REVIEW) and same_unit(
        principal.user_id, application.user_id)
