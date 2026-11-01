from modules.mess.models import RebateRequest, RebateRule
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction
from datetime import datetime

@transaction.atomic
def submit_rebate(user_id, reason, explanation, start_date, end_date, today):
    # Get existing pending and approved rebate requests
    pending_requests = RebateRequest.objects.filter(user=user_id, status='PENDING')
    approved_requests = RebateRequest.objects.filter(user=user_id, status='APPROVED')

    # Validate the rebate rules
    errors = RebateRule.validate(start_date, end_date, today, pending_requests, approved_requests)
    if errors:
        raise ValueError('Validation errors: ' + ', '.join(errors))

    # Create a new pending rebate request
    request = RebateRequest(user=user_id, reason=reason, explanation=explanation, start_date=start_date, end_date=end_date, status='PENDING')
    request.save()

    # Record the transition
    record_transition('REBATE', request.id, 'NONE', 'PENDING', user_id)

    # Queue the notification
    queue_notification('REBATE_SUBMITTED', user_id)

def review_rebate(request_id, actor_user_id, approve, now, new_start=None, new_end=None):
    request = RebateRequest.objects.get(id=request_id)

    if not request.can_transition('REBATE'):
        raise ValueError('Cannot transition to REBATE state')

    if approve:
        request.approved_start_date = new_start or request.start_date
        request.approved_end_date = new_end or request.end_date
        request.decided_by_user_id = actor_user_id
        request.decided_at = now
    else:
        request.status = 'REJECTED'

    request.save()

    # Record the transition
    record_transition('REBATE', request.id, 'NONE', 'PENDING', actor_user_id)

    # Queue the notification
    queue_notification('REBATE_DECIDED', actor_user_id)
