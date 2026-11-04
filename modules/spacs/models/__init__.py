"""Export all SPACS models."""
from modules.spacs.models.catalogue import CatalogueEntry, CataloguePolicyVersion
from modules.spacs.models.scholarships import (
    ScholarshipApplication,
    ApplicationDocument,
    ApplicationTransition,
)
from modules.spacs.models.awards import (
    AwardCycle,
    AwardCandidate,
    AwardCycleTransition,
)
from modules.spacs.models.notifications import SpacsNotificationOutbox
from modules.spacs.models.audit import SpacsAuditLog
from modules.spacs.models.tasks import SpacsTask

__all__ = [
    "CatalogueEntry",
    "CataloguePolicyVersion",
    "ScholarshipApplication",
    "ApplicationDocument",
    "ApplicationTransition",
    "AwardCycle",
    "AwardCandidate",
    "AwardCycleTransition",
    "SpacsNotificationOutbox",
    "SpacsAuditLog",
    "SpacsTask",
]
