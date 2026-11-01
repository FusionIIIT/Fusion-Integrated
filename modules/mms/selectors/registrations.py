"""MMS registration selectors.

Ownership is enforced by narrowing the queryset — never by fetching a row
and then checking fields. A row you may not see is a 404, not a 403.
"""
from django.db.models import QuerySet

from modules.mms.models import RegistrationRequest, RegistrationWindow


def open_windows() -> QuerySet[RegistrationWindow]:
    """Windows that are currently accepting submissions."""
    from django.utils import timezone
    now = timezone.now()
    return RegistrationWindow.objects.filter(opens_at__lte=now, closes_at__gte=now)


def visible_requests(principal) -> QuerySet[RegistrationRequest]:
    """Return the registration requests the caller may see.

    - mms.registration.view  → all requests (Caretaker / Warden scope)
    - otherwise              → only the caller's own requests (Student scope)
    """
    qs = RegistrationRequest.objects.select_related("window")
    if principal.has_permission("mms.registration.view"):
        return qs
    return qs.filter(student_user_id=principal.user_id)


def pending_requests() -> QuerySet[RegistrationRequest]:
    """All requests awaiting a Caretaker decision."""
    return RegistrationRequest.objects.filter(
        status=RegistrationRequest.STATUS_PENDING
    ).select_related("window")
