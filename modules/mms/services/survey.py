"""Vacation food continuity surveys (BR-MMS-026/027/041; UC-016/017/028/031;
BW-MMS-08/09/10, CW-MMS-04)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import rules
from modules.mms.domain.exceptions import GuardFailed
from modules.mms.models import VacationResponse, VacationSurvey
from modules.mms.services import authz, notifications


def create(actor, vacation: str, response_deadline) -> VacationSurvey:
    """BR-MMS-026: Caretaker creates a survey for currently registered
    students only."""
    authz.require(actor, "mms.survey.create")
    if response_deadline <= timezone.now():
        raise ConflictError("The response deadline must be in the future.")
    survey = VacationSurvey.objects.create(
        vacation=vacation,
        response_deadline=response_deadline,
        is_open=True,
        created_by_user_id=actor.user_id,
    )
    notifications.enqueue(
        topic="survey.created",
        dedupe_key=f"survey.created:{survey.pk}",
        subject="Vacation food continuity survey",
        body=f"A vacation food continuity survey for {vacation} is now open. "
        f"Please respond Yes or No before {response_deadline}.",
        recipient_email="mms-broadcast@invalid",
        payload={"audience": "students", "survey_id": survey.pk, "vacation": vacation},
    )
    return survey


def respond(actor, survey_id: int, response: str) -> VacationResponse:
    """BR-MMS-041: Yes or No only; before the deadline."""
    authz.require(actor, "mms.survey_response.create")
    try:
        rules.valid_vacation_response(response)
    except GuardFailed as exc:
        raise ConflictError(exc.message) from exc
    now = timezone.now()
    with transaction.atomic():
        survey = (
            VacationSurvey.objects.filter(pk=survey_id, is_open=True, response_deadline__gt=now)
            .select_for_update()
            .first()
        )
        if survey is None:
            raise NotFoundError("No open vacation survey accepting responses.")
        own = actor.user_id
        resp, _ = VacationResponse.objects.update_or_create(
            survey=survey_id,
            student_user_id=own,
            defaults={"response": response, "responded_at": now},
        )
    return resp


def apply_default_no() -> int:
    """UC-028 / BR-MMS-027: default No for registered students with no
    response at the deadline. Idempotent."""
    now = timezone.now()
    due = VacationSurvey.objects.filter(is_open=True, response_deadline__lte=now)
    count = 0
    for survey in due:
        # Students with no response get default_no. "Currently registered"
        # is represented by an approved registration (no cross-module source).
        from modules.mms.models import Registration

        registered = set(
            Registration.objects.filter(status="approved").values_list("user_id", flat=True)
        )
        responded = set(
            VacationResponse.objects.filter(survey=survey.pk).values_list(
                "student_user_id", flat=True
            )
        )
        for uid in registered - responded:
            VacationResponse.objects.update_or_create(
                survey=survey.pk,
                student_user_id=uid,
                defaults={"response": "default_no", "responded_at": survey.response_deadline},
            )
        survey.is_open = False
        survey.save(update_fields=["is_open", "updated_at"])
        notifications.enqueue(
            topic="survey.default_no",
            dedupe_key=f"survey.default_no:{survey.pk}",
            subject="Vacation survey closed",
            body=f"The vacation survey '{survey.vacation}' has closed and "
            f"non-responding students are recorded as No.",
            recipient_email="mms-broadcast@invalid",
            payload={"audience": "students", "survey_id": survey.pk},
        )
        count += 1
    return count


def send_reminders() -> int:
    """UC-031: send survey reminders. Cadence is institution-defined and is
    supplied externally; this enqueues reminder events for open surveys."""
    now = timezone.now()
    open_surveys = VacationSurvey.objects.filter(is_open=True, response_deadline__gt=now)
    count = 0
    for survey in open_surveys:
        notifications.enqueue(
            topic="survey.reminder",
            dedupe_key=f"survey.reminder:{survey.pk}:{now.date()}",
            subject=f"Reminder: {survey.vacation} survey",
            body=f"You have not yet responded to the vacation food continuity "
            f"survey for {survey.vacation}. Please respond Yes or No "
            f"before {survey.response_deadline}.",
            recipient_email="mms-broadcast@invalid",
            payload={"audience": "students", "survey_id": survey.pk},
        )
        count += 1
    return count
