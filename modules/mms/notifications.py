import logging

logger = logging.getLogger(__name__)

def trigger_mms_notification(event_type: str, recipient_user, payload: dict = None):
    """
    Triggers system-generated notifications for MMS events (BR-MMS-035).
    External email delivery infrastructure is outside MMS scope.
    """
    logger.info(f"[MMS-NOTIFICATION] Event: {event_type} | To: {recipient_user} | Data: {payload}")
    return True