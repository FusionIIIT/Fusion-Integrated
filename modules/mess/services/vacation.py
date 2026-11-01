from modules.mess.models import VacationSurvey, VacationResponse
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction
import datetime

@transaction.atomic
def create_survey(actor_user_id, title, vacation_start, vacation_end, response_deadline):
    if not response_deadline:
        raise ValueError("Response deadline is missing.")
    
    survey = VacationSurvey.objects.create(status=VacationSurvey.OPEN, actor_user_id=actor_user_id, title=title, vacation_start=vacation_start, vacation_end=vacation_end, response_deadline=response_deadline)
    return survey

def respond(survey_id, user_id, answer, now, registered_user_ids):
    survey = VacationSurvey.objects.get(pk=survey_id)

    if survey.status != VacationSurvey.OPEN:
        raise ValueError("The survey status is not OPEN.")

    if now > survey.response_deadline:
        raise ValueError("The response deadline has passed.")

    if user_id not in registered_user_ids:
        raise ValueError("The user is not registered.")

    response = validate_response(answer)
    record_transition(survey, user_id, response)
    queue_notification(survey, user_id, response)

    return VacationResponse.objects.create(survey=survey, user_id=user_id, response=response)
