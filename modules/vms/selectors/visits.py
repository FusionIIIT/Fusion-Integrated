from modules.vms.models import VisitRequest


def visible_visits(*, user_id: int, permissions: set[str] | frozenset[str]):
    qs = VisitRequest.objects.select_related("visitor", "event")
    if "vms.visit_request.view" in permissions:
        return qs
    return qs.filter(host_user_id=user_id)


def visitor_visits(*, visitor_id: int):
    return VisitRequest.objects.filter(visitor_id=visitor_id).select_related("event")


def pending_host_visits(*, user_id: int):
    return VisitRequest.objects.filter(host_user_id=user_id, status="pending").select_related(
        "visitor"
    )
