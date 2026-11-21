from modules.directory.contracts import get_users
from modules.oap.models import CaseEvent, Notification


class ServiceError(Exception):
    """A business rule refused the request (the API turns it into HTTP 400)."""


def record_event(case_type, case, from_state, to_state, action, actor_id, remark=""):
    return CaseEvent.objects.create(
        case_type=case_type,
        case_id=case.id,
        from_state=from_state,
        to_state=to_state,
        action=action,
        actor_id=actor_id,
        remark=remark,
    )


def notify(recipient_id, message, case_type, case_id):
    """Every notification is an in-app alert and an email (OA-BR-03)."""
    for channel in ("alert", "email"):
        Notification.objects.create(
            recipient_id=recipient_id,
            channel=channel,
            message=message,
            case_type=case_type,
            case_id=case_id,
        )


def directory_user(user_id):
    return get_users([user_id]).get(user_id)


def department_of(user_id):
    user = directory_user(user_id)
    return (user.department or "") if user else ""
