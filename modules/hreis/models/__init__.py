"""HR-EIS Models package."""
from modules.hreis.models.appraisals import AppraisalSubmission
from modules.hreis.models.audit import HrAuditLog, HrNotification
from modules.hreis.models.claims import CpdaRequest, LtcRequest
from modules.hreis.models.leaves import LeaveRequest
from modules.hreis.models.records import EmployeeServiceRecord
from modules.hreis.models.workflow import WorkflowConfiguration

__all__ = [
    "EmployeeServiceRecord",
    "LeaveRequest",
    "AppraisalSubmission",
    "LtcRequest",
    "CpdaRequest",
    "WorkflowConfiguration",
    "HrAuditLog",
    "HrNotification",
]
