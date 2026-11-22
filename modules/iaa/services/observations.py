"""Audit observations: raise, respond, verify and close (UC-501/502/503, BR-301/302)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.iaa.domain import roles
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import AuditObservation, ObservationResponse
from modules.iaa.selectors import scoping
from modules.iaa.services import notify, trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import domain_errors, lock, now

P_CREATE = "iaa.observation.create"
P_RESPOND = "iaa.observation.update"
P_REVIEW = "iaa.observation.review"
SATISFACTORY = ObservationResponse.SATISFACTORY
UNSATISFACTORY = ObservationResponse.UNSATISFACTORY
NOT_FOUND = "That audit observation does not exist, or is not visible to you."


def _kind(actor) -> str:
    return roles.actor_kind(role_of(actor))


@transaction.atomic
def raise_observation(actor, *, title: str, detail: str, record_id: int | None = None,
                      respondent_user_id: int | None = None) -> AuditObservation:
    require(actor, P_CREATE)
    if _kind(actor) != roles.AUDITOR_ACTOR:
        raise ConflictError("Only an Auditor may raise an audit observation.",
                            code="actor_not_allowed")
    if not title.strip() or not detail.strip():
        raise DomainError("Give the observation a title and describe the finding.",
                          code="observation_incomplete")
    record = None
    if record_id is not None:
        record = scoping.records_for(actor).filter(pk=record_id).first()
        if record is None:
            raise NotFoundError("That request or claim is not visible to your role.")
        respondent_user_id = respondent_user_id or record.user_id
    if respondent_user_id is None:
        raise DomainError("Name the user who must respond, or link a request or claim.",
                          code="respondent_required")
    obs = AuditObservation.objects.create(
        record=record, respondent_user_id=respondent_user_id, title=title, detail=detail,
        raised_by=actor.user_id, raised_role=role_of(actor))
    trail.log("observation", obs.pk, "raise", actor=actor, to=sm.OBS_OPEN, remarks=title)
    notify.to_user(respondent_user_id, "observation",
                   f"Audit observation #{obs.pk} needs your response: {title}",
                   "observation", obs.pk)
    return obs


@transaction.atomic
def respond(actor, pk: int, *, corrective_action: str, evidence_link: str = ""
            ) -> AuditObservation:
    require(actor, P_RESPOND)
    if not corrective_action.strip():
        raise DomainError("Describe the corrective action taken.", code="response_required")
    obs = lock(scoping.observations_for(actor).filter(respondent_user_id=actor.user_id), pk,
               NOT_FOUND)
    with domain_errors():
        t = sm.resolve_observation(obs.status, sm.RESPOND, sm.RESPONDENT)
    ObservationResponse.objects.create(observation=obs, cycle=obs.cycle,
                                       corrective_action=corrective_action,
                                       evidence_link=evidence_link, responded_by=actor.user_id)
    obs.status = t.to
    obs.save(update_fields=["status", "updated_at"])
    trail.log("observation", obs.pk, "respond", actor=actor, frm=t.frm, to=t.to,
              remarks=corrective_action)
    notify.to_role(roles.AUDITOR, "observation_responded",
                   f"Audit observation #{obs.pk} has a response to verify.", "observation", obs.pk)
    return obs


@transaction.atomic
def review(actor, pk: int, *, verdict: str, remarks: str = "") -> AuditObservation:
    require(actor, P_REVIEW)
    if verdict not in (SATISFACTORY, UNSATISFACTORY):
        raise DomainError("Verdict must be 'satisfactory' or 'unsatisfactory'.",
                          code="invalid_verdict")
    if verdict == UNSATISFACTORY and not remarks.strip():
        raise DomainError("Tell the respondent what is still missing.", code="remarks_required")
    obs = lock(scoping.observations_for(actor), pk, NOT_FOUND)
    event = sm.CLOSE if verdict == SATISFACTORY else sm.RETURN
    with domain_errors():
        t = sm.resolve_observation(obs.status, event, _kind(actor))
    response = ObservationResponse.objects.select_for_update().get(observation=obs,
                                                                     cycle=obs.cycle)
    response.verdict, response.review_remarks = verdict, remarks
    response.reviewed_by, response.reviewed_at = actor.user_id, now()
    response.save()
    obs.status = t.to
    if event == sm.RETURN:
        obs.cycle += 1
    obs.save(update_fields=["status", "cycle", "updated_at"])
    trail.log("observation", obs.pk, event, actor=actor, frm=t.frm, to=t.to, remarks=remarks)
    message = (f"Audit observation #{obs.pk} is closed." if event == sm.CLOSE else
               f"Audit observation #{obs.pk} needs another response: {remarks}")
    notify.to_user(obs.respondent_user_id, f"observation_{event}", message, "observation", obs.pk)
    return obs
