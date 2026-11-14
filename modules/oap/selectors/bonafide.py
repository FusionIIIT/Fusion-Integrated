from django.db.models import QuerySet

from modules.oap.models.bonafide import BonafideRequest


def get_student_bonafides(user_id: int) -> QuerySet[BonafideRequest]:
    return BonafideRequest.objects.filter(user_id=user_id)


def get_all_bonafides() -> QuerySet[BonafideRequest]:
    return BonafideRequest.objects.all()


def get_bonafide_by_id(bonafide_id: int) -> BonafideRequest | None:
    return BonafideRequest.objects.filter(id=bonafide_id).first()
