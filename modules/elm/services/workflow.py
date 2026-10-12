from django.core.exceptions import ValidationError
from django.db import transaction

from modules.elm.models import LeaveDecision, LeaveRequest, SubstituteResponse


@transaction.atomic
def respond_to_substitute(leave_request, actor, decision, note=""):
    if leave_request.status != LeaveRequest.Status.AWAITING_SUBSTITUTE:
        raise ValidationError("This request is not awaiting substitute consent.")
    if leave_request.substitute_id != actor.user_id:
        raise ValidationError("Only the nominated substitute can respond.")

    if decision not in {
        SubstituteResponse.Decision.ACCEPTED,
        SubstituteResponse.Decision.DECLINED,
    }:
        raise ValidationError("Invalid substitute response.")

    SubstituteResponse.objects.create(
        leave_request=leave_request,
        substitute=actor,
        decision=decision,
        note=note,
    )

    if decision == SubstituteResponse.Decision.ACCEPTED:
        leave_request.status = LeaveRequest.Status.UNIT_HEAD_REVIEW
    else:
        leave_request.status = LeaveRequest.Status.APPLICANT_ACTION

    leave_request.save()
    return leave_request


@transaction.atomic
def decide_leave(leave_request, actor, stage, decision, note=""):
    allowed = {
        LeaveRequest.Status.UNIT_HEAD_REVIEW: "unit_head",
        LeaveRequest.Status.ESTABLISHMENT_ROUTING: "establishment",
        LeaveRequest.Status.FINAL_SANCTION: "final_sanction",
        LeaveRequest.Status.DIRECTOR_SANCTION: "director_sanction",
    }
    if allowed.get(leave_request.status) != stage:
        raise ValidationError("This request is not awaiting this decision stage.")

    if decision not in {"approve", "reject", "recommend", "not_recommend", "route"}:
        raise ValidationError("Invalid decision.")

    LeaveDecision.objects.create(
        leave_request=leave_request,
        actor=actor,
        stage=stage,
        decision=decision,
        note=note,
    )

    if stage == "unit_head":
        if leave_request.category in {"CL", "RH"}:
            leave_request.status = (
                LeaveRequest.Status.APPROVED if decision == "approve"
                else LeaveRequest.Status.REJECTED
            )
        else:
            if decision not in {"recommend", "not_recommend"}:
                raise ValidationError("Higher-sanction leave requires a recommendation.")
            leave_request.unit_head_recommended = decision == "recommend"
            leave_request.status = (
                LeaveRequest.Status.ESTABLISHMENT_ROUTING
                if leave_request.establishment_required
                else LeaveRequest.Status.FINAL_SANCTION
            )
    elif stage == "establishment":
        if decision != "route":
            raise ValidationError("Establishment must route the request.")
        leave_request.status = LeaveRequest.Status.FINAL_SANCTION
    else:
        if decision not in {"approve", "reject"}:
            raise ValidationError("Final sanction requires approve or reject.")
        leave_request.status = (
            LeaveRequest.Status.APPROVED if decision == "approve"
            else LeaveRequest.Status.REJECTED
        )
        leave_request.final_decision_by = actor
        leave_request.decision_note = note

    leave_request.save()
    return leave_request
