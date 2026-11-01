from modules.mess.models import User, RegistrationRequest, DeregistrationRequest
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction

@transaction.atomic
def submit_deregistration(user_id, reason, now):
    request = RegistrationRequest.objects.get(user=user, status='APPROVED')
    if DeregistrationRequest.objects.filter(user=user, status__in=['PENDING', 'APPROVED_AWAITING_EFFECTIVE']).exists():
        raise ValueError("User already has a pending or approved deregistration request")
    DeregistrationRequest.objects.create(user=user, status='PENDING')
    record_transition('DEREGISTRATION', request.id, 'NONE', 'PENDING', user_id)
    queue_notification('DEREGISTRATION_SUBMITTED', user_id)

def review_deregistration(request_id, actor_user_id, approve, now):
    request = DeregistrationRequest.objects.get(id=request_id)
    if not can_transition('DEREGISTRATION', request.status, approve):
        raise ValueError("Business rule failed")
    if approve == 'approve':
        request.status = 'APPROVED_AWAITING_EFFECTIVE'
        request.effective_on = deregistration_effective_date(now.date())
        request.decided_by_user_id = actor_user_id
        request.decided_at = now
        request.save()
        record_transition('DEREGISTRATION', request.id, 'NONE', 'APPROVED_AWAITING_EFFECTIVE', actor_user_id)
        queue_notification('DEREGISTRATION_DECIDED', actor_user_id)
    else:
        request.status = 'REJECTED'
        request.save()
        record_transition('DEREGISTRATION', request.id, 'NONE', 'REJECTED', actor_user_id)
        queue_notification('DEREGISTRATION_DECIDED', actor_user_id)
