"""Read-only selectors for visitor and visit requests."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import QuerySet

from modules.vms.models import Visitor, VisitRequest


def get_live_onsite_visitors() -> QuerySet[VisitRequest]:
    """Return all currently on-site visitors (CHECKED_IN)."""
    return (
        VisitRequest.objects.filter(status="CHECKED_IN")
        .select_related("visitor", "digital_pass")
        .order_by("-actual_check_in")
    )


def list_visits_scoped(
    user_id: int | None = None,
    roles: Sequence[str] = (),
    status: str | None = None,
    host_id: int | None = None,
    search: str | None = None,
    is_admin: bool = False,
) -> QuerySet[VisitRequest]:
    """Return visits strictly scoped by the caller's role."""
    qs = VisitRequest.objects.select_related("visitor", "digital_pass").all()

    # Scope filtering:
    # Admins and Security can see all visits
    is_staff = is_admin or any(
        r in {"Super Admin", "Admin", "Security Personnel", "admin", "security"} for r in roles
    )

    if not is_staff and user_id is not None:
        # Default host scope
        qs = qs.filter(host_id=user_id)
    elif host_id is not None:
        qs = qs.filter(host_id=host_id)

    if status:
        qs = qs.filter(status=status)

    if search:
        qs = qs.filter(visitor__name__icontains=search)

    return qs.order_by("-created_at")


def get_visit_by_id(visit_id: int) -> VisitRequest | None:
    """Retrieve visit request by primary key."""
    return (
        VisitRequest.objects.filter(pk=visit_id).select_related("visitor", "digital_pass").first()
    )


def get_visitor_by_contact(phone: str, email: str) -> Visitor | None:
    """Find visitor by phone or email."""
    res = Visitor.objects.filter(phone=phone).first()
    if res:
        return res
    return Visitor.objects.filter(email=email).first()
