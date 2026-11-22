"""PMS public cross-module interface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.pms.models.application import ApplicationStatus, PatentApplication


@dataclass(frozen=True)
class PatentSummaryDTO:
    user_id: int
    total_filed: int
    total_granted: int
    active_applications: int


def get_patent_summaries(user_ids: Sequence[int]) -> dict[int, PatentSummaryDTO]:
    """Return patent productivity metrics for a sequence of user IDs.
    
    Used by Faculty Appraisal and Student Achievement portals.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    apps = PatentApplication.objects.filter(is_active=True).filter(
        applicant_user_id__in=ids
    )

    result = {}
    for uid in ids:
        user_apps = [a for a in apps if a.applicant_user_id == uid]
        total_filed = len([a for a in user_apps if a.status in {
            ApplicationStatus.FILED,
            ApplicationStatus.FER_RECEIVED,
            ApplicationStatus.FER_RESPONDED,
            ApplicationStatus.GRANTED,
        }])
        total_granted = len([a for a in user_apps if a.status == ApplicationStatus.GRANTED])
        active_apps = len([a for a in user_apps if a.status not in {
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.ABANDONED,
            ApplicationStatus.EXPIRED,
        }])
        result[uid] = PatentSummaryDTO(
            user_id=uid,
            total_filed=total_filed,
            total_granted=total_granted,
            active_applications=active_apps,
        )

    return result


@dataclass(frozen=True)
class PatentStatusDTO:
    application_id: int
    application_no: str
    status: str
    official_filing_number: str
    grant_number: str


def get_patent_statuses(application_ids: Sequence[int]) -> dict[int, PatentStatusDTO]:
    """Query status for a sequence of patent application IDs."""
    ids = {int(i) for i in application_ids if i is not None}
    if not ids:
        return {}

    rows = PatentApplication.objects.filter(pk__in=ids)
    return {
        app.id: PatentStatusDTO(
            application_id=app.id,
            application_no=app.application_no,
            status=app.status,
            official_filing_number=app.official_filing_number,
            grant_number=app.grant_number,
        )
        for app in rows
    }
