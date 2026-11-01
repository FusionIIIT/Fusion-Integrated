"""Notifications selectors (BR-PHC-07, 11, 13)."""
from modules.phc.models.notifications import PHCNotification


def get_user_notifications(user_id: int) -> list[PHCNotification]:
    return list(PHCNotification.objects.filter(recipient_user_id=user_id).order_by("-created_at")[:50])


def count_unread_notifications(user_id: int) -> int:
    return PHCNotification.objects.filter(recipient_user_id=user_id, is_read=False).count()
