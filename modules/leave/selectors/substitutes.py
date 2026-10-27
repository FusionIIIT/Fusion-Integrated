from django.core.exceptions import ObjectDoesNotExist
from .models import SubstituteRequest

class NotFoundError(Exception):
    pass

def get_substitute_requests_for_user(user_id: int, status: str | None = None) -> list[SubstituteRequest]:
    """
    Returns a queryset of `SubstituteRequest` objects where `substitute_user_id` matches the given `user_id`.
    If `status` is provided, filters by that status as well.
    Results are ordered by `-created_at`.
    """
    query = SubstituteRequest.objects.filter(substitute_user_id=user_id)
    if status:
        query = query.filter(status=status)
    return list(query.order_by('-created_at'))

def get_request_by_id(request_id: int, substitute_user_id: int | None = None) -> SubstituteRequest:
    """
    Returns a `SubstituteRequest` object with the given `request_id`.
    If `substitute_user_id` is provided, filters by that as well.
    Raises `NotFoundError` if no matching request is found.
    """
    try:
        query = SubstituteRequest.objects.filter(id=request_id)
        if substitute_user_id:
            query = query.filter(substitute_user_id=substitute_user_id)
        return query.get()
    except ObjectDoesNotExist:
        raise NotFoundError(f"SubstituteRequest with id {request_id} not found")