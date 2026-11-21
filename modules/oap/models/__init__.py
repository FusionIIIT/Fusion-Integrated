from modules.oap.models.assistantship import AssistantshipClaim, SupervisorVerification
from modules.oap.models.bonafide import BonafideRequest
from modules.oap.models.history import CaseEvent, Notification
from modules.oap.models.leave import LeaveApplication
from modules.oap.models.nodues import NoDuesClearance, NoDuesRequest
from modules.oap.models.records import SupervisorAssignment, TAAssignment
from modules.oap.models.seminar import SeminarRequest

__all__ = [
    "AssistantshipClaim",
    "BonafideRequest",
    "CaseEvent",
    "LeaveApplication",
    "NoDuesClearance",
    "NoDuesRequest",
    "Notification",
    "SeminarRequest",
    "SupervisorAssignment",
    "SupervisorVerification",
    "TAAssignment",
]
