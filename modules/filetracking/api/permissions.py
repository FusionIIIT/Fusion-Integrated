"""Permission constants and gates for File Tracking System."""

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE = HasModuleGrant("filetracking")

P_FILE_VIEW = "filetracking.file.view"
P_FILE_CREATE = "filetracking.file.create"
P_FILE_FORWARD = "filetracking.file.forward"
P_FILE_RETURN = "filetracking.file.return"
P_FILE_ARCHIVE = "filetracking.file.archive"
P_GOVERNANCE_VIEW = "filetracking.governance.view"
P_GOVERNANCE_MANAGE = "filetracking.governance.manage"
P_API_INTEGRATE = "filetracking.api.integrate"


def require_permission(perm_code: str):
    """Return permission class tuple for module grant + specific permission."""
    return [MODULE, HasPermission(perm_code)]
