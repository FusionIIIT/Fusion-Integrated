"""DRF permission classes and declared permissions for VMS API endpoints."""
from rest_framework.permissions import BasePermission

# All declared VMS permissions (must match modules.vms.registry.PERMISSIONS)
PERM_VISITOR_VIEW = "vms.visitor.view"
PERM_VISITOR_REGISTER = "vms.visitor.register"
PERM_VISIT_REQUEST_CREATE = "vms.visit_request.create"
PERM_VISIT_REQUEST_APPROVE = "vms.visit_request.approve"
PERM_VISIT_VIEW = "vms.visit.view"
PERM_VISIT_TERMINATE = "vms.visit.terminate"
PERM_PASS_VIEW = "vms.pass.view"
PERM_PASS_CHECKIN = "vms.pass.checkin"
PERM_PASS_CHECKOUT = "vms.pass.checkout"
PERM_PASS_MANAGE = "vms.pass.manage"
PERM_GATE_MANAGE = "vms.gate.manage"
PERM_ZONE_VALIDATE = "vms.zone.validate"
PERM_ZONE_ELEVATE = "vms.zone.elevate"
PERM_BLACKLIST_MANAGE = "vms.blacklist.manage"
PERM_POLICY_MANAGE = "vms.policy.manage"
PERM_MUSTER_TRIGGER = "vms.muster.trigger"
PERM_MUSTER_VIEW = "vms.muster.view"
PERM_ALERT_VIEW = "vms.alert.view"
PERM_ALERT_MANAGE = "vms.alert.manage"
PERM_REPORT_VIEW = "vms.report.view"
PERM_ROLE_MANAGE = "vms.role.manage"

ALL_VMS_PERMISSIONS = [
    PERM_VISITOR_VIEW,
    PERM_VISITOR_REGISTER,
    PERM_VISIT_REQUEST_CREATE,
    PERM_VISIT_REQUEST_APPROVE,
    PERM_VISIT_VIEW,
    PERM_VISIT_TERMINATE,
    PERM_PASS_VIEW,
    PERM_PASS_CHECKIN,
    PERM_PASS_CHECKOUT,
    PERM_PASS_MANAGE,
    PERM_GATE_MANAGE,
    PERM_ZONE_VALIDATE,
    PERM_ZONE_ELEVATE,
    PERM_BLACKLIST_MANAGE,
    PERM_POLICY_MANAGE,
    PERM_MUSTER_TRIGGER,
    PERM_MUSTER_VIEW,
    PERM_ALERT_VIEW,
    PERM_ALERT_MANAGE,
    PERM_REPORT_VIEW,
    PERM_ROLE_MANAGE,
]


class HasVMSPermission(BasePermission):
    """Checks whether the request user possesses a specific VMS permission."""
    required_permission: str | None = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser:
            return True
        req_perm = getattr(view, "required_permission", self.required_permission)
        if not req_perm:
            return True
        user_perms = getattr(request.user, "permissions", set())
        if hasattr(user_perms, "__iter__"):
            return req_perm in user_perms
        return True


class IsVMSAdmin(BasePermission):
    """Permits VMS administrators and superusers."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser or getattr(request.user, "is_staff", False):
            return True
        perms = getattr(request.user, "permissions", set())
        admin_perms = {
            "vms.policy.manage",
            "vms.blacklist.manage",
            "vms.report.view",
            "vms.role.manage",
            "vms.alert.manage",
        }
        return bool(admin_perms & perms)


class IsSecurityPersonnel(BasePermission):
    """Permits gate guards and campus security officers."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser:
            return True
        perms = getattr(request.user, "permissions", set())
        sec_perms = {
            "vms.pass.checkin",
            "vms.pass.checkout",
            "vms.pass.manage",
            "vms.gate.manage",
            "vms.zone.validate",
            "vms.visitor.register",
            "vms.muster.trigger",
            "vms.muster.view",
            "vms.alert.view",
        }
        return bool(sec_perms & perms)


class IsHost(BasePermission):
    """Permits campus faculty and staff hosts."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser:
            return True
        perms = getattr(request.user, "permissions", set())
        host_perms = {
            "vms.visit_request.approve",
            "vms.visit_request.create",
            "vms.visit.view",
            "vms.visit.terminate",
            "vms.pass.view",
            "vms.visitor.view",
            "vms.zone.elevate",
        }
        return bool(host_perms & perms)
