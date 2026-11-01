"""HR-EIS data boundary for callers in other Fusion modules."""

from modules.hreis.models import EmployeeRecord


def get_service_records(user_ids: list[int]):
    """Return basic service-record projections for an explicit set of IAM user IDs."""
    return list(
        EmployeeRecord.objects.filter(user_id__in=user_ids).values(
            "user_id", "category", "department", "designation", "retirement_status"
        )
    )
