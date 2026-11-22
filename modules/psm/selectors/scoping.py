"""Queryset scoping for PSM entities based on user permissions and departmental context."""

from django.db.models import QuerySet

from modules.psm.models.goods_receipt import GoodsReceiptNote
from modules.psm.models.indent import Indent
from modules.psm.models.purchase_order import PurchaseOrder


def _has_perm(user, code: str) -> bool:
    if hasattr(user, "has_permission"):
        return user.has_permission(code)
    if hasattr(user, "has_perm"):
        return user.has_perm(code)
    return False


def scope_indents_for_user(user, queryset: QuerySet[Indent]) -> QuerySet[Indent]:
    """Scopes indents visible to the acting user.

    - Institute-wide authorities (Director, PS Admin) see all indents.
    - Department Heads and Dept Admins see indents in their department.
    - Plain employees / faculty see only their own raised indents.
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    # Institute authorities
    if _has_perm(user, "psm.indent.approve_director") or _has_perm(user, "psm.indent.approve_ps"):
        return queryset

    # Department level
    if _has_perm(user, "psm.indent.approve_dept"):
        dept = getattr(user, "department", None)
        if dept:
            return queryset.filter(department_code=dept)
        return queryset

    # Own indents only (requestor / employee)
    return queryset.filter(user_id=user.user_id)


def scope_purchase_orders(user, queryset: QuerySet[PurchaseOrder]) -> QuerySet[PurchaseOrder]:
    """Scopes purchase orders visible to the acting user."""
    if not user or not user.is_authenticated:
        return queryset.none()

    if _has_perm(user, "psm.po.view") or _has_perm(user, "psm.po.create"):
        return queryset

    # Employees can see POs created for their own indents
    return queryset.filter(indent__user_id=user.user_id)


def scope_goods_receipts(user, queryset: QuerySet[GoodsReceiptNote]) -> QuerySet[GoodsReceiptNote]:
    """Scopes goods receipt notes visible to the acting user."""
    if not user or not user.is_authenticated:
        return queryset.none()

    if _has_perm(user, "psm.grn.view") or _has_perm(user, "psm.grn.create"):
        return queryset

    # Indent creators see GRNs for their indents
    return queryset.filter(purchase_order__indent__user_id=user.user_id)
