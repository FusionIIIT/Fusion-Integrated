from django.db.models import QuerySet

from modules.oap.domain import constants as c
from modules.oap.models.seminar import GraduateSeminar


def get_student_seminar_requests(user_id: int) -> QuerySet[GraduateSeminar]:
    return GraduateSeminar.objects.filter(user_id=user_id)


def get_all_scheduled_seminars() -> QuerySet[GraduateSeminar]:
    return GraduateSeminar.objects.filter(status=c.SEMINAR_SCHEDULED)


def get_all_seminar_requests() -> QuerySet[GraduateSeminar]:
    return GraduateSeminar.objects.all()


def get_seminar_by_id(seminar_id: int) -> GraduateSeminar | None:
    return GraduateSeminar.objects.filter(id=seminar_id).first()
