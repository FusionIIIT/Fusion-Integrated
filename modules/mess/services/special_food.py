from modules.mess.models import SpecialFoodRequest
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction

def validate_lead_time(request_date, requested_for):
    # Implement your lead time validation logic here
    pass

@transaction.atomic
def submit_special_food(user_id, requested_for, reason_type, description, now):
    if not validate_lead_time(now.date(), requested_for):
        raise ValueError("Lead time validation failed")

    request = SpecialFoodRequest.objects.create(user_id=user_id, requested_for=requested_for, reason_type=reason_type, description=description)
    record_transition('SPECIAL_FOOD', request.id, 'NONE', 'REQUESTED', user_id)
    queue_notification('SPECIAL_FOOD_SUBMITTED', user_id)

def review_special_food(request_id, actor_user_id, approve, now, charge_amount=None):
    request = SpecialFoodRequest.objects.get(id=request_id)
    if is_decision_expired(request.created_at, now):
        raise ValueError("Decision has expired")

    if not can_transition('SPECIAL_FOOD', request.status):
        raise ValueError("Business rule failed")

    if approve:
        request.status = 'APPROVED'
        if charge_amount:
            request.charge_amount = charge_amount
        request.decided_by_user_id = actor_user_id
        request.decided_at = now
        request.save()
        record_transition('SPECIAL_FOOD', request.id, 'APPROVED', 'DECIDED', actor_user_id)
        queue_notification('SPECIAL_FOOD_DECIDED', actor_user_id)
    else:
        request.status = 'REJECTED'
        request.decided_by_user_id = actor_user_id
        request.decided_at = now
        request.save()
        record_transition('SPECIAL_FOOD', request.id, 'APPROVED', 'REJECTED', actor_user_id)
        queue_notification('SPECIAL_FOOD_DECIDED', actor_user_id)

def is_decision_expired(created_at, now):
    # Implement your decision expiration logic here
    pass

def can_transition(state, status):
    # Implement your transition logic here
    pass

def update_fulfillment(request_id, actor_user_id, outcome):
    request = SpecialFoodRequest.objects.get(id=request_id)
    if outcome not in ['SERVED', 'CANCELLED']:
        raise ValueError("Invalid outcome")

    if request.status != 'APPROVED':
        raise ValueError("Request must be APPROVED")

    if not can_transition('SPECIAL_FOOD', request.status):
        raise ValueError("Business rule failed")

    request.outcome = outcome
    request.decided_by_user_id = actor_user_id
    request.decided_at = now
    request.save()
    record_transition('SPECIAL_FOOD', request.id, request.status, outcome, actor_user_id)
    queue_notification('SPECIAL_FOOD_FULFILLMENT', actor_user_id)
