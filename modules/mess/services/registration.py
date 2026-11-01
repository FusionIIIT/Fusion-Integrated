from modules.mess.models import RegistrationWindow, RegistrationRequest
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction

@transaction.atomic
def open_window(actor_user_id, title, opens_on, closes_on):
    # Validate with validate_window from modules.mess.domain.registration_rules
    # Raise ValueError joining the errors
    pass

@transaction.atomic
def submit_registration(user_id, window_id, today):
    # Load the window
    window = RegistrationWindow.objects.get(pk=window_id)
    # Raise ValueError unless window_is_open(...) is True
    if not window.is_open(today):
        raise ValueError('Window is not open')
    # Raise ValueError if the user already has a request for this window
    if RegistrationRequest.objects.filter(user=user_id, window=window_id).exists():
        raise ValueError('User already has a request for this window')
    # Create RegistrationRequest PENDING
    request = RegistrationRequest.objects.create(user=user_id, window=window_id, status='PENDING')
    # Record_transition('REGISTRATION', id, 'NONE', 'PENDING', user_id)
    record_transition('REGISTRATION', request.id, 'NONE', 'PENDING', user_id)
    # Queue_notification('REGISTRATION_SUBMITTED', user_id)
    queue_notification('REGISTRATION_SUBMITTED', user_id)
    return request

@transaction.atomic
def review_registration(request_id, actor_user_id, approve, now):
    # Load the request
    request = RegistrationRequest.objects.get(pk=request_id)
    # Only PENDING may change
    if request.status != 'PENDING':
        raise ValueError('Only PENDING may change')
    # Set status APPROVED or REJECTED
    request.status = 'APPROVED' if approve else 'REJECTED'
    request.decided_by = actor_user_id
    request.decided_at = now
    request.save()
    # Record_transition('REGISTRATION', id, 'NONE', 'DECIDED', user_id)
    record_transition('REGISTRATION', request.id, 'NONE', 'DECIDED', actor_user_id)
    # Queue_notification('REGISTRATION_DECIDED', user_id)
    queue_notification('REGISTRATION_DECIDED', actor_user_id)
