from modules.elm.models import Notification


def notify(*, topic: str, title: str, body: str, user_id: int | None = None,
           role: str = "", payload: dict | None = None) -> Notification:
    return Notification.objects.create(recipient_user_id=user_id, recipient_role=role,
        topic=topic, title=title, body=body, payload=payload or {})
