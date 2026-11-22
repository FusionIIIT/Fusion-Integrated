"""Hostel access uses IAM module and action grants, never Django is_staff."""

from rest_framework.permissions import BasePermission


class HostelPermission(BasePermission):
    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if not (
            principal
            and principal.kind in {"student", "faculty", "staff"}
            and principal.has_module("visitor_hostel")
            and principal.has_permission(view.permission_code)
        ):
            return False
        role = ROLE_FOR_PERMISSION.get(view.permission_code)
        return role is None or holds_role(principal, role)


ROLE_FOR_PERMISSION = {
    "visitor_hostel.booking.manage": "vh_caretaker",
    "visitor_hostel.inventory.manage": "vh_caretaker",
    "visitor_hostel.booking.approve": "vh_in_charge",
    "visitor_hostel.inventory.approve": "vh_in_charge",
    "visitor_hostel.tariff.manage": "vh_in_charge",
}


def holds_role(principal, role):
    from django.utils import timezone

    from .models import RoleAssignment

    now = timezone.now()
    return RoleAssignment.objects.filter(
        role=role, user_id=principal.user_id, starts_at__lte=now, ends_at__gt=now
    ).exists()


def is_operator(principal):
    return (
        principal.has_permission("visitor_hostel.booking.manage")
        and holds_role(principal, "vh_caretaker")
    ) or (
        principal.has_permission("visitor_hostel.booking.approve")
        and holds_role(principal, "vh_in_charge")
    )
