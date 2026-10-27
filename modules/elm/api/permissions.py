"""ELM API permission classes using fusion_auth gates."""
from fusion_auth.permissions import HasModuleGrant, HasPermission

RequireElmModule = HasModuleGrant("elm")
RequireLeaveApply = HasPermission("elm.leave.apply")
RequireLeaveView = HasPermission("elm.leave.view_self")
RequireLeaveSubstitute = HasPermission("elm.leave.substitute")
RequireLeaveReview = HasPermission("elm.leave.review")
RequireLeaveAdmin = HasPermission("elm.leave.admin")
