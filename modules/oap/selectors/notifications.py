from django.db.models import QuerySet

from modules.oap.models.notification import OAPNotification


def get_notifications_for_user(user_id: int, unread_only: bool = False) -> QuerySet[OAPNotification]:
    qs = OAPNotification.objects.filter(recipient_user_id=user_id)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs
