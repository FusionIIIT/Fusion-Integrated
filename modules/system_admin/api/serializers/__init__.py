"""System Admin serializers package."""

from .archival import (
    ArchivedRecordReadSerializer,
    ArchiveHistoricalDataSerializer,
    ArchiveUserRequestSerializer,
    AuthorizePurgeSerializer,
    PurgeRequestReadSerializer,
    RequestPurgeSerializer,
    RestoreUserRequestSerializer,
)
from .audit import (
    AuditLogReadSerializer,
    SuperAdminLoginSerializer,
    SuperAdminLogoutSerializer,
)
from .config import UpdateSystemConfigurationSerializer
from .roles import (
    AssignRoleSerializer,
    ExtendRoleSerializer,
    ReassignRoleSerializer,
    RevokeRoleSerializer,
    RoleAssignmentReadSerializer,
    RoleDefinitionSerializer,
    SwitchActiveRoleSerializer,
)
from .users import (
    BasicUserCreateSerializer,
    BasicUserReadSerializer,
    BasicUserUpdateSerializer,
    BulkOperationLogSerializer,
    BulkStatusUpdateSerializer,
    BulkUserCreateSerializer,
    UserStatusActionSerializer,
)

__all__ = [
    "ArchiveHistoricalDataSerializer",
    "ArchiveUserRequestSerializer",
    "ArchivedRecordReadSerializer",
    "AssignRoleSerializer",
    "AuditLogReadSerializer",
    "AuthorizePurgeSerializer",
    "BasicUserCreateSerializer",
    "BasicUserReadSerializer",
    "BasicUserUpdateSerializer",
    "BulkOperationLogSerializer",
    "BulkStatusUpdateSerializer",
    "BulkUserCreateSerializer",
    "ExtendRoleSerializer",
    "PurgeRequestReadSerializer",
    "ReassignRoleSerializer",
    "RequestPurgeSerializer",
    "RestoreUserRequestSerializer",
    "RevokeRoleSerializer",
    "RoleAssignmentReadSerializer",
    "RoleDefinitionSerializer",
    "SuperAdminLoginSerializer",
    "SuperAdminLogoutSerializer",
    "SwitchActiveRoleSerializer",
    "UpdateSystemConfigurationSerializer",
    "UserStatusActionSerializer",
]
