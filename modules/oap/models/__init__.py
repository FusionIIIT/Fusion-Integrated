from modules.oap.models.assignments import (
    TeachingAssistantAssignment,
    ThesisSupervisorAssignment,
)
from modules.oap.models.assistantship import (
    AssistantshipClaim,
    ClaimSupervisorVerification,
)
from modules.oap.models.bonafide import BonafideRequest
from modules.oap.models.leave import LeaveAttachment, StudentLeaveApplication
from modules.oap.models.no_dues import NoDuesAuthorityClearance, NoDuesRequest
from modules.oap.models.notification import OAPNotification
from modules.oap.models.seminar import GraduateSeminar

__all__ = [
    "StudentLeaveApplication",
    "LeaveAttachment",
    "BonafideRequest",
    "NoDuesRequest",
    "NoDuesAuthorityClearance",
    "ThesisSupervisorAssignment",
    "TeachingAssistantAssignment",
    "AssistantshipClaim",
    "ClaimSupervisorVerification",
    "GraduateSeminar",
    "OAPNotification",
]
