"""Celery task implementations for PMS scheduled jobs."""
from datetime import date, timedelta
import structlog

from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.models.office_action import OfficeAction, ResponseStatus

logger = structlog.get_logger(__name__)


def check_office_action_deadlines() -> int:
    """Audit statutory deadlines approaching for Office Actions / FER."""
    threshold = date.today() + timedelta(days=30)
    pending = OfficeAction.objects.filter(
        response_status=ResponseStatus.PENDING,
        statutory_deadline__lte=threshold,
    ).select_related("application")

    count = 0
    for action in pending:
        logger.warning(
            "pms.statutory_deadline_approaching",
            application_id=action.application_id,
            action_id=action.id,
            deadline=str(action.statutory_deadline),
        )
        count += 1
    return count


def check_maintenance_renewals() -> int:
    """Audit upcoming maintenance annuity renewals for granted patents."""
    granted = PatentApplication.objects.filter(
        status=ApplicationStatus.GRANTED,
        is_active=True,
    )
    return granted.count()


def rebuild_patent_analytics() -> dict:
    """Rebuild summary analytics snapshot for PMS."""
    from modules.pms.selectors.reporting import get_pms_summary_statistics

    stats = get_pms_summary_statistics()
    logger.info("pms.analytics_rebuilt", total=stats["total_applications"])
    return stats
