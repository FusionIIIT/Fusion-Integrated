"""HR-EIS business tables, intentionally without IAM/ERP foreign keys."""

from .appraisals import AppraisalDetail
from .claims import ClaimDetail, ClaimDocument, FinancialStatusProjection
from .events import AuditEvent, Notification, OutboxEvent
from .leave import LeaveLedgerEntry
from .policies import HRPolicyVersion
from .requests import ApprovalRouteStep, HRRequest, HRRequestTransition
from .service_records import EmployeeServiceRecord, ServiceRecordRevision

__all__ = [
    "AppraisalDetail",
    "ApprovalRouteStep",
    "AuditEvent",
    "ClaimDetail",
    "ClaimDocument",
    "EmployeeServiceRecord",
    "FinancialStatusProjection",
    "HRPolicyVersion",
    "HRRequest",
    "HRRequestTransition",
    "LeaveLedgerEntry",
    "Notification",
    "OutboxEvent",
    "ServiceRecordRevision",
]
