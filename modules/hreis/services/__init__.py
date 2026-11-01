"""HR-EIS Services package."""
from modules.hreis.services import (
    appraisals,
    audit,
    claims,
    leaves,
    notifications,
    service_records,
    workflow_config,
)

__all__ = [
    "audit",
    "notifications",
    "workflow_config",
    "service_records",
    "leaves",
    "appraisals",
    "claims",
]
