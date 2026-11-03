from django.db.models import QuerySet

from modules.oap.models.no_dues import NoDuesAuthorityClearance, NoDuesRequest


def get_student_no_dues(user_id: int) -> QuerySet[NoDuesRequest]:
    return NoDuesRequest.objects.filter(user_id=user_id).prefetch_related("clearances")


def get_all_no_dues() -> QuerySet[NoDuesRequest]:
    return NoDuesRequest.objects.all().prefetch_related("clearances")


def get_no_dues_by_id(request_id: int) -> NoDuesRequest | None:
    return NoDuesRequest.objects.filter(id=request_id).prefetch_related("clearances").first()


def get_clearances_for_domain(domain: str) -> QuerySet[NoDuesAuthorityClearance]:
    return NoDuesAuthorityClearance.objects.filter(domain=domain).select_related("request")
