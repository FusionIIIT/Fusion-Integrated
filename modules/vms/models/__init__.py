"""VMS tables, split by area (SRS section 3.14). Everything is re-exported so
`from modules.vms.models import X` keeps working.

People are plain `*_user_id` integers; foreign keys stay inside `modules.vms`.
"""
from .access import (  # noqa: F401
    Escalation, GateOverride, VisitLog, VisitPass, ZoneElevation,
)
from .base import AppendOnlyError, AppendOnlyModel  # noqa: F401
from .core import Gate, VisitRequest, Zone  # noqa: F401
from .events import (  # noqa: F401
    EmergencyMuster, EventAttendee, EventBatch, ExtensionRequest, MusterEntry,
)
from .ops import Alert, AuditLog, Notification, OfflineSyncRun  # noqa: F401
from .people import (  # noqa: F401
    PreAuthorization, RoleAssignment, VipPermission, Visitor, VisitorSession,
)
from .policy import (  # noqa: F401
    AccessPolicy, BlacklistEntry, BlacklistVersion, IntegrationSetting,
    SafeListEntry,
)
