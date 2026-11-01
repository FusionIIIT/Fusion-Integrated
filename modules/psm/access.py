from core.api.exceptions import PermissionDeniedError
from modules.psm.domain.permissions import ROLE_PERMISSION
from modules.psm.models import Membership


def member(principal):
    if principal is None or not principal.has_module("psm"):
        raise PermissionDeniedError("Purchase and Stores module access is required.")
    row = Membership.objects.filter(user_id=principal.user_id).first()
    if row is None:
        raise PermissionDeniedError("A PSM role and department must be assigned.")
    if not principal.has_permission("psm.workspace.view") or not principal.has_permission(
        ROLE_PERMISSION.get(row.role, "")
    ):
        raise PermissionDeniedError()
    return row


def require(principal, roles, department=None):
    row = member(principal)
    if row.role not in roles or not principal.has_permission("psm.workflow.manage"):
        raise PermissionDeniedError()
    if (
        department
        and row.role in ("department_admin", "department_head")
        and row.department != department
    ):
        raise PermissionDeniedError("This action is outside your department.")
    return row
