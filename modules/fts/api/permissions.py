"""API authorization permissions for FTS."""
from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant, HasPermission

RequireFtsModule = HasModuleGrant("fts")
RequireFileCreate = HasPermission("fts.file.create")
RequireFileForward = HasPermission("fts.file.forward")
RequireFileReturn = HasPermission("fts.file.return")
RequireFileArchive = HasPermission("fts.file.archive")
RequireFileView = HasPermission("fts.file.view")
RequireGovernanceView = HasPermission("fts.governance.view")
RequireIntegrationAccess = HasPermission("fts.integration.access")


class IsInstituteEmployee(BasePermission):
    message = "Only faculty and staff Institute Employees may perform operational file actions."

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        if not principal:
            return False
        return principal.kind in ("faculty", "staff")
