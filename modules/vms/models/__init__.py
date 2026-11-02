"""VMS domain tables, split by aggregate."""
from modules.vms.models.access import (
    AccessPolicy,
    Gate,
    Violation,
    VmsRoleAssignment,
    Zone,
    ZoneElevation,
)
from modules.vms.models.muster import Muster, MusterEntry
from modules.vms.models.visitors import (
    Alert,
    BlacklistRecord,
    SafeListRecord,
    Visitor,
    normalize_id,
)
from modules.vms.models.visits import (
    Pass,
    Visit,
    VisitLog,
    VisitRequest,
    VmsNotification,
)

__all__ = [
    "AccessPolicy",
    "Alert",
    "BlacklistRecord",
    "CampusZone",
    "EmergencyMuster",
    "Gate",
    "GateAlert",
    "Muster",
    "MusterEntry",
    "MusterRollCall",
    "Pass",
    "SafeListRecord",
    "Violation",
    "Visit",
    "VisitLog",
    "VisitPass",
    "VisitRequest",
    "Visitor",
    "VmsNotification",
    "VmsRoleAssignment",
    "Zone",
    "ZoneElevation",
    "normalize_id",
]

VisitPass = Pass
CampusZone = Zone
GateAlert = Alert
EmergencyMuster = Muster
MusterRollCall = MusterEntry

