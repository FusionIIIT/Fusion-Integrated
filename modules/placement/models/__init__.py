"""Placement domain tables, split by aggregate.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.

Import from `modules.placement.models` as before; the split is internal.
"""
from modules.placement.models.announcements import (
    Announcement,
    ConductIncident,
    NotificationOutbox,
    PlacementStatsSnapshot,
)
from modules.placement.models.applications import (
    Application,
    ApplicationTransition,
)
from modules.placement.models.companies import (
    Company,
    CompanyContact,
    RecruiterAccount,
    RecruiterLoginAttempt,
    RecruiterSession,
)
from modules.placement.models.interviews import (
    InterviewRound,
    RoundParticipation,
)
from modules.placement.models.offers import (
    Offer,
    PlacementRecord,
)
from modules.placement.models.policy import (
    PlacementPolicy,
    PolicyCategory,
)
from modules.placement.models.postings import (
    JobPosting,
)
from modules.placement.models.students import (
    PlacementRegistration,
    ProfileDocument,
    StudentProfile,
)

__all__ = [
    "Announcement",
    "Application",
    "ApplicationTransition",
    "Company",
    "CompanyContact",
    "ConductIncident",
    "InterviewRound",
    "JobPosting",
    "NotificationOutbox",
    "Offer",
    "PlacementPolicy",
    "PlacementRecord",
    "PlacementRegistration",
    "PlacementStatsSnapshot",
    "PolicyCategory",
    "ProfileDocument",
    "RecruiterAccount",
    "RecruiterLoginAttempt",
    "RecruiterSession",
    "RoundParticipation",
    "StudentProfile",
]
