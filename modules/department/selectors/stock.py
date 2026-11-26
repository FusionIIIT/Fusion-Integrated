from modules.department.domain.roles import role_kind
from modules.department.models import InventoryItem, StockMovement, StockRequest
from modules.department.selectors.role_assignments import current_holder
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.directory import contracts as directory


def visible_inventory(actor):
    """Returns inventory items visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return InventoryItem.objects.filter(
            department_id__in=department_ids_for_role(actor, kind)
        )
    if kind == "faculty":
        user_record = directory.get_users([actor.user_id]).get(actor.user_id)
        if not user_record:
            return InventoryItem.objects.none()
        return InventoryItem.objects.filter(
            department__code__in=member_department_codes(actor)
        ).select_related("department")
    return InventoryItem.objects.none()


def visible_requests(actor):
    """Returns stock requests visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind == "faculty":
        return StockRequest.objects.filter(
            requester_user_id=actor.user_id
        ).select_related("item", "department")
    if kind in ("hod", "dept_admin"):
        return StockRequest.objects.filter(
            department_id__in=department_ids_for_role(actor, kind)
        ).select_related("item", "department")
    return StockRequest.objects.none()


def issued_history(actor):
    """Returns issued stock requests for a faculty member."""
    if role_kind(actor.active_role) != "faculty":
        return StockRequest.objects.none()
    return StockRequest.objects.filter(
        requester_user_id=actor.user_id, state="issued"
    ).select_related("item", "department")


def visible_movements(actor):
    """Returns stock movements visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return StockMovement.objects.filter(
            item__department_id__in=department_ids_for_role(actor, kind)
        ).select_related("item", "request")
    return StockMovement.objects.none()


def current_role_user_id(department, role):
    """Returns the user_id of the current holder of a department role."""
    holder = current_holder(department, role)
    return holder.user_id if holder else None
