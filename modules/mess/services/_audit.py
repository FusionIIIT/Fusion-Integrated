from modules.mess.models import RequestTransition, NotificationEvent

def record_transition(request_type, request_id, from_status, to_status, actor_user_id=None, reason='', actor_label=''):
    transition = RequestTransition(request_type=request_type, request_id=request_id, from_status=from_status, to_status=to_status, actor_user_id=actor_user_id, reason=reason, actor_label=actor_label)
    transition.save()
    return transition

def queue_notification(event_type, user_id, payload=None):
    if payload is None:
        payload = {}
    notification = NotificationEvent(event_type=event_type, user_id=user_id, payload=payload, status='PENDING')
    notification.save()
    return notification
