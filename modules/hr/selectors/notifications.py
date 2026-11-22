from django.db.models import QuerySet

from modules.hr.models import HRNotification


def notifications_for(principal) -> QuerySet[HRNotification]:
    return HRNotification.objects.filter(recipient_user_id=principal.user_id).order_by(
        "-created_at"
    )
