from django.db import transaction
from modules.mess.models import DeregistrationRequest, VacationSurvey, SpecialFoodRequest
from modules.mess.services._audit import record_transition, queue_notification

@transaction.atomic
def activate_due_deregistrations(today):
    count = 0
    for request in DeregistrationRequest.objects.filter(status=DeregistrationRequest.APPROVED_AWAITING_EFFECTIVE, effective_on__lte=today):
        request.status = DeregistrationRequest.EFFECTIVE
        request.save()
        count += 1
    return count

@transaction.atomic
def apply_default_vacation_responses(now, registered_user_ids):
    count = 0
    for survey in VacationSurvey.objects.filter(response_deadline__lte=now, response=None):
        for user_id in registered_user_ids:
            if not VacationResponse.objects.filter(user_id=user_id).exists():
                VacationResponse.objects.create(user_id=user_id, response=VacationResponse.DEFAULT_NO)
                count += 1
        survey.status = VacationSurvey.CLOSED
        survey.save()
    return count

@transaction.atomic
def reject_expired_special_food(now):
    count = 0
    for request in SpecialFoodRequest.objects.filter(status=SpecialFoodRequest.REQUESTED, is_decision_expired=True):
        request.status = SpecialFoodRequest.REJECTED
        request.rejected_by_default = True
        request.save()
        record_transition('SPECIAL_FOOD', request.id, 'REQUESTED', 'REJECTED', None, actor_label='system')
        queue_notification('SPECIAL_FOOD_DECIDED', request.user_id)
        count += 1
    return count
